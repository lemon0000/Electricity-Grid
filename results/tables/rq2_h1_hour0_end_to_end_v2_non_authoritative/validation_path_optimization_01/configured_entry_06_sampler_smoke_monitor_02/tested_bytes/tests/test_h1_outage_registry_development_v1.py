from fractions import Fraction as Q
import gzip
import json

import pytest

from experiments import h1_outage_registry_development_v1 as m


@pytest.fixture(scope='module')
def training():
    return m._load('training')


@pytest.fixture(scope='module')
def holdout():
    return m._load('holdout')


def synthetic(training, observations, *, start=0):
    context = dict(training)
    context['catalog_entries'] = [dict(source_start=start,observed_end_inclusive=start+len(observations)-1,
        outage_seed=20260822,chain_id='power:training:outage_seed=20260822')]
    rows = {}
    for i,(eid,kind,uid) in enumerate(observations):
        row = dict(training['rows'][20260822][start+i])
        row.update(active_event_id=eid,active_component_type=kind,active_component_uid=uid)
        rows[start+i] = row
    context['rows'] = {20260822:rows}
    return context


def initial_generator(monkeypatch, uid='101_CT_1'):
    monkeypatch.setattr(m.frozen,'prefix_overlay',lambda components,seed,hour: (('init','generator',uid),))


def test_offline_archive_is_lossless_and_reproducible(tmp_path):
    expected = json.loads((m.ARCHIVE/'manifest.json').read_bytes())
    actual = m.extractor.build(tmp_path)
    assert actual == expected
    for split in ('training','holdout'):
        name = expected['members'][split]['path']
        assert (tmp_path/name).read_bytes() == (m.ARCHIVE/name).read_bytes()
    assert sum(e['row_count'] for e in actual['members'].values()) == 25704


def test_holdout_reader_never_decodes_mixed_or_training_source(monkeypatch):
    def reject(*args,**kwargs):
        raise AssertionError('original semantic row/event reader forbidden')
    monkeypatch.setattr(m.frozen,'_read_rows',reject)
    monkeypatch.setattr(m.old.source.audit,'_power_audit',reject)
    monkeypatch.setattr(m.old.source.audit,'_load_outage_events',reject)
    original = gzip.decompress
    allowed = (m.ARCHIVE/'holdout.json.gz').read_bytes()
    seen = []
    def decode(data):
        assert data == allowed
        seen.append(1)
        return original(data)
    monkeypatch.setattr(gzip,'decompress',decode)
    ctx = m._load('holdout')
    r = m._prepare(ctx,raw_start=4440,hours=2,outage_seed=20260822)
    assert len(seen) == 1 and r.audit['origin_kind'] == 'generated_same_split_boundary'
    assert all(row['split']=='holdout' for row in r.audit['current_rows'])


@pytest.mark.parametrize('seed,uid',[(20260822,None),(20260823,'B14'),(20260824,'A15')])
def test_chronology_first_action_never_calls_disclose(training,monkeypatch,seed,uid):
    def reject(*args,**kwargs):
        raise AssertionError('first action must not manufacture a report')
    monkeypatch.setattr(m.events,'disclose_current',reject)
    r = m._prepare(training,raw_start=0,hours=1,outage_seed=seed)
    assert type(r.actions[0]) is m.FirstAction
    assert r.audit['predecessor_source_hour'] is None
    assert r.audit['completed_actions']==1 and r.audit['last_revealed_raw_hour']==0
    view = m.decision_view(r.actions[0])
    assert view['started'] is None and view['ended'] is None and view['repair_cap_exact'] is None
    assert (None if view['active'] is None else view['active']['uid']) == uid
    if r.origin.active: assert r.origin.active.observed_start_hour is None


