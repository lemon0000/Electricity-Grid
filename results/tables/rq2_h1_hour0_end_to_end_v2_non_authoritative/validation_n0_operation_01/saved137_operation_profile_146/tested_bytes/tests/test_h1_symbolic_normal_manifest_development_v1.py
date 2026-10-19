"""Pinned proof catalog arithmetic and static symbolic slots; zero solver/Job."""
from copy import copy, deepcopy
from dataclasses import fields, replace
from hashlib import sha256
from math import prod
import json
import pickle
import random

import pytest
from experiments import h1_symbolic_normal_manifest_development_v1 as m


@pytest.fixture(scope='module')
def raw(): return (m.ROOT/m.PROOF).read_bytes()


@pytest.fixture(scope='module')
def profile():
    # Explicit synthetic declaration; these are not a proposed run profile.
    return m.StaticProfile(**{f.name:sha256(f.name.encode()).hexdigest() for f in fields(m.StaticProfile)})


@pytest.fixture(scope='module')
def snapshot(raw,profile): return m._compile(raw,profile,'a'*64)


def point(raw,family='training_ub'):
    p=json.loads(raw);axes=p['catalog']['axes'][family]
    cell=next(c for c in p['cells'] if not c['arm_implication_nodes'])
    return {k:(cell[k] if k in ('theta','alpha') else axes[k][0]) for k in p['catalog']['axis_order'][family]}


def ordinal(raw,family,coordinate):return m.proof._resolver(raw).encode_coordinate(family,coordinate)


def test_partition_independent_cell_arm_oracle(raw,snapshot):
    p=json.loads(raw);s=snapshot.data();computed={}
    for family,order in p['catalog']['axis_order'].items():
        a=p['catalog']['axes'][family];unresolved=0
        for cell in p['cells']:
            for arm in a['arm']:
                if arm not in cell['arm_implication_nodes']:
                    unresolved+=len(a['power'])*len(a['workload'])*len(a.get('capacity',[None]))
        computed[family]=unresolved
        assert s['families'][family]['unresolved_identities']==unresolved
        assert s['families'][family]['original_identities']==prod(map(len,a.values()))
    assert computed==dict(holdout=29130752,training_b6_actual=644336,training_lb=29756608,training_ub=3005417408)
    assert s['totals']['unresolved_identities']==3064949104
    assert s['totals']['potential_hour_slots']==588470227968
    assert s['totals']['conditional_stage_slots']==136525092888576
    assert s['candidate_pair_hour_counts']==dict(training=2811648,holdout=2752512)
    assert s['conditional_candidate_pair_stage_count']==1290885120
    assert 'not validated here' in s['stage_count_condition']
    assert not s['ceiling_is_enforced'] and s['complete_study_task_bound'] is None
    assert all(s[k] is False for k in m.FLAGS)


def test_mixed_radix_first_last_random_and_proof_partition(snapshot):
    rng=random.Random(91)
    for family,counts in snapshot.data()['families'].items():
        for ordinal_ in [0,counts['original_identities']-1]+[rng.randrange(counts['original_identities']) for _ in range(5)]:
            for hour in (0,191):
                item=snapshot.resolve(family,ordinal_*192+hour)
                mapping=snapshot.obligation(family,ordinal_)
                if mapping['kind']=='proof_terminal_ref':
                    assert item==mapping and item['slot_range'] is None
                    assert all(not e['solver_reuse_edge'] for e in item['obligation_node']['record']['edges'])
                else:
                    assert item['record']['ordinal']==ordinal_ and item['record']['relative_hour']==hour
                    assert divmod(item['slot_ordinal'],192)==(ordinal_,hour)
                    assert mapping['slot_range']==[ordinal_*192,(ordinal_+1)*192]


def test_predecessor_dag_phase_barrier_and_null_runtime(raw,snapshot):
    for family in ('training_ub','holdout'):
        i=ordinal(raw,family,point(raw,family))
        for hour in (0,1,167,168,191):
            item=snapshot.resolve(family,i*192+hour)
            assert item['record']['phase']==('enrollment' if hour<168 else 'followup')
            assert item['training_frozen_barrier_required']==(family=='holdout')
            if hour:
                previous=snapshot.resolve(family,i*192+hour-1)
                assert item['edges'][0]['parent']==previous['slot_id']
                assert item['candidate_predecessor_class']==previous['candidate_class_id']
            else: assert item['edges'][0]['kind']=='declared_genesis'
            assert all(item[k] is None for k in ('source_identity','before_identity','normal_input_identity',
                'causal_key','runtime_task_id','process_identity','outcome','resource_profile_id'))
            assert not item['eligible_for_execution'] and not item['edges'][0]['solver_reuse_edge']


