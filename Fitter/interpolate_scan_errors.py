#!/usr/bin/env python3
"""Replace the grid-quantized 1-sigma edges in the FitparameterValues txt files
with linearly interpolated deltaNLL=0.5 crossings of the MultiDimFit scans.

The corrTES fit step stores 1sigma_low/high as the outermost GRID NODE with
deltaNLL <= 0.5, which underestimates the interval by up to one grid step per
side (0.0015 TES / 0.00875 tid_SF) and collapses to zero width when the
crossing lies before the first node (e.g. eTight DM1 tes up == nom). This
script re-derives the edges from the scan ROOT files already on disk — same
projection logic as the writer (per-column profile envelope; TES = tightest of
the per-pT projections chosen by the writer's node-based width) — and rewrites
ONLY the _1sigma_low/_1sigma_high lines in place (nominals and nuisance seeds
untouched). Original txt kept as <file>.bak_gridsigma (created once, never
overwritten); reruns are deterministic from the same scans.

Run (any env with uproot+numpy, e.g. LCG), after workflow step 1:
  python3 interpolate_scan_errors.py [-y 2024] [-j VVTight] [-e Tight VVLoose]
"""
import argparse
import glob
import os
import re
import shutil

import numpy as np
import uproot

SCAN_RE = re.compile(r"higgsCombine\.mt_m_vis-(DM\d+)_(pt\d+)_mutau_DeepTau-.*\.MultiDimFit\.")


def profile_crossings(x, dnll):
    """(lo, hi, edge_flags): interpolated deltaNLL=0.5 crossings of the
    per-column profile of a 2D grid scan projected on x. Mirrors the writer's
    envelope convention: the outermost column with profile <= 0.5 anchors the
    interpolation to the next column outside."""
    cols = np.unique(x)
    prof = np.array([dnll[x == c].min() for c in cols])
    inside = np.flatnonzero(prof <= 0.5)
    if len(inside) == 0:
        raise ValueError("no scan point inside deltaNLL <= 0.5")
    lo_i, hi_i = inside[0], inside[-1]
    edges = [False, False]
    if lo_i == 0:
        lo = cols[0]
        edges[0] = True
    else:
        f = (0.5 - prof[lo_i]) / (prof[lo_i - 1] - prof[lo_i])
        lo = cols[lo_i] + f * (cols[lo_i - 1] - cols[lo_i])
    if hi_i == len(cols) - 1:
        hi = cols[-1]
        edges[1] = True
    else:
        f = (0.5 - prof[hi_i]) / (prof[hi_i + 1] - prof[hi_i])
        hi = cols[hi_i] + f * (cols[hi_i + 1] - cols[hi_i])
    return float(lo), float(hi), edges


def read_scan(path):
    """Per-scan payload: interpolated tid interval + tes projection with the
    writer's node-based width (used to pick the same 'tightest' scan)."""
    with uproot.open(path) as f:
        arrs = f["limit"].arrays(library="np")
    tes_b = [b for b in arrs if re.fullmatch(r"tes_DM\d+", b)]
    tid_b = [b for b in arrs if re.fullmatch(r"tid_SF_DM\d+_pt\d+", b)]
    if len(tes_b) != 1 or len(tid_b) != 1:
        raise ValueError(f"{path}: cannot identify POI branches ({tes_b}, {tid_b})")
    keep = arrs["deltaNLL"] >= 0
    dnll = arrs["deltaNLL"][keep]
    tes, tid = arrs[tes_b[0]][keep], arrs[tid_b[0]][keep]
    if len(dnll) == 0:
        raise ValueError(f"{path}: no usable scan points")
    in1s = dnll <= 0.5
    if not in1s.any():
        raise ValueError(f"{path}: no point inside deltaNLL <= 0.5")
    return {
        "tes_poi": tes_b[0], "tid_poi": tid_b[0],
        "tid_lo_hi": profile_crossings(tid, dnll),
        "tes_lo_hi": profile_crossings(tes, dnll),
        "tes_node_width": tes[in1s].max() - tes[in1s].min(),
    }


