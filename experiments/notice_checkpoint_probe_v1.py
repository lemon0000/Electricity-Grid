"""Finite-state notice/checkpoint probe. All physical parameters are assumptions."""
from pathlib import Path
from functools import lru_cache
from itertools import product
import json
import hashlib
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]


def step(t,state,action,c,upgrade):
    remaining,age,saving=state
    assert min(state)>=0
    rate=0 if t in (4,5) else (2 if t>=upgrade else 1)
    lost=0;work=0
    if remaining==0:
        return (0,0,0),dict(t=t,action='done',work=0,lost=0,power=1,remaining=0)
    if t==4:
        lost=age;remaining+=age;age=0;saving=0
    if rate==0:
        assert action==0
        result=(remaining,age,saving)
        power=1
    elif saving or action=='save':
        assert saving or action=='save'
        saving=(saving if saving else c)-1
        if saving==0:age=0
        result=(remaining,age,saving);power=2
    else:
        assert isinstance(action,int) and 0<=action<=rate
        work=min(remaining,action)
        remaining-=work;age+=work
        result=(remaining,age,0) if remaining else (0,0,0)
        power=1+work
    assert result[0]==state[0]+lost-work
    assert power<=(1 if t in (4,5) else 3 if t>=upgrade else 2)
    return result,dict(t=t,action=action,work=work,lost=lost,power=power,remaining=result[0])


def routine_action(t,state,c,upgrade):
    if t in (4,5) or not state[0]:return 0
    if state[2] or state[1]>=4:return 'save'
    return 2 if t>=upgrade else 1


def prehistory(R,a,L,c,upgrade):
    state=(R,a,0);records=[]
    for t in range(4-L):
        state,rec=step(t,state,routine_action(t,state,c,upgrade),c,upgrade);records.append(rec)
    return state,records


def greedy(R,a,L,c,upgrade,aware):
    state,records=prehistory(R,a,L,c,upgrade)
    checkpoint_triggered=False
    for t in range(4-L,12):
        action=routine_action(t,state,c,upgrade)
        if aware and not checkpoint_triggered and t<4 and state[0] and 4-t>=(state[2] or c):
            action='save';checkpoint_triggered=True
        state,rec=step(t,state,action,c,upgrade);records.append(rec)
    return state[0]==0,records


def exact(R,a,L,c,upgrade):
    initial,prefix=prehistory(R,a,L,c,upgrade)
    @lru_cache(None)
    def solve(t,state):
        if t==12:return () if state[0]==0 else None
        rate=0 if t in (4,5) else 2 if t>=upgrade else 1
        actions=(0,) if not state[0] or rate==0 else ('save',) if state[2] else tuple(range(rate,-1,-1))+('save',)
        for action in actions:
            after,_=step(t,state,action,c,upgrade)
            tail=solve(t+1,after)
            if tail is not None:return (action,)+tail
        return None
    actions=solve(4-L,initial)
    if actions is None:return False,None,solve.cache_info().currsize
    state=initial;records=list(prefix)
    for t,action in enumerate(actions,4-L):
        state,rec=step(t,state,action,c,upgrade);records.append(rec)
    assert state[0]==0
    return True,records,solve.cache_info().currsize


def self_check():
    state,rec=step(4,(3,2,1),0,2,8)
    assert state==(5,0,0) and rec['lost']==2
    assert step(3,(3,2,1),'save',2,8)[0]==(3,0,0)
    assert step(4,(0,0,0),0,2,8)[0]==(0,0,0)
    assert step(5,(3,0,0),0,2,8)[0]==(3,0,0)
    for c in (1,2):
        for up in (6,8,10):
            assert exact(0,3,0,c,up)[0]
            assert not exact(18,3,0,c,up)[0]
    return 16


def main():
    start=time.perf_counter();tracemalloc.start()
    out=ROOT/'results/tables/notice_checkpoint_probe_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True,exist_ok=False)
    deps=[Path(__file__),ROOT/'docs/plan/notice_checkpoint_probe_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,rows=[],
                hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deps})
    try:
        report['self_checks']=self_check()
        for a,L,c,upgrade,R in product(range(4),(0,1,2,4),(1,2),(6,8,10),range(19)):
            if time.perf_counter()-start>30:raise TimeoutError('30s budget')
            blind,blind_trace=greedy(R,a,L,c,upgrade,False)
            aware,aware_trace=greedy(R,a,L,c,upgrade,True)
            optimal,trace,states=exact(R,a,L,c,upgrade)
            assert not blind or optimal
            assert not aware or optimal
            report['rows'].append(dict(age=a,notice=L,save_steps=c,upgrade=upgrade,R=R,
                checkpoint_blind=blind,notice_greedy=aware,exact=optimal,exact_states=states,
                blind_trace=blind_trace,aware_trace=aware_trace,exact_trace=trace))
        report['counts']={m:sum(r[m] for r in report['rows']) for m in ['checkpoint_blind','notice_greedy','exact']}
        report['status']='completed'
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:
        report['wall_seconds']=time.perf_counter()-start;report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['hashes'].items())
        data=json.dumps(report,indent=2).encode();(out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<10*1024*1024
        assert json.loads((out/'report.json').read_bytes())['status']==report['status']
        print(report['status'],len(report['rows']),report.get('counts'),report['wall_seconds'],len(data))


if __name__=='__main__':main()
