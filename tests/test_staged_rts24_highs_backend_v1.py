"""Fake native structs/statuses only; never import the highspy extension."""
from copy import deepcopy
from enum import Enum
from types import SimpleNamespace as NS

import pytest

from test_staged_rts24_numeric_interface_v1 import frame, raw_snapshot
from src import staged_rts24_highs_backend_v1 as backend
from src.staged_rts24_numeric_interface_v1 import import_snapshot, UnresolvedNumeric


class Status(Enum):
    kOk = 0
    kWarning = 1
    kError = -1


class FakeApi:
    HighsLp = HighsSparseMatrix = HighsModel = HighsHessian = NS
    HighsStatus = Status
    ObjSense = NS(kMinimize="min")
    MatrixFormat = NS(kRowwise="row")
    HessianFormat = NS(kTriangular="triangle")
    HighsVarType = NS(kContinuous="continuous")

    def __init__(self, raw):
        self.raw, self.options, self.called, self.model = raw, {}, [], None
        self.version_text, self.fail_at, self.clear_error = backend.VERSION, None, False
        self.model_status, self.dual_valid, self.info_valid = raw.model_status, raw.dual_valid, True
        self.nonfinite = False

    def Highs(self): self.called.append("construct"); return self
    def version(self): return self.version_text
    def githash(self): return "fake_only"
    def versionMajor(self): return 1
    def versionMinor(self): return 15
    def versionPatch(self): return 1

    def setOptionValue(self, key, value):
        self.options[key] = value
        return Status.kError if self.fail_at == "set_"+key else Status.kOk

    def getOptionValue(self, key):
        return (Status.kError, None) if self.fail_at == "get_"+key else (Status.kOk, self.options[key])

    def passModel(self, model):
        self.model = model
        return Status.kWarning if self.fail_at == "pass_model" else Status.kOk

    def run(self):
        self.called.append("run")
        from pathlib import Path
        Path(self.options["log_file"]).write_text("ordinary fake API log\n", encoding="utf-8")
        if self.fail_at == "raise_run": raise OSError("fake native exception")
        return Status.kWarning if self.fail_at == "run" else Status.kOk

    def getModelStatus(self): return NS(name=self.model_status, value=backend.MODEL_STATUS[self.model_status])

    def getSolution(self):
        return NS(value_valid=self.raw.primal_valid, dual_valid=self.dual_valid,
            col_value=list(self.raw.column_value), row_value=list(self.raw.row_value),
            col_dual=[float("nan")] if self.nonfinite else list(self.raw.column_dual), row_dual=list(self.raw.row_dual))

    def getInfo(self):
        values = {name: 0 for name in backend.INFO_FIELDS}
        values.update(valid=self.info_valid, objective_function_value=self.raw.objective,
            primal_solution_status=2, dual_solution_status=2, num_primal_infeasibilities=0,
            num_dual_infeasibilities=0, max_primal_infeasibility=0., max_dual_infeasibility=0.,
            max_complementarity_violation=0., simplex_iteration_count=0, ipm_iteration_count=0, qp_iteration_count=1)
        return NS(**values)

    def getRunTime(self): return .001
    def getObjectiveValue(self): return self.raw.objective

    def clear(self):
        self.called.append("clear")
        if self.clear_error: raise OSError("fake clear failure")
        return Status.kOk


@pytest.mark.parametrize("hour,role", [(0, "reference"), (0, "lower"), (0, "upper"), (1, "raw"), (1, "upper")])
def test_fake_native_transport_roundtrips_independent_evidence(tmp_path, hour, role):
    item = getattr(frame(hour), role)
    problem, expected = raw_snapshot(item)
    api = FakeApi(expected)
    raw = backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert import_snapshot(item.query, problem, backend.snapshot_from_raw(problem, raw)) == item
    lp = api.model.lp_
    assert lp.num_col_ == len(problem.columns) and lp.num_row_ == len(problem.rows)
    assert lp.col_names_ == list(problem.columns) and lp.row_names_ == [r.name for r in problem.rows]
    assert lp.offset_ == problem.constant and lp.sense_ == "min"
    assert lp.integrality_ == ["continuous"]*lp.num_col_
    matrix = lp.a_matrix_
    for i, row in enumerate(problem.rows):
        lo, hi = matrix.start_[i:i+2]
        assert tuple(zip(matrix.index_[lo:hi], matrix.value_[lo:hi])) == row.terms
    if problem.quadratic: assert api.model.hessian_.value_ == [2e-8]
    else: assert not hasattr(api.model, "hessian_")
    assert api.options["presolve"] == "off" and api.options["threads"] == 1
    assert api.options["qp_regularization_value"] == 0.
    assert api.options["solver"] == ("qpasm" if problem.quadratic else "simplex")
    assert api.called == ["construct", "run", "clear"]


