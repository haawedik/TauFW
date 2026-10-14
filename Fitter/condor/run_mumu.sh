#!/bin/bash
# Build the Z->mumu CR inputs ONCE. The mumu CR is a single 'baseline' region (one bin) with no tau
# leg, so its content is independent of BOTH VSjet and VSe. We build one copy and symlink it into
# every VSjet x VSe dir so each (VSjet,VSe) fit finds its CR file. mumu.sub therefore queues ONE job.
# Usage (via mumu.sub): run_mumu.sh   -- RELEASE_SRC/FITTER_DIR from the environment.
set -e
: "${RELEASE_SRC:?set RELEASE_SRC in the environment (the CMSSW .../src dir)}"
FITTER_DIR="${FITTER_DIR:-$RELEASE_SRC/TauFW-pnet/Fitter}"
YEAR="${YEAR:-2526}"
CONFIG_MM="${CONFIG_MM:-TauES/config/FitSetup_mumu.yml}"
OUTBASE="${OUTBASE:-input_pt_less_region_pnet}"
J_VALUES="${J_VALUES:-Loose Medium Tight VTight VVTight}"
E_VALUES="${E_VALUES:-Tight VVLoose}"
REF_J="${REF_J:-Medium}"; REF_E="${REF_E:-VVLoose}"   # dir that gets the single real build
FNAME="ztt_mm_tes_m_vis.inputs-${YEAR}-13TeV_mumu.root"

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "$RELEASE_SRC" && eval $(scramv1 runtime -sh)
cd "$FITTER_DIR"
mkdir -p "${OUTBASE}/rebinning"
echo ">>> building the mumu CR once (ref ${REF_J}/${REF_E})"
python3 TauES/createinputsTES_pnet.py -y "$YEAR" -c "$CONFIG_MM" -j "$REF_J" -e "$REF_E" -O "$OUTBASE"
REF="$(readlink -f "${OUTBASE}/againstjet_${REF_J}/againstelectron_${REF_E}/${FNAME}")"
[ -f "$REF" ] || { echo "ERROR: mumu CR build failed, ${REF} missing"; exit 1; }
echo ">>> symlinking the single mumu CR into every VSjet x VSe dir"
for J in $J_VALUES; do
  for E in $E_VALUES; do
    d="${OUTBASE}/againstjet_${J}/againstelectron_${E}"
    if [ "$J" = "$REF_J" ] && [ "$E" = "$REF_E" ]; then continue; fi   # ref dir already has the real file
    mkdir -p "$d"
    ln -sf "$REF" "$d/${FNAME}"
  done
done
echo ">>> mumu CR done (1 build, symlinked into all VSjet x VSe dirs)"
