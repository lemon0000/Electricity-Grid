"""Explicit HiGHS transport. Construction/run occur only in call_highs()."""
from dataclasses import asdict
from math import isfinite
from pathlib import Path
import hashlib
import stat
import time

from src import staged_rts24_development_v1 as c
from src.staged_rts24_numeric_interface_v1 import (
    NumericProblem, NumericSnapshot, SCHEMA, SNAPSHOT_SCHEMA, UnresolvedNumeric, hessian_columns,
)

VERSION = "1.15.1"
MODEL_STATUS = {"kNotset": 0, "kLoadError": 1, "kModelError": 2, "kPresolveError": 3, "kSolveError": 4,
    "kPostsolveError": 5, "kModelEmpty": 6, "kOptimal": 7, "kInfeasible": 8, "kUnboundedOrInfeasible": 9,
    "kUnbounded": 10, "kObjectiveBound": 11, "kObjectiveTarget": 12, "kTimeLimit": 13, "kIterationLimit": 14,
    "kUnknown": 15, "kSolutionLimit": 16, "kInterrupt": 17, "kMemoryLimit": 18, "kHighsInterrupt": 19}
OPTIONS = dict(threads=1, parallel="off", presolve="off", time_limit=5., random_seed=0,
               primal_feasibility_tolerance=1e-8, dual_feasibility_tolerance=1e-8,
               kkt_tolerance=1e-8, optimality_tolerance=1e-8, qp_regularization_value=0.,
               output_flag=True, log_to_console=False)
INFO_FIELDS = ("valid", "objective_function_value", "primal_solution_status", "dual_solution_status",
    "num_primal_infeasibilities", "num_dual_infeasibilities", "max_primal_infeasibility",
    "max_dual_infeasibility", "max_complementarity_violation", "sum_primal_infeasibilities",
    "sum_dual_infeasibilities", "num_complementarity_violations", "basis_validity", "max_integrality_violation",
    "simplex_iteration_count", "ipm_iteration_count", "qp_iteration_count", "pdlp_iteration_count",
    "crossover_iteration_count", "mip_dual_bound", "mip_gap", "mip_node_count",
    "max_dual_residual_error", "max_primal_residual_error", "max_relative_dual_infeasibility",
    "max_relative_dual_residual_error", "max_relative_primal_infeasibility", "max_relative_primal_residual_error",
    "num_dual_residual_errors", "num_primal_residual_errors", "num_relative_dual_infeasibilities",
    "num_relative_dual_residual_errors", "num_relative_primal_infeasibilities", "num_relative_primal_residual_errors",
    "primal_dual_integral", "primal_dual_objective_error")


def options_for(problem): return {**OPTIONS, "solver": "qpasm" if problem.quadratic else "simplex"}


def scalar(value):
    if type(value) is bool: return value
    if isinstance(value, int): return int(value)
    v = float(value)
    return v if isfinite(v) else {"nonfinite": "nan" if v != v else "+inf" if v > 0 else "-inf"}


def enum_name(value):
    name = value.name
    c.require(type(name) is str and name.startswith("k"), "invalid native enum")
    return name


class BackendFailure(RuntimeError):
    def __init__(self, record, cause):
        super().__init__(f"native {record['stage']}: {type(cause).__name__}: {cause}")
        self.record = record


def make_model(problem, api):
    """Only struct construction; fake APIs can verify every array without native code."""
    c.require(type(problem) is NumericProblem and problem.schema == SCHEMA, "wrong backend problem")
    n, m = len(problem.columns), len(problem.rows)
    lp = api.HighsLp()
    lp.num_col_, lp.num_row_ = n, m
    lp.col_names_, lp.row_names_ = list(problem.columns), [r.name for r in problem.rows]
    lp.col_cost_, lp.offset_, lp.sense_ = list(problem.linear), problem.constant, api.ObjSense.kMinimize
    lp.col_lower_ = [float("-inf") if v is None else v for v in problem.lower]
    lp.col_upper_ = [float("inf") if v is None else v for v in problem.upper]
    lp.row_lower_ = [float("-inf") if r.lower is None else r.lower for r in problem.rows]
    lp.row_upper_ = [float("inf") if r.upper is None else r.upper for r in problem.rows]
    lp.integrality_ = [api.HighsVarType.kContinuous]*n
    matrix = api.HighsSparseMatrix()
    matrix.num_col_, matrix.num_row_, matrix.format_ = n, m, api.MatrixFormat.kRowwise
    starts, indices, values = [0], [], []
    for row in problem.rows:
        for i, v in row.terms: indices.append(i); values.append(v)
        starts.append(len(indices))
    matrix.start_, matrix.index_, matrix.value_ = starts, indices, values
    lp.a_matrix_ = matrix
    model = api.HighsModel()
    model.lp_ = lp
    if problem.quadratic:
        hess = api.HighsHessian()
        hess.dim_, hess.format_ = n, api.HessianFormat.kTriangular
        start, index, value = hessian_columns(problem)
        hess.start_, hess.index_, hess.value_ = list(start), list(index), list(value)
        model.hessian_ = hess
    return model


