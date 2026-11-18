"""Independent local subset checker based on Cecilia's supplied v0.1 README.
NOT Cecilia's actual JSON Schema/checker or clinical validation.
"""
import argparse, json, math, re, sys
from pathlib import Path

def valid_number(x):
    return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)

def validate(x):
    errors=[]
    def check(ok,msg):
        if not ok: errors.append(msg)
    req=['schema_version','plan_id','modality','source','synthetic','prescription','rbe','structures','dvh','metrics','quality','provenance','prediction','flags']
    for k in req:check(k in x,f'missing {k}')
    check(x.get('schema_version')=='0.1','schema_version must be "0.1"')
    check(x.get('modality')=='electron','modality must be electron')
    check(isinstance(x.get('plan_id'),str) and bool(re.fullmatch(r'ELE-[A-Za-z0-9_]+-[0-9]+',x.get('plan_id',''))),'plan_id malformed')
    check(isinstance(x.get('source'),str) and bool(re.fullmatch('[a-z0-9_]+',x.get('source',''))),'source malformed')
    check(type(x.get('synthetic')) is bool,'synthetic must be boolean')
    p=x.get('prescription',{})
    check(isinstance(p,dict) and valid_number(p.get('dose')) and p['dose']>0 and p.get('unit')=='Gy' and (p.get('fractions') is None or type(p.get('fractions')) is int and p['fractions']>0),'prescription invalid')
    check(x.get('rbe')==1.0,'electron rbe must equal 1.0')
    structs=x.get('structures')
    check(isinstance(structs,list) and len(structs)>0,'structures must be nonempty list')
    names=[]
    if isinstance(structs,list):
      for s in structs:
        if not isinstance(s,dict):errors.append('structure not object');continue
        name=s.get('name');names.append(name)
        check(isinstance(name,str) and bool(name),'structure name invalid')
        check(isinstance(s.get('original_name'),str),'original_name invalid')
        check(s.get('type') in ('target','oar','other'),'type invalid')
        check(s.get('volume_cc') is None or valid_number(s['volume_cc']) and s['volume_cc']>=0,'volume_cc invalid')
    check(len(set(names))==len(names),'duplicate structures')
    dvhs=x.get('dvh');check(isinstance(dvhs,list),'dvh must be list')
    if isinstance(dvhs,list):
      for d in dvhs:
        if not isinstance(d,dict):errors.append('dvh not object');continue
        check(d.get('structure') in names,'dvh structure unknown')
        check(d.get('dose_unit')=='Gy','dvh dose_unit must be Gy')
        ds=d.get('dose');vs=d.get('volume_pct')
        check(isinstance(ds,list) and isinstance(vs,list) and len(ds)==len(vs) and len(ds)>1,'dvh arrays malformed')
        if isinstance(ds,list) and isinstance(vs,list) and ds and vs:
          check(all(valid_number(z) for z in ds+vs),'dvh nonnumeric')
          if all(valid_number(z) for z in ds+vs):
            check(ds[0]==0 and vs[0]==100,'dvh must begin at 0 Gy/100%')
            check(all(a<=b for a,b in zip(ds,ds[1:])),'dvh doses nonascending')
            check(all(a>=b for a,b in zip(vs,vs[1:])),'dvh volume increasing')
            check(all(0<=v<=100 for v in vs),'dvh percentage out of range')
    metrics=x.get('metrics');check(isinstance(metrics,list),'metrics must be list')
    if isinstance(metrics,list):
      for m in metrics:
        if not isinstance(m,dict):errors.append('metric not object');continue
        check(m.get('structure') in names,'metric structure unknown')
        check(isinstance(m.get('name'),str),'metric name invalid')
        check(valid_number(m.get('value')),'metric value invalid')
        check(m.get('unit') in ('Gy','%','cm³','mm'),'metric unit invalid')
        check(m.get('pct_rx') is None or valid_number(m['pct_rx']),'metric pct_rx invalid')
        if m.get('unit')=='%' : check(m.get('pct_rx') is None,'volume metric pct_rx should be null')
    check(x.get('prediction') is None,'prediction must be null for this experiment')
    check(x.get('flags')==[],'flags must be [] for this experiment')
    q=x.get('quality');check(isinstance(q,dict) and q.get('status') in ('usable','quarantined') and isinstance(q.get('issues'),list),'quality invalid')
    if isinstance(q,dict):
      if q.get('status')=='quarantined':check(bool(q.get('issues')),'quarantined requires issues')
      if q.get('status')=='usable':check(q.get('issues')==[],'usable requires empty issues')
    prov=x.get('provenance');check(isinstance(prov,dict) and all(k in prov for k in ('created','created_by','software')),'provenance missing')
    electron=x.get('electron')
    check(electron is None or isinstance(electron,dict),'electron must be null or object')
    # CANNOT check structure whitelist, official schema, medical accuracy, or real dataset consistency.
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('paths',nargs='+');args=p.parse_args()
    files=[]
    for item in args.paths:
      q=Path(item)
      files.extend(sorted(q.glob('*.json')) if q.is_dir() else [q])
    status=0
    for f in files:
      try: errors=validate(json.loads(f.read_text()))
      except Exception as exc:errors=[str(exc)]
      print(('PASS' if not errors else 'FAIL')+': '+str(f))
      for e in errors:print('  - '+e)
      status |= bool(errors)
    sys.exit(status)
if __name__=='__main__':main()
