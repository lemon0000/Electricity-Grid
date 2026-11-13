"""Saved-case follow-up: just-in-time checkpoint, no redundant post-event saves."""
from pathlib import Path
import sys
import json
import hashlib
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.notice_checkpoint_probe_v1 import prehistory,step


def main():
    start=time.perf_counter()
    folder=ROOT/'results/tables/notice_checkpoint_probe_v1_non_authoritative/attempt_01'
    source=folder/'report.json';raw=source.read_bytes();report=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()==(folder/'report.sha256').read_text().strip()
    target=folder/'strong_baseline.json'
    if target.exists():raise FileExistsError(target)
    rows=[]
    for r in report['rows']:
        if time.perf_counter()-start>10:raise TimeoutError('10s baseline audit')
        a,L,c,up,R=[r[k] for k in ['age','notice','save_steps','upgrade','R']]
        state,trace=prehistory(R,a,L,c,up)
        for t in range(4-L,12):
            action=0 if t in (4,5) or not state[0] else 'save' if state[2] or t==4-c else 2 if t>=up else 1
            state,record=step(t,state,action,c,up);trace.append(record)
        ok=state[0]==0
        assert not ok or r['exact']
        rows.append(dict(age=a,notice=L,save_steps=c,upgrade=up,R=R,feasible=ok,exact=r['exact'],trace=trace))
    result=dict(authority='DRAFT_NONAUTHORITATIVE',source_sha256=hashlib.sha256(raw).hexdigest(),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        model_sha256=hashlib.sha256((ROOT/'experiments/notice_checkpoint_probe_v1.py').read_bytes()).hexdigest(),
        budget_seconds=10,wall_seconds=time.perf_counter()-start,
        rule='Same prefix, continue pending saves, begin new save at 4-c if notified in time, otherwise work; no routine saves after sole event.',
        feasible=sum(r['feasible'] for r in rows),exact_feasible=sum(r['exact'] for r in rows),
        disagreements=sum(r['feasible']!=r['exact'] for r in rows),rows=rows)
    data=json.dumps(result,indent=2).encode();target.write_bytes(data)
    target.with_suffix('.sha256').write_text(hashlib.sha256(data).hexdigest())
    print(result['feasible'],result['exact_feasible'],result['disagreements'],result['wall_seconds'])


if __name__=='__main__':main()
