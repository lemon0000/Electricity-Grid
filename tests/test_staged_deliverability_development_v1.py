"""Bounded ordinary tests of the declared B1 mechanism, never formal results."""
from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from src.staged_deliverability_development_v1 import (
    METHODS, advance, assessment, execute, initialize, load_small_case,
    plain, power_mapping, read_checkpoint, save_checkpoint, task_balances,
)
from src.staged_deliverability_audit_v1 import audit_records, offline_recovery_check

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "configs/staged_deliverability_small_case_v1.DRAFT.yaml"


def case(plan="on_time", clean="early", method="full_temporal"):
    p, observations = load_small_case(FIXTURE, plan, clean)
    return p, observations, execute(p, observations, method, f"{plan}:{clean}:{method}")


def record(state, hour):
    return next(r for r in state.records if r.observation.hour == hour)


@pytest.mark.parametrize("plan,clean", [("on_time", "early"), ("on_time", "late"), ("delayed", "early")])
@pytest.mark.parametrize("method", METHODS)
def test_nine_declared_paths_have_independent_work_and_power_balances(plan, clean, method):
    p, inputs, state = case(plan, clean, method)
    audit = audit_records(plain(p), plain(state.records), state.method)
    assert audit["envelope"] == dict(previous_call=state.previous_call, call_energy=state.call_energy,
                                     events=state.events, duration=state.duration, rest=state.rest)
    assert len(state.records) == len(inputs) == 10
    assert not state.stopped
    assert len(task_balances(state)) == 10  # Every task, including uncurtailed tasks.
    for task in task_balances(state):
        assert task["original"] == task["immediate"] + task["recovered"] + task["remaining"]
        if task["birth"] in audit["balances"]:
            assert task["remaining"] == audit["balances"][task["birth"]]["remaining"]
            assert task["deadline_miss"] == audit["deadline_misses"].get(task["birth"])
    assert assessment(state)["fx_contract_status"] == "not_assessed_scalar_stub"


def test_stage_and_exact_anchor_values():
    p, inputs, state = case()
    before, after = record(state, 1), record(state, 2)
    assert before.observation.compute_capacity == Q(4, 5)
    assert after.observation.compute_capacity == Q(6, 5)
    assert before.observation.idle_mw == Q(2, 25)
    assert after.observation.idle_mw == Q(3, 25)
    assert before.reference_mw == Q(3, 4)
    assert before.grid_request_mw == before.cfe_request_mw == Q(1, 8)
    assert before.grid_served == before.cfe_served == Q(1, 10)
    assert before.deferred == Q(1, 5) and before.power_mw == Q(1, 2)
    assert after.recovery == Q(1, 5) and after.power_mw == Q(21, 20)
    assert after.allocations == ((1, Q(1, 5)),)
    assert p.alpha * after.power_mw == Q(21, 25)
    assert record(state, 3).reference_mw == Q(21, 20)
    assert assessment(state)["method_conditions_satisfied"] is True
    assert state.ledger.debt == 0
    _, _, idle_only = power_mapping(p, replace(inputs[0], workload=Q(0)))
    assert idle_only == Q(1, 8) > 0


def test_late_clean_resources_preserve_deadline_miss_after_full_repayment():
    p, observations, late = case(clean="late")
    assert record(late, 2).recovery == record(late, 3).recovery == 0
    assert record(late, 4).recovery == Q(1, 5)
    task = next(t for t in task_balances(late) if t["birth"] == 1)
    assert task["remaining"] == 0 and task["deadline_miss"] == Q(1, 5)
    assert task["status"] == "deadline_missed"
    assert assessment(late)["method_conditions_satisfied"] is False


def test_three_methods_report_distinct_scopes_and_fixed_plan_rejection():
    _, _, instant = case(clean="late", method="instantaneous")
    p, _, fixed = case(clean="late", method="fixed_headroom")
    _, _, full = case(clean="late")
    assert assessment(instant)["method_conditions_satisfied"] is True
    assert assessment(fixed)["method_conditions_satisfied"] is True
    assert assessment(full)["method_conditions_satisfied"] is False
    audit = audit_records(plain(p), plain(fixed.records), fixed.method)
    assert audit["first_full_contract_rejection"] == 2
    assert audit["debt_before_full_contract_rejection"] == Q(1, 5)
    assert record(fixed, 2).cfe_shortfall_mwh == Q(1, 5)
    assert assessment(fixed)["scope"] == "constant_headroom_approximation"


