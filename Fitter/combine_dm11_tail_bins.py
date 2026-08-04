#!/usr/bin/env python3
"""Merge the two DM11_pt1 tail bins (130-140 + 140-150) of the WHAM-exported
mutau input files into a single 130-150 bin (11 -> 10 m_vis bins).

The original file is kept next to the new one as <file>.bak_dm11_11bins; the
script refuses to run twice (DM11_pt1 already at 10 bins) so the backup always
holds the untouched 11-bin version. All other TDirectories are copied
unchanged; values AND Sumw2 variances are summed in the merged bin.

Run (any env with uproot+hist, e.g. LCG):
  python3 combine_dm11_tail_bins.py [-y 2024] [-j VVTight] [-e Tight VVLoose]
"""
import argparse
import os
import shutil

import numpy as np
import uproot
import hist

TARGET_EDGES = [40., 50., 60., 70., 80., 90., 100., 110., 120., 130., 150.]
MERGE_DIR = "DM11_pt1"


def rebin_to_edges(h, target):
    src = h.axes[0].edges
    idx = np.array([int(np.abs(src - e).argmin()) for e in target])
    if not np.allclose(src[idx], target) or idx[0] != 0 or idx[-1] != len(src) - 1:
        raise ValueError(f"target edges {target} do not align with source {src}")
    out = hist.Hist(hist.axis.Variable(target), storage=hist.storage.Weight())
    view, ov = h.view(), out.view()
    ov["value"] = np.add.reduceat(view["value"], idx[:-1])
    ov["variance"] = np.add.reduceat(view["variance"], idx[:-1])
    return out


def process_file(path):
    with uproot.open(path) as f:
        dirs = {}
        for key in f.keys(cycle=False):
            if "/" not in key:
                continue
            d, name = key.split("/", 1)
            dirs.setdefault(d, {})[name] = f[key].to_hist()
    if MERGE_DIR not in dirs:
        raise SystemExit(f"  ERROR: no {MERGE_DIR} directory in {path}")
    nbins = len(dirs[MERGE_DIR]["data_obs"].axes[0].edges) - 1
    if nbins == len(TARGET_EDGES) - 1:
        print(f"  {MERGE_DIR} already at {nbins} bins -- skipping (backup untouched)")
        return
    backup = path + ".bak_dm11_11bins"
    if os.path.exists(backup):
        raise SystemExit(f"  ERROR: backup {backup} exists but {MERGE_DIR} has "
                         f"{nbins} bins -- refusing to guess, resolve by hand")
    shutil.copy2(path, backup)
    print(f"  backup -> {backup}")
    dirs[MERGE_DIR] = {n: rebin_to_edges(h, TARGET_EDGES)
                       for n, h in dirs[MERGE_DIR].items()}
    tmp = path + ".tmp"
    with uproot.recreate(tmp) as f:
        for d, by_name in dirs.items():
            for name, h in by_name.items():
                f[f"{d}/{name}"] = h
    os.replace(tmp, path)
    n = len(dirs[MERGE_DIR])
    print(f"  rewrote {path} ({MERGE_DIR}: {n} hists at 10 bins, last = 130-150)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-y", "--year", default="2024")
    ap.add_argument("-j", "--jet-wp", default="VVTight")
    ap.add_argument("-e", "--ele-wps", nargs="+", default=["Tight", "VVLoose"])
    ap.add_argument("-i", "--input-root", default="input_pt_less_region")
    args = ap.parse_args()
    for wp in args.ele_wps:
        path = (f"{args.input_root}/againstjet_{args.jet_wp}/againstelectron_{wp}/"
                f"ztt_mt_tes_m_vis.inputs-{args.year}-13TeV_mutau.root")
        print(f"=== {path}")
        process_file(path)


if __name__ == "__main__":
    main()
