# Author: CMSDAS26 Tau long exercise 
# Description: 2024 Run3 (13.6 TeV, NanoAODv15) sample list for the mutau exercise.
#   - MC: Drell-Yan (2Tau signal + 2Mu/2E), ttbar, W+jets, single-top, diboson.
#   - Data: Muon0/Muon1 primary datasets (SingleMuon no longer exists in Run3).
# This list is used by 'pico.py' when you (re)process NanoAOD -> flat pico ntuples.
# For the exercise you normally READ the pre-made 2024 pico ntuples and only run
# 'pico.py' on ONE small sample as a demo; the full teaching subset below is enough.
# The complete production list is PicoProducer/samples/samples_2024v15.py.
from TauFW.PicoProducer.storage.Sample import MC as M
from TauFW.PicoProducer.storage.Sample import Data as D
storage  = None # read NanoAOD from DAS via the global redirector
url      = "root://cms-xrd-global.cern.ch/"
filelist = None
opts     = "useT1=False,dojec=False"
opts_dy  = opts+",zpt=True"    # apply Z-pT reweighting to Drell-Yan
opts_tt  = opts+",toppt=True"  # apply top-pT reweighting to ttbar
CAMP     = "RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2"
samples  = [

  # DRELL-YAN -> tautau (this is the Z->tautau SIGNAL in mutau)
  M('DY','DYto2Tau_Bin-MLL-10to50',
    "/DYto2Tau_Bin-MLL-10to50_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),
  M('DY','DYto2Tau_Bin-MLL-50to120',
    "/DYto2Tau_Bin-MLL-50to120_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),
  M('DY','DYto2Tau_Bin-MLL-120to200',
    "/DYto2Tau_Bin-MLL-120to200_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),

  # DRELL-YAN -> mumu (used for the Z->mumu cross-section cross-check)
  M('DY','DYto2Mu_Bin-MLL-10to50',
    "/DYto2Mu_Bin-MLL-10to50_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),
  M('DY','DYto2Mu_Bin-MLL-50to120',
    "/DYto2Mu_Bin-MLL-50to120_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),
  M('DY','DYto2Mu_Bin-MLL-120to200',
    "/DYto2Mu_Bin-MLL-120to200_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),

  # DRELL-YAN -> ee (contributes to the ZL background via e->tau_h fakes)
  M('DY','DYto2E_Bin-MLL-10to50',
    "/DYto2E_Bin-MLL-10to50_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),
  M('DY','DYto2E_Bin-MLL-50to120',
    "/DYto2E_Bin-MLL-50to120_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_dy),

  # TTBAR
  M('TT','TTto2L2Nu',
    "/TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/%s-v3/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_tt),
  M('TT','TTtoLNu2Q',
    "/TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_tt),
  M('TT','TTto4Q',
    "/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts_tt),

  # W+JETS
  M('WJ','WtoTauNu-2Jets',
    "/WtoTauNu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/%s-v3/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('WJ','WtoMuNu-2Jets',
    "/WtoMuNu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/%s-v3/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('WJ','WtoENu-2Jets',
    "/WtoENu-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/%s-v3/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),

  # SINGLE TOP
  M('ST','TBbarQ_t-channel',
    "/TBbarQtoLNu-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('ST','TbarBQ_t-channel',
    "/TbarBQtoLNu-t-channel-4FS_TuneCP5_13p6TeV_powheg-madspin-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('ST','TWminusto2L2Nu',
    "/TWminusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/Run3Winter24NanoAOD-JMENanoV14_133X_mcRun3_2024_realistic_v10-v2/NANOAODSIM",
    store=storage,url=url,files=filelist,opts=opts),
  M('ST','TbarWplusto2L2Nu',
    "/TbarWplusto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/Run3Winter24NanoAOD-JMENanoV14_133X_mcRun3_2024_realistic_v10-v2/NANOAODSIM",
    store=storage,url=url,files=filelist,opts=opts),

  # DIBOSON
  M('VV','WWto2L2Nu',
    "/WWto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('VV','WZto2L2Q',
    "/WZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),
  M('VV','ZZto2L2Nu',
    "/ZZto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/%s-v2/NANOAODSIM"%CAMP,
    store=storage,url=url,files=filelist,opts=opts),

  # DATA: Muon primary datasets (SingleMuon merged into Muon0/Muon1 in Run3)
  D('Data','Muon0_Run2024C',"/Muon0/Run2024C-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024D',"/Muon0/Run2024D-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024E',
    "/Muon0/Run2024E-MINIv6NANOv15-v1/NANOAOD",
    "/Muon0/Run2024E-PromptReco-v2/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024F',"/Muon0/Run2024F-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024G',"/Muon0/Run2024G-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024H',"/Muon0/Run2024H-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon0_Run2024I',
    "/Muon0/Run2024I-MINIv6NANOv15-v1/NANOAOD",
    "/Muon0/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024C',"/Muon1/Run2024C-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024D',"/Muon1/Run2024D-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024E',"/Muon1/Run2024E-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024F',"/Muon1/Run2024F-MINIv6NANOv15-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024G',"/Muon1/Run2024G-MINIv6NANOv15-v2/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024H',"/Muon1/Run2024H-MINIv6NANOv15-v2/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),
  D('Data','Muon1_Run2024I',
    "/Muon1/Run2024I-MINIv6NANOv15-v1/NANOAOD",
    "/Muon1/Run2024I-MINIv6NANOv15_v2-v1/NANOAOD",
    store=storage,url=url,files=filelist,opts=opts,channels=["skim*",'mutau','mumu']),

]
