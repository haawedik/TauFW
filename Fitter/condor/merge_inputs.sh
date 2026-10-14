#!/bin/bash
# After the per-(DM,WP) mutau input jobs (inputs.sub) finish, hadd the per-DM files into the single
# mutau inputs file the fit reads -- one per VSjet WP. The mumu CR file is already whole (built per WP
# by mumu.sub). Run locally from Fitter/condor/:  bash merge_inputs.sh
# RELEASE_SRC/FITTER_DIR from the environment (or the defaults below).
set -e
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
ELE_WP="${ELE_WP:-VVLoose}"
YEAR="${YEAR:-2526}"
OUTBASE="${OUTBASE:-input_pt_less_region_pnet}"
J_VALUES=("Loose" "Medium" "Tight" "VTight" "VVTight")
DMS=("DM0" "DM1" "recovAllDMs" "DM10" "DM11")

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
for JET_WP in "${J_VALUES[@]}"; do
  d="${OUTBASE}/againstjet_${JET_WP}/againstelectron_${ELE_WP}"
  inputs=()
  for DM in "${DMS[@]}"; do
    f="${d}/ztt_mt_tes_m_vis${DM}.inputs-${YEAR}-13TeV_mutau.root"
    if [ -f "$f" ]; then inputs+=("$f"); else echo "WARNING: missing $f"; fi
  done
  if [ ${#inputs[@]} -eq 0 ]; then echo "no per-DM mutau files for ${JET_WP} -- skip"; continue; fi
  echo ">>> hadd ${JET_WP}: ${#inputs[@]} per-DM files -> ztt_mt_tes_m_vis.inputs-${YEAR}-13TeV_mutau.root"
  hadd -f "${d}/ztt_mt_tes_m_vis.inputs-${YEAR}-13TeV_mutau.root" "${inputs[@]}"
done
echo "All WP merges done."
