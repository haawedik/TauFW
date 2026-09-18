# 5. Normalization, QCD & corrections

Now compare **data** to the **expected** contributions and get the normalization right. Use the exercise
plotter, which reads the pre-made 2024 n-tuples:
```sh
cd $CMSSW_BASE/src/TauFW/Plotter
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau
```
Outputs: control plots in `plots/2024/` (e.g. `m_vis_mutau-signalRegion-2024.pdf`) and histograms in
`hists/2024/mutau.root`. One region is produced: the **opposite-sign signal region** `signalRegion`
(`q_1*q_2<0`, `mt_1<65`). QCD multijet is still estimated data-driven from the same-sign region
internally by the OS/SS method (there is no separate same-sign plot).

## Normalization
MC is scaled to **σ × L / N_eff**. Cross-sections, k-factors and effective event counts for 2024 are
handled for you by the production sample set (`Plotter/config/samples_v15.py`, `setera(2024)` sets the
2024 luminosity and 13.6 TeV). Drell-Yan is split by generator matching of the τ_h candidate:
- `ZTT` — genuine τ_h (`genmatch_2==5`): **the signal**.
- `ZL` — lepton→τ_h fakes (`0<genmatch_2<5`); `ZJ` — jet→τ_h fakes (`genmatch_2==0`).

## Data-driven QCD (OS/SS)
QCD multijet is taken from **data** in the **same-sign** region (`q_1*q_2>0`), after subtracting the
other MC, and extrapolated to the opposite-sign signal region with a transfer factor (`scale`, ≈1.1 in
CMSDAS2020). In the plotter this is `sampleset.getstack(..., method='QCD_OSSS', scale=1.1)`
(`Plotter/python/methods/QCD_OSSS.py`).
> **Task:** re-derive the OS/SS `scale` for 2024 from a QCD-enriched sideband (invert the muon isolation,
> e.g. `0.15 < iso_1 < 0.5`) and update it.

## Corrections (Run 3, correctionlib)
The pre-made n-tuples already carry the standard event weights (pileup, muon ID/iso/trigger,
τ ES/ID) from the **`jsonpog-integration`** POG JSONs applied during pico production. If you reprocess,
these come from `PicoProducer/python/corrections/` (`PileupTool`, `MuonSFs`, tau ES/ID). Check the effect
by comparing data/MC agreement before and after in the control plots.

> **Task:** look at `m_vis`, `pt_1`, `pt_2`, `mt_1`, `met`, `decayMode_2` in both regions. Is data/MC ≈ 1
> in the signal region? Where does QCD dominate?
