"""Trace eligibility plus assumed recovery; finite-grid repeated-call diagnostic."""
from pathlib import Path
import sys
import io
import json
import hashlib
import zipfile
import itertools
import time
import tracemalloc
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments.stage_boundary_validation_v1 import flow_schedule,subset_certificate,edf_schedule


def checked(cap,jobs):
    feasible,allocation=flow_schedule(cap,jobs)
    certified,witness=subset_certificate(cap,jobs)
    assert feasible==certified
    return dict(feasible=feasible,allocation=allocation,witness=witness)


def main():
    start=time.perf_counter();tracemalloc.start()
    out=ROOT/'results/tables/asi_repeated_call_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True,exist_ok=False)
    archive=ROOT/'data/raw/asi_trace_power/v1.0.1/upstream/asi-trace-power-v1.0.1.zip'
    deps=[archive,Path(__file__),ROOT/'experiments/stage_boundary_validation_v1.py',ROOT/'docs/plan/asi_repeated_call_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deps},rows=[])
    def check():
        if time.perf_counter()-start>30:raise TimeoutError('30s budget')
    try:
        with zipfile.ZipFile(archive) as z:
            def table(name):
                return pd.read_parquet(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('/data/products/'+name+'.parquet')))))
            cluster=table('envelope_cluster_hourly');env=table('envelope_hourly');surface=table('k_surface')
        matrix=cluster.pivot(index='cluster_id',columns='t',values='curtail_idle_retained')
        keep=matrix.index[matrix.mean(axis=1)>=.02]
        hourly=matrix.loc[keep].sum(axis=0).to_numpy()
        good=env.good.to_numpy(bool)
        k=float(surface[(surface.scope=='fleet')&(surface.n==len(keep))&(surface.h==2)&np.isclose(surface.alpha,.95)].iloc[0].k_obs)
        k_milli=int(np.floor(k*1000));report['reference_k_mw']=k;report['quantized_reference_mw']=k_milli/1000
        counts=dict(eligible_reject=0,missing=0,separate_pass_joint_fail=0,static_pass_joint_fail=0,joint_pass=0,edf_disagreement=0)
        for origin,gap,lag,stage,level in itertools.product(range(0,12*168,168),(4,8),(4,12),(8,16),range(5)):
            check()
            row=dict(origin=origin,gap=gap,lag=lag,stage=stage,offer_level=level)
            if not good[origin:origin+32].all():
                row['status']='unresolved_missing';counts['missing']+=1;report['rows'].append(row);continue
            offer=k_milli*level
            calls=set(range(2))|set(range(gap,gap+2))
            eligible=[int(np.floor(x*4000)) for x in hourly[origin:origin+32]]
            instantaneous=all(offer<=eligible[t] for t in calls)
            actual=[0 if t in calls else k_milli*(1 if t<stage else 2) for t in range(32)]
            terminal=[0 if t in calls else k_milli*2 for t in range(32)]
            jobs=[(2,1+lag,offer*2),(gap+2,gap+1+lag,offer*2)]
            joint=checked(actual,jobs);static=checked(terminal,jobs)
            single=[checked(actual,[job]) for job in jobs]
            edf_ok,edf_allocation=edf_schedule(actual,jobs)
            assert edf_ok==joint['feasible']
            independent=instantaneous and all(s['feasible'] for s in single)
            joint_ok=instantaneous and joint['feasible']
            static_ok=instantaneous and static['feasible']
            counts['eligible_reject']+=int(not instantaneous)
            counts['separate_pass_joint_fail']+=int(independent and not joint_ok)
            counts['static_pass_joint_fail']+=int(static_ok and not joint_ok)
            counts['joint_pass']+=int(joint_ok)
            row.update(status='evaluated',offer_mw=offer/4000,eligible_units=eligible,actual_recovery_units=actual,
                jobs=jobs,eligible_only=instantaneous,separate_event=independent,terminal_static=static_ok,
                chronological=joint_ok,joint=joint,static=static,single=single,edf_feasible=edf_ok,
                edf_allocation=edf_allocation)
            report['rows'].append(row)
        report['counts']=counts;report['status']='completed'
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:
        report['wall_seconds']=time.perf_counter()-start
        report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in report['hashes'].items())
        data=json.dumps(report,indent=2).encode();(out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<10*1024*1024
        assert json.loads((out/'report.json').read_bytes())['status']==report['status']
        print(report['status'],len(report['rows']),report.get('counts'),report['wall_seconds'])


if __name__=='__main__':main()
