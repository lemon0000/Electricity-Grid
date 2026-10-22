import json

import pytest

from experiments import staged_c_saved_cost_audit_v1 as audit


def row():
    point = {"load": "1"}
    return dict(contract=dict(normal=point, scenarios=[
        dict(outages=[], firm_point=None, post_call_point=dict(point)),
        dict(outages=[0], firm_point=point, post_call_point=point),
        dict(outages=[1], firm_point=point, post_call_point=point)]),
        reference_point=point, actual_point=point, proposal={}, committed=True)


def test_saved_normal_alias_does_not_create_an_eighth_solve():
    value = row()
    assert audit.work(dict(records=[value])) == dict(pypower_flows=7, network_attempts=1, business_steps=1)
    value["contract"]["scenarios"][0]["post_call_point"] = {"load": "2"}
    with pytest.raises(ValueError, match="alias"):
        audit.point_count(value)


def test_failed_actual_and_early_admission_have_different_business_work():
    value = row()
    value["actual_point"] = None
    assert audit.work(dict(records=[value]))["business_steps"] == 1
    assert audit.point_count(value) == 6
    value["proposal"] = None
    assert audit.work(dict(records=[value]))["business_steps"] == 0


def test_rejected_attempt_is_counted_separately_from_accepted_child_state():
    child = dict(state=dict(records=[row()], stopped=False),
                 summary=dict(pending=dict(b2_candidate_record=row())))
    attempted = audit.attempted_state(child)
    assert len(attempted["records"]) == 2 and attempted["stopped"] is True
    assert len(child["state"]["records"]) == 1 and child["state"]["stopped"] is False


def test_repeated_reopens_are_charged_and_no_wall_extrapolation():
    budget = audit.structural_budget(10, 2, (4, 10), trajectories=3)
    assert budget["network_hour_visits"] == 72
    assert budget["point_compute_roles"] == 504
    assert budget["initial_digest_record_visits"] == 300
    assert budget["reopen_after_digest_record_visits"] == 195
    assert budget["wall_seconds"] is None
    assert audit.structural_budget(192, 2, (192,))["within_existing_horizon_and_outage_limits"] is False
    with pytest.raises(ValueError):
        audit.structural_budget(10, 2, (11,))
    with pytest.raises(ValueError):
        audit.structural_budget(True, 2)


@pytest.mark.parametrize("probe,reason,reopened_reason,length", [
    ("missing_input", "missing_input", "missing_input", 4),
    ("network_unresolved", "network_unresolved", "network_unresolved", 3),
    ("save_before_publish", "persistence_failure", "incomplete_publication", 4),
    ("save_after_publish", "commit_outcome_unknown", None, 4),
])
def test_probe_reason_and_candidate_adoption_cannot_be_swapped(probe, reason, reopened_reason, length):
    state = dict(records=[row() for _ in range(length)])
    candidate = row() if probe != "missing_input" else None
    if probe == "network_unresolved":
        candidate.update(committed=False, actual_point=None)
    proposed = dict(records=state["records"] + [candidate])
    pending = None if candidate is None else dict(b2_candidate_record=candidate,
        b2_candidate_state=None if probe == "network_unresolved" else proposed,
        role="network_attempt" if probe == "network_unresolved" else "step",
        adoption="unknown" if probe == "save_after_publish" else "not_adopted")
    saved = dict(before_reopen=dict(termination_reason=reason, last_verified_state=state,
                 pending=pending),
                 reopened_reason=reopened_reason, reopened_state=proposed if probe == "save_after_publish" else state)
    audit.probe_work(saved, probe)
    if pending is not None:
        original = pending["adoption"]
        pending["adoption"] = "accepted"
        with pytest.raises(ValueError, match="pending disposition"):
            audit.probe_work(saved, probe)
        pending["adoption"] = original
    # All work counts stay identical, but a different recovery verdict must fail.
    saved["reopened_reason"] = "wrong_reason"
    with pytest.raises(ValueError, match="recovery reason"):
        audit.probe_work(saved, probe)
    saved["reopened_reason"] = reopened_reason
    saved["reopened_state"] = state if probe == "save_after_publish" else proposed
    with pytest.raises(ValueError, match="adoption|unaccepted"):
        audit.probe_work(saved, probe)


def completed(tmp_path):
    folder = tmp_path / "saved"
    folder.mkdir()
    data = folder / "row.json"
    data.write_text("{}", encoding="utf-8")
    item = audit.stamp(data)
    (folder / "completion.json").write_text(json.dumps(dict(
        status="development_diagnostic_completed", authority="DRAFT_NONAUTHORITATIVE",
        artifacts={"row.json": item}, artifact_bytes_before_completion=item["bytes"])), encoding="utf-8")
    for name in ("validation_report.md", "verification.json"):
        (folder / name).write_text("{}", encoding="utf-8")
    return folder, {"saved/row.json": item}


def test_import_age_does_not_charge_unit_helpers_but_cli_budget_remains_active(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "START", audit.time.perf_counter() - 1000)
    path = tmp_path / "row.json"
    path.write_text("{}", encoding="utf-8")
    assert audit.stamp(path)["bytes"] == 2
    monkeypatch.setattr(audit, "BUDGET_ACTIVE", True)
    with pytest.raises(ValueError, match="wall limit"):
        audit.stamp(path)


def test_saved_inventory_rejects_drift_extra_file_and_failure_marker(tmp_path):
    folder, snapshot = completed(tmp_path)
    assert audit.check_completion(tmp_path, folder, snapshot) == 1
    changed = dict(snapshot)
    changed["saved/row.json"] = dict(bytes=2, sha256="0" * 64)
    with pytest.raises(ValueError, match="artifact differs"):
        audit.check_completion(tmp_path, folder, changed)
    extra = folder / "unexpected.json"
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        audit.check_completion(tmp_path, folder, snapshot)
    extra.unlink()
    (folder / "failure.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="failure marker"):
        audit.check_completion(tmp_path, folder, snapshot)
