"""Finite menu of firm capacity versus notice, all parameters hypothetical."""
from pathlib import Path
from functools import lru_cache
from itertools import product
import json
import hashlib
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]


def rate(t,up,firm):
    return firm if t in (4,5) else 2 if t>=up else 1


def step(t,s,action,c,up,firm):
    remaining,age,saving=s;lost=work=0
    if not remaining:return (0,0,0),dict(t=t,action='done',remaining=0,work=0,lost=0,power=1)
    if t==4 and firm==0:
        lost=age;remaining+=age;age=0;saving=0
    cap=rate(t,up,firm)
    if cap==0:
        assert action==0
        after=(remaining,age,saving);power=1
    elif saving or action=='save':
        saving=(saving or c)-1
        if not saving:age=0
        after=(remaining,age,saving);power=2
    else:
        assert isinstance(action,int) and 0<=action<=cap
        work=min(action,remaining);remaining-=work;age+=work
        after=(remaining,age,0) if remaining else (0,0,0);power=1+work
    assert after[0]==s[0]+lost-work
    assert power<=1+cap
    return after,dict(t=t,action=action,remaining=after[0],work=work,lost=lost,power=power)


def prefix(R,a,L,c,up,firm):
    s=(R,a,0);trace=[]
    for t in range(4-L):
        action=0 if not s[0] else 'save' if s[2] or s[1]>=4 else rate(t,up,firm)
        s,rec=step(t,s,action,c,up,firm);trace.append(rec)
    return s,trace


def solve_case(R,a,L,c,up,firm):
    initial,pre=prefix(R,a,L,c,up,firm)
    @lru_cache(None)
    def search(t,s):
        if t==12:return () if not s[0] else None
        cap=rate(t,up,firm)
        actions=(0,) if not s[0] or cap==0 else ('save',) if s[2] else tuple(range(cap,-1,-1))+('save',)
        for action in actions:
            after,_=step(t,s,action,c,up,firm)
            tail=search(t+1,after)
            if tail is not None:return (action,)+tail
        return None
    actions=search(4-L,initial)
    trace=list(pre);s=initial
    if actions is not None:
        for t,action in enumerate(actions,4-L):
            s,rec=step(t,s,action,c,up,firm);trace.append(rec)
        assert s[0]==0
    strong=initial;strong_trace=list(pre)
    for t in range(4-L,12):
        cap=rate(t,up,firm)
        action=0 if not strong[0] or cap==0 else 'save' if strong[2] or (firm==0 and t==4-c) else cap
        strong,rec=step(t,strong,action,c,up,firm);strong_trace.append(rec)
    relaxed=initial[0]<=sum(rate(t,up,firm) for t in range(4-L,12))
    exact=actions is not None
    assert not exact or relaxed
    assert not (strong[0]==0) or exact
    return dict(exact=exact,strong=strong[0]==0,capacity_only=relaxed,
                exact_trace=trace if exact else None,strong_trace=strong_trace,states=search.cache_info().currsize)


def self_check():
    assert step(4,(3,2,0),0,1,6,0)[0]==(5,0,0)
    assert step(4,(3,2,0),1,1,6,1)[0]==(2,3,0)
    assert step(4,(3,2,1),'save',2,6,1)[0]==(3,0,0)
    assert step(4,(0,0,0),0,1,6,0)[0]==(0,0,0)


def main():
    start=time.perf_counter();tracemalloc.start()
    folder=ROOT/'results/tables/firm_notice_frontier_v1_non_authoritative/attempt_01'
    folder.mkdir(parents=True,exist_ok=False)
    deps=[Path(__file__),ROOT/'docs/plan/firm_notice_frontier_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,rows=[],
                units='5min slots; normalized power; one work unit per unit batch power per slot',
                hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deps})
    try:
        self_check()
        for a,c,up,L,firm,R in product((0,3),(1,2),(2,6,10),(0,1,2,4),(0,1),range(27)):
            if R==0 and a>0:continue
            if time.perf_counter()-start>30:raise TimeoutError('30s budget')
            result=solve_case(R,a,L,c,up,firm)
            report['rows'].append(dict(age=a,save_steps=c,upgrade=up,notice=L,firm_batch=firm,R=R,**result))
        report['boundaries']=[]
        for a,c,up,L,firm in product((0,3),(1,2),(2,6,10),(0,1,2,4),(0,1)):
            rows=[r for r in report['rows'] if (r['age'],r['save_steps'],r['upgrade'],r['notice'],r['firm_batch'])==(a,c,up,L,firm)]
            assert not next(r for r in rows if r['R']==26)['exact']
            report['boundaries'].append(dict(age=a,save_steps=c,upgrade=up,notice=L,firm_batch=firm,max_R=max(r['R'] for r in rows if r['exact'])))
        report['counts']={m:sum(r[m] for r in report['rows']) for m in ('exact','strong','capacity_only')}
        report['strong_disagreements']=sum(r['strong']!=r['exact'] for r in report['rows'])
        report['status']='completed'
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:
        report['wall_seconds']=time.perf_counter()-start;report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['hashes'].items())
        data=json.dumps(report,indent=2).encode();(folder/'report.json').write_bytes(data)
        (folder/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<10*1024*1024
        assert json.loads((folder/'report.json').read_bytes())['status']==report['status']
        print(report['status'],len(report['rows']),report.get('counts'),report.get('strong_disagreements'),report['wall_seconds'],len(data))


if __name__=='__main__':main()
