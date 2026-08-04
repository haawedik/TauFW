from postfit_TES import drawpostfit
import yaml

def main(args):
    configs   = args.configs
    againstjet = args.againstjet
    againstelectron = args.againstelectron

    # Variant-aware paths:
    #   uncorr (default): PostFitShape file per region (e.g. ..._DM0_pt1.root)
    #   corr            : PostFitShape file per DM    (e.g. ..._DM0.root, holds 3 pT channels)
    #   fullcorr        : same per-DM layout as corr, but its own output tree
    _tt = ("_" + args.tagger) if getattr(args, 'tagger', '') else ""  # tagger suffix (pnet/upart)
    if args.variant == 'corr':
        postfit_root = './postfit_pt_less_region_corrTES' + _tt
        outroot      = 'output_plots_corrTES' + _tt
    elif args.variant == 'fullcorr':
        postfit_root = './postfit_pt_less_region_fullcorr' + _tt
        outroot      = 'output_plots_fullcorr' + _tt
    else:
        postfit_root = './postfit_pt_less_region' + _tt
        outroot      = 'output_plots' + _tt
    # POI-only companion files (make_poionly_postfit.py): postfit = fitted POIs
    # with all nuisances at prefit; plots go to a separate output tree
    _poi = '_poionly' if getattr(args, 'poi_only', False) else ''
    outroot += _poi

    for config in configs:
        if not config.endswith(".yml"): # config = channel name
            config = "config/setup_%s.yml"%(config)
        print(">>> Using configuration file: %s"%config)
        with open(config, 'r') as file:
            setup = yaml.safe_load(file)
        tag = setup.get('tag',"")

    for region in setup["regions"]:
        if region == "baseline": continue

        print(">>>   Region: %s"%(region))
        era = "%s" % args.year

        # Map region -> PostFitShape file: corr/fullcorr variants use per-DM file.
        if args.variant in ('corr', 'fullcorr'):
            dm_part = region.split('_')[0]  # e.g. DM0_pt1 -> DM0
            shape_label = dm_part
        else:
            shape_label = region

        fname = '%s/againstjet_%s/againstelectron_%s/%s/PostFitShape_%s__mutau_%s%s.root' % (
                postfit_root, againstjet, againstelectron, era, era, shape_label, _poi)
        procs = setup["processes"]
        text  = setup["regions"][region]["title"]
        print(">>>   Title: %s"%(text))

        drawpostfit(fname, region, procs,
                     outdir='%s/jet_%s_ele_%s/' % (outroot, againstjet, againstelectron),
                     pname='$FIT.png', ratio=True, era=era, text=text)
        if args.include_cr:
            cr_procs = ['ZL', 'ZTT', 'ZJ', 'W','VV','ST', 'TT','QCD','data_obs']
            import ROOT
            froot = ROOT.TFile.Open(fname)
            cr_candidates = [f"{args.cr_name}_{region}", f"{region}_{args.cr_name}", args.cr_name]
            found = False
            for cr_region in cr_candidates:
                if froot and not froot.IsZombie() and froot.Get(f"{cr_region}_postfit"):
                    pname_cr = f"{region}_{cr_region}_$FIT_CR.png"
                    drawpostfit(fname, cr_region, cr_procs,
                                 outdir='%s/jet_%s_ele_%s/' % (outroot, againstjet, againstelectron),
                                 pname=pname_cr, ratio=True, era=era, text="Z#rightarrow#mu#mu CR")
                    found = True
                    break
            if not found:
                drawpostfit(fname, args.cr_name, cr_procs,
                             outdir='%s/jet_%s_ele_%s/' % (outroot, againstjet, againstelectron),
                             pname=f"{region}_{args.cr_name}_$FIT_CR.png", ratio=True, era=era,
                             text="Z#rightarrow#mu#mu CR")
            if froot:
                froot.Close()
if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter
    description = """Simple plotting script for postfit plots"""

    parser = ArgumentParser(prog="plot",description=description,epilog="Good luck!")

    parser.add_argument('-c', '--config', '--channel',
                                         dest='configs', type=str, nargs='+', default=['config/setup_mutau.yml'], action='store',
                                         help="config file(s) containing channel setup for samples and selections, default=%(default)r" )
    parser.add_argument('--include-cr', dest='include_cr', action='store_true', default=False,
                                         help="also draw control-region (Zmm) prefit/postfit plots" )
    parser.add_argument('--cr-name', dest='cr_name', type=str, default='Zmm',
                                         help="control-region directory prefix in ROOT file (default='Zmm')" )
    parser.add_argument('-j', '--jet', dest='againstjet', default='Tight', help="against jet WP")
    parser.add_argument('-e', '--electron', dest='againstelectron', default='Tight', help="against electron WP")
    parser.add_argument('-y', '--year', dest='year', default='2024', help="year for plotting")
    parser.add_argument('--variant', dest='variant', choices=['uncorr','corr','fullcorr'], default='uncorr',
                                         help="fit variant: uncorr (per-region), corr (per-DM TES), fullcorr (per-DM TES+TauID)")
    parser.add_argument('--poi-only', dest='poi_only', action='store_true', default=False,
                                         help="plot the _poionly shape files: postfit = fitted POIs only, nuisances at prefit" )
    parser.add_argument('--tagger', dest='tagger', type=str, default='',
                                         help="tree tagger suffix (e.g. pnet, upart); '' = DeepTau default")

    args = parser.parse_args()
  
    main(args)
    print("\n>>> Done.")