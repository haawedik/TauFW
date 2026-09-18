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
# with the measured TauID SF applied to genuine taus (per DM,pt weight read from the Iteration4 JSON):
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau -t withSF --tauid-sf
```
`--tauid-sf` reads the measured SF JSON directly (no correctionlib needed), builds a per-(DM,pt) weight
applied only to genuine taus (`genmatch_2==5`), and multiplies it into the MC. Compare `m_vis`
**before/after** — the ZTT normalization/shape moves by the SF. Default WPs are VSjet=Tight, VSe=VVLoose
(`--vsjet`/`--vse` to change); values come from `.../tau_sf/TauCorrections_2024_corrTES.json`.
Note: the 2024 pico have `idweight_2 = 1` (the SF is *not* pre-applied), which is exactly why we apply it
here at plot level.

**TES** shifts the τ_h 4-momentum (and hence `m_vis`). The pre-made n-tuples contain TES-shifted copies
(`_TES0p950 … _TES1p050`); overlay a shifted ZTT `m_vis` against nominal to see the scale move the Z peak.

> **Task:** by how much does data/MC in the Z peak improve once the TauID SF is applied? Which decay mode
> shifts most under TES?

## Tier B (advanced) — measure the SFs with Combine
Reproduce the SFs from the `m_vis` **templates** with a maximum-likelihood fit. The templates
(`ztt_mt_tes_m_vis.inputs-2024-13TeV_mutau.root`, 12 DM×pt categories, per-process `m_vis`, `ZTT_TES*`
signal shifts, jet/μ→τ fake shape systematics) are in `.../Iteration4_corrTES/input_pt_less_region/`.

The fit floats one **TES** POI per decay mode (correlated across pt) and one **TauID SF** POI per
decay mode × pt bin, from the μτ `m_vis` shapes.

> **Important — no Z→μμ control region here.** The standard corrTES driver (`run_workflow_zmm_corrTES.sh`)
> anchors the DY normalization with a Z→μμ CR. For CMSDAS26 we must **not** do that: we also measure the
> Z→ττ cross-section (Fit 2), and tying the DY/Z→ττ normalization to μμ would bias the cross-section and
> spoil the σ(Z→ττ)/σ(Z→μμ) universality test. Without the CR, DY is normalized to theory and the TauID SF
> measures the data/MC efficiency ratio (the standard TauPOG way), leaving the Z→ττ normalization free for
> Fit 2. Use the **no-CR** driver:

```sh
cd $CMSSW_BASE/src/TauFW/Fitter
# 1) build the m_vis inputs from the 2024 pico (or reuse the provided templates):
python3 TauES/createinputsTES.py -y 2024 -c TauES_ID/config/config_coarse_TT.yml
# 2) run the correlated-TES + TauID-SF fit WITHOUT the Zmm CR (one WP by default; edit J_/E_VALUES):
bash run_workflow_corrTES_noCR.sh     # YEAR="2024"; no harvestDatacards_zmm, no --mumu_datacard_file
```
Compare your fitted TES / TauID SFs to the shipped `Iteration4` values in `.../tau_sf/`.

> **Task:** run one working point (e.g. VSjet=Tight, VSe=Tight), extract the per-DM TES and TauID SF, and
> compare to the provided JSON. Do the numbers and uncertainties agree?
