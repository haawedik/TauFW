# CMSDAS26: correlated-TES + TauID-SF fit WITHOUT the Z->mumu control region.
# Why no CR: the CMSDAS exercise ALSO measures the Z->tautau cross-section (Fit 2). If the SF fit were
# anchored by the Z->mumu CR, the DY/Z->tautau normalization would be tied to mumu, biasing the
# cross-section and the sigma(Z->tautau)/sigma(Z->mumu) universality test. Without the CR, DY is
# normalized to theory and the TauID SF measures the data/MC efficiency ratio (the standard TauPOG way),
# leaving the Z->tautau normalization free for the independent cross-section fit.
# Sibling of run_workflow_zmm_corrTES.sh (which DOES use the Zmm CR) — mumu steps/args removed.
# One TES POI per DM (correlated across pT) + 3 TauID SF POIs per DM (uncorrelated by pT).

J_VALUES=("Tight")     # VSjet WP (exercise default: one WP; add more to compare)
E_VALUES=("VVLoose")   # VSe WP (mutau convention: VVLoose VSe)

YEAR="2024"
CONFIG_TT="TauES_ID/config/config_coarse_TT.yml"

INPUT_ROOT="input_pt_less_region"
OUTPUT_ROOT="output_pt_less_region_corrTES"
PLOTS_ROOT="plots_pt_less_region_corrTES"

for JET_WP in "${J_VALUES[@]}"; do
  for ELE_WP in "${E_VALUES[@]}"; do
    echo "=========================================="
    echo "=== [corrTES noCR] Jet=$JET_WP, Ele=$ELE_WP ==="
    echo "=========================================="

    BASE_INPUT="${INPUT_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
    BASE_OUTPUT="${OUTPUT_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
    BASE_POSTFIT="${OUTPUT_ROOT/output/postfit}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
    BASE_PLOTS="${PLOTS_ROOT}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"

    echo "=== Step 1: per-DM MultiDimFit (corrTES, NO Zmm CR) ==="
    # NB: no harvestDatacards_zmm.py, and no --mumu_datacard_file -> the fit macro skips the Zmm CR.
    python3 TauES_ID/makecombinedfitTES_SF_corrTES.py -y $YEAR -c $CONFIG_TT -i ${BASE_INPUT}/ \
      --input_file ${BASE_INPUT}/ztt_mt_tes_m_vis.inputs-$YEAR-13TeV_mutau.root \
      -o 3 \
      2>&1 | tee step1_multidimfit_corrTES_noCR_${JET_WP}_${ELE_WP}.log

    echo "=== Step 2: FitDiagnostics + PostFit (corrTES, per-DM, NO Zmm CR) ==="
    python3 TauES_ID/makecombinedfitTES_SF_postfit_corrTES.py -y $YEAR -c $CONFIG_TT \
      --indir ${BASE_OUTPUT}/ -o 3 --jet_wp ${JET_WP} --ele_wp ${ELE_WP} \
      2>&1 | tee step2_postfit_corrTES_noCR_${JET_WP}_${ELE_WP}.log

    echo "=== Step 3: Plots (no CR) ==="
    python3 python/plot/runpostfit.py --variant corr -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -y $YEAR \
      2>&1 | tee step3_plots_corrTES_noCR_${JET_WP}_${ELE_WP}.log
    python3 pre_post_plot_combiner.py --variant corr --scan_dir ${BASE_PLOTS}/$YEAR/ --jet_wp ${JET_WP} --ele_wp ${ELE_WP}
    python3 plot_measurements.py --variant corr --jet_wp ${JET_WP} --ele_wp ${ELE_WP} --year $YEAR

    echo "=== Step 4: Correction file generation (corrTES) ==="
    python3 createroot_TES.py --variant corr -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -f root -y $YEAR
    python3 createroot_TES.py --variant corr -c $CONFIG_TT -j ${JET_WP} -e ${ELE_WP} -f json -y $YEAR

    echo "=== [corrTES noCR] done: Jet=$JET_WP, Ele=$ELE_WP ==="
    echo
  done
done

echo "=== Merging JSON correction files (corrTES) ==="
python3 merge_tau_jsons.py --variant corr --type both -y $YEAR -o tau_sf/TauCorrections_${YEAR}_corrTES_noCR.json

echo "All corrTES (no-CR) workflows completed!"
