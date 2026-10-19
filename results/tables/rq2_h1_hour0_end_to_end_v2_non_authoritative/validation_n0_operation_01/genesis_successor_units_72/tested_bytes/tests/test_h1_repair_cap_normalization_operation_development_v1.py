"""Pure frozen-input reuse with real pin reads; no Parent or solver transport."""
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from types import ModuleType,SimpleNamespace

import pytest

from experiments import h1_repair_cap_normalization_operation_development_v1 as m


@pytest.fixture
def case(tmp_path):
    calls=[];faults={};counts=dict(q=0)
    table=json.dumps(dict(rows=[dict(generator_uid='G1',proposed_cap_mw_fraction='3/2'),
        dict(generator_uid='G2',proposed_cap_mw_fraction='2')])).encode()
    table_path=tmp_path/'caps.json';table_path.write_bytes(table)
    authority=json.dumps(dict(cap_table_path='caps.json',cap_table_sha256=sha256(table).hexdigest())).encode()
    authority_path=tmp_path/'authority.json';authority_path.write_bytes(authority)
    def pin(path,expected):
        calls.append(Path(path).name)
        if faults.get('pin')==Path(path).name:raise OSError('pin failed')
        raw=Path(path).read_bytes()
        if sha256(raw).hexdigest()!=expected:raise ValueError('input drift')
        return raw+b'changed' if faults.get('raw')==Path(path).name else raw
    registry=SimpleNamespace(_pin=pin,AUTHORITY=authority_path,
        AUTHORITY_SHA=sha256(authority).hexdigest(),ROOT=tmp_path)
    physical=ModuleType('explicit_repair_normalization_test')
    physical.registry=registry;physical.json=json;physical.Q=Fraction
    def digest(*parts):
        counts['digest']=counts.get('digest',0)+1
        raw=json.dumps(parts,separators=(',',':')).encode()
        wrong=faults.get('digest') or (faults.get('oracle') and counts['digest']==1)
        return 'wrong' if wrong else sha256(raw).hexdigest()
    physical._digest=digest
    exec("def repair_mechanism_identity():\n"
        "    authority=json.loads(registry._pin(registry.AUTHORITY,registry.AUTHORITY_SHA))\n"
        "    table=json.loads(registry._pin(registry.ROOT/authority['cap_table_path'],authority['cap_table_sha256']))\n"
        "    values=tuple((r['generator_uid'],str(Q(r['proposed_cap_mw_fraction']).numerator),\n"
        "        str(Q(r['proposed_cap_mw_fraction']).denominator)) for r in table['rows'])\n"
        "    return _digest('approved_Rref_actual_repair_cap_min_Pmax_60ramp',values)\n",vars(physical))
    return SimpleNamespace(physical=physical,registry=registry,calls=calls,faults=faults,
        original=physical.repair_mechanism_identity)


def test_each_request_preserves_ordered_pins_and_digest_and_clears_all_cached_bytes(case):
    c=case;context,receipt=m.operation(c.physical);expected=c.original()
    with pytest.raises(ValueError,match='closed'):receipt()
    with context:
        before=len(c.calls)
        for _ in range(4):assert c.physical.repair_mechanism_identity()==expected
        assert c.calls[before:]==['authority.json','caps.json']*4
        with pytest.raises(ValueError,match='closed'):receipt()
        with pytest.raises(TypeError,match='nested'):m.operation(c.physical)
    assert c.physical.repair_mechanism_identity is c.original
    r=receipt();assert r['calls']==4 and r['all_normalization_cache_entries_cleared']
    assert r['per_routed_call_two_pin_order_preserved'] and not r['overall_pin_read_schedule_preserved']
    assert r['routed_pin_read_attempts']==8 and r['original_oracle_invocations']==dict(entry=1,exit=1)
    assert r['cache_build_pin_reads']==r['cache_build_pin_read_attempts']==2
    assert r['adapter_pin_reads']==14 and r['routed_and_bookend_successful_pin_reads']==12
    assert r['original_alias_restored'] and not r['json_fraction_failure_timing_preserved']
    assert not r['post_scope_consumer_reuse_allowed'] and r['process_must_exit_after_receipt']
    r['calls']=100
    assert receipt()['calls']==4