def test_business_axes_change_unshared_slot_not_candidate(raw,snapshot):
    p=point(raw);a=json.loads(raw)['catalog']['axes']['training_ub']
    # Network-only has no CFE analytic exclusion at any theta/alpha.
    p['arm']='network-only'
    base=snapshot.resolve('training_ub',ordinal(raw,'training_ub',p)*192+1)
    for axis in ('theta','alpha','capacity','arm'):
        q=dict(p);q[axis]=next(v for v in a[axis] if v!=p[axis])
        item=snapshot.resolve('training_ub',ordinal(raw,'training_ub',q)*192+1)
        assert item['kind']=='potential_N_slot'
        assert item['slot_id']!=base['slot_id']
        assert item['candidate_class_id']==base['candidate_class_id']


def test_pair_hour_and_every_profile_pin_change_candidate(raw,profile,snapshot):
    p=point(raw);i=ordinal(raw,'training_ub',p)
    base=snapshot.resolve('training_ub',i*192+1)
    assert snapshot.resolve('training_ub',i*192+2)['candidate_class_id']!=base['candidate_class_id']
    axes=json.loads(raw)['catalog']['axes']['training_ub']
    for axis in ('power','workload'):
        q=dict(p);q[axis]=next(v for v in axes[axis] if v!=p[axis])
        assert snapshot.resolve('training_ub',ordinal(raw,'training_ub',q)*192+1)['candidate_class_id']!=base['candidate_class_id']
    for f in fields(profile):
        changed=m._compile(raw,replace(profile,**{f.name:'b'*64}),'a'*64)
        assert changed.resolve('training_ub',i*192+1)['candidate_class_id']!=base['candidate_class_id']
    holdout=snapshot.resolve('holdout',ordinal(raw,'holdout',point(raw,'holdout'))*192+1)
    assert holdout['candidate_class_id']!=base['candidate_class_id']


@pytest.mark.parametrize('value',[True,-1,1.0,'1'])
def test_invalid_slot_ordinal(snapshot,value):
    with pytest.raises(ValueError): snapshot.resolve('training_ub',value)


def test_mutation_copy_and_bounds(raw,snapshot):
    d=snapshot.data();d['formal_result']=True
    assert not snapshot.data()['formal_result']
    for f in (copy,deepcopy,pickle.dumps):
        with pytest.raises(ValueError):f(snapshot)
    with pytest.raises(ValueError): m.SymbolicManifest()
    with pytest.raises(ValueError):snapshot.resolve('unknown',0)
    with pytest.raises(ValueError):snapshot.resolve('training_ub',snapshot.data()['families']['training_ub']['ordinal_span'])
    p=point(raw);i=ordinal(raw,'training_ub',p);item=snapshot.resolve('training_ub',i*192)
    item['record']['static_profile']['network_sha256']='z'
    assert snapshot.resolve('training_ub',i*192)['record']['static_profile']['network_sha256']!='z'


def test_build_inspect_no_loader_and_tamper(tmp_path,profile,monkeypatch):
    def denied(*a,**k):raise AssertionError('source loading or proof reconstruction forbidden')
    monkeypatch.setattr(m.proof,'build',denied)
    monkeypatch.setattr(m.proof.exclusion,'inspect',denied)
    monkeypatch.setattr(m.proof.exclusion.source_window,'load_source_window',denied)
    snap=m.build(profile);path=tmp_path/'symbolic_non_authoritative.json';path.write_bytes(snap.raw)
    assert m.inspect(path,expected_sha256=snap.identity).raw==snap.raw
    v=snap.data();v['resource_admission']=True;bad=m.io.encode(v);path.write_bytes(bad)
    with pytest.raises(ValueError,match='reconstruction'):m.inspect(path,expected_sha256=m.io.digest(bad))
    with pytest.raises(ValueError,match='external pin'):m.inspect(path,expected_sha256=snap.identity)
