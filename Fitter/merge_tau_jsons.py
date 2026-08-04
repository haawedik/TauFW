#!/usr/bin/env python3
"""
Script to create combined tau correction JSON files with variation parameters and multiple Working Points.
Author: haawedik, NCBJ. Nov. 2025
Usage: python3 merge_tau_jsons.py --type both -o tau_sf/TauCorrections_2024.json

This script merges individual per-WP JSON files into a single correctionlib file.
Input files should be named like: TauES_SF_dm_DeepTau2018v2p5_2024_VSjetMedium_VSeleVVLoose.json
"""

import json
import glob
import os
import re
from argparse import ArgumentParser
import correctionlib.schemav2 as cs


def extract_genmatch_data(data_node):
    """
    Navigate through the nested category structure to extract the genmatch->DM->syst->pT data.
    The input files have structure: wp_VSmu -> wp_VSe -> wp_VSjet -> genmatch -> ...
    We want to extract just the genmatch part onwards.
    """
    # Navigate: wp_VSmu (Tight) -> wp_VSe (e.g. VVLoose) -> wp_VSjet (e.g. Medium) -> genmatch data
    try:
        # Get the first (and only) wp_VSmu item
        vsmu_content = data_node.content[0].value
        # Get the first (and only) wp_VSe item  
        vse_content = vsmu_content.content[0].value
        # Get the first (and only) wp_VSjet item
        vsjet_content = vse_content.content[0].value
        # This should be the genmatch category
        return vsjet_content
    except (KeyError, IndexError, TypeError, AttributeError) as e:
        print(f"  Warning: Could not extract genmatch data: {e}")
        return None


def create_combined_correction(input_dir, output_filename, correction_type="tes", variant="uncorr", label=""):
    """Create a single correction with variation parameter from individual JSON files."""

    print(f"Creating {correction_type.upper()} correction file (variant={variant})...")

    # Create the correction
    combined_corr = create_single_correction(input_dir, correction_type, variant=variant, label=label)
    
    if not combined_corr:
        print(f"ERROR: Could not create {correction_type.upper()} correction!")
        return
    
    # Create correction set
    cset = cs.CorrectionSet(
        schema_version=2,
        description=combined_corr.description,
        corrections=[combined_corr],
    )
    
    # Write file
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w") as fout:
        print(f"\n>>> Writing {correction_type.upper()} correction to {output_filename}!")
        fout.write(cset.json(exclude_unset=True))
    
    print(f">>> Successfully created {correction_type.upper()} correction file")

    # Test the correction
    if not test_correction(output_filename, combined_corr):
        raise SystemExit(1)


