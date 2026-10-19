"""Shared-window protocol with explicit fake Parent/numerical anchors.

Real bounded saved-file views and four distinct held locks are used. No live
Parent4/Handoff integration or scientific result is established by this fixture.
"""
import json
import os
from threading import Lock,get_ident
from types import SimpleNamespace as NS

import pytest

from experiments import h1_reference_validation_window_development_v1 as window
from tests.h1_reference_window_test_helpers_v1 import Literal
from tests.test_h1_selector_source_window_development_v2 import case


@pytest.fixture
def shared(case,monkeypatch):
    parent=case.parent
    monkeypatch.setattr(parent,'SCHEMA','h1_selector_parent_controller_development_v4')
    guards=tuple(obj._guard for obj in case.parents)
    for obj in (*case.actuals,case.ref):
        assert obj._guard.acquire(blocking=False)
        obj._reference_held=obj is not case.ref
    row=dict(parents=tuple((obj,obj._issued,obj._raw,obj._issued_bytes,obj._guard) for obj in case.parents),
             creator=(os.getpid(),get_ident()),failure=None,frames=[],window=None)
    original=parent.worker.snapshot._build.__globals__
    args=(case.reference_root,original['frame'],original['disclosure'],original['before'])
    reference=json.loads(case.actuals[0]._raw)['declaration']['reference']
    keywords=dict(expected_terminal_sha256=reference['terminal_sha256'],max_archive_bytes=reference['max_archive_bytes'],
                  run_configuration=original['config'],**original['arguments'])
    engines=[]

    def check_owner(observed,owner=None,*,borrowed=False):
        assert observed is row and all(guard.locked() for guard in guards)
        assert row['creator']==(os.getpid(),get_ident())
        if borrowed:assert any(owner is obj for obj in case.actuals)
        else:assert owner is None

    def bind(profile):
        row['window']=dict(kind='records_bundle' if profile=='records_bundle' else 'bundle')
        build_globals=dict(args=args,keywords=keywords)
        exec('def build():\n return inspect(*args,**keywords)\n',build_globals)
        rebuild_globals=dict(build=build_globals['build'])
        exec('def rebuild():\n return build()\n',rebuild_globals)
        scope_globals={}
        exec('def scope():\n return finish()\n',scope_globals)
        create=window._bind_post_negative_window if profile=='post_negative_bundle' else window._bind_parent_validation_window
        api=create(row,parent,check_owner,case.reference_sequence,
            caller_code=build_globals['build'].__code__,caller_globals=build_globals,
            rebuild_code=rebuild_globals['rebuild'].__code__,rebuild_globals=rebuild_globals,
            scope_code=scope_globals['scope'].__code__,scope_globals=scope_globals)
        engines.append(api)
        build_globals['inspect']=api['inspect'];scope_globals['finish']=api['finish']
        return NS(api=api,rebuild=rebuild_globals['rebuild'],scope=scope_globals['scope'])

    def borrow(bound,owner,count):
        row['frames'].append(dict(owner=owner))
        try:return [bound.rebuild() for _ in range(count)]
        finally:row['frames'].pop()

    try:yield NS(case=case,row=row,bind=bind,borrow=borrow,keywords=keywords,guards=guards)
    finally:
        for api in reversed(engines):
            api['close']()
            assert api['generator'].gi_frame is None
        for obj,guard in zip(case.parents,guards):
            obj._guard=guard
            if guard.locked():guard.release()
            obj._reference_held=False


@pytest.mark.parametrize('profile',('bundle','records_bundle','post_negative_bundle'))
def test_three_actuals_share_one_key_and_keep_exact_owner_sites(shared,profile):
    s=shared;bound=s.bind(profile);values=[]
    for owner in s.case.actuals:values.extend(s.borrow(bound,owner,window.SITE_COUNTS[profile]))
    receipt=bound.scope()
    assert receipt['logical_reference_inspects']==window.COUNTS[profile]
    assert receipt['original_reference_inspects']==2
    assert receipt['borrowed_reference_results']==window.COUNTS[profile]-1
    assert s.case.reference_counts['original']==2
    assert [item['logical_reference_inspects'] for item in receipt['parent_sites']]==[window.SITE_COUNTS[profile]]*3
    assert len({id(value) for value in values})==len(values)
    assert all(set(value)=={'request_sha256','replay'} for value in values)
    assert receipt['cross_actual_reference_payload_reuse'] and receipt['bookend_only_freshness']
    assert not receipt['same_per_parent_reference_observation_schedule']
    assert not receipt['between_owner_calls_ABA_covered']
    assert not receipt['canonical_reference_sequence']  # Explicit numerical fixture.
    assert not receipt['actual_output_inspection_cached']
    bound.api['close']()
    assert bound.api['generator'].gi_frame is None


@pytest.mark.parametrize('counts',((15,16,16),(16,16,15),(17,15,16),(48,0,0)))
def test_total_and_per_owner_counts_cannot_substitute_for_one_another(shared,counts):
    s=shared;bound=s.bind('bundle')
    with pytest.raises(ValueError,match='site count|per-owner request'):
        for owner,count in zip(s.case.actuals,counts):s.borrow(bound,owner,count)
        bound.scope()
    assert s.case.reference_counts['original']==1


@pytest.mark.parametrize('fault',('reference_guard','actual_guard','actual_raw','actual_completion','second_key'))
def test_later_actual_cannot_borrow_after_anchor_or_key_drift(shared,fault):
    s=shared;bound=s.bind('bundle');s.borrow(bound,s.case.actuals[0],16)
    if fault=='reference_guard':s.case.ref._guard=Lock()
    elif fault=='actual_guard':s.case.actuals[2]._guard=Lock()
    elif fault=='actual_raw':s.case.actuals[2]._raw+=b' '
    elif fault=='actual_completion':s.case.actuals[2]._issued_bytes+=b' '
    else:s.keywords['selector']=Literal('second key')
    with pytest.raises(ValueError):s.borrow(bound,s.case.actuals[1],1)
    assert s.case.reference_counts['original']==1


def test_rref_frame_is_never_a_borrowing_actual_site(shared):
    bound=shared.bind('bundle')
    with pytest.raises(ValueError,match='private snapshot build caller'):
        shared.borrow(bound,shared.case.ref,1)
    assert shared.case.reference_counts['original']==0
