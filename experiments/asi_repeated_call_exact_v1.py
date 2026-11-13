"""Analytical bounds within the predeclared offer range, from saved inputs."""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'results/tables/asi_repeated_call_v1_non_authoritative/attempt_01'
p=folder/'report.json';raw=p.read_bytes();report=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()==(folder/'report.sha256').read_text().strip()
k_milli=round(report['quantized_reference_mw']*1000)
rows=[]
for x in report['rows']:
    if x['offer_level'] or x['status']!='evaluated':continue
    gap=x['gap'];jobs=x['jobs'];calls=(0,1,gap,gap+1)
    eligibility=min(4*k_milli,*(x['eligible_units'][h] for h in calls))
    bounds={}
    for mode,cap in [('chronological',x['actual_recovery_units']),
                     ('terminal_static',[0 if h in calls else 2*k_milli for h in range(32)])]:
        cuts=[]
        for ids in [(0,),(1,),(0,1)]:
            hours=set(h for j in ids for h in range(jobs[j][0],jobs[j][1]+1))
            cuts.append((F(sum(cap[h] for h in hours),2*len(ids)),ids))
        bounds[mode]=str(min(F(eligibility),*(v for v,ids in cuts))/4000)
        if mode=='chronological':
            bounds['separate_event']=str(min(F(eligibility),*(v for v,ids in cuts if len(ids)==1))/4000)
    key={k:x[k] for k in ['origin','gap','lag','stage']}
    for other in report['rows']:
        if all(other[k]==v for k,v in key.items()):
            for method in bounds:
                assert other[method]==(F(str(other['offer_mw']))<=F(bounds[method]))
    rows.append(dict(**key,bounds=bounds))
a={(r['origin'],r['gap'],r['lag']):r for r in rows if r['stage']==8}
b={(r['origin'],r['gap'],r['lag']):r for r in rows if r['stage']==16}
result=dict(authority='DRAFT_NONAUTHORITATIVE',source_sha256=hashlib.sha256(raw).hexdigest(),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    offer_domain_mw=[0,report['quantized_reference_mw']],
    formula='min(offer-domain ceiling, event eligibility, each Hall subset capacity / (2 * number of event debts))',
    repeat_conflict_count=sum(F(r['bounds']['separate_event'])>F(r['bounds']['chronological']) for r in rows),
    stage_pair_differences=sum(a[k]['bounds']['chronological']!=b[k]['bounds']['chronological'] for k in a),rows=rows)
target=folder/'exact_bounds.json'
if target.exists():raise FileExistsError(target)
data=json.dumps(result,indent=2).encode();target.write_bytes(data)
target.with_suffix('.sha256').write_text(hashlib.sha256(data).hexdigest())
print('exact bounds',len(rows),'repeat conflicts',result['repeat_conflict_count'],'stage differences',result['stage_pair_differences'])
