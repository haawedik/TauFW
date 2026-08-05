#!/usr/bin/env python3
# Combine 2025 + 2026 data pileup profiles into one Run-3 profile.
# pileupCalc normalises each histogram to its own integrated luminosity,
# so a plain 1:1 Add() already gives the luminosity-weighted combination.

import os
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)

myDir = os.path.dirname(os.path.abspath(__file__))

minbiases = ['66p0168', '69p2', '72p3832', '80p0']  # nominal is 69p2

for minbias in minbiases:
    f1 = ROOT.TFile.Open(os.path.join(myDir, f'Data_PileUp_2025_{minbias}.root'))
    f2 = ROOT.TFile.Open(os.path.join(myDir, f'Data_PileUp_2026_{minbias}.root'))

    h1 = f1.Get('pileup')
    h2 = f2.Get('pileup')
    print(f'[{minbias}] 2025 integral: {h1.Integral():.6g}  mean: {h1.GetMean():.3f}')
    print(f'[{minbias}] 2026 integral: {h2.Integral():.6g}  mean: {h2.GetMean():.3f}')

    hsum = h1.Clone()
    hsum.Reset()
    hsum.Add(h1, h2, 1, 1)  # assume correct normalisation by luminosity
    frac = hsum.Integral() / (h1.Integral() + h2.Integral())
    print(f'[{minbias}] sum  integral: {hsum.Integral():.6g}  mean: {hsum.GetMean():.3f}  (frac {frac:.6f})')

    outname = os.path.join(myDir, f'Data_PileUp_2025_2026_{minbias}.root')
    fout = ROOT.TFile.Open(outname, 'RECREATE')
    fout.cd()
    hsum.Write()
    print(f'[{minbias}] wrote {outname}')

    f1.Close()
    f2.Close()
    fout.Close()
