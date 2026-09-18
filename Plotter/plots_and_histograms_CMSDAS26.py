#! /usr/bin/env python3
# Author: CMSDAS26 Tau long exercise 
# Description: data/MC control plots + data-driven QCD (OS/SS) for the 2024 mutau exercise,
#              plus a 3-tagger comparison (DeepTau2018v2p5 / PNet / UParT) and an optional
#              plot-time TauID/TES scale-factor hook (Tier A of the TES/TauID measurement).
# Usage:
#   ./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau                 # control plots
#   ./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau --tagger         # ROC-like tagger comparison
#   ./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau --addsf "<expr>" # apply a plot-time SF (Tier A)
# It reads the pre-made 2024 pico ntuples via the production sample set (config.samples_v15),
# so cross-sections / k-factors / effective events are handled for you.
import os
import json
import bisect
import numpy as np
import ROOT as R
from TauFW.Plotter.plot.utils import LOG as PLOG
from TauFW.Plotter.sample.utils import LOG, ensuredir, repkey, setera, Sel, Var
from config.samples_v15 import getsampleset

R.gROOT.SetBatch(True)

# default measured 2024 TES/TauID SFs (Iteration4). Override with --tauid-sf.
DEFAULT_SF_JSON = "/eos/user/h/haawedik/2024_SFs/Iteration4_corrTES/tau_sf/TauCorrections_2024_corrTES.json"


def _sf_eval(node, inp):
  """Minimal evaluator for a correctionlib schema node (category/binning/leaf); stdlib only,
  so it works even when the compiled correctionlib is unavailable."""
  if isinstance(node, (int, float)):
    return float(node)
  nt = node.get("nodetype")
  if nt == "category":
    key = inp[node["input"]]
    for it in node["content"]:
      if it["key"] == key:
        return _sf_eval(it["value"], inp)
    if node.get("default") is not None:
      return _sf_eval(node["default"], inp)
    raise KeyError("%s=%r" % (node["input"], key))
  if nt == "binning":
    x = inp[node["input"]]; e = node["edges"]
    i = max(0, min(bisect.bisect_right(e, x) - 1, len(node["content"]) - 1))
    return _sf_eval(node["content"][i], inp)
  raise ValueError("unsupported SF node %r" % nt)


def _pt_edges(node):
  if isinstance(node, dict):
    if node.get("nodetype") == "binning" and node.get("input") == "pT":
      return node["edges"]
    for it in node.get("content", []):
      v = it["value"] if isinstance(it, dict) and "value" in it else it
      r = _pt_edges(v)
      if r:
        return r
  return None


def build_tauid_sf_weight(jsonfile, wp_vsjet='Tight', wp_vse='VVLoose', wp_vsmu='Tight',
                          corrname='TauIdSF_2024_corrTES', syst='nom'):
  """Build a per-(DM,pt) TauID SF weight expression from the measured JSON, applied to genuine taus
  (genmatch_2==5) and 1.0 otherwise. Reads the JSON directly (no correctionlib dependency)."""
  d = json.load(open(jsonfile))
  data = [c for c in d["corrections"] if c["name"] == corrname][0]["data"]
  edges = _pt_edges(data) or [0.0, 1e4]
  def val(dm, pt):
    return _sf_eval(data, {"genmatch": 5, "DM": dm, "pT": pt, "syst": syst,
                           "wp_VSmu": wp_vsmu, "wp_VSe": wp_vse, "wp_VSjet": wp_vsjet})
  mids = [0.5 * (edges[i] + edges[i + 1]) for i in range(len(edges) - 1)]
  dmexpr = {}
  for dm in (0, 1, 10, 11):
    vals = [val(dm, m) for m in mids]
    e = "".join("pt_2<%g?%.4f:" % (edges[i + 1], vals[i]) for i in range(len(vals) - 1))
    dmexpr[dm] = "(" + e + "%.4f)" % vals[-1]
  expr = ("(genmatch_2!=5?1.0:dm_2==0?%s:dm_2==1?%s:dm_2==10?%s:dm_2==11?%s:1.0)"
          % (dmexpr[0], dmexpr[1], dmexpr[10], dmexpr[11]))
  LOG.info(">>> TauID SF weight (VSjet=%s,VSe=%s): %s" % (wp_vsjet, wp_vse, expr))
  return expr


