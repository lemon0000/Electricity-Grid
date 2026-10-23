"""Mechanical complete-P2 requests; every model/solver/writer route is denied."""
from copy import deepcopy
from collections import Counter
from dataclasses import replace

import pytest

from src import staged_rts24_p2_packet_v1 as prep
from experiments import staged_rts24_native_probe_v1 as p1


@pytest.fixture(autouse=True)
def deny_execution(monkeypatch):
    from src import staged_rts24_numeric_interface_v1 as numeric,staged_rts24_highs_backend_v1 as backend
    from src import staged_rts24_journal_v2 as journal,staged_rts24_evidence_store_v1 as codec
    def denied(*a,**kw):pytest.fail('numeric/writer/replay effect in preparation')
    for module,names in [(prep.c,['build_point_model']),(numeric,['compile_problem','import_snapshot']),
        (backend,['make_model','call_highs']),(journal,['create_session','begin_step','commit_step','finish','reopen']),
        (codec,['publish']),(codec.EvidenceStore,['put'])]:
        for name in names:monkeypatch.setattr(module,name,denied)


@pytest.fixture(scope='module')
def fixture():return prep.c.load_fixture()


def test_complete_public_schedule_and_future_bindings(fixture):
    assert (fixture.first_hour,fixture.registration_end,fixture.observation_end)==(-2,4,8)
    value=prep.packet(fixture);rows=value['schedule']
    assert Counter(r['role'] for r in rows)==prep.ROLES
    assert value['counts']==dict(points=319,QP=160,LP=159,actual=41,contract=278,economic_kkt=12,
        child_lp_kkt=159,primal_point=148,static_request_identities=309,dynamic_actual_request_identities=10,
        successful_path_model_builds=1276,successful_path_imports=638,schedule_generation_request_objects=326,
        validation_request_objects_per_pass=316,validation_passes_for_prepare=2,full_preparation_request_objects=958)
    assert value['schedule_sha']==prep.digest(rows)
    assert all(value[k] is False for k in ('native_authorized','formal_result','resource_admission','execution_supported'))
    assert [r['ordinal'] for r in rows if r['role']=='normal_contract_C']==[42,181]
    assert [r['ordinal'] for r in rows if r['role']=='actual_P']==[4,8,12,17,21,25,29,33,37,41]
    assert all(r['request_sha'] is None for r in rows if r['role']=='actual_P')


def test_all_original_P1_requests_preserved_as_P2_subset(fixture):
    old=p1.request_schedule(fixture);new=prep.build_schedule(fixture)
    keys=('hour','role','objective','request_sha','parent_request_sha','bound_query_sha','dynamic_reason')
    for prior in old:
        matches=[r for r in new if all(r[k]==prior[k] for k in keys) and r['outage']==prep.c.plain(prior['outage'])]
        assert len(matches)==1
    assert len(old)==31


def test_schedule_serialization_is_deterministic_and_valid(fixture):
    import json
    rows=prep.build_schedule(fixture)
    decoded=json.loads(json.dumps(rows))
    prep.validate_schedule(decoded,fixture)
    assert prep.digest(decoded)==prep.digest(rows)==prep.digest(prep.build_schedule(fixture))


@pytest.mark.parametrize('fault',['missing','cycle','parent_request','carry','contingency','future_bound','actual_request','objective','reference_dependency','static_sha','extra_future'])
def test_invalid_packet_edges_or_invented_future_results_are_refused(fixture,fault):
    rows=deepcopy(prep.build_schedule(fixture))
    if fault=='missing':rows.pop()
    elif fault=='cycle':rows[1]['parent_slot']=2
    elif fault=='parent_request':rows[1]['parent_request_sha']='0'*64
    elif fault=='carry':rows[8]['state_after_actual_slot']=4
    elif fault=='contingency':rows[44]['outage']=rows[43]['outage']
    elif fault=='future_bound':rows[0]['bound_query_sha']='0'*64
    elif fault=='actual_request':rows[3]['request_sha']='0'*64
    elif fault=='objective':rows[1]['objective']='min_curtailment'
    elif fault=='static_sha':rows[1]['request_sha']='0'*64
    elif fault=='extra_future':rows[1]['actual_power_mw']=123
    else:rows[3]['reference_slots']=[1]
    with pytest.raises(ValueError):prep.validate_schedule(rows,fixture)


def test_extra_top_level_future_result_is_refused(fixture):
    value=prep.packet(fixture);value['solver_result_sha']='0'*64
    with pytest.raises(ValueError,match='packet fields'):prep.validate_packet(value,fixture)


@pytest.mark.parametrize('field,value',[('registration_end',9),('actual_duration',2)])
def test_expansion_requires_a_new_scope(fixture,field,value):
    with pytest.raises(ValueError):prep.build_schedule(replace(fixture,**{field:value}))
