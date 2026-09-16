# Author: Izaak Neutelings (May 2020); adapted for CMSDAS26 (2024 Run3, DeepTau2018v2p5 + PNet + UParT)
# Description: Simple, self-contained teaching module to pre-select mutau events on 2024 NanoAODv15.
#   Writes a flat 'tree' with branch names matching the production pico (TreeProducerMuTau.py), so the
#   same plotter works on both this demo output and the pre-made 2024 ntuples. For the full exercise you
#   read the pre-made ntuples; run this module on ONE small sample only, to learn how ntuples are made.
from ROOT import TFile, TTree, TH1D
from ROOT import Math
import numpy as np
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection, Object


# Inspired by 'Object' class from NanoAODTools.
# Convenient to add MET as a 4-momentum to other physics objects using p4().
class Met(Object):
  def __init__(self,event,prefix,index=None):
    self.eta = 0.0
    self.mass = 0.0
    Object.__init__(self,event,prefix,index)


class ModuleMuTau(Module):

  def __init__(self,fname,**kwargs):
    self.outfile = TFile(fname,'RECREATE')
    self.default_float = -999.0
    self.default_int = -999
    self.dtype      = kwargs.get('dtype', 'data')
    self.ismc       = self.dtype=='mc'
    self.isdata     = self.dtype=='data'

  def beginJob(self):
    """Prepare output analysis tree and cutflow histogram."""

    # CUTFLOW HISTOGRAM
    self.cutflow           = TH1D('cutflow','cutflow',25,0,25)
    self.cut_none          = 0
    self.cut_trig          = 1
    self.cut_muon          = 2
    self.cut_muon_veto     = 3
    self.cut_tau           = 4
    self.cut_electron_veto = 5
    self.cut_pair          = 6
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_none,           "no cut"        )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_trig,           "trigger"       )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_muon,           "muon"          )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_muon_veto,      "muon     veto" )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_tau,            "tau"           )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_electron_veto,  "electron veto" )
    self.cutflow.GetXaxis().SetBinLabel(1+self.cut_pair,           "pair"          )

    # TREE
    self.tree        = TTree('tree','tree')
    self.pt_1        = np.zeros(1,dtype='f')
    self.eta_1       = np.zeros(1,dtype='f')
    self.q_1         = np.zeros(1,dtype='i')
    self.id_1        = np.zeros(1,dtype='?')
    self.iso_1       = np.zeros(1,dtype='f')
    self.genmatch_1  = np.zeros(1,dtype='f')
    self.decayMode_1 = np.zeros(1,dtype='i')
    self.pt_2        = np.zeros(1,dtype='f')
    self.eta_2       = np.zeros(1,dtype='f')
    self.q_2         = np.zeros(1,dtype='i')
    self.genmatch_2  = np.zeros(1,dtype='f')
    self.decayMode_2 = np.zeros(1,dtype='i')
    # --- DeepTau2018v2p5 (main tagger for the selection) ---
    self.idDeepTau2018v2p5VSjet_2  = np.zeros(1,dtype='i')
    self.idDeepTau2018v2p5VSe_2    = np.zeros(1,dtype='i')
    self.idDeepTau2018v2p5VSmu_2   = np.zeros(1,dtype='i')
    self.rawDeepTau2018v2p5VSjet_2 = np.zeros(1,dtype='f')
    # --- the two other taggers, for the tagger comparison (raw VSjet score + decay mode) ---
    self.rawPNetVSjet_2   = np.zeros(1,dtype='f')
    self.rawUParTVSjet_2  = np.zeros(1,dtype='f')
    self.decayModePNet_2  = np.zeros(1,dtype='i')
    self.decayModeUParT_2 = np.zeros(1,dtype='i')
    self.m_vis       = np.zeros(1,dtype='f')
    self.genWeight   = np.zeros(1,dtype='f')
    self.tree.Branch('pt_1',         self.pt_1,        'pt_1/F'       )
    self.tree.Branch('eta_1',        self.eta_1,       'eta_1/F'      )
    self.tree.Branch('q_1',          self.q_1,         'q_1/I'        )
    self.tree.Branch('id_1',         self.id_1,        'id_1/O'       )
    self.tree.Branch('iso_1',        self.iso_1,       'iso_1/F'      )
    self.tree.Branch('genmatch_1',   self.genmatch_1,  'genmatch_1/F' )
    self.tree.Branch('decayMode_1',  self.decayMode_1, 'decayMode_1/I')
    self.tree.Branch('pt_2',         self.pt_2,  'pt_2/F'             )
    self.tree.Branch('eta_2',        self.eta_2, 'eta_2/F'            )
    self.tree.Branch('q_2',          self.q_2,   'q_2/I'              )
    self.tree.Branch('genmatch_2',   self.genmatch_2,  'genmatch_2/F' )
    self.tree.Branch('decayMode_2',  self.decayMode_2, 'decayMode_2/I')
    self.tree.Branch('idDeepTau2018v2p5VSjet_2',  self.idDeepTau2018v2p5VSjet_2,  'idDeepTau2018v2p5VSjet_2/I' )
    self.tree.Branch('idDeepTau2018v2p5VSe_2',    self.idDeepTau2018v2p5VSe_2,    'idDeepTau2018v2p5VSe_2/I'   )
    self.tree.Branch('idDeepTau2018v2p5VSmu_2',   self.idDeepTau2018v2p5VSmu_2,   'idDeepTau2018v2p5VSmu_2/I'  )
    self.tree.Branch('rawDeepTau2018v2p5VSjet_2', self.rawDeepTau2018v2p5VSjet_2, 'rawDeepTau2018v2p5VSjet_2/F')
    self.tree.Branch('rawPNetVSjet_2',   self.rawPNetVSjet_2,   'rawPNetVSjet_2/F'  )
    self.tree.Branch('rawUParTVSjet_2',  self.rawUParTVSjet_2,  'rawUParTVSjet_2/F' )
    self.tree.Branch('decayModePNet_2',  self.decayModePNet_2,  'decayModePNet_2/I' )
    self.tree.Branch('decayModeUParT_2', self.decayModeUParT_2, 'decayModeUParT_2/I')
    self.tree.Branch('m_vis',        self.m_vis, 'm_vis/F'            )
    self.tree.Branch('genWeight',    self.genWeight,   'genWeight/F'  )

  def endJob(self):
    """Wrap up after running on all events and files"""
    self.outfile.Write()
    self.outfile.Close()

  def analyze(self, event):
    """Process event, return True (pass, go to next module) or False (fail, go to next event)."""

    # NO CUT
    self.cutflow.Fill(self.cut_none)

    # TRIGGER (2024: single-muon HLT is IsoMu24)
    if not event.HLT_IsoMu24: return False
    self.cutflow.Fill(self.cut_trig)

    # SELECT MUON (offline pt threshold above the IsoMu24 plateau)
    muons = [ ]
    # TODO section 4: extend with a veto of additional muons. Veto muons should have the same (or looser)
    # quality selection as signal muons, but with a lower pt cut, e.g. muon.pt > 15.0
    veto_muons = [ ]
    for muon in Collection(event,'Muon'):
      good_muon = muon.mediumId and muon.pfRelIso04_all < 0.5 and abs(muon.eta) < 2.4
      signal_muon = good_muon and muon.pt > 26.0
      veto_muon   = False # TODO section 4: introduce a veto muon selection here
      if signal_muon:
        muons.append(muon)
      if veto_muon: # CAUTION: NOT an elif, intended!
        veto_muons.append(muon)
    if len(muons) == 0: return False
    self.cutflow.Fill(self.cut_muon)
    # TODO section 4: What should be the requirement to veto events with additional muons?
    self.cutflow.Fill(self.cut_muon_veto)

    # SELECT TAU (2024: DeepTau2018v2p5; VSjet/VSe/VSmu WP bits differ from the old 2017v2p1!)
    # TODO section 6: which decay modes should be considered? Extend the tau selection accordingly.
    taus = [ ]
    for tau in Collection(event,'Tau'):
      good_tau = (tau.pt > 20.0 and abs(tau.eta) < 2.3 and
                  tau.idDeepTau2018v2p5VSe >= 1 and tau.idDeepTau2018v2p5VSmu >= 1 and
                  tau.idDeepTau2018v2p5VSjet >= 1)
      if good_tau:
        taus.append(tau)
    if len(taus)<1: return False
    self.cutflow.Fill(self.cut_tau)

    # SELECT ELECTRONS FOR VETO
    # TODO section 4: extend the veto electron selection: pt > 15.0, loose WP of the mva-based ID
    # (Run3: Electron_mvaIso_WPL / mvaIso_WP90), and a custom PF isolation cut.
    electrons = []
    for electron in Collection(event,'Electron'):
      veto_electron = False # TODO section 4: introduce a veto electron selection here
      if veto_electron:
        electrons.append(electron)
    if len(electrons) > 0: return False
    self.cutflow.Fill(self.cut_electron_veto)

    # PAIR: highest-pt muon x highest-pt tau (see HTT pair-selection algorithm for the isolation-based variant)
    muon = max(muons,key=lambda p: p.pt)
    tau  = max(taus,key=lambda p: p.pt)
    if muon.DeltaR(tau)<0.4: return False
    self.cutflow.Fill(self.cut_pair)

    # SELECT JETS / b-tag (TODO section 4): pt>20, |eta|<4.7, jetID tight, dR>0.5 from mu & tau;
    # count jets with pt>30 and DeepJet-medium b-tags (|eta|<2.5). Not stored here yet.

    # MET (TODO section 4): compare PuppiMET vs PF MET; Run3 default is PuppiMET.
    puppimet = Met(event, 'PuppiMET')
    met = Met(event, 'MET')

    # SAVE VARIABLES
    # TODO section 4: extend with high-level quantities (Z pT, m_T(mu,MET), Dzeta, DeltaR, npv, nTrueInt).
    self.pt_1[0]        = muon.pt
    self.eta_1[0]       = muon.eta
    self.q_1[0]         = muon.charge
    self.id_1[0]        = muon.mediumId
    self.iso_1[0]       = muon.pfRelIso04_all # SMALLER = more isolated
    self.decayMode_1[0] = self.default_int    # not defined for a muon
    self.pt_2[0]        = tau.pt
    self.eta_2[0]       = tau.eta
    self.q_2[0]         = tau.charge
    self.decayMode_2[0] = tau.decayMode
    # --- DeepTau2018v2p5 ---
    self.idDeepTau2018v2p5VSjet_2[0]  = tau.idDeepTau2018v2p5VSjet
    self.idDeepTau2018v2p5VSe_2[0]    = tau.idDeepTau2018v2p5VSe
    self.idDeepTau2018v2p5VSmu_2[0]   = tau.idDeepTau2018v2p5VSmu
    self.rawDeepTau2018v2p5VSjet_2[0] = tau.rawDeepTau2018v2p5VSjet # HIGHER = more tau-like
    # --- PNet & UParT raw VSjet scores + decay modes (for the tagger comparison) ---
    self.rawPNetVSjet_2[0]   = getattr(tau,'rawPNetVSjet',  self.default_float)
    self.rawUParTVSjet_2[0]  = getattr(tau,'rawUParTVSjet', self.default_float)
    self.decayModePNet_2[0]  = getattr(tau,'decayModePNet', self.default_int)
    self.decayModeUParT_2[0] = getattr(tau,'decayModeUParT',self.default_int)
    self.m_vis[0]       = (muon.p4()+tau.p4()).M()

    if self.ismc:
      self.genmatch_1[0] = muon.genPartFlav # 1=prompt mu, 15=mu from tau, ...
      self.genmatch_2[0] = tau.genPartFlav  # 0=jet(unmatched), 1=prompt e, 2=prompt mu, 3=e from tau,
                                            #                   4=mu from tau, 5=genuine hadronic tau
      self.genWeight[0]  = event.genWeight
    self.tree.Fill()

    return True
