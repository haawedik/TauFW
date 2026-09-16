# CMSDAS 2026 — Tau long exercise

Measure the **Z → τ τ cross-section** in the μτ_h final state with **2024 (Run 3, 13.6 TeV)** CMS data,
and along the way **measure and apply the τ_h energy scale (TES) and τ_h identification (TauID) scale
factors** and **compare the three tau taggers** (DeepTau2018v2p5, ParticleNet, UParT). Modelled on the
original CMSDAS2020 exercise (2018), updated to the latest TauFW / LCG / Combine and to 2024 samples.

## What you will learn
- Find CMS datasets in **DAS**.
- Produce **flat n-tuples** from NanoAOD with TauFW's `PicoProducer` (demo on one sample; pre-made 2024
  n-tuples are provided for the rest).
- **Normalize** MC to data and estimate **QCD multijet** from the same-sign region (OS/SS method).
- Apply Run-3 **corrections** (pileup, muon SF, τ ES/ID) via `correctionlib`.
- **Compare** the three tau taggers and pick the best (genuine-τ efficiency vs jet→τ fake rate).
- Measure and apply **TauID + TES scale factors** — Tier A at plot level, Tier B with a Combine fit.
- Build **datacards** and run **Combine** to extract the **Z→ττ cross-section**, and cross-check it
  against the **Z→μμ cross-section** (lepton universality).

## Software
Single modern area: **`CMSSW_14_1_0_pre4`** (el9) with **Combine v10** — no separate combine release. See
[sw_setup.md](sw_setup.md).

## Steps
1. [Software setup](sw_setup.md)
2. [Configuration](configuration.md)
3. [Finding samples in DAS](das_samples.md)
4. [Flat n-tuples](flat_n-tuples.md)
5. [Normalization, QCD & corrections](norm_and_corr.md)
6. [Tagger comparison](tagger_comparison.md)
7. [TauID + TES scale factors](tauid_es.md)
8. [Datacards](datacards.md)
9. [The measurement (Z→ττ xsec, Z→μμ cross-check)](measurement.md)
10. [Presentation](presentation.md)

Reference: the 2.3 fb⁻¹ Z→ττ paper, [doi:10.1140/epjc/s10052-018-6146-9](https://doi.org/10.1140/epjc/s10052-018-6146-9).