def build_tes_map(jsonfile, wp_vsjet='Tight', wp_vse='VVLoose', wp_vsmu='Tight',
                  corrname='TauES_2024_corrTES', step=0.002):
  """{DM: '_TESXpXXX'} — the measured per-DM TES snapped to the pre-shifted sample grid (step 0.002).
  TES is pt-independent, so one value per DM (evaluated at genmatch=5)."""
  d = json.load(open(jsonfile))
  data = [c for c in d["corrections"] if c["name"] == corrname][0]["data"]
  out = {}
  for dm in (0, 1, 10, 11):
    tes = _sf_eval(data, {"genmatch": 5, "DM": dm, "pT": 40.0, "syst": "nom",
                          "wp_VSmu": wp_vsmu, "wp_VSe": wp_vse, "wp_VSjet": wp_vsjet})
    grid = round(tes / step) * step
    out[dm] = ("_TES%.3f" % grid).replace(".", "p")  # e.g. 0.994 -> _TES0p994
  LOG.info(">>> per-DM TES samples: %s" % out)
  return out


def _apply_tes_ztt(sampleset, stacks, variables, selection, tesmap, parallel=True):
  """Replace the ZTT histograms in 'stacks' with the per-DM TES-shifted ones: for each DM, swap ZTT to
  the closest pre-shifted _TES sample (sampleset.shift) and take its dm_2==DM slice, then sum over DM."""
  ztt_sum = {}  # Var.name -> TH1 (summed over DM, TES-shifted)
  for dm, tag in tesmap.items():
    LOG.info(">>> TES swap: DM%-2d -> ZTT read from *%s*.root samples" % (dm, tag))
    shifted = sampleset.shift(['ZTT'], tag, tag, split=True, filter=False, share=True)
    sel_dm = Sel(selection.filename + '_dm%d' % dm, selection.selection + " && dm_2==%d" % dm)
    res = shifted.getstack(variables, sel_dm, method=None, data=False, parallel=parallel)
    items = res.items() if isinstance(res, dict) else [(res, (variables[0], sel_dm))]
    for stack, key in items:
      var = key[0] if isinstance(key, tuple) else key
      for h in stack.hists:
        if h.GetName().endswith('_ZTT'):
          hc = h.Clone(h.GetName() + "_tes%d" % dm); hc.SetDirectory(0)
          if var.name in ztt_sum: ztt_sum[var.name].Add(hc)
          else: ztt_sum[var.name] = hc
          break
  for stack, key in stacks.items():
    var = key[0] if isinstance(key, tuple) else key
    if var.name not in ztt_sum: continue
    for h in stack.hists:
      if h.GetName().endswith('_ZTT'):
        h.Reset(); h.Add(ztt_sum[var.name]); break


def getset(channel,era,fpattern,addsf=None,rmsf=None,table=True):
  """Build the 2024 sample set (ZTT/ZL/ZJ + TT + ST + VV + WJ + data), split DY by gen-match.
  addsf: extra weight applied to all MC (e.g. a measured TauID SF) -> Tier A.
  rmsf:  weight(s) to remove from MC (e.g. 'idweight_2') so a SF can be re-measured."""
  setera(era)
  rmsfs  = rmsf if rmsf else [ ]
  addsfs = addsf if addsf else [ ]
  split  = ['DY'] if 'tau' in channel else [ ] # gen-match split needs a hadronic tau (mutau only)
  sampleset = getsampleset(channel,era,fname=fpattern,rmsf=rmsfs,addsf=addsfs,split=split,table=table)
  return sampleset


