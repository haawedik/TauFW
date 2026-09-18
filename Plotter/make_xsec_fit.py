#! /usr/bin/env python3
# Author: CMSDAS26 Tau long exercise
# Description: build a small DEDICATED Combine datacard for the Z cross-section fit (Fit 2),
#   separate from the TES/TauID SF fit (Fit 1). POI = r, the signal strength on the Z signal:
#       sigma(Z) = r * sigma_theory .
#   Signal = ZTT (mutau) or DY (mumu). Backgrounds are floated within lnN normalization
#   uncertainties. For mutau the TauID and TES scale factors (already APPLIED when the input
#   hists were produced with --addsf) are varied within their measured uncertainties as lnN
#   nuisances on the ZTT signal ("fixed to measured, floated up/down"). For mumu use --onebin
#   to collapse m_vis to a single bin (a counting experiment).
#
# Inputs: the per-process histograms written by plots_and_histograms_CMSDAS26.py, i.e.
#   hists/<era>/<channel>.root -> dir '<region>' -> 'm_vis_<process>' (+ '..._<syst>Up/Down').
# Usage:
#   ./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau --addsf "getTauIDSF(dm_2,genmatch_2)"
#   ./make_xsec_fit.py -c mutau -y 2024                     # inclusive m_vis mutau card
#   ./plots_and_histograms_CMSDAS26.py -y 2024 -c mumu
#   ./make_xsec_fit.py -c mumu -y 2024 --onebin            # 1-bin mumu counting card
# Then (see docs/CMSDAS26/measurement.md):
#   text2workspace.py xsec_fit/datacard_<channel>.txt
#   combine -M MultiDimFit -P r --algo singles xsec_fit/datacard_<channel>.root
import os
import argparse
import ROOT as R
R.gROOT.SetBatch(True)

# background normalization uncertainties (relative) -> "backgrounds floated within uncertainties".
# Any background not listed falls back to DEFAULT_LNN.
BKG_LNN = {'WJ':0.15,'QCD':0.20,'ZJ':0.15,'ZL':0.10,'TT':0.06,'ST':0.10,'VV':0.05,'Top':0.08}
DEFAULT_LNN = 0.10
# hist names the plotter uses for the observed data (data group name, e.g. 'Muon' in Run3)
DATA_NAMES = ('data_obs','data','Muon','Muon0','Muon1','SingleMuon','EGamma','Observed')


def collect_nominal(fin, region, var):
  """Return {process: TH1} for nominal hists named '<var>_<process>' (skip *Up/*Down variations)."""
  d = fin.Get(region)
  if not d:
    raise SystemExit("region %r not found in input file" % region)
  procs, pre = {}, var + "_"
  for key in d.GetListOfKeys():
    n = key.GetName()
    if not n.startswith(pre):
      continue
    proc = n[len(pre):]
    if proc.endswith('Up') or proc.endswith('Down'):
      continue  # systematic shape variation, not a nominal process
    if proc.endswith('QCD'):
      proc = 'QCD'  # plotter names the data-driven QCD '<region>_QCD'
    h = d.Get(n)
    h.SetDirectory(0)
    procs[proc] = h
  return procs


def to_onebin(h):
  h2 = h.Clone(h.GetName() + "_1b")
  h2.SetDirectory(0)
  h2.Rebin(h2.GetNbinsX())  # merge all bins -> single-bin counting experiment
  return h2


