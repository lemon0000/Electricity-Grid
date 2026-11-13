"""Derive minimum firm menu entries from the saved bounded probe."""
from pathlib import Path
import hashlib
import json
import csv

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'results/tables/firm_notice_frontier_v1_non_authoritative/attempt_01'
p=folder/'report.json';raw=p.read_bytes();report=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()==(folder/'report.sha256').read_text().strip()
lookup={(r['age'],r['save_steps'],r['upgrade'],r['notice'],r['firm_batch'],r['R']):r for r in report['rows']}
contexts=sorted({(r['age'],r['save_steps'],r['upgrade'],r['R']) for r in report['rows']})
rows=[];substitutions=[]
for a,c,up,R in contexts:
    minima=[]
    for L in (0,1,2,4):
        options=[firm for firm in (0,1) if lookup[(a,c,up,L,firm,R)]['exact']]
        minimum=min(options)+1 if options else None
        minima.append(minimum)
        rows.append(dict(age=a,save_steps=c,upgrade=up,R=R,notice_steps=L,min_total_firm=minimum))
    if minima[0]==2 and minima[-1]==1:substitutions.append(dict(age=a,save_steps=c,upgrade=up,R=R,min_total_firm_by_notice=minima))
for a,c,up,firm in sorted({(r['age'],r['save_steps'],r['upgrade'],r['firm_batch']) for r in report['rows']}):
    values=[max(r['R'] for r in report['rows'] if (r['age'],r['save_steps'],r['upgrade'],r['notice'],r['firm_batch'])==(a,c,up,L,firm) and r['exact']) for L in (0,1,2,4)]
    assert values==sorted(values)
for r in report['rows']:
    if r['firm_batch']==0 and r['exact']:
        assert lookup[(r['age'],r['save_steps'],r['upgrade'],r['notice'],1,r['R'])]['exact']
target=folder/'menu_summary.json'
if target.exists():raise FileExistsError(target)
summary=dict(authority='DRAFT_NONAUTHORITATIVE',source_sha256=hashlib.sha256(raw).hexdigest(),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),contexts=len(contexts),
    substitution_context_count=len(substitutions),substitutions=substitutions,
    warning='Discrete total Firm menu {1,2}; None means no feasible menu entry, not missing data; not a continuous minimum or empirical frequency',rows=rows)
data=json.dumps(summary,indent=2).encode();target.write_bytes(data)
target.with_suffix('.sha256').write_text(hashlib.sha256(data).hexdigest())
with (folder/'minimum_firm_menu.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print('contexts',len(contexts),'substitutions',len(substitutions),'monotonicity checks passed')
