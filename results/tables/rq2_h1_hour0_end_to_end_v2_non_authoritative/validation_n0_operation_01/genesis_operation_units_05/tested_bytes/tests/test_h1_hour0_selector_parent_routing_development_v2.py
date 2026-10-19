"""Exercise successor reference/Actual aliases before the long full-chain exit.

Synthetic common/source and fabricated native/lifecycle seams are explicit.
These regression cases do not replace the three independent N0 integration.
"""
from dataclasses import replace

import pytest

from experiments import h1_selector_parent_controller_development_v2 as parent
from experiments import h1_selector_phase_handoff_development_v2 as handoff
from tests import test_h1_selector_parent_controller_development_v1 as parent_cases
from tests import test_h1_selector_phase_handoff_multi_actual_development_v1 as multi_cases
from tests.test_h1_hour0_persistence_faults_development_v2 import (
    case,context,setup as base_setup,legacy_setup,no_solver)
from tests.h1_hour0_synthetic_harness_v2 import harness
from tests.test_h1_selector_parent_controller_development_v1 import (
    sequence_factory,
    test_reference_parent_issues_only_after_joint_terminal_and_replays,
    test_actual_requires_live_reference_and_closing_reference_invalidates_completion)


@pytest.fixture
def setup(base_setup):
    state=base_setup;lane=state.manifest.lanes[0]
    state.manifest=replace(state.manifest,lanes=(lane,replace(lane,lane_id='second')))
    return state


@pytest.fixture(autouse=True)
def routed_cases(monkeypatch):
    monkeypatch.setattr(parent_cases,'canonical',parent)
    monkeypatch.setattr(multi_cases,'canonical',handoff)
    original=multi_cases.load
    def load(file,name,patch,dependencies=None):
        if dependencies:
            dependencies={key.replace('h1_selector_parent_controller_development_v1',
                'h1_selector_parent_controller_development_v2'):value for key,value in dependencies.items()}
        result=original(file,name,patch,dependencies)
        assert result.SCHEMA==handoff.SCHEMA and result.snapshot is parent.worker.snapshot
        return result
    monkeypatch.setattr(multi_cases,'load',load)


def test_two_successor_actuals_commit_the_exact_shared_reference(harness,monkeypatch):
    assert harness.module.worker is parent.worker
    multi_cases.test_two_complete_actuals_share_exact_reference_and_commit_all_lanes(harness,monkeypatch)
