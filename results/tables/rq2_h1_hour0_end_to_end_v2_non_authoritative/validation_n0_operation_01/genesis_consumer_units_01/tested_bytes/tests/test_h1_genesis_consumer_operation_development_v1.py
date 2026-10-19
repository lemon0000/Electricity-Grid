"""Real Snapshot/Genesis observations over explicit fake N0 and common routes.

This exercises consumer code and guards; it is not numerical source or Job
acceptance. Scientific equivalence and the connected workflow have separate
bounded diagnostics.
"""
from dataclasses import replace
from importlib.metadata import version
import json
from pathlib import Path

import experiments
import pytest

from tests.test_h1_common_genesis_validation_operation_development_v1 import case,create,setup,legacy_setup
from tests.test_h1_selector_phase_handoff_development_v5 import static_identity_test_seam
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.h1_hour0_synthetic_harness_v3 import load


@pytest.fixture
def observed(case,monkeypatch,no_solver):
    c=case;s=c.phase_setup
    s.manifest=replace(s.manifest,solver_specification=replace(s.manifest.solver_specification,
        name='gurobi',expected_package_version=version('gurobipy')))
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
            with create(c) as owner:yield c,snapshot,owner,config,receipt
        c.closed_observation_receipt=receipt()


def test_real_snapshot_capture_binds_active_genesis_and_two_common_calls(observed):
    c,snapshot,owner,config,receipt=observed
    raw=snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert json.loads(raw)['implementation']==snapshot.implementation_identity()
    assert owner._holder.inspect()==()
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    # The fixture checks the closed receipt after the real owner has closed.
    assert c.sessions[-1]._common_calls==2 and c.sessions[-1].closed


@pytest.mark.parametrize('symbol',['implementation_identity','_owner_view','_document'])
def test_first_capture_rejects_changed_consumer_function_before_acquisition(observed,monkeypatch,symbol):
    c,snapshot,owner,config,receipt=observed
    with monkeypatch.context() as patch:
        patch.setattr(snapshot,symbol,lambda *args,**kw:'f'*64)
        with pytest.raises(ValueError,match='original Genesis consumer'):
            snapshot.capture_reference(owner,config,max_archive_bytes=2**30)
    assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    assert owner.inspect()['stage']==3
