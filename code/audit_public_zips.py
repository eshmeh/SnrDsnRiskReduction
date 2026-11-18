"""Offline, privacy-preserving DICOM modality census of ZIP archives.

Uses only standard library. Counts (0008,0060) Modality for each member;
no names, UIDs, dates, or other metadata are printed or saved.
This is NOT a clinical validation or a complete DICOM parser.
"""
import argparse,csv,json,struct,zipfile
from collections import Counter
from pathlib import Path

MODALITY_TAG = b'\x08\x00\x60\x00'

def get_modality(blob):
    # Both provided datasets use little-endian implicit-VR data sets.
    # The metadata value uses a 32-bit length following the tag.
    pos = blob.find(MODALITY_TAG)
    if pos == -1: return 'UNREADABLE'
    # Also supports explicit VR CS when encountered.
    if blob[pos+4:pos+6] == b'CS':
        length = struct.unpack_from('<H', blob, pos+6)[0]
        start = pos+8
    else:
        length = struct.unpack_from('<I', blob, pos+4)[0]
        start = pos+8
    if length > 32 or start+length > len(blob): return 'UNREADABLE'
    return blob[start:start+length].decode('ascii', errors='replace').strip() or 'UNREADABLE'

def audit(path):
    path=Path(path)
    with zipfile.ZipFile(path) as z:
        files=[i for i in z.infolist() if not i.is_dir()]
        counts=Counter()
        for info in files:
            with z.open(info) as file:
                # Modality tag is in the early part of the datasets in these archives
                counts[get_modality(file.read(min(info.file_size, 32768)))] += 1
    return {
        'archive': path.name,
        'total_files': len(files),
        'CT': counts['CT'], 'RTPLAN': counts['RTPLAN'],
        'RTSTRUCT':counts['RTSTRUCT'], 'RTDOSE':counts['RTDOSE'],
        'unreadable_or_other':len(files)-sum(counts[k] for k in ('CT','RTPLAN','RTSTRUCT','RTDOSE')),
        'dose_based_usable_cases':0,
        'blocker':'No RTDOSE objects in uploaded archive; no source dose grid for real DVH/metrics'
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('zips',nargs='+');p.add_argument('--output',default='results/public_zip_audit.csv')
    a=p.parse_args(); rows=[audit(x) for x in a.zips]
    out=Path(a.output);out.parent.mkdir(exist_ok=True,parents=True)
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for row in rows:print(json.dumps(row,indent=2))
    print('Saved',out)
if __name__=='__main__':main()
