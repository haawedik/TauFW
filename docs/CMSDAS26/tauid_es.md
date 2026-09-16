# 7. TauID + TES scale factors

Simulation does not perfectly reproduce the τ_h **identification efficiency** (TauID) or **energy scale**
(TES). We correct these with **scale factors** measured from Z→ττ data, per τ_h **decay mode** (and pt).
This step has two tiers.

The 2024 measurement (templates + measured SFs) is provided at
`/eos/user/h/haawedik/2024_SFs/Iteration4_corrTES/`.

## Tier A (core) — apply the measured SFs at plot level
No reprocessing: apply the already-measured 2024 SFs as an event weight on MC and see the effect on the
data/MC agreement.
```sh
cd $CMSSW_BASE/src/TauFW/Plotter
# nominal (no extra SF):
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau -t nominal
# with the measured TauID SF applied to genuine taus (Tier A):
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau -t withSF \
    --addsf "getTauIDSF(dm_2,genmatch_2)"
```
`--addsf` multiplies an extra weight into all MC (`getsampleset(addsf=[...])`,
`Plotter/config/samples_v15.py`). Compare `m_vis` **before/after** — the ZTT normalization and shape
should move by the SF. The measured values live in
`.../tau_sf/TauCorrections_2024_corrTES.json`.

**TES** shifts the τ_h 4-momentum (and hence `m_vis`). The pre-made n-tuples contain TES-shifted copies
(`_TES0p950 … _TES1p050`); overlay a shifted ZTT `m_vis` against nominal to see the scale move the Z peak.

> **Task:** by how much does data/MC in the Z peak improve once the TauID SF is applied? Which decay mode
> shifts most under TES?

## Tier B (advanced) — measure the SFs with Combine
Reproduce the SFs from the `m_vis` **templates** with a maximum-likelihood fit. The templates
(`ztt_mt_tes_m_vis.inputs-2024-13TeV_mutau.root`, 12 DM×pt categories, per-process `m_vis`, `ZTT_TES*`
signal shifts, jet/μ→τ fake shape systematics) are in `.../Iteration4_corrTES/input_pt_less_region/`.

The fit floats one **TES** POI per decay mode (correlated across pt) and one **TauID SF** POI per
decay mode × pt bin. Driver and macros (Combine v10 + CombineHarvester):
```sh
cd $CMSSW_BASE/src/TauFW/Fitter
# 1) build the m_vis inputs from the 2024 pico (or reuse the provided templates):
python3 TauES/createinputsTES.py -y 2024 -c TauES_ID/config/config_coarse_TT.yml
# 2) harvest datacards + text2workspace + fit (one WP shown), see the driver for the full grid:
less run_workflow_zmm_corrTES.sh      # YEAR="2024" already set
python3 TauES_ID/makecombinedfitTES_SF_corrTES.py -y 2024 -c TauES_ID/config/config_coarse_TT.yml ...
```
Compare your fitted TES / TauID SFs to the shipped `Iteration4` values in `.../tau_sf/`.

> **Task:** run one working point (e.g. VSjet=Tight, VSe=Tight), extract the per-DM TES and TauID SF, and
> compare to the provided JSON. Do the numbers and uncertainties agree?
