"""Fail-closed validator for the RQ2 V5 implementation successor v2."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
from itertools import product
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_implementation_successor_v2.yaml"
MODEL_RELATIVE = "src/rq2_joint_deliverability_v2/model.py"
SCENARIOS_RELATIVE = "src/rq2_joint_deliverability_v2/scenarios.py"
EVALUATION_RELATIVE = "src/rq2_joint_deliverability_v2/evaluation.py"
RUNNER_RELATIVE = "experiments/run_rq2_joint_deliverability_implementation_v2.py"
VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_joint_deliverability_implementation_v2.py"
)
TEST_RELATIVE = "tests/test_rq2_joint_deliverability_implementation_v2.py"
ARCHITECTURE_RELATIVE = "docs/model_spec/rq2_joint_deliverability_implementation_v2.md"
SRC_INIT_RELATIVE = "src/__init__.py"
IMPLEMENTATION_INIT_RELATIVE = "src/rq2_joint_deliverability_v2/__init__.py"
SOLVER_ADAPTER_RELATIVE = "src/rq2_joint_deliverability_v2/solver_adapter.py"
EXPERIMENTS_INIT_RELATIVE = "experiments/__init__.py"
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_implementation_successor_v2.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_implementation_successor_v2.OUTER.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
V5_OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5."
    "OUTER.SHA256SUMS.json"
)
V5_INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5.SHA256SUMS.json"
)
V5_REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_review_pass_v5.yaml"
)
V5_OUTER_SHA256 = "92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd"
V5_INNER_SHA256 = "84847114b6cd66925326f541f2ecfbd0ad825ca0591d09894c51c2db2ac1162f"
V5_REVIEW_SHA256 = "0ec073c38eac003255fa2d2753edb28f4d02e0f7756c34e185027ac23b140722"
V1_OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_implementation_successor_v1.OUTER.SHA256SUMS.json"
)
V1_INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_implementation_successor_v1.SHA256SUMS.json"
)
V1_REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_implementation_review_rework_v1.yaml"
)
V1_OUTER_SHA256 = "61493905239137a3e82093ce3da0daa75b86f82f3ff47a30e7bcc29097298699"
V1_INNER_SHA256 = "e2039c4505ca72c53aae1c75844a431165cdaf993ab275d14bbdbde5bed4a4f7"
V1_REVIEW_SHA256 = "5ee80168459bef736f25d833697bbb80498a72923edd4f995ce5680b24f907c0"
V5_MEMBERS = {
    "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml",
    "docs/model_spec/rq2_joint_deliverability_estimands_v4.md",
    "docs/plan/RQ2_联合服务可交付前沿确认性方案_v5.md",
    "experiments/validate_rq2_joint_deliverability_preregistration_successor_v5.py",
    "tests/test_rq2_joint_deliverability_preregistration_successor_v5.py",
}
V1_MEMBERS = {
    "configs/rq2_joint_deliverability_implementation_successor_v1.yaml",
    "docs/model_spec/rq2_joint_deliverability_implementation_v1.md",
    "experiments/run_rq2_joint_deliverability_implementation_v1.py",
    "experiments/validate_rq2_joint_deliverability_implementation_v1.py",
    "src/evaluation/rq2_joint_deliverability.py",
    "src/models/rq2_joint_deliverability.py",
    "src/scenarios/rq2_joint_deliverability.py",
    "tests/test_rq2_joint_deliverability_implementation_v1.py",
}
EXPECTED_MEMBERS = {
    CONFIG_RELATIVE,
    MODEL_RELATIVE,
    SCENARIOS_RELATIVE,
    EVALUATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
    TEST_RELATIVE,
    ARCHITECTURE_RELATIVE,
    SOLVER_ADAPTER_RELATIVE,
    SRC_INIT_RELATIVE,
    IMPLEMENTATION_INIT_RELATIVE,
    EXPERIMENTS_INIT_RELATIVE,
    V1_OUTER_RELATIVE,
    V1_REVIEW_RELATIVE,
}
EXPECTED_RUNTIME_MODULES = {
    SRC_INIT_RELATIVE,
    IMPLEMENTATION_INIT_RELATIVE,
    MODEL_RELATIVE,
    SCENARIOS_RELATIVE,
    EVALUATION_RELATIVE,
    SOLVER_ADAPTER_RELATIVE,
    EXPERIMENTS_INIT_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
}


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise TypeError(f"YAML mapping key must be a string: {key!r}")
        if key in result:
            raise ValueError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.load(_stable_bytes(path).decode("utf-8"), Loader=_UniqueKeyLoader)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a mapping")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(
        _stable_bytes(path).decode("utf-8"),
        object_pairs_hook=reject_duplicates,
    )
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(_stable_bytes(path)).hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _require_regular_file(path: Path, label: str) -> None:
    absolute = Path(os.path.abspath(path))
    for ancestor in reversed(absolute.parents):
        mode = os.lstat(ancestor).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ValueError(f"{label} has an unsafe ancestor")
    mode = os.lstat(absolute).st_mode
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError(f"{label} must be a regular file")


def _stable_bytes(path: Path) -> bytes:
    _require_regular_file(path, str(path))
    before = os.stat(path, follow_symlinks=False)
    first = path.read_bytes()
    middle = os.stat(path, follow_symlinks=False)
    second = path.read_bytes()
    after = os.stat(path, follow_symlinks=False)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(middle) or identity(middle) != identity(after):
        raise ValueError(f"file identity changed during stable read: {path}")
    if first != second:
        raise ValueError(f"file bytes changed during stable read: {path}")
    return first


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _functions(path: Path) -> set[str]:
    tree = ast.parse(_stable_bytes(path).decode("utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _imports(path: Path) -> set[str]:
    tree = ast.parse(_stable_bytes(path).decode("utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _called_names(path: Path) -> set[str]:
    tree = ast.parse(_stable_bytes(path).decode("utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _validate_authority(config: dict[str, Any]) -> None:
    expected = {
        "sealed_v5_outer": {
            "path": V5_OUTER_RELATIVE,
            "sha256": V5_OUTER_SHA256,
        },
        "v5_pass_receipt": {
            "path": V5_REVIEW_RELATIVE,
            "sha256": V5_REVIEW_SHA256,
        },
    }
    if config.get("scientific_authority") != expected:
        raise ValueError("scientific authority binding drifted")
    for label, item in expected.items():
        path = ROOT / item["path"]
        _require_regular_file(path, label)
        if _sha256(path) != item["sha256"]:
            raise ValueError(f"{label} SHA-256 drifted")
    outer = _load_json(ROOT / V5_OUTER_RELATIVE)
    if outer != {
        "schema": "rq2_joint_deliverability_preregistration_successor_outer_v5",
        "version": 5,
        "inner": {
            "path": V5_INNER_RELATIVE,
            "sha256": V5_INNER_SHA256,
        },
    }:
        raise ValueError("V5 scientific outer manifest drifted")
    inner_path = ROOT / V5_INNER_RELATIVE
    if _sha256(inner_path) != V5_INNER_SHA256:
        raise ValueError("V5 scientific inner manifest SHA-256 drifted")
    inner = _load_json(inner_path)
    if (
        set(inner) != {"schema", "files"}
        or inner.get("schema")
        != "rq2_joint_deliverability_preregistration_successor_manifest_v5"
    ):
        raise ValueError("V5 scientific inner manifest schema drifted")
    members = _mapping(inner["files"], "V5 scientific members")
    if set(members) != V5_MEMBERS:
        raise ValueError("V5 scientific member inventory drifted")
    for relative, digest in members.items():
        member = ROOT / relative
        _require_regular_file(member, f"V5 scientific member {relative}")
        if _sha256(member) != digest:
            raise ValueError(f"V5 scientific member SHA-256 drifted: {relative}")
    receipt = _load_yaml(ROOT / V5_REVIEW_RELATIVE)
    if (
        receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_subject")
        != {
            "outer_path": V5_OUTER_RELATIVE,
            "outer_sha256": V5_OUTER_SHA256,
            "inner_sha256": V5_INNER_SHA256,
            "sealed_member_count": 5,
        }
        or receipt.get("effect", {}).get("implementation_authorized") is not False
        or receipt.get("effect", {}).get("formal_execution_authorized") is not False
    ):
        raise ValueError("V5 scientific review is not PASS")


def _validate_predecessor_authority(config: dict[str, Any]) -> None:
    expected = {
        "sealed_v1_outer": {
            "path": V1_OUTER_RELATIVE,
            "sha256": V1_OUTER_SHA256,
        },
        "v1_rework_receipt": {
            "path": V1_REVIEW_RELATIVE,
            "sha256": V1_REVIEW_SHA256,
        },
    }
    if config.get("predecessor_authority") != expected:
        raise ValueError("predecessor authority binding drifted")
    for label, item in expected.items():
        path = ROOT / item["path"]
        _require_regular_file(path, label)
        if _sha256(path) != item["sha256"]:
            raise ValueError(f"{label} SHA-256 drifted")
    outer = _load_json(ROOT / V1_OUTER_RELATIVE)
    if outer != {
        "schema": "rq2_joint_deliverability_implementation_outer_v1",
        "version": 1,
        "inner": {
            "path": V1_INNER_RELATIVE,
            "sha256": V1_INNER_SHA256,
        },
    }:
        raise ValueError("V1 implementation outer manifest drifted")
    inner_path = ROOT / V1_INNER_RELATIVE
    if _sha256(inner_path) != V1_INNER_SHA256:
        raise ValueError("V1 implementation inner manifest SHA-256 drifted")
    inner = _load_json(inner_path)
    if (
        set(inner) != {"schema", "version", "files"}
        or inner.get("schema") != "rq2_joint_deliverability_implementation_inner_v1"
        or inner.get("version") != 1
    ):
        raise ValueError("V1 implementation inner manifest schema drifted")
    members = _mapping(inner["files"], "V1 implementation members")
    if set(members) != V1_MEMBERS:
        raise ValueError("V1 implementation member inventory drifted")
    for relative, digest in members.items():
        member = ROOT / relative
        _require_regular_file(member, f"V1 implementation member {relative}")
        if _sha256(member) != digest:
            raise ValueError(f"V1 implementation member SHA-256 drifted: {relative}")
    receipt = _load_yaml(ROOT / V1_REVIEW_RELATIVE)
    if (
        receipt.get("verdict") != "REWORK"
        or receipt.get("reviewed_subject")
        != {
            "outer_path": V1_OUTER_RELATIVE,
            "outer_sha256": V1_OUTER_SHA256,
            "inner_sha256": V1_INNER_SHA256,
            "sealed_member_count": 8,
        }
        or receipt.get("effect", {}).get("v1_bytes_immutable") is not True
        or receipt.get("effect", {}).get("one_focused_versioned_successor_allowed")
        is not True
        or receipt.get("effect", {}).get("formal_execution_authorized") is not False
    ):
        raise ValueError("V1 implementation review is not an authorized REWORK")


def _validate_inventory(config: dict[str, Any]) -> None:
    implementation = _mapping(config.get("implementation"), "implementation")
    expected_paths = {
        "model": MODEL_RELATIVE,
        "scenarios": SCENARIOS_RELATIVE,
        "evaluation": EVALUATION_RELATIVE,
        "runner": RUNNER_RELATIVE,
        "validator": VALIDATOR_RELATIVE,
        "tests": TEST_RELATIVE,
        "architecture": ARCHITECTURE_RELATIVE,
    }
    if set(implementation) != set(expected_paths):
        raise ValueError("implementation inventory drifted")
    for name, expected in expected_paths.items():
        item = _mapping(implementation[name], f"implementation {name}")
        if item != {"path": expected}:
            raise ValueError(f"implementation path drifted: {name}")
        _require_regular_file(ROOT / expected, f"implementation {name}")
    dependencies = _mapping(config.get("local_dependencies"), "local dependencies")
    if dependencies != {
        "experiments_package_initializer": {
            "path": EXPERIMENTS_INIT_RELATIVE,
        },
        "implementation_package_initializer": {
            "path": IMPLEMENTATION_INIT_RELATIVE,
        },
        "src_package_initializer": {
            "path": SRC_INIT_RELATIVE,
        },
        "solver_adapter": {
            "path": SOLVER_ADAPTER_RELATIVE,
        },
    }:
        raise ValueError("local dependency inventory drifted")
    for name, item in dependencies.items():
        _require_regular_file(
            ROOT / str(item["path"]),
            f"local dependency {name}",
        )


def _validate_symbols() -> None:
    required = {
        MODEL_RELATIVE: {
            "effective_request",
            "build_arm_planning_model",
            "audit_fixed_service_trajectory",
            "solve_arm_minimum_capacity",
        },
        SCENARIOS_RELATIVE: {
            "load_power_blocks",
            "load_workload_blocks",
            "expand_registered_cells",
            "raw_cfe_request",
            "build_pair_scenario",
            "select_representatives",
            "condition_finite_power",
            "structural_recovery_witness",
            "scenario_track_requirements",
            "network_capacity_key",
        },
        EVALUATION_RELATIVE: {
            "finalize_capacity_certificate",
            "capacity_contrast_intervals",
            "capacity_attribution",
            "execute_holdout_policy",
            "finite_conditioning",
            "certify_scalar_transport",
            "operational_labels",
            "bootstrap_raw_draw_stream",
            "bootstrap_draw_stream",
            "bootstrap_transport_intervals",
            "canonical_certificate_payload",
            "sealed_holdout_probe_projection",
            "recursive_manifest",
            "publish_output_bundle",
            "validate_transport_runtime",
        },
        RUNNER_RELATIVE: {
            "planning_task_inventory",
            "execute_capacity_stage",
            "execute_holdout_stage",
            "execute_identification_stage",
            "build_report",
            "validate_runtime_config",
            "run",
        },
    }
    for relative, names in required.items():
        missing = names - _functions(ROOT / relative)
        if missing:
            raise ValueError(f"{relative} missing functions: {sorted(missing)}")
    validator_imports = _imports(ROOT / VALIDATOR_RELATIVE)
    if {"scipy", "scipy.optimize", "pyomo", "pyomo.environ"} & validator_imports:
        raise ValueError("validator imports an optimization runtime")
    if {"linprog", "SolverFactory"} & _called_names(ROOT / VALIDATOR_RELATIVE):
        raise ValueError("validator calls an optimization solver")
    model_imports = _imports(ROOT / MODEL_RELATIVE)
    if (
        "src.models.economic_temporal_stochastic" in model_imports
        or "solver_adapter" not in model_imports
    ):
        raise ValueError("model local dependency closure drifted")
    expected_versioned_imports = {
        SCENARIOS_RELATIVE: {"model"},
        EVALUATION_RELATIVE: {
            "model",
            "solver_adapter",
        },
        RUNNER_RELATIVE: {
            "experiments.validate_rq2_joint_deliverability_implementation_v2",
            "src.rq2_joint_deliverability_v2.evaluation",
            "src.rq2_joint_deliverability_v2.model",
            "src.rq2_joint_deliverability_v2.scenarios",
            "src.rq2_joint_deliverability_v2.solver_adapter",
        },
    }
    for relative, expected_imports in expected_versioned_imports.items():
        if not expected_imports.issubset(_imports(ROOT / relative)):
            raise ValueError(f"versioned import closure drifted: {relative}")
    evaluation_source = _stable_bytes(ROOT / EVALUATION_RELATIVE).decode("utf-8")
    if (
        "common_pi" in evaluation_source
        or "classify_registered_attribution" in evaluation_source
    ):
        raise ValueError("V5 implementation references the retired classifier")
    runner_calls = _called_names(ROOT / RUNNER_RELATIVE)
    required_runner_calls = {
        "bootstrap_draw_stream",
        "bootstrap_transport_intervals",
        "canonical_certificate_payload",
        "finalize_operational_attribution",
    }
    if not required_runner_calls.issubset(runner_calls):
        raise ValueError("runner does not wire the registered identification path")


def _validate_cells(scientific: dict[str, Any]) -> None:
    factors = scientific["registered_design"]["primary_factorial"]["factors"]
    primary = list(
        product(
            factors["hourly_cfe_target"],
            factors["flexible_fraction"],
            factors["normalized_recovery_headroom"],
        )
    )
    secondary = scientific["registered_design"]["secondary_oat"]
    levels = scientific["temporal_envelope"]["oat_levels"]
    oat_count = sum(
        len(
            [
                level
                for level in levels[dimension]
                if level != secondary["anchor"][dimension]
            ]
        )
        for dimension in secondary["varied_dimensions"]
    )
    if len(primary) != 36 or oat_count != 10:
        raise ValueError("scientific 46-cell inventory drifted")


def _validate_semantic_closure(config: dict[str, Any]) -> None:
    closure = _mapping(config.get("semantic_closure"), "semantic closure")
    implemented = {
        "exact_46_cell_inventory",
        "target_specific_full_cfe_deficit",
        "service_tolerance_preprocessing",
        "arm_and_track_specific_recovery",
        "shared_physical_budget",
        "B6_separate_planning_tracks",
        "global_zero_recovery_precheck",
        "network_only_alpha_invariance",
        "certified_capacity_intervals",
        "signed_interval_attribution",
        "registered_attribution_vector",
        "registered_frontier_summary",
        "solver_certificate_scalar_consistency_validation",
        "full_support_grid_excess_fallback",
        "representative_selection",
        "current_state_holdout",
        "channel_separated_shortfall",
        "E0_finite_conditioning",
        "scalar_transport_primal_dual_certificates",
        "operational_exists_metric_forall_pi_quantifier",
        "exact_PCG64DXSM_bootstrap_stream",
        "exact_bootstrap_endpoint_recomputation",
        "float_hex_certificate_serialization",
        "recursive_output_manifest",
        "atomic_result_publication",
        "caller_bound_live_provenance_validation",
        "sealed_holdout_probe_hash",
        "solver_certificate_authority_binding",
        "nested_output_internal_consistency_validation",
        "fallback_certificate_audit_closure",
        "network_alpha_certificate_identity",
        "local_runtime_dependency_closure",
        "durable_success_parent_fsync",
    }
    allowed_states = {
        "implemented",
        "implemented_by_solver_task_reuse",
        "implemented_with_explicit_execution_flag",
    }
    if set(closure) != implemented or any(
        closure.get(name) not in allowed_states for name in implemented
    ):
        raise ValueError("implemented semantic closure is incomplete")
    legacy = config.get("legacy_isolation")
    if legacy != {
        "modifies_old_sealed_implementation": False,
        "old_exclusive_classifier_used": False,
        "old_common_pi_classifier_used": False,
        "old_result_artifacts_reinterpreted": False,
    }:
        raise ValueError("legacy implementation isolation drifted")
    if config.get("predecessor_isolation") != {
        "modifies_v1_sealed_members": False,
        "rework_scope_limited_to_official_findings": True,
    }:
        raise ValueError("V1 predecessor isolation drifted")


def _validate_gates(
    config: dict[str, Any],
    *,
    require_sealed: bool,
) -> None:
    lifecycle = _mapping(config.get("lifecycle"), "lifecycle")
    gates = _mapping(config.get("gates"), "gates")
    if require_sealed:
        if lifecycle != {
            "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
            "sealed_on": "2026-09-05",
            "pre_seal_audit_complete": True,
            "sealed_ready_for_independent_review": True,
        }:
            raise ValueError("sealed lifecycle drifted")
        if gates.get("implementation_candidate_complete") is not True:
            raise ValueError("sealed implementation candidate is incomplete")
        if gates.get("pre_seal_audit_complete") is not True:
            raise ValueError("sealed pre-seal gate is incomplete")
    elif lifecycle.get("status") not in {
        "DRAFT_NONAUTHORITATIVE",
        "PRE_SEAL_AUDIT",
    }:
        raise ValueError("draft lifecycle status drifted")
    if set(gates) != {
        "implementation_candidate_complete",
        "pre_seal_audit_complete",
        "independent_R3_review_passed",
        "upstream_grid_package_ready",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
    }:
        raise ValueError("implementation gate inventory drifted")
    for key in (
        "independent_R3_review_passed",
        "upstream_grid_package_ready",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
    ):
        if gates.get(key) is not False:
            raise ValueError(f"forbidden gate opened: {key}")


def _validate_manifest() -> None:
    _require_regular_file(INNER, "implementation inner manifest")
    _require_regular_file(OUTER, "implementation outer manifest")
    inner = _load_json(INNER)
    if (
        inner.get("schema") != "rq2_joint_deliverability_implementation_inner_v2"
        or inner.get("version") != 2
        or set(inner) != {"schema", "version", "files"}
    ):
        raise ValueError("implementation inner manifest schema drifted")
    files = _mapping(inner["files"], "implementation manifest files")
    if set(files) != EXPECTED_MEMBERS:
        raise ValueError("implementation manifest inventory drifted")
    for relative, digest in files.items():
        path = ROOT / relative
        _require_regular_file(path, f"manifest member {relative}")
        if _sha256(path) != digest:
            raise ValueError(f"manifest member hash drifted: {relative}")
    outer = _load_json(OUTER)
    if outer != {
        "schema": "rq2_joint_deliverability_implementation_outer_v2",
        "version": 2,
        "inner": {
            "path": INNER_RELATIVE,
            "sha256": _sha256(INNER),
        },
    }:
        raise ValueError("implementation outer manifest drifted")


def validate(
    config: dict[str, Any],
    *,
    require_sealed: bool,
) -> dict[str, object]:
    """Validate the complete implementation candidate without runtime calls."""

    if set(config) != {
        "schema",
        "version",
        "created_on",
        "lifecycle",
        "scope",
        "scientific_config",
        "scientific_authority",
        "predecessor_authority",
        "implementation",
        "local_dependencies",
        "semantic_closure",
        "legacy_isolation",
        "predecessor_isolation",
        "capacity_stage",
        "solver_contract",
        "output_contract",
        "formal_scale",
        "validation_contract",
        "gates",
    }:
        raise ValueError("implementation top-level schema drifted")
    if (
        config["schema"] != "rq2_joint_deliverability_implementation_successor_v2"
        or config["version"] != 2
        or config["created_on"] != "2026-09-05"
        or config["scientific_config"]
        != "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
    ):
        raise ValueError("implementation identity drifted")
    _validate_authority(config)
    _validate_predecessor_authority(config)
    _validate_inventory(config)
    _validate_symbols()
    scientific_path = ROOT / str(config["scientific_config"])
    _require_regular_file(scientific_path, "scientific config")
    scientific = _load_yaml(scientific_path)
    _validate_cells(scientific)
    _validate_semantic_closure(config)
    _validate_gates(config, require_sealed=require_sealed)
    if require_sealed:
        _validate_manifest()
    capacity = _mapping(config["capacity_stage"], "capacity stage")
    if capacity != {
        "registered_cell_outputs": 46,
        "registered_arm_outputs_per_cell": 4,
        "total_arm_outputs": 184,
        "unique_network_only_solver_tasks": 19,
        "unique_other_arm_solver_tasks": 138,
        "maximum_unique_representative_solver_tasks": 157,
        "full_support_fallback_batch_size": 256,
        "conditional_full_support_fallback_solver_calls": True,
        "representative_power_blocks": 8,
        "representative_workload_blocks": 8,
        "representative_pair_count_per_cell": 64,
        "precheck_scope": "full_evaluable_training_cartesian_support",
        "full_support_capacity_increase_after_failure": False,
        "registered_input_package_counts_enforced": False,
        "cross_split_disjointness_enforced": False,
    }:
        raise ValueError("capacity-stage contract drifted")
    if config["scope"] != {
        "task_risk": "R3",
        "purpose": "v1_official_R3_review_focused_rework",
        "changes_scientific_protocol": False,
        "runs_solver_during_validation": False,
        "writes_results_during_validation": False,
        "formal_execution": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certification": False,
    }:
        raise ValueError("implementation scope drifted")
    if config["solver_contract"] != {
        "source": "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml",
        "solver_called_by_validate_only": False,
        "timeout_is_infeasible": False,
        "missing_incumbent_is_infeasible": False,
        "missing_bound_is_infeasible": False,
        "local_failure_is_infeasible": False,
    }:
        raise ValueError("implementation solver contract drifted")
    if config["output_contract"] != {
        "required_schemas": [
            "rq2_joint_deliverability_capacity_frontier_v3",
            "rq2_joint_deliverability_holdout_v3",
            "rq2_joint_deliverability_identification_v3",
            "rq2_joint_deliverability_report_v3",
        ],
        "formal_output_path": None,
        "exact_recursive_manifest_required": True,
        "atomic_publication_required": True,
        "publication_mechanics_implemented": True,
        "solver_certificate_binding_required": True,
        "nested_internal_consistency_required": True,
        "independent_solver_primal_replay": False,
        "independent_holdout_trajectory_replay": False,
        "independent_bootstrap_interval_replay": False,
        "provenance_authority_derived_internally": False,
        "path_and_activation_binding_deferred_to_execution_successor": True,
        "in_memory_reference_implementation_only": True,
        "formal_publication_allowed_by_this_candidate": False,
    }:
        raise ValueError("implementation output contract drifted")
    if config["formal_scale"] != {
        "status": "blocked_pending_streaming_execution_successor",
        "maximum_holdout_policy_executions": 3_315_680,
        "maximum_hourly_state_transitions": 79_576_320,
        "point_transport_endpoint_solves": 2_116,
        "bootstrap_transport_endpoint_solves": 423_200,
        "dense_transport_equalities_used": False,
        "holdout_trajectory_retention_default": False,
        "required_before_formal_run": [
            "streaming_holdout_persistence",
            "resumable_cell_metric_bootstrap_checkpoints",
            "bounded_memory_profile_on_registered_dimensions",
            "measured_transport_runtime_projection",
            "exact_registered_input_package_and_split_closure",
            "native_solver_evidence_and_primal_replay",
            "content_addressed_holdout_trajectory_replay",
            "bootstrap_replicate_evidence_or_independent_recompute",
            "internally_derived_provenance_authority",
            "separate_R3_execution_successor_review",
        ],
    }:
        raise ValueError("formal-scale boundary drifted")
    validation_contract = _mapping(
        config["validation_contract"],
        "validation contract",
    )
    if validation_contract != {
        "focused_test_command": (
            "python -m pytest -q "
            "tests/test_rq2_joint_deliverability_implementation_v2.py"
        ),
        "related_regression_includes": [
            "tests/test_rq2_joint_deliverability_implementation_v1.py",
            "tests/test_rq2_joint_deliverability_preregistration_v1.py",
            "tests/test_rq2_joint_deliverability_preregistration_amendment_v2.py",
            "tests/test_rq2_joint_deliverability_preregistration_successor_v3.py",
            "tests/test_rq2_joint_deliverability_preregistration_successor_v4.py",
            "tests/test_rq2_joint_deliverability_preregistration_successor_v5.py",
            "tests/test_rq2_baseline_robustness_core.py",
            "tests/test_rq2_public_replay.py",
            "tests/test_rq2_identification_bounds.py",
        ],
        "analytic_oracles": [
            "four_arm_fixed_service_minimum_capacity",
            "cfe_compatible_recovery_counterexample",
            "transport_primal_dual_witness",
            "holdout_golden_trajectory",
            "bootstrap_rng_golden_hash",
        ],
        "adversarial_cases": [
            "CFE_request_exceeds_available_flexibility",
            "subthreshold_request_equals_tolerance",
            "E0_mass_equals_one",
            "transport_interval_crosses_zero",
            "invalid_transport_dual",
            "missing_capacity_bound",
            "raw_effective_request_aliasing",
            "nontraining_E0_split_bypass",
            "full_support_status_bypass",
            "forged_solver_options",
            "nested_output_semantic_drift",
            "publication_failure_windows",
            "fallback_capacity_exceeds_representative_incumbent",
            "fallback_infeasible_forged_as_passed",
            "network_alpha_reuse_certificate_drift",
            "success_parent_fsync_failure",
            "fresh_process_local_import_closure",
        ],
        "validator_imports_or_calls_optimization_solver": False,
        "validator_writes_files": False,
    }:
        raise ValueError("validation contract drifted")
    return {
        "schema": "rq2_joint_deliverability_implementation_validation_v2",
        "valid": True,
        "lifecycle": config["lifecycle"]["status"],
        "semantic_payload_sha256": _canonical_sha256(
            {key: value for key, value in config.items() if key != "lifecycle"}
        ),
        "registered_cell_count": 46,
        "arm_output_count": 184,
        "unique_solver_task_count": 157,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-sealed", action="store_true")
    arguments = parser.parse_args()
    report = validate(
        _load_yaml(CONFIG),
        require_sealed=arguments.require_sealed,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
