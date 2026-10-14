#!/bin/bash
# One HTCondor job per (decay mode, VSjet WP): build the full-PNet mutau m_vis inputs for that DM.
# Usage (via inputs.sub): run_inputs.sh <DM> <JET_WP>   -- RELEASE_SRC/FITTER_DIR come from the environment.
set -e
DM=$1
JET_WP=$2
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"   # the pnet worktree's Fitter
ELE_WP="${ELE_WP:-VVLoose}"
YEAR="${YEAR:-2526}"
CONFIG="${CONFIG:-TauES_ID/config/config_coarse_TT_pnet.yml}"
OUTBASE="${OUTBASE:-input_pt_less_region_pnet}"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)      # cmsenv (shared TauFW modules via $CMSSW_BASE/python)
cd "$FITTER_DIR"
mkdir -p "${OUTBASE}/rebinning"
python3 TauES/createinputsTES_pnet.py -y "$YEAR" -c "$CONFIG" -d "$DM" -j "$JET_WP" -e "$ELE_WP" -O "$OUTBASE"
