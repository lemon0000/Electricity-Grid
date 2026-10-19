from dataclasses import replace
from pathlib import Path

import pytest

from tests.test_rq2_normal_episode_binding_v1 import (
    api, bind, bound, supplied, legacy_request, declared_source, prepared_source,
    bound_source, base_bound_source, source_supplied)


@pytest.mark.parametrize('index', range(4))
def test_binding_guard_blocks_execution_and_restores_entries(index):
    targets = ((api.normal, 'run_source'), (api.episode.controller, 'supervise_selector'),
        (api.episode.controller.process, 'normal_task_child'),
        (api.episode.DevelopmentMixedSelectorEpisode, 'advance'))
    originals = [getattr(obj, name) for obj, name in targets]
    obj, name = targets[index]
    with pytest.raises(RuntimeError, match='forbidden'):
        with api.solver_free(): getattr(obj, name)()
    assert [getattr(obj, name) for obj, name in targets] == originals


def test_unknown_normal_cannot_supply_episode(bound, monkeypatch):
    request, _, packet, environment = bound
    calls = []
    def lost(*a, **k): calls.append(1); raise RuntimeError('lost native return')
    monkeypatch.setattr(api.normal.projection.capture, 'solve_once', lost)
    record = api.normal.run_source(request, expected_request_identity=api.normal.request_identity(request))
    assert record['solver_calls'] is None and not record['accepted']
    changed = (request, api.normal.replay._bytes(record), packet, environment)
    with pytest.raises(ValueError, match='accepted complete numerical normal plan'): bind(changed)
    assert calls == [1]


def test_declaration_drift_during_binding_is_refused(bound, monkeypatch, tmp_path):
    path = Path(bound[0].source.config_path).resolve()
    assert path.is_relative_to(tmp_path.resolve())
    original = api._origins
    def drift(packet):
        result = original(packet)
        path.write_bytes(path.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(api, '_origins', drift)
    with pytest.raises(ValueError): bind(bound)


def test_single_normal_diagnostic_has_no_episode_dependency(supplied):
    n = api.normal
    plan = n.budgets.SingleNormalResourcePlan(supplied.budget.normal, supplied.budget.envelope,
        supplied.resource_plan.serial_budget)
    budget = n.budgets.budget_for_task(plan, task_id='normal', max_observed_wall_seconds=121.,
        max_process_peak_working_set_bytes=8*1024**3, max_core_evidence_payload_bytes=16*1024**2)
    request = replace(supplied, normal=replace(supplied.normal, resource_plan=plan, budget=budget,
        expected_normal_execution_identity=n.kernel.normal_execution_identity(
            supplied.source.expected_input_identity, supplied.source.expected_scale,
            supplied.normal.specification, budget)))
    n.request_identity(request)
    with pytest.raises(ValueError, match='single-normal diagnostic'):
        api.binding_identity(request, normal_sha256='1'*64, episode_sha256='2'*64,
            max_normal_bytes=32*1024**2, max_episode_bytes=api.transport.LIMIT)
