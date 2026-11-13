"""Exact audit of physical reduction; no claim of full model equivalence."""
from pathlib import Path
from fractions import Fraction as Q
import sys
import itertools
import json
import hashlib
import time
import tracemalloc

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.staged_deliverability_d_grid_v2 import load_grid_case
from src.staged_deliverability_development_v1 import power_mapping,execute,assessment,plain


def physical_cap(p,o):
    b=p.facility_factor*o.idle_mw+p.auxiliary_mw
    caps=[o.compute_capacity,(o.supply_mw-b)/p.slope]
    if p.alpha:
        caps.append((o.clean_mwh/p.alpha-b)/p.slope)
    return min(caps)


def main():
    start=time.perf_counter();tracemalloc.start()
    out=ROOT/'results/tables/stage_physical_reduction_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True,exist_ok=False)
    config='configs/staged_deliverability_d_v1.DRAFT.yaml'
    deps=[config,'src/staged_deliverability_development_v1.py','src/staged_deliverability_d_grid_v2.py',
          'src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py',
          'experiments/stage_physical_reduction_v1.py','docs/plan/stage_physical_reduction_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,rows=[],
                hashes={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in deps},physical_points=0,recovery_checks=0)
    try:
        for business,grid,clean in itertools.product(('fast','slow'),('on_time','delayed'),('early','late')):
            p,obs=load_grid_case(ROOT/config,business,grid,clean)
            values=[]
            for o in obs:
                if time.perf_counter()-start>10: raise TimeoutError('10s budget')
                cap=physical_cap(p,o)
                for q,r in itertools.product((Q(0),o.workload/2,o.workload),(Q(0),p.max_recovery,2*p.max_recovery)):
                    x,_,power=power_mapping(p,o,q,r)
                    direct=(0<=x<=o.compute_capacity and power<=o.supply_mw and p.alpha*power<=o.clean_mwh)
                    reduced=(0<=x<=cap)
                    assert direct==reduced
                    report['physical_points']+=1
                values.append(dict(hour=o.hour,physical_cap=cap,workload=o.workload))
            state=execute(p,obs,'full_temporal','audit')
            debt=Q(0)
            for rec in state.records:
                o=rec.observation
                if rec.grid_request_mw+rec.cfe_request_mw==0:
                    expected=min(p.capacity,p.max_recovery,debt/p.eta,max(physical_cap(p,o)-o.workload,Q(0)))
                    assert rec.recovery==expected
                    report['recovery_checks']+=1
                if rec.ledger_applied:
                    debt+=rec.deferred-p.eta*rec.recovery
            report['rows'].append(dict(key=[business,grid,clean],caps=plain(values),
                assessment=plain(assessment(state,registration_end=obs[-1].hour+1,expected_last_hour=obs[-1].hour))))
        report['ramp_counterexample']=[]
        for trajectory in ((0,2),(1,2),(0,1)):
            static=all(0<=p<=2 for p in trajectory)
            dynamic=static and all(abs(b-a)<=1 for a,b in zip((0,)+trajectory,trajectory))
            report['ramp_counterexample'].append(dict(trajectory=trajectory,static=static,dynamic=dynamic))
        assert [r['dynamic'] for r in report['ramp_counterexample']]==[False,True,True]
        report['status']='completed'
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:
        report['wall_seconds']=time.perf_counter()-start
        report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/x).read_bytes()).hexdigest()==v for x,v in report['hashes'].items())
        data=json.dumps(report,indent=2).encode();(out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<2*1024*1024
        assert json.loads((out/'report.json').read_bytes())['status']==report['status']
        print(report['status'],report['physical_points'],report['recovery_checks'],report['wall_seconds'])


if __name__=='__main__':
    main()
