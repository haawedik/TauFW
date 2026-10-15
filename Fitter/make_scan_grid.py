#!/usr/bin/env python3
"""Combine the per-region 2D-scan PNGs into one grid per WP combo (rows=DM, cols=pT bin).

Each DM's pT columns are AUTO-DISCOVERED from the scan filenames, so a DM with a
different pT split (e.g. recovAllDMs merged into pt1 + pt23) renders correctly instead
of showing empty pt2/pt3 boxes. The --variant flag picks the filename pattern.
"""
import argparse
import os
import re
import sys
import glob
from PIL import Image, ImageDraw, ImageFont

DMS = ["DM0", "DM1", "recovAllDMs", "DM10", "DM11"]
# sort order for discovered pT labels (merged pt23 sits between pt2 and pt3)
PT_ORDER = {"pt1": 1, "pt2": 2, "pt23": 2.5, "pt3": 3}


def discover(folder, dm, variant):
    """Return an ordered list of (pt_label, png_path) for this DM in this folder."""
    d = re.escape(dm)
    if variant == "fullcorr":
        p = os.path.join(folder, f"scan_2D_tes_{dm}_tid_SF_{dm}_mt_{dm}_mutaumultidimfit.png")
        return [("", p)] if os.path.isfile(p) else []
    if variant == "corr":   # tes_<dm> (no pT) + tid_SF_<dm>_<pt>
        pat = f"scan_2D_tes_{dm}_tid_SF_{dm}_*_mt_{dm}_*_mutaumultidimfit.png"
        rx = re.compile(rf"tid_SF_{d}_(.+?)_mt_{d}_")
    else:                   # uncorr: tes_<dm>_<pt> + tid_SF_<dm>_<pt>
        pat = f"scan_2D_tes_{dm}_*_tid_SF_{dm}_*_mt_{dm}_*_mutaumultidimfit.png"
        rx = re.compile(rf"tes_{d}_(.+?)_tid_SF_{d}_")
    out = []
    for p in glob.glob(os.path.join(folder, pat)):
        m = rx.search(os.path.basename(p))
        if m:
            out.append((m.group(1), p))
    if variant == "corr" and not out:   # single inclusive region (no pT split, e.g. recovAllDMs)
        p = os.path.join(folder, f"scan_2D_tes_{dm}_tid_SF_{dm}_mt_{dm}_mutaumultidimfit.png")
        if os.path.isfile(p):
            out.append(("incl", p))
    out.sort(key=lambda x: PT_ORDER.get(x[0], 99))
    return out


def build_grid(folder, out_path, dms, variant, title=None):
    rows = [discover(folder, dm, variant) for dm in dms]
    found = [p for row in rows for (_, p) in row]
    if not found:
        print(f"  no scans found in {folder}, skipping")
        return False
    ncols = max(len(r) for r in rows)

    sample = Image.open(found[0]); cw, ch = sample.size; sample.close()
    label_w, cap_h, title_h, pad = 130, 34, 70 if title else 0, 8
    row_block = cap_h + ch + pad
    grid_w = label_w + ncols * cw + (ncols + 1) * pad
    grid_h = title_h + pad + len(dms) * row_block

    canvas = Image.new("RGB", (grid_w, grid_h), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = font_small = ImageFont.load_default()

    if title:
        draw.text((pad, pad), title, fill="black", font=font)

    for i, dm in enumerate(dms):
        y0 = title_h + pad + i * row_block
        yimg = y0 + cap_h
        # DM label (left gutter, vertical centre of the image)
        bb = draw.textbbox((0, 0), dm, font=font_small)
        draw.text((pad, yimg + ch // 2 - (bb[3] - bb[1]) // 2), dm, fill="black", font=font_small)
        for j, (ptlab, path) in enumerate(rows[i]):
            x = label_w + pad + j * (cw + pad)
            # pT caption above the cell (per cell, since DMs differ)
            tb = draw.textbbox((0, 0), ptlab, font=font_small)
            draw.text((x + cw // 2 - (tb[2] - tb[0]) // 2, y0 + 4), ptlab, fill="black", font=font_small)
            img = Image.open(path); canvas.paste(img, (x, yimg)); img.close()

    canvas.save(out_path)
    print(f"  wrote {out_path}  ({len(found)} scans, {len(dms)}x{ncols})")
    return True


def walk_wps(root):
    for jet_wp in sorted(os.listdir(root)):
        jet_dir = os.path.join(root, jet_wp)
        if not os.path.isdir(jet_dir):
            continue
        for ele_wp in sorted(os.listdir(jet_dir)):
            ele_dir = os.path.join(jet_dir, ele_wp)
            if not os.path.isdir(ele_dir):
                continue
            for year in sorted(os.listdir(ele_dir)):
                year_dir = os.path.join(ele_dir, year)
                if os.path.isdir(year_dir):
                    yield jet_wp, ele_wp, year, year_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="root dir (defaults depend on --variant)")
    ap.add_argument("--variant", choices=["uncorr", "corr", "fullcorr"], default="uncorr")
    ap.add_argument("--dms", default=",".join(DMS), help="comma-separated DM rows")
    args = ap.parse_args()
    dms = [d for d in args.dms.split(",") if d]

    suffix = {'corr': '_corrTES', 'fullcorr': '_fullcorr', 'uncorr': ''}[args.variant]
    if args.root is None:
        args.root = f"plots_pt_less_region{suffix}"
    if not os.path.isdir(args.root):
        sys.exit(f"root not found: {args.root}")

    n = 0
    for jet_wp, ele_wp, year, folder in walk_wps(args.root):
        title = f"{jet_wp} | {ele_wp} | {year} ({args.variant})"
        out_path = os.path.join(folder, f"grid_{args.variant}_{jet_wp}_{ele_wp}_{year}.png")
        print(f"[{jet_wp} / {ele_wp} / {year}]")
        if build_grid(folder, out_path, dms, args.variant, title=title):
            n += 1
    print(f"done: {n} grid(s) written")


if __name__ == "__main__":
    main()
