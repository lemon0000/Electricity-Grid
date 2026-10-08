from dataclasses import replace
from fractions import Fraction
import json
import os
from pathlib import Path

import pytest

from experiments import h1_overshoot_accounting_development_v1 as api
from tests.test_h1_job_clock_bridge_development_v1 import make
from tests.test_h1_timed_job_controller_development_v1 import install_launcher,step
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved


def frac(value):return Fraction(*value)


@pytest.mark.parametrize('actual,reserved',[
    ((6,0),(Fraction(5),Fraction(5))),
    ((5,5),(Fraction(5),Fraction(5))),
    ((4,4),(Fraction(5),Fraction(5))),
    ((6,8),(Fraction(5),Fraction(5))),
    ((1,2),(Fraction(3,2),Fraction(3,2))),
    ((0,1),(Fraction(.1)*10**9,Fraction(.1)*10**9)),
])
def test_exact_accounting_oracle(actual,reserved):
    wall=sum(actual)+7
    result=api.account(wall_ns=wall,actual_ns=actual,reserved_ns=reserved)
    excess=sum((max(Fraction(a)-r,0) for a,r in zip(actual,reserved)),Fraction(0))
    unused=sum((max(r-Fraction(a),0) for a,r in zip(actual,reserved)),Fraction(0))
    assert frac(result['stagewise_charge_contract_candidate_ns_ratio'])==7+excess
    assert frac(result['aggregate_charge_descriptive_lower_bound_ns_ratio'])==wall-min(sum(actual),sum(reserved))
    assert excess-unused==sum(actual)-sum(reserved)
    assert frac(result['stagewise_charge_contract_candidate_ns_ratio'])>=frac(result['aggregate_charge_descriptive_lower_bound_ns_ratio'])
    for row in result['stages']:
        assert row['reserved_ns_ratio']==api.ratio(frac(row['reserved_ns_ratio']))
    if actual==(6,0):
        assert result['aggregate_overshoot_descriptive_lower_bound_ns_ratio']==[0,1]
        assert result['stagewise_overshoot_ns_ratio']==[1,1]


@pytest.mark.parametrize('field,value',[
    ('wall_ns',True),('wall_ns',-1),('wall_ns',0),('wall_ns',float('inf')),
    ('actual_ns',(True,1)),('actual_ns',(1,)),('actual_ns',[1,1]),
    ('reserved_ns',(Fraction(0),Fraction(1))),('reserved_ns',(1.,Fraction(1))),
    ('reserved_ns',(True,Fraction(1))),('reserved_ns',(Fraction(1),)),
    ('reserved_ns',(Fraction(2**2049),Fraction(1))),
])
def test_invalid_or_incomplete_vectors_rejected(field,value):
    args=dict(wall_ns=10,actual_ns=(1,1),reserved_ns=(Fraction(5),Fraction(5)))
    args[field]=value
    with pytest.raises(ValueError):api.account(**args)


@pytest.mark.skipif(os.name!='nt',reason='real synthetic Windows Job clock evidence')
def test_fresh_accounting_binds_same_stage_spec_and_rejects_late_drift(tmp_path,environment,synthetic_reports,monkeypatch):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=make(tmp_path/'accounting_non_authoritative',environment)
    original=c._job;items=[]
    def job(*args,**kwargs):items.append(args[1]);return original(*args,**kwargs)
    monkeypatch.setattr(c,'_job',job)
    try:
        step(c,environment);item=items[0]
        pins=dict(binding_pin=c.binding_pin,
            intent_pin=api.io.digest((c.clock_root/'000/intent.json').read_bytes()),
            terminal_pin=c.last_observation.terminal_sha256)
        def inspect(specification=item.specification):
            return api.inspect_window(c.clock_root,0,item.packet,specification,item.limits,**pins)
        result=inspect()
        assert result['declared_seconds_per_stage_ratio']==[5,1]
        assert result['arithmetic']['reserved_total_ns_ratio']==[15000000000,1]
        assert len(result['stage_specification_sha256'])==3
        assert not result['component_budget_verified'] and not result['actual_solver_time_limit_authenticated']
        assert not result['threshold_comparison_performed'] and not result['formal_result']
        with pytest.raises(ValueError):inspect(replace(item.specification,time_limit_seconds=4.))
        actual=api.bridge.inspect
        root=c._lease.root/'job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative'
        targets=[root/'stages/000/specification.json',root/'stages/001/native_timing/completion.json']
        for path in targets:
            raw=path.read_bytes();stamp=path.stat()
            def late(*args,**kwargs):
                checked=actual(*args,**kwargs)
                path.write_bytes(b'['+raw[1:]);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                return checked
            with monkeypatch.context() as mp:
                mp.setattr(api.bridge,'inspect',late)
                with pytest.raises(ValueError):inspect()
            path.write_bytes(raw);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        path=targets[0];raw=path.read_bytes();stamp=path.stat();reached=[]
        def wrong_options(*args,**kwargs):
            checked=actual(*args,**kwargs);reached.append(True)
            doc=json.loads(raw);doc['options']['TimeLimit']=4.
            changed=api.io.encode(doc);assert len(changed)==len(raw)
            path.write_bytes(changed);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            return checked
        with monkeypatch.context() as mp:
            mp.setattr(api.bridge,'inspect',wrong_options)
            with pytest.raises(ValueError,match='stage reservation declaration differs'):inspect()
        assert reached==[True]
        path.write_bytes(raw);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        # Mutate a frozen caller object only after the final readback helper;
        # output must not combine the initial reservation with a later spec.
        unchanged=api.worker._unchanged;original_limit=item.specification.time_limit_seconds;reached=[]
        def mutate_context(views):
            unchanged(views)
            if targets[0] in views:
                reached.append(True);object.__setattr__(item.specification,'time_limit_seconds',4.)
        try:
            with monkeypatch.context() as mp:
                mp.setattr(api.worker,'_unchanged',mutate_context)
                with pytest.raises(ValueError,match='accounting evidence changed'):inspect()
            assert reached==[True]
        finally:object.__setattr__(item.specification,'time_limit_seconds',original_limit)
        original_hour=c.clock_root/'000';parked=tmp_path/'parked_clock_hour';replacement=tmp_path/'replacement_empty'
        for target in (original_hour,parked,replacement):assert target.resolve().is_relative_to(tmp_path.resolve())
        reached=[]
        def replace_directory(*args,**kwargs):
            checked=actual(*args,**kwargs);reached.append(True)
            original_hour.rename(parked);original_hour.mkdir()
            for name in ('intent.json','job.json','terminal.json'):(parked/name).rename(original_hour/name)
            return checked
        try:
            with monkeypatch.context() as mp:
                mp.setattr(api.bridge,'inspect',replace_directory)
                with pytest.raises(ValueError,match='accounting evidence changed'):inspect()
            assert reached==[True]
        finally:
            if parked.exists():
                for name in ('intent.json','job.json','terminal.json'):(original_hour/name).rename(parked/name)
                original_hour.rename(replacement);parked.rename(original_hour)
    finally:c.close()
