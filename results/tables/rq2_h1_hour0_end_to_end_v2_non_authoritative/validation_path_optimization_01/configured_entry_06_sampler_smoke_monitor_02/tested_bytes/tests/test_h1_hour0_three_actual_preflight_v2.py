"""Exercise the complete integration helper over a tiny declared source seam.

Real selector/business replay and persistent handoff/reopen; fabricated common
roster/manifest/source, solver and Job lifecycle. Lane configurations are cloned,
so this covers three-Actual orchestration, not the real three-arm policy contrast.
This does not replace the independent three-N0 chain.
"""
from dataclasses import replace
from fractions import Fraction as Q
import json
from types import SimpleNamespace
from time import perf_counter
from threading import Lock

import pytest

from tests.test_h1_hour0_persistence_faults_development_v2 import (
    case as common_case, context, setup as phase_setup, legacy_setup, no_solver)
from tests import h1_group_selector_integration_helpers_v2 as helper
from tests.test_rq2_normal_h1_source_v1 import packet


@pytest.fixture
def case(common_case,monkeypatch):
    c=common_case
    roster=c.roster;bootstrap=roster._owner
    roster._original_operation=c.guard
    bootstrap._original_operation=Lock()
    roster._operation=c.guard
    roster._owner_guard=bootstrap._original_operation
    roster._original_owner=bootstrap
    bootstrap._operation=bootstrap._original_operation
    def enter():
        if not c.guard.acquire(False):raise ValueError('roster active')
        if not bootstrap._original_operation.acquire(False):
            c.guard.release()
            raise ValueError('bootstrap active')
    def leave():
        bootstrap._original_operation.release();c.guard.release()
    def check():
        assert c.guard.locked() and bootstrap._original_operation.locked()
    monkeypatch.setattr(roster,'_enter',enter)
    monkeypatch.setattr(roster,'_leave',leave)
    monkeypatch.setattr(roster,'_check',check)
    return c


@pytest.fixture
def setup(phase_setup):
    s=phase_setup
    phase=helper.handoff.phase
    lane=s.manifest.lanes[0]
    s.manifest=replace(s.manifest,lanes=tuple(replace(lane,lane_id=k)
        for k in ('cfe_only_shared','joint','network_only_shared')))
    original=s.currents[0]
    physical=phase.selection.physical
    p=packet(raw_workload='0',relative_hour=0)
    after=physical._owned(type(p.before),network_identity=p.network.identity,
        completed_hours=1,units=(('G1',True,20.,1),),evidence_role='numerical_lex_candidate')
    frame=physical._frame(p,after)
    audit=json.loads(original.source_projection_audit_payload)
    audit['source_observation_audit_payload']['workload_source_row']['workload_fraction']='0'
    s.windows['workload',0]['rows'][0]['workload_fraction']='0'
    scientific=phase.encode(dict(hour=0,normal=p.input_identity,w=['0','1'],cfe=['3','5']))
    s.currents[0]=phase.source.normal._owned(type(original),
        prepared_current=SimpleNamespace(frame=frame,
            source_origin=original.prepared_current.source_origin,
            source_action=original.prepared_current.source_action),
        workload_exact=Q(0),source_cfe_at_alpha_one_exact=Q(3,5),
        exogenous_scientific_payload=scientific,
        source_observation_identity=phase.digest(audit['source_observation_audit_payload']),
        source_projection_audit_payload=phase.encode(audit))
    return s


def test_actual_helper_three_lanes_paired_commit_and_reopen(context,monkeypatch,tmp_path):
    traces=[];start=perf_counter()
    def trace(label):
        traces.append(label)
        print(json.dumps(dict(label=label,elapsed_seconds=perf_counter()-start)),flush=True)
    outcome=helper.consume_zero_workload(context.owner,context.config,monkeypatch,
        tmp_path,trace)
    context.owner.close()
    replay=helper.reopen_paired(outcome,trace)
    assert replay['paired_lanes']==3 and replay['completed_hours']==1
    assert replay['replayed_from_saved_records'] and not replay['formal_result']
    assert outcome['real_native_calls']==0 and outcome['synthetic_selector_parents']==4
    assert traces[-1]=='paired_owner_reopen_replay_and_close'
    assert sum(label in {'Actual_'+c.lane_id for c in context.s.manifest.lanes} for label in traces)==3
    assert 'paired_commit_and_readback' in traces
