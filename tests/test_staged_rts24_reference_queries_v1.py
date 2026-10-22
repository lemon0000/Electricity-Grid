"""Ordinary, no-solver equivalence checks for the selective-query successor."""
from dataclasses import replace

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
from src import staged_rts24_development_v1 as c
from src import staged_rts24_causal_v1 as old
from src import staged_rts24_causal_v2 as new
from src.staged_rts24_causal_audit_v1 import audit_execution as old_audit
from src.staged_rts24_causal_audit_v2 import audit_execution as new_audit
from src.staged_rts24_reference_queries_v1 import reference_requests


@pytest.fixture(autouse=True)
def no_solver(monkeypatch):
    import pyomo.environ as pyo
    def denied(*args, **kwargs): pytest.fail("ordinary test requested a solver")
    monkeypatch.setattr(pyo, "SolverFactory", denied)


@pytest.fixture(scope="module")
def public():
    return c.load_fixture()


@pytest.mark.parametrize("plan", ["on_time", "delayed"])
@pytest.mark.parametrize("clean", ["early", "late"])
@pytest.mark.parametrize("method", c.METHODS)
def test_public_subset_preserves_requests_order_id_and_consumed_metadata(public, plan, clean, method):
    for hour in range(public.first_hour, public.observation_end):
        full = c.hour_requests(public, plan, clean, method, hour)
        selected = reference_requests(public, plan, clean, method, hour)
        expected = tuple(r for r in full["requests"] if r.role.startswith(("reference_", "recovery_")))
        assert selected["requests"] == expected
        assert tuple(r.identity for r in selected["requests"]) == tuple(r.identity for r in expected)
        for key in ("observation", "reference_mw", "firm", "conditional", "reference_connection_shortfall_mw", "actual_outage"):
            assert selected[key] == full[key]
        assert selected["reference_node_upper_bound_including_actual"] == len(expected)+1
        assert selected["full_contract_requests_materialized"] is False


def test_descriptor_constructions_remove_only_unused_contract_nodes(public, monkeypatch):
    constructor, calls = c.PointRequest, []
    def counted(*args, **kwargs):
        result = constructor(*args, **kwargs)
        calls.append(result.role)
        return result
    monkeypatch.setattr(c, "PointRequest", counted)
    for method in c.METHODS:
        for hour in (public.first_hour, public.actual_hour):
            full = c.hour_requests(public, "on_time", "early", method, hour)
            n = len(calls); calls.clear()
            selected = reference_requests(public, "on_time", "early", method, hour)
            assert n == len(full["requests"]) == 1+2*len(public.selected)+len(selected["requests"])
            assert len(calls) == len(selected["requests"])
            assert not any(role.startswith(("normal_contract", "fault_")) for role in calls)
            calls.clear()


@pytest.mark.parametrize("late", [False, True])
@pytest.mark.parametrize("plan", ["on_time", "delayed"])
@pytest.mark.parametrize("clean", ["early", "late"])
@pytest.mark.parametrize("method", c.METHODS)
def test_multistep_state_policy_audits_and_cross_version_continuation(late, plan, clean, method):
    fixture = analytic_fixture(late)
    left = old.initialize_execution(fixture, plan, clean, method)
    right = new.initialize_execution(fixture, plan, clean, method)
    for hour in range(5):
        evidence = analytic_hour(fixture, left)
        # Alternate the drivers to exercise continuation from both versions.
        a, b = (old, new) if hour % 2 == 0 else (new, old)
        pa, pb = a.prepare_hour(fixture, left, evidence), b.prepare_hour(fixture, right, evidence)
        qa, qb = a.propose_hour(left, pa), b.propose_hour(right, pb)
        assert pa == pb and qa == qb and c.digest(pa) == c.digest(pb)
        actual = analytic_actual(pa, qa)
        left = a.accept_hour(fixture, left, pa, qa, actual)
        right = b.accept_hour(fixture, right, pb, qb, actual)
        assert left == right and c.digest(left) == c.digest(right)
    assert old.execution_summary(fixture, left) == new.execution_summary(fixture, right)
    assert old_audit(fixture, left) == new_audit(fixture, right)


def test_new_kernel_and_independent_auditor_do_not_call_full_compiler(monkeypatch):
    fixture = analytic_fixture()
    state = old.initialize_execution(fixture, "on_time", "early", "full_temporal")
    evidence = analytic_hour(fixture, state)
    def denied(*args, **kwargs): pytest.fail("old full compiler or writer used")
    monkeypatch.setattr(c, "hour_requests", denied)
    prepared = new.prepare_hour(fixture, state, evidence)
    proposal = new.propose_hour(state, prepared)
    state = new.accept_hour(fixture, state, prepared, proposal, analytic_actual(prepared, proposal))
    for module in (old, new):
        for name in ("initialize_execution", "prepare_hour", "propose_hour", "accept_hour"):
            monkeypatch.setattr(module, name, denied)
    assert new_audit(fixture, state)["record_consistency_satisfied"]
    assert new.execution_summary(fixture, state)["coverage_complete"] is False


@pytest.mark.parametrize("outage", [c.Outage("bad", (999,)), c.Outage("bad", (), (999,)),
                                      c.Outage("bad", (True,)), c.Outage("bad"), c.Outage("bad", (0,), (0,))])
def test_unused_invalid_selected_N1_is_still_rejected(outage):
    fixture = analytic_fixture()
    fixture = replace(fixture, selected=fixture.selected+(outage,))
    for compiler in (c.hour_requests, reference_requests):
        with pytest.raises(ValueError): compiler(fixture, "on_time", "early", "full_temporal", 0)


@pytest.mark.parametrize("arguments", [("bad", "early", "full_temporal", 0), ("on_time", "bad", "full_temporal", 0),
                                          ("on_time", "early", "bad", 0), ("on_time", "early", "full_temporal", 99)])
def test_invalid_context_is_not_accepted(arguments):
    for compiler in (c.hour_requests, reference_requests):
        with pytest.raises((ValueError, KeyError)): compiler(analytic_fixture(), *arguments)


def test_empty_selected_is_lazy_outside_actual_event():
    fixture = replace(analytic_fixture(), selected=())
    assert reference_requests(fixture, "on_time", "early", "full_temporal", 0)["actual_outage"] == c.Outage("normal")
    for compiler in (c.hour_requests, reference_requests):
        with pytest.raises(IndexError): compiler(fixture, "on_time", "early", "full_temporal", 1)
