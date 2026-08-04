#!/usr/bin/env python3
"""Build POI-only postfit shape files for the corrTES variant.

The full postfit (PostFitShape_<era>__mutau_<DM>.root, step 2) applies the
fitted POIs AND all nuisance pulls. This script writes a companion
PostFitShape_<era>__mutau_<DM>_poionly.root in which the `<region>_postfit`
directories hold the model evaluated at the FITTED POI values only
(tes_DM<X> + tid_SF_DM<X>_pt<N>) with every nuisance kept at its prefit
value — i.e. what the signal parameters alone do to the templates. The
`<region>_prefit` directories are copied verbatim from the full file, so
`runpostfit.py --variant corr --poi-only` draws the pre vs POI-only-post
comparison with the unchanged plotting code.

POI values come from the step-1 MultiDimFit grid-scan param file
(FitparameterValues_..._<DM>.txt — the numbers shown on the scan plots);
--poi-source fitdiag switches to the FitDiagnostics fit_s values instead.

Needs cmsenv (PostFitShapesFromWorkspace). Run from Fitter/ AFTER step 2:
    python3 make_poionly_postfit.py -j VVTight -e Tight -y 2024
"""
import os
import re
import glob
import argparse


def read_poi_values_fitdiag(fitdiag_path, dm):
    """POI best-fit values from the fit_s RooFitResult (tes_<dm>, tid_SF_<dm>_pt*)."""
    import ROOT
    f = ROOT.TFile.Open(fitdiag_path)
    if not f or f.IsZombie():
        return None
    fr = f.Get("fit_s")
    if not fr:
        f.Close()
        return None
    vals = {}
    pars = fr.floatParsFinal()
    for i in range(pars.getSize()):
        p = pars.at(i)
        name = p.GetName()
        if name == f"tes_{dm}" or name.startswith(f"tid_SF_{dm}_pt"):
            vals[name] = p.getVal()
    f.Close()
    return vals


def read_poi_values_multidimfit(param_path, dm):
    """POI best-fit values from the step-1 MultiDimFit grid-scan param file.

    Keeps only exact POI keys (tes_<dm>, tid_SF_<dm>_pt<N>) — skips the
    _1sigma_low/high entries, nuisance seeds and combine diagnostics.
    """
    vals = {}
    with open(param_path) as f:
        for line in f:
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            key = key.strip()
            if key == f"tes_{dm}" or re.fullmatch(rf"tid_SF_{dm}_pt\d+", key):
                try:
                    vals[key] = float(value.strip())
                except ValueError:
                    pass
    return vals


def copy_dir(src_dir, fout, out_name):
    fout.mkdir(out_name)
    d = fout.Get(out_name)
    d.cd()
    for k in src_dir.GetListOfKeys():
        obj = k.ReadObj()
        obj.Write(k.GetName())


def main():
    ap = argparse.ArgumentParser(description="POI-only postfit shapes (corrTES)")
    ap.add_argument('-j', '--jet', dest='jet_wp', default='VVTight')
    ap.add_argument('-e', '--electron', dest='ele_wp', default='Tight')
    ap.add_argument('-y', '--year', dest='year', default='2024')
    ap.add_argument('--dms', default=None, help="comma-separated DM filter (default: all found)")
    ap.add_argument('--poi-source', dest='poi_source', choices=['multidimfit', 'fitdiag'],
                    default='multidimfit',
                    help="where to take the POI values from: step-1 grid-scan param file "
                         "(default, matches the scan plots) or FitDiagnostics fit_s")
    args = ap.parse_args()

    out_dir = f"output_pt_less_region_corrTES/againstjet_{args.jet_wp}/againstelectron_{args.ele_wp}/{args.year}"
    pf_dir = f"postfit_pt_less_region_corrTES/againstjet_{args.jet_wp}/againstelectron_{args.ele_wp}/{args.year}"
    if not os.path.isdir(out_dir) or not os.path.isdir(pf_dir):
        raise SystemExit(f"missing {out_dir} or {pf_dir} — run steps 1+2 first")

    dms = []
    for ws in sorted(glob.glob(os.path.join(out_dir, "combinecards_DM*_mutau.root"))):
        m = re.search(r"combinecards_(DM\d+)_mutau\.root$", ws)
        if m:
            dms.append(m.group(1))
    if args.dms:
        keep = set(args.dms.split(','))
        dms = [d for d in dms if d in keep]
    print(f"[poionly] DMs: {dms}")

    import ROOT
    ROOT.gROOT.SetBatch(True)

    for dm in dms:
        ws = os.path.join(out_dir, f"combinecards_{dm}_mutau.root")
        full_shapes = os.path.join(pf_dir, f"PostFitShape_{args.year}__mutau_{dm}.root")
        out_path = os.path.join(pf_dir, f"PostFitShape_{args.year}__mutau_{dm}_poionly.root")
        if args.poi_source == 'multidimfit':
            poi_src = os.path.join(out_dir,
                                   f"FitparameterValues__mutau_DeepTau_{args.year}-13TeV_{dm}.txt")
        else:
            poi_src = os.path.join(pf_dir,
                                   f"fitDiagnostics.mt_m_vis-{dm}_mutau_DeepTau-{args.year}-13TeV.root")
        for req in (ws, poi_src, full_shapes):
            if not os.path.isfile(req):
                print(f"[poionly] {dm}: missing {req} — skipped")
                break
        else:
            if args.poi_source == 'multidimfit':
                poi_vals = read_poi_values_multidimfit(poi_src, dm)
            else:
                poi_vals = read_poi_values_fitdiag(poi_src, dm)
            if not poi_vals:
                print(f"[poionly] {dm}: no POI values in {poi_src} — skipped")
                continue
            freeze = ",".join(["r=1"] + [f"{k}={v:.6f}" for k, v in sorted(poi_vals.items())])
            print(f"[poionly] {dm}: freeze {freeze}")

            # nuisances untouched -> stay at prefit zero; only the POIs move
            tmp = os.path.join(pf_dir, f"tmp_poionly_{dm}.root")
            rc = os.system(f"PostFitShapesFromWorkspace --output {tmp} --workspace {ws} --freeze {freeze}")
            if rc != 0 or not os.path.isfile(tmp):
                print(f"[poionly] {dm}: PostFitShapesFromWorkspace FAILED (rc={rc}) — skipped")
                continue

            fin_tmp = ROOT.TFile.Open(tmp)
            fin_full = ROOT.TFile.Open(full_shapes)
            fout = ROOT.TFile(out_path, "RECREATE")
            n = 0
            for k in fin_tmp.GetListOfKeys():
                name = k.GetName()
                if not name.endswith("_prefit"):
                    continue
                region = name[: -len("_prefit")]
                # POI-only evaluation becomes the postfit stack
                copy_dir(fin_tmp.Get(name), fout, f"{region}_postfit")
                # true prefit comes from the full-postfit file
                src = fin_full.Get(name)
                if src:
                    copy_dir(src, fout, name)
                else:
                    print(f"[poionly] {dm}: WARNING no {name} in {full_shapes}; using POI-only shapes as prefit")
                    copy_dir(fin_tmp.Get(name), fout, name)
                n += 1
            fout.Close()
            fin_full.Close()
            fin_tmp.Close()
            os.remove(tmp)
            print(f"[poionly] {dm}: wrote {out_path} ({n} regions)")


if __name__ == '__main__':
    main()
