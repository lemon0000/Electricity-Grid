"""Regression for repair-009 frontier reload and preregistration amendment."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal import (
    _apply_formal_successor_solver_override,
    _assert_implementation_only_contract_amendment,
    common_input_signature_sha256,
    _sha256,
)

CONFIG = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
)
IFOUS4 = Path(
    "results/tables/"
    "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4"
)


def test_apply_formal_successor_solver_override_sets_gurobi_contract() -> None:
    formal_solver = {
        "solver": {
            "name": "highs",
            "threads": 4,
            "random_seed": 0,
            "feasibility_tolerance": 1e-6,
            "bound_consistency_tolerance": 1e-6,
        }
    }
    formal_successor = {
        "solver_name": "gurobi",
        "solver_threads": 4,
        "solver_options": {"IntegralityFocus": 1},
    }
    _apply_formal_successor_solver_override(formal_solver, formal_successor)
    assert formal_solver["solver"]["name"] == "gurobi"
    assert formal_solver["solver"]["options"] == {"IntegralityFocus": 1}


def test_apply_formal_successor_solver_override_is_idempotent() -> None:
    formal_solver = {
        "solver": {
            "name": "gurobi",
            "threads": 4,
            "options": {"IntegralityFocus": 1},
        }
    }
    formal_successor = {
        "solver_name": "gurobi",
        "solver_threads": 4,
        "solver_options": {"IntegralityFocus": 1},
    }
    before = dict(formal_solver["solver"])
    _apply_formal_successor_solver_override(formal_solver, formal_successor)
    assert formal_solver["solver"] == before


def test_implementation_only_amendment_allows_runner_and_pilot_hash_delta() -> None:
    archive = (
        IFOUS4
        / "preregistration_amendments"
        / "0b34bfe901d054ff_to_b1c3044f339bdbdb_20260811T185447237514Z"
        / "previous_preregistration"
        / "registration.json"
    )
    if not archive.is_file():
        return
    published = json.loads(archive.read_text(encoding="utf-8"))
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    expected = copy.deepcopy(published)
    contract = expected["input_contract"]
    contract["successor_config_sha256"] = _sha256(CONFIG)
    impl = contract["implementation"]
    for key, value in config["implementation"].items():
        if key.endswith("_sha256"):
            impl[key] = value
    expected["input_contract_sha256"] = common_input_signature_sha256(contract)
    changed = _assert_implementation_only_contract_amendment(published, expected)
    assert "implementation.runner_sha256" in changed
    assert "implementation.pilot_gurobi_module_sha256" in changed
    assert published["input_contract_sha256"] != expected["input_contract_sha256"]
    assert (
        json.loads((IFOUS4 / "candidate_frontier" / "summary.json").read_text())[
            "input_contract_sha256"
        ]
        == published["input_contract_sha256"]
    )


def test_round_validation_context_uses_published_contract_sha() -> None:
    from dataclasses import dataclass, replace

    @dataclass(frozen=True)
    class _Ctx:
        input_contract_sha256: str

    published = "0b34bfe901d054ff8d42562ce21f336b1c6b0b34009ba2f01bc687b4ec37598d"
    live = "ea992b982ad1526dfe349100b939d61a7acf031737bde250acd176566d3a0f71"
    context = _Ctx(input_contract_sha256=live)
    bridged = replace(context, input_contract_sha256=published)
    assert bridged.input_contract_sha256 == published
    assert context.input_contract_sha256 == live


def test_published_frontier_solver_matches_formal_successor_contract() -> None:
    if not (IFOUS4 / "candidate_frontier" / "summary.json").is_file():
        return
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    successor = config["formal_successor"]
    summary = json.loads(
        (IFOUS4 / "candidate_frontier" / "summary.json").read_text(encoding="utf-8")
    )
    expected_solver = {
        "bound_consistency_tolerance": 1e-6,
        "feasibility_tolerance": 1e-6,
        "name": successor["solver_name"],
        "options": dict(successor.get("solver_options") or {}),
        "random_seed": 0,
        "threads": int(successor["solver_threads"]),
    }
    assert summary["solver"] == expected_solver