def test_delayed_grid_changes_call_and_carries_both_cohorts():
    _, _, on_time = case()
    _, _, delayed = case(plan="delayed")
    assert record(on_time, 3).grid_request_mw == 0
    assert record(delayed, 2).recovery == 0
    assert record(delayed, 3).grid_request_mw == Q(1, 4)
    assert record(delayed, 3).grid_served == Q(1, 5)
    assert delayed.events == 2 and delayed.call_energy == Q(2, 5)
    assert {t["birth"] for t in task_balances(delayed) if t["deadline_miss"]} == {1, 3}


def test_efficiency_changes_recovery_consumption_without_erasing_work():
    p, observations = load_small_case(FIXTURE)
    p = replace(p, eta=Q(1, 2))
    state = execute(p, observations)
    assert record(state, 2).recovery == Q(1, 5)
    assert record(state, 2).allocations == ((1, Q(1, 10)),)
    task = next(t for t in task_balances(state) if t["birth"] == 1)
    assert task["original"] == task["immediate"] + task["recovered"] + task["remaining"]
    assert task["deadline_miss"] == Q(1, 10)
    audit_records(plain(p), plain(state.records), state.method)


def test_causal_future_changes_do_not_change_prefix_actions():
    p, early = load_small_case(FIXTURE)
    _, late = load_small_case(FIXTURE, clean="late")
    _, delayed = load_small_case(FIXTURE, plan="delayed")
    a = execute(p, early[:4], trajectory_id="shared-prefix")
    assert a == execute(p, late[:4], trajectory_id="shared-prefix")
    assert a == execute(p, delayed[:4], trajectory_id="shared-prefix")


def test_due_hour_recovery_is_included_and_birth_recovery_is_forbidden():
    p, inputs = load_small_case(FIXTURE)
    # The debt at hour 1 may be repaid at its deadline 2, after the stage change.
    changed = tuple(replace(o, due=2) if o.hour == 1 else o for o in inputs)
    state = execute(p, changed)
    task = next(t for t in task_balances(state) if t["birth"] == 1)
    assert task["deadline_miss"] == 0
    assert not record(state, 1).allocations


def test_partial_prefix_is_censored_not_complete():
    p, inputs = load_small_case(FIXTURE)
    prefix = execute(p, inputs[:4])
    result = assessment(prefix)
    assert result["primary_right_censored"]
    assert result["method_conditions_satisfied"] is None
    assert not result["coverage_complete"]


def test_mandatory_failure_does_not_commit_tasks_or_new_debt():
    p, inputs = load_small_case(FIXTURE)
    p = replace(p, capacity=Q(1, 20))
    state = execute(p, inputs)
    assert state.stopped and not state.records[-1].ledger_applied
    assert state.records[-1].observation.hour == 1 and state.next_hour == 1
    assert state.ledger.debt == 0 and len(task_balances(state)) == 3
    assert assessment(state)["method_conditions_satisfied"] is False
    with pytest.raises(ValueError):
        advance(p, state, inputs[4])


def test_parameter_and_time_drift_are_rejected():
    p, inputs = load_small_case(FIXTURE)
    state = execute(p, inputs[:4])
    with pytest.raises(ValueError, match="parameters changed"):
        advance(replace(p, eta=Q(1, 2)), state, inputs[4])
    with pytest.raises(ValueError, match="nonconsecutive"):
        advance(p, state, inputs[5])
    with pytest.raises(ValueError):
        replace(inputs[0], clean_mwh=None)
    with pytest.raises(ValueError):
        replace(p, alpha=True)


@pytest.mark.parametrize("plan,clean", [("on_time", "early"), ("on_time", "late"), ("delayed", "early")])
@pytest.mark.parametrize("method", METHODS)
def test_checkpoint_prefix_replay_and_resumed_suffix_equal_continuous(tmp_path, plan, clean, method):
    p, inputs, continuous = case(plan, clean, method)
    identity = f"{plan}:{clean}:{method}"
    prefix = execute(p, inputs[:4], method, identity)
    path = tmp_path / "checkpoint.json"
    save_checkpoint(path, p, prefix)
    reopened = read_checkpoint(path, p, inputs[:4], method, identity)
    assert reopened == prefix
    assert execute(p, inputs[4:], state=reopened) == continuous
    with pytest.raises(FileExistsError):
        save_checkpoint(path, p, prefix)


