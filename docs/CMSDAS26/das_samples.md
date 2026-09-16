# 3. Finding samples in DAS

Before processing anything, learn to find datasets in the **Data Aggregation System (DAS)**:
<https://cmsweb.cern.ch/das/>. On the command line use `dasgoclient` (needs a valid grid proxy).

## Data — the Muon primary dataset (Run 3)
In Run 3 the `SingleMuon` PD was merged into **`Muon0` / `Muon1`**. List the 2024 NanoAOD data:
```sh
dasgoclient --query "dataset=/Muon0/Run2024*/NANOAOD"
dasgoclient --query "dataset=/Muon1/Run2024*/NANOAOD"
```
Inspect one dataset (number of files/events, run range):
```sh
dasgoclient --query "summary dataset=/Muon0/Run2024F-MINIv6NANOv15-v1/NANOAOD"
dasgoclient --query "file dataset=/Muon0/Run2024F-MINIv6NANOv15-v1/NANOAOD" | head
```

## MC — signal and backgrounds (NanoAODv15, 13.6 TeV)
```sh
# Z->tautau signal (mass-binned, powheg):
dasgoclient --query "dataset=/DYto2Tau_Bin-MLL-*_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-*/NANOAODSIM"
# Z->mumu (for the cross-section cross-check):
dasgoclient --query "dataset=/DYto2Mu_Bin-MLL-*/RunIII2024Summer24NanoAODv15-*/NANOAODSIM"
# backgrounds: ttbar, W+jets, single-top, diboson
dasgoclient --query "dataset=/TTto*_TuneCP5_13p6TeV_powheg-pythia8/RunIII2024Summer24NanoAODv15-*/NANOAODSIM"
dasgoclient --query "dataset=/Wto*Nu-2Jets*/RunIII2024Summer24NanoAODv15-*/NANOAODSIM"
```

All the datasets used in this exercise are collected in
`PicoProducer/samples/CMSDAS26/samples_mutau_2024.py` — open it and match each entry to a DAS query above.

> **Note:** in CMSDAS2020 this step also included *skimming* NanoAOD. Here we **skip the required skim** —
> the pre-made 2024 pico n-tuples are provided. You will still run the analysis module on one small sample
> in the next step to see how n-tuples are made.
