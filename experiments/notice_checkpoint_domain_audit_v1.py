"""Audit saved cases after excluding completed jobs with stale checkpoint age."""
from pathlib import Path
import json
import hashlib

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'results/tables/notice_checkpoint_probe_v1_non_authoritative/attempt_01'
original=folder/'report.json';strong=folder/'strong_baseline.json'
r=json.loads(original.read_bytes());s=json.loads(strong.read_bytes())
keys=('age','notice','save_steps','upgrade','R')
lookup={tuple(x[k] for k in keys):x for x in s['rows']}
valid=[x for x in r['rows'] if x['R']>0 or x['age']==0]
assert len(valid)==1752
assert all(x['exact']==lookup[tuple(x[k] for k in keys)]['feasible'] for x in valid)
boundaries=[]
for key in sorted({tuple(x[k] for k in keys[:-1]) for x in valid}):
    candidates=[x for x in valid if tuple(x[k] for k in keys[:-1])==key]
    boundaries.append(dict(zip(keys[:-1],key),max_R=max(x['R'] for x in candidates if x['exact'])))
result=dict(authority='DRAFT_NONAUTHORITATIVE',domain='R>0 or age==0; completed job has no unpersisted progress',
    source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
    strong_sha256=hashlib.sha256(strong.read_bytes()).hexdigest(),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    raw_rows=len(r['rows']),excluded_semantic_rows=len(r['rows'])-len(valid),valid_rows=len(valid),
    feasible_counts={m:sum(x[m] for x in valid) for m in ('checkpoint_blind','notice_greedy','exact')},
    strong_equals_exact=True,boundaries=boundaries)
target=folder/'valid_domain_summary.json'
if target.exists():raise FileExistsError(target)
data=json.dumps(result,indent=2).encode();target.write_bytes(data)
target.with_suffix('.sha256').write_text(hashlib.sha256(data).hexdigest())
print(result['valid_rows'],result['feasible_counts'])
