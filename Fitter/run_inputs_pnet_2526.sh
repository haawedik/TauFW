#!/usr/bin/env bash
# Input-histogram generation for the FULL ParticleNet VSjet+VSe+VSmu measurement, era 2526,
# with the Z->mumu CR. Sibling of run_inputs_pnet.sh (hybrid) but points at the full-PNet config
# config_coarse_TT_pnet.yml and uses the generalized builder createinputsTES_pnet.py (3-leg WP
# injection). Builds, per VSjet WP: the mutau signal-region inputs AND the (tagger-independent)
# Z->mumu CR inputs, both into input_pt_less_region_pnet/.
#
# Prereq: the 2526 pico dir must expose the 2025 _TES*/_LTF*/_JTF* shifted PNet samples
# (the external TES_variations/2526->2025 symlink under $PICODIR).

CONFIG="TauES_ID/config/config_coarse_TT_pnet.yml"   # full PNet (all 3 legs)
CONFIG_MM="TauES/config/FitSetup_mumu.yml"           # Z->mumu CR (tagger-independent, reused unchanged)
OUTBASE="input_pt_less_region_pnet"

J_VALUES=("Loose" "Medium" "Tight" "VTight" "VVTight")   # PNet VSjet WPs (raw-score) to sweep
E_VALUES=("Tight" "VVLoose")                             # PNet VSe WPs to sweep
YEARS=("2526")

TIMESTAMP=$(date +"%Y%m%d_%H%M")
LOGFILE="run_inputs_pnet_2526_${TIMESTAMP}.log"
echo "Logging to ${LOGFILE}  (config=${CONFIG}, outbase=${OUTBASE})"
echo "Run started at $(date)" | tee -a "$LOGFILE"

for YEAR in "${YEARS[@]}"; do
  for j in "${J_VALUES[@]}"; do
    for e in "${E_VALUES[@]}"; do
      echo "------------------------------------------------------------" | tee -a "$LOGFILE"
      echo "[full-PNet] year=${YEAR}  VSjet=${j}  VSe=${e}"                | tee -a "$LOGFILE"
      echo "------------------------------------------------------------" | tee -a "$LOGFILE"

      # mutau signal region (full-PNet config: $VSJET swept by -j, $VSE/$VSMU fixed from the config)
      python3 TauES/createinputsTES_pnet.py -y ${YEAR} -c ${CONFIG}    -j ${j} -e ${e} -O ${OUTBASE} 2>&1 | tee -a "$LOGFILE"
      STATUS=${PIPESTATUS[0]}
      # Z->mumu CR (no tau leg -> WP replacement auto-skipped; -j/-e only pick the output WP dir)
      python3 TauES/createinputsTES_pnet.py -y ${YEAR} -c ${CONFIG_MM} -j ${j} -e ${e} -O ${OUTBASE}

      if [[ $STATUS -ne 0 ]]; then
        echo "ERROR: full-PNet year=${YEAR} j=${j} e=${e} (exit ${STATUS}) -- skipping" | tee -a "$LOGFILE"
        continue
      fi
      echo "Completed full-PNet year=${YEAR} j=${j} e=${e}" | tee -a "$LOGFILE"
    done
  done
done

echo "Run finished at $(date)" | tee -a "$LOGFILE"
