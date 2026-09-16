# 6. Tagger comparison

The 2024 n-tuples store **three** τ_h identification taggers against jets:
`rawDeepTau2018v2p5VSjet_2`, `rawPNetVSjet_2`, `rawUParTVSjet_2`. Which one best separates **genuine**
τ_h from **jet→τ_h fakes**?

## Metric: efficiency vs fake rate (ROC-like)
- **Signal**: genuine τ_h from `ZTT` (`genmatch_2==5`).
- **Background**: jet→τ_h fakes from `W+jets` (`genmatch_2==0`).

For each tagger, scan a threshold on the raw score and compute:
- genuine-τ_h **efficiency** = (signal above threshold) / (all signal),
- jet→τ_h **fake rate** = (background above threshold) / (all background).

Plotting efficiency vs fake rate gives a ROC-like curve; the tagger whose curve is highest (more
efficiency at the same fake rate) is best.

## Run it
```sh
cd $CMSSW_BASE/src/TauFW/Plotter
./plots_and_histograms_CMSDAS26.py -y 2024 -c mutau --tagger
```
Output: `plots/2024/tagger_ROC_mutau_2024.png` with the three curves, plus an AUC-like number per tagger
printed to the terminal.

> **Tasks:**
> - Which tagger wins overall? Does the ranking change vs τ_h **pt** or **decay mode** (`decayMode_2`)?
>   (Add a pt/DM split to the selection in `plot_tagger_comparison`.)
> - The measurement downstream uses **DeepTau2018v2p5** (the tagger with published Run-3 scale factors).
>   Keep that as the default even if another tagger looks marginally better — SFs are only available for
>   DeepTau.

*(This replaces the CMSDAS2020 "refine selection" step: instead of hand-tuning cuts, you compare taggers
and justify the working point.)*
