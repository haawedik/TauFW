# 8. Datacards for the cross-section fit

This exercise has **two independent fits**:
- **Fit 1 — TES/TauID scale factors** ([tauid_es.md](tauid_es.md), Tier B): your corrTES workflow, POIs
  `tes_DM*` / `tid_SF_*`. Its datacards are built there.
- **Fit 2 — the Z→ττ cross-section** (this section + [measurement.md](measurement.md)): a *small dedicated*
  datacard with **`r` on the Z signal** as the only POI. The TES/TauID scale factors measured in Fit 1
  are **applied** here (not floated), and only varied within their measured uncertainties.

## Build the cross-section datacards
The dedicated builder `Plotter/make_xsec_fit.py` turns the per-process histograms from the plotter into a
Combine datacard: signal = `ZTT` (mutau) or `DY` (mumu), backgrounds floated within lnN uncertainties,
and — for mutau — `tauID` and `tes` as lnN nuisances on `ZTT` (the measured SF, varied ±1σ).

First make the input histograms **with the measured SFs applied** (Fit-1 result, Tier A):
```sh
cd $CMSSW_BASE/src/TauFW/Plotter
# mutau: inclusive m_vis with the measured TauID SF applied
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau --addsf "getTauIDSF(dm_2,genmatch_2)"
# mumu: m_vis around the Z peak
./plots_and_histograms_CMSDAS26.py -y 2024 -c mumu
```
Then build the datacards:
```sh
./make_xsec_fit.py -c mutau -y 2024                 # inclusive m_vis shape, signal ZTT
./make_xsec_fit.py -c mumu  -y 2024 --onebin        # single-bin counting, signal DY
```
Outputs in `xsec_fit/`: `datacard_mutau.txt` + `shapes_mutau.root`, and `datacard_mumu.txt` +
`shapes_mumu.root`.

## What's in the mutau card (inspect it)
```sh
less xsec_fit/datacard_mutau.txt
```
- **signal** `ZTT` (process id 0 → scaled by the POI `r`); **backgrounds** `ZL, ZJ, WJ, VV, TT, ST, QCD`.
- `lumi_2024` lnN on all MC; per-background `norm_*` lnN (the "float within uncertainties");
  `tauID` and `tes` lnN on `ZTT` (measured SF ± its uncertainty — tune with `--tauid-unc`/`--tes-unc`).
- `* autoMCStats 0` for bin-by-bin MC statistics.

> The μμ card is the same idea in **one bin** (a counting experiment): signal `DY`, backgrounds + lnN,
> no τ_h nuisances.

> ⚠️ **First-run checks:** process names must match the plotter output (`ZTT, ZL, ZJ, WJ, TT, ST, VV, QCD`);
> if the data hist is named `m_vis_data` rather than `m_vis_data_obs`, the builder handles both. Adjust
> `--tauid-unc`/`--tes-unc` to the uncertainties from your Fit-1 result
> (`/eos/user/h/haawedik/2024_SFs/Iteration4_corrTES/tau_sf/`).