@pytest.mark.parametrize('kind',['pin','raw'])
@pytest.mark.parametrize('name',['authority.json','caps.json'])
def test_first_input_failure_stops_before_later_io_and_poison_is_sticky(case,kind,name):
    c=case;context,receipt=m.operation(c.physical)
    with pytest.raises(ValueError,match='poisoned'):
        with context:
            c.faults[kind]=name;before=len(c.calls)
            with pytest.raises((OSError,ValueError)):c.physical.repair_mechanism_identity()
            assert c.calls[before:]==(['authority.json'] if name=='authority.json' else ['authority.json','caps.json'])
            c.faults.clear()
            with pytest.raises(ValueError,match='poisoned'):c.physical.repair_mechanism_identity()
    assert receipt()['all_normalization_cache_entries_cleared']
    assert c.physical.repair_mechanism_identity is c.original


@pytest.mark.parametrize('fault',['pin','raw','oracle'])
def test_enter_failure_restores_and_produces_only_closed_failure_receipt(case,fault):
    c=case;context,receipt=m.operation(c.physical)
    if fault=='oracle':c.faults['oracle']=True
    else:c.faults[fault]='authority.json'
    with pytest.raises((OSError,ValueError,KeyError,json.JSONDecodeError)):
        with context:raise AssertionError('cannot enter')
    c.faults.clear()
    r=receipt();assert r['first_failure'] and r['all_normalization_cache_entries_cleared']
    assert all(key in r for key in ('authority_sha256','cap_table_sha256','digest'))
    assert r['cache_build_pin_read_attempts']>=r['cache_build_pin_reads']
    assert c.physical.repair_mechanism_identity is c.original


def test_digest_difference_poison_clears_without_reusing_failed_result(case):
    c=case;context,receipt=m.operation(c.physical)
    with pytest.raises(ValueError,match='digest'):
        with context:
            c.faults['digest']=True
            c.physical.repair_mechanism_identity()
    c.faults.clear()
    assert receipt()['calls']==0 and receipt()['all_normalization_cache_entries_cleared']


def test_foreign_alias_is_preserved_and_reported(case):
    c=case;context,receipt=m.operation(c.physical);foreign=lambda:'foreign'
    with pytest.raises(ValueError,match='route'):
        with context:c.physical.repair_mechanism_identity=foreign
    assert c.physical.repair_mechanism_identity is foreign
    assert not receipt()['original_alias_restored'] and receipt()['cleanup_error']


def test_foreign_creator_cannot_read_or_poison_operation(case):
    c=case;context,receipt=m.operation(c.physical);errors=[]
    with context:
        def foreign():
            for call in (c.physical.repair_mechanism_identity,receipt):
                try:call()
                except BaseException as error:errors.append(error)
        thread=Thread(target=foreign);thread.start();thread.join(timeout=2)
        assert not thread.is_alive() and len(errors)==2
        assert c.physical.repair_mechanism_identity()==c.original()
    assert receipt()['first_failure'] is None


def test_import_fixed_consumer_prevents_late_activation(case,monkeypatch):
    import sys
    consumer=ModuleType('explicit_import_fixed_consumer')
    consumer._SOURCE_FIXED=((case.physical,'repair_mechanism_identity',case.original),)
    monkeypatch.setitem(sys.modules,consumer.__name__,consumer)
    with pytest.raises(ValueError,match='precede'):m.operation(case.physical)
    assert case.physical.repair_mechanism_identity is case.original


def test_real_frozen_table_matches_original_with_repeated_fresh_reads():
    # Exercise the mandatory dedicated-process lifecycle even when other tests
    # in this pytest invocation imported original fixed consumers at collection.
    code='\n'.join((
        'import sys,json',f'sys.path.insert(0,{str(Path(__file__).resolve().parents[1])!r})',
        'from time import perf_counter',
        'from experiments import h1_origin_grid_step_development_v1 as physical',
        'from experiments import h1_repair_cap_normalization_operation_development_v1 as m',
        'original=physical.repair_mechanism_identity',
        'start=perf_counter();expected=original();baseline=perf_counter()-start',
        'context,receipt=m.operation(physical)',
        'with context:',
        '    start=perf_counter()',
        '    assert [physical.repair_mechanism_identity() for _ in range(8)]==[expected]*8',
        '    reused=(perf_counter()-start)/8',
        'r=receipt()',
        'assert r["digest"]==expected and r["calls"]==8 and r["all_normalization_cache_entries_cleared"]',
        'assert physical.repair_mechanism_identity is original',
        'print(json.dumps(dict(original_one_seconds=baseline,reused_mean_seconds=reused,repetitions=8,receipt=r)))',
    ))
    result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout.splitlines()[-1])
    assert value['receipt']['process_must_exit_after_receipt']
    print(json.dumps(value),flush=True)