def test_raw1_first_report_and_repair_cap_lookup(training,monkeypatch):
    initial_generator(monkeypatch,'107_CC_1')
    ctx = synthetic(training,[('init','generator','107_CC_1'),('','',''),('','','')])
    original = m.events.disclose_current
    calls=[]
    def watch(state,report):
        calls.append(report.source_hour)
        return original(state,report)
    monkeypatch.setattr(m.events,'disclose_current',watch)
    r = m._prepare(ctx,raw_start=0,hours=3,outage_seed=20260822)
    # Creation plus deterministic validation in decision_view, never a raw0 report.
    assert calls == [1,2,1,2]
    assert r.actions[0].current_state.source_hour==0
    assert r.actions[1].step.before.source_hour==0 and r.actions[1].step.after.source_hour==1
    assert m.decision_view(r.actions[1])['repair_cap_exact'] == ['1242','5']
    assert r.actions[1].step.repaired_generator_return_limit_mw == 248.4
    assert r.actions[2].step.repaired_generator_return_limit_mw is None


@pytest.mark.parametrize('second', [('init','generator','101_CT_1'),('next','branch','B14'),('next','generator','107_CC_1')])
def test_return_cap_belongs_only_to_ended_generator(training,monkeypatch,second):
    initial_generator(monkeypatch)
    ctx=synthetic(training,[('init','generator','101_CT_1'),second])
    r=m._prepare(ctx,raw_start=0,hours=2,outage_seed=20260822)
    expected=None if second[0]=='init' else 20.
    assert r.actions[1].step.repaired_generator_return_limit_mw==expected


def test_branch_return_has_no_generator_cap(training):
    ctx=dict(training)
    row=dict(training['rows'][20260823][1]);row.update(active_event_id='',active_component_type='',active_component_uid='')
    ctx['rows']={20260823:{0:training['rows'][20260823][0],1:row}}
    r=m._prepare(ctx,raw_start=0,hours=2,outage_seed=20260823)
    assert r.actions[1].step.ended.component.uid=='B14'
    assert r.actions[1].step.repaired_generator_return_limit_mw is None


@pytest.mark.parametrize('seed,start,uid',[(20260822,4440,'202_CT_2'),(20260823,4560,None),(20260824,4632,None)])
def test_only_approved_holdout_gaps_replay_prefix(holdout,monkeypatch,seed,start,uid):
    original=m.frozen.prefix_overlay;calls=[]
    def watch(components,seed,hour):
        calls.append((seed,hour))
        return original(components,seed,hour)
    monkeypatch.setattr(m.frozen,'prefix_overlay',watch)
    r=m._prepare(holdout,raw_start=start,hours=2,outage_seed=seed)
    assert calls==[(seed,start-1)]
    assert r.audit['origin_kind']=='generated_same_split_boundary' and not r.audit['existing_same_chain_row']
    assert (None if r.origin.active is None else r.origin.active.component.uid)==uid


def test_ordinary_boundary_and_generated_label_are_decision_neutral(holdout):
    generated=m._prepare(holdout,raw_start=4440,hours=2,outage_seed=20260822)
    ctx=dict(holdout);ctx['rows']=dict(holdout['rows']);group=dict(ctx['rows'][20260822])
    row=dict(group[4440]);row.update(generated.audit['boundary_evidence'])
    from datetime import datetime,timedelta
    row['source_hour']='4439';row['timestamp']=(datetime.fromisoformat(row['timestamp'])-timedelta(hours=1)).isoformat()
    group[4439]=row;ctx['rows'][20260822]=group
    ordinary=m._prepare(ctx,raw_start=4440,hours=2,outage_seed=20260822)
    assert ordinary.audit['origin_kind']=='existing_same_chain_boundary'
    assert ordinary.decision_identity==generated.decision_identity


