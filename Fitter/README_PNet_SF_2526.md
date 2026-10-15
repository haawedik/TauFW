# Full-PNet 2526 TES + TauID scale factors — how to run

Measures tau **energy-scale (TES)** and **ID (TauID) scale factors** for the **full-ParticleNet** tagger
(VSjet + VSe + VSmu all on PNet raw scores, PNet decay modes) on **2526** (2025+2026 combined, L ≈ 135.48 fb⁻¹),
in the µτ_h channel, **anchored by a Z→µµ control region** (fixes the DY normalisation).

Everything runs from `Fitter/`. Main config: `TauES_ID/config/config_coarse_TT_pnet.yml`.

---

## Design

**Decay-mode categories** (PNet DM) × **pT bins** of `pt_2*ptCorrPNet_2` (the single PNet-corrected tau pT):

| DM | definition | pT bins |
|----|------------|---------|
| DM0 | `decayModePNet_2==0` (h±) | pt1 20–40, pt2 40–60, pt3 60–200 |
| DM1 | `decayModePNet_2==1\|\|2` (h±π⁰) | pt1, pt2, pt3 |
| DM10 | `decayModePNet_2==10` (3h±) | pt1, pt2, pt3 |
| DM11 | `decayModePNet_2==11` (3h±π⁰) | pt1, pt2, pt3 |
| recovAllDMs | `!idDecayModeNewDMs_2` (HPS-invalid, PNet-recovered) | **one inclusive bin 20–200** |

**m_vis binning** (per region, in the config): default **5 GeV** `[22,40,150]`; **10 GeV** `[11,40,150]` for the
stats-thin regions — every `pt3`, all of `DM11`, and `recovAllDMs`. `createinputsTES_pnet.py` honours the
per-region `binning:` key, so a fresh inputs build already produces the right binning (no manual rebinning).

**WP sweep** (10 cells): VSjet `{Loose, Medium, Tight, VTight, VVTight}` × VSe `{Tight 0.9897, VVLoose 0.3547}`;
VSmu fixed `Tight 0.9451`. Official PNet raw-score thresholds live in the `tagger:` block of the config.

**Fit (per DM, with the Zmm CR):** one correlated `tes_<DM>` POI + one `tid_SF_<region>` POI per pT bin.
See *Fit method* below for how the central value is extracted.

---

## 0. Setup (every fresh shell)

```sh
cd ~/CMSSW_14_1_0_pre4/src && cmsenv && cd TauFW-pnet/Fitter
# for condor only:
source condor/make_proxy.sh afs               # grid proxy (enter passphrase), valid ~192 h
export RELEASE_SRC=$HOME/CMSSW_14_1_0_pre4/src
export FITTER_DIR=$RELEASE_SRC/TauFW-pnet/Fitter
```

Prereq: the 2526 pico at `/eos/cms/store/group/phys_tau/TauFW/pico2024/TES_variations/2526/`
(symlink → 2025) with the PNet branches (`decayModePNet_2`, `ptCorrPNet_2`, `rawPNetVS{jet,e,mu}_2`) and the
`_TES*/_LTF*/_JTF*` shifted samples.

---

## 1. Build inputs

Config-driven (correct binning + the inclusive recov region come straight from the config).

```sh
cd condor
condor_submit inputs.sub          # 50 jobs = 5 DM × 5 VSjet × 2 VSe  (16 threads each)
condor_submit mumu.sub            # 1 job: builds the Zmm CR once, symlinks it into every WP×VSe dir
condor_q                          # wait until both clusters drain
bash merge_inputs.sh              # hadd per-DM → one mutau inputs file per WP×VSe
cd ..
```
Local alternative (no condor): `bash run_inputs_pnet_2526.sh`.
Outputs land in `input_pt_less_region_pnet/againstjet_<J>/againstelectron_<E>/`.

---

## 2. Fit + 3. Merge  — one submit

```sh
cd condor
condor_submit_dag pipeline.dag    # node 'fit' (10 cells) → node 'merge' (runs once fits finish)
```
`pipeline.dag` chains `fit.sub` → `merge.sub`. The **merge** node produces the combined JSON, the scan
grids, and the 1D NLL profiles. Watch it with `condor_q -dag` / the `*.dagman.out` log.

Or run the two stages by hand:

```sh
cd condor
condor_submit fit.sub             # 10 jobs, one per VSjet×VSe: per-DM MultiDimFit (+boost+best-fit), postfit, createroot
condor_q                          # wait until gone
condor_submit merge.sub           # cross-WP: scan grids + NLL + merge_tau_jsons (+ make_tid)
cd ..
```
Local alternative (all cells sequentially, then merge): `bash run_workflow_zmm_corrTES_pnet_2526.sh`.

**Result:** `tau_sf/TauCorrections_2526_corrTES_pnet.json` — corrections `TauES_2526_corrTES` and
`TauIdSF_2526_corrTES`, schema inputs `genmatch, dm, pt, syst, wp_VSmu, wp_VSe, wp_VSjet`
(`dm`: -1 = recovAllDMs, 0, 1, 10, 11). Per-cell files:
`tau_sf/Tau{ES,ID}_SF_dm_PNet_2526_corrTES_VSjet<J>_VSele<E>.{root,json}`.
Scan grids: `plots_pt_less_region_corrTES_pnet/againstjet_<J>/againstelectron_<E>/2526/grid_corr_*.png`.

