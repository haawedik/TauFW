# 2. Configuration

## Per-login environment
```sh
cd CMSSW_14_1_0_pre4/src && cmsenv
voms-proxy-init --voms cms --valid 192:00:00 --rfc   # grid proxy for DAS/xrootd
voms-proxy-info
```

## One-time TauFW / PicoProducer configuration
List the current config and see the available samples/channels:
```sh
cd $CMSSW_BASE/src/TauFW/PicoProducer
pico.py list
```

Register the **2024 era** (sample list) and the **mutau channel** (analysis module) for the exercise:
```sh
pico.py era     2024 CMSDAS26/samples_mutau_2024.py
pico.py channel mutau CMSDAS26.ModuleMuTau
pico.py set     nfilesperjob 10
```

Point the reader at the **pre-made 2024 pico n-tuples** (so you don't have to reprocess):
```sh
pico.py set picodir /eos/cms/store/group/phys_tau/TauFW/pico2024/TES_variations/$ERA/$GROUP
```
These hold the mutau (and mumu) trees for `DY, TT, WJ, ST, VV, Data`, with **all three taggers**
(DeepTau2018v2p5, PNet, UParT) and pre-computed TES/fake systematic shifts.

Have a look at the sample list and the analysis module you just registered:
```sh
less $CMSSW_BASE/src/TauFW/PicoProducer/samples/CMSDAS26/samples_mutau_2024.py
less $CMSSW_BASE/src/TauFW/PicoProducer/python/analysis/CMSDAS26/ModuleMuTau.py
```

The **2024 TES/TauID measurement** (templates + measured scale factors) used later is at:
```
/eos/user/h/haawedik/2024_SFs/Iteration4_corrTES/
  input_pt_less_region/   # m_vis templates per (VSjet,VSe) WP  -> Combine (Tier B)
  tau_sf/                 # measured TauCorrections_2024_corrTES.json + TauES_SF_*.json -> plot level (Tier A)
```
