from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from experiments import audit_rts_gmlc_solver_inventory as inventory


def _interfaces(available: bool = True):
    return {
        solver: [
            {
                "name": names[0],
                "available": available,
                "implementation": "test.Interface",
                "error": None,
            }
        ]
        for solver, names in inventory._INTERFACES.items()
    }


def _licenses():
    return {
        "highs": {"classification": "unrestricted_open_source"},
        "gurobi": {"classification": "restricted_non_production"},
        "cplex": {"classification": "community"},
        "xpress": {"classification": "community"},
    }


def test_capacity_boundaries_and_model_sizes_are_schema_locked() -> None:
    assert inventory._MODEL_SIZES == {
        "formal_24h_candidate_proxy_stage": {
            "variables": 215689,
            "constraints": 350615,
        },
        "solver_pilot_6h_candidate_proxy_stage": {
            "variables": 53923,
            "constraints": 87545,
        },
    }
    assert inventory._CAPACITY_BOUNDARIES["gurobi"]["maximum_variables"] == 2000
    assert inventory._CAPACITY_BOUNDARIES["cplex"]["maximum_constraints"] == 1000
    assert (
        inventory._CAPACITY_BOUNDARIES["xpress"]["maximum_rows_plus_columns"]
        == 5000
    )
    assert inventory._CAPACITY_BOUNDARIES["highs"]["maximum_variables"] is None


def test_eligibility_marks_only_highs_formal_eligible() -> None:
    observed = inventory._eligibility(_interfaces(), _licenses())

    assert observed["highs"]["eligible_for_formal"]
    assert observed["highs"]["eligible_for_6h_pilot"]
    for solver in ("gurobi", "cplex", "xpress"):
        assert not observed[solver]["eligible_for_formal"]
        assert not observed[solver]["eligible_for_6h_pilot"]
        assert observed[solver]["formal_ineligibility_reasons"]


def test_xpress_eligibility_uses_combined_rows_and_columns() -> None:
    formal = inventory._capacity_reasons(
        "xpress", "formal_24h_candidate_proxy_stage"
    )
    pilot = inventory._capacity_reasons(
        "xpress", "solver_pilot_6h_candidate_proxy_stage"
    )

    assert formal == ["rows_plus_columns_566304_exceed_observed_limit_5000"]
    assert pilot == ["rows_plus_columns_141468_exceed_observed_limit_5000"]


def test_payload_disclaims_legal_and_project_solve_claims(monkeypatch) -> None:
    monkeypatch.setattr(inventory, "_pyomo_interfaces", lambda: _interfaces())
    monkeypatch.setattr(inventory, "_license_observations", _licenses)
    monkeypatch.setattr(
        inventory,
        "_package_versions",
        lambda: {name: "test" for name in inventory._PACKAGE_NAMES},
    )
    monkeypatch.setattr(
        inventory,
        "_runtime_versions",
        lambda: {"python": "test"},
    )

    payload = inventory._build_inventory_payload()

    assert payload["schema"] == "rts_gmlc_solver_inventory_v1"
    assert not payload["license_observation_is_legal_conclusion"]
    assert not payload["capacity_boundaries_retested_by_this_audit"]
    assert not payload["project_model_built_or_solved"]
    assert not payload["formal_candidate_started"]


def test_atomic_inventory_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    payload = {
        "schema": "rts_gmlc_solver_inventory_v1",
        "status": "test",
    }
    monkeypatch.setattr(inventory, "_build_inventory_payload", lambda: payload)
    target = tmp_path / "inventory"

    first = inventory.run(output_directory=target)
    before = {
        path.name: path.read_bytes() for path in target.iterdir() if path.is_file()
    }
    second = inventory.run(output_directory=target)

    assert first == second == payload
    assert before == {
        path.name: path.read_bytes() for path in target.iterdir() if path.is_file()
    }
    manifest = (target / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    assert manifest == [
        f"{hashlib.sha256((target / 'inventory.json').read_bytes()).hexdigest()}  inventory.json"
    ]
    assert not list(tmp_path.glob(".inventory.processing-*"))


def test_idempotent_inventory_rejects_environment_drift(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "inventory"
    monkeypatch.setattr(
        inventory,
        "_build_inventory_payload",
        lambda: {"schema": "rts_gmlc_solver_inventory_v1", "version": 1},
    )
    inventory.run(output_directory=target)
    original = (target / "inventory.json").read_bytes()
    monkeypatch.setattr(
        inventory,
        "_build_inventory_payload",
        lambda: {"schema": "rts_gmlc_solver_inventory_v1", "version": 2},
    )

    with pytest.raises(RuntimeError, match="drifted from the environment"):
        inventory.run(output_directory=target)
    assert (target / "inventory.json").read_bytes() == original
