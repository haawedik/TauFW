#!/usr/bin/env bash
# FULL ParticleNet (VSjet+VSe+VSmu) TES+TauID SF measurement, era 2526, WITH the Z->mumu CR.
# corrTES variant: one TES POI per DM (correlated across pT) + TauID SF POIs per DM/pT.
# Adapted from run_workflow_zmm_pnet.sh (hybrid) -> points at the FULL-PNet config and re-enables
# the Step-1 MultiDimFit (which also enables the CR via --mumu_datacard_file).
#
# Prereq: inputs built by run_inputs_pnet_2526.sh (or the condor inputs/mumu jobs) into
#   input_pt_less_region_pnet/. Needs the external TES_variations/2526->2025 pico symlink.
#
# Env overrides (used by condor fan-out; all optional):
#   J_WP=<WP>       run only this one VSjet WP (default: the full sweep below)
#   PER_WP_ONLY=1   do only the per-WP fit chain, skip the cross-WP post-loop (merge/grids/NLL/tid)
#   MERGE_ONLY=1    skip the per-WP fit chain, do only the cross-WP post-loop
#
# NOTE: the fit scripts embed extratag "_DeepTau" in output filenames (TAG below). Cosmetic --
# outputs live in the separate _pnet trees. createroot_TES.py's correctionlib id label still needs
# de-hardcoding to the tagger (pre-existing caveat, not specific to this driver).

SUFFIX="pnet"
CONFIG_TT="TauES_ID/config/config_coarse_TT_pnet.yml"   # FULL PNet (all three legs)
CONFIG_MM="TauES/config/FitSetup_mumu.yml"              # Z->mumu CR (tagger-independent)

# VSjet WP sweep: condor fans out one WP per job via J_WP; default = full sweep.
if [ -n "$J_WP" ]; then J_VALUES=($J_WP); else J_VALUES=("Loose" "Medium" "Tight" "VTight" "VVTight"); fi
if [ -n "$E_WP" ]; then E_VALUES=($E_WP); else E_VALUES=("Tight" "VVLoose"); fi   # PNet VSe WPs to sweep
YEARS=("2526")
DMS=("DM0" "DM1" "recovAllDMs" "DM10" "DM11")           # 5 PNet DM bins (DM1 = PNet DM 1||2; recov = HPS-invalid)
DMS_CSV=$(IFS=,; echo "${DMS[*]}")                      # for plotters that take --dms
TAG="_DeepTau"                                          # embedded fit tag (see NOTE above)

INPUT_ROOT="input_pt_less_region_${SUFFIX}"             # produced by run_inputs_pnet_2526.sh / condor
OUTPUT_ROOT="output_pt_less_region_corrTES_${SUFFIX}"
PLOTS_ROOT="plots_pt_less_region_corrTES_${SUFFIX}"
PULL_TOOL="${CMSSW_BASE}/src/HiggsAnalysis/CombinedLimit/test/diffNuisances.py"