---

## 4. Inspect

```sh
PYTHONNOUSERSITE=1 python3 -c "from correctionlib import CorrectionSet; \
  cs=CorrectionSet.from_file('tau_sf/TauCorrections_2526_corrTES_pnet.json'); \
  tes=cs['TauES_2526_corrTES']; tid=cs['TauIdSF_2526_corrTES']; \
  print('DM0 TES', tes.evaluate(5,0,50.,'nom','Tight','VVLoose','Tight'))"

# re-make the scan grids by hand (merge.sub does this automatically):
python3 make_scan_grid.py --variant corr --root plots_pt_less_region_corrTES_pnet \
  --dms DM0,DM1,recovAllDMs,DM10,DM11
```

---

## Fit method (per region)

Each 2D scan is `combine -M MultiDimFit --algo grid --points=1600` over `tes_<DM>` × `tid_SF_<region>`
(TES 0.95–1.05; TauID 0.7–1.2, DM11 0.5–1.2), with the other POIs profiled and the Zmm CR merged in.

1. **Grid scan + boost loop** — up to 6 passes; each pass re-seeds from the deepest grid point if a deeper
   basin was found. Reused if the scan ROOT already exists (set `REFIT_SCAN=1` to force a rescan).
2. **Seeded best-fit** — a `combine -M MultiDimFit --algo none` seeded at the deepest grid point slides
   continuously into that basin → the **central value** (stable, not a quantised/flip-flopping grid node).
   Disable with `NO_BESTFIT=1`.
3. **1σ band** comes from the grid (ΔNLL ≤ 0.5), clamped to bracket the best-fit central.
4. **Boundary-rail fallback** — if the best-fit rails to a scan-range edge (an unconstrained direction),
   revert that POI to the interior grid node.

The 2D grid PNG shows the true likelihood (so a genuine degeneracy still *looks* double-welled); the
reported number is the best-fit.

### Recovery taus (recovAllDMs) — TES is not measurable
Recovery taus are HPS-invalid, so their m_vis is smeared with no sharp Z peak. TES shifts that peak, so with
no peak the TES likelihood is flat and trades fully against TauID — the fit rails `tes_recovAllDMs` to the
range edge in roughly half the WP cells, regardless of pT binning or pooling (confirmed: one inclusive
region still rails). The TauID SF (just the yield) *is* constrained.
- **Current (option A):** `tes_recovAllDMs` floats → railed/edge values, and the recov TauID SF is
  contaminated. Treat recov TES as unreliable.
- **Recommended (option B):** fix `tes_recovAllDMs = 1.0` and float only `tid_SF_recovAllDMs`. (Not yet
  wired — needs the fit to freeze the recov TES POI.)

---

## Config knobs

- **Binning:** per-region `binning:` key in `config_coarse_TT_pnet.yml` (`[nbins, lo, hi]`). Default from
  `observables.m_vis.binning`.
- **Regions / DMs:** the `regions:` block + `plottingOrder` / `fitRegions` / `scanRegions` (aliased to
  `&region_list`). `config_coarse_TT_pnet_recovonly.yml` is the same config restricted to recov, for a
  targeted recov-only re-fit (`condor/recov_fit.sub`).
- **WP sweep:** the `queue` lists in `condor/inputs.sub` + `condor/fit.sub`, and `J_VALUES/E_VALUES` in the
  `run_*` scripts.

### Env flags
| flag | effect |
|------|--------|
| `REFIT_SCAN=1` | force a fresh grid scan instead of reusing the existing ROOT |
| `NO_BESTFIT=1` | skip the seeded MIGRAD; take the central from the grid node |
| `PER_WP_ONLY=1` | run only the per-cell chain (harvest + fit + postfit + createroot) — used by `fit.sub` |
| `MERGE_ONLY=1` | run only the cross-WP merge (grids + NLL + JSON + make_tid) — used by `merge.sub` |

---

## Troubleshooting

- **Condor jobs crash at import** (`Address already in use`): TauFW's `Plotter/python/plot/MultiThread.py`
  opens a `multiprocessing.Manager()` AF_UNIX socket at import, which overflows condor's long scratch
  `$TMPDIR`. Every condor wrapper exports a short one: `export TMPDIR=$(mktemp -d /tmp/pnet.XXXXXX)`.
- **Jobs HELD "Disk quota exceeded":** combine stdout fills the 10 GB AFS quota. Delete `condor/logs/*.out`
  and `step*.log` (not pipeline data), then `condor_release`. The fit/merge watchers do this periodically.
- **correctionlib `undefined symbol: __cxa_call_terminate`:** a broken `~/.local` correctionlib shadows the
  release. Prefix every correctionlib step with `PYTHONNOUSERSITE=1` (already done in the workflow for
  `createroot -f json`, `merge_tau_jsons`, `make_tid`). Permanent cure: `pip uninstall correctionlib`.
- **make_tid is deferred:** `make_tid_2025.py` (secondary combined-SF packaging) is hardcoded for the old
  4-DM × 4-pT layout, so it does not emit for this DM12 config. It is made non-fatal in the workflow — grids
  and the merged JSON are produced before it runs.
