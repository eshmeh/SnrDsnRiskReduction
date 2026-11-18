"""SP07 electron data triage and v0.1 plan-summary exporter.

Only use de-identified, precomputed metrics and DVHs. Does NOT infer or
calculate dose from DICOM, establish plan usability, or contact any service.
Final dashboard acceptance must be checked with Cecilia's tools/check_plan.py.
"""
import argparse
import csv
import json
import math
import re
from datetime import date
from pathlib import Path

FIELDS = ['case_folder','electron_beams','plan_files','structure_files','dose_files','status','blockers']

def scan(root, output):
    try:
        import pydicom
    except ImportError as exc:
        raise SystemExit('Install pydicom: pip install pydicom') from exc
    root = Path(root)
    if not root.is_dir():
        raise SystemExit('Input must be an extracted local directory')
    groups = {}
    for file in root.rglob('*'):
        if not file.is_file():
            continue
        try:
            d = pydicom.dcmread(str(file), stop_before_pixels=True, force=False)
        except Exception:
            continue
        modality = str(getattr(d, 'Modality', '')).upper()
        if modality not in ('RTPLAN', 'RTSTRUCT', 'RTDOSE'):
            continue
        # Conservative grouping by folder, not patient identifiers.
        folder = str(file.parent.relative_to(root))
        g = groups.setdefault(folder, {'plans': 0, 'structures': 0, 'doses': 0, 'electrons': 0})
        if modality == 'RTPLAN':
            g['plans'] += 1
            for beam in getattr(d, 'BeamSequence', []):
                if str(getattr(beam, 'RadiationType', '')).upper() == 'ELECTRON':
                    g['electrons'] += 1
        elif modality == 'RTSTRUCT':
            g['structures'] += 1
        else:
            g['doses'] += 1
    rows = []
    for folder, g in sorted(groups.items()):
        if not g['electrons']:
            continue
        blockers = []
        if not g['structures']:
            blockers.append('RTSTRUCT not found in same directory')
        if not g['doses']:
            blockers.append('RTDOSE not found in same directory')
        blockers.append('DICOM relationships, prescription, dose grid, target and DVH not verified')
        rows.append(dict(case_folder=folder, electron_beams=g['electrons'],
                         plan_files=g['plans'], structure_files=g['structures'],
                         dose_files=g['doses'], status='CANDIDATE_NOT_VERIFIED',
                         blockers='; '.join(blockers)))
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'Electron-containing directory groups: {len(rows)}; usable verified: 0; saved {out}')


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def convert(src, dst):
    """Convert locally prepared, de-identified values into Cecilia's v0.1 shape.

    Does not assert clinical validity. Input structure names MUST be approved
    externally against Cecilia's structure-names.json; this file is not supplied.
    """
    data = json.loads(Path(src).read_text())
    for field in ('plan_id', 'source', 'synthetic', 'prescription_Gy', 'structures'):
        ensure(field in data, f'Missing input field: {field}')
    ensure(data.get('modality', 'electron') == 'electron', 'modality must be electron')
    ensure(isinstance(data['synthetic'], bool), 'synthetic must be boolean')
    ensure(bool(re.fullmatch(r'[A-Za-z0-9_-]+', data['plan_id'])), 'plan_id must be letters/digits/-/_')
    ensure(bool(re.fullmatch(r'ELE-[A-Za-z0-9_-]+-[0-9]+', data['plan_id'])),
           'plan_id must follow ELE-SOURCE-NUMBER pattern')
    ensure(isinstance(data['source'], str) and bool(re.fullmatch(r'[a-z0-9_]+', data['source'])),
           'source must be a lowercase source key')
    rx = data['prescription_Gy']
    ensure(number(rx) and rx > 0, 'prescription_Gy must be positive finite')
    fractions = data.get('fractions')
    ensure(fractions is None or (type(fractions) is int and fractions > 0),
           'fractions must be positive integer or null')
    ensure(isinstance(data['structures'], list) and data['structures'], 'nonempty structures required')
    result_structures, result_dvh, result_metrics = [], [], []
    names = set()
    for s in data['structures']:
        name, original = s.get('name'), s.get('original_name')
        ensure(isinstance(name, str) and bool(name), 'approved structure name required')
        ensure(name not in names, f'duplicate structure {name}')
        names.add(name)
        ensure(isinstance(original, str) and bool(original), 'original_name required')
        kind = s.get('type')
        ensure(kind in ('target', 'oar', 'other'), 'structure type must be target/oar/other')
        vol = s.get('volume_cc')
        ensure(vol is None or (number(vol) and vol >= 0), 'volume_cc must be nonnegative or null')
        result_structures.append({'name': name, 'original_name': original,
                                  'type': kind, 'volume_cc': vol})
        dvh = s.get('dvh')
        ensure(isinstance(dvh, list) and len(dvh) >= 2, 'at least two DVH [dose, volume_pct] points required')
        for p in dvh:
            ensure(isinstance(p, list) and len(p) == 2 and all(number(x) for x in p),
                   'every DVH point must be two finite numbers')
        dose, volume = [p[0] for p in dvh], [p[1] for p in dvh]
        ensure(dose[0] == 0 and volume[0] == 100, 'DVH must start at [0,100]')
        ensure(all(a <= b for a, b in zip(dose, dose[1:])), 'DVH dose must ascend')
        ensure(all(0 <= x <= 100 for x in volume), 'DVH volumes must be 0-100')
        ensure(all(a >= b for a, b in zip(volume, volume[1:])), 'DVH volume must not increase')
        result_dvh.append({'structure': name, 'dose_unit': 'Gy',
                           'dose': dose, 'volume_pct': volume})
        metric_dict = s.get('metrics_Gy', {})
        ensure(isinstance(metric_dict, dict), 'metrics_Gy must be an object')
        for metric, value in metric_dict.items():
            ensure(metric in ('D95', 'D2', 'Dmean', 'Dmax') or re.fullmatch(r'D\d+', metric),
                   f'unsupported dose metric {metric}; use D95/D2/Dmean/Dmax/Dxx')
            ensure(number(value) and value >= 0, f'invalid metric {metric}')
            result_metrics.append({'structure': name, 'name': metric, 'value': value,
                                   'unit': 'Gy', 'pct_rx': 100 * value / rx})
        for metric, value in s.get('metrics_volume_pct', {}).items():
            ensure(bool(re.fullmatch(r'V\d+', metric)), f'invalid volume metric {metric}')
            ensure(number(value) and 0 <= value <= 100, f'invalid {metric}')
            result_metrics.append({'structure': name, 'name': metric, 'value': value,
                                   'unit': '%', 'pct_rx': None})
    electron = data.get('electron')
    ensure(electron is None or isinstance(electron, dict), 'electron metadata must be an object or null')
    if electron is not None:
        for key in electron:
            ensure(key in ('energy_mev', 'applicator', 'ssd_cm', 'R90_mm'),
                   f'unapproved electron metadata key: {key}')
    quality = data.get('quality', {'status': 'quarantined', 'issues': ['Synthetic interface demonstration; not a verified treatment plan']})
    ensure(isinstance(quality, dict) and quality.get('status') in ('usable', 'quarantined'),
           'quality must contain usable/quarantined status')
    ensure(isinstance(quality.get('issues'), list), 'quality.issues must be a list')
    if quality['status'] == 'quarantined':
        ensure(bool(quality['issues']), 'quarantined plan requires at least one issue')
    if quality['status'] == 'usable':
        ensure(not quality['issues'], 'usable plans cannot have issues')
        ensure(not data['synthetic'] or data.get('synthetic_verified') is True,
               'demo synthetic data cannot be marked usable without external verification')
    source_note = data.get('notes', 'De-identified source values; independent clinical validation not performed by exporter.')
    ensure(isinstance(source_note, str), 'notes must be text')
    result = {
        'schema_version': '0.1', 'plan_id': data['plan_id'], 'modality': 'electron',
        'source': data['source'], 'synthetic': data['synthetic'],
        'site': data.get('site'),
        'prescription': {'dose': rx, 'unit': 'Gy', 'fractions': fractions},
        'rbe': 1.0, 'structures': result_structures, 'dvh': result_dvh,
        'metrics': result_metrics, 'prediction': None, 'flags': [],
        'quality': quality,
        'provenance': {'created': date.today().isoformat(), 'created_by': 'SP07 Electron Lead converter',
                       'software': {'electron_pipeline': '0.2'}, 'notes': source_note},
        'electron': electron
    }
    output = Path(dst)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'Wrote v0.1-shaped electron summary (NOT schema-checker validated): {output}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command', required=True)
    s = subs.add_parser('scan'); s.add_argument('input_dir'); s.add_argument('output_csv')
    c = subs.add_parser('convert'); c.add_argument('input_json'); c.add_argument('output_json')
    a = p.parse_args()
    if a.command == 'scan':
        scan(a.input_dir, a.output_csv)
    else:
        convert(a.input_json, a.output_json)

if __name__ == '__main__':
    main()