def plot(sampleset,channel,era,parallel=True,tag="",outdir="plots",histdir="",apply_tes=None):
  """Data/MC comparison in the mutau signal region (mt_1<65). If apply_tes (a {DM:'_TES..'} map) is
  given, the ZTT signal is rebuilt from the per-DM closest TES-shifted samples."""
  LOG.header("plot")

  # SELECTIONS + VARIABLES (channel-aware)
  if channel=='mumu':
    # Z->mumu: two isolated opposite-sign muons; no tau cuts, no data-driven QCD (negligible)
    mumusel = "q_1*q_2<0 && iso_1<0.15 && iso_2<0.15"
    selections = [ Sel('signalRegion', mumusel) ]
    variables  = [ Var('m_vis', 40, 50, 130) ]  # Z peak; the xsec fit integrates this to one bin
    qcdmethod  = None
  else:
    # mutau signal region: opposite-sign, mt_1<65 (cuts the W tail). QCD is still estimated
    # data-driven from the same-sign region internally by the OS/SS method (no separate SS plot).
    signalRegion = "q_1*q_2<0 && iso_1<0.15 && idDeepTau2018v2p5VSjet_2>=5 && idDeepTau2018v2p5VSe_2>=2 && idDeepTau2018v2p5VSmu_2>=4 && mt_1<65"
    selections = [ Sel('signalRegion', signalRegion) ]
    variables = [
      Var('m_vis',        40,  0, 200),
      Var('pt_1',  "Muon pt",   40,  0, 120),
      Var('pt_2',  "tau_h pt",  40,  0, 120),
      Var('eta_2', "tau_h eta", 30, -3,   3),
      Var('mt_1',  "mt(mu,MET)",40,  0, 200),
      Var('met',   50,  0, 150),
      Var('dm_2', "tau_h decay mode", 14, 0, 14),
    ]
    qcdmethod  = 'QCD_OSSS'

  outdir   = ensuredir(repkey(outdir,CHANNEL=channel,ERA=era))
  histdir  = ensuredir(repkey(histdir,CHANNEL=channel,ERA=era,TAG=tag))
  outhists = R.TFile.Open(histdir,'recreate')
  exts     = ['png','pdf']
  for selection in selections:
    outhists.mkdir(selection.filename)
    # data-driven QCD from the same-sign region, extrapolated to opposite-sign with 'scale'
    stacks = sampleset.getstack(variables,selection,method=qcdmethod,scale=1.1,parallel=parallel)
    if apply_tes and 'tau' in channel:  # rebuild ZTT from the per-DM TES-shifted samples
      _apply_tes_ztt(sampleset,stacks,variables,selection,apply_tes,parallel)
    fname  = "%s/$VAR_%s-%s-%s$TAG"%(outdir,channel,selection.filename,era)
    text   = "%s: %s"%(channel.replace('mu',"#mu").replace('tau',"#tau_{h}"),selection.title)
    for stack, variable in stacks.items():
      outhists.cd(selection.filename)
      for h in stack.hists:
        h.Write(h.GetName().replace("QCD_","QCD")+tag,R.TH1.kOverwrite)
      stack.draw()
      stack.drawlegend(x1=0.6,x2=0.95,y1=0.35,y2=0.95)
      stack.drawtext(text)
      stack.saveas(fname,ext=exts,tag=tag)
      stack.close()
  outhists.Close()


def _summed_mc_multi(sampleset, variables, sel, parallel=True):
  """{Var.name: total-MC TH1} for every variable in 'variables' under selection 'sel' (data excluded,
  so a genmatch_2 cut is safe). One event loop for all variables."""
  res = sampleset.getstack(variables, sel, method=None, data=False, parallel=parallel)
  items = res.items() if isinstance(res, dict) else [(res, (variables[0], sel))]
  out = {}
  for stack, key in items:
    var = key[0] if isinstance(key, tuple) else key
    htot = None
    for h in stack.hists:
      if 'data' in h.GetName().lower():
        continue
      hc = h.Clone(h.GetName()+"_c"); hc.SetDirectory(0)
      if htot is None: htot = hc
      else: htot.Add(hc)
    out[var.name] = htot
  return out


