#!/usr/bin/env python3
"""Combine 2D-scan PNGs into a grid (rows=DM, cols=pt) per WP combo.

Rows and columns are DISCOVERED from the scan PNGs present in each folder,
so the grid tracks the region scheme automatically (13 ragged regions since
2026-07-28: DM{0,1,2,10} x pt{1..3} + a single DM11_pt1). Cells absent from
a ragged row (e.g. DM11 pt2/pt3) stay blank; the found/total count printed
per grid flags real gaps. The --variant flag picks the filename pattern.
"""
import argparse
import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

# capture (dm, pt) from each variant's scan png name; [A-Za-z0-9] (not \w)
# so the DM token cannot swallow underscores
SCAN_RE = {
    "uncorr":   re.compile(r"^scan_2D_tes_(DM[A-Za-z0-9]+)_(pt\d+)_tid_SF_.*multidimfit\.png$"),
    "corr":     re.compile(r"^scan_2D_tes_(DM[A-Za-z0-9]+)_tid_SF_DM[A-Za-z0-9]+_(pt\d+)_mt_.*multidimfit\.png$"),
    "fullcorr": re.compile(r"^scan_2D_tes_(DM[A-Za-z0-9]+)_tid_SF_DM[A-Za-z0-9]+_mt_.*multidimfit\.png$"),
}


def _dm_key(dm):
    m = re.search(r"\d+", dm)
    return (0, int(m.group()), dm) if m else (1, 0, dm)  # DM2 < DM10; DMrest last


def _pt_key(pt):
    m = re.search(r"\d+", pt)
    return int(m.group()) if m else 0


def discover(folder, variant):
    """(dms, pts) present in this folder, naturally sorted."""
    rx = SCAN_RE[variant]
    dms, pts = set(), set()
    for fn in os.listdir(folder):
        m = rx.match(fn)
        if not m:
            continue
        dms.add(m.group(1))
        pts.add("combined" if variant == "fullcorr" else m.group(2))
    return sorted(dms, key=_dm_key), sorted(pts, key=_pt_key)


def find_scan(folder, dm, pt):
    """uncorr: tes_<dm>_<pt> + tid_SF_<dm>_<pt>."""
    name = f"scan_2D_tes_{dm}_{pt}_tid_SF_{dm}_{pt}_mt_{dm}_{pt}_mutaumultidimfit.png"
    path = os.path.join(folder, name)
    return path if os.path.isfile(path) else None


def find_corr_scan(folder, dm, pt):
    """corrTES: tes_<dm> (no pT) + tid_SF_<dm>_<pt>."""
    name = f"scan_2D_tes_{dm}_tid_SF_{dm}_{pt}_mt_{dm}_{pt}_mutaumultidimfit.png"
    path = os.path.join(folder, name)
    return path if os.path.isfile(path) else None


def find_fullcorr_scan(folder, dm, pt):
    """fullcorr: 1 scan per DM (no pT in name); tes_<dm> + tid_SF_<dm>.
       The `pt` arg is ignored — returns the per-DM scan."""
    name = f"scan_2D_tes_{dm}_tid_SF_{dm}_mt_{dm}_mutaumultidimfit.png"
    path = os.path.join(folder, name)
    return path if os.path.isfile(path) else None


def build_grid(folder, out_path, title=None, finder=find_scan, variant="uncorr", dms=None):
    disc_dms, pts = discover(folder, variant)
    dms = dms or disc_dms
    if not dms or not pts:
        print(f"  no scans found in {folder}, skipping")
        return False

    cells = [[finder(folder, dm, pt) for pt in pts] for dm in dms]
    found = [p for row in cells for p in row if p]
    if not found:
        print(f"  no scans found in {folder}, skipping")
        return False

    sample = Image.open(found[0])
    cw, ch = sample.size
    sample.close()

    label_w = 90  # left gutter for DM labels
    label_h = 60  # top gutter for pt labels
    title_h = 70 if title else 0
    pad = 8

    grid_w = label_w + len(pts) * cw + (len(pts) + 1) * pad
    grid_h = title_h + label_h + len(dms) * ch + (len(dms) + 1) * pad

    canvas = Image.new("RGB", (grid_w, grid_h), "white")
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
        font_small = font

    if title:
        draw.text((pad, pad), title, fill="black", font=font)

    for j, pt in enumerate(pts):
        x = label_w + pad + j * (cw + pad) + cw // 2
        y = title_h + pad
        bbox = draw.textbbox((0, 0), pt, font=font_small)
        draw.text((x - (bbox[2] - bbox[0]) // 2, y), pt, fill="black", font=font_small)

    for i, dm in enumerate(dms):
        x = pad
        y = title_h + label_h + pad + i * (ch + pad) + ch // 2
        bbox = draw.textbbox((0, 0), dm, font=font_small)
        draw.text((x, y - (bbox[3] - bbox[1]) // 2), dm, fill="black", font=font_small)

    for i, dm in enumerate(dms):
        for j, pt in enumerate(pts):
            path = cells[i][j]
            if not path:
                continue  # ragged scheme (e.g. single DM11 region) — leave blank
            x = label_w + pad + j * (cw + pad)
            y = title_h + label_h + pad + i * (ch + pad)
            img = Image.open(path)
            canvas.paste(img, (x, y))
            img.close()

    canvas.save(out_path)
    print(f"  wrote {out_path}  ({len(found)}/{len(dms)*len(pts)} cells)")
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
                if not os.path.isdir(year_dir):
                    continue
                yield jet_wp, ele_wp, year, year_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="root dir (defaults depend on --variant)")
    ap.add_argument("--variant", choices=["uncorr", "corr", "fullcorr"], default="uncorr")
    ap.add_argument("--dms", default=None,
                    help="comma-separated DM rows to force (default: discovered per folder)")
    args = ap.parse_args()
    dms = [d for d in args.dms.split(",") if d] if args.dms else None

    _suffix = {'corr': '_corrTES', 'fullcorr': '_fullcorr', 'uncorr': ''}[args.variant]
    if args.root is None:
        args.root = f"plots_pt_less_region{_suffix}"

    if not os.path.isdir(args.root):
        sys.exit(f"root not found: {args.root}")

    finder = {"uncorr": find_scan, "corr": find_corr_scan, "fullcorr": find_fullcorr_scan}[args.variant]

    n = 0
    for jet_wp, ele_wp, year, folder in walk_wps(args.root):
        title = f"{jet_wp} | {ele_wp} | {year} ({args.variant})"
        out_name = f"grid_{args.variant}_{jet_wp}_{ele_wp}_{year}.png"
        out_path = os.path.join(folder, out_name)
        print(f"[{jet_wp} / {ele_wp} / {year}]")
        if build_grid(folder, out_path, title=title, finder=finder, variant=args.variant, dms=dms):
            n += 1
    print(f"done: {n} grid(s) written")


if __name__ == "__main__":
    main()
