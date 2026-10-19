"""Real Snapshot/Genesis observations over explicit fake N0 and common routes.

This exercises consumer code and guards; it is not numerical source or Job
acceptance. Scientific equivalence and the connected workflow have separate
bounded diagnostics.
"""
from contextlib import ExitStack
from dataclasses import replace,fields,is_dataclass
from fractions import Fraction
from importlib.metadata import version
import json
from pathlib import Path
from types import SimpleNamespace,ModuleType

import experiments
import pytest

from tests.test_h1_common_genesis_validation_operation_development_v1 import case,create,setup,legacy_setup
from tests.test_h1_selector_phase_handoff_development_v5 import static_identity_test_seam,load_handoff
from tests.test_h1_selector_parent_controller_development_v3 import ExplicitSyntheticPreparedCurrent,sequence_factory
from tests import h1_hour0_synthetic_harness_v3 as parent_cases
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.h1_hour0_synthetic_harness_v3 import load


@pytest.fixture
def observed(case,monkeypatch,no_solver,request,sequence_factory,tmp_path):
    c=case;s=c.phase_setup
    s.manifest=replace(s.manifest,solver_specification=replace(s.manifest.solver_specification,
        name='gurobi',expected_package_version=version('gurobipy')))
    if getattr(request,'param',None)=='unresolved':
        first=s.manifest.lanes[0]
        s.manifest=replace(s.manifest,lanes=(replace(first,
            mechanism=replace(first.mechanism,flexible_fraction=Fraction(1,2))),))
    elif getattr(request,'param',None)=='three':
        first=s.manifest.lanes[0]
        s.manifest=replace(s.manifest,lanes=tuple(replace(first,lane_id=name) for name in ('a','b','c')))
    for hour,current in tuple(s.currents.items()):
        if not is_dataclass(current.prepared_current):
            values={field.name:getattr(current,field.name) for field in fields(current)}
            values['prepared_current']=ExplicitSyntheticPreparedCurrent(**vars(current.prepared_current))
            s.currents[hour]=c.host.phase.source.normal._owned(c.host.phase.source.ExactSourceCurrent,**values)
    prepare_parent=None
    if getattr(request,'param',None) in ('unresolved','three'):
        # All explicit producer/identity/I/O seams precede the active Genesis
        # observation. Only the consumer imports and snapshots follow it.
        prepare_parent=parent_cases.harness.__wrapped__(None,sequence_factory,monkeypatch,tmp_path,prepare_only=True)
    with static_identity_test_seam(monkeypatch):
        context,receipt=c.adapter.operation(c.host)
        with context:
            root=Path(c.host.__file__).parent
            snapshot=load(str(root/'h1_selector_input_snapshot_development_v2.py'),
                'experiments.h1_selector_input_snapshot_development_v2',monkeypatch,
                {'h1_common_owner_genesis_development_v2':c.host})
            monkeypatch.setattr(experiments,'h1_selector_input_snapshot_development_v2',snapshot)
            frame=s.currents[0].prepared_current.frame
            budget=snapshot.sequence.configuration_api.process.TaskProcessBudget(
                300,.05,512*1024**2,768*1024**2,2)
            config=snapshot.sequence.configuration_api.SelectorRunConfiguration(frame.normal_network_identity,
                tuple(g.uid for g in frame.info.network.units),s.manifest.reference_selector,
                s.manifest.actual_selector,s.manifest.solver_specification,s.manifest.replay_limits,
                budget,budget,2,2)
            with create(c) as owner:
                if prepare_parent is not None:
                    monkeypatch.setattr(parent_cases.canonical.worker,'snapshot',snapshot)
                    monkeypatch.setattr(parent_cases.canonical.inspection,'snapshot',snapshot)
                    c.parent_harness=prepare_parent(SimpleNamespace(owner=owner,config=config,s=s,case=c,cap=2**30))
                yield c,snapshot,owner,config,receipt
        c.closed_observation_receipt=receipt()
        assert c.closed_observation_receipt['all_aliases_restored']
        assert c.closed_observation_receipt['all_private_sessions_cleared']
        if hasattr(c,'expected_external_success'):
            external=c.closed_observation_receipt['external_receipts']
            assert len(external)==1 and external[0]['guards_released']
            assert external[0]['complete'] is c.expected_external_success
            assert external[0]['handoff_committed'] is c.expected_external_success
            if c.expected_external_success:assert external[0]['original_resources_closed']
            else:assert external[0]['first_failure']
        with (tmp_path/'genesis_observation_closed.json').open('x',encoding='utf-8') as stream:
            json.dump(c.closed_observation_receipt,stream,indent=2)


def test_real_snapshot_capture_binds_active_genesis_and_two_common_calls(observed):
    c,snapshot,owner,config,receipt=observed
    raw=snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert json.loads(raw)['implementation']==snapshot.implementation_identity()
    assert owner._holder.inspect()==()
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    # The fixture checks the closed receipt after the real owner has closed.
    assert c.sessions[-1]._common_calls==2 and c.sessions[-1].closed


@pytest.mark.parametrize('symbol',['implementation_identity','_owner_view','_document','encode','sequence'])
def test_first_capture_rejects_changed_consumer_function_before_acquisition(observed,monkeypatch,symbol):
    c,snapshot,owner,config,receipt=observed
    with monkeypatch.context() as patch:
        if symbol=='sequence':
            foreign=ModuleType('foreign_snapshot_sequence');vars(foreign).update(vars(snapshot.sequence))
            patch.setattr(snapshot,symbol,foreign)
        else:patch.setattr(snapshot,symbol,lambda *args,**kw:'f'*64)
        with pytest.raises(ValueError,match='original Genesis consumer|canonical Genesis Snapshot aliases'):
            snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    assert owner.inspect()['stage']==3


@pytest.mark.parametrize('observed',['unresolved'],indirect=True)
@pytest.mark.parametrize('fault',['none','body','validation_commit'])
def test_real_handoff_closes_external_observation_after_commit_or_failure(
        observed,sequence_factory,monkeypatch,tmp_path,fault):
    c,snapshot,genesis,config,receipt=observed
    c.expected_external_success=fault=='none'
    h=c.parent_harness
    faults={};consumer=load_handoff(h,monkeypatch,genesis=c.host,validation_faults=faults)
    retained=[]
    def retain(path,before,after):
        if fault=='body':raise RuntimeError('synthetic handoff body failure')
        retained.append(after);return after
    with h.module.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        faults['validation_commit']=fault=='validation_commit'
        with consumer.Handoff(genesis,(reference,issued),{'joint':None},retain_head=retain,
                max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2) as owner:
            if fault=='none':
                result=owner.consume();assert result['completed_hours']==1
                assert owner._state=='complete' and genesis.closed
            else:
                with pytest.raises(RuntimeError,match='synthetic'):owner.consume()
                assert owner._state=='failed'
    assert not genesis._operation.locked() and not c.guard.locked() and not c.extra.locked()
    if not genesis.closed:genesis.close()
