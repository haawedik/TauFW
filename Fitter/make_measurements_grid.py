#!/usr/bin/env python3
"""Combine per-WP TauID and TES measurement PNGs into a grid.

Rows (VSjet WPs) and columns (VSele WPs) are discovered from the
VSjet<X>_VSele<Y> subdirectories present in --dir, so the grid follows
whatever WP combos the workflow actually ran (e.g. only VTight x
{VVLoose,Tight} in the WHAM PNet setup)."""
import os
import re
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

WP_ORDER = {"VVLoose": 0, "VLoose": 1, "Loose": 2, "Medium": 3,
            "Tight": 4, "VTight": 5, "VVTight": 6}
QUANTITIES = ["tauID_measurements", "tes_measurements"]


def discover_wps(measurements_dir):
    """(jet_wps, ele_wps) from the VSjet<X>_VSele<Y> dirs present."""
    jet_wps, ele_wps = set(), set()
    for entry in os.listdir(measurements_dir):
        m = re.match(r"^VSjet([A-Za-z]+)_VSele([A-Za-z]+)$", entry)
        if m and os.path.isdir(os.path.join(measurements_dir, entry)):
            jet_wps.add(m.group(1))
            ele_wps.add(m.group(2))
    key = lambda wp: WP_ORDER.get(wp, 99)
    return sorted(jet_wps, key=key), sorted(ele_wps, key=key)


def build_grid(measurements_dir, quantity, out_path, jet_wps, ele_wps):
    JET_WPS, ELE_WPS = jet_wps, ele_wps
    nrows, ncols = len(JET_WPS), len(ELE_WPS)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
    if nrows == 1: axes = [axes]
    if ncols == 1: axes = [[ax] for ax in axes]

    missing = []
    for i, jet in enumerate(JET_WPS):
        for j, ele in enumerate(ELE_WPS):
            ax = axes[i][j]
            png = os.path.join(measurements_dir, f"VSjet{jet}_VSele{ele}", f"{quantity}.png")
            if os.path.exists(png):
                ax.imshow(mpimg.imread(png))
            else:
                missing.append(png)
                ax.text(0.5, 0.5, "missing", ha="center", va="center", transform=ax.transAxes, color="red")
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values(): spine.set_visible(False)
            if i == 0:
                ax.set_title(f"VSele {ele}", fontsize=20, pad=10)
            if j == 0:
                ax.set_ylabel(f"VSjet {jet}", fontsize=20, labelpad=15, rotation=90)

    title = "TauID SF" if quantity.startswith("tauID") else "TES"
    fig.suptitle(f"{title} measurements per (VSjet, VSele) WP", fontsize=24, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[grid] wrote {out_path}")
    if missing:
        print(f"[grid] WARNING: {len(missing)} missing PNG(s):")
        for m in missing: print(f"   - {m}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Measurements"),
                   help="Path to Fitter/Measurements")
    p.add_argument("--out", default=None, help="Output directory (default: same as --dir)")
    args = p.parse_args()

    if not os.path.isdir(args.dir):
        print(f"ERROR: {args.dir} not found"); sys.exit(1)
    out_dir = args.out or args.dir
    os.makedirs(out_dir, exist_ok=True)

    jet_wps, ele_wps = discover_wps(args.dir)
    if not jet_wps:
        print(f"ERROR: no VSjet*_VSele* dirs in {args.dir}"); sys.exit(1)
    print(f"[grid] WP combos found: VSjet {jet_wps} x VSele {ele_wps}")
    for q in QUANTITIES:
        build_grid(args.dir, q, os.path.join(out_dir, f"grid_{q}.png"), jet_wps, ele_wps)


if __name__ == "__main__":
    main()
