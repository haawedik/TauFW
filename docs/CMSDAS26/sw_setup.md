# 1. Software setup

Everything runs in **one** CMSSW area on **lxplus (el9 / AlmaLinux 9)**. Combine **v10** is el9-native, so
no separate combine release is needed (unlike the old 2020 two-area setup).

## Create the working area
```sh
export SCRAM_ARCH=el9_amd64_gcc12
cmsrel CMSSW_14_1_0_pre4
cd CMSSW_14_1_0_pre4/src
cmsenv
```

## TauFW
```sh
git clone https://github.com/cms-tau-pog/TauFW.git
# NanoAOD-tools is needed to (re)process NanoAOD:
git clone https://github.com/cms-nanoAOD/nanoAOD-tools.git PhysicsTools/NanoAODTools
scram b -j8
```
> For the CMSDAS26 material specifically, use the branch that carries the 2024 wiring and the
> `CMSDAS26/` folders (ask the organizers which fork/branch to clone).

## Combine (v10) + CombineHarvester
```sh
git clone https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit.git HiggsAnalysis/CombinedLimit
cd HiggsAnalysis/CombinedLimit; git checkout v10.0.0; cd -
git clone https://github.com/cms-analysis/CombineHarvester.git CombineHarvester
scram b -j8
```

## Storage
- Work under your CERN **EOS user space** `/eos/user/<l>/<user>/` for outputs.
- The **pre-made 2024 pico n-tuples** and the **2024 TES/TauID templates + scale factors** are provided on
  EOS by the organizers (paths given in [configuration.md](configuration.md)).

Each new login: `cd CMSSW_14_1_0_pre4/src && cmsenv`, and get a grid proxy (see
[configuration.md](configuration.md)).