def test_fresh_process_reopen_has_same_exact_terminal_state(tmp_path):
    p, inputs, continuous = case(clean="late")
    identity = "on_time:late:full_temporal"
    path = tmp_path / "checkpoint.json"
    save_checkpoint(path, p, execute(p, inputs[:4], trajectory_id=identity))
    script = (
        "import json,sys; from src.staged_deliverability_development_v1 import *; "
        "p,x=load_small_case(sys.argv[1],clean='late'); "
        "s=read_checkpoint(sys.argv[2],p,x[:4],'full_temporal',sys.argv[3]); "
        "print(json.dumps(plain(execute(p,x[4:],state=s)),sort_keys=True))"
    )
    child = subprocess.run([sys.executable, "-B", "-c", script, str(FIXTURE), str(path), identity],
                           cwd=ROOT, capture_output=True, text=True, timeout=15, check=True)
    assert json.loads(child.stdout) == plain(continuous)


@pytest.mark.parametrize("field", ["eta", "due", "capacity", "idle", "events_bool", "applied"])
def test_checkpoint_tampering_is_rejected(tmp_path, field):
    p, inputs = load_small_case(FIXTURE)
    state = execute(p, inputs[:4])
    path = tmp_path / "checkpoint.json"
    save_checkpoint(path, p, state)
    data = json.loads(path.read_text())
    if field == "eta":
        data["parameters"]["eta"] = "1/2"
    elif field == "due":
        data["observations"][-1]["due"] += 1
    elif field == "capacity":
        data["state"]["records"][-1]["observation"]["compute_capacity"] = "99"
    elif field == "idle":
        data["state"]["records"][-1]["observation"]["idle_mw"] = "0"
    elif field == "events_bool":
        data["state"]["events"] = True  # bool equals int 1 in Python, but is invalid encoding.
    else:
        data["state"]["records"][-1]["ledger_applied"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint differs"):
        read_checkpoint(path, p, inputs[:4], "full_temporal", "mechanism")


def test_duplicate_json_keys_rejected(tmp_path):
    p, inputs = load_small_case(FIXTURE)
    path = tmp_path / "checkpoint.json"
    path.write_text('{"schema":1,"schema":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        read_checkpoint(path, p, inputs[:4], "full_temporal", "mechanism")


@pytest.mark.parametrize("clean,feasible,flow", [("early", True, Q(1, 5)), ("late", False, Q(0))])
def test_independent_flow_and_subset_cuts_on_complete_fixed_obligations(clean, feasible, flow):
    p, inputs, state = case(clean=clean)
    audit = audit_records(plain(p), plain(state.records), state.method)
    result = offline_recovery_check(plain(p), plain(inputs), audit["calls"])
    assert result["feasible"] is feasible
    assert result["flow"] == flow and result["required"] == Q(1, 5)
    assert result["subset_deficit"] == Q(1, 5) - flow
    assert result["recovery_slots"][1] == 0  # No birth-hour recovery.


def test_offline_oracle_never_fills_unobserved_future_deadlines():
    p, inputs, state = case()
    calls = audit_records(plain(p), plain(state.records), state.method)["calls"]
    result = offline_recovery_check(plain(p), plain(inputs[:4]), calls)
    assert result == dict(status="right_censored", flow=None)
    with pytest.raises(ValueError, match="prefix debt bound"):
        offline_recovery_check(plain(replace(p, max_debt=Q(1, 10))), plain(inputs), calls)


def test_independent_auditor_rejects_meter_or_work_tampering():
    p, _, state = case()
    rows = plain(state.records)
    rows[4]["power_mw"] = "0"
    with pytest.raises(AssertionError):
        audit_records(plain(p), rows, state.method)


@pytest.mark.parametrize("key,value", [("max_events", 0), ("max_duration", 0), ("minimum_rest", 2),
                                      ("call_ramp", "1/10"), ("max_call_energy", "1/10"),
                                      ("max_debt", "1/10")])
def test_independent_audit_does_not_trust_event_or_budget_flags(key, value):
    p, _, state = case(plan="delayed")
    parameters = plain(p)
    parameters[key] = value
    with pytest.raises(AssertionError):
        audit_records(parameters, plain(state.records), state.method)


@pytest.mark.parametrize("changes", [dict(max_events=0), dict(minimum_rest=2),
                                    dict(max_call_energy=Q(1, 5)), dict(max_debt=Q(1, 5))])
def test_resource_limits_stop_without_committing_unsupported_grid_calls(changes):
    p, inputs = load_small_case(FIXTURE, plan="delayed")
    p = replace(p, **changes)
    state = execute(p, inputs)
    assert state.stopped and not state.records[-1].ledger_applied
    audit_records(plain(p), plain(state.records), state.method)


def test_third_event_is_rejected_even_with_ample_energy_and_debt_capacity():
    p, inputs = load_small_case(FIXTURE)
    p = replace(p, max_call_energy=Q(1), max_debt=Q(1))
    inputs = tuple(replace(o, supply_mw=Q(37, 40)) if o.hour in (3, 5) else o for o in inputs)
    state = execute(p, inputs)
    assert state.stopped and state.records[-1].observation.hour == 5
    assert state.events == 2 and state.records[-1].grid_shortfall_mw == Q(1, 8)


@pytest.mark.parametrize("path,value", [
    (("flexible_fraction",), .4), (("prehistory_clean",), True),
    (("equipment", 0, "capacity"), .8), (("equipment", 1, "idle_mw"), True),
    (("workload", "before"), .5), (("grid", "before"), .8),
    (("grid", "temporary_limit"), True), (("clean_paths", "late", 7), .84),
    (("first_hour",), True), (("last_hour",), True), (("deadline_lag",), True),
    (("workload", "change_hour"), True), (("grid", "temporary_hour"), True),
    (("grid", "delays", "delayed"), True), (("equipment", 1, "lead"), True),
    (("source_class",), "measured"),
])
def test_fixture_rejects_float_bool_and_source_drift(tmp_path, path, value):
    cfg = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    target = cfg
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    modified = tmp_path / "fixture.yaml"
    modified.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(ValueError):
        load_small_case(modified)


def test_audit_cannot_be_disabled_by_python_optimization():
    script = (
        "from src.staged_deliverability_development_v1 import *; "
        "from src.staged_deliverability_audit_v1 import audit_records; "
        "p,x=load_small_case(sys.argv[1]); s=execute(p,x); rows=plain(s.records); "
        "rows[3]['power_mw']='0'; audit_records(plain(p),rows,s.method)"
    )
    child = subprocess.run([sys.executable, "-O", "-B", "-c", "import sys; " + script, str(FIXTURE)],
                           cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert child.returncode != 0 and "AssertionError" in child.stderr


def test_diagnostic_refuses_output_outside_its_dedicated_root(tmp_path):
    from experiments.staged_deliverability_b1_development_v1 import run
    with pytest.raises(ValueError, match="dedicated"):
        run(tmp_path / "attempt")
    assert not (tmp_path / "attempt").exists()


def test_diagnostic_resource_rejection_preserves_failure_without_launching_children(tmp_path, monkeypatch):
    from experiments import staged_deliverability_b1_development_v1 as driver
    monkeypatch.setattr(driver, "BASE", tmp_path)
    process = SimpleNamespace(children=lambda **kw: [],
                              memory_info=lambda: SimpleNamespace(rss=513 * 1024**2))
    monkeypatch.setattr(driver.psutil, "Process", lambda: process)
    output = tmp_path / "resource_failure"
    with pytest.raises(RuntimeError, match="resource limit"):
        driver.run(output)
    failed = json.loads((output / "failure.json").read_text())
    assert failed["counts"]["child_processes"] == failed["counts"]["policy_steps"] == 0
    with pytest.raises(FileExistsError):
        driver.run(output)


def test_direct_child_cannot_write_outside_dedicated_attempt(tmp_path):
    from experiments.staged_deliverability_b1_development_v1 import child
    args = SimpleNamespace(reopen=tmp_path / "checkpoint.json", result=tmp_path / "terminal.json",
                           plan="on_time", clean="early", method="full_temporal")
    with pytest.raises(ValueError, match="child paths"):
        child(args)
    assert not args.result.exists()


def test_direct_child_requires_exact_case_filenames(tmp_path, monkeypatch):
    from experiments import staged_deliverability_b1_development_v1 as driver
    monkeypatch.setattr(driver, "BASE", tmp_path)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    args = SimpleNamespace(reopen=attempt / "wrong_checkpoint.json", result=attempt / "wrong_terminal.json",
                           plan="on_time", clean="early", method="full_temporal")
    with pytest.raises(ValueError, match="child paths"):
        driver.child(args)