def _wp_combos(node, _acc=None):
    """Distinct WP-axis paths ({input: key}) above the genmatch level of the
    correction data tree — i.e. the WP combinations actually in the file."""
    _acc = _acc or {}
    if getattr(node, "nodetype", None) != "category" or node.input == "genmatch":
        return [dict(_acc)]
    combos = []
    for item in node.content:
        combos.extend(_wp_combos(item.value, {**_acc, node.input: item.key}))
    seen, out = set(), []
    for c in combos:
        key = tuple(sorted(c.items()))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def test_correction(filename, combined_corr):
    """Evaluate nom/up/down for every WP combination actually present in the
    file (never hardcoded WPs). Returns True only if all evaluations succeed."""
    print(f"\n>>> Testing correction {combined_corr.name}...")
    try:
        import correctionlib
        cset = correctionlib.CorrectionSet.from_file(filename)
        evaluator = cset[combined_corr.name]

        input_names = [inp.name for inp in combined_corr.inputs]
        print(f"  Inputs: {input_names}")
        combos = _wp_combos(combined_corr.data)
        if not combos:
            print(">>> Correction validation FAILED: no WP combinations found in the data")
            return False

        failed = []
        for combo in combos:
            for dm in (0, 11):  # 11 exercises the single-pT-bin DM
                for var in ("nom", "up", "down"):
                    values = {"genmatch": 5, "DM": dm, "pT": 50.0, "syst": var, **combo}
                    args = []
                    for name in input_names:
                        if name not in values:
                            print(f"  Warning: Unknown input '{name}', using default")
                        args.append(values.get(name, 0))
                    label = ", ".join(f"{k}={v}" for k, v in combo.items()) + f", DM={dm}, {var}"
                    try:
                        result = evaluator.evaluate(*args)
                        print(f"  Test [{label}]: {result:.6f}")
                    except Exception as e:
                        print(f"  Test [{label}] FAILED: {e}")
                        failed.append(label)

        if failed:
            print(f">>> Correction validation FAILED ({len(failed)} evaluation(s), see above)")
            return False
        print(f">>> Correction validation successful!")
        return True

    except Exception as e:
        print(f">>> ERROR testing correction: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_combined_both_corrections(input_dir, output_filename, variant="uncorr", label=""):
    """Create a single file with both TES and TauIdSF corrections."""

    print(f"Creating combined file with both TES and TauIdSF corrections (variant={variant})...")

    # Create TES correction
    print("\n=== Creating TES correction ===")
    tes_corr = create_single_correction(input_dir, "tes", variant=variant, label=label)

    # Create TauIdSF correction
    print("\n=== Creating TauIdSF correction ===")
    id_corr = create_single_correction(input_dir, "id", variant=variant, label=label)
    
    corrections_list = []
    if tes_corr:
        corrections_list.append(tes_corr)
    if id_corr:
        corrections_list.append(id_corr)
        
    if not corrections_list:
        print("ERROR: Could not create any corrections!")
        return
    
    # Create combined correction set with both corrections
    combined_cset = cs.CorrectionSet(
        schema_version=2,
        description="Tau Energy Scale and ID Scale Factor corrections with systematic variations",
        corrections=corrections_list,
    )
    
    # Write file
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    with open(output_filename, "w") as fout:
        print(f"\n>>> Writing combined corrections to {output_filename}!")
        fout.write(combined_cset.json(exclude_unset=True))
    
    print(f">>> Successfully created combined file with {len(corrections_list)} correction(s)")

    # Test each correction (always test all, then fail if any did)
    results = [test_correction(output_filename, corr) for corr in corrections_list]
    if not all(results):
        raise SystemExit(1)


def create_single_correction(input_dir, correction_type, variant="uncorr", label=""):
    """Helper function to create a single correction with all WP combinations merged."""

    # Settings based on type
    variant_suffix = {'corr': '_corrTES', 'fullcorr': '_fullcorr'}.get(variant, '')
    if correction_type == "tes":
        pattern_base = "TauES"
        final_name = "TauES_2024" + variant_suffix
        description = f"Tau Energy Scale corrections with all WP combinations ({variant} variant)"
    else:
        pattern_base = "TauID"
        final_name = "TauIdSF_2024" + variant_suffix
        description = f"Tau ID Scale Factor corrections with all WP combinations ({variant} variant)"

    # Regex to find files and extract WPs from filename
    wp_regex = re.compile(r".*VSjet(?P<jet>[a-zA-Z]+)_VSele(?P<ele>[a-zA-Z]+)\.json$")

    # Find all potential files; filter by variant on the filename.
    # Each variant's per-WP JSONs carry a unique tag; uncorr files have neither.
    search_pattern = os.path.join(input_dir, f"*{pattern_base}*.json")
    all_files = glob.glob(search_pattern)
    if variant == "corr":
        all_files = [f for f in all_files if "_corrTES_" in os.path.basename(f)]
    elif variant == "fullcorr":
        all_files = [f for f in all_files if "_fullcorr_" in os.path.basename(f)]
    else:
        all_files = [f for f in all_files
                     if "_corrTES_" not in os.path.basename(f)
                     and "_fullcorr_" not in os.path.basename(f)]
    # Tagger filter: tau_sf/ is shared, so keep only files for this tagger label
    # (e.g. label="ParticleNet" -> "..._ParticleNet_..."; "" keeps all = DeepTau default).
    if label:
        all_files = [f for f in all_files if f"_{label}_" in os.path.basename(f)]
    all_files.sort()
    
    if not all_files:
        print(f"No JSON files found for {correction_type} with pattern {search_pattern}")
        return None

    # Structure to hold data: wp_map[jet_wp][ele_wp] = genmatch_data
    wp_map = {}
    reference_inputs = None
    
    print(f"Scanning {len(all_files)} files for {correction_type}...")
    
    for fpath in all_files:
        fname = os.path.basename(fpath)
        
        match = wp_regex.match(fname)
        if match:
            jet_wp = match.group('jet')
            ele_wp = match.group('ele')
            
            print(f"  Found WP: VSjet={jet_wp}, VSele={ele_wp} in {fname}")
            
            try:
                with open(fpath, 'r') as f:
                    cset = cs.CorrectionSet.parse_obj(json.load(f))
                
                # Find the main correction
                found_corr = None
                for corr in cset.corrections:
                    if '_up' not in corr.name and '_down' not in corr.name:
                        found_corr = corr
                        break
                
                if found_corr:
                    # Store inputs from the first valid file (they should all be the same)
                    if reference_inputs is None:
                        reference_inputs = found_corr.inputs
                    
                    # Extract the innermost data (genmatch onwards)
                    genmatch_data = extract_genmatch_data(found_corr.data)
                    
                    if genmatch_data:
                        if jet_wp not in wp_map:
                            wp_map[jet_wp] = {}
                        wp_map[jet_wp][ele_wp] = genmatch_data
                        print(f"    Successfully extracted data for VSjet={jet_wp}, VSele={ele_wp}")
                    else:
                        print(f"    Warning: Could not extract genmatch data from {fname}")
                    
            except Exception as e:
                print(f"  Warning: Failed to read {fpath}: {e}")
                import traceback
                traceback.print_exc()

    if not wp_map:
        print("Error: No valid WP files found/parsed.")
        return None

    if reference_inputs is None:
        print("Error: Could not determine inputs from files.")
        return None

    print(f"\nBuilding combined correction with {sum(len(v) for v in wp_map.values())} WP combinations...")
    
    # Build the Category structure
    # Root: wp_VSmu -> wp_VSe -> wp_VSjet -> genmatch -> DM -> syst -> pT
    # Since we only have Tight for VSmu, we'll keep it simple
    
    # Build wp_VSjet categories for each ele_wp
    jet_cat_items = []
    for jet_wp in sorted(wp_map.keys()):
        ele_map = wp_map[jet_wp]
        
        ele_cat_items = []
        for ele_wp in sorted(ele_map.keys()):
            genmatch_data = ele_map[ele_wp]
            ele_cat_items.append(cs.CategoryItem(key=ele_wp, value=genmatch_data))
        
        # Create wp_VSe category
        ele_cat = cs.Category(
            nodetype="category",
            input="wp_VSe",
            content=ele_cat_items
        )
        
        jet_cat_items.append(cs.CategoryItem(key=jet_wp, value=ele_cat))

    # Create wp_VSjet category
    jet_cat = cs.Category(
        nodetype="category",
        input="wp_VSjet",
        content=jet_cat_items
    )
    
    # Wrap in wp_VSmu (assuming Tight is the only value)
    root_data = cs.Category(
        nodetype="category",
        input="wp_VSmu",
        content=[cs.CategoryItem(key="Tight", value=jet_cat)]
    )

    # Build the correction object
    combined_corr = cs.Correction(
        name=final_name,
        version=1,
        description=description,
        inputs=reference_inputs,
        output=cs.Variable(name="sf", type="real", description=f"{pattern_base} scale factor"),
        data=root_data
    )
    
    return combined_corr


def list_corrections_in_file(filename):
    """List all corrections in a JSON file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        print(f"\nCorrections in {os.path.basename(filename)}:")
        if 'corrections' in data:
            for corr in data['corrections']:
                print(f"  - {corr.get('name', 'unnamed')}")
                if 'inputs' in corr:
                    print(f"    Inputs: {[inp['name'] for inp in corr['inputs']]}")
    except Exception as e:
        print(f"ERROR reading {filename}: {e}")

def main():
    description = '''Create combined tau correction JSON files with variation parameters.
    
Examples:
  python3 merge_tau_jsons.py --type both                    # Merge all into one file
  python3 merge_tau_jsons.py --type tes -o tau_sf/TES.json  # Only TES
  python3 merge_tau_jsons.py --list-all                     # List all corrections
'''
    parser = ArgumentParser(prog="merge_tau_jsons", description=description)
    parser.add_argument('-i', '--input-dir', dest='input_dir', type=str, default='tau_sf/', 
                        help="Input directory containing JSON files")
    parser.add_argument('-o', '--output', dest='output_file', type=str, 
                        default='tau_sf/TauCorrections_2024.json',
                        help="Output JSON file")
    parser.add_argument('--type', dest='correction_type', type=str, choices=['tes', 'id', 'both'], 
                        default='both', help="Type of corrections to create: tes, id, or both")
    parser.add_argument('--list', dest='list_file', type=str, default=None,
                        help="List corrections in a specific JSON file")
    parser.add_argument('--list-all', dest='list_all', action='store_true',
                        help="List corrections in all found JSON files")
    parser.add_argument('--variant', dest='variant', choices=['uncorr','corr','fullcorr'], default='uncorr',
                        help="uncorr / corr / fullcorr: filter per-WP input files by variant tag in filename")
    parser.add_argument('-c', '--config', dest='config', type=str, default=None,
                        help="fit config with a 'tagger' block; filters shared tau_sf/ inputs to that tagger (PNet/UParT). DeepTau if omitted.")
    parser.add_argument('--label', dest='label', type=str, default=None,
                        help="explicit tagger label filter (e.g. ParticleNet); overrides --config")

    args = parser.parse_args()

    # Resolve tagger label filter for the shared tau_sf/ dir
    label = args.label or ""
    if not label and args.config:
        import yaml
        with open(args.config) as _f:
            _tagger = (yaml.safe_load(_f).get('tagger') or {})
        _id = _tagger.get('id_label', 'DeepTau2018v2p5VSjet')
        _lab = _id.replace('VSjet', '').rstrip('_')
        label = '' if _lab == 'DeepTau2018v2p5' else _lab  # '' keeps DeepTau default behavior
    if label:
        print(f">>> merge: filtering tau_sf/ inputs to tagger label '{label}'")
    
    if args.list_file:
        list_corrections_in_file(args.list_file)
        return
    
    if args.list_all:
        json_files = glob.glob(os.path.join(args.input_dir, "*.json"))
        for json_file in sorted(json_files):
            list_corrections_in_file(json_file)
        return
    
    # Create corrections based on type
    if args.correction_type == "tes":
        create_combined_correction(args.input_dir, args.output_file, "tes", variant=args.variant, label=label)
    elif args.correction_type == "id":
        create_combined_correction(args.input_dir, args.output_file, "id", variant=args.variant, label=label)
    else:  # both - create single file with both corrections
        create_combined_both_corrections(args.input_dir, args.output_file, variant=args.variant, label=label)


if __name__ == '__main__':
    main()