#!/bin/bash
# Final cross-WP step: merge all per-WP SF outputs into the combined full-PNet 2526 correction JSON
# (+ scan grids, NLL profiles, combined TauEnergy/TauID SF). Run AFTER all fit jobs finish.
# Usage: bash run_merge.sh   (locally) or submit merge.sub.  RELEASE_SRC/FITTER_DIR from the environment.
set -e
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
MERGE_ONLY=1 bash run_workflow_zmm_corrTES_pnet_2526.sh
