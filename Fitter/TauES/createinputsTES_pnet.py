#! /usr/bin/env python
# Author: Izaak Neutelings (August 2020)
# Generalized variant (CMSDAS2026 port): per-leg tagger WP injection for vsjet/vse/vsmu via
#   $VSJET/$VSE/$VSMU placeholders + a config 'workingPoints' block + outbase auto-derived from
#   tagger.id_label (e.g. input_pt_less_region_pnet). Needed for FULL PNet (all three legs on raw
#   scores). The tracked createinputsTES.py (VSjet-only) is left untouched -- this is a parallel variant.
# Description: Create input histograms for datacards
#   ./createinputsTES_pnet.py  -y 2526 -c <config>
import os
import sys
from collections import OrderedDict
sys.path.append("../Plotter/") # for config.samples
# from config.samples import *
from config.samples_v15 import *
from TauFW.Plotter.plot.utils import LOG as PLOG, ensuredir
from TauFW.Fitter.plot.datacard import createinputs, plotinputs
from TauFW.Fitter.plot.rebinning import rebinning
import yaml
import time

#nano doc: https://cms-nanoaod-integration.web.cern.ch/autoDoc/NanoAODv12/2022/2023/doc_DYJetsToLL_M-50_TuneCP5_13p6TeV-madgraphMLM-pythia8_Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2.html

map_wp_to_int = OrderedDict([('againstjet',
				OrderedDict([('VVLoose', 2),
               ('VLoose', 3),
               ('Loose',  4),
					     ('Medium', 5),
					     ('Tight',  6),
					     ('VTight', 7)])),
	                    ('againstelectron',
				OrderedDict([('VVLoose', 2),
                                             ('Tight', 6),
                                             ('Loose', 4 )])),
                            ('againstmuon',
				OrderedDict([('VLoose', 1),
                                             ('Loose',  2),
                                             ('Medium', 3),
                                             ('Tight',  4)]))
                           ])

