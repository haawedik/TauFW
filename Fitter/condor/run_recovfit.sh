#!/bin/bash
# Targeted re-fit of ONLY recovAllDMs with the coarser 11-bin templates. One job per (VSjet WP, VSe WP).
# Runs just makecombinedfit with the recov-only config (scanRegions = recovAllDMs_pt*), so DM0/1/10/11
# fits are left intact. createroot(full config) + run_merge are done afterwards.
# Usage (via recov_fit.sub): run_recovfit.sh <JET_WP> <ELE_WP>   -- RELEASE_SRC/FITTER_DIR from environment.
set -e
JET_WP=$1
ELE_WP=$2
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
export TMPDIR="$(mktemp -d /tmp/pnet.XXXXXX)"; trap 'rm -rf "$TMPDIR"' EXIT
YEAR=2526
CFG=TauES_ID/config/config_coarse_TT_pnet_recovonly.yml

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
BASE_IN=input_pt_less_region_pnet/againstjet_${JET_WP}/againstelectron_${ELE_WP}
BASE_OUT=output_pt_less_region_corrTES_pnet/againstjet_${JET_WP}/againstelectron_${ELE_WP}
python3 TauES_ID/makecombinedfitTES_SF_corrTES.py -y "$YEAR" -c "$CFG" -i ${BASE_IN}/ \
  --input_file ${BASE_IN}/ztt_mt_tes_m_vis.inputs-${YEAR}-13TeV_mutau.root \
  -o 3 --mumu_datacard_file ${BASE_OUT}/${YEAR}/ztt_mm_m_vis-baseline_mumu-${YEAR}-13TeV.txt
