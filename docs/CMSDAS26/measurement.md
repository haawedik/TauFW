# 9. The measurement (Z→ττ cross-section, Z→μμ cross-check)

Fit 2 extracts the Z→ττ cross-section from the dedicated datacards of [datacards.md](datacards.md). The
single POI is **`r`**, the signal strength on the Z signal: **σ(Z) = r × σ_theory**.

## Z→ττ (mutau, inclusive m_vis)
```sh
cd $CMSSW_BASE/src/TauFW/Plotter/xsec_fit
text2workspace.py datacard_mutau.txt
# best-fit r with its uncertainty:
combine -M MultiDimFit -P r --algo singles -n .xsec_mutau datacard_mutau.root
# full diagnostics (pulls, correlations) + impacts:
combine -M FitDiagnostics --robustHesse 1 -n .xsec_mutau datacard_mutau.root
combineTool.py -M Impacts -d datacard_mutau.root -m 90 --doInitialFit --robustFit 1
combineTool.py -M Impacts -d datacard_mutau.root -m 90 --doFits     --robustFit 1
combineTool.py -M Impacts -d datacard_mutau.root -m 90 -o impacts_mutau.json
plotImpacts.py -i impacts_mutau.json -o impacts_mutau
```
Read the best-fit `r` (± stat ± syst) from the `MultiDimFit`/`FitDiagnostics` output. Then
**σ(Z→ττ) = r × σ_theory(Z→ττ)**, using the DY σ×BR from the sample normalization.

## Z→μμ (one-bin counting)
```sh
text2workspace.py datacard_mumu.txt
combine -M MultiDimFit -P r --algo singles -n .xsec_mumu datacard_mumu.root
```
gives `r` for the Z→μμ signal → **σ(Z→μμ) = r × σ_theory(Z→μμ)**.

## Cross-check: lepton universality
Both fits scale the **same** Z production cross-section (`σ_theory` is the same DY process), so the ratio
is simply
```
σ(Z→ττ) / σ(Z→μμ)  =  r(μτ) / r(μμ)
```
which should be **1 within uncertainties** (lepton universality). This closes the loop: it tests your
τ_h efficiency, the TauID/TES scale factors, and the background model all at once.

> **Tasks:**
> - Quote σ(Z→ττ) with its uncertainty; from the impacts, name the dominant systematic.
> - Report `r(μτ)/r(μμ)` and comment on the agreement with unity.

> ⚠️ **First-run checks:** the POI is `r` (Combine's default signal strength — signal process id 0 in the
> card), *not* `tes`/`tid_SF` (those belong to Fit 1). If `combine` complains about negative QCD bins,
> floor them in the shapes or widen the m_vis range.