def _roc_arrays(hsig, hbkg, nbins):
  """Cumulative (fake rate, efficiency) scanning the raw score over the in-range [0,1] bins.
  The -1 'no-score' default lands in the underflow (bin 0) and is excluded from both."""
  stot = hsig.Integral(1, nbins+1); btot = hbkg.Integral(1, nbins+1)
  eff  = np.array([hsig.Integral(i, nbins+1)/stot if stot>0 else 0 for i in range(1, nbins+1)])
  fake = np.array([hbkg.Integral(i, nbins+1)/btot if btot>0 else 0 for i in range(1, nbins+1)])
  return fake, eff, stot, btot


def plot_tagger_comparison(sampleset,channel,era,outdir="plots",tag="",parallel=True):
  """ROC comparison of the three taggers for VSjet, VSe and VSmu. Signal = genuine taus
  (genmatch_2==5); background = jet (0), e (1||3) or mu (2||4) fakes. Log-log axes; raw score in [0,1]."""
  LOG.header("tagger comparison")
  families = [
    ('VSjet', {'DeepTau2018v2p5':'rawDeepTau2018v2p5VSjet_2','PNet':'rawPNetVSjet_2','UParT':'rawUParTVSjet_2'},
     "genmatch_2==0", "jet#rightarrow#tau_{h} fake rate"),
    ('VSe',   {'DeepTau2018v2p5':'rawDeepTau2018v2p5VSe_2',  'PNet':'rawPNetVSe_2',  'UParT':'rawUParTVSe_2'},
     "(genmatch_2==1||genmatch_2==3)", "e#rightarrow#tau_{h} fake rate"),
    ('VSmu',  {'DeepTau2018v2p5':'rawDeepTau2018v2p5VSmu_2', 'PNet':'rawPNetVSmu_2', 'UParT':'rawUParTVSmu_2'},
     "(genmatch_2==2||genmatch_2==4)", "#mu#rightarrow#tau_{h} fake rate"),
  ]
  base   = "q_1*q_2<0 && iso_1<0.15 && mt_1<65"  # loose, no tau-ID cuts (unbiased between taggers)
  outdir = ensuredir(repkey(outdir,CHANNEL=channel,ERA=era))
  nbins  = 100
  colors = [R.kBlack, R.kRed+1, R.kAzure+2]

  # signal (genuine taus): all 9 discriminants in ONE event loop
  allbranches = [b for _,taggers,_,_ in families for b in taggers.values()]
  sig = _summed_mc_multi(sampleset, [Var(b,nbins,0,1) for b in allbranches],
                         Sel('sig', base+" && genmatch_2==5"), parallel)

  for fam, taggers, bkgsel, xtitle in families:
    bkg = _summed_mc_multi(sampleset, [Var(b,nbins,0,1) for b in taggers.values()],
                           Sel('bkg_'+fam, base+" && "+bkgsel), parallel)
    c = R.TCanvas('roc_'+fam,'roc',700,650); c.SetLogx(); c.SetGrid()  # x (fake rate) log, y (eff) linear
    frame = c.DrawFrame(1e-3, 0.0, 1.0, 1.05)                          # fake rate floored at 1e-3
    frame.SetTitle("%s ROC (%s);%s;genuine #tau_{h} efficiency"%(fam,channel,xtitle))
    leg = R.TLegend(0.16,0.72,0.52,0.90); graphs = [ ]
    for (name,branch),col in zip(taggers.items(),colors):
      hsig = sig.get(branch); hbkg = bkg.get(branch)
      if hsig is None or hbkg is None:
        LOG.warning("%s/%s: missing hist, skip"%(fam,name)); continue
      fake,eff,stot,btot = _roc_arrays(hsig,hbkg,nbins)
      m = (fake>0)  # log-x needs fake>0; the efficiency axis is linear
      if int(m.sum())<2: continue
      g = R.TGraph(int(m.sum()), fake[m].astype('d'), eff[m].astype('d'))
      g.SetLineColor(col); g.SetLineWidth(2); g.Draw('L SAME')
      leg.AddEntry(g,name,'l'); graphs.append(g)
      LOG.info(">>> %-6s %-16s sig=%.0f bkg=%.0f AUC~%.3f"%(fam,name,stot,btot,float(abs(np.trapz(eff,fake)))))
    leg.Draw()
    fn = os.path.join(outdir,"tagger_ROC_%s_%s_%s%s"%(fam,channel,era,tag))
    for ext in ('png','pdf'): c.SaveAs(fn+"."+ext)
    LOG.info(">>> wrote %s.png"%fn)


