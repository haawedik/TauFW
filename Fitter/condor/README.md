# Condor driver — full-PNet 2526 TES + TauID SF (with Z→µµ CR)

HTCondor fan-out for the full-ParticleNet 2526 measurement. Jobs rely on the shared AFS/EOS
filesystem (`should_transfer_files = NO`); nothing is sandboxed. `RELEASE_SRC` is the CMSSW
`.../src` dir (for `cmsenv`); `FITTER_DIR` is the pnet **worktree's** Fitter (where this code lives).

## Launch sequence (from this `Fitter/condor/` directory)

```sh
source make_proxy.sh                                   # long-lived X509 proxy on AFS/EOS
export RELEASE_SRC=$HOME/CMSSW_14_1_0_pre4/src
export FITTER_DIR=$RELEASE_SRC/TauFW-pnet/Fitter

# 1. build inputs: 25 mutau jobs (DM x VSjet WP, each builds both VSe=Tight,VVLoose)
#    + 1 mumu CR job (built once, symlinked into every VSjet x VSe dir -- VSjet/VSe-independent).
condor_submit inputs.sub
condor_submit mumu.sub
# ...wait for all 26 to finish...

# 2. hadd the per-DM mutau files into one inputs file per WP (local, quick)
bash merge_inputs.sh

# 3. fit: one job per VSjet WP (per-WP chain only: harvest CR + MultiDimFit + postfit + createroot)
condor_submit fit.sub
# ...wait for all 5 to finish...

# 4. final cross-WP merge -> tau_sf/TauCorrections_2526_corrTES_pnet.json (+ grids/NLL/tid)
bash run_merge.sh          # or: condor_submit merge.sub
```

## Notes
- The fit step enables the Z→µµ CR via `--mumu_datacard_file` inside
  `run_workflow_zmm_corrTES_pnet_2526.sh` (re-enabled Step-1 MultiDimFit).
- JSON steps use `PYTHONNOUSERSITE=1` (release correctionlib; the `~/.local` one is ABI-broken).
- Prereq: the 2526 pico dir must expose the 2025 `_TES*/_LTF*/_JTF*` shifted PNet samples
  (the external `TES_variations/2526→2025` symlink under `$PICODIR`).
- Resource defaults: inputs/mumu 4 cpu / 4 GB / longlunch; fit & merge 1 cpu / 4 GB / longlunch.
  No retry/hold logic — resubmit failed jobs by hand (check `logs/`).
