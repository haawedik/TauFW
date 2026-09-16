# 4. Flat n-tuples

Analyses run on small **flat n-tuples** (one TTree with simple per-event branches), not on NanoAOD
directly. The analysis module `CMSDAS26/ModuleMuTau.py` selects μτ_h events and writes such a tree.

## Look at the module
```sh
less $CMSSW_BASE/src/TauFW/PicoProducer/python/analysis/CMSDAS26/ModuleMuTau.py
```
Key ingredients (find them in the code):
- **Trigger**: `HLT_IsoMu24` (the Run-3 single-muon path).
- **Muon**: `mediumId`, `pfRelIso04_all < 0.5`, `|η| < 2.4`, `pt > 26`.
- **Tau**: `DeepTau2018v2p5` VSjet/VSe/VSmu ≥ 1, `pt > 20`, `|η| < 2.3`. *(WP integer conventions differ
  from the old 2017v2p1 tagger!)*
- **Pair**: highest-pt μ × highest-pt τ_h with ΔR > 0.4.
- **Three taggers written for the comparison**: `rawDeepTau2018v2p5VSjet_2`, `rawPNetVSjet_2`,
  `rawUParTVSjet_2` (+ `decayModePNet_2`, `decayModeUParT_2`).
- `TODO section 4/6` blocks: extend the muon/electron veto, jets & b-tag, MET choice, high-level
  variables (m_T, Dζ, ΔR, Z pT, npv, nTrueInt), and tau decay modes.

## Run it on ONE small sample (demo)
```sh
cd $CMSSW_BASE/src/TauFW/PicoProducer
pico.py run -c mutau -y 2024 -s DYto2Tau_Bin-MLL-50to120 -m 2000    # -m: max 2000 events
```
Output: `output/pico_mutau_2024_DYto2Tau_Bin-MLL-50to120.root`. Inspect it:
```sh
root -l output/pico_*.root
root [1] tree->GetEntries()
root [2] tree->Print()                 # see the branches, incl. the three tagger scores
root [3] tree->Draw("m_vis>>h(40,0,200)")
root [4] cutflow->Draw()               # how many events survive each cut
```

## The pre-made n-tuples (used for everything else)
You do **not** reprocess the full sample set. The organizers provide the complete 2024 pico n-tuples
(nominal + TES/fake shifts, all three taggers) at
`/eos/cms/store/group/phys_tau/TauFW/pico2024/TES_variations/2024/{DY,TT,WJ,ST,VV,Data}/`, already pointed
to by `pico.py set picodir ...` in [configuration.md](configuration.md). The plotting in the next steps
reads these directly.

> **Batch processing** (for reference only): `pico.py submit -c mutau -y 2024`, monitor with
> `pico.py status -c mutau -y 2024`, then `pico.py hadd -c mutau -y 2024`.
