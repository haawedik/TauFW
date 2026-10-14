#!/bin/bash
# One HTCondor job per VSjet WP: build the (tagger-independent) Z->mumu CR inputs.
# The mumu config has no tau leg, so its content is WP-independent; it is still written once per WP
# dir so each WP's fit finds its CR file alongside the mutau inputs.
# Usage (via mumu.sub): run_mumu.sh <JET_WP>   -- RELEASE_SRC/FITTER_DIR from the environment.
set -e
JET_WP=$1
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
ELE_WPS="${ELE_WPS:-Tight VVLoose}"   # one mumu CR copy per VSe WP dir (content is VSe-independent)
YEAR="${YEAR:-2526}"
CONFIG_MM="${CONFIG_MM:-TauES/config/FitSetup_mumu.yml}"
OUTBASE="${OUTBASE:-input_pt_less_region_pnet}"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
mkdir -p "${OUTBASE}/rebinning"
for ELE_WP in $ELE_WPS; do
  echo ">>> mumu CR inputs: VSjet=$JET_WP VSe=$ELE_WP"
  python3 TauES/createinputsTES_pnet.py -y "$YEAR" -c "$CONFIG_MM" -j "$JET_WP" -e "$ELE_WP" -O "$OUTBASE"
done
