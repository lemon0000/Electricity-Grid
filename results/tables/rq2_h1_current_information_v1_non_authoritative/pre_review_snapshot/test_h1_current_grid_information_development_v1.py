from copy import copy,deepcopy
from dataclasses import replace
from datetime import timedelta
import json
import pickle

import pytest

from experiments import h1_current_grid_information_development_v1 as m
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests.test_rq2_v2_normal_obligation_controller_development_v1 import real,synthetic_controller
from tests.test_h1_timed_job_controller_development_v1 import install_launcher,step
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved


def boundary(p,generation=20.,on=True):
    """Synthetic pure projection input, not an accepted child or publication."""
    return m.source._owned(m.source.H1NormalBoundary,network_identity=p.network.identity,completed_hours=1,
        units=(('G1',on,generation,1 if on else p.before.units[0][3]+1),),evidence_role='numerical_lex_candidate')


def test_current_view_is_minimal_and_not_old_information():
    p=packet();view=m._decision(p,boundary(p))
    assert view.relative_hour==0
    assert view.normal.previous_commitment==(('G1',False),)
    assert view.normal.commitment==(('G1',True),)
    assert view.normal.generation_mw==(('G1',20.),)
    assert view.current.dc_baseline_mw==0.
    assert type(view) is m.H1CurrentInformation
    assert not isinstance(view,m.legacy.CurrentGridInformation)
    assert set(json.loads(view.decision_bytes))=={'contract','relative_hour','network','current','normal'}
    for forbidden in ('forecast','pre_episode','allowed_plan','source','pair','split','seed','ordinal','job','solver','lock'):
        assert forbidden.encode() not in view.decision_bytes
    for cls in (m.H1CurrentInformation,m.H1CurrentConditions,m.H1CurrentNormalView,m.H1NormalAuditEnvelope):
        with pytest.raises(TypeError):cls()
    for clone in (copy,deepcopy,pickle.dumps,lambda v:replace(v,relative_hour=1)):
        with pytest.raises(TypeError):clone(view)


def test_future_and_audit_clock_do_not_enter_decision():
    class Poison:
        def __iter__(self):raise AssertionError('future read')
        def __deepcopy__(self,memo):raise AssertionError('future copy')
        def __len__(self):raise AssertionError('future count')
    data=fixture(3).data
    first=packet(data)
    shifted=replace(data.hourly_points[0],timestamp=data.hourly_points[0].timestamp+timedelta(days=500))
    second=packet(replace(data,hourly_points=Poison()),shifted)
    assert first.audit_identity!=second.audit_identity
    a=m._decision(first,boundary(first));b=m._decision(second,boundary(second))
    assert a.decision_bytes==b.decision_bytes and a.decision_identity==b.decision_identity


def test_current_generation_commitment_and_base_change_decision():
    p=packet();base=m._decision(p,boundary(p))
    assert m._decision(p,boundary(p,21.)).decision_identity!=base.decision_identity
    assert m._decision(p,boundary(p,0.,False)).decision_identity!=base.decision_identity
    row=replace(p.inputs.data.hourly_points[0],demand_by_bus_mw={1:21.,2:0.})
    changed=packet(p.network.data,row)
    assert m._decision(changed,boundary(changed)).decision_identity!=base.decision_identity


def test_old_information_and_wrong_normal_boundary_rejected():
    p=packet()
    with pytest.raises(ValueError):m._decision(object(),boundary(p))
    bad=m.source._owned(m.source.H1NormalBoundary,network_identity='1'*64,completed_hours=1,
        units=boundary(p).units,evidence_role='numerical_lex_candidate')
    with pytest.raises(ValueError):m._decision(p,bad)


def test_fresh_accepted_prefix_to_information_and_pin_failures(tmp_path,real,environment,synthetic_reports,monkeypatch):
    # Real pinned Resolver plus explicit synthetic source/catalog seam. One
    # saved-report Windows Job; no native solve and no real RTS feasibility claim.
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=synthetic_controller(tmp_path/'information_non_authoritative',environment,real,monkeypatch)
    try:
        outcome=step(c,environment)
        observation=c.last_obligation_observation
        args=dict(expected_binding_sha256=observation.header_sha256,
            expected_terminal_sha256=observation.terminal_sha256,completed_hours=1)
        envelope=m.prepare(c._lease.root,**args)
        audit=json.loads(envelope.audit_payload)
        assert audit['completed_stages']==3 and audit['normal_after']['completed_hours']==1
        assert audit['decision_identity']==envelope.decision.decision_identity
        assert audit['controller_terminal_sha256']==observation.terminal_sha256
        assert audit['normal_before']['units'][0][1] is False
        assert envelope.decision.normal.commitment==(('G1',True),)
        assert not audit['policy_visible'] and not audit['common_prefix_publication_verified']
        assert not audit['reference_or_actual_ready'] and not audit['formal_result']
        with pytest.raises(ValueError):m.prepare(c._lease.root,**dict(args,expected_binding_sha256='1'*64))
        with pytest.raises(ValueError):m.prepare(c._lease.root,**dict(args,expected_terminal_sha256='1'*64))
        # Changing the persisted accepted projection is caught by full replay.
        projection=c._lease.root/'job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative/projection.bin'
        raw=projection.read_bytes();projection.write_bytes(raw+b' ')
        with pytest.raises(ValueError):m.prepare(c._lease.root,**args)
        projection.write_bytes(raw)
        assert c.inspect()==outcome
    finally:c.close()
