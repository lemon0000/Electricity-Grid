"""Exact small scheduling diagnostic, independent of frozen q/r models."""
from collections import deque
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]


def flow_schedule(cap, jobs):
    n, horizon = len(jobs), len(cap)
    sink = n + horizon + 1
    residual = [[0]*(sink+1) for _ in range(sink+1)]
    total = sum(e for a,d,e in jobs)
    for j,(a,d,e) in enumerate(jobs,1):
        residual[0][j] = e
        for h in range(a,d+1):
            residual[j][n+1+h] = total
    for h,c in enumerate(cap):
        residual[n+1+h][sink] = c
    value = 0
    while True:
        parent = [-1]*(sink+1); parent[0] = 0
        queue = deque([0])
        while queue and parent[sink] < 0:
            u = queue.popleft()
            for v,c in enumerate(residual[u]):
                if c > 0 and parent[v] < 0:
                    parent[v] = u; queue.append(v)
        if parent[sink] < 0:
            break
        amount = total; v = sink
        while v:
            amount = min(amount,residual[parent[v]][v]); v=parent[v]
        v=sink
        while v:
            u=parent[v]; residual[u][v]-=amount; residual[v][u]+=amount; v=u
        value += amount
    schedule = [[residual[n+1+h][j+1] for h in range(horizon)] for j in range(n)]
    for j,(a,d,e) in enumerate(jobs):
        assert sum(schedule[j]) <= e
        assert all(x >= 0 and (a <= h <= d or x == 0) for h,x in enumerate(schedule[j]))
    assert all(sum(row[h] for row in schedule) <= cap[h] for h in range(horizon))
    assert sum(map(sum,schedule)) == value
    return value == total, schedule


def subset_certificate(cap, jobs):
    """Exhaustive Hall test for this splittable bipartite allocation model only."""
    for count in range(1,len(jobs)+1):
        for ids in combinations(range(len(jobs)),count):
            hours=set(h for j in ids for h in range(jobs[j][0],jobs[j][1]+1))
            demand=sum(jobs[j][2] for j in ids)
            available=sum(cap[h] for h in hours)
            if demand > available:
                return False, dict(jobs=ids,hours=sorted(hours),demand=demand,available=available)
    return True, None


def edf_schedule(cap,jobs):
    remaining=[e for a,d,e in jobs]
    schedule=[[0]*len(cap) for _ in jobs]
    for h,c in enumerate(cap):
        for j in sorted(range(len(jobs)),key=lambda j:(jobs[j][1],j)):
            if jobs[j][0] <= h <= jobs[j][1]:
                take=min(c,remaining[j]);remaining[j]-=take;c-=take;schedule[j][h]=take
    return not any(remaining),schedule


def self_check():
    cases=[([4,0],[(0,0,4)],True),([0,4],[(0,0,4)],False),
           ([4,0],[(0,0,3),(0,0,3)],False),([4,4],[(0,1,4),(0,0,4)],True),
           ([0,4,4],[(0,2,4),(1,1,4)],True)]
    for cap,jobs,expected in cases:
        assert flow_schedule(cap,jobs)[0] == subset_certificate(cap,jobs)[0] == edf_schedule(cap,jobs)[0] == expected
    return len(cases)


def main():
    start=time.perf_counter();tracemalloc.start()
    out=ROOT/'results/tables/stage_boundary_validation_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),ROOT/'docs/plan/stage_boundary_validation_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,
                units='integer work quanta; 4 quanta = 1 normalized work unit; 1h slots',
                hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},rows=[])
    try:
        report['self_checks']=self_check()
        for e,g,c,due in product((1,3,5),(1,3,5),(1,5),(1,5)):
            capacities={name:[8 if h<t else 16 for h in range(8)] for name,t in [('equipment',e),('grid',g),('clean',c)]}
            actual=[min(values[h] for values in capacities.values()) for h in range(8)]
            modes={'current_frozen':[actual[0]]*8,'terminal_frozen':[actual[-1]]*8,'chronological':actual}
            row=dict(equipment=e,grid=g,clean=c,debt_due=due,capacities=capacities,runs=[])
            case_start=time.perf_counter()
            for scale in range(33):
                if time.perf_counter()-start>60: raise TimeoutError('60s wall budget')
                jobs=[(0,due,4)]+[(h,h+2,scale) for h in (0,2,4)]
                results={}
                for mode,cap in modes.items():
                    ok,allocation=flow_schedule(cap,jobs)
                    cert,witness=subset_certificate(cap,jobs)
                    assert ok == cert
                    results[mode]=dict(feasible=ok,allocation=allocation,infeasible_witness=witness)
                edf_ok,edf_alloc=edf_schedule(actual,jobs)
                assert edf_ok == results['chronological']['feasible']
                results['edf']=dict(feasible=edf_ok,allocation=edf_alloc)
                row['runs'].append(dict(scale_quanta=scale,jobs=jobs,results=results))
            row['boundary']={mode:max(r['scale_quanta'] for r in row['runs'] if r['results'][mode]['feasible'])/4 for mode in (*modes,'edf')}
            row['wall_seconds']=time.perf_counter()-case_start
            report['rows'].append(row)
        report['status']='completed'
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc)
        raise
    finally:
        report['wall_seconds']=time.perf_counter()-start
        report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in report['hashes'].items())
        data=json.dumps(report,indent=2).encode()
        (out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<10*1024*1024
        assert json.loads((out/'report.json').read_bytes())['status']==report['status']
        print(report['status'],len(report['rows']),report['wall_seconds'],len(data))


if __name__=='__main__':
    main()