def test_future_suffix_event_labels_and_clock_are_not_decision_inputs(training):
    a=m._prepare(training,raw_start=24,hours=2,outage_seed=20260822)
    ctx=dict(training);ctx['rows']=dict(training['rows']);rows=dict(ctx['rows'][20260822])
    from datetime import datetime,timedelta
    for h in (23,24,25):
        row=dict(rows[h]);row['timestamp']=(datetime.fromisoformat(row['timestamp'])+timedelta(days=1)).isoformat()
        if row['active_event_id']:row['active_event_id']='renamed_'+row['active_event_id']
        rows[h]=row
    rows[26]=dict(rows[26],active_event_id='future_bad',active_component_type='future',active_component_uid='future')
    ctx['rows'][20260822]=rows
    b=m._prepare(ctx,raw_start=24,hours=2,outage_seed=20260822)
    assert a.audit!=b.audit and a.decision_identity==b.decision_identity


@pytest.mark.parametrize('observations,match',[
    ([('init','generator','101_CT_1'),('replacement','generator','101_CT_1')],'hidden same-hour'),
    ([('init','generator','101_CT_1'),('init','branch','B14')],'changed component'),
    ([('init','generator','101_CT_1'),('','',''),('init','generator','101_CT_1')],'reappeared'),
    ([('init','generator','101_CT_1'),('next','','G')],'incomplete'),
])
def test_source_event_corruption_rejected(training,monkeypatch,observations,match):
    initial_generator(monkeypatch)
    with pytest.raises(ValueError,match=match):
        m._prepare(synthetic(training,observations),raw_start=0,hours=len(observations),outage_seed=20260822)


@pytest.mark.parametrize('start,hours,seed',[(True,1,20260822),(0,True,20260822),(0,193,20260822),(0,1,True),(1,1,20260822),(0,1,7)])
def test_invalid_or_non_catalog_coordinates(training,start,hours,seed):
    with pytest.raises(ValueError):m._prepare(training,raw_start=start,hours=hours,outage_seed=seed)


def test_missing_unapproved_predecessor_not_repaired(training):
    ctx=dict(training);ctx['rows']=dict(training['rows']);rows=dict(ctx['rows'][20260822]);del rows[23];ctx['rows'][20260822]=rows
    with pytest.raises(ValueError,match='outside approved'):
        m._prepare(ctx,raw_start=24,hours=1,outage_seed=20260822)


def test_public_prepare_rereads_and_rejects_drift(training,monkeypatch):
    calls=[]
    def load(split):
        calls.append(split)
        c=dict(training)
        if len(calls)>1:c['identity']='0'*64
        return c
    monkeypatch.setattr(m,'_load',load)
    with pytest.raises(ValueError,match='changed during'):
        m.prepare(split='training',raw_start=0,hours=1,outage_seed=20260822,expected_registry_identity=training['identity'])
    assert len(calls)==2


def test_public_registry_pin_required(training):
    with pytest.raises(ValueError,match='identity mismatch'):
        m.prepare(split='training',raw_start=0,hours=1,outage_seed=20260822,expected_registry_identity='0'*64)
    with pytest.raises(TypeError):
        m.prepare(split='training',raw_start=0,hours=1,outage_seed=20260822,
                  expected_registry_identity=training['identity'],repair_limits=(999.,))


def test_repair_table_has_complete_exact_inventory_and_guards(training):
    assert len(training['caps'])==93
    assert training['caps']['107_CC_1']==Q(1242,5)
    assert training['caps']['123_STEAM_3']==240
    assert len(training['protocol'].components)==211
    assert all(c.uid not in ('B11','C11') for c in training['protocol'].components)


def test_all_catalog_entries_retained_and_only_development_gate():
    result=m.audit_catalog()
    assert {k:v['power_entries'] for k,v in result['families'].items()}=={
        'training_lb':523,'training_ub':523,'training_b6_actual':523,'holdout':512}
    assert result['unique_entries']==1035
    assert result['origin_kinds']=={'chronology_origin':3,'generated_same_split_boundary':3,'existing_same_chain_boundary':1029}
    assert result['source_input_unresolved']==0 and result['obligations_removed']==0
    for key in ('full_boundary_coverage_verified','full_192_hour_execution_verified','physical_consumer_connected',
                'persistent_lane_owner_implemented','formal_execution_ready','formal_result','resource_admission','native_execution_authorized'):
        assert result[key] is False