def main(args):
  channel  = args.channel
  era      = args.era
  parallel = args.parallel
  tag      = args.tag
  fpattern = args.picopattern
  addsf    = [args.addsf] if args.addsf else [ ]
  if args.tauid_sf:  # apply the measured TauID SF (per DM,pt weight on genuine taus)
    addsf.append(build_tauid_sf_weight(args.tauid_sf, wp_vsjet=args.vsjet, wp_vse=args.vse))
  addsf    = addsf or None
  rmsf     = args.rmsf.split(',') if args.rmsf else None

  tesmap = build_tes_map(args.apply_tes, wp_vsjet=args.vsjet, wp_vse=args.vse) if args.apply_tes else None

  setera(era)
  sampleset = getset(channel,era,fpattern,addsf=addsf,rmsf=rmsf,table=True)
  if args.tagger:
    plot_tagger_comparison(sampleset,channel,era,outdir="plots/$ERA",tag=tag,parallel=parallel)
  else:
    plot(sampleset,channel,era,parallel=parallel,tag=tag,
         outdir="plots/$ERA",histdir="hists/$ERA/$CHANNEL$TAG.root",apply_tes=tesmap)


if __name__ == "__main__":
  from argparse import ArgumentParser
  parser = ArgumentParser(prog="plots_and_histograms_CMSDAS26",description="CMSDAS26 mutau plots",epilog="Good luck!")
  parser.add_argument('-y','--era',     dest='era', default='2024', help="era, default=%(default)s")
  parser.add_argument('-c','--channel', dest='channel', default='mutau', help="channel, default=%(default)s")
  parser.add_argument('-t','--tag',     dest='tag', default="", help="output tag")
  parser.add_argument('-s','--serial',  dest='parallel', action='store_false', help="run serial")
  parser.add_argument('--tagger',       dest='tagger', action='store_true', help="make the 3-tagger ROC comparison instead of control plots")
  parser.add_argument('--addsf',        dest='addsf', default="", help="extra weight applied to all MC (Tier A SF), e.g. a measured TauID SF expression")
  parser.add_argument('--rmsf',         dest='rmsf', default="", help="comma-separated weights to remove from MC (e.g. idweight_2) so a SF can be re-measured")
  parser.add_argument('--tauid-sf',     dest='tauid_sf', nargs='?', const=DEFAULT_SF_JSON, default="",
                                         help="apply the measured TauID SF as a per-(DM,pt) weight on genuine taus; "
                                              "bare flag uses the Iteration4 JSON, or give a JSON path")
  parser.add_argument('--vsjet',        dest='vsjet', default='Tight',   help="VSjet WP for the TauID SF/TES (default: %(default)s)")
  parser.add_argument('--vse',          dest='vse',   default='VVLoose', help="VSe WP for the TauID SF/TES (default: %(default)s)")
  parser.add_argument('--apply-tes',    dest='apply_tes', nargs='?', const=DEFAULT_SF_JSON, default="",
                                         help="rebuild ZTT from the per-DM closest TES-shifted samples; "
                                              "bare flag uses the Iteration4 JSON, or give a JSON path")
  parser.add_argument('--picopattern',  dest='picopattern', default="$PICODIR/$SAMPLE_$CHANNEL$TAG.root", help="pico file name pattern")
  parser.add_argument('-v','--verbose', dest='verbosity', type=int, nargs='?', const=1, default=0)
  args = parser.parse_args()
  LOG.verbosity = args.verbosity
  PLOG.verbosity = args.verbosity
  main(args)
  print("\n>>> Done.")