def call_highs(problem, log_path, *, api=None):
    """One explicit native attempt, no retry. Caller must hold separate run authority."""
    started = time.monotonic()
    record = dict(schema="staged_highs_raw_v1", problem_sha=problem.identity, problem=asdict(problem),
                  options={**options_for(problem), "log_file": str(Path(log_path).absolute())}, version_expected=VERSION,
                  stage="import", run_invoked=False, run_returned=False, api_calls=[], cleanup_error=None)
    solver = None
    failure = None
    try:
        if api is None:
            import highspy as api  # Deliberately lazy; tests supply a pure fake API.
        c.require(not Path(log_path).exists() and Path(log_path).parent.is_dir(), "exclusive native log target required")
        record["stage"] = "construct"
        solver = api.Highs()
        record["api_version"] = solver.version()
        record["api_githash"] = solver.githash()
        record["api_version_parts"] = [solver.versionMajor(), solver.versionMinor(), solver.versionPatch()]
        c.require(record["api_version"] == VERSION, "native API version differs")

        def ok(stage, status):
            name = enum_name(status)
            record["api_calls"].append(dict(stage=stage, status=name, value=status.value))
            c.require(status == api.HighsStatus.kOk and name == "kOk", "native interface did not return kOk")

        record["stage"] = "options"
        for name, value in record["options"].items():
            ok("set_"+name, solver.setOptionValue(name, value))
            status, actual = solver.getOptionValue(name)
            ok("get_"+name, status)
            c.require(type(actual) is type(value) and actual == value, "native option readback differs")
        record["stage"] = "pass_model"
        ok("pass_model", solver.passModel(make_model(problem, api)))
        record["stage"], record["run_invoked"] = "run", True
        status = solver.run()
        record["run_returned"] = True
        # Extract diagnostics even after a run warning. The warning remains a
        # failure and can never be superseded by an optimal model status.
        try: ok("run", status)
        except ValueError as error: failure = error
        record["stage"] = "extract"
        def model_status():
            status = solver.getModelStatus()
            return dict(model_status=enum_name(status), model_status_value=status.value)
        getters = {
            "model": model_status,
            "solution": lambda: {"solution": (lambda s: dict(primal_valid=s.value_valid, dual_valid=s.dual_valid,
                **{name: [scalar(v) for v in getattr(s, name)] for name in ("col_value", "row_value", "col_dual", "row_dual")}))(solver.getSolution())},
            "info": lambda: {"info": (lambda i: {name: scalar(getattr(i, name)) for name in INFO_FIELDS})(solver.getInfo())},
            "timing": lambda: dict(native_run_seconds=scalar(solver.getRunTime()), objective_value=scalar(solver.getObjectiveValue())),
        }
        for name, getter in getters.items():
            try: record.update(getter())
            except BaseException as error:
                record.setdefault("extraction_errors", {})[name] = dict(type=type(error).__name__, message=str(error))
                failure = failure or error
        if failure is not None: raise failure
        record["stage"] = "returned"
    except BaseException as error:
        failure = error
        record["error"] = dict(type=type(error).__name__, message=str(error))
    finally:
        if solver is not None:
            try:
                cleanup = solver.clear()
                record["cleanup_status"] = dict(name=enum_name(cleanup), value=cleanup.value)
                c.require(enum_name(cleanup) == "kOk" and cleanup == api.HighsStatus.kOk, "native clear failed")
            except BaseException as error:
                record["cleanup_error"] = dict(type=type(error).__name__, message=str(error))
                failure = failure or error
        record["elapsed_seconds"] = time.monotonic()-started
    try:
        path = Path(log_path)
        info = path.lstat()
        c.require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
                  and not getattr(info, "st_file_attributes", 0)&0x400, "ordinary native log missing")
        raw_log = path.read_bytes()
        record["log_pin"] = dict(bytes=len(raw_log), sha256=hashlib.sha256(raw_log).hexdigest())
    except BaseException as error:
        failure = failure or error
        record["artifact_error"] = dict(type=type(error).__name__, message=str(error))
    record["elapsed_seconds"] = time.monotonic()-started
    if failure is not None: raise BackendFailure(record, failure) from failure
    return record