@pytest.mark.parametrize("stage", ["set_threads", "get_threads", "pass_model", "run", "raise_run"])
def test_native_api_failure_retains_attempt_and_clears_without_retry(tmp_path, stage):
    problem, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected)
    api.fail_at = stage
    with pytest.raises(backend.BackendFailure) as error:
        backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert error.value.record["problem_sha"] == problem.identity
    assert api.called.count("construct") == 1 and api.called.count("run") <= 1 and api.called[-1] == "clear"
    assert error.value.record["error"]


def test_version_mismatch_never_starts_solver(tmp_path):
    problem, raw = raw_snapshot(frame().reference)
    api = FakeApi(raw)
    api.version_text = "other"
    with pytest.raises(backend.BackendFailure): backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert api.called == ["construct", "clear"]


def test_cleanup_failure_cannot_produce_consumable_raw(tmp_path):
    problem, raw = raw_snapshot(frame().reference)
    api = FakeApi(raw)
    api.clear_error = True
    with pytest.raises(backend.BackendFailure) as error:
        backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert error.value.record["cleanup_error"]["type"] == "OSError"
    with pytest.raises(ValueError): backend.snapshot_from_raw(problem, error.value.record)


@pytest.mark.parametrize("status", ["kTimeLimit", "kInfeasible", "kUnboundedOrInfeasible", "kUnknown"])
def test_native_nonoptimal_state_preserved_without_infeasibility_claim(tmp_path, status):
    problem, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected)
    api.model_status = status
    raw = backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert raw["model_status"] == status
    with pytest.raises(UnresolvedNumeric, match="infeasibility not inferred"): backend.snapshot_from_raw(problem, raw)


def test_nonfinite_raw_dual_saved_as_tag_and_never_consumed(tmp_path):
    item = frame().reference
    problem, expected = raw_snapshot(item)
    api = FakeApi(expected)
    api.nonfinite = True
    raw = backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert raw["solution"]["col_dual"] == [{"nonfinite": "nan"}]
    with pytest.raises(ValueError): import_snapshot(item.query, problem, backend.snapshot_from_raw(problem, raw))


def test_native_missing_dual_flag_is_not_repaired(tmp_path):
    item = frame().reference
    problem, expected = raw_snapshot(item)
    api = FakeApi(expected)
    api.dual_valid = False
    raw = backend.call_highs(problem, tmp_path/"native.log", api=api)
    snap = backend.snapshot_from_raw(problem, raw)
    assert snap.column_dual == snap.row_dual == ()
    assert raw["solution"]["row_dual"]
    with pytest.raises(UnresolvedNumeric): import_snapshot(item.query, problem, snap)


@pytest.mark.parametrize("field", ["model_status_value", "options", "api_calls", "num_complementarity_violations"])
def test_raw_binding_status_and_unavailable_info_cannot_be_consumed(tmp_path, field):
    problem, expected = raw_snapshot(frame().reference)
    raw = backend.call_highs(problem, tmp_path/"native.log", api=FakeApi(expected))
    if field == "model_status_value": raw[field] = 8
    elif field == "options": raw[field]["threads"] = True
    elif field == "api_calls": raw[field][0]["value"] = 1
    else: raw["info"][field] = -1
    with pytest.raises(ValueError): backend.snapshot_from_raw(problem, raw)


def test_run_warning_keeps_diagnostics_and_log_without_becoming_success(tmp_path):
    problem, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected); api.fail_at = "run"
    with pytest.raises(backend.BackendFailure) as failure:
        backend.call_highs(problem, tmp_path/"native.log", api=api)
    raw = failure.value.record
    assert raw["run_invoked"] and raw["run_returned"] and raw["solution"]["col_value"]
    assert raw["api_calls"][-1] == dict(stage="run", status="kWarning", value=1)
    assert raw["log_pin"]["bytes"] == (tmp_path/"native.log").stat().st_size
    with pytest.raises(UnresolvedNumeric): backend.snapshot_from_raw(problem, raw)


def test_missing_native_log_never_becomes_consumable_success(tmp_path, monkeypatch):
    problem, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected)
    monkeypatch.setattr(api, "run", lambda: Status.kOk)
    with pytest.raises(backend.BackendFailure) as failure:
        backend.call_highs(problem, tmp_path/"native.log", api=api)
    assert failure.value.record["artifact_error"]["type"] == "FileNotFoundError"
    with pytest.raises(ValueError): backend.snapshot_from_raw(problem, failure.value.record)


def test_nonoptimal_name_value_or_payload_tamper_is_transport_not_numeric(tmp_path):
    problem, expected = raw_snapshot(frame().reference)
    api = FakeApi(expected); api.model_status = "kTimeLimit"
    raw = backend.call_highs(problem, tmp_path/"native.log", api=api)
    raw["model_status_value"] = 14
    with pytest.raises(ValueError, match="name/value"): backend.snapshot_from_raw(problem, raw)
    raw["model_status_value"] = 13
    raw["info"].pop("valid")
    with pytest.raises(ValueError, match="payload incomplete"): backend.snapshot_from_raw(problem, raw)
