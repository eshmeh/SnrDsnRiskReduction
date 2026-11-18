# Actual-source verification log — November 17, 2026

## Method
The team uploaded the original `ECT-Nose.zip` and `ECT-Chestwall.zip` archives from .decimal. We enumerated **every file** and examined the DICOM `(0008,0060)` Modality tag, including files with `.img` extensions. Only aggregate modality counts were recorded; no patient identifiers, UIDs, dates or image data were included in any output. The standard-library script `code/audit_public_zips.py` reproduces the audit with the two ZIPs available locally.

| Archive | Total | CT | RTPLAN | RTSTRUCT | RTDOSE | Status |
|---|---:|---:|---:|---:|---:|---|
| ECT-Nose.zip | 124 | 122 | 1 | 1 | **0** | Electron planning example; missing calculated dose |
| ECT-Chestwall.zip | 154 | 152 | 1 | 1 | **0** | Electron planning example; missing calculated dose |
| **Total** | **278** | **274** | **2** | **2** | **0** | **0 dose-based usable** |

**Important:** These contain RTPLAN objects; they are *not* empty or fake. Their published descriptions identify electron treatments (nose 9 MeV, chestwall 12 MeV). We have not recalculated treatment dose or independently validated beam prescriptions or DICOM references. **Absence of RTDOSE** is sufficient to block conversion to an authentic, populated v0.1 `dvh` and `metrics` output, since no calculated voxel dose is supplied. A user cannot responsibly fabricate DVH values from these inputs.

## Count definitions
- Cases found: **2** RTPLAN examples located and audited. This is a count of candidate planning examples, not 278 individual cases.
- Verified dose-based usable cases: **0**.
- Mentor-provided: **0**, per Electron Lead/team statement.
- Synthetic module fixture: **1**, deliberately quarantined; excluded from clinical/usable counts.

## Other researched sources
- eFLASH Beam Model to TPS: beam/Monte Carlo model, not established as complete clinically compatible plan library.
- Strathclyde VHEE FLUKA simulations: water-phantom dose simulations rather than clinical electron-plan sets.
- DoseRAD2026 and TCIA HNC IMRT: comparison datasets not established as clinical electron datasets.
Source URLs, conditions and uncertainties: `results/source_survey.csv`.

## Limits
No RTDOSE in either supplied ZIP; this does **not** prove electron treatment datasets do not exist elsewhere or prevent future dose recalculation with appropriate software and commissioning data. No real clinical dose was generated. Cecilia's official checker/dashboard code was not supplied, and acceptance by those exact implementations was not tested. Dataset access does not automatically confer unrestricted reuse; verify licensing before redistribution. Original DICOM archives are **not bundled** to avoid redistributing potentially identifying source material.
