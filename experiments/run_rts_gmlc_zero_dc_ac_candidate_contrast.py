"""Zero-DC AC contrast: does a repair-009 candidate commitment recover h15/h21?

Diagnostic sensitivity only.  This script reuses the frozen zero-DC AC
machinery read-only and injects nothing but a commitment / generation vector
taken from a published repair-009 candidate checkpoint.  Data-centre injection
is held at exactly 0 MW so the boundary matches the published zero-DC control
in ``docs/model_spec/blocker_register.md``.

It cannot and does not certify security.  There is no access equipment, no
real P/Q envelope, no full N-1.  ``security_certified`` stays false.

Why this exists
---------------
The published zero-DC diagnostics recover 22/24 hours; h15 and h21 return
``Infeasible_Problem_Detected`` under the official voltage bounds, and a
symmetric 0.01 p.u. relaxation makes all 24 succeed.  That points at a
marginal voltage limit rather than at the commitment.  Candidates 1 and 5 of
the repair-009 frontier are near-identical apart from a set of extra
synchronous CT/CC units, so running both through the same AC path is a clean
contrast: if candidate 5 recovers h15/h21 and candidate 1 does not, the extra
reactive support is the mechanism; if neither does, the frontier cannot answer
the question and the base-case voltage/reactive data is where to look.

Hour mapping is NOT assumed
---------------------------
A candidate checkpoint stores ``commitment`` / ``generation_mw`` as bare
24-element lists with no timestamps.  This script therefore derives the
authoritative timestamp order from the zero-DC baseline's own hourly rows and
maps candidate list position -> that order, then records the resulting
mapping in the output so it can be audited.  It refuses to run if the baseline
does not yield exactly 24 unique timestamps or the candidate lists are not
length 24.

Self-check
----------
The zero-DC baseline commitment is run through the identical code path as a
control.  If this harness cannot reproduce the published outcome (h15/h21 not
witnessed, the other hours witnessed), ``harness_reproduces_published_baseline``
is false and every candidate row in the same run must be treated as void.
Without that gate a buggy harness reporting "candidate passes" would be the
easiest possible false positive to accept.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

import yaml

import experiments.run_rts_gmlc_zero_dc_ac_recovery as primary
from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _configure_q_capable_voltage_control,
)
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows
from src.grid.rts_gmlc_ac_ipopt import solve_ac_feasibility_ipopt
from src.grid.rts_gmlc_ac_recovery import prepare_rts_gmlc_ac_recovery

# Frozen scope of this diagnostic.
_IPOPT_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic.yaml")
_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_candidate_contrast_v1"
)
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_ac_candidate_contrast.py"),
    Path("experiments/run_rts_gmlc_zero_dc_ac_recovery.py"),
    Path("experiments/run_rts_gmlc_zero_dc_ac_ipopt_diagnostic.py"),
    Path("src/grid/rts_gmlc_ac_recovery.py"),
    Path("src/grid/rts_gmlc_ac_ipopt.py"),
    Path("src/grid/rts_gmlc_ac.py"),
)

# Published zero-DC outcome this harness must reproduce before candidate rows
# may be read.  Source: docs/model_spec/blocker_register.md (IPOPT, official
# bounds, three fixed initial strategies, 22/24 each, h15/h21 infeasible).
_TARGET_HOURS = ("2020-01-01T15:00:00+00:00", "2020-01-01T21:00:00+00:00")
_CONTROL_HOUR = "2020-01-01T00:00:00+00:00"
_INITIAL_STRATEGIES = ("source", "midpoint", "flat_target_midq")

# Candidate checkpoints are read only for their commitment/generation vectors.
# They carry an older input_contract_sha256 and are NOT reusable as checkpoints.
_CANDIDATE_ROOT = Path(
    ".backup_repair009_output_20260805T113832Z"
    "/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009"
    "/candidate_checkpoints"
)
_CANDIDATES = (
    ("candidate_01", "01_q_proxy_delta_0p0010"),
    ("candidate_05", "05_q_proxy_delta_0p0200"),
)

_WITNESS_TOLERANCE = 1.0e-6


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)


def _result_field(result: Any, name: str) -> Any:
    value = getattr(result, name, None)
    if value is None and is_dataclass(result):
        value = asdict(result).get(name)
    return value


def _witness(result: Any) -> bool:
    """Feasibility witness, ported verbatim from the published diagnostic gate.

    Solved + converged + every violation within 1e-6.  Kept identical so that
    'witnessed' here means the same thing it means in blocker_register.md.
    """
    if not bool(_result_field(result, "solved")):
        return False
    if not bool(_result_field(result, "converged")):
        return False
    for name in (
        "maximum_voltage_violation_pu",
        "maximum_branch_violation",
        "maximum_active_power_violation_mw",
        "maximum_reactive_power_violation_mvar",
        "maximum_slack_pg_deviation_mw",
    ):
        value = _result_field(result, name)
        if value is None:
            continue
        if abs(float(value)) > _WITNESS_TOLERANCE:
            return False
    return True


def _ipopt_solver_options() -> dict[str, object]:
    config = yaml.safe_load(_IPOPT_CONFIG_PATH.read_text(encoding="utf-8"))
    options = config["solver"]["ipopt_options"]
    if not isinstance(options, Mapping):
        raise RuntimeError("zero-DC contrast: ipopt_options drifted")
    return dict(options)


def _load_candidate(directory: Path) -> dict[str, Any]:
    payload = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
    candidate = payload["candidate"]
    for key in ("commitment", "generation_mw", "branch_flows_mw"):
        series = candidate[key]
        if not isinstance(series, list) or len(series) != 24:
            raise RuntimeError(
                f"zero-DC contrast: candidate {key} is not a 24-element list"
            )
    return {
        "requested_candidate_id": candidate["requested_candidate_id"],
        "operating_cost_usd": candidate["operating_cost_usd"],
        "reactive_proxy_fraction": candidate["reactive_proxy_fraction"],
        "commitment_sha256": candidate["commitment_sha256"],
        "checkpoint_input_contract_sha256": payload["input_contract_sha256"],
        "checkpoint_manifest_sha256": _sha256(directory / "SHA256SUMS"),
        "commitment": candidate["commitment"],
        "generation_mw": candidate["generation_mw"],
        "branch_flows_mw": candidate["branch_flows_mw"],
    }


def _baseline_timestamps(hourly: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    timestamps = tuple(str(row["timestamp"]) for row in hourly)
    if len(timestamps) != 24 or len(set(timestamps)) != 24:
        raise RuntimeError("zero-DC contrast: baseline hourly timestamps drifted")
    for target in _TARGET_HOURS + (_CONTROL_HOUR,):
        if target not in timestamps:
            raise RuntimeError(f"zero-DC contrast: baseline lacks {target}")
    return timestamps


def _solve_one(
    context: Any,
    point: Any,
    *,
    commitment: Mapping[str, bool],
    generation_mw: Mapping[str, float],
    branch_flows_mw: Mapping[str, float],
    initial_strategy: str,
    solver_options: Mapping[str, object],
) -> tuple[Any, float, float]:
    placeholder_bus = int(context.config["zero_control"]["dc_bus_api_placeholder"])
    tolerance_mw = float(context.config["solver"]["tolerance_mw"])
    dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
        context.ac.scan_context.data,
        demand_by_bus_mw=point.demand_by_bus_mw,
        generation_mw=generation_mw,
        ac_branch_flows_mw=branch_flows_mw,
        tolerance_mw=tolerance_mw,
    )
    configured = _configure_q_capable_voltage_control(
        context.ac.template,
        context.ac.scan_context.data,
        point,
        generation_mw=generation_mw,
        commitment=commitment,
        dc_bus=placeholder_bus,
        data_center_power_mw=0.0,
        data_center_power_factor=1.0,
        dc_flows_mw=dc_flows,
    )
    prepared = prepare_rts_gmlc_ac_recovery(
        configured,
        context.ac.template,
        context.ac.scan_context.data,
        mode=primary._MODE if hasattr(primary, "_MODE") else "distributed_committable",
        voltage_limits_pu=(0.95, 1.05),
    )
    started = perf_counter()
    result = solve_ac_feasibility_ipopt(
        prepared,
        initial_strategy=initial_strategy,
        solver_options=dict(solver_options),
    )
    return result, perf_counter() - started, float(residual)


def run_contrast(*, hours: Sequence[str] | None = None) -> dict[str, Any]:
    solver_options = _ipopt_solver_options()
    context = primary._build_context(primary._CONFIG_PATH)
    hourly, generation, commitment, flows = primary._load_zero_dispatch(
        context, primary._ZERO_OUTPUT_ROOT
    )
    timestamps = _baseline_timestamps(hourly)
    point_by_timestamp = {
        point.timestamp.isoformat(): point
        for point in context.ac.scan_context.business.points
    }

    selected = tuple(hours) if hours else (_CONTROL_HOUR,) + _TARGET_HOURS
    for timestamp in selected:
        if timestamp not in timestamps:
            raise RuntimeError(f"zero-DC contrast: unknown hour {timestamp}")

    candidates = {
        label: _load_candidate(_CANDIDATE_ROOT / name) for label, name in _CANDIDATES
    }

    sources: list[tuple[str, Any]] = [("zero_dc_baseline", None)]
    sources.extend((label, candidates[label]) for label, _ in _CANDIDATES)

    rows: list[dict[str, Any]] = []
    for source_label, payload in sources:
        for timestamp in selected:
            hour_index = timestamps.index(timestamp)
            point = point_by_timestamp[timestamp]
            if payload is None:
                hour_commitment = commitment[timestamp]
                hour_generation = generation[timestamp]
                hour_flows = flows[timestamp]
            else:
                hour_commitment = payload["commitment"][hour_index]
                hour_generation = payload["generation_mw"][hour_index]
                hour_flows = payload["branch_flows_mw"][hour_index]
            for strategy in _INITIAL_STRATEGIES:
                try:
                    result, seconds, residual = _solve_one(
                        context,
                        point,
                        commitment=hour_commitment,
                        generation_mw=hour_generation,
                        branch_flows_mw=hour_flows,
                        initial_strategy=strategy,
                        solver_options=solver_options,
                    )
                    row = {
                        "source": source_label,
                        "timestamp": timestamp,
                        "hour_index": hour_index,
                        "initial_strategy": strategy,
                        "witnessed": _witness(result),
                        "solved": bool(_result_field(result, "solved")),
                        "converged": bool(_result_field(result, "converged")),
                        "status": str(_result_field(result, "status")),
                        "solve_seconds": seconds,
                        "dc_reconstruction_residual_mw": residual,
                        "error": None,
                    }
                    for name in (
                        "maximum_voltage_violation_pu",
                        "maximum_branch_violation",
                        "maximum_active_power_violation_mw",
                        "maximum_reactive_power_violation_mvar",
                        "maximum_slack_pg_deviation_mw",
                        "minimum_voltage_pu",
                        "maximum_voltage_pu",
                    ):
                        value = _result_field(result, name)
                        row[name] = None if value is None else float(value)
                except Exception as error:  # noqa: BLE001 - recorded, not hidden
                    row = {
                        "source": source_label,
                        "timestamp": timestamp,
                        "hour_index": hour_index,
                        "initial_strategy": strategy,
                        "witnessed": False,
                        "solved": False,
                        "converged": False,
                        "status": None,
                        "solve_seconds": None,
                        "dc_reconstruction_residual_mw": None,
                        "error": f"{type(error).__name__}: {error}",
                    }
                rows.append(row)

    def _witnessed(source: str, timestamp: str) -> bool:
        return any(
            row["witnessed"]
            for row in rows
            if row["source"] == source and row["timestamp"] == timestamp
        )

    baseline_control_ok = _witnessed("zero_dc_baseline", _CONTROL_HOUR)
    baseline_targets_absent = not any(
        _witnessed("zero_dc_baseline", hour) for hour in _TARGET_HOURS
    )
    harness_ok = bool(baseline_control_ok and baseline_targets_absent)

    per_source = {}
    for source_label, _ in sources:
        per_source[source_label] = {
            hour: _witnessed(source_label, hour)
            for hour in selected
        }

    summary = {
        "schema": "rts_gmlc_zero_dc_ac_candidate_contrast_results_v1",
        "security_certified": False,
        "diagnostic_sensitivity_only_not_security_certification": True,
        "data_center_power_mw": 0.0,
        "voltage_limits_pu": [0.95, 1.05],
        "witness_tolerance": _WITNESS_TOLERANCE,
        "initial_strategies": list(_INITIAL_STRATEGIES),
        "hours_solved": list(selected),
        "baseline_timestamp_order": list(timestamps),
        "candidate_hour_mapping_rule": (
            "candidate list position -> baseline hourly timestamp order; "
            "derived, not assumed to equal hour-of-day"
        ),
        "harness_reproduces_published_baseline": harness_ok,
        "harness_baseline_control_hour_witnessed": baseline_control_ok,
        "harness_baseline_target_hours_absent": baseline_targets_absent,
        "candidate_rows_void_if_harness_check_failed": True,
        "witness_by_source_and_hour": per_source,
        "candidate_metadata": {
            label: {
                key: payload[key]
                for key in (
                    "requested_candidate_id",
                    "operating_cost_usd",
                    "reactive_proxy_fraction",
                    "commitment_sha256",
                    "checkpoint_input_contract_sha256",
                    "checkpoint_manifest_sha256",
                )
            }
            for label, payload in candidates.items()
        },
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "rows": rows,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hours",
        nargs="*",
        default=None,
        help="ISO timestamps; default is the control hour plus h15/h21",
    )
    parser.add_argument("--output-directory", type=Path, default=_OUTPUT_ROOT)
    args = parser.parse_args()
    summary = run_contrast(hours=args.hours)
    target = args.output_directory
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(
        _stable_json(summary) + "\n", encoding="utf-8"
    )
    if not summary["harness_reproduces_published_baseline"]:
        print(
            "HARNESS CHECK FAILED - candidate rows are void; "
            "fix the harness before reading any candidate result."
        )
    print(_stable_json(summary["witness_by_source_and_hour"]))
    print(
        "harness_reproduces_published_baseline="
        f"{summary['harness_reproduces_published_baseline']}"
    )


if __name__ == "__main__":
    main()