def process_wp(outdir, year):
    scans = sorted(glob.glob(os.path.join(
        outdir, f"higgsCombine.mt_m_vis-DM*_mutau_DeepTau-{year}-13TeV.MultiDimFit.mH90.root")))
    by_dm = {}
    for s in scans:
        m = SCAN_RE.search(os.path.basename(s))
        if m:
            by_dm.setdefault(m.group(1), []).append(s)
    if not by_dm:
        raise SystemExit(f"  ERROR: no MultiDimFit scan files in {outdir}")

    for dm in sorted(by_dm, key=lambda d: int(d[2:])):
        txts = glob.glob(os.path.join(
            outdir, f"FitparameterValues_*_DeepTau_{year}-13TeV_{dm}.txt"))
        if len(txts) != 1:
            print(f"  {dm}: expected one param file, found {txts} -- skipping")
            continue
        txt = txts[0]
        new = {}  # poi -> (lo, hi)
        tes_projs = []  # (node_width, lo, hi, poi) in writer's pt order
        for s in by_dm[dm]:
            try:
                r = read_scan(s)
            except ValueError as e:
                print(f"  {dm}: {e} -- leaving its grid values")
                continue
            lo, hi, edges = r["tid_lo_hi"]
            if any(edges):
                print(f"  WARNING {dm} {r['tid_poi']}: no crossing before the scan "
                      f"edge ({'low' if edges[0] else 'high'} side pinned)")
            new[r["tid_poi"]] = (lo, hi)
            tes_projs.append((r["tes_node_width"],) + r["tes_lo_hi"][:2] + (r["tes_poi"],))
        if tes_projs:
            # same selection as the writer: tightest node-based projection
            w, lo, hi, tes_poi = sorted(tes_projs, key=lambda p: p[0])[0]
            new[tes_poi] = (lo, hi)
        rewrite_txt(txt, new)


def rewrite_txt(path, new):
    with open(path) as f:
        lines = f.readlines()
    noms = {m.group(1): float(m.group(2)) for ln in lines
            if (m := re.match(r"^(\w+?): (-?[\d.]+)\s*$", ln)) and m.group(1) in new}
    changed = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\w+)_1sigma_(low|high): (-?[\d.]+)\s*$", ln)
        if not m or m.group(1) not in new:
            continue
        poi, side, old = m.group(1), m.group(2), float(m.group(3))
        val = new[poi][0 if side == "low" else 1]
        nom = noms.get(poi)
        if nom is not None and ((side == "low" and val > nom) or (side == "high" and val < nom)):
            print(f"  WARNING {os.path.basename(path)} {poi} {side}: interpolated "
                  f"{val:.6f} on the wrong side of nominal {nom:.6f} -- keeping {old:.6f}")
            continue
        lines[i] = f"{poi}_1sigma_{side}: {val:.6f}\n"
        if abs(val - old) > 5e-7:
            changed.append(f"{poi} {side}: {old:.6f} -> {val:.6f}")
    backup = path + ".bak_gridsigma"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    with open(path, "w") as f:
        f.writelines(lines)
    tag = os.path.basename(path)
    if changed:
        print(f"  {tag}:")
        for c in changed:
            print(f"    {c}")
    else:
        print(f"  {tag}: no changes (already interpolated?)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-y", "--year", default="2024")
    ap.add_argument("-j", "--jet-wp", default="VVTight")
    ap.add_argument("-e", "--ele-wps", nargs="+", default=["Tight", "VVLoose"])
    ap.add_argument("-o", "--output-root", default="output_pt_less_region_corrTES")
    args = ap.parse_args()
    for wp in args.ele_wps:
        outdir = (f"{args.output_root}/againstjet_{args.jet_wp}/"
                  f"againstelectron_{wp}/{args.year}")
        print(f"=== {outdir}")
        process_wp(outdir, args.year)


if __name__ == "__main__":
    main()
