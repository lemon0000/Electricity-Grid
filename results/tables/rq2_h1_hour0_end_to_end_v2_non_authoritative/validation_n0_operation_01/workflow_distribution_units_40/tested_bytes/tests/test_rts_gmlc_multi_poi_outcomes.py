from pathlib import Path

import pytest
import yaml

from experiments.handle_rts_gmlc_multi_poi_outcomes import (
    _diagnostic_audit,
    _read_amendment_config,
)
from src.grid import RtsGmlcSolverAudit

AMENDMENT_PATH = Path("configs/rts_gmlc_google_day0_multi_poi_outcome_amendment.yaml")


def test_outcome_amendment_is_limited_to_serialization_and_aggregation():
    config = _read_amendment_config(AMENDMENT_PATH)

    assert config["observed_before_amendment"]["feasible_candidate_buses"] == [
        108,
        120,
    ]
    assert config["observed_before_amendment"]["failed_candidate_bus"] == 208
    assert config["observed_before_amendment"][
        "remaining_full_candidate_outcomes_unseen"
    ] == [220, 308, 320]
    assert "model_constraints" in config["scope"]["forbidden_changes"]
    assert "comparison_or_representative_rules" in config["scope"]["forbidden_changes"]
    assert config["scope"]["infeasible_candidate_counts_as_completed"]


def test_outcome_amendment_rejects_a_scientific_scope_change(tmp_path):
    config = yaml.safe_load(AMENDMENT_PATH.read_text(encoding="utf-8"))
    config["scope"]["forbidden_changes"].remove("model_constraints")
    path = tmp_path / "invalid-amendment.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="scope drifted"):
        _read_amendment_config(path)


def test_infeasibility_diagnostic_audit_omits_economic_outcomes():
    audit = RtsGmlcSolverAudit(
        accepted=False,
        termination_condition="infeasible",
        solver_status="ok",
        solver_message="test",
        objective_usd=10.0,
        lower_bound_usd=9.0,
        upper_bound_usd=10.0,
        absolute_gap_usd=1.0,
        gap_tolerance_usd=0.1,
        maximum_constraint_violation=None,
        maximum_integrality_violation=None,
        solver_threads=4,
        configured_mip_relative_gap=1.0e-6,
    )

    payload = _diagnostic_audit(audit)

    assert payload["termination_condition"] == "infeasible"
    assert not {
        "objective_usd",
        "lower_bound_usd",
        "upper_bound_usd",
        "absolute_gap_usd",
        "gap_tolerance_usd",
    } & set(payload)
