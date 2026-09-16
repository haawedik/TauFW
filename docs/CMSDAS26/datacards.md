# 8. Datacards

For the cross-section fit we describe the data with a statistical model built from the `m_vis`
histograms: a **datacard** per category listing the processes, their rates, and the systematic
uncertainties, plus the shape templates.

Unlike CMSDAS2020 (which used an external package), CMSDAS26 uses the **in-repo Fitter** tools with
**CombineHarvester** (Combine v10).

## Build the shapes and cards
```sh
cd $CMSSW_BASE/src/TauFW/Fitter
# m_vis shapes per category from the pre-made 2024 pico (signal region + systematics):
python3 TauES/createinputsTES.py -y 2024 -c TauES_ID/config/config_coarse_TT.yml
# datacards (mutau signal categories, and the Z->mumu region used for the xsec cross-check):
python3 TauES_ID/harvestDatacards_zmm.py -y 2024 -c TauES/config/FitSetup_mumu.yml
```
These call the CombineHarvester Python API
(`AddObservations / AddProcesses / AddSyst / ExtractShapes`) and write one card per category with shapes
`\$BIN/\$PROCESS` and systematics `\$BIN/\$PROCESS_\$SYSTEMATIC`.

## Uncertainty model (inspect a card)
- Processes: `ZTT` (signal), `ZL, ZJ, W, VV, TTT, TTL, TTJ, ST, QCD` (backgrounds).
- `lumi_2024` (lnN), τ_h **energy scale** (shape, `ZTT_TES*`), jet/μ→τ **fake** shapes, and the
  **TauID SF** as a rate parameter on `ZTT`.
- `SetAutoMCStats` for bin-by-bin MC-statistics (Barlow-Beeston lite).

## Make the workspace
```sh
combineTool.py -M T2W -i <datacard-dir>/ -o workspace.root --parallel 4
```

> **Task:** open a datacard and identify the signal, the backgrounds, and each nuisance. Which
> uncertainties are shape vs normalization? Which constrain the τ_h energy scale?