def main(args):
  start_time = time.time()  # Start timing
  eras      = args.eras
  parallel  = args.parallel
  verbosity = args.verbosity
  setupConfFile = args.config
  DM = args.DM
  inclusive = args.inclusive
  plot      = True
  analysis  = 'ztt'

  print("Using configuration file: %s"%setupConfFile  )
  with open(setupConfFile, 'r') as file:
    setup = yaml.safe_load(file)

    # FIX: Handle missing 'regions' key (e.g. for mumu config)
    if "regions" not in setup:
        # If fitRegions are used in observables, we might need them.
        # For mumu config provided, it uses "baseline".
        print("WARNING: 'regions' key missing in config. Adding default 'baseline' region.")
        setup["regions"] = { 'baseline': {'definition': '1', 'title': 'Baseline'} }

    if DM and 'regions' in setup or inclusive:
       newreg = {}
       for reg in setup['regions']:
          if not inclusive:
             if DM+'_' not in reg: continue
             assert(reg not in newreg)
             newreg[reg] = setup['regions'][reg]
          else:
             if 'pt' in reg: continue
             assert(reg not in newreg)
             newreg[reg] = setup['regions'][reg]
       setup['regions'] = newreg

  # WORKING POINTS: -j/-e/-m on the command line override the config's own 'workingPoints' block
  # (if any), which in turn overrides these legacy hardcoded defaults -- so a config file can now
  # drive the WPs end to end, while Condor WP-scan loops can still override via the CLI flags.
  wp_defaults = setup.get('workingPoints', {}) or {}
  againstjet      = args.againstjet      or wp_defaults.get('vsjet',  'Medium')
  againstelectron = args.againstelectron or wp_defaults.get('vse',    'VVLoose')
  againstmuon     = args.againstmuon     or wp_defaults.get('vsmu',   'Tight')

  # separate tree per tagger (e.g. input_pt_less_region_pnet), so DeepTau/PNet/UParT runs of the
  # same WP names (Tight/VVLoose/...) never collide in the same output directory; -O overrides.
  tagger_label = (setup.get('tagger') or {}).get('id_label')
  outbase   = getattr(args, 'outbase', None) or (f'input_pt_less_region_{tagger_label.lower()}' if tagger_label else 'input_pt_less_region')
  outdir    = ensuredir(f"{outbase}/againstjet_{againstjet}/againstelectron_{againstelectron}")
  plotdir   = ensuredir(outdir,"plots")

  channel  = setup["channel"]
  tag      = "13TeV"
  if "tag" in setup:
    tag += setup["tag"]

  for era in eras:

    ###############
    #   SAMPLES   #
    ###############

    # GET SAMPLESET
    sname     = setup["samples"]["filename"]
    sampleset = getsampleset(channel,era,fname=sname,join=setup["samples"]["join"],split=[],table=False,rmsf=setup["samples"].get("removeSFs",[]),addsf=setup["samples"].get("addSFs",[]))

    # Potentially split up samples in several processes
    if "split" in setup["samples"]:
      for splitSample in setup["samples"]["split"]:
        print("Splitting sample %s into %s"%(splitSample,setup["samples"]["split"][splitSample]))
        sampleset.split(splitSample, setup["samples"]["split"][splitSample])

    # Rename processes according to custom convention
    if "rename" in setup["samples"]:
      for renamedSample in setup["samples"]["rename"]:
        print("Renaming sample %s into %s"%(renamedSample,setup["samples"]["rename"][renamedSample]))
        sampleset.rename(renamedSample,setup["samples"]["rename"][renamedSample])

    # On-the-fly reweighting of specific processes -- do after splitting and renaming!
    if "scaleFactors" in setup:
      for SF in setup["scaleFactors"]:
        SFset = setup["scaleFactors"][SF]
        if not era in SFset["values"]: continue
        print("Reweighting with SF -- %s -- for the following processes: %s"%(SF, SFset["processes"]))
        for proc in SFset["processes"]:
          weight = "( q_1*q_2<0 ? ( "
          for cond in SFset["values"][era]:
            weight += cond+" ? "+str(SFset["values"][era][cond])+" : ("
          weight += "1.0)"
          for i in range(len(SFset["values"][era])-1):
            weight += " )"
          weight +=  ") : 1.0 )"
          print("Applying weight: %s"%weight)
          sampleset.get(proc, unique=True).addextraweight(weight)

    # Name of observed data
    sampleset.datasample.name = setup["samples"]["data"]

    ################################################
    #   APPLY WORKING POINTS TO BASELINE CUTS      #
    ################################################
    # Map string WP to integer and replace in baseline cuts
    # Assumes config has 'idDeepTau2018v2p5VSjet_2>=5' (Medium) and 'idDeepTau2018v2p5VSe_2>=2' (VVLoose)

    if "baselineCuts" in setup:
        # Only apply WP replacement if we are in a channel that likely uses Taus (mutau, etau, etc)
        # or if the cuts are actually present.
        if "tau" in channel or "idDeepTau" in setup["baselineCuts"]:
            tagger = setup.get("tagger") or {}
            # --- Tagger-generic WP selection, independently per discriminant (vsjet/vse/vsmu) ---
            # Each leg uses tagger.<key>.discriminant + tagger.<key>.wps[<WP>] (a raw-score cut,
            # PNet/UParT/etc, injected at its $VSJET/$VSE/$VSMU placeholder, or the default DeepTau
            # term if no placeholder is present) when the config's 'tagger' block has that key;
            # otherwise it falls back to the legacy DeepTau integer-WP replacement. So a config can
            # mix taggers per leg (e.g. PNet for VSjet, DeepTau for VSe/VSmu), or use none at all.
            legs = [
                ('vsjet', 'VSjet', '$VSJET', 'idDeepTau2018v2p5VSjet_2', 5, 'againstjet',      againstjet),
                ('vse',   'VSe',   '$VSE',   'idDeepTau2018v2p5VSe_2',   2, 'againstelectron', againstelectron),
                ('vsmu',  'VSmu',  '$VSMU',  'idDeepTau2018v2p5VSmu_2',  4, 'againstmuon',     againstmuon),
            ]
            summary = []
            for key, label, placeholder, deeptau_branch, default_int, map_key, wp in legs:
                legacy_term = f'{deeptau_branch}>={default_int}'
                leg_cfg = tagger.get(key)
                if leg_cfg:
                    disc = leg_cfg["discriminant"]
                    wps  = leg_cfg["wps"]
                    if wp not in wps:
                        raise KeyError("%s WP %r not in tagger.%s.wps %s" % (label, wp, key, list(wps)))
                    cut = "%s>=%s" % (disc, wps[wp])
                    if placeholder in setup["baselineCuts"]:
                        setup["baselineCuts"] = setup["baselineCuts"].replace(placeholder, cut)
                    elif legacy_term in setup["baselineCuts"]:
                        setup["baselineCuts"] = setup["baselineCuts"].replace(legacy_term, cut)
                    else:
                        print(f"WARNING: no {placeholder} placeholder or default {label} term in baselineCuts to replace!")
                    summary.append(f"{label}({disc}) {wp}>={wps[wp]}")
                else:
                    intval = map_wp_to_int[map_key][wp]
                    new_term = f'{deeptau_branch}>={intval}'
                    if legacy_term in setup["baselineCuts"]:
                        setup["baselineCuts"] = setup["baselineCuts"].replace(legacy_term, new_term)
                    else:
                        print(f"WARNING: Could not find standard {label} cut {legacy_term!r} in baselineCuts to replace!")
                    summary.append(f"{label}(DeepTau) {wp} idx {intval}")
            print("Updating baseline cuts: " + ", ".join(summary))
            print(f"New baselineCuts: {setup['baselineCuts']}")
        else:
            print(f"Channel '{channel}' does not seem to use Tau ID working points. Skipping WP replacement in baseline cuts.")


    ###################
    #   OBSERVABLES   #
    ###################

    # Organize observables and regions
    # Structure: [ (Var_obj, [Sel_obj, Sel_obj, ...]) ]
    obs_region_groups = []

    for obsName in setup["observables"]:
        obs_config = setup["observables"][obsName]
        default_binning = obs_config["binning"]

        # Get target regions for this observable
        target_region_names = obs_config.get("fitRegions", setup.get("regions", {}).keys())
        # Filter to only those present in setup['regions']
        target_region_names = [r for r in target_region_names if r in setup["regions"]]

        # Group regions by binning
        regions_by_binning = {} # Key: tuple(binning), Value: list of region names

        if not target_region_names:
             print(f"WARNING: No target regions found for observable {obsName}")
             print(f"  fitRegions: {obs_config.get('fitRegions')}")
             print(f"  setup['regions'].keys(): {list(setup['regions'].keys())}")

        for regName in target_region_names:
            reg_config = setup["regions"][regName]
            # Check if region has specific binning
            binning = tuple(reg_config.get("binning", default_binning))

            if binning not in regions_by_binning:
                regions_by_binning[binning] = []
            regions_by_binning[binning].append(regName)

        # Create Var and Sel objects for each group
        for binning, regNames in regions_by_binning.items():
            # Create Var object
            obsExpr = obs_config.get('variable', obsName)
            extra = obs_config.get("extra", {}).copy()
            if 'filename' not in extra:
                 extra['filename'] = obsName

            var_obj = Var(obsExpr, binning[0], binning[1], binning[2], **extra)

            # Create Sel objects
            sel_objs = []
            for regName in regNames:
                reg_config = setup["regions"][regName]
                sel_objs.append(
                    Sel(regName, reg_config['title'], setup["baselineCuts"]+" && "+reg_config["definition"])
                )

            obs_region_groups.append((var_obj, sel_objs))


    #######################
    #   DATACARD INPUTS   #
    #######################
    # histogram inputs for the datacards

    # https://twiki.cern.ch/twiki/bin/viewauth/CMS/SMTauTau2016
    chshort = channel.replace('tau','t').replace('mu','m') # abbreviation of channel

    fname   = "%s/%s_%s_tes_$OBS%s.inputs-%s-%s.root"%(outdir,analysis,chshort,DM,era,tag)

    print("Nominal inputs")

    # Helper function to run createinputs for all groups
    def run_createinputs_all(fname_in, sampleset_in, groups_in, **kwargs):
        for var_obj, sel_objs in groups_in:
             createinputs(fname_in, sampleset_in, [var_obj], sel_objs, **kwargs)

    run_createinputs_all(fname, sampleset, obs_region_groups, filter=setup["processes"], dots=True, parallel=parallel)

    if "TESvariations" in setup:
      for var in setup["TESvariations"]["values"]:
        print("Variation: TES = %f"%var)

        newsampleset = sampleset.shift(setup["TESvariations"]["processes"], ("_TES%.3f"%var).replace(".","p"), "_TES%.3f"%var, " %.1d"%((1.-var)*100.)+"% TES", split=True,filter=False,share=True)
        run_createinputs_all(fname, newsampleset, obs_region_groups, filter=setup["TESvariations"]["processes"], dots=True, parallel=parallel)

    if "systematics" in setup:
      for sys in setup["systematics"]:

        sysDef = setup["systematics"][sys]
        if sysDef["effect"] != "shape":
          continue
        print("Systematic: %s"%sys)

        # Iterate through the variations of the systematic
        for iSysVar in range(len(sysDef["variations"])):

          # Extract relevant parameters for modifying the sample
          sampleAppend = sysDef["sampleAppend"][iSysVar] if "sampleAppend" in sysDef else ""
          weightReplaced = [sysDef["nomWeight"],sysDef["altWeights"][iSysVar]] if "altWeights" in sysDef else ["",""]
          # Create a new sample set with systematic variations
          newsampleset_sys = sampleset.shift(sysDef["processes"], sampleAppend, "_"+sysDef["name"]+sysDef["variations"][iSysVar], sysDef["title"], split=True,filter=False,share=True)
          run_createinputs_all(fname, newsampleset_sys, obs_region_groups, filter=sysDef["processes"], replaceweight=weightReplaced, dots=True, parallel=parallel)

          # Check for overlap with TES variations in setup #### HERE these should be removed
          # if "TESvariations" in setup:
          #   overlap_TES_sys = list( set(sysDef["processes"]) & set(setup["TESvariations"]["processes"]) )
          #   # If overlap exists, apply TES variations
          #   if overlap_TES_sys:
          #     for var in setup["TESvariations"]["values"]:
          #       print("Variation: TES = %f"%var)
          #       newsampleset_TESsys = sampleset.shift(overlap_TES_sys, ("_TES%.3f"%var).replace(".","p")+sampleAppend, "_TES%.3f"%var+"_"+sysDef["name"]+sysDef["variations"][iSysVar], " %.1d"%((1.-var)*100.)+"% TES" + sysDef["title"], split=True,filter=False,share=True)
          #       createinputs(fname,newsampleset_TESsys, observables, bins, filter=overlap_TES_sys, replaceweight=weightReplaced, dots=True, parallel=parallel)

      ############
      #   PLOT   #
      ############
      # control plots of the histogram inputs

      if plot:
        pname  = "%s/%s_$OBS_%s-$BIN-%s$TAG%s.png"%(plotdir,analysis,chshort,era,tag)
        text   = "%s: $BIN"%(channel.replace("mu","#mu").replace("tau","#tau_{h}"))
        groups = [ ] #(['^TT','ST'],'Top'),]

        if "mumu" in channel:
            varprocs = OrderedDict([
                       ('Nom',      ['ZL','ZTT', 'ZJ','W','ST','TT','QCD','data_obs'])])
        elif "mutau"in channel:
            varprocs = OrderedDict([
                       ('Nom',      ["ZTT","ZL","ZJ","W","VV","ST","TTT","TTL","TTJ","QCD","data_obs"])])

        # Helper function for plotting per observable
        def run_plotinputs_all(fname_in, varprocs_in, groups_in, **kwargs):
            for var_obj, sel_objs in groups_in:
                plotinputs(fname_in, varprocs_in, [var_obj], sel_objs, **kwargs)

        if obs_region_groups:
            run_plotinputs_all(fname,varprocs,obs_region_groups,text=text,
                       pname=pname,tag=tag,group=groups, parallel=parallel)
            rebinning(fname, obs=obs_region_groups[0][0].filename, tag=tag)
            fname = os.path.join(os.path.dirname(fname), 'rebinning', os.path.basename(fname))
        else:
            print("WARNING: No observable/region groups found. Skipping plotting.")
        plotdir   = ensuredir(plotdir,"rebinning")
        pname  = "%s/%s_$OBS_%s-$BIN-%s$TAG%s.png"%(plotdir,analysis,chshort,era,tag)
        run_plotinputs_all(fname,varprocs,obs_region_groups,text=text,
                   pname=pname,tag=tag,group=groups, parallel=parallel)
        pname  = "%s/%s_$OBS_%s-$BIN-%s$TAG%s_wqcd_subtracted.png"%(plotdir,analysis,chshort,era,tag)
        varprocs = OrderedDict([
                       ('Nom',      ['ZTT', 'data_obs_nonztt_subtratced'])])
        run_plotinputs_all(fname,varprocs,obs_region_groups,text=text,
                   pname=pname,tag=tag,group=groups, parallel=parallel, mean=True)
  end_time = time.time()    # End timing
  elapsed = end_time - start_time
  print(f"\n>>> Done. Total runtime: {elapsed:.2f} seconds.")

