#! /usr/bin/env python3
# Author: Izaak Neutelings (January 2021)
# Description: Script to play around with format of TauPOG SFs.
# Instructions:
#  ./scripts/tau_tid.py
# Sources:
#   https://github.com/cms-tau-pog/TauIDSFs/blob/master/utils/createSFFiles.py
#   https://github.com/cms-nanoAOD/correctionlib/blob/master/tests/test_core.py
#   https://cms-nanoaod-integration.web.cern.ch/integration/master-106X/mc102X_doc.html#Tau
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TauES', 'correctionlib'))
from utils import *

def syst_sortkey(s):
  """Sort key: 'nom' first, then 'up'/'down' pairs, then everything else."""
  order = {'nom': 0, 'up': 1, 'down': 2}
  return (order.get(s, 99), s)


def maketiddata_ptform(pt,sfnom,sferr=0,syst='nom',newExtrapolation=False,verb=0):
  """Interpolate for second to last bin."""
  # sf = "x<20?0: x<25?1.00: x<30?1.01: x<35?1.02: x<40?1.03: 1.04"
  # sf = "x<20?0: x<25?1.10: x<30?1.11: x<35?1.12: x<40?1.13: x<500?1.14: x<1000?1.04+0.2*x/500.: 1.44"
  # sf = "x<20?0: x<25?0.90: x<30?0.91: x<35?0.92: x<40?0.93: x<500?0.94: x<1000?1.04-0.2*x/500.: 0.64"
  # f = TFormula('f',sf)
  # for x in [10,20,29,30,31,35,45,100,200,499,500,501,750,999,1000,1001,1500,2000]: x, f.Eval(x)
  #print(sfs,pt,syst)
  if syst=='nom' or sferr==0:
    sf = sfnom
  else:
    if newExtrapolation:
      if isinstance(sferr,str):
        sf = {
          'nodetype': 'formula', # pT-dependent
          'expression': sferr,
          'parser': "TFormula",
          'variables': ["pt"],
        }
      else: sf = sfnom-sferr if 'down' in syst else sfnom+sferr
    else:
      if pt<500: # pt < 500
        sf = sfnom-sferr if 'down' in syst else sfnom+sferr
      elif 500<=pt<1000: # 500 < pt < 1000
        sf = "%.6g-%.6g*x"%(sfnom,sferr/500.) if 'down' in syst else "%.6g+%.6g*x"%(sfnom,sferr/500.)
        sf = { # linearly inflate uncertainty x2
          'nodetype': 'formula', # pT-dependent
          'expression': sf,
          'parser': "TFormula",
          'variables': ["pt"],
        }
      else: # pt > 1000
        sf = sfnom-2*sferr if 'down' in syst else sfnom+2*sferr # inflate uncertainty x2
  if verb>=2:
    sfstr = ("'"+sf['expression']+"'") if isinstance(sf,dict) else str(sf)
    print(f">>> maketiddata_ptform({pt},{sfnom},{sferr},{syst}) = "+sfstr)
  return sf
  

def maketiddata_ptbin_syst(sfs,pt,newExtrapolation=False,verb=0):
  """Make systematic bins of pt-dependent tau ID SFs."""
  if isinstance(sfs,dict):
    tiddata_syst = [ ]
    for syst in sorted(sfs.keys(),key=syst_sortkey):
      sferr = 0.0 if syst=='nom' else sfs[syst]
      if syst=='nom': continue # we don't add nominal value anymore since we have a default value specified instead
      tiddata_syst.append(
        { 'key': syst, 'value': maketiddata_ptform(pt,sfs['nom'],sferr,syst,newExtrapolation,verb=verb) }
      )
  else:
    assert len(sfs)==3, "SF must be of form (sfnom,errup,errdown)"
    tiddata_syst = [
      #{ 'key': 'nom',  'value': maketiddata_ptform(pt,sfs[0],0.0,   'nom', newExtrapolation, verb=verb) },
      { 'key': 'up',   'value': maketiddata_ptform(pt,sfs[0],sfs[1],'up', newExtrapolation, verb=verb) },
      { 'key': 'down', 'value': maketiddata_ptform(pt,sfs[0],sfs[2],'down', newExtrapolation, verb=verb) },
    ]
  return tiddata_syst
  

def maketiddata_ptbin(sfs,ptbins,newExtrapolation=False,verb=0):
  """Make pt bins of tau ID SFs."""
  tiddata_ptbins = {
    'nodetype': 'binning', # binning:pt
    'input': "pt",
    'edges': ptbins,
    'flow': "clamp",
    'content': [ # bin:pt
      { 'nodetype': 'category', # category:syst
        'input': "syst",
        'default': maketiddata_ptform(pt,sf['nom'],0.0,'nom',newExtrapolation,verb=verb) if isinstance(sf,dict) else maketiddata_ptform(pt,sf[0],0.0,   'nom', newExtrapolation, verb=verb),
        'content': maketiddata_ptbin_syst(sf,pt,newExtrapolation,verb=verb)
      } for pt, sf in zip(ptbins,sfs) # loop over pT bins
    ] # bin:pt
  } # binning:pt
  return tiddata_ptbins
  

