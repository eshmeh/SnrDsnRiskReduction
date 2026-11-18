# Plan-summary format, v0.1

Each plan you contribute (proton, photon or electron) goes into **one JSON file** in this format. The dashboard and the checker both read it. You don't need to read `plan-summary.schema.json`. This page covers everything in it.

**Before you send files, run the checker:**

```
python tools/check_plan.py path/to/your/folder
```

## Ground rules

- **No patient information, ever.** No names, MRNs, dates of birth, treatment dates or DICOM UIDs. The file rejects any top-level field it doesn't recognise, so identifying data can't slip in unnoticed.
- **Write the numbers your source reports.** Don't rescale or round them for the dashboard. It shows exactly what's in the file.
- **Units are fixed:** proton doses use `Gy(RBE)`, photon and electron doses use `Gy`, volumes in a DVH use `%`, and structure volumes use cm³.
- If you don't know a value, use `null` where this page allows it. Don't guess.

## Fields

(R) means required.

### Identity

| Field | What to put |
|---|---|
| `schema_version` (R) | Always the text `"0.1"` (a string, not a number). |
| `plan_id` (R) | A unique ID that you make up. Use letters, digits, `-` and `_`. The pattern is `<MODALITY>-<SOURCE>-<NUMBER>`, e.g. `PRO-MENTOR-007` or `PHO-OPENKBP-0213`. Never derive it from a patient ID. |
| `modality` (R) | `"proton"`, `"photon"` or `"electron"`. |
| `source` (R) | Where the plan came from, in lower case: `"mentor"`, `"openkbp"`, `"opentps_synthetic"`, … Use the same spelling for every file from that source, because the inventory groups by it. |
| `synthetic` (R) | `true` if the plan was generated or simulated, `false` if it is a real (de-identified) clinical plan. Synthetic plans get a "Synthetic" badge. |
| `site` | Treatment site in snake_case, e.g. `"head_and_neck"`, `"abdomen"`, `"scalp"`. |

### Prescription and RBE

| Field | What to put |
|---|---|
| `prescription` (R) | `{ "dose": 70, "unit": "Gy(RBE)", "fractions": 35 }`. `dose` is the total primary prescription. `unit` is `"Gy(RBE)"` for proton and `"Gy"` otherwise. `fractions` is a whole number, or `null` if unknown. |
| `rbe` (R) | `1.1` for proton and `1.0` for photon and electron. The checker warns if `rbe` or the unit doesn't match the modality. |

### Structures

`structures` (R) lists every structure that appears in `dvh` or `metrics`.

| Key | What to put |
|---|---|
| `name` | The standard name from [`structure-names.json`](structure-names.json), e.g. `Parotid_L`, `SpinalCord`, `PTV_7000`. That file lists common source spellings as `aliases`. If a name is missing from the list, ask Cecilia to add it rather than inventing one. The checker warns about names that aren't on the list. |
| `original_name` | The name exactly as it appeared in your source, e.g. `"LeftParotid"`. This keeps the mapping traceable. |
| `type` | `"target"`, `"oar"` (organ at risk) or `"other"` (e.g. `External`). |
| `volume_cc` | The volume in cm³, or `null` if unknown. |

### DVH

`dvh` (R) holds one cumulative DVH per structure:

| Key | What to put |
|---|---|
| `structure` | Must match a `structures[].name`. |
| `dose_unit` | `"Gy(RBE)"` (proton), `"Gy"` (photon and electron), or `"%Rx"` if your source only gives dose as a percent of prescription. |
| `dose` | Dose values, **ascending**, starting at 0. |
| `volume_pct` | Percent of the structure receiving at least that dose. It starts at 100 and only goes down. It must be the **same length** as `dose`. |

### Metrics

`metrics` (R) lists the dose metrics as your source reports them:

