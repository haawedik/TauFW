#!/bin/bash
# Source this, do not run it: it sets X509_USER_PROXY to a proxy copy on a globally-visible
# filesystem (AFS or EOS), so renewal/transfer doesn't depend on which lxplus node you happened
# to run voms-proxy-init on (unlike /tmp, which caused "Transfer input files failure" before).
# Usage: source make_proxy.sh [afs|eos]   (no argument: auto-detect from $CMSSW_BASE)
FS="$1"
if [ -z "$FS" ]; then
  case "$CMSSW_BASE" in
    /afs/*) FS=afs ;;
    /eos/*) FS=eos ;;
    *) echo "make_proxy.sh: could not tell AFS from EOS from \$CMSSW_BASE ($CMSSW_BASE)."
       echo "Usage: source make_proxy.sh [afs|eos]"
       return 1 2>/dev/null || exit 1 ;;
  esac
fi
case "$FS" in
  afs) DIR="$HOME/private/.condor_proxy" ;;        # private/ has a restrictive AFS ACL
  eos) DIR=/eos/user/${USER:0:1}/$USER/.condor_proxy ;;
  *)   echo "Usage: source make_proxy.sh [afs|eos]"; return 1 2>/dev/null || exit 1 ;;
esac
mkdir -p "$DIR" && chmod 700 "$DIR"
voms-proxy-init --voms cms --valid 192:00:00 --rfc --out "$DIR/x509up" && chmod 600 "$DIR/x509up"
export X509_USER_PROXY="$DIR/x509up"
echo "X509_USER_PROXY=$X509_USER_PROXY"