def maketiddata_pt(sfs,ptbins,newExtrapolation=False,verb=0):
  """Construct data block for pt-dependent tau ID SFs."""
 
  # PREPARE DATA BLOCK per WP
  tiddata_wps = [ ]
  wps = list(sfs.keys()) # VSjet WPs
  wps.sort(key=wp_sortkey) # sort from loosest to tightest
  for wp in wps:
    # category:wp -> category:wp_VSe -> category:syst -> formula:sf(pt)
    if isinstance(sfs[wp],dict):
      assert all(len(sfs[wp][wpe])==len(ptbins)-1 for wpe in sfs[wp]), f"Number of SFs ({sfs[wp]}) does not match ({len(ptbins)-1})!"
      wps_VSe = list(sfs[wp].keys()) # VSe WPs
      wps_VSe.sort(key=wp_sortkey) # sort from loosest to tightest
      tiddata_wps.append( # key:wp
        { 'key': wp,
          'value': {
            'nodetype': 'category', # category:wp_VSe
            'input': "wp_VSe",
            #'default': 1.0, # no default => throw error if unrecognized WP
            'content': [ # key:wp_VSe
              { 'key': wp_VSe,
                'value': maketiddata_ptbin(sfs[wp][wp_VSe],ptbins,newExtrapolation,verb=verb)
              } for wp_VSe in wps_VSe
            ] # key:wp_VSe
          } # category:wp_VSe
        } # key:wp
      )
    # category:wp -> category:syst -> formula:sf(pt)
    else:
      assert len(sfs[wp])==len(ptbins)-1, f"Number of SFs ({len(sfs[wp])}) does not match ({len(ptbins)-1})!"
      tiddata_wps.append( # key:wp
        { 'key': wp,
          'value': maketiddata_ptbin(sfs[wp],ptbins,newExtrapolation,verb=verb)
        } # key:wp
      )
  
  # FULL DATA BLOCK for pt-dependent SFs
  # category:genmatch -> category:wp (-> category:wp_VSe) -> category:syst -> formula:sf(pt)
  tiddata = schema.Category.parse_obj({
    'nodetype': 'category', # category:genmatch
    'input': "genmatch",
    #'default': 1.0, # no default: throw error if unrecognized genmatch
    'content': [
      { 'key': 0, 'value': 1.0 }, # j  -> tau_h fake
      { 'key': 1, 'value': 1.0 }, # e  -> tau_h fake
      { 'key': 2, 'value': 1.0 }, # mu -> tau_h fake
      { 'key': 3, 'value': 1.0 }, # e  -> tau_h fake
      { 'key': 4, 'value': 1.0 }, # mu -> tau_h fake
      { 'key': 5,  # real tau_h
        'value': {
          'nodetype': 'category', # category:wp
          'input': "wp",
          #'default': 1.0, # no default => throw error if unrecognized WP
          'content': tiddata_wps # key:wp
        } # category:wp
      },
      { 'key': 6, 'value': 1.0 }, # j  -> tau_h fake
    ]
  }) # category:genmatch
  
  return tiddata

#def maketiddata_dmbin_syst(sfs):
#  """Make systematic bins of DM-dependent tau ID SFs."""
#  
#  if isinstance(sfs,dict):
#    tiddata_syst = [ ]
#    for syst in sorted(sfs.keys(),key=syst_sortkey):
#      lsyst = syst.lower()
#      #assert 'up' in lsyst and 'down' in lsyst # avoid confusion
#      # if systematic is defined as a string then we assume it is a function and we add it as a TFormula
#      # else we add it as a binned value
#      if syst in ['nom']: continue # we don't add nominal value anymore since we have a default value specified instead
#      if syst in ["statandsyst_up", "statandsyst_down"]:
#        if "up" in syst:
#          tiddata_syst.append( { 'key': "up", 'value': { 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
#        else:
#          tiddata_syst.append( { 'key': "down", 'value': { 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
#        continue
#      if isinstance(sfs[syst],str):
#        tiddata_syst.append({ 'key':syst, 'value':{ 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
#      else:
#        sferr = -sfs[syst] if 'down' in lsyst else sfs[syst] if 'up' in lsyst else 0.0
#        tiddata_syst.append(
#          { 'key': syst, 'value': sfs['nom']+sferr }
#        )
#  else:
#    assert len(sfs)==3, "SF must be of form (sfnom,errup,errdown)"
#    tiddata_syst = [
#      #{ 'key': 'nom',  'value': sfs[0] },
#      { 'key': 'up',   'value': sfs[0]+sfs[1] },
#      { 'key': 'down', 'value': sfs[0]-sfs[2] },
#    ]
#  return tiddata_syst