def snapshot_from_raw(problem, raw):
    c.require(raw["schema"] == "staged_highs_raw_v1" and raw["problem_sha"] == problem.identity
              and c.digest(raw["problem"]) == c.digest(asdict(problem)), "raw problem binding differs")
    c.require(raw.get("stage") in ("returned", "extract") and raw.get("cleanup_error") is None
              and raw.get("run_invoked") is True and raw.get("run_returned") is True, "raw native call incomplete")
    c.require(raw.get("artifact_error") is None and type(raw.get("log_pin")) is dict, "raw native log incomplete")
    c.require(raw.get("cleanup_status") == dict(name="kOk", value=0), "raw native cleanup not confirmed")
    c.require(not raw.get("extraction_errors") and all(k in raw for k in
              ("model_status", "model_status_value", "solution", "info", "native_run_seconds", "objective_value")),
              "native diagnostics extraction incomplete")
    c.require(type(raw["model_status_value"]) is int and raw["model_status"] in MODEL_STATUS
              and raw["model_status_value"] == MODEL_STATUS[raw["model_status"]], "native model status name/value differs")
    c.require(type(raw["info"]) is dict and set(raw["info"]) == set(INFO_FIELDS)
              and type(raw["solution"]) is dict and set(raw["solution"]) ==
              {"primal_valid", "dual_valid", "col_value", "row_value", "col_dual", "row_dual"},
              "native getter payload incomplete")
    c.require(raw.get("api_version") == VERSION and raw.get("version_expected") == VERSION, "raw native version differs")
    c.require(type(raw.get("api_githash")) is str and bool(raw["api_githash"])
              and raw.get("api_version_parts") == [1, 15, 1], "raw native build identity differs")
    expected_options = options_for(problem)
    c.require(set(raw["options"]) == {*expected_options, "log_file"}
              and all(type(raw["options"][k]) is type(v) and raw["options"][k] == v for k, v in expected_options.items()),
              "raw native options differ")
    expected_stages = [s for name in raw["options"] for s in ("set_"+name, "get_"+name)]+["pass_model", "run"]
    # Canonical JSON sorts object keys, so validate per-option set/get adjacency
    # from the recorded call sequence instead of relying on mapping order.
    stages = [v["stage"] for v in raw["api_calls"]]
    c.require(len(stages) == len(expected_stages) and stages[-2:] == ["pass_model", "run"]
              and set(stages) == set(expected_stages)
              and all(stages.index("get_"+name) == stages.index("set_"+name)+1 for name in raw["options"])
              and all(v["status"] == "kOk" and v["value"] == 0 for v in raw["api_calls"][:-1]), "raw API call trace differs")
    run = raw["api_calls"][-1]
    if (run["status"], run["value"]) in (("kWarning", 1), ("kError", -1)):
        c.require(raw["stage"] == "extract", "raw warning stage differs")
        raise UnresolvedNumeric("native run returned non-kOk; infeasibility not inferred")
    c.require(run["status"] == "kOk" and run["value"] == 0 and raw["stage"] == "returned", "raw native return differs")
    s = raw["solution"]
    if raw["model_status"] != "kOptimal" or s["primal_valid"] is not True:
        raise UnresolvedNumeric("native unresolved; infeasibility not inferred")
    c.require(type(raw.get("model_status_value")) is int and raw["model_status_value"] == 7,
              "native model status name/value differs")
    c.require(raw["info"]["valid"] is True, "native info unresolved")
    c.require(type(s["dual_valid"]) is bool, "native dual validity malformed")
    info = raw["info"]
    for side in ("primal", "dual") if s["dual_valid"] else ("primal",):
        c.require(type(info[side+"_solution_status"]) is int and info[side+"_solution_status"] == 2
                  and type(info["num_"+side+"_infeasibilities"]) is int and info["num_"+side+"_infeasibilities"] == 0,
                  "native feasibility status unresolved")
        for name in ("max_"+side+"_infeasibility", "sum_"+side+"_infeasibilities"):
            v = info[name]
            c.require(type(v) in (int, float) and isfinite(v) and v >= 0, "native infeasibility info nonfinite")
    if s["dual_valid"]:
        c.require(type(info["num_complementarity_violations"]) is int and info["num_complementarity_violations"] == 0,
                  "native complementarity count unresolved")
        for name in ("max_complementarity_violation",):
            v = info[name]
            c.require(type(v) in (int, float) and isfinite(v) and v >= 0, "native complementarity info nonfinite")
    c.require(type(raw["objective_value"]) in (float, int) and isfinite(raw["objective_value"])
              and abs(raw["objective_value"]-info["objective_function_value"]) <= 1e-6, "native objective getters differ")
    # Invalid native dual arrays remain in raw. They do not become evidence.
    return NumericSnapshot(problem.identity, raw["model_status"], s["primal_valid"], s["dual_valid"],
        tuple(s["col_value"]), tuple(s["row_value"]), tuple(s["col_dual"]) if s["dual_valid"] else (),
        tuple(s["row_dual"]) if s["dual_valid"] else (), raw["info"]["objective_function_value"], SNAPSHOT_SCHEMA)
