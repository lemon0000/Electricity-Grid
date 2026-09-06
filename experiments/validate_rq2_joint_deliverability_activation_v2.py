"""Static validator for RQ2 joint-deliverability activation v2."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import bootstrap_rq2_joint_deliverability_activation_v2 as bootstrap

CONFIG = ROOT / bootstrap.CONFIG_RELATIVE
EXPECTED_CLOSURE_ROOTS = {
    bootstrap.BOOTSTRAP_RELATIVE,
    bootstrap.CONTROLLER_RELATIVE,
    bootstrap.EXECUTION_CORE_RELATIVE,
    "experiments/run_rq2_joint_deliverability_implementation_v2.py",
}
FORBIDDEN_TOP_LEVEL_IMPORT_PREFIXES = (
    "experiments",
    "src",
    "numpy",
    "pyomo",
    "yaml",
)
EXPECTED_BUNDLE_MEMBERS = {
    "configs/rq2_joint_deliverability_activation_review_rework_v1.json",
    "configs/rq2_joint_deliverability_activation_successor_v1.OUTER.SHA256SUMS.json",
    "configs/rq2_joint_deliverability_activation_successor_v2.json",
    "configs/rq2_joint_deliverability_execution_review_pass_v3.yaml",
    "configs/rq2_joint_deliverability_execution_successor_v1.OUTER.SHA256SUMS.json",
    "configs/rq2_joint_deliverability_execution_successor_v2.OUTER.SHA256SUMS.json",
    "configs/rq2_joint_deliverability_execution_successor_v3.OUTER.SHA256SUMS.json",
    "docs/model_spec/rq2_joint_deliverability_activation_v2.md",
    "environments/rq2_executor_v2.yml",
    "experiments/__init__.py",
    "experiments/bootstrap_rq2_joint_deliverability_activation_v2.py",
    "experiments/run_rq2_joint_deliverability_activation_v2.py",
    "experiments/run_rq2_joint_deliverability_implementation_v2.py",
    "experiments/validate_rq2_joint_deliverability_activation_v2.py",
    "experiments/validate_rq2_joint_deliverability_implementation_v2.py",
    "src/__init__.py",
    "src/rq2_joint_deliverability_execution_v3/__init__.py",
    "src/rq2_joint_deliverability_execution_v3/core.py",
    "src/rq2_joint_deliverability_v2/__init__.py",
    "src/rq2_joint_deliverability_v2/evaluation.py",
    "src/rq2_joint_deliverability_v2/model.py",
    "src/rq2_joint_deliverability_v2/scenarios.py",
    "src/rq2_joint_deliverability_v2/solver_adapter.py",
    "tests/test_rq2_joint_deliverability_activation_v2.py",
}


def _module_path(name: str) -> Path | None:
    path = ROOT.joinpath(*name.split("."))
    source = path.with_suffix(".py")
    if source.is_file():
        return source
    package = path / "__init__.py"
    return package if package.is_file() else None


def _package_name(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    parts = list(relative.parts)
    if path.name == "__init__.py":
        parts = parts[:-1]
    else:
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_from(
    node: ast.ImportFrom,
    *,
    source: Path,
) -> list[str]:
    base = node.module or ""
    if node.level:
        package_parts = _package_name(source).split(".")
        keep = len(package_parts) - node.level + 1
        prefix = package_parts[: max(keep, 0)]
        if base:
            prefix.extend(base.split("."))
        base = ".".join(prefix)
    names = [base] if base else []
    for alias in node.names:
        if alias.name != "*":
            names.append(f"{base}.{alias.name}" if base else alias.name)
    return names


def discover_local_python_closure(roots: set[str]) -> set[str]:
    queue = [ROOT / relative for relative in sorted(roots, key=str.encode)]
    seen: set[Path] = set()
    while queue:
        source = queue.pop(0).resolve()
        if source in seen:
            continue
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"closure source is not an ordinary file: {source}")
        seen.add(source)
        relative = source.relative_to(ROOT)
        for index in range(1, len(relative.parts)):
            package_init = ROOT.joinpath(*relative.parts[:index], "__init__.py")
            if package_init.is_file() and package_init.resolve() not in seen:
                queue.append(package_init)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = _resolve_from(node, source=source)
            for name in names:
                if name in {"src", "experiments"} or name.startswith(
                    ("src.", "experiments.")
                ):
                    target = _module_path(name)
                else:
                    target = None
                if target is not None and target.resolve() not in seen:
                    queue.append(target)
    return {path.relative_to(ROOT).as_posix() for path in seen}


def _validate_stdlib_first_bootstrap() -> None:
    source = ROOT / bootstrap.BOOTSTRAP_RELATIVE
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        if any(
            name == prefix or name.startswith(f"{prefix}.")
            for name in names
            for prefix in FORBIDDEN_TOP_LEVEL_IMPORT_PREFIXES
        ):
            raise ValueError(
                f"bootstrap has a project/science top-level import: {names}"
            )


def _load() -> dict[str, object]:
    config, _raw = bootstrap._load_config()
    return config


def _closed_external_authorities(config: Mapping[str, object]) -> None:
    authorities = bootstrap._mapping(
        config.get("external_authorities"),
        "external authorities",
    )
    if set(authorities) != {
        "activation_review",
        "dispatched_grid_manifest",
        "runtime",
        "execution_activation",
        "formal_run",
    }:
        raise ValueError("external authority inventory drifted")
    for name, raw in authorities.items():
        item = bootstrap._mapping(raw, f"{name} authority")
        if name == "activation_review":
            if item != bootstrap._expected_activation_review_contract():
                raise ValueError("activation_review authority contract drifted")
        elif (
            set(item) != {"path", "schema", "present"}
            or item.get("present") is not False
        ):
            raise ValueError(f"{name} authority contract drifted")
        path = ROOT / bootstrap._relative(item.get("path"), f"{name} path")
        if name == "activation_review":
            if bootstrap._path_is_present_or_aliased(path):
                bootstrap._require_activation_review(config)
            continue
        if bootstrap._path_is_present_or_aliased(path):
            raise ValueError(f"closed external authority unexpectedly exists: {name}")


def _validate_contract(config: Mapping[str, object]) -> None:
    if set(config) != {
        "schema",
        "version",
        "created_on",
        "lifecycle",
        "scope",
        "predecessor_activation",
        "execution_authority",
        "python_closure",
        "external_authorities",
        "stage_contract",
        "side_effect_order",
        "formal_roots",
        "validation_contract",
        "bundle",
        "gates",
    }:
        raise ValueError("activation top-level schema drifted")
    if (
        config.get("schema") != "rq2_joint_deliverability_activation_successor_v2"
        or config.get("version") != 2
        or config.get("created_on") != "2026-09-06"
    ):
        raise ValueError("activation identity drifted")
    scope = bootstrap._mapping(config.get("scope"), "activation scope")
    if scope != {
        "purpose": "fresh_process_activation_boundary_for_sealed_execution_v3",
        "scientific_protocol_changed": False,
        "solver_semantics_changed": False,
        "evidence_schema_changed": False,
        "formal_run_authorized_by_this_candidate": False,
        "runs_solver_during_validation": False,
        "writes_formal_results_during_validation": False,
    }:
        raise ValueError("activation scope drifted")
    stages = bootstrap._mapping(config.get("stage_contract"), "stage contract")
    if stages != {
        "write_capable_stage_surface": "absent",
        "execution_v3_private_helper_bypass_allowed": False,
        "execution_v3_null_authority_override_allowed": False,
        "future_bound_execution_successor_required": True,
        "future_formal_run_authority_required": True,
    }:
        raise ValueError("activation stage contract drifted")
    validation = bootstrap._mapping(
        config.get("validation_contract"),
        "validation contract",
    )
    if validation != {
        "fresh_process_probe_required": True,
        "fresh_process_probe_is_nonformal": True,
        "fresh_process_timeout_seconds": 60,
        "fresh_process_BaseException_cleanup_required": True,
        "parent_snapshot_envelope_required": True,
        "parent_post_probe_revalidation_required": True,
        "child_exact_inventory_required": True,
        "artifact_reads_descriptor_anchored": True,
        "windows_relative_handle_traversal_required": True,
        "ancestor_swap_fault_test_required": True,
        "solver_calls": 0,
        "formal_result_files_written": 0,
        "authority_presence_checked_with_anchored_traversal": True,
        "authority_presence_double_snapshot_required": True,
        "anchored_handle_cleanup_required": True,
        "close_failure_recovery_required": True,
        "single_field_fault_tests_required": True,
        "receipt_presence_must_not_change_validation_pass": True,
    }:
        raise ValueError("activation validation contract drifted")
    gates = bootstrap._mapping(config.get("gates"), "activation gates")
    false_gates = {
        "independent_activation_R3_review_passed",
        "dispatched_grid_package_ready",
        "execution_machine_runtime_ready",
        "native_solver_replay_passed",
        "registered_memory_profile_passed",
        "transport_runtime_projection_accepted",
        "execution_activation_authority_present",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
        "security_certified",
    }
    if any(gates.get(name) is not False for name in false_gates):
        raise ValueError("activation runtime or formal gate opened")
    if gates.get("activation_candidate_complete") not in {False, True}:
        raise ValueError("activation candidate completion gate malformed")
    if gates.get("pre_seal_audit_complete") not in {False, True}:
        raise ValueError("activation pre-seal gate malformed")


def validate(
    config: Mapping[str, object] | None = None,
    *,
    require_sealed: bool = False,
) -> dict[str, object]:
    value = dict(_load() if config is None else config)
    _validate_contract(value)
    lifecycle = bootstrap._mapping(value.get("lifecycle"), "activation lifecycle")
    if require_sealed and lifecycle.get("status") != (
        "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    ):
        raise ValueError("sealed activation lifecycle is required")
    bundle = bootstrap._verify_bundle(value, require_sealed=require_sealed)
    bundle_contract = bootstrap._mapping(value.get("bundle"), "activation bundle")
    if set(bundle_contract.get("members", [])) != EXPECTED_BUNDLE_MEMBERS:
        raise ValueError("activation bundle member inventory drifted")
    predecessor = bootstrap._verify_predecessor_activation(value)
    execution = bootstrap._verify_execution_authority(value)
    closure = bootstrap._verify_python_closure(value)
    discovered = discover_local_python_closure(EXPECTED_CLOSURE_ROOTS)
    if set(closure) != discovered:
        raise ValueError(
            "Python closure inventory drifted: "
            f"missing={sorted(discovered - set(closure))}, "
            f"extra={sorted(set(closure) - discovered)}"
        )
    _validate_stdlib_first_bootstrap()
    _closed_external_authorities(value)
    return {
        "schema": "rq2_joint_deliverability_activation_static_validation_v2",
        "lifecycle": lifecycle["status"],
        "bundle_member_count": bundle["member_count"],
        "python_closure_member_count": len(closure),
        **predecessor,
        **execution,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-sealed", action="store_true")
    arguments = parser.parse_args(argv)
    print(
        json.dumps(
            validate(require_sealed=arguments.require_sealed),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