| Key | What to put |
|---|---|
| `structure` | Must match a `structures[].name`. |
| `name` | `"D95"`, `"D2"`, `"Dmean"`, `"Dmax"`, `"V20"`, etc. `Dxx` is the dose to the hottest xx % of the volume. `Vxx` is the % of volume receiving at least xx Gy (or Gy(RBE)). |
| `value` | The number. |
| `unit` | One of `"Gy"`, `"Gy(RBE)"`, `"%"`, `"cm³"`, `"mm"`. Dose metrics use the prescription unit, and `V` metrics use `"%"`. |
| `pct_rx` | `value` as a percent of `prescription.dose` (e.g. 68.6 Gy on a 70 Gy plan is `98.0`). Use `null` for metrics that aren't doses, such as V20. |

### Model output (leave empty for now)

| Field | What to put |
|---|---|
| `prediction` | `null`. There's no model yet. Later this becomes `{ "model": "name vX", "ranges": [ { "structure", "name", "lower", "upper" } ] }`. |
| `flags` | `[]`. Later each item is `{ "structure", "metric", "status": "pass" or "review" or "flag", "reason" }`. |

### Quality and provenance

| Field | What to put |
|---|---|
| `quality` (R) | `{ "status": "usable", "issues": [] }`. If something is wrong but you still want the plan visible, set `"status": "quarantined"` and describe each problem in plain words in `issues` (at least one is required). |
| `provenance` (R) | `{ "created": "2026-11-15", "created_by": "your name or script", "software": { "OpenTPS": "2.0.1" }, "notes": "..." }`. `created` is the date you made the file (YYYY-MM-DD), **not** a treatment date. `notes` is optional. |

### Electron fields (proposed)

| Field | What to put |
|---|---|
| `electron` | `null` (or leave it out) for proton and photon. For electron, it's currently proposed as `{ "energy_mev": 9, "applicator": "10x10", "ssd_cm": 100, "R90_mm": 27 }`. **The Electron Lead owns this block.** Extra keys are allowed here until it is agreed. |

## Full example

This is a small but complete, valid proton file. Real DVHs have many more points.

```json
{
  "schema_version": "0.1",
  "plan_id": "PRO-MENTOR-007",
  "modality": "proton",
  "source": "mentor",
  "synthetic": false,
  "site": "head_and_neck",
  "prescription": { "dose": 70, "unit": "Gy(RBE)", "fractions": 35 },
  "rbe": 1.1,
  "structures": [
    { "name": "PTV_7000",  "original_name": "PTV 70",     "type": "target", "volume_cc": 212.4 },
    { "name": "Parotid_L", "original_name": "Lt_Parotid", "type": "oar",    "volume_cc": 27.9 }
  ],
  "dvh": [
    {
      "structure": "PTV_7000",
      "dose_unit": "Gy(RBE)",
      "dose":       [0,   60,   66,   68,   70,   72,   74],
      "volume_pct": [100, 100,  99.6, 97.1, 62.0, 8.3,  0]
    },
    {
      "structure": "Parotid_L",
      "dose_unit": "Gy(RBE)",
      "dose":       [0,   10,   20,   30,   40,   50,  60],
      "volume_pct": [100, 71.5, 42.0, 18.4, 7.2,  1.9, 0]
    }
  ],
  "metrics": [
    { "structure": "PTV_7000",  "name": "D95",   "value": 68.4, "unit": "Gy(RBE)", "pct_rx": 97.7 },
    { "structure": "PTV_7000",  "name": "D2",    "value": 73.1, "unit": "Gy(RBE)", "pct_rx": 104.4 },
    { "structure": "Parotid_L", "name": "Dmean", "value": 18.2, "unit": "Gy(RBE)", "pct_rx": 26.0 },
    { "structure": "Parotid_L", "name": "V30",   "value": 18.4, "unit": "%",       "pct_rx": null }
  ],
  "prediction": null,
  "flags": [],
  "quality": { "status": "usable", "issues": [] },
  "provenance": {
    "created": "2026-11-15",
    "created_by": "Proton Lead",
    "software": { "OpenTPS": "2.0.1", "export_script": "0.3" },
    "notes": "Exported from mentor's de-identified research set."
  },
  "electron": null
}
```

For more examples, see `public/data/`, generated by `python tools/make_examples.py`.

## Changing the format

The schema is shared by all four of us. To request a change, message Cecilia rather than editing the file. Each change bumps `schema_version`.
