# 9. The measurement

Fit the workspace with **Combine** to extract the Z→ττ signal strength and cross-section, together with
the τ_h ID/ES parameters.

## Signal strength and TauID SF
```sh
cd $CMSSW_BASE/src/TauFW/Fitter
# r = ZTT normalization = sigma(Z->tautau)/sigma_theory; float it together with the TauID SF:
combine -M MultiDimFit workspace.root --redefineSignalPOIs r,tauh_id \
        --setParameterRanges r=0.8,1.2 -n .r_and_tauID
# diagnostics + correlation between r and the TauID SF / TES:
combine -M FitDiagnostics workspace.root --robustHesse 1 -n .r_vs_tauID
```
Scans and impacts:
```sh
combineTool.py -M Impacts -d workspace.root -m 90 --doInitialFit --robustFit 1
combineTool.py -M Impacts -d workspace.root -m 90 --doFits --robustFit 1
combineTool.py -M Impacts -d workspace.root -m 90 -o impacts.json && plotImpacts.py -i impacts.json -o impacts
```

## Cross-section
The Z→ττ cross-section is `r × σ_theory(Z→ττ)`. Read the best-fit `r` (and its uncertainty) from the
fit, multiply by the theory σ×BR used in the sample normalization, and quote
`σ(Z→ττ) = r × σ_theory` with statistical + systematic uncertainties.

## Z→μμ cross-check (lepton universality)
Measure the **Z→μμ** cross-section from the μμ n-tuples the same way (its own region / card), and
**compare σ(Z→μμ) to σ(Z→ττ)**. Within uncertainties they should be equal (lepton universality):
`σ(Z→ττ) / σ(Z→μμ) ≈ 1`. This is a powerful closure test of the whole chain — efficiencies, TauID/TES
SFs, and the QCD/backgrounds.

> **Tasks:**
> - Quote σ(Z→ττ) with its uncertainty breakdown (stat vs syst; dominant nuisances from the impacts).
> - Report σ(Z→ττ)/σ(Z→μμ) and comment on the agreement.
