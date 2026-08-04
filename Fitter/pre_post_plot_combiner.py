import os
import argparse
from PIL import Image

def main():
    parser = argparse.ArgumentParser(description="Combine prefit, postfit, and optional scan plots.")
    parser.add_argument('--img_dir', type=str, default=None, help="Directory containing prefit/postfit PNGs (defaults depend on --variant)")
    parser.add_argument('--out_dir', type=str, default=None, help="Output directory (defaults depend on --variant)")
    parser.add_argument('--scan_dir', type=str, default=None, help="Directory containing scan plots (optional)")
    parser.add_argument('--jet_wp', type=str, default="medium", help="Jet working point (not used in this script)")
    parser.add_argument('--ele_wp', type=str, default="tight", help="Electron working point (not used in this script)")
    parser.add_argument('--variant', choices=['uncorr','corr','fullcorr'], default='uncorr',
                        help="uncorr: per-region 2D scan; corr: per-DM TES scan; fullcorr: per-DM TES+TauID scan")
    parser.add_argument('--tagger', type=str, default='',
                        help="tree tagger suffix (e.g. pnet, upart); '' = DeepTau default")
    parser.add_argument('--poi-only', dest='poi_only', action='store_true', default=False,
                        help="combine the POI-only postfit plots (runpostfit --poi-only output tree)")
    args = parser.parse_args()
    # Variant defaults (+ tagger/poionly suffixes so it matches runpostfit's output_plots tree)
    _suffix = {'corr': '_corrTES', 'fullcorr': '_fullcorr', 'uncorr': ''}[args.variant]
    _tt = ("_" + args.tagger) if args.tagger else ""
    _poi = "_poionly" if args.poi_only else ""
    if args.img_dir is None:
        args.img_dir = f"./output_plots{_suffix}{_tt}{_poi}/"
    if args.out_dir is None:
        args.out_dir = f"./combined_pre_post{_suffix}{_tt}{_poi}/"
    
    IMG_DIR = args.img_dir + f"jet_{args.jet_wp}_ele_{args.ele_wp}/"
    OUT_DIR = args.out_dir + f"jet_{args.jet_wp}_ele_{args.ele_wp}/"
    SCAN_DIR = args.scan_dir

    os.makedirs(OUT_DIR, exist_ok=True)

    files = [f for f in os.listdir(IMG_DIR) if f.endswith(".png")]

    # Create dictionaries for fast lookup
    # key includes extension, e.g., "DM0_pt1.png"
    prefit = {f.replace("prefit_", ""): f for f in files if f.startswith("prefit_")}
    postfit = {f.replace("postfit_", ""): f for f in files if f.startswith("postfit_")}

    for key in sorted(prefit.keys()):
        if key in postfit:
            pre_path = os.path.join(IMG_DIR, prefit[key])
            post_path = os.path.join(IMG_DIR, postfit[key])

            pre_img = Image.open(pre_path)
            post_img = Image.open(post_path)
            
            images_to_combine = [pre_img]

            # Check for scan plot if directory is provided
            if SCAN_DIR:
                tag = key.replace(".png", "") # e.g. DM0_pt1
                if args.variant == 'corr':
                    # corrTES: tes_<DM> (no pT suffix) + tid_SF_<region>
                    dm_part = tag.split('_')[0]  # DM0_pt1 -> DM0
                    candidates = [
                        os.path.join(SCAN_DIR,
                            f"scan_2D_tes_{dm_part}_tid_SF_{tag}_mt_{tag}_mutaumultidimfit.png"),
                    ]
                elif args.variant == 'fullcorr':
                    # fullcorr: 1 scan per DM (no pT bin in scan name).
                    # Use the DM-only scan plot for every pT region of that DM.
                    dm_part = tag.split('_')[0]
                    candidates = [
                        os.path.join(SCAN_DIR,
                            f"scan_2D_tes_{dm_part}_tid_SF_{dm_part}_mt_{dm_part}_mutaumultidimfit.png"),
                    ]
                else:
                    # uncorr: 2D scan per (DM, pT) with both POIs region-tagged
                    candidates = [
                        os.path.join(SCAN_DIR,
                            f"scan_2D_tes_{tag}_tid_SF_{tag}_mt_{tag}_mutaumultidimfit.png"),
                    ]
                scan_path = next((p for p in candidates if os.path.exists(p)), None)
                if scan_path:
                    scan_img = Image.open(scan_path)
                    images_to_combine.append(scan_img)
                else:
                    print(f"Warning: Scan plot not found for {tag} (tried: {candidates})")

            images_to_combine.append(post_img)

            # Match heights (resize all to max height among images)
            max_h = max(img.height for img in images_to_combine)
            resized_images = []
            for img in images_to_combine:
                # Resize to max height, keeping original width (as per original script logic)
                resized_images.append(img.resize((img.width, max_h)))

            # Calculate total width
            total_width = sum(img.width for img in resized_images)
            
            # Create combined image
            combined = Image.new("RGB", (total_width, max_h))
            
            current_x = 0
            for img in resized_images:
                combined.paste(img, (current_x, 0))
                current_x += img.width

            # Output name
            out_name = f"pre_scan_post_{key}"
            combined.save(os.path.join(OUT_DIR, out_name))

            print(f"Created {out_name}")

    print("Done!")

if __name__ == "__main__":
    main()
