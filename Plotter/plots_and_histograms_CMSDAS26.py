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
import numpy as np
import ROOT as R
from TauFW.Plotter.plot.utils import LOG as PLOG
from TauFW.Plotter.sample.utils import LOG, ensuredir, repkey, setera, Sel, Var
from config.samples_v15 import getsampleset

R.gROOT.SetBatch(True)


def getset(channel,era,fpattern,addsf=None,rmsf=None,table=True):
  """Build the 2024 sample set (ZTT/ZL/ZJ + TT + ST + VV + WJ + data), split DY by gen-match.
  addsf: extra weight applied to all MC (e.g. a measured TauID SF) -> Tier A.
  rmsf:  weight(s) to remove from MC (e.g. 'idweight_2') so a SF can be re-measured."""
  setera(era)
  rmsfs  = rmsf if rmsf else [ ]
  addsfs = addsf if addsf else [ ]
  sampleset = getsampleset(channel,era,fname=fpattern,rmsf=rmsfs,addsf=addsfs,split=['DY'],table=table)
  return sampleset


def plot(sampleset,channel,era,parallel=True,tag="",outdir="plots",histdir=""):
  """Data/MC comparison in the opposite-sign signal region and the same-sign QCD control region."""
  LOG.header("plot")

  # SELECTIONS: OS signal region + SS control region (QCD-enriched); mt_1<65 keeps the W tail out
  baseline = "q_1*q_2<0 && iso_1<0.15 && idDeepTau2018v2p5VSjet_2>=5 && idDeepTau2018v2p5VSe_2>=2 && idDeepTau2018v2p5VSmu_2>=4 && mt_1<65"
  ss       = baseline.replace("q_1*q_2<0","q_1*q_2>0")
  selections = [
    Sel('baseline',        baseline),
    Sel('baseline_cr_qcd', ss),
  ]

  # VARIABLES available in the 2024 pico ntuples (extend as you like)
  variables = [
    Var('m_vis',        40,  0, 200),
    Var('pt_1',  "Muon pt",   40,  0, 120),
    Var('pt_2',  "tau_h pt",  40,  0, 120),
    Var('eta_2', "tau_h eta", 30, -3,   3),
    Var('mt_1',  "mt(mu,MET)",40,  0, 200),
    Var('met',   50,  0, 150),
    Var('decayMode_2', "tau_h decay mode", 14, 0, 14),
  ]

  outdir   = ensuredir(repkey(outdir,CHANNEL=channel,ERA=era))
  histdir  = ensuredir(repkey(histdir,CHANNEL=channel,ERA=era,TAG=tag))
  outhists = R.TFile.Open(histdir,'recreate')
  exts     = ['png','pdf']
  for selection in selections:
    outhists.mkdir(selection.filename)
    # data-driven QCD from the same-sign region, extrapolated to opposite-sign with 'scale'
    stacks = sampleset.getstack(variables,selection,method='QCD_OSSS',scale=1.1,parallel=parallel)
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


def plot_tagger_comparison(sampleset,channel,era,outdir="plots",tag=""):
  """ROC-like comparison of the three tau taggers: genuine-tau efficiency vs jet->tau fake rate,
  scanning the raw VSjet score. Signal = genuine taus in ZTT (genmatch_2==5);
  background = jet fakes in W+jets (genmatch_2==0)."""
  LOG.header("tagger comparison")
  taggers = {
    'DeepTau2018v2p5': 'rawDeepTau2018v2p5VSjet_2',
    'PNet':            'rawPNetVSjet_2',
    'UParT':           'rawUParTVSjet_2',
  }
  base   = "q_1*q_2<0 && iso_1<0.15 && idDeepTau2018v2p5VSmu_2>=1 && mt_1<65" # loose, tagger-agnostic
  sig    = sampleset.get('ZTT',unique=True) # genuine taus
  bkg    = sampleset.get('WJ', unique=True) # jet fakes
  outdir = ensuredir(repkey(outdir,CHANNEL=channel,ERA=era))
  nbins  = 100
  roc    = { }
  for name,branch in taggers.items():
    var  = Var(branch,nbins,0,1)
    hsig = sig.gethist(var,Sel('sig',base+" && genmatch_2==5"))
    hbkg = bkg.gethist(var,Sel('bkg',base+" && genmatch_2==0"))
    stot = hsig.Integral(0,nbins+1); btot = hbkg.Integral(0,nbins+1)
    eff  = np.array([hsig.Integral(i,nbins+1)/stot if stot>0 else 0 for i in range(1,nbins+1)])
    fake = np.array([hbkg.Integral(i,nbins+1)/btot if btot>0 else 0 for i in range(1,nbins+1)])
    roc[name] = (fake,eff)
    LOG.info(">>> %-16s: AUC-like sum(eff*dfake)=%.4f"%(name,float(np.trapz(eff,fake)*-1)))
  # draw ROC
  c = R.TCanvas('roc','roc',700,650); c.SetLogx()
  graphs = [ ]; colors = [R.kBlack,R.kRed+1,R.kAzure+2]; leg = R.TLegend(0.18,0.70,0.55,0.88)
  for (name,(fake,eff)),col in zip(roc.items(),colors):
    g = R.TGraph(len(fake),fake.astype('d'),eff.astype('d'))
    g.SetLineColor(col); g.SetLineWidth(2); g.SetTitle(";jet#rightarrow#tau_{h} fake rate;genuine #tau_{h} efficiency")
    g.GetXaxis().SetLimits(1e-3,1.0); g.GetYaxis().SetRangeUser(0,1.05)
    ('AL' if not graphs else 'L') and g.Draw('AL' if not graphs else 'L SAME')
    graphs.append(g); leg.AddEntry(g,name,'l')
  leg.Draw()
  fname = os.path.join(outdir,"tagger_ROC_%s_%s%s"%(channel,era,tag))
  for ext in ('png','pdf'): c.SaveAs(fname+"."+ext)
  LOG.info(">>> wrote %s.png"%fname)


def main(args):
  channel  = args.channel
  era      = args.era
  parallel = args.parallel
  tag      = args.tag
  fpattern = args.picopattern
  addsf    = [args.addsf] if args.addsf else None
  rmsf     = args.rmsf.split(',') if args.rmsf else None

  setera(era)
  sampleset = getset(channel,era,fpattern,addsf=addsf,rmsf=rmsf,table=True)
  if args.tagger:
    plot_tagger_comparison(sampleset,channel,era,outdir="plots/$ERA",tag=tag)
  else:
    plot(sampleset,channel,era,parallel=parallel,tag=tag,
         outdir="plots/$ERA",histdir="hists/$ERA/$CHANNEL$TAG.root")


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
  parser.add_argument('--picopattern',  dest='picopattern', default="$PICODIR/$SAMPLE_$CHANNEL$TAG.root", help="pico file name pattern")
  parser.add_argument('-v','--verbose', dest='verbosity', type=int, nargs='?', const=1, default=0)
  args = parser.parse_args()
  LOG.verbosity = args.verbosity
  PLOG.verbosity = args.verbosity
  main(args)
  print("\n>>> Done.")