for YEAR in "${YEARS[@]}"; do

  if [ -z "$MERGE_ONLY" ]; then
  for JET_WP in "${J_VALUES[@]}"; do
    for ELE_WP in "${E_VALUES[@]}"; do
      echo "==============================================================="
      echo "=== [full-PNet] year=${YEAR} VSjet=${JET_WP} VSe=${ELE_WP} (with Zmm CR) ==="
      echo "==============================================================="

      BASE_INPUT="${INPUT_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
      BASE_OUTPUT="${OUTPUT_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
      BASE_POSTFIT="${OUTPUT_ROOT/output/postfit}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
      BASE_PLOTS="${PLOTS_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"

      echo "=== Step 1: Zmm CR datacard + per-DM MultiDimFit (CR enabled via --mumu_datacard_file) ==="
      python3 TauES_ID/harvestDatacards_zmm.py -y $YEAR -c $CONFIG_MM -i ${BASE_INPUT}/ -o ${BASE_OUTPUT}/$YEAR/
      python3 TauES_ID/makecombinedfitTES_SF_corrTES.py -y $YEAR -c $CONFIG_TT -i ${BASE_INPUT}/ \
        --input_file ${BASE_INPUT}/ztt_mt_tes_m_vis.inputs-$YEAR-13TeV_mutau.root \
        -o 3 --mumu_datacard_file ${BASE_OUTPUT}/$YEAR/ztt_mm_m_vis-baseline_mumu-$YEAR-13TeV.txt \
        2>&1 | tee step1_multidimfit_${SUFFIX}_${YEAR}_${JET_WP}_${ELE_WP}.log

      echo "=== Step 2: FitDiagnostics + PostFit (per-DM) ==="
      python3 TauES_ID/makecombinedfitTES_SF_postfit_corrTES.py -y $YEAR -c $CONFIG_TT \
        --indir ${BASE_OUTPUT}/ -o 3 \
        --mumu_input_file ${BASE_OUTPUT}/$YEAR/ztt_mm_m_vis-baseline_mumu-$YEAR-13TeV.txt \
        -cmm $CONFIG_MM --jet_wp ${JET_WP} --ele_wp ${ELE_WP} \
        2>&1 | tee step2_postfit_${SUFFIX}_${YEAR}_${JET_WP}_${ELE_WP}.log

      echo "=== Step 2b: Nuisance pull plots (per DM) ==="
      PULLDIR="${BASE_PLOTS}/${YEAR}/pulls"
      mkdir -p "${PULLDIR}"
      for DM in "${DMS[@]}"; do
        FD="${BASE_POSTFIT}/${YEAR}/fitDiagnostics.mt_m_vis-${DM}_mutau${TAG}-${YEAR}-13TeV.root"
        if [ ! -f "${FD}" ]; then echo "  [pulls] missing ${FD} -- skip ${DM}"; continue; fi
        PULLTXT="${PULLDIR}/pulls_${JET_WP}_${ELE_WP}_${DM}.txt"
        python3 "${PULL_TOOL}" --poi tes_${DM} --vtol=0.1 "${FD}" 2>/dev/null | sed 's/[!,]/ /g' | tail -n +4 > "${PULLTXT}"
        python3 scripts/plot_pulls.py -f "${PULLTXT}" -o "${PULLDIR}/pulls_${JET_WP}_${ELE_WP}_${DM}" -t "${JET_WP}/${ELE_WP} ${DM}"
      done

      echo "=== Step 3: Plots ==="
      python3 python/plot/runpostfit.py --variant corr --tagger ${SUFFIX} -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -y $YEAR --include-cr \
        2>&1 | tee step3_plots_${SUFFIX}_${YEAR}_${JET_WP}_${ELE_WP}.log
      python3 pre_post_plot_combiner.py --variant corr --tagger ${SUFFIX} --scan_dir ${BASE_PLOTS}/$YEAR/ --jet_wp ${JET_WP} --ele_wp ${ELE_WP}
      python3 plot_measurements.py --variant corr --tagger ${SUFFIX} --jet_wp ${JET_WP} --ele_wp ${ELE_WP} --year $YEAR

      echo "=== Step 4: Correction file generation ==="
      python3 createroot_TES.py --variant corr --tagger ${SUFFIX} -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -f root -y $YEAR
      # PYTHONNOUSERSITE=1: use the release correctionlib (cvmfs), not the ABI-broken ~/.local one
      PYTHONNOUSERSITE=1 python3 createroot_TES.py --variant corr --tagger ${SUFFIX} -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -f json -y $YEAR

      echo "=== [full-PNet] done: year=${YEAR} Jet=${JET_WP} Ele=${ELE_WP} ==="
      echo
    done
  done
  fi  # MERGE_ONLY

  if [ -z "$PER_WP_ONLY" ]; then
    echo "=== Scan grids (full-PNet, ${YEAR}) ==="
    python3 make_scan_grid.py --variant corr --root ${PLOTS_ROOT} --dms ${DMS_CSV}
    python3 make_measurements_grid.py

    echo "=== Merging JSON correction files (full-PNet, ${YEAR}) ==="
    PYTHONNOUSERSITE=1 python3 merge_tau_jsons.py --variant corr --type both -y $YEAR -c $CONFIG_TT -o tau_sf/TauCorrections_${YEAR}_corrTES_${SUFFIX}.json

    echo "=== 1D profile NLLs (full-PNet, ${YEAR}) ==="
    python3 plot1D_NLL_profiles.py --variant corr --year $YEAR --dms ${DMS_CSV} --indir ${OUTPUT_ROOT} --outdir ${PLOTS_ROOT}

    echo "=== Building combined TauEnergy_SF + TauID_SF (full-PNet, ${YEAR}) ==="
    PYTHONNOUSERSITE=1 python3 make_tid_2025.py --variant corr -y $YEAR -c $CONFIG_TT \
      || echo "[warn] make_tid_2025 failed (deferred: saveSFs_root_JSON hardcoded for old 4-DM x 4-pt layout) — grids + merged JSON already written"
  fi  # PER_WP_ONLY
done

echo "All full-PNet 2526 (with Zmm CR) workflows completed!"
