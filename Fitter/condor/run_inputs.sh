#!/bin/bash
# One HTCondor job per (DM, VSjet WP, VSe WP): build the full-PNet mutau m_vis inputs for that cell.
# Usage (via inputs.sub): run_inputs.sh <DM> <JET_WP> <ELE_WP>   -- RELEASE_SRC/FITTER_DIR from the environment.
# ROOT implicit-MT uses the job's request_cpus cores (16), so the heavy QCD/MultiDraw event loop is threaded.
set -e
DM=$1
JET_WP=$2
ELE_WP=$3
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
YEAR="${YEAR:-2526}"
CONFIG="${CONFIG:-TauES_ID/config/config_coarse_TT_pnet.yml}"
OUTBASE="${OUTBASE:-input_pt_less_region_pnet}"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)      # cmsenv (shared TauFW modules via $CMSSW_BASE/python)
cd "$FITTER_DIR"
mkdir -p "${OUTBASE}/rebinning"
echo ">>> mutau inputs: DM=$DM VSjet=$JET_WP VSe=$ELE_WP"
python3 TauES/createinputsTES_pnet.py -y "$YEAR" -c "$CONFIG" -d "$DM" -j "$JET_WP" -e "$ELE_WP" -O "$OUTBASE"
