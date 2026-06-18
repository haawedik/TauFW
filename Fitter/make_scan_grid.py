#!/usr/bin/env python3
"""Combine 2D-scan PNGs into a grid (rows=DM, cols=pt) per WP combo.

Both variants produce 12 scan_2D_*.png files; only the POI names in the
filename differ. The --variant flag picks the right name pattern.
"""
import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFont

DMS = ["DM0", "DM1", "DM10", "DM11"]
PTS = ["pt1", "pt2", "pt3", "pt4", "pt5"]


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


def build_grid(folder, out_path, title=None, finder=find_scan):
    cells = [[finder(folder, dm, pt) for pt in PTS] for dm in DMS]
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

    grid_w = label_w + len(PTS) * cw + (len(PTS) + 1) * pad
    grid_h = title_h + label_h + len(DMS) * ch + (len(DMS) + 1) * pad

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

    for j, pt in enumerate(PTS):
        x = label_w + pad + j * (cw + pad) + cw // 2
        y = title_h + pad
        bbox = draw.textbbox((0, 0), pt, font=font_small)
        draw.text((x - (bbox[2] - bbox[0]) // 2, y), pt, fill="black", font=font_small)

    for i, dm in enumerate(DMS):
        x = pad
        y = title_h + label_h + pad + i * (ch + pad) + ch // 2
        bbox = draw.textbbox((0, 0), dm, font=font_small)
        draw.text((x, y - (bbox[3] - bbox[1]) // 2), dm, fill="black", font=font_small)

    for i, dm in enumerate(DMS):
        for j, pt in enumerate(PTS):
            path = cells[i][j]
            x = label_w + pad + j * (cw + pad)
            y = title_h + label_h + pad + i * (ch + pad)
            if path:
                img = Image.open(path)
                canvas.paste(img, (x, y))
                img.close()
            else:
                draw.rectangle([x, y, x + cw, y + ch], outline="gray", width=2)
                msg = f"{dm} {pt}\n(missing)"
                draw.text((x + cw // 2 - 60, y + ch // 2 - 20), msg, fill="gray", font=font_small)

    canvas.save(out_path)
    print(f"  wrote {out_path}  ({len(found)}/{len(DMS)*len(PTS)} cells)")
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
    global PTS, DMS  # fullcorr collapses to a single per-DM column; DMS may grow for PNet/UParT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None,
                    help="root dir (defaults depend on --variant)")
    ap.add_argument("--variant", choices=["uncorr", "corr", "fullcorr"], default="uncorr")
    ap.add_argument("--dms", default=",".join(DMS),
                    help="comma-separated DM rows (e.g. DM0,DM1,DM2,DM10,DM11,DMrest for PNet/UParT)")
    args = ap.parse_args()
    DMS = [d for d in args.dms.split(",") if d]

    _suffix = {'corr': '_corrTES', 'fullcorr': '_fullcorr', 'uncorr': ''}[args.variant]
    if args.root is None:
        args.root = f"plots_pt_less_region{_suffix}"

    if not os.path.isdir(args.root):
        sys.exit(f"root not found: {args.root}")

    if args.variant == "corr":
        finder = find_corr_scan
    elif args.variant == "fullcorr":
        finder = find_fullcorr_scan
        # fullcorr: 1 scan per DM, no pT split — collapse to single column
        PTS = ["combined"]
    else:
        finder = find_scan

    n = 0
    for jet_wp, ele_wp, year, folder in walk_wps(args.root):
        title = f"{jet_wp} | {ele_wp} | {year} ({args.variant})"
        out_name = f"grid_{args.variant}_{jet_wp}_{ele_wp}_{year}.png"
        out_path = os.path.join(folder, out_name)
        print(f"[{jet_wp} / {ele_wp} / {year}]")
        if build_grid(folder, out_path, title=title, finder=finder):
            n += 1
    print(f"done: {n} grid(s) written")


if __name__ == "__main__":
    main()
