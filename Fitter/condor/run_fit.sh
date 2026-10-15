#!/bin/bash
# One HTCondor job per VSjet WP: run the full-PNet 2526 corrTES fit chain (WITH Zmm CR) for that WP.
# PER_WP_ONLY=1 => only the per-WP chain (harvest CR + MultiDimFit + postfit + createroot); the
# cross-WP merge/grids/NLL/tid is done once afterwards by run_merge.sh (merge.sub).
# Usage (via fit.sub): run_fit.sh <JET_WP>   -- RELEASE_SRC/FITTER_DIR from the environment.
set -e
JET_WP=$1
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
# short unique TMPDIR (see run_inputs.sh): the fit scripts import the same MultiThread.py Manager,
# which clashes on AF_UNIX under condor's long scratch TMPDIR -> "Address already in use".
export TMPDIR="$(mktemp -d /tmp/pnet.XXXXXX)"; trap 'rm -rf "$TMPDIR"' EXIT

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
J_WP="$JET_WP" PER_WP_ONLY=1 bash run_workflow_zmm_corrTES_pnet_2526.sh