if __name__ == "__main__":
  from argparse import ArgumentParser
  description = """Create input histograms for datacards"""
  parser = ArgumentParser(prog="createInputs",description=description,epilog="Good luck!")
  parser.add_argument('-y', '--era',     dest='eras', nargs='*', default=['UL2017'], action='store', help="set era" )
  parser.add_argument('-c', '--config', dest='config', type=str, default='TauES/config/defaultFitSetupTES_mutau.yml', action='store',
                                         help="set config file containing sample & fit setup" )
  parser.add_argument('-s', '--serial',  dest='parallel', action='store_false',
                                         help="run Tree::MultiDraw serial instead of in parallel" )
  parser.add_argument('-v', '--verbose', dest='verbosity', type=int, nargs='?', const=1, default=0, action='store',
                                         help="set verbosity" )
  parser.add_argument('-d', '--decaymode', dest='DM', type=str, default='', help="which decay mode" )
  parser.add_argument('-i', '--inclusive', dest='inclusive', action='store_true', default=False, help="which pt region" )
  parser.add_argument('-j', '--jet', dest='againstjet', default=None, help="against jet cut (default: config's workingPoints.vsjet, else Medium)")
  parser.add_argument('-e', '--electron', dest='againstelectron', default=None, help="against electron cut (default: config's workingPoints.vse, else VVLoose)")
  parser.add_argument('-m', '--muon', dest='againstmuon', default=None, help="against muon cut (default: config's workingPoints.vsmu, else Tight)")
  parser.add_argument('-O', '--outbase', dest='outbase', default=None, help="base dir for input histograms (default: auto, from the config's tagger.id_label, e.g. input_pt_less_region_pnet; else input_pt_less_region)")
  args = parser.parse_args()
  # LOG.verbosity = args.verbosity
  PLOG.verbosity = args.verbosity
  main(args)
  print("\n>>> Done.")