def main():
  ap = argparse.ArgumentParser(description="CMSDAS26 dedicated Z cross-section datacard builder")
  ap.add_argument('-c', '--channel', default='mutau', help="mutau or mumu")
  ap.add_argument('-y', '--era', default='2024')
  ap.add_argument('-r', '--region', default='signalRegion', help="TDirectory in the hist file")
  ap.add_argument('--var', default='m_vis')
  ap.add_argument('--histfile', default=None, help="default hists/<era>/<channel>.root")
  ap.add_argument('--signal', default=None, help="signal process (default: ZTT for mutau, DY for mumu)")
  ap.add_argument('--onebin', action='store_true', help="collapse to a single bin (use for mumu)")
  ap.add_argument('--tauid-unc', dest='tauid_unc', type=float, default=0.05, help="TauID SF rel. uncertainty (mutau)")
  ap.add_argument('--tes-unc', dest='tes_unc', type=float, default=0.03, help="TES rel. uncertainty (mutau)")
  ap.add_argument('--lumi-unc', dest='lumi_unc', type=float, default=0.014, help="luminosity rel. uncertainty")
  ap.add_argument('-o', '--outdir', default='xsec_fit')
  args = ap.parse_args()

  signal = args.signal or ('ZTT' if 'tau' in args.channel else 'DY')
  histfile = args.histfile or "hists/%s/%s.root" % (args.era, args.channel)
  fin = R.TFile.Open(histfile)
  if not fin or fin.IsZombie():
    raise SystemExit("cannot open %s -- run plots_and_histograms_CMSDAS26.py first" % histfile)

  nominal = collect_nominal(fin, args.region, args.var)
  dataname = next((p for p in nominal if p in DATA_NAMES), None)
  if not dataname:
    raise SystemExit("no data histogram (data_obs/data) in %s:%s" % (histfile, args.region))
  data = nominal.pop(dataname)
  if signal not in nominal:
    raise SystemExit("signal %r not found; available: %s" % (signal, sorted(nominal)))

  if args.onebin:
    data = to_onebin(data)
    nominal = {p: to_onebin(h) for p, h in nominal.items()}

  backgrounds = sorted(p for p in nominal if p != signal and nominal[p].Integral() > 0)
  procs = [signal] + backgrounds
  ismc = lambda p: p != 'QCD'  # QCD is data-driven -> no lumi uncertainty

  os.makedirs(args.outdir, exist_ok=True)
  shapes = os.path.join(args.outdir, "shapes_%s.root" % args.channel)
  fout = R.TFile(shapes, 'RECREATE')
  data.Write('data_obs')
  for p in procs:
    nominal[p].Write(p)
  fout.Close()

  bin = args.channel
  def row(name, typ, vals):
    return name + " " + typ + "".join(" %s" % v for v in vals)
  L = []
  L += ["imax 1", "jmax %d" % (len(procs) - 1), "kmax *", "-" * 60]
  L += ["shapes * %s %s $PROCESS $PROCESS_$SYSTEMATIC" % (bin, os.path.basename(shapes)), "-" * 60]
  L += ["bin %s" % bin, "observation %.4f" % data.Integral(), "-" * 60]
  L += [row("bin", "", [bin for _ in procs])]
  L += [row("process", "", procs)]
  L += [row("process", "", [0 if p == signal else i for i, p in enumerate(procs)])]  # signal id = 0
  L += [row("rate", "", ["%.4f" % nominal[p].Integral() for p in procs])]
  L += ["-" * 60]
  # luminosity on all MC
  L += [row("lumi_%s" % args.era, "lnN", ["%.3f" % (1 + args.lumi_unc) if ismc(p) else "-" for p in procs])]
  # TauID + TES on the signal (mutau only): measured value applied, varied within uncertainty
  if 'tau' in args.channel and signal == 'ZTT':
    L += [row("tauID", "lnN", ["%.3f" % (1 + args.tauid_unc) if p == signal else "-" for p in procs])]
    L += [row("tes",   "lnN", ["%.3f" % (1 + args.tes_unc)   if p == signal else "-" for p in procs])]
  # background normalizations (floated within uncertainties)
  for b in backgrounds:
    unc = BKG_LNN.get(b, DEFAULT_LNN)
    L += [row("norm_%s" % b, "lnN", ["%.3f" % (1 + unc) if p == b else "-" for p in procs])]
  L += ["* autoMCStats 0"]

  card = os.path.join(args.outdir, "datacard_%s.txt" % args.channel)
  with open(card, 'w') as f:
    f.write("\n".join(L) + "\n")
  print(">>> wrote %s" % shapes)
  print(">>> wrote %s  (signal=%s, %d backgrounds, %s)" %
        (card, signal, len(backgrounds), "1 bin" if args.onebin else "%d bins" % data.GetNbinsX()))
  print(">>> POI r scales %s;  sigma(Z) = r * sigma_theory" % signal)


if __name__ == '__main__':
  main()