def maketiddata_dmbin_syst(sfs, dm, ibin):
  """Make systematic bins of DM-dependent tau ID SFs."""
  #from IPython import embed; embed()
  if isinstance(sfs,dict):
    tiddata_syst = [ ]
    for syst in sorted(sfs.keys(),key=syst_sortkey):
      lsyst = syst.lower()
      #assert 'up' in lsyst and 'down' in lsyst # avoid confusion
      # if systematic is defined as a string then we assume it is a function and we add it as a TFormula
      # else we add it as a binned value
      if syst in ['nom']: continue # we don't add nominal value anymore since we have a default value specified instead
      if syst in ["statandsyst_up", "statandsyst_down"]:
        if "up" in syst:
          tiddata_syst.append( { 'key': "up", 'value': { 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
        else:
          tiddata_syst.append( { 'key': "down", 'value': { 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
        continue
      if isinstance(sfs[syst],str):
        tiddata_syst.append({ 'key':syst, 'value':{ 'nodetype': 'formula', 'expression': sfs[syst], 'parser': "TFormula", 'variables': ["pt"] } })
      else:
        sferr = -sfs[syst] if 'down' in lsyst else sfs[syst] if 'up' in lsyst else 0.0
        tiddata_syst.append(
          { 'key': syst, 'value': sfs['nom']+sferr }
        )
  else:
    assert len(sfs)==3, "SF must be of form (sfnom,errup,errdown)"
    tiddata_syst = [
      { 'key': 'nom',               'value': sfs[0] },
      { 'key': 'up',                'value': sfs[0]+sfs[1] },
      { 'key': 'down',              'value': sfs[0]-sfs[2] },
      { 'key': 'DM0_pt_bin1_up',   'value': sfs[0]+sfs[1] if ((dm == 0) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM0_pt_bin1_down', 'value': sfs[0]-sfs[2] if ((dm == 0) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM0_pt_bin2_up',   'value': sfs[0]+sfs[1] if ((dm == 0) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM0_pt_bin2_down', 'value': sfs[0]-sfs[2] if ((dm == 0) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM0_pt_bin3_up',   'value': sfs[0]+sfs[1] if ((dm == 0) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM0_pt_bin3_down', 'value': sfs[0]-sfs[2] if ((dm == 0) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM1_pt_bin1_up',   'value': sfs[0]+sfs[1] if ((dm == 1) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM1_pt_bin1_down', 'value': sfs[0]-sfs[2] if ((dm == 1) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM1_pt_bin2_up',   'value': sfs[0]+sfs[1] if ((dm == 1) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM1_pt_bin2_down', 'value': sfs[0]-sfs[2] if ((dm == 1) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM1_pt_bin3_up',   'value': sfs[0]+sfs[1] if ((dm == 1) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM1_pt_bin3_down', 'value': sfs[0]-sfs[2] if ((dm == 1) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM2_pt_bin1_up',   'value': sfs[0]+sfs[1] if ((dm == 2) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM2_pt_bin1_down', 'value': sfs[0]-sfs[2] if ((dm == 2) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM2_pt_bin2_up',   'value': sfs[0]+sfs[1] if ((dm == 2) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM2_pt_bin2_down', 'value': sfs[0]-sfs[2] if ((dm == 2) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM2_pt_bin3_up',   'value': sfs[0]+sfs[1] if ((dm == 2) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM2_pt_bin3_down', 'value': sfs[0]-sfs[2] if ((dm == 2) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM10_pt_bin1_up',  'value': sfs[0]+sfs[1] if ((dm == 10) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM10_pt_bin1_down','value': sfs[0]-sfs[2] if ((dm == 10) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM10_pt_bin2_up',  'value': sfs[0]+sfs[1] if ((dm == 10) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM10_pt_bin2_down','value': sfs[0]-sfs[2] if ((dm == 10) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM10_pt_bin3_up',  'value': sfs[0]+sfs[1] if ((dm == 10) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM10_pt_bin3_down','value': sfs[0]-sfs[2] if ((dm == 10) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM11_pt_bin1_up',  'value': sfs[0]+sfs[1] if ((dm == 11) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM11_pt_bin1_down','value': sfs[0]-sfs[2] if ((dm == 11) and (ibin == 0)) else sfs[0] },
      { 'key': 'DM11_pt_bin2_up',  'value': sfs[0]+sfs[1] if ((dm == 11) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM11_pt_bin2_down','value': sfs[0]-sfs[2] if ((dm == 11) and (ibin == 1)) else sfs[0] },
      { 'key': 'DM11_pt_bin3_up',  'value': sfs[0]+sfs[1] if ((dm == 11) and (ibin == 2)) else sfs[0] },
      { 'key': 'DM11_pt_bin3_down','value': sfs[0]-sfs[2] if ((dm == 11) and (ibin == 2)) else sfs[0] },
    ]
  return tiddata_syst


#def maketiddata_dmbin(sfs,dms):
#  """Make DM bins of DM-dependent tau ID SFs."""
#  ###if 1 in sfs and 2 not in sfs: # reuse DM1 for DM2 if not available
#  ###  sfs[2] = sfs[1]
#  ###if 10 in sfs and 11 not in sfs: # reuse DM10 for DM11 if not available
#  ###  sfs[11] = sfs[10]
#
#  tiddata_dmbins = {
#    'nodetype': 'category', # category:dm
#    'input': "dm",
#    #'default': 1.0, # no default: throw error if unsupported DM
#    'content': [ # key:dm
#      { 'key': dm,
#        'value': {
#          'nodetype': 'category', # syst
#          'input': "syst",
#          'default':  ( {'nodetype': 'formula', 'expression': sfs[dm]['nom'], 'parser': "TFormula", 'variables': ["pt"] } if isinstance(sfs[dm]['nom'],str) else sfs[dm]['nom']) if isinstance(sfs[dm],dict) else sfs[dm][0],
#          'content': maketiddata_dmbin_syst(sfs[dm])
#        }
#      } for dm in dms
#    ] # key:dm
#  } # category:dm
#  
#  return tiddata_dmbins


def maketiddata_dmbin(sfs,dms,dmptbins):
  """Make DM bins of DM-dependent tau ID SFs."""
  ###if 1 in sfs and 2 not in sfs: # reuse DM1 for DM2 if not available
  ###  sfs[2] = sfs[1]
  ###if 10 in sfs and 11 not in sfs: # reuse DM10 for DM11 if not available
  ###  sfs[11] = sfs[10]

  tiddata_dmbins = {
    'nodetype': 'category', # category:dm
    'input': "dm",
    #'default': 1.0, # no default: throw error if unsupported DM
    'content': [ # key:dm
      { 'key': dm,
        'value': {
          'nodetype': 'binning',
          'input': "pt",
          'edges': dmptbins,
          'content': [ # key nbin
            { 'nodetype': 'category',
              'input': "syst",
              'content': maketiddata_dmbin_syst(sfs[dm][ibin], dm, ibin)
            }
            for ibin in range(len(dmptbins)-1)
          ], # key: ibin
          'flow': "clamp",
        }
      }
      for dm in dms
    ] # key:dm
  } # category:dm
  
  return tiddata_dmbins


def maketiddata_dm(sfs,dms,dmptbins): #new
  """Construct data block for DM-dependent tau ID SFs."""
  
  # PREPARE DATA BLOCK per WP
  tiddata_wps = [ ]
  wps = list(sfs.keys()) # VSjet WPs
  wps.sort(key=wp_sortkey) # sort from loosest to tightest
  for wp in wps:
    #from IPython import embed; embed()
    sfswp = sfs[wp]
    # category:wp -> category:wp_VSe -> category:syst -> formula:sf(pt)
    if any(isinstance(k,str) for k in sfswp.keys()):
      wps_VSe = list(sfswp.keys()) # VSe WPs
      wps_VSe.sort(key=wp_sortkey) # sort from loosest to tightest
      tiddata_wps.append( # key:wp
        { 'key': wp,
          'value': {
            'nodetype': 'category', # category:wp_VSe
            'input': "wp_VSe",
            #'default': 1.0, # no default => throw error if unrecognized WP
            'content': [ # key:wp_VSe
              { 'key': wp_VSe,
                'value': maketiddata_dmbin(sfswp[wp_VSe], dms, dmptbins) #new
              } for wp_VSe in wps_VSe
            ] # key:wp_VSe
          } # category:wp_VSe
        } # key:wp
      )
    # category:wp -> category:syst -> formula:sf(pt)
    else:
      tiddata_wps.append( # key:wp
        { 'key': wp,
          'value': maketiddata_dmbin(sfs[wp],dms, dmptbins) #new
        } # key:wp
      )

  #from IPython import embed; embed()



  
  # FULL DATA BLOCK for pt-dependent SFs
  # category:genmatch -> category:wp -> category:dm -> category:syst
  tiddata = schema.Category.parse_obj({ # category:genmatch -> category:wp -> category:dm -> category:syst
    'nodetype': 'category', # category:genmatch
    'input': "genmatch",
    #'default': 1.0, # no default: throw error if unrecognized genmatch
    'content': [
      { 'key': 1, 'value': 1.0 }, # e  -> tau_h fake
      { 'key': 2, 'value': 1.0 }, # mu -> tau_h fake
      { 'key': 3, 'value': 1.0 }, # e  -> tau_h fake
      { 'key': 4, 'value': 1.0 }, # mu -> tau_h fake
      {
        'key': 5,  # real tau_h
        'value': {
          'nodetype': 'category', # category:wp
          'input': "wp",
          #'default': 1.0, # no default: throw error if unrecognized WP
          'content': tiddata_wps # key:wp
        } # category:wp
      },
      { 'key': 6, 'value': 1.0 }, # j  -> tau_h fake
      { 'key': 0, 'value': 1.0 }, # j  -> tau_h fake
    ]
  }) # category:genmatch
  return tiddata

def makecorr_tid(ptsfs=None,dmsfs=None,Format='',**kwargs):
  """Tau ID SF Correction object for BOTH pT-dependent and DM-dependent SFs.
     makecorr_tid
       -> maketiddata_pt -> maketiddata_ptbin -> maketiddata_pt
       bin_syst -> maketiddata_ptform
       -> maketiddata_dm -> maketiddata_dmbin -> maketiddata_dmbin_syst
  """
  verb     = kwargs.get('verb',0) # verbosity level
  tag      = kwargs.get('tag',"") # output tag for JSON file
  outdir   = kwargs.get('outdir',"data/tau") # output directory for JSON file
  dms      = kwargs.get('dms',None)
  ptbins   = kwargs.get('bins',[20.,25.,30.,35.,40.,500.,1000.,2000.])
  dmptbins = kwargs.get('dmptbins',[20.0, 40.0, 60.0, 200.0]) # 2025 binning: 3 pT bins per DM
  wps_VSe  = kwargs.get('wps_VSe',None) # VSe WPs
  vse_id   = kwargs.get('vse_id',"DeepTau2018v2p5VSe") # anti-electron discriminator (DeepTau even for the PNet VSjet measurement)
  systkeys = kwargs.get('systs',['nom','up','down']) # keys/flags for systematic variations
  version  = kwargs.get('version',3)
  systkeys.sort(key=syst_sortkey) # sort nom, up, down
  ensuredir(outdir)
  if ptsfs and dmsfs:
    tid   = kwargs.get('id',   "unkown")
    era   = kwargs.get('era',  "unkown")
    #name  = kwargs.get('name', f"tau_sf_pt-dm_{tid}_{era}{tag}")
    name  = kwargs.get('name', f"tau_sf_pt-dm_{tid}_{era}_{tag}")
    fname = kwargs.get('fname',f"{outdir}/{name}.json")
    info  = kwargs.get('info', f"{tid} SFs in {era}")
  else: # test format with dummy values
    tid   = kwargs.get('id',  "DeepTau2017v2p1VSjet")
    header(f"Dummy {tid} SFs for test")
    name  = kwargs.get('name', f"test_{tid}_pt-dm")
    fname = kwargs.get('fname',f"{outdir}/test_tau_pt-dm{tag}.json")
    info  = kwargs.get('info', f"{tid} SFs")
    ptbins = [20.,40.,500.,1000.,2000.]
    dms   = [0,1] #,2,10,11]
    wps   = [
      #'VVVLoose', 'VVLoose', 'VLoose',
      'Loose', 'Medium', #'Tight',
      #'VTight', 'VVTight'
    ]
    sf = (1.,0.2,0.2) # dummy sf
    #sf = { 'nom': 1.0, 'up': 0.2, 'down': 0.2, 'yearup': 0.2, 'yeardown': 0.2 } # dummy sf
    if wps_VSe:
      ptsfs = { wp: {wpe: [sf for i in range(len(ptbins)-1)] for wpe in wps_VSe} for wp in wps }
      dmsfs = { wp: {wpe: {dm: [sf]*(len(dmptbins)-1) for dm in dms} for wpe in wps_VSe} for wp in wps }
    else:
      ptsfs = {wp: [sf for i in range(len(ptbins)-1)] for wp in wps}
      dmsfs = {wp: {dm: [sf]*(len(dmptbins)-1) for dm in dms} for wp in wps}
  #assert all(len(ptsfs[wp])==len(ptbins)-1 for wp in ptsfs), f"Number of SFs ({sfs}) does not match ({len(ptbins)-1})!"
  assert Format in ['Mar07','Jul18','Run3_Dec05', "Run3_May24"] or ptbins[-3]==500.,  f"Third-to-last bin ({ptbins[-3]}) should be 500!"
  assert Format in ['Mar07','Jul18','Run3_Dec05', "Run3_May24"] or ptbins[-2]==1000., f"Second-to-last bin ({ptbins[-2]}) should be 1000!"
  assert Format in ['Mar07','Jul18','Run3_Dec05', "Run3_May24"] or ptbins[-1]>1000.,  f"Last bin ({ptbins[-1]}) should be larger than 1000!"
  
  # FIND ALL DMS
  if dms==None:
    dms = set()
    for wp in dmsfs.keys():
      if any(isinstance(k,str) for k in dmsfs[wp].keys()):
        for wp_VSe in dmsfs[wp].keys():
          dms.update(dmsfs[wp][wp_VSe].keys())
      else:
        dms.update(dmsfs[wp].keys())
    dms = list(dms) # convert back to a list
    dms.sort() # sort numerically
    assert all(0<=dm<=12 for dm in dms), f"DMs must be integers from 0 to 12. Got dms={dms}..."
  
  # VSjet WPs
  wps = sorted(set(list(ptsfs.keys())+list(dmsfs.keys())))
  wps.sort(key=wp_sortkey) # sort from loosest to tightest
  
  # FIND ALL VSe WPs
  if wps_VSe==None:
    wps_VSe = set()
    for sfs in [ptsfs,dmsfs]:
      for wp in sfs.keys():
        if isinstance(sfs[wp],dict) and any(isinstance(k,str) for k in sfs[wp].keys()):
          wps_VSe.update(sfs[wp].keys())
    wps_VSe = list(wps_VSe) # convert back to a list
    wps_VSe.sort(key=wp_sortkey) # sort from loosest to tightest
  
  # INPUTS
  inputs = [
    {'name': "pt",       'type': "real",   'description': "Reconstructed tau pT"},
    {'name': "dm",       'type': "int",    'description': getdminfo(dms)},
    {'name': "genmatch", 'type': "int",    'description': getgminfo()},
    {'name': "wp",       'type': "string", 'description': getwpinfo(tid,wps)},
  ]
  if wps_VSe: # only add wp_VSe if specified by user, or found in SF dict
    inputs += [
      {'name': "wp_VSe", 'type': "string", 'description': getwpinfo(vse_id,wps_VSe)},
    ]
  dmlist = ",".join(str(d) for d in sorted(dms)) # actual DM list (e.g. 0,1,2,10,11)
  nptbin = len(dmptbins)-1
  if Format == 'Mar07':
    syst_info = "Systematic variations for the pT-binned SF: "\
      "'up'/'down' (the total uncertainty) , "\
      "'stat_ptbin1_up'/'stat_ptbin1_down' (stat. uncertainty for 20<pt<25 bin) , " \
      "'stat_ptbin2_up'/'stat_ptbin2_down' (stat. uncertainty for 25<pt<30 bin) , " \
      "'stat_ptbin3_up'/'stat_ptbin3_down' (stat. uncertainty for 30<pt<35 bin) , " \
      "'stat_ptbin4_up'/'stat_ptbin4_down' (stat. uncertainty for 35<pt<40 bin) , " \
      "'stat_ptbin5_up'/'stat_ptbin5_down' (stat. uncertainty for 40<pt<50 bin) , " \
      "'stat_ptbin6_up'/'stat_ptbin6_down' (stat. uncertainty for 50<pt<60 bin) , " \
      "'stat_ptbin7_up'/'stat_ptbin7_down' (stat. uncertainty for 60<pt<80 bin) , " \
      "'stat_ptbin8_up'/'stat_ptbin8_down' (stat. uncertainty for 80<pt<100 bin) , " \
      "'stat_ptbin9_up'/'stat_ptbin9_down' (stat. uncertainty for 100<pt<140 bin) , " \
      "'syst_alleras_up'/'syst_alleras_down' (syst. uncertainty for low pT bins correlated by eras) , " \
      "'syst_$ERA_up'/'syst_$ERA_down' (syst. uncertainty for low pT bins uncorrelated by eras $ERA=2016_preVFP,2016_postVFP,2017,2018) , " \
      "'stat_highpT_bin1_up'/'stat_highpT_bin1_down' (stat. uncertainty for 140<pt<200 bin) , " \
      "'stat_highpT_bin2_up'/'stat_highpT_bin2_down' (stat. uncertainty for pt>200 bin) , " \
      "'syst_highpT_up'/'syst_highpT_down' (syst. uncertainty for high pT bins correlated by eras) , " \
      "'syst_highpT_extrap_up'/'syst_highpT_extrap_down' (syst. uncertainty to account for the extrapolation of SF from measured pT regions to higher pT regions correlated by eras) , " \
      "Systematic variations for the DM-binned SF: " \
      "'stat$i_dm$DM_up'/'stat$i_dm$DM_up' (stat. uncertainty for dm bin from ith eigenvector $i=1,2 $DM=0,1,10,11) , " \
      "'syst_alleras_up'/'syst_alleras_down' (syst. uncertainty for low pT bins correlated by eras and DM-bins) , " \
      "'syst_$ERA_up'/'syst_$ERA_down' (syst. uncertainty for low pT bins uncorrelated by eras $ERA=2016_preVFP,2016_postVFP,2017,2018) , " \
      "'syst_$ERA_dm$DM_up'/'syst_$ERA_$DM_down' (syst. uncertainty for low pT bins uncorrelated by eras and DM $ERA=2016_preVFP,2016_postVFP,2017,2018) $DM=0,1,10,11 , "    
  elif Format == 'Jul18' or Format == 'Run3_Dec05' or Format == "Run3_May24":
    syst_info = "Systematic variations: 'nom'; "\
      f"'up'/'down' = total uncertainty of the (DM, pT) cell, to be treated as uncorrelated "\
      f"across DM ({dmlist}) and the {nptbin} pT bins; "\
      f"'DM$DM_pt_bin$N_up'/'DM$DM_pt_bin$N_down' ($DM in {dmlist}; $N in 1..{nptbin}) = "\
      "decorrelated variations shifting a single (DM, pT-bin) cell with all others held at nominal."


    #syst_info += "Systematic variations for the DM-binned SF: " \
      #"'stat$i_dm$DM_up'/'stat$i_dm$DM_up' (stat. uncertainty for dm bin from ith eigenvector $i=1,2 $DM=0,1,10,11) , " \
      #"'syst_alleras_up'/'syst_alleras_down' (syst. uncertainty for low pT bins correlated by eras and DM-bins) , " \
      #"'syst_$ERA_up'/'syst_$ERA_down' (syst. uncertainty for low pT bins uncorrelated by eras $ERA=2016_preVFP,2016_postVFP,2017,2018,2022,2023) , " \
      #"'syst_TES_$ERA_dm$DM_up'/'syst_TES_$ERA_$DM_down' (syst. uncertainty for low pT bins due to the tau energy scale uncorrelated by eras and DM $ERA=2016_preVFP,2016_postVFP,2017,2018,2022,2023) $DM=0,1,10,11 , "
      
  inputs += [
    {'name': "syst",     'type': "string", 'description': syst_info},
  ]
  #from IPython import embed; embed()
    
  if Format == 'Jul18' or Format == "Run3_Dec05" or Format == "Run3_May24":
    inputs += [
      {'name': "flag",     'type': "string", 'description': "Flag: 'pt' = pT-dependent SFs, 'dm' = DM-dependent SFs"},
    ]
    content = [
      { 'key': 'pt', 'value': maketiddata_pt(ptsfs,ptbins,newExtrapolation=(Format in ['Mar07','Jul18','Run3_Dec05','Run3_May24']),verb=verb) }, # pt-dependent
      { 'key': 'dm', 'value': maketiddata_dm(dmsfs,dms,dmptbins) }, # DM-dependent
    ]
  else: # no high pT SF for Run-3 at the moment - add back when available
    inputs += [
      {'name': "flag",     'type': "string", 'description': "Flag: 'dm' = DM-dependent SFs"},
    ]
    content = [
      { 'key': 'dm', 'value': maketiddata_dm(dmsfs,dms) }, # DM-dependent
    ]

  # FULL CORRECTION OBJECT
  corr = schema.Correction.parse_obj({
    'version': version,
    'name': name,
    'description': f"{info}, measured over pT in [{dmptbins[0]:g}, {dmptbins[-1]:g}] GeV. "+\
                   "Use flag='dm' for the per-DM, per-pT-bin SFs (default). "+\
                   "flag='pt' gives a DM-averaged pT-binned SF for analyses that don't categorize by DM. "+\
                   "Beyond the per-axis 'up'/'down' total uncertainty, the 'syst' axis also exposes "+\
                   f"DM{{DM}}_pt_bin{{N}}_up/down keys (DM in {dmlist}; N in 1..{nptbin}) that vary a single "+\
                   "(DM, pT-bin) cell with all others held at nominal — for use as decorrelated "+\
                   "nuisances in a fit.",
    'inputs': inputs,
    'output': {'name': "sf", 'type': "real", 'description': kwargs.get('output_desc', f"{tid} scale factor")},
    'data': schema.Category.parse_obj({ # category:genmatch -> category:wp -> category:dm -> category:syst
      'nodetype': 'category', # category:genmatch
      'input': "flag",
      #'default': 1.0, # no default: throw error if unrecognized genmatch
      'content': content,
    })
  })
  
  # LOG
  if verb>=2:
    print(JSONEncoder.dumps(corr))
  elif verb>=1:
    print(corr)
  if fname:
    print(f">>> Writing {fname}...")
    cset = schema.CorrectionSet(
      schema_version = schema.VERSION,
      description    = info,
      corrections    = [corr],
    )
    JSONEncoder.write(cset,fname)

  return corr


def makecorr_tid_pt(sfs=None,**kwargs):
  """Tau ID SF Correction object for ONLY pT-dependent SFs."""
  verb    = kwargs.get('verb',0)
  tag     = kwargs.get('tag',"") # output tag for JSON file
  outdir  = kwargs.get('outdir',"data/tau") # output directory for JSON file
  ptbins  = kwargs.get('bins',[20.,25.,30.,35.,40.,500.,1000.,2000.])
  ensuredir(outdir)
  if sfs:
    id    = kwargs.get('id',   "unkown")
    era   = kwargs.get('era',  "unkown")
    name  = kwargs.get('name', f"tau_sf_pt_{id}_{era}")
    fname = kwargs.get('fname',f"{outdir}/{name}{tag}.json")
    info  = kwargs.get('info', f"pT-dependent SFs for {id} in {era}")
    wps   = list(sfs.keys())
  else: # test format with dummy values
    id    = kwargs.get('id',  "DeepTau2017v2p1VSjet")
    header(f"Dummy pT-dependent {id} SFs for test")
    name  = kwargs.get('name', f"test_{id}_pt")
    fname = kwargs.get('fname',f"{outdir}/test_tau_pt{tag}.json")
    info  = kwargs.get('info', f"pT-dependent SFs for {id}")
    wps   = [
      #'VVVLoose', 'VVLoose', 'VLoose',
      'Loose', 'Medium', 'Tight',
      #'VTight', 'VVTight'
    ]
    sfs   = {wp: [(1.,0.2,0.2) for i in range(len(ptbins)-1)] for wp in wps}
  assert all(len(sfs[w])==len(ptbins)-1 for w in sfs), f"Number of SFs ({sfs}) does not match ({len(ptbins)-1})!"
  assert ptbins[-3]==500., f"Third-to-last bin ({ptbins[-3]}) should be 500!"
  assert ptbins[-2]==1000., f"Second-to-last bin ({ptbins[-2]}) should be 1000!"
  assert ptbins[-1]>1000., f"Last bin ({ptbins[-1]}) should be larger than 1000!"
  wps.sort(key=wp_sortkey)
  corr    = schema.Correction.parse_obj({
    'version': version,
    'name': name,
    'description': "pT-dependent SFs for DeepTau2017v2p1VSjet",
    'inputs': [
      {'name': "pt",       'type': "real",   'description': "Reconstructed tau pT"},
      {'name': "genmatch", 'type': "int",    'description': getgminfo()},
      {'name': "wp",       'type': "string", 'description': getwpinfo(id,wps)},
      {'name': "syst",     'type': "string", 'description': getsystinfo()},
    ],
    'output': {'name': "sf", 'type': "real", 'description': f"pT-dependent {id} scale factor"},
    'data': maketiddata_pt(sfs,ptbins,wps)
  })
  if verb>=2:
    print(JSONEncoder.dumps(corr))
  elif verb>=1:
    print(corr)
  if fname:
    print(f">>> Writing {fname}...")
    JSONEncoder.write(corr,fname)
  return corr
  

def makecorr_tid_dm(sfs=None,**kwargs):
  """Tau ID SF Correction object for ONLY DM-dependent SFs."""
  verb    = kwargs.get('verb',0)
  tag     = kwargs.get('tag',"") # output tag for JSON file
  outdir  = kwargs.get('outdir',"data/tau") # output directory for JSON file
  ensuredir(outdir)
  if sfs:
    id    = kwargs.get('id',   "unkown")
    era   = kwargs.get('era',  "unkown")
    name  = kwargs.get('name', f"tau_sf_dm_{id}_{era}")
    fname = kwargs.get('fname',f"{outdir}/{name}{tag}.json")
    info  = kwargs.get('info', f"DM-dependent SFs for {id} in {era}")
    wps   = list(sfs.keys())
    dms   = list(sfs[wps[0]].keys()) # get list of DMs from first WP
  else: # test format with dummy values
    id    = kwargs.get('id',  "DeepTau2017v2p1VSjet")
    header(f"Dummy DM-dependent {id} SFs for test")
    name  = kwargs.get('name', f"test_{id}_dm")
    fname = kwargs.get('fname',f"{outdir}/test_tau_dm{tag}.json")
    info  = kwargs.get('info', f"DM-dependent SFs for {id}")
    wps   = [
      #'VVVLoose', 'VVLoose', 'VLoose',
      'Loose', 'Medium', 'Tight',
      'VTight', 'VVTight'
    ]
    dms   = [0,1,2,10,11]
    sfs   = {wp: {dm: (1.,0.2,0.2) for dm in dms} for wp in wps}
  wps.sort(key=wp_sortkey)
  dms.sort()

  corr = schema.Correction.parse_obj({
    'version': version,
    'name': name,
    'description': info,
    'inputs': [
      #{'name': "pt",       'type': "real",   'description': "Reconstructed tau pT"},
      {'name': "dm",       'type': "int",    'description': getdminfo(dms)},
      {'name': "genmatch", 'type': "int",    'description': getgminfo()},
      {'name': "wp",       'type': "string", 'description': getwpinfo(id,wps)},
      {'name': "syst",     'type': "string", 'description': getsystinfo()},
    ],
    'output': {'name': "sf", 'type': "real", 'description': f"DM-dependent {id} scale factor"},
    'data': maketiddata_dm(sfs,dms,wps)
  })
  if verb>=2:
    print(JSONEncoder.dumps(corr))
  elif verb>=1:
    print(corr)
  if fname:
    print(f">>> Writing {fname}...")
    JSONEncoder.write(corr,fname)
  return corr
  

def evaluate(corrs):
  header("Evaluate")
  cset = wrap(corrs) # wrap to create C++ object that can be evaluated
  dms  = [-1,0,1,2,5,10,11]
  gms  = [0,1,2,3,4,5,6,7]
  pts  = [10.,21.,26.,31.,36.,41.,501.,750.,999.,2000.]
  for name in list(cset):
    corr = cset[name]
    print(f">>>\n>>> {name}: {corr.description}")
    wps = ['Medium','Tight']
    if 'dm' in name:
      xbins = dms
      head  = ">>> %8s"%("genmatch")+" ".join("  %-15d"%(d) for d in dms)
    else:
      xbins = pts
      head  = ">>> %8s"%("genmatch")+" ".join("  %-15.1f"%(p) for p in pts)
    for wp in wps:
      print(f">>>\n>>> WP={wp}")
      print(head)
      for gm in gms:
        row = ">>> %8d"%(gm)
        for x in xbins:
          sfnom = 0.0
          for syst in ['nom','up','down']:
            #print(">>>   gm=%d, eta=%4.1f, syst=%r sf=%s"%(gm,eta,syst,eval(corr,eta,gm,wp,syst)))
            try:
              sf = corr.evaluate(x,gm,wp,syst)
              if 'nom' in syst:
                row += "%6.2f"%(sf)
                sfnom = sf
              elif 'up' in syst:
                row += "%+6.2f"%(sf-sfnom)
              else:
                row += "%+6.2f"%(sf-sfnom)
            except Exception as err:
              row += "\033[1m\033[91m"+"  ERR".ljust(6)+"\033[0m"
        print(row)
  print(">>>")
  

def main():
  """Test format: validate with dummy variables; evaluate with dummy input; ..."""
  #corr1 = makecorr_tid_pt()
  #corr2 = makecorr_tid_dm()
  #corr3 = makecorr_tid(wps_VSe=None,verb=2)
  corr3 = makecorr_tid(wps_VSe=['VVLoose'],verb=2)
  #corrs = [corr1,corr2] #,corr3]
  #evaluate(corrs)
  #write(corrs)
  #read(corrs)
  

if __name__ == '__main__':
  print("Testing tau_tid format")
  main()
  print()
  
