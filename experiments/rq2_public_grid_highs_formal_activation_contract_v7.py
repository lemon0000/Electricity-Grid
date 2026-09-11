"""V7 lifecycle and production-authority contract.

Before sealing, the module selects only the non-authoritative draft artifacts.
After an atomic seal, fresh processes select and strictly verify the canonical
artifacts before any independent-review or execution gate can open.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from experiments import bootstrap_rq2_joint_deliverability_activation_v3 as anchored_v3
from experiments import rq2_public_grid_highs_formal_activation_contract_v4 as v4

ROOT = Path(__file__).resolve().parents[1]
DRAFT_CONFIG = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_v7.DRAFT.json"
)
SEALED_CONFIG = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_v7.json"
)
DRAFT_FORMAL_CONFIG = (
    ROOT
    / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v8.DRAFT.yaml"
)
SEALED_FORMAL_CONFIG = (
    ROOT
    / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v8.yaml"
)
CONFIG = SEALED_CONFIG if os.path.lexists(SEALED_CONFIG) else DRAFT_CONFIG
FORMAL_CONFIG = (
    SEALED_FORMAL_CONFIG
    if os.path.lexists(SEALED_FORMAL_CONFIG)
    else DRAFT_FORMAL_CONFIG
)
PREDECESSOR_OUTER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v4.OUTER.SHA256SUMS.json"
)
PREDECESSOR_CLOSURE = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v4.EXECUTION_CLOSURE.SHA256SUMS.json"
)
PREDECESSOR_ESCALATE = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v4.json"
)
SEALED_PREDECESSOR_OUTER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v6.OUTER.SHA256SUMS.json"
)
SEALED_PREDECESSOR_CLOSURE = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v6.EXECUTION_CLOSURE.SHA256SUMS.json"
)
SEALED_PREDECESSOR_FORMAL_CONFIG = (
    ROOT
    / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v7.yaml"
)
SEALED_PREDECESSOR_ESCALATE = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v6.json"
)
DRAFT_PRE_SEAL_AUDIT = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v7.PRE_SEAL_AUDIT_DRAFT.json"
)
SEALED_PRE_SEAL_AUDIT = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v7.PRE_SEAL_AUDIT.json"
)
PRE_SEAL_AUDIT = (
    SEALED_PRE_SEAL_AUDIT
    if os.path.lexists(SEALED_PRE_SEAL_AUDIT)
    else DRAFT_PRE_SEAL_AUDIT
)
PRE_SEAL_AUDIT_DRAFT = DRAFT_PRE_SEAL_AUDIT
GIB = 1024**3
PREFLIGHT_THRESHOLD_BYTES = 10 * GIB
CHILD_PRIVATE_COMMIT_STOP_BYTES = 8 * GIB
SYSTEM_COMMIT_AVAILABLE_STOP_BYTES = 2 * GIB
DYNAMIC_EXECUTION_MODULES = {
    "experiments.run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1",
    "src.grid.rts_gmlc",
}

FormalActivationRejected = v4.FormalActivationRejected
sha256_file = v4.sha256_file
canonical_bytes = v4.canonical_bytes
canonical_sha256 = v4.canonical_sha256
_is_sha256 = v4._is_sha256
_mapping = v4._mapping
_repo_path = v4._repo_path
_load_json = v4._load_json
_load_yaml = v4._load_yaml
_atomic_write = v4._atomic_write
_read_stable = v4._read_stable
persist_json_stable = v4.persist_json_stable
persist_json_exclusive_stable = v4.persist_json_exclusive_stable
_process_identity = v4._process_identity
STARTUP_BINDING_NAMES = v4.STARTUP_BINDING_NAMES
build_startup_handshake = v4.build_startup_handshake
validate_startup_handshake = v4.validate_startup_handshake
build_startup_ack = v4.build_startup_ack
validate_startup_ack = v4.validate_startup_ack
build_startup_ready = v4.build_startup_ready
validate_startup_ready = v4.validate_startup_ready
build_science_release = v4.build_science_release
validate_science_release = v4.validate_science_release
build_science_release_acceptance = v4.build_science_release_acceptance
validate_science_release_acceptance = v4.validate_science_release_acceptance

PREDECESSOR_OUTER_SHA256 = (
    "6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068"
)
PREDECESSOR_CLOSURE_SHA256 = (
    "ba9195283cf3ad149e08c875820198648d0a9c0cf6b99ac7e3c37b212683b948"
)
PREDECESSOR_ESCALATE_SHA256 = (
    "1d4f5f1b65512a0092438051055171c5abf4dbbe2aa358675c5f580636bc4e9c"
)
SEALED_PREDECESSOR_OUTER_SHA256 = (
    "12a00b1c4a75943c81e712bc02f53ed38d67a6749e440c1103294a3c568937aa"
)
SEALED_PREDECESSOR_CLOSURE_SHA256 = (
    "535bb0eba4c36b58efd45711f1e9fffbcaf65f703754517896fd67c7b0c3c0e4"
)
SEALED_PREDECESSOR_FORMAL_CONFIG_SHA256 = (
    "2128a11ebca54396dd7927afcd9496de10013fbb00142a12fa5df26d4543a05c"
)
SEALED_PREDECESSOR_ESCALATE_SHA256 = (
    "ee41fe26122862650fd492fe54aa950936f8cb38da21991b063130a771f6a2aa"
)
EXPECTED_RUNTIME_FILES = {
    "locked_python": {
        "path": r"D:\conda_envs\rq2-executor-v2-audit\python.exe",
        "sha256": "91df9733b71b293eec9945cc8c5388bbfe1abc5e6ee94a14333076e5f55cb6bf",
    },
    "highspy_package_init": {
        "path": r"D:\conda_envs\rq2-executor-v2-audit\Lib\site-packages\highspy\__init__.py",
        "sha256": "152eab96c80668ff98d8447bdca93d1bd6253aebaf1df3e455872a05e7dbd0c2",
    },
    "highspy_python_source": {
        "path": r"D:\conda_envs\rq2-executor-v2-audit\Lib\site-packages\highspy\highs.py",
        "sha256": "5310ab9947289b49de9e8f650bec7aa24e058cdfcd45bdc57fdf80e0fb5a270a",
    },
    "highspy_binary": {
        "path": r"D:\conda_envs\rq2-executor-v2-audit\Lib\site-packages\highspy\_core.cp311-win_amd64.pyd",
        "sha256": "b44417e1cae9c30e5fce3e38535c2970e25d6367a07a1e5ff8e94d623c22aa29",
    },
}
RUNTIME_FILE_KEYS = {
    "locked_python": ("locked_python_executable", "locked_python_sha256"),
    "highspy_package_init": (
        "highspy_package_init_path",
        "highspy_package_init_sha256",
    ),
    "highspy_python_source": (
        "highspy_python_source_path",
        "highspy_python_source_sha256",
    ),
    "highspy_binary": ("highspy_binary_path", "highspy_binary_sha256"),
}


def _validate_runtime_config(config: Mapping[str, Any]) -> None:
    runtime = _mapping(config.get("runtime"), "runtime")
    expected_keys = {
        "locked_python_executable",
        "locked_python_sha256",
        "highspy_package_init_path",
        "highspy_package_init_sha256",
        "highspy_python_source_path",
        "highspy_python_source_sha256",
        "highspy_binary_path",
        "highspy_binary_sha256",
        "formal_controller_module",
        "exact_cwd",
        "controller_command_prefix",
        "sanitized_environment",
    }
    expected_prefix = [
        EXPECTED_RUNTIME_FILES["locked_python"]["path"],
        "-B",
        "-m",
        "experiments.run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v8",
        "--config",
        FORMAL_CONFIG.relative_to(ROOT).as_posix(),
        "--activation-authority",
    ]
    if (
        set(runtime) != expected_keys
        or any(
            runtime.get(RUNTIME_FILE_KEYS[name][0]) != binding["path"]
            or runtime.get(RUNTIME_FILE_KEYS[name][1]) != binding["sha256"]
            for name, binding in EXPECTED_RUNTIME_FILES.items()
        )
        or runtime.get("formal_controller_module") != expected_prefix[3]
        or runtime.get("exact_cwd") != str(ROOT)
        or runtime.get("controller_command_prefix") != expected_prefix
        or not isinstance(runtime.get("sanitized_environment"), Mapping)
    ):
        raise FormalActivationRejected("V7 runtime authority drifted")


def validate_runtime_files(config: Mapping[str, Any] | None = None) -> None:
    value = dict(config) if config is not None else load_config()
    _validate_runtime_config(value)
    runtime = _mapping(value["runtime"], "runtime")
    for name in EXPECTED_RUNTIME_FILES:
        path_key, sha256_key = RUNTIME_FILE_KEYS[name]
        path = Path(str(runtime[path_key]))
        raw, _ = _ordinary_stable_bytes(path, f"runtime file {name}")
        if hashlib.sha256(raw).hexdigest() != runtime[sha256_key]:
            raise FormalActivationRejected(f"runtime file drifted: {name}")


def load_config() -> dict[str, Any]:
    config = _ordinary_stable_json(CONFIG, "V7 activation config")
    production = _mapping(config.get("production_artifacts"), "production artifacts")
    sealed_predecessor = _mapping(
        config.get("sealed_predecessor_v6"), "sealed V6 predecessor"
    )
    gates = _mapping(config.get("gates"), "activation gates")
    draft = config.get("status") == "DRAFT_NONAUTHORITATIVE"
    expected_gates = (
        {
            "draft_non_authoritative": True,
            "pre_seal_audit_complete": False,
            "sealed_ready_for_independent_review": False,
            "independent_formal_activation_review_passed": False,
            "user_formal_run_authorized": False,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
        if draft
        else {
            "draft_non_authoritative": False,
            "pre_seal_audit_complete": True,
            "sealed_ready_for_independent_review": True,
            "independent_formal_activation_review_passed": False,
            "user_formal_run_authorized": False,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
    )
    expected_production_keys = {
        "inner_manifest",
        "outer_manifest",
        "execution_closure",
        "one_shot_lease",
        "activation_review_receipt",
        "user_formal_run_authority",
    }
    if (
        config.get("version") != 7
        or sealed_predecessor
        != {
            "outer_path": SEALED_PREDECESSOR_OUTER.relative_to(ROOT).as_posix(),
            "outer_sha256": SEALED_PREDECESSOR_OUTER_SHA256,
            "execution_closure_path": SEALED_PREDECESSOR_CLOSURE.relative_to(
                ROOT
            ).as_posix(),
            "execution_closure_sha256": SEALED_PREDECESSOR_CLOSURE_SHA256,
            "formal_config_path": SEALED_PREDECESSOR_FORMAL_CONFIG.relative_to(
                ROOT
            ).as_posix(),
            "formal_config_sha256": SEALED_PREDECESSOR_FORMAL_CONFIG_SHA256,
            "escalate_receipt_path": SEALED_PREDECESSOR_ESCALATE.relative_to(
                ROOT
            ).as_posix(),
            "escalate_receipt_sha256": SEALED_PREDECESSOR_ESCALATE_SHA256,
            "supersession_reason": "official_rework_successor_lifecycle_escalation",
            "changes_scientific_protocol": False,
        }
        or set(production) != expected_production_keys
        or gates != expected_gates
        or (
            draft
            and (
                CONFIG != DRAFT_CONFIG
                or config.get("schema")
                != "rq2_public_grid_highs_formal_activation_successor_v7_draft"
                or config.get("authority_effect") != "none"
                or any(value is not None for value in production.values())
            )
        )
        or (
            not draft
            and (
                CONFIG != SEALED_CONFIG
                or config.get("schema")
                != "rq2_public_grid_highs_formal_activation_successor_v7"
                or config.get("status") != "SEALED_READY_FOR_INDEPENDENT_REVIEW"
                or config.get("authority_effect")
                != "independent_review_only_no_execution"
                or any(
                    not isinstance(production.get(name), str)
                    for name in expected_production_keys - {"one_shot_lease"}
                )
                or not isinstance(production.get("one_shot_lease"), Mapping)
            )
        )
    ):
        raise FormalActivationRejected("V7 draft identity or fail-closed gates drifted")
    _validate_runtime_config(config)
    return config


def production_artifact_paths() -> list[Path]:
    production = _mapping(load_config()["production_artifacts"], "production artifacts")
    paths = [
        _repo_path(value, f"production artifact {name}")
        for name, value in production.items()
        if name != "one_shot_lease" and value is not None
    ]
    if production.get("one_shot_lease") is not None:
        lease = _production_one_shot()
        paths.extend(
            _repo_path(lease[name], f"production one-shot {name}")
            for name in ("fresh_path", "consumed_path")
        )
    return paths


def validate_formal_config() -> dict[str, Any]:
    formal = _load_yaml(FORMAL_CONFIG, "V7 formal science config")
    predecessor = _load_yaml(
        SEALED_PREDECESSOR_FORMAL_CONFIG, "V6 predecessor formal science config"
    )
    draft = formal.get("status") == "DRAFT_NONAUTHORITATIVE_NOT_EXECUTABLE"
    lifecycle_name = "draft_lifecycle" if draft else "activation_lifecycle"
    lifecycle = _mapping(formal.get(lifecycle_name), "activation lifecycle")
    execution = _mapping(formal.get("execution"), "formal execution")
    process = _mapping(execution.get("process_isolation"), "process isolation")
    solver = _mapping(formal.get("solver"), "solver")
    expected_lifecycle = {
        "authority_effect": (
            "none" if draft else "independent_review_only_no_execution"
        ),
        "predecessor_config_path": SEALED_PREDECESSOR_FORMAL_CONFIG.relative_to(
            ROOT
        ).as_posix(),
        "predecessor_config_sha256": SEALED_PREDECESSOR_FORMAL_CONFIG_SHA256,
        "changes_scientific_protocol": False,
        "pre_seal_audit_complete": not draft,
        "sealed_ready_for_independent_review": not draft,
    }
    if (
        formal.get("schema")
        != (
            "rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v8_draft"
            if draft
            else "rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v8"
        )
        or formal.get("version") != 8
        or formal.get("status")
        != (
            "DRAFT_NONAUTHORITATIVE_NOT_EXECUTABLE"
            if draft
            else "SEALED_READY_FOR_INDEPENDENT_REVIEW"
        )
        or lifecycle != expected_lifecycle
        or set(formal).intersection({"draft_lifecycle", "activation_lifecycle"})
        != {lifecycle_name}
        or any(
            formal.get(key) != predecessor.get(key)
            for key in ("input", "grid_source", "model", "solver", "provenance")
        )
        or solver.get("name") != "highs"
        or solver.get("expected_package_version") != "1.15.1"
        or solver.get("threads") != 4
        or execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not False
        or execution.get("starts_from_block_zero") is not True
        or execution.get("resume_allowed") is not False
        or execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is not False
        or execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
        or process.get("mode") != "one_fresh_python_worker_per_complete_24h_block"
        or process.get("expected_block_count") != 1071
        or process.get("resource_sample_interval_seconds") != 5.0
        or process.get("observation_jitter_budget_seconds") != 1.0
        or process.get("maximum_detection_overrun_seconds") != 1.0
        or process.get("owned_termination_grace_seconds") != 2.0
        or process.get("private_commit_limit_gib") != 8.0
        or process.get("minimum_system_commit_available_gib") != 2.0
        or process.get("external_watchdog_seconds") != 21600
        or process.get("timeout_or_failure_is_mathematical_infeasibility") is not False
        or formal.get("claims") != predecessor.get("claims")
    ):
        raise FormalActivationRejected("V7 draft formal science contract drifted")
    return formal


def formal_roots() -> dict[str, Path]:
    paths = _mapping(load_config()["planned_paths"], "planned formal paths")
    return {
        name: _repo_path(paths[key], key)
        for name, key in (
            ("checkpoint", "checkpoint_root"),
            ("worker", "worker_root"),
            ("log", "log_root"),
            ("output", "output_root"),
        )
    }


def activation_audit_root() -> Path:
    return _repo_path(
        load_config()["planned_paths"]["activation_audit_root"],
        "activation audit root",
    )


def _module_file(module: str) -> Path | None:
    base = ROOT.joinpath(*module.split("."))
    candidates = (base.with_suffix(".py"), base / "__init__.py")
    return next((path.resolve() for path in candidates if path.is_file()), None)


def _module_name(path: Path) -> str:
    relative = path.resolve().relative_to(ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _package_initializers(path: Path) -> set[Path]:
    initializers: set[Path] = set()
    parent = path.resolve().parent
    while parent != ROOT and parent.is_relative_to(ROOT):
        initializer = parent / "__init__.py"
        if initializer.is_file():
            initializers.add(initializer.resolve())
        parent = parent.parent
    return initializers


def _local_imports(path: Path) -> set[Path]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    current = _module_name(path)
    package = current if path.name == "__init__.py" else current.rpartition(".")[0]
    found: set[Path] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".") if package else []
                keep = max(0, len(parts) - node.level + 1)
                prefix = ".".join(parts[:keep])
            else:
                prefix = ""
            base = ".".join(part for part in (prefix, node.module or "") if part)
            if base:
                names.append(base)
            names.extend(
                ".".join(part for part in (base, alias.name) if part)
                for alias in node.names
                if alias.name != "*"
            )
        for name in names:
            candidate = _module_file(name)
            if candidate is not None:
                found.add(candidate)
                found.update(_package_initializers(candidate))
    return found


def derive_execution_closure_members() -> dict[str, str]:
    """Derive the selected V7 lifecycle closure without consulting V4's closure."""
    pending = [
        Path(__file__).resolve(),
        ROOT
        / "experiments/bootstrap_rq2_public_grid_highs_formal_activation_successor_v7.py",
        ROOT
        / "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v8.py",
    ]
    pending.extend(
        path
        for module in sorted(DYNAMIC_EXECUTION_MODULES)
        if (path := _module_file(module)) is not None
    )
    visited: set[Path] = set()
    while pending:
        path = pending.pop().resolve()
        if path in visited:
            continue
        if not path.is_relative_to(ROOT) or not path.is_file() or path.is_symlink():
            raise FormalActivationRejected(f"closure member is not ordinary: {path}")
        visited.add(path)
        pending.extend(_package_initializers(path) - visited)
        if path.suffix == ".py":
            pending.extend(_local_imports(path) - visited)
    visited.update({CONFIG.resolve(), FORMAL_CONFIG.resolve()})
    return {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in sorted(visited, key=lambda item: item.as_posix())
    }


def _closure_payload() -> dict[str, Any]:
    members = derive_execution_closure_members()
    return {
        "schema": "rq2_public_grid_highs_formal_activation_v7_preseal_execution_closure",
        "version": 7,
        "status": "NONAUTHORITATIVE_PRE_SEAL_ONLY",
        "member_count": len(members),
        "members": members,
        "members_sha256": canonical_sha256(members),
        "hash_authority": "derived_current",
        "derived_current_hashes_verified": True,
        "expected_hashes_verified": False,
        "formal_execution_authorized": False,
        "claim": False,
        "security_certified": False,
    }


def persist_preseal_execution_closure(path: Path) -> dict[str, Any]:
    if path.exists():
        raise FormalActivationRejected("pre-seal closure path must not preexist")
    payload = _closure_payload()
    persist_json_stable(path, payload)
    return payload


def _validate_frozen_execution_closure(path: Path) -> dict[str, Any]:
    observed = _ordinary_stable_json(path, "V7 frozen execution closure")
    members = derive_execution_closure_members()
    expected_keys = {
        "schema",
        "version",
        "status",
        "member_count",
        "members",
        "members_sha256",
        "hash_authority",
        "derived_current_hashes_verified",
        "expected_hashes_verified",
        "formal_execution_authorized",
        "claim",
        "security_certified",
    }
    if (
        set(observed) != expected_keys
        or observed.get("schema")
        != "rq2_public_grid_highs_formal_activation_v7_execution_closure"
        or observed.get("version") != 7
        or observed.get("status") != "FROZEN_EXPECTED"
        or observed.get("member_count") != len(members)
        or observed.get("members") != members
        or observed.get("members_sha256") != canonical_sha256(members)
        or observed.get("hash_authority") != "frozen_expected"
        or observed.get("derived_current_hashes_verified") is not True
        or observed.get("expected_hashes_verified") is not True
        or observed.get("formal_execution_authorized") is not False
        or observed.get("claim") is not False
        or observed.get("security_certified") is not False
    ):
        raise FormalActivationRejected("V7 frozen execution closure drifted")
    return observed


def verify_execution_closure(
    *, require_frozen_expected: bool = False
) -> dict[str, Any]:
    derived = _closure_payload()
    configured = os.environ.get("RQ2_V7_PRESEAL_CLOSURE")
    if configured is not None:
        if require_frozen_expected:
            raise FormalActivationRejected(
                "tmp pre-seal closure is not frozen expected authority"
            )
        path = Path(configured).resolve()
        observed = _ordinary_stable_json(path, "V7 pre-seal execution closure")
        if observed != derived:
            raise FormalActivationRejected("V7 pre-seal execution closure drifted")
        return observed
    raw = load_config()["production_artifacts"].get("execution_closure")
    if raw is not None:
        return _validate_frozen_execution_closure(
            _repo_path(raw, "production execution closure")
        )
    if require_frozen_expected:
        raise FormalActivationRejected("frozen expected execution closure is absent")
    return derived


def _canonical_path(path: Path) -> Path:
    return path.resolve()


def startup_paths(attempt_root: Path) -> dict[str, str]:
    names = _mapping(load_config()["startup_handshake"], "startup handshake")
    return {
        key: str((attempt_root / str(names[field])).resolve())
        for key, field in (
            ("handshake", "handshake_filename"),
            ("bootstrap_ack", "bootstrap_ack_filename"),
            ("startup_ready", "startup_ready_filename"),
            ("science_release", "science_release_filename"),
            ("science_release_accepted", "science_release_accepted_filename"),
            ("launch_incomplete", "launch_incomplete_filename"),
            ("terminal_outcome", "authoritative_terminal_outcome_filename"),
            ("controller_cancellation", "controller_cancellation_filename"),
            (
                "controller_cancellation_ack",
                "controller_cancellation_ack_filename",
            ),
            ("spawn_receipt", "spawn_receipt_filename"),
            ("lifecycle_decision", "lifecycle_decision_filename"),
            (
                "deferred_supervisor_interruption",
                "deferred_supervisor_interruption_filename",
            ),
        )
    }


def exact_controller_environment(closure_path: Path | None = None) -> dict[str, str]:
    environment = {
        str(key): str(value)
        for key, value in load_config()["runtime"]["sanitized_environment"].items()
    }
    if closure_path is not None:
        environment["RQ2_V7_PRESEAL_CLOSURE"] = str(closure_path.resolve())
    return environment


def exact_controller_command(
    authority_path: Path,
    *,
    bootstrap_identity: Mapping[str, int],
    preseal_probe: bool | None = None,
    fault_phase: str | None = None,
    fault_type: str | None = None,
) -> list[str]:
    authority_path = authority_path.resolve()
    if preseal_probe is None and authority_path.is_file():
        dynamic = _load_json(authority_path, "dynamic activation authority")
        preseal_probe = dynamic.get("preseal_startup_probe") is True
        fault_phase = dynamic.get("fault_phase")
        fault_type = dynamic.get("fault_type")
    identity = _process_identity(bootstrap_identity, "bootstrap identity")
    paths = startup_paths(authority_path.parent)
    command = [
        *list(load_config()["runtime"]["controller_command_prefix"]),
        str(authority_path),
        "--bootstrap-pid",
        str(identity["pid"]),
        "--bootstrap-create-time-ns",
        str(identity["create_time_ns"]),
        "--startup-handshake",
        paths["handshake"],
        "--startup-ack",
        paths["bootstrap_ack"],
        "--startup-ready",
        paths["startup_ready"],
        "--science-release",
        paths["science_release"],
        "--science-release-accepted",
        paths["science_release_accepted"],
    ]
    if preseal_probe:
        command.append("--preseal-startup-probe")
    if fault_phase is not None:
        command.extend(("--fault-phase", fault_phase))
    if fault_type is not None:
        command.extend(("--fault-type", fault_type))
    return command


def ensure_formal_roots_absent(
    roots_override: Mapping[str, Path] | None = None,
) -> None:
    roots = dict(roots_override if roots_override is not None else formal_roots())
    existing = [name for name, path in roots.items() if path.exists()]
    if existing:
        raise FormalActivationRejected(
            "formal roots must not preexist: " + ", ".join(sorted(existing))
        )


def _production_artifact_path(name: str) -> Path:
    production = _mapping(load_config()["production_artifacts"], "production artifacts")
    raw = production.get(name)
    if not isinstance(raw, str):
        raise FormalActivationRejected(f"production artifact is absent: {name}")
    return _repo_path(raw, f"production artifact {name}")


def _production_one_shot() -> dict[str, Any]:
    production = _mapping(load_config()["production_artifacts"], "production artifacts")
    lease = _mapping(production.get("one_shot_lease"), "production one-shot lease")
    expected = {
        "fresh_path",
        "fresh_sha256",
        "consumed_path",
        "authority_id",
        "one_shot",
    }
    if (
        set(lease) != expected
        or not _is_sha256(lease.get("fresh_sha256"))
        or not _is_sha256(lease.get("authority_id"))
        or lease.get("one_shot") is not True
    ):
        raise FormalActivationRejected("production one-shot lease binding drifted")
    _repo_path(lease["fresh_path"], "fresh one-shot authority")
    _repo_path(lease["consumed_path"], "consumed one-shot authority")
    return lease


def _entry_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _validated_frozen_closure_snapshot(
    validated_closure: Mapping[str, Any],
) -> dict[str, Any]:
    closure = dict(validated_closure)
    path = _production_artifact_path("execution_closure")
    if (
        closure.get("schema")
        != "rq2_public_grid_highs_formal_activation_v7_execution_closure"
        or closure.get("version") != 7
        or closure.get("status") != "FROZEN_EXPECTED"
        or closure.get("hash_authority") != "frozen_expected"
        or closure.get("derived_current_hashes_verified") is not True
        or closure.get("expected_hashes_verified") is not True
        or _ordinary_stable_json(path, "validated frozen execution closure snapshot")
        != closure
    ):
        raise FormalActivationRejected("validated frozen closure snapshot drifted")
    return closure


def _expected_inner_member_paths(lease: Mapping[str, Any]) -> set[str]:
    return {
        PREDECESSOR_OUTER.relative_to(ROOT).as_posix(),
        PREDECESSOR_CLOSURE.relative_to(ROOT).as_posix(),
        PREDECESSOR_ESCALATE.relative_to(ROOT).as_posix(),
        SEALED_PREDECESSOR_OUTER.relative_to(ROOT).as_posix(),
        SEALED_PREDECESSOR_CLOSURE.relative_to(ROOT).as_posix(),
        SEALED_PREDECESSOR_ESCALATE.relative_to(ROOT).as_posix(),
        (
            "configs/rq2_public_grid_two_block_pilot_vnext_execution_"
            "successor_post_result_review_pass_v8.json"
        ),
        CONFIG.relative_to(ROOT).as_posix(),
        FORMAL_CONFIG.relative_to(ROOT).as_posix(),
        _production_artifact_path("execution_closure").relative_to(ROOT).as_posix(),
        (
            "configs/rq2_public_grid_highs_formal_activation_successor_"
            "v7.PRE_SEAL_AUDIT.json"
        ),
        "experiments/bootstrap_rq2_public_grid_highs_formal_activation_successor_v7.py",
        "experiments/rq2_public_grid_highs_formal_activation_contract_v7.py",
        (
            "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_"
            "process_isolated_formal_v8.py"
        ),
        "tests/test_rq2_public_grid_highs_formal_activation_successor_v7.py",
        str(lease["fresh_path"]),
    }


def _verify_sealed_bundle(
    *, validated_closure: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    config = load_config()
    if config.get("status") != "SEALED_READY_FOR_INDEPENDENT_REVIEW":
        raise FormalActivationRejected("V7 sealed bundle is absent")
    inner_path = _production_artifact_path("inner_manifest")
    outer_path = _production_artifact_path("outer_manifest")
    inner = _ordinary_stable_json(inner_path, "V7 sealed inner manifest")
    outer = _ordinary_stable_json(outer_path, "V7 sealed outer manifest")
    members = _mapping(inner.get("members"), "V7 sealed inner members")
    lease = _production_one_shot()
    closure = (
        verify_execution_closure(require_frozen_expected=True)
        if validated_closure is None
        else _validated_frozen_closure_snapshot(validated_closure)
    )
    if (
        set(inner) != {"schema", "version", "members"}
        or inner.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v7_inner"
        or inner.get("version") != 7
        or set(members) != _expected_inner_member_paths(lease)
        or set(outer) != {"schema", "version", "inner"}
        or outer
        != {
            "schema": "rq2_public_grid_highs_formal_activation_successor_v7_outer",
            "version": 7,
            "inner": {
                "path": inner_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(inner_path),
            },
        }
        or members.get(
            _production_artifact_path("execution_closure").relative_to(ROOT).as_posix()
        )
        != sha256_file(_production_artifact_path("execution_closure"))
        or closure.get("expected_hashes_verified") is not True
    ):
        raise FormalActivationRejected("V7 sealed bundle drifted")
    for raw_path, expected_sha256 in members.items():
        member_path = _repo_path(raw_path, f"sealed member {raw_path}")
        if raw_path == lease["fresh_path"] and not _entry_exists(member_path):
            tombstone = _validate_consumed_one_shot_authority(lease=lease)
            if tombstone["fresh_authority_sha256"] != expected_sha256:
                raise FormalActivationRejected("sealed fresh lease binding drifted")
            continue
        raw, _ = _ordinary_stable_bytes(member_path, f"sealed member {raw_path}")
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise FormalActivationRejected(f"sealed member drifted: {raw_path}")
    return {"inner": inner, "outer": outer, "closure": closure}


def _verify_fresh_one_shot_authority() -> dict[str, Any]:
    lease = _production_one_shot()
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    consumed = _repo_path(lease["consumed_path"], "consumed one-shot authority")
    reservation = _one_shot_reservation_path(consumed)
    if _entry_exists(consumed) or _entry_exists(reservation):
        raise FormalActivationRejected("consumed one-shot authority already exists")
    raw, _ = _ordinary_stable_bytes(fresh, "fresh one-shot authority")
    try:
        value = _mapping(json.loads(raw), "fresh one-shot authority")
    except json.JSONDecodeError as exc:
        raise FormalActivationRejected("fresh one-shot authority is not JSON") from exc
    expected_keys = {
        "schema",
        "version",
        "authority_id",
        "state",
        "one_shot",
        "formal_execution_authorized",
        "materialized_from_successor_design_authorization",
        "security_certified",
    }
    if (
        hashlib.sha256(raw).hexdigest() != lease["fresh_sha256"]
        or set(value) != expected_keys
        or value.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v7_one_shot_authority"
        or value.get("version") != 7
        or value.get("authority_id") != lease["authority_id"]
        or value.get("state") != "fresh"
        or value.get("one_shot") is not True
        or value.get("formal_execution_authorized") is not False
        or value.get("materialized_from_successor_design_authorization") is not False
        or value.get("security_certified") is not False
    ):
        raise FormalActivationRejected("fresh one-shot authority drifted")
    return {"binding": lease, "payload": value}


def _powershell_related_processes(module_name: str) -> list[dict[str, object]]:
    escaped = module_name.replace("'", "''")
    script = (
        "$selfPid=$PID; Get-CimInstance Win32_Process | "
        f"Where-Object {{$_.ProcessId -ne $selfPid -and "
        f"([string]$_.CommandLine).Contains('{escaped}')}} | "
        "Select-Object ProcessId,Name | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    raw = completed.stdout.strip()
    if not raw:
        return []
    value = json.loads(raw)
    return [value] if isinstance(value, dict) else list(value)


def related_formal_processes() -> list[dict[str, object]]:
    module = str(load_config()["runtime"]["formal_controller_module"])
    return _powershell_related_processes(module)


def ensure_no_related_formal_process() -> None:
    if related_formal_processes():
        raise FormalActivationRejected("related formal process is already active")


def next_attempt_root() -> Path:
    root = activation_audit_root()
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        candidate = root / f"attempt_{time.time_ns()}"
        if not candidate.exists():
            return candidate
    raise FormalActivationRejected("could not allocate activation attempt root")


def capture_preflight_evidence(
    attempt_root: Path,
    *,
    authority_mapping: Mapping[str, str],
    observed_available_commit_bytes: Callable[[], int],
    wall_time_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> dict[str, Any]:
    if attempt_root.exists():
        raise FormalActivationRejected("activation attempt root must not preexist")
    if attempt_root.parent.resolve() != activation_audit_root().resolve():
        raise FormalActivationRejected("activation attempt parent drifted")
    attempt_root.mkdir(parents=True, exist_ok=False)
    observed = observed_available_commit_bytes()
    wall = wall_time_ns()
    monotonic = monotonic_ns()
    mapping = dict(sorted(authority_mapping.items()))
    if (
        type(observed) is not int
        or observed < 0
        or type(wall) is not int
        or wall <= 0
        or type(monotonic) is not int
        or monotonic <= 0
        or any(
            not isinstance(key, str) or not _is_sha256(value)
            for key, value in mapping.items()
        )
    ):
        raise FormalActivationRejected("system commit preflight observation malformed")
    payload = {
        "schema": "rq2_public_grid_highs_formal_activation_preflight_v7",
        "version": 7,
        "wall_time_ns": wall,
        "monotonic_ns": monotonic,
        "observed_available_commit_bytes": observed,
        "preflight_threshold_bytes": PREFLIGHT_THRESHOLD_BYTES,
        "child_private_commit_stop_bytes": CHILD_PRIVATE_COMMIT_STOP_BYTES,
        "system_commit_available_stop_bytes": SYSTEM_COMMIT_AVAILABLE_STOP_BYTES,
        "authority_mapping": mapping,
        "authority_mapping_sha256": canonical_sha256(mapping),
        "comparison": "observed_available_commit_bytes >= preflight_threshold_bytes",
        "threshold_passed": observed >= PREFLIGHT_THRESHOLD_BYTES,
        "formal_roots_created": False,
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "mathematical_infeasibility_inferred": False,
    }
    path = attempt_root / "preflight.json"
    persist_json_stable(path, payload)
    return {
        **payload,
        "persisted_path": str(path.resolve()),
        "persisted_sha256": sha256_file(path),
        "stable_readback_verified": True,
    }


def _validate_production_preflight(
    preflight: Mapping[str, Any],
    *,
    attempt_root: Path,
    expected_authority_mapping: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    path = attempt_root / "preflight.json"
    persisted = _ordinary_stable_json(path, "production preflight")
    expected_mapping = dict(
        expected_authority_mapping
        if expected_authority_mapping is not None
        else _expected_preflight_authority_mapping()
    )
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "observed_available_commit_bytes",
        "preflight_threshold_bytes",
        "child_private_commit_stop_bytes",
        "system_commit_available_stop_bytes",
        "authority_mapping",
        "authority_mapping_sha256",
        "comparison",
        "threshold_passed",
        "formal_roots_created",
        "authority_consumed",
        "formal_controller_spawned",
        "mathematical_infeasibility_inferred",
    }
    if (
        set(persisted) != expected_keys
        or persisted.get("schema")
        != "rq2_public_grid_highs_formal_activation_preflight_v7"
        or persisted.get("version") != 7
        or persisted.get("authority_mapping") != expected_mapping
        or persisted.get("authority_mapping_sha256")
        != canonical_sha256(expected_mapping)
        or persisted.get("threshold_passed") is not True
        or persisted.get("formal_roots_created") is not False
        or persisted.get("authority_consumed") is not False
        or persisted.get("formal_controller_spawned") is not False
        or persisted.get("mathematical_infeasibility_inferred") is not False
        or preflight.get("path") != str(path.resolve())
        or preflight.get("sha256") != sha256_file(path)
    ):
        raise FormalActivationRejected("production preflight binding drifted")
    return persisted


def production_static_authority_mapping(
    *, validated_closure: Mapping[str, Any] | None = None
) -> dict[str, str]:
    closure_path = _production_artifact_path("execution_closure")
    closure = (
        verify_execution_closure(require_frozen_expected=True)
        if validated_closure is None
        else _validated_frozen_closure_snapshot(validated_closure)
    )
    mapping = dict(_mapping(closure["members"], "frozen execution members"))
    for name in (
        "inner_manifest",
        "outer_manifest",
        "activation_review_receipt",
        "user_formal_run_authority",
    ):
        path = _production_artifact_path(name)
        mapping[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    mapping[closure_path.relative_to(ROOT).as_posix()] = sha256_file(closure_path)
    return dict(sorted(mapping.items()))


def preflight_authority_mapping() -> dict[str, str]:
    closure = verify_execution_closure(require_frozen_expected=True)
    _verify_sealed_bundle(validated_closure=closure)
    static_mapping = production_static_authority_mapping(validated_closure=closure)
    lease = _mapping(
        _verify_fresh_one_shot_authority()["binding"], "fresh lease binding"
    )
    return _expected_preflight_authority_mapping(
        validated_static_mapping=static_mapping,
        validated_lease=lease,
    )


def _expected_preflight_authority_mapping(
    *,
    validated_static_mapping: Mapping[str, str] | None = None,
    validated_lease: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    mapping = dict(
        validated_static_mapping
        if validated_static_mapping is not None
        else production_static_authority_mapping()
    )
    lease = dict(
        validated_lease if validated_lease is not None else _production_one_shot()
    )
    if lease != _production_one_shot():
        raise FormalActivationRejected("validated one-shot lease snapshot drifted")
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    mapping[fresh.relative_to(ROOT).as_posix()] = str(lease["fresh_sha256"])
    return dict(sorted(mapping.items()))


def _validate_activation_review_receipt(
    receipt: Mapping[str, Any], *, path: Path
) -> dict[str, Any]:
    outer = _production_artifact_path("outer_manifest")
    expected_keys = {
        "schema",
        "version",
        "reviewed_on",
        "reviewer_agent",
        "reviewer_role",
        "reviewer_model",
        "verdict",
        "reviewed_outer",
        "findings",
        "materialized_from_independent_review_report",
        "cryptographic_reviewer_signature_present",
        "effect",
    }
    if (
        path != _production_artifact_path("activation_review_receipt")
        or set(receipt) != expected_keys
        or receipt.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_review_pass_v7"
        or receipt.get("version") != 7
        or not isinstance(receipt.get("reviewed_on"), str)
        or len(str(receipt.get("reviewed_on"))) != 10
        or not isinstance(receipt.get("reviewer_agent"), str)
        or not str(receipt.get("reviewer_agent")).startswith("/root/")
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("reviewer_model") != "gpt-5.6-sol"
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer")
        != {
            "path": outer.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(outer),
        }
        or receipt.get("findings") != []
        or receipt.get("materialized_from_independent_review_report") is not True
        or receipt.get("cryptographic_reviewer_signature_present") is not False
        or receipt.get("effect")
        != {
            "formal_activation_successor_independent_review_passed": True,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
    ):
        raise FormalActivationRejected("activation review PASS receipt drifted")
    return dict(receipt)


def require_activation_review_pass() -> dict[str, Any]:
    path = _production_artifact_path("activation_review_receipt")
    receipt = _ordinary_stable_json(path, "activation review PASS receipt")
    return _validate_activation_review_receipt(receipt, path=path)


def require_user_formal_run_authority(
    *, validated_review: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    review_path = _production_artifact_path("activation_review_receipt")
    if validated_review is None:
        review = require_activation_review_pass()
    else:
        review = _validate_activation_review_receipt(
            dict(validated_review), path=review_path
        )
        if review != _ordinary_stable_json(
            review_path, "validated activation review snapshot"
        ):
            raise FormalActivationRejected("activation review snapshot drifted")
    path = _production_artifact_path("user_formal_run_authority")
    outer = _production_artifact_path("outer_manifest")
    closure = _production_artifact_path("execution_closure")
    receipt = _ordinary_stable_json(path, "user formal-run authority")
    lease = _production_one_shot()
    expected_keys = {
        "schema",
        "version",
        "authority_source",
        "materialized_from_user_instruction",
        "cryptographic_user_signature_present",
        "review_pass",
        "reviewed_outer",
        "formal_config",
        "execution_closure",
        "controller_command_prefix",
        "one_shot_authority",
        "effect",
    }
    if (
        set(receipt) != expected_keys
        or receipt.get("schema") != "rq2_public_grid_highs_formal_run_authority_v7"
        or receipt.get("version") != 7
        or receipt.get("authority_source") != "explicit_user_formal_run_authorization"
        or receipt.get("materialized_from_user_instruction") is not True
        or receipt.get("cryptographic_user_signature_present") is not False
        or receipt.get("review_pass")
        != {
            "path": review_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(review_path),
        }
        or receipt.get("reviewed_outer")
        != {"path": outer.relative_to(ROOT).as_posix(), "sha256": sha256_file(outer)}
        or receipt.get("formal_config")
        != {
            "path": FORMAL_CONFIG.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(FORMAL_CONFIG),
        }
        or receipt.get("execution_closure")
        != {
            "path": closure.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(closure),
        }
        or receipt.get("controller_command_prefix")
        != load_config()["runtime"]["controller_command_prefix"]
        or receipt.get("one_shot_authority") != lease
        or receipt.get("effect")
        != {
            "formal_activation_successor_independent_review_passed": True,
            "user_formal_run_authorized": True,
            "formal_execution_authorized": True,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
        or review.get("effect", {}).get("formal_execution_authorized") is not False
    ):
        raise FormalActivationRejected("user formal-run authority drifted")
    return receipt


def static_authority_mapping() -> dict[str, str]:
    members = derive_execution_closure_members()
    return dict(sorted(members.items()))


def _preseal_placeholder(path: Path, kind: str) -> None:
    persist_json_stable(
        path,
        {
            "schema": f"rq2_v7_preseal_{kind}_placeholder",
            "version": 7,
            "status": "NONAUTHORITATIVE",
            "formal_execution_authorized": False,
            "claim": False,
            "security_certified": False,
        },
    )


def prepare_preseal_authority(
    attempt_root: Path,
    *,
    bootstrap_identity: Mapping[str, int],
    fault_phase: str | None = None,
    fault_type: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create and consume a tmp-only authority for zero-solver startup probes."""
    attempt_root = _canonical_path(attempt_root)
    if attempt_root.exists():
        raise FormalActivationRejected("pre-seal attempt root must not preexist")
    attempt_root.mkdir(parents=True, exist_ok=False)
    closure_path = attempt_root / "execution_closure.NONAUTHORITATIVE.json"
    closure = persist_preseal_execution_closure(closure_path)
    placeholders = {
        name: attempt_root / f"{name}.NONAUTHORITATIVE.json"
        for name in ("outer", "activation_review_pass", "user_formal_run_authority")
    }
    for name, path in placeholders.items():
        _preseal_placeholder(path, name)
    mapping = static_authority_mapping()
    preflight = {
        "schema": "rq2_public_grid_highs_formal_activation_preflight_v7_preseal",
        "version": 7,
        "status": "NONAUTHORITATIVE_SYNTHETIC_THRESHOLD_PROBE",
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "observed_available_commit_bytes": PREFLIGHT_THRESHOLD_BYTES,
        "preflight_threshold_bytes": PREFLIGHT_THRESHOLD_BYTES,
        "child_private_commit_stop_bytes": CHILD_PRIVATE_COMMIT_STOP_BYTES,
        "system_commit_available_stop_bytes": SYSTEM_COMMIT_AVAILABLE_STOP_BYTES,
        "authority_mapping": mapping,
        "authority_mapping_sha256": canonical_sha256(mapping),
        "threshold_passed": True,
        "formal_roots_created": False,
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "formal_execution_authorized": False,
    }
    preflight_path = attempt_root / "preflight.json"
    persist_json_stable(preflight_path, preflight)
    fresh_path = attempt_root / "one_shot_authority.fresh.json"
    consumed_path = attempt_root / "one_shot_authority.consumed.json"
    fresh = {
        "schema": "rq2_public_grid_highs_formal_activation_v7_preseal_one_shot",
        "version": 7,
        "authority_id": canonical_sha256({"attempt_root": str(attempt_root)}),
        "state": "fresh",
        "one_shot": True,
        "formal_execution_authorized": False,
    }
    persist_json_stable(fresh_path, fresh)
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    authority_path = attempt_root / "authority.json"
    command = exact_controller_command(
        authority_path,
        bootstrap_identity=bootstrap_pair,
        preseal_probe=True,
        fault_phase=fault_phase,
        fault_type=fault_type,
    )
    environment = exact_controller_environment(closure_path)
    roots = {
        name: str(attempt_root / "formal_roots" / name)
        for name in ("checkpoint", "worker", "log", "output")
    }
    dynamic = {
        "schema": "rq2_public_grid_highs_formal_dynamic_activation_authority_v7_preseal",
        "version": 7,
        "status": "NONAUTHORITATIVE_STARTUP_PROBE_ONLY",
        "preflight": {
            "path": str(preflight_path),
            "sha256": sha256_file(preflight_path),
        },
        "execution_closure": {
            "path": str(closure_path),
            "sha256": sha256_file(closure_path),
            "members_sha256": closure["members_sha256"],
        },
        "placeholder_bindings": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in placeholders.items()
        },
        "one_shot": {
            "authority_id": fresh["authority_id"],
            "fresh_path": str(fresh_path),
            "consumed_path": str(consumed_path),
        },
        "bootstrap_identity": bootstrap_pair,
        "startup_paths": startup_paths(attempt_root),
        "exact_command": command,
        "exact_cwd": str(ROOT),
        "exact_environment": environment,
        "exact_environment_sha256": canonical_sha256(environment),
        "formal_roots": roots,
        "preseal_startup_probe": True,
        "fault_phase": fault_phase,
        "fault_type": fault_type,
        "starts_from_block_zero": True,
        "resume_allowed": False,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    persist_json_stable(authority_path, dynamic)
    receipt = {
        "schema": "rq2_public_grid_highs_formal_activation_attempt_receipt_v7_preseal",
        "version": 7,
        "status": "NONAUTHORITATIVE",
        "authority_path": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "formal_execution_authorized": False,
        "claim": False,
        "security_certified": False,
    }
    receipt_path = attempt_root / "activation_receipt.json"
    persist_json_stable(receipt_path, receipt)
    os.replace(fresh_path, consumed_path)
    tombstone = {
        "schema": "rq2_public_grid_highs_formal_activation_v7_preseal_consumed_authority",
        "version": 7,
        "authority_id": fresh["authority_id"],
        "state": "consumed",
        "one_shot_reusable": False,
        "dynamic_authority_path": str(authority_path),
        "dynamic_authority_sha256": sha256_file(authority_path),
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": sha256_file(receipt_path),
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    persist_json_stable(consumed_path, tombstone)
    return {
        **dynamic,
        "authority_path": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": sha256_file(receipt_path),
    }, tombstone


def _production_artifact_bindings() -> dict[str, dict[str, str]]:
    paths = {
        "formal_config": FORMAL_CONFIG,
        "controller": ROOT
        / "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v8.py",
        "inner": _production_artifact_path("inner_manifest"),
        "outer": _production_artifact_path("outer_manifest"),
        "execution_closure": _production_artifact_path("execution_closure"),
        "activation_review_pass": _production_artifact_path(
            "activation_review_receipt"
        ),
        "user_formal_run_authority": _production_artifact_path(
            "user_formal_run_authority"
        ),
    }
    return {
        name: {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
        }
        for name, path in paths.items()
    }


def publish_dynamic_authority(
    preflight: Mapping[str, Any],
    *,
    review_receipt: Mapping[str, Any],
    user_run_authority: Mapping[str, Any],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    preflight_path = Path(str(preflight.get("persisted_path"))).resolve()
    attempt_root = preflight_path.parent
    if (
        preflight_path != attempt_root / "preflight.json"
        or preflight.get("stable_readback_verified") is not True
        or preflight.get("threshold_passed") is not True
        or preflight.get("persisted_sha256") != sha256_file(preflight_path)
    ):
        raise FormalActivationRejected("preflight persistence binding drifted")
    closure = verify_execution_closure(require_frozen_expected=True)
    _verify_sealed_bundle(validated_closure=closure)
    static_mapping = production_static_authority_mapping(validated_closure=closure)
    lease = _mapping(
        _verify_fresh_one_shot_authority()["binding"], "fresh lease binding"
    )
    expected_preflight_mapping = _expected_preflight_authority_mapping(
        validated_static_mapping=static_mapping,
        validated_lease=lease,
    )
    persisted_preflight = _validate_production_preflight(
        {
            "path": str(preflight_path),
            "sha256": preflight["persisted_sha256"],
        },
        attempt_root=attempt_root,
        expected_authority_mapping=expected_preflight_mapping,
    )
    validated_review = require_activation_review_pass()
    if dict(review_receipt) != validated_review:
        raise FormalActivationRejected("activation review receipt argument drifted")
    validated_user = require_user_formal_run_authority(
        validated_review=validated_review
    )
    if dict(user_run_authority) != validated_user:
        raise FormalActivationRejected("user run authority argument drifted")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    authority_path = attempt_root / "authority.json"
    command = exact_controller_command(
        authority_path, bootstrap_identity=bootstrap_pair, preseal_probe=False
    )
    environment = exact_controller_environment()
    payload = {
        "schema": "rq2_public_grid_highs_formal_dynamic_activation_authority_v7",
        "version": 7,
        "status": "PRODUCTION_ONE_SHOT_AUTHORITY",
        "preflight": {
            "path": str(preflight_path),
            "sha256": sha256_file(preflight_path),
        },
        "preflight_authority_mapping": persisted_preflight["authority_mapping"],
        "preflight_authority_mapping_sha256": persisted_preflight[
            "authority_mapping_sha256"
        ],
        "execution_closure": {
            "path": str(_production_artifact_path("execution_closure")),
            "sha256": sha256_file(_production_artifact_path("execution_closure")),
            "members_sha256": closure["members_sha256"],
            "expected_hashes_verified": True,
        },
        "artifact_bindings": _production_artifact_bindings(),
        "one_shot": lease,
        "bootstrap_identity": bootstrap_pair,
        "startup_paths": startup_paths(attempt_root),
        "exact_command": command,
        "exact_cwd": str(ROOT),
        "exact_environment": environment,
        "exact_environment_sha256": canonical_sha256(environment),
        "formal_roots": {
            name: str(path.resolve()) for name, path in formal_roots().items()
        },
        "preseal_startup_probe": False,
        "fault_phase": None,
        "fault_type": None,
        "starts_from_block_zero": True,
        "resume_allowed": False,
        "formal_execution_authorized": True,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    persist_json_stable(authority_path, payload)
    receipt = {
        "schema": "rq2_public_grid_highs_formal_activation_attempt_receipt_v7",
        "version": 7,
        "preflight_path": str(preflight_path),
        "preflight_sha256": sha256_file(preflight_path),
        "authority_path": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "threshold_passed": True,
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    receipt_path = attempt_root / "activation_receipt.json"
    persist_json_stable(receipt_path, receipt)
    return {
        **payload,
        "authority_path": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": sha256_file(receipt_path),
    }


def _validate_reserved_one_shot_move(consumed: Path, *, expected_sha256: str) -> None:
    raw, _ = _ordinary_stable_bytes(consumed, "reserved one-shot authority")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise FormalActivationRejected("reserved one-shot authority drifted")


def _one_shot_reservation_path(consumed: Path) -> Path:
    return consumed.with_name(f".{consumed.name}.reservation")


def _validate_consumed_one_shot_authority(
    *, lease: Mapping[str, Any], dynamic_authority: Path | None = None
) -> dict[str, Any]:
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    consumed = _repo_path(lease["consumed_path"], "consumed one-shot authority")
    tombstone = _ordinary_stable_json(consumed, "consumed one-shot authority")
    expected_keys = {
        "schema",
        "version",
        "authority_id",
        "state",
        "one_shot_reusable",
        "fresh_authority_path",
        "fresh_authority_sha256",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "activation_receipt_path",
        "activation_receipt_sha256",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    dynamic_path = Path(str(tombstone.get("dynamic_authority_path"))).resolve()
    receipt_path = Path(str(tombstone.get("activation_receipt_path"))).resolve()
    if (
        _entry_exists(fresh)
        or set(tombstone) != expected_keys
        or tombstone.get("schema")
        != "rq2_public_grid_highs_formal_activation_v7_consumed_authority"
        or tombstone.get("version") != 7
        or tombstone.get("authority_id") != lease["authority_id"]
        or tombstone.get("state") != "consumed"
        or tombstone.get("one_shot_reusable") is not False
        or tombstone.get("fresh_authority_path") != str(fresh)
        or tombstone.get("fresh_authority_sha256") != lease["fresh_sha256"]
        or (dynamic_authority is not None and dynamic_path != dynamic_authority)
        or not dynamic_path.is_file()
        or tombstone.get("dynamic_authority_sha256") != sha256_file(dynamic_path)
        or receipt_path != dynamic_path.parent / "activation_receipt.json"
        or not receipt_path.is_file()
        or tombstone.get("activation_receipt_sha256") != sha256_file(receipt_path)
        or any(
            tombstone.get(key) is not False
            for key in ("formal_result_exists", "claim", "security_certified")
        )
    ):
        raise FormalActivationRejected("consumed one-shot authority drifted")
    return tombstone


def _consume_reserved_one_shot(
    fresh: Path,
    consumed: Path,
    *,
    expected_sha256: str,
    tombstone: Mapping[str, Any],
) -> dict[str, Any]:
    if os.name != "nt":
        raise FormalActivationRejected(
            "one-shot consumption requires Windows no-replace rename semantics"
        )
    if _entry_exists(consumed):
        raise FormalActivationRejected(
            "consumed one-shot destination is already reserved"
        )
    reservation = _one_shot_reservation_path(consumed)
    try:
        reservation.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise FormalActivationRejected(
            "one-shot consumption is already reserved"
        ) from exc
    except OSError as exc:
        raise FormalActivationRejected(
            "one-shot consumption cannot be reserved"
        ) from exc
    if _entry_exists(consumed):
        raise FormalActivationRejected(
            "consumed one-shot destination appeared after reservation"
        )
    try:
        os.rename(fresh, consumed)
    except OSError as exc:
        raise FormalActivationRejected(
            "fresh one-shot authority cannot be moved into reservation"
        ) from exc
    if _entry_exists(fresh):
        raise FormalActivationRejected("one-shot authority remained reusable")
    _validate_reserved_one_shot_move(consumed, expected_sha256=expected_sha256)
    persist_json_stable(consumed, tombstone)
    reservation.rmdir()
    return dict(tombstone)


def consume_one_shot_authority(dynamic: Mapping[str, Any]) -> dict[str, Any]:
    authority_path = Path(str(dynamic.get("authority_path"))).resolve()
    validated = validate_dynamic_authority(authority_path)
    if any(dynamic.get(key) != value for key, value in validated.items()):
        raise FormalActivationRejected("dynamic authority changed before consume")
    lease = _production_one_shot()
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    consumed = _repo_path(lease["consumed_path"], "consumed one-shot authority")
    verified_lease = _mapping(
        _verify_fresh_one_shot_authority()["binding"], "fresh lease binding"
    )
    if verified_lease != lease:
        raise FormalActivationRejected("fresh one-shot lease changed before consume")
    tombstone = {
        "schema": "rq2_public_grid_highs_formal_activation_v7_consumed_authority",
        "version": 7,
        "authority_id": lease["authority_id"],
        "state": "consumed",
        "one_shot_reusable": False,
        "fresh_authority_path": str(fresh),
        "fresh_authority_sha256": lease["fresh_sha256"],
        "dynamic_authority_path": str(authority_path),
        "dynamic_authority_sha256": sha256_file(authority_path),
        "activation_receipt_path": str(
            authority_path.parent / "activation_receipt.json"
        ),
        "activation_receipt_sha256": sha256_file(
            authority_path.parent / "activation_receipt.json"
        ),
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    _consume_reserved_one_shot(
        fresh,
        consumed,
        expected_sha256=str(lease["fresh_sha256"]),
        tombstone=tombstone,
    )
    return _validate_consumed_one_shot_authority(
        lease=lease, dynamic_authority=authority_path
    )


def _validate_preseal_dynamic_authority(path: Path) -> dict[str, Any]:
    path = _canonical_path(path)
    dynamic = _ordinary_stable_json(path, "dynamic activation authority")
    expected_keys = {
        "schema",
        "version",
        "status",
        "preflight",
        "execution_closure",
        "placeholder_bindings",
        "one_shot",
        "bootstrap_identity",
        "startup_paths",
        "exact_command",
        "exact_cwd",
        "exact_environment",
        "exact_environment_sha256",
        "formal_roots",
        "preseal_startup_probe",
        "fault_phase",
        "fault_type",
        "starts_from_block_zero",
        "resume_allowed",
        "formal_execution_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    preflight = _mapping(dynamic.get("preflight"), "dynamic preflight")
    closure = _mapping(dynamic.get("execution_closure"), "dynamic closure")
    one_shot = _mapping(dynamic.get("one_shot"), "dynamic one-shot")
    attempt_root = path.parent
    preflight_path = attempt_root / "preflight.json"
    closure_path = attempt_root / "execution_closure.NONAUTHORITATIVE.json"
    consumed_path = attempt_root / "one_shot_authority.consumed.json"
    fresh_path = attempt_root / "one_shot_authority.fresh.json"
    placeholders = {
        name: attempt_root / f"{name}.NONAUTHORITATIVE.json"
        for name in ("outer", "activation_review_pass", "user_formal_run_authority")
    }
    expected_placeholders = {
        name: {"path": str(value), "sha256": sha256_file(value)}
        for name, value in placeholders.items()
    }
    expected_roots = {
        name: str(attempt_root / "formal_roots" / name)
        for name in ("checkpoint", "worker", "log", "output")
    }
    preflight_payload = _ordinary_stable_json(preflight_path, "preseal preflight")
    tombstone = _ordinary_stable_json(consumed_path, "preseal consumed authority")
    if (
        path.name != "authority.json"
        or set(dynamic) != expected_keys
        or dynamic.get("schema")
        != "rq2_public_grid_highs_formal_dynamic_activation_authority_v7_preseal"
        or dynamic.get("version") != 7
        or dynamic.get("status") != "NONAUTHORITATIVE_STARTUP_PROBE_ONLY"
        or dynamic.get("bootstrap_identity")
        != _process_identity(dynamic.get("bootstrap_identity"), "bootstrap identity")
        or dynamic.get("startup_paths") != startup_paths(path.parent)
        or dynamic.get("exact_command")
        != exact_controller_command(
            path, bootstrap_identity=dynamic["bootstrap_identity"]
        )
        or dynamic.get("exact_cwd") != str(ROOT)
        or dynamic.get("exact_environment")
        != exact_controller_environment(closure_path)
        or dynamic.get("exact_environment_sha256")
        != canonical_sha256(dynamic.get("exact_environment"))
        or dynamic.get("formal_roots") != expected_roots
        or dynamic.get("placeholder_bindings") != expected_placeholders
        or preflight
        != {"path": str(preflight_path), "sha256": sha256_file(preflight_path)}
        or preflight_payload.get("authority_mapping") != static_authority_mapping()
        or preflight_payload.get("authority_mapping_sha256")
        != canonical_sha256(static_authority_mapping())
        or preflight_payload.get("threshold_passed") is not True
        or closure
        != {
            "path": str(closure_path),
            "sha256": sha256_file(closure_path),
            "members_sha256": _closure_payload()["members_sha256"],
        }
        or one_shot
        != {
            "authority_id": canonical_sha256({"attempt_root": str(attempt_root)}),
            "fresh_path": str(fresh_path),
            "consumed_path": str(consumed_path),
        }
        or dynamic.get("preseal_startup_probe") is not True
        or dynamic.get("starts_from_block_zero") is not True
        or dynamic.get("resume_allowed") is not False
        or any(
            dynamic.get(key) is not False
            for key in (
                "formal_execution_authorized",
                "formal_result_exists",
                "claim",
                "security_certified",
            )
        )
        or _ordinary_stable_json(closure_path, "preseal closure") != _closure_payload()
        or fresh_path.exists()
        or tombstone.get("schema")
        != "rq2_public_grid_highs_formal_activation_v7_preseal_consumed_authority"
        or tombstone.get("authority_id") != one_shot["authority_id"]
        or tombstone.get("state") != "consumed"
        or tombstone.get("one_shot_reusable") is not False
        or tombstone.get("dynamic_authority_path") != str(path)
        or tombstone.get("dynamic_authority_sha256") != sha256_file(path)
        or tombstone.get("activation_receipt_path")
        != str(attempt_root / "activation_receipt.json")
        or tombstone.get("activation_receipt_sha256")
        != sha256_file(attempt_root / "activation_receipt.json")
    ):
        raise FormalActivationRejected("dynamic pre-seal authority drifted")
    return dynamic


def _validate_production_dynamic_authority(
    path: Path, dynamic: Mapping[str, Any]
) -> dict[str, Any]:
    attempt_root = path.parent
    expected_keys = {
        "schema",
        "version",
        "status",
        "preflight",
        "preflight_authority_mapping",
        "preflight_authority_mapping_sha256",
        "execution_closure",
        "artifact_bindings",
        "one_shot",
        "bootstrap_identity",
        "startup_paths",
        "exact_command",
        "exact_cwd",
        "exact_environment",
        "exact_environment_sha256",
        "formal_roots",
        "preseal_startup_probe",
        "fault_phase",
        "fault_type",
        "starts_from_block_zero",
        "resume_allowed",
        "formal_execution_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    pair = _process_identity(dynamic.get("bootstrap_identity"), "bootstrap identity")
    preflight = _mapping(dynamic.get("preflight"), "dynamic preflight")
    closure = _mapping(dynamic.get("execution_closure"), "dynamic closure")
    expected_closure = verify_execution_closure(require_frozen_expected=True)
    _verify_sealed_bundle(validated_closure=expected_closure)
    static_mapping = production_static_authority_mapping(
        validated_closure=expected_closure
    )
    lease = _production_one_shot()
    expected_preflight_mapping = _expected_preflight_authority_mapping(
        validated_static_mapping=static_mapping,
        validated_lease=lease,
    )
    persisted_preflight = _validate_production_preflight(
        preflight,
        attempt_root=attempt_root,
        expected_authority_mapping=expected_preflight_mapping,
    )
    validated_review = require_activation_review_pass()
    require_user_formal_run_authority(validated_review=validated_review)
    closure_path = _production_artifact_path("execution_closure")
    exact_environment = exact_controller_environment()
    if (
        path.name != "authority.json"
        or attempt_root.parent.resolve() != activation_audit_root().resolve()
        or not attempt_root.name.startswith("attempt_")
        or set(dynamic) != expected_keys
        or dynamic.get("schema")
        != "rq2_public_grid_highs_formal_dynamic_activation_authority_v7"
        or dynamic.get("version") != 7
        or dynamic.get("status") != "PRODUCTION_ONE_SHOT_AUTHORITY"
        or dynamic.get("preflight_authority_mapping") != expected_preflight_mapping
        or dynamic.get("preflight_authority_mapping_sha256")
        != canonical_sha256(expected_preflight_mapping)
        or persisted_preflight.get("threshold_passed") is not True
        or closure
        != {
            "path": str(closure_path),
            "sha256": sha256_file(closure_path),
            "members_sha256": expected_closure["members_sha256"],
            "expected_hashes_verified": True,
        }
        or dynamic.get("artifact_bindings") != _production_artifact_bindings()
        or dynamic.get("one_shot") != lease
        or dynamic.get("bootstrap_identity") != pair
        or dynamic.get("startup_paths") != startup_paths(attempt_root)
        or dynamic.get("exact_command")
        != exact_controller_command(path, bootstrap_identity=pair, preseal_probe=False)
        or dynamic.get("exact_cwd") != str(ROOT)
        or dynamic.get("exact_environment") != exact_environment
        or dynamic.get("exact_environment_sha256")
        != canonical_sha256(exact_environment)
        or dynamic.get("formal_roots")
        != {name: str(root.resolve()) for name, root in formal_roots().items()}
        or dynamic.get("preseal_startup_probe") is not False
        or dynamic.get("fault_phase") is not None
        or dynamic.get("fault_type") is not None
        or dynamic.get("starts_from_block_zero") is not True
        or dynamic.get("resume_allowed") is not False
        or dynamic.get("formal_execution_authorized") is not True
        or any(
            dynamic.get(key) is not False
            for key in ("formal_result_exists", "claim", "security_certified")
        )
    ):
        raise FormalActivationRejected("dynamic production authority drifted")
    return dict(dynamic)


def validate_dynamic_authority(path: Path) -> dict[str, Any]:
    path = _canonical_path(path)
    dynamic = _ordinary_stable_json(path, "dynamic activation authority")
    schema = dynamic.get("schema")
    if schema == "rq2_public_grid_highs_formal_dynamic_activation_authority_v7_preseal":
        return _validate_preseal_dynamic_authority(path)
    if schema == "rq2_public_grid_highs_formal_dynamic_activation_authority_v7":
        return _validate_production_dynamic_authority(path, dynamic)
    raise FormalActivationRejected("dynamic activation authority schema drifted")


def startup_bindings(
    dynamic_authority: Path,
    *,
    validated_dynamic: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    dynamic_authority = dynamic_authority.resolve()
    if validated_dynamic is None:
        dynamic = validate_dynamic_authority(dynamic_authority)
    else:
        dynamic = dict(validated_dynamic)
        if dynamic != _ordinary_stable_json(
            dynamic_authority, "validated dynamic authority snapshot"
        ):
            raise FormalActivationRejected("dynamic authority snapshot drifted")
    schema = dynamic["schema"]
    if schema.endswith("_preseal"):
        placeholders = _mapping(dynamic["placeholder_bindings"], "placeholders")
        closure = _mapping(dynamic["execution_closure"], "execution closure")
        paths = {
            "formal_config": FORMAL_CONFIG,
            "controller": ROOT
            / "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v8.py",
            "outer": Path(str(_mapping(placeholders["outer"], "outer")["path"])),
            "execution_closure": Path(str(closure["path"])),
            "activation_review_pass": Path(
                str(_mapping(placeholders["activation_review_pass"], "review")["path"])
            ),
            "user_formal_run_authority": Path(
                str(
                    _mapping(
                        placeholders["user_formal_run_authority"], "run authority"
                    )["path"]
                )
            ),
        }
    else:
        artifacts = _mapping(dynamic["artifact_bindings"], "artifact bindings")
        paths = {
            name: (ROOT / str(_mapping(artifacts[name], name)["path"])).resolve()
            for name in (
                "formal_config",
                "controller",
                "outer",
                "execution_closure",
                "activation_review_pass",
                "user_formal_run_authority",
            )
        }
    one_shot = _mapping(dynamic["one_shot"], "one-shot authority")
    paths.update(
        {
            "dynamic_authority": dynamic_authority,
            "preflight": Path(str(dynamic["preflight"]["path"])).resolve(),
            "activation_receipt": dynamic_authority.parent / "activation_receipt.json",
            "consumed_authority": Path(str(one_shot["consumed_path"])).resolve(),
        }
    )
    bindings = {
        name: {"path": str(path), "sha256": sha256_file(path)}
        for name, path in paths.items()
    }
    if set(bindings) != STARTUP_BINDING_NAMES:
        raise FormalActivationRejected("startup binding set drifted")
    return bindings


def runtime_authority_mapping(
    dynamic_authority: Path,
    *,
    validated_dynamic: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    dynamic_authority = dynamic_authority.resolve()
    if validated_dynamic is None:
        dynamic = validate_dynamic_authority(dynamic_authority)
    else:
        dynamic = dict(validated_dynamic)
        if dynamic != _ordinary_stable_json(
            dynamic_authority, "validated dynamic authority snapshot"
        ):
            raise FormalActivationRejected("dynamic authority snapshot drifted")
    if dynamic["schema"].endswith("_preseal"):
        mapping = static_authority_mapping()
    else:
        mapping = dict(
            _mapping(
                dynamic["preflight_authority_mapping"],
                "validated production authority mapping",
            )
        )
        fresh_key = str(
            _mapping(dynamic["one_shot"], "one-shot authority")["fresh_path"]
        )
        if mapping.pop(fresh_key, None) is None:
            raise FormalActivationRejected("fresh lease mapping is absent")
    receipt = dynamic_authority.parent / "activation_receipt.json"
    consumed = Path(str(dynamic["one_shot"]["consumed_path"])).resolve()
    for path in (dynamic_authority, receipt, consumed):
        mapping[str(path)] = sha256_file(path)
    return dict(sorted(mapping.items()))


def terminal_outcome_path(attempt_root: Path) -> Path:
    filename = load_config()["startup_handshake"][
        "authoritative_terminal_outcome_filename"
    ]
    return attempt_root / str(filename)


def _controller_cancellation_path(attempt_root: Path) -> Path:
    return Path(startup_paths(attempt_root.resolve())["controller_cancellation"])


def _controller_cancellation_ack_path(attempt_root: Path) -> Path:
    return Path(startup_paths(attempt_root.resolve())["controller_cancellation_ack"])


def persist_controller_cancellation(
    attempt_root: Path,
    *,
    dynamic_authority: Path,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    reason: str,
) -> dict[str, Any]:
    attempt_root = attempt_root.resolve()
    dynamic_authority = dynamic_authority.resolve()
    dynamic = validate_dynamic_authority(dynamic_authority)
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    paths = {key: Path(value) for key, value in startup_paths(attempt_root).items()}
    if (
        dynamic_authority != attempt_root / "authority.json"
        or dynamic.get("bootstrap_identity") != bootstrap_pair
        or not isinstance(reason, str)
        or not reason
        or not paths["science_release"].is_file()
    ):
        raise FormalActivationRejected("controller cancellation authority drifted")
    payload = {
        "schema": "rq2_public_grid_highs_formal_controller_cancellation_v7",
        "version": 7,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": str(dynamic_authority),
        "dynamic_authority_sha256": sha256_file(dynamic_authority),
        "controller_identity": controller_pair,
        "bootstrap_identity": bootstrap_pair,
        "science_release_path": str(paths["science_release"]),
        "science_release_sha256": sha256_file(paths["science_release"]),
        "terminal_outcome_path": str(paths["terminal_outcome"]),
        "reason": reason,
        "formal_work_continuation_authorized": False,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    persist_json_exclusive_stable(paths["controller_cancellation"], payload)
    return validate_controller_cancellation(
        paths["controller_cancellation"],
        dynamic_authority=dynamic_authority,
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
    )


def validate_controller_cancellation(
    path: Path,
    *,
    dynamic_authority: Path,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    dynamic_authority = dynamic_authority.resolve()
    attempt_root = dynamic_authority.parent
    expected_path = _controller_cancellation_path(attempt_root)
    cancellation = _ordinary_stable_json(path.resolve(), "controller cancellation")
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "controller_identity",
        "bootstrap_identity",
        "science_release_path",
        "science_release_sha256",
        "terminal_outcome_path",
        "reason",
        "formal_work_continuation_authorized",
        "retry_allowed",
        "resume_allowed",
        "formal_result_exists",
        "mathematical_infeasibility_inferred",
        "claim",
        "security_certified",
    }
    release_path = Path(startup_paths(attempt_root)["science_release"])
    if (
        path.resolve() != expected_path
        or set(cancellation) != expected_keys
        or cancellation.get("schema")
        != "rq2_public_grid_highs_formal_controller_cancellation_v7"
        or cancellation.get("version") != 7
        or any(
            type(cancellation.get(key)) is not int or cancellation[key] <= 0
            for key in ("wall_time_ns", "monotonic_ns")
        )
        or cancellation.get("attempt_root") != str(attempt_root)
        or cancellation.get("dynamic_authority_path") != str(dynamic_authority)
        or cancellation.get("dynamic_authority_sha256")
        != sha256_file(dynamic_authority)
        or cancellation.get("controller_identity") != controller_pair
        or cancellation.get("bootstrap_identity") != bootstrap_pair
        or cancellation.get("science_release_path") != str(release_path)
        or cancellation.get("science_release_sha256") != sha256_file(release_path)
        or cancellation.get("terminal_outcome_path")
        != str(terminal_outcome_path(attempt_root).resolve())
        or not isinstance(cancellation.get("reason"), str)
        or not cancellation["reason"]
        or any(
            cancellation.get(key) is not False
            for key in (
                "formal_work_continuation_authorized",
                "retry_allowed",
                "resume_allowed",
                "formal_result_exists",
                "mathematical_infeasibility_inferred",
                "claim",
                "security_certified",
            )
        )
    ):
        raise FormalActivationRejected("controller cancellation evidence drifted")
    return cancellation


def persist_controller_stop_ack(
    attempt_root: Path,
    *,
    cancellation: Mapping[str, Any],
    dynamic_authority: Path,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    observed_before_phase: str,
) -> dict[str, Any]:
    attempt_root = attempt_root.resolve()
    dynamic_authority = dynamic_authority.resolve()
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    cancellation_path = _controller_cancellation_path(attempt_root)
    validated_cancellation = validate_controller_cancellation(
        cancellation_path,
        dynamic_authority=dynamic_authority,
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
    )
    if (
        dict(cancellation) != validated_cancellation
        or not isinstance(observed_before_phase, str)
        or not observed_before_phase
    ):
        raise FormalActivationRejected("controller stop acknowledgement input drifted")
    payload = {
        "schema": "rq2_public_grid_highs_formal_controller_cancellation_ack_v7",
        "version": 7,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": str(dynamic_authority),
        "dynamic_authority_sha256": sha256_file(dynamic_authority),
        "cancellation_path": str(cancellation_path),
        "cancellation_sha256": sha256_file(cancellation_path),
        "controller_identity": controller_pair,
        "bootstrap_identity": bootstrap_pair,
        "observed_before_phase": observed_before_phase,
        "stop_acknowledged": True,
        "formal_work_continuation_authorized": False,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    persist_json_exclusive_stable(
        _controller_cancellation_ack_path(attempt_root), payload
    )
    return validate_controller_stop_ack(
        _controller_cancellation_ack_path(attempt_root),
        dynamic_authority=dynamic_authority,
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
    )


def validate_controller_stop_ack(
    path: Path,
    *,
    dynamic_authority: Path,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    dynamic_authority = dynamic_authority.resolve()
    attempt_root = dynamic_authority.parent
    ack = _ordinary_stable_json(path.resolve(), "controller stop acknowledgement")
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    cancellation_path = _controller_cancellation_path(attempt_root)
    validate_controller_cancellation(
        cancellation_path,
        dynamic_authority=dynamic_authority,
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
    )
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "cancellation_path",
        "cancellation_sha256",
        "controller_identity",
        "bootstrap_identity",
        "observed_before_phase",
        "stop_acknowledged",
        "formal_work_continuation_authorized",
        "retry_allowed",
        "resume_allowed",
        "formal_result_exists",
        "mathematical_infeasibility_inferred",
        "claim",
        "security_certified",
    }
    if (
        path.resolve() != _controller_cancellation_ack_path(attempt_root)
        or set(ack) != expected_keys
        or ack.get("schema")
        != "rq2_public_grid_highs_formal_controller_cancellation_ack_v7"
        or ack.get("version") != 7
        or any(
            type(ack.get(key)) is not int or ack[key] <= 0
            for key in ("wall_time_ns", "monotonic_ns")
        )
        or ack.get("attempt_root") != str(attempt_root)
        or ack.get("dynamic_authority_path") != str(dynamic_authority)
        or ack.get("dynamic_authority_sha256") != sha256_file(dynamic_authority)
        or ack.get("cancellation_path") != str(cancellation_path)
        or ack.get("cancellation_sha256") != sha256_file(cancellation_path)
        or ack.get("controller_identity") != controller_pair
        or ack.get("bootstrap_identity") != bootstrap_pair
        or not isinstance(ack.get("observed_before_phase"), str)
        or not ack["observed_before_phase"]
        or ack.get("stop_acknowledged") is not True
        or any(
            ack.get(key) is not False
            for key in (
                "formal_work_continuation_authorized",
                "retry_allowed",
                "resume_allowed",
                "formal_result_exists",
                "mathematical_infeasibility_inferred",
                "claim",
                "security_certified",
            )
        )
    ):
        raise FormalActivationRejected(
            "controller stop acknowledgement evidence drifted"
        )
    return ack


def _ordinary_stable_json(path: Path, label: str) -> dict[str, Any]:
    raw, _ = _ordinary_stable_bytes(path, label)
    try:
        return _mapping(json.loads(raw), label)
    except (OSError, json.JSONDecodeError) as exc:
        raise FormalActivationRejected(f"{label} is unreadable") from exc


def _ordinary_file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(metadata.st_ctime_ns),
        int(metadata.st_nlink),
    )


def _open_ordinary_anchored(path: Path, label: str) -> int:
    try:
        return anchored_v3._open_anchored(path)
    except anchored_v3.ActivationRejected as exc:
        raise FormalActivationRejected(f"{label} anchored open failed") from exc


def _close_ordinary_descriptor(
    descriptor: int, label: str, *, primary_error: BaseException | None
) -> None:
    outcome = anchored_v3._close_descriptor_with_recovery(descriptor)
    if outcome.failed:
        failure = anchored_v3._CleanupFailure(
            primary_error=primary_error,
            outcomes=[outcome],
        )
        raise FormalActivationRejected(
            f"{label} descriptor cleanup failed"
        ) from failure


def _ordinary_stable_bytes(path: Path, label: str) -> tuple[bytes, tuple[int, ...]]:
    descriptor = _open_ordinary_anchored(path, label)
    read_error: BaseException | None = None
    try:
        opened = os.fstat(descriptor)
        if opened.st_nlink != 1:
            raise FormalActivationRejected(
                f"{label} must be an ordinary, non-linked file"
            )
        first = anchored_v3._read_all_descriptor(descriptor)
        after_first = os.fstat(descriptor)
        second = anchored_v3._read_all_descriptor(descriptor)
        after_second = os.fstat(descriptor)
    except BaseException as exc:  # noqa: BLE001 - cleanup precedes propagation
        read_error = exc
    _close_ordinary_descriptor(descriptor, label, primary_error=read_error)
    if read_error is not None:
        if isinstance(read_error, OSError):
            raise FormalActivationRejected(f"{label} descriptor read failed") from (
                read_error
            )
        raise read_error

    replay_descriptor = _open_ordinary_anchored(path, label)
    replay_error: BaseException | None = None
    try:
        replay_before = os.fstat(replay_descriptor)
        if replay_before.st_nlink != 1:
            raise FormalActivationRejected(
                f"{label} must be an ordinary, non-linked file"
            )
        replay = anchored_v3._read_all_descriptor(replay_descriptor)
        replay_after = os.fstat(replay_descriptor)
    except BaseException as exc:  # noqa: BLE001 - cleanup precedes propagation
        replay_error = exc
    _close_ordinary_descriptor(replay_descriptor, label, primary_error=replay_error)
    if replay_error is not None:
        if isinstance(replay_error, OSError):
            raise FormalActivationRejected(f"{label} replay read failed") from (
                replay_error
            )
        raise replay_error

    identity = _ordinary_file_identity(opened)
    if (
        first != second
        or first != replay
        or identity != _ordinary_file_identity(after_first)
        or identity != _ordinary_file_identity(after_second)
        or identity != _ordinary_file_identity(replay_before)
        or identity != _ordinary_file_identity(replay_after)
    ):
        raise FormalActivationRejected(f"{label} stable file identity drifted")
    return first, identity


def observe_release_acceptance_authority(
    release_path: Path,
    acceptance_path: Path,
    *,
    validate_release: Callable[[Mapping[str, Any]], dict[str, Any]],
    validate_acceptance: Callable[
        [Mapping[str, Any], Mapping[str, Any]], dict[str, Any]
    ],
) -> dict[str, Any]:
    """Reconstruct release/acceptance solely from stable disk artifacts."""
    release = validate_release(_ordinary_stable_json(release_path, "science release"))
    acceptance: dict[str, Any] | None = None
    acceptance_sha256: str | None = None
    if acceptance_path.is_file() and not acceptance_path.is_symlink():
        raw_acceptance = _ordinary_stable_json(
            acceptance_path, "science release acceptance"
        )
        try:
            acceptance = validate_acceptance(raw_acceptance, release)
            acceptance_sha256 = sha256_file(acceptance_path)
        except BaseException:  # noqa: BLE001 - proof stays false if validation aborts
            acceptance = None
            acceptance_sha256 = None
    return {
        "release": release,
        "release_path": str(release_path),
        "release_sha256": sha256_file(release_path),
        "release_acceptance": acceptance,
        "release_acceptance_path": str(acceptance_path),
        "release_acceptance_sha256": acceptance_sha256,
        "release_acceptance_proven": acceptance is not None,
    }


def _root_observations(
    formal_roots_override: Mapping[str, Path] | None,
) -> dict[str, dict[str, Any]]:
    roots = dict(
        formal_roots_override if formal_roots_override is not None else formal_roots()
    )
    return {name: v4.observe_path(path) for name, path in sorted(roots.items())}


def _validated_protocol_evidence(
    attempt_root: Path,
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    *,
    validated_dynamic: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    attempt_root = attempt_root.resolve()
    release_path = release_path.resolve()
    paths = {key: Path(value) for key, value in startup_paths(attempt_root).items()}
    if release_path != paths["science_release"]:
        raise FormalActivationRejected("release path is outside the exact attempt")
    authority_path = attempt_root / "authority.json"
    if validated_dynamic is None:
        dynamic = validate_dynamic_authority(authority_path)
    else:
        dynamic = dict(validated_dynamic)
        if dynamic != _ordinary_stable_json(
            authority_path, "validated dynamic authority snapshot"
        ):
            raise FormalActivationRejected("dynamic authority snapshot drifted")
    dynamic_bootstrap = _process_identity(
        dynamic.get("bootstrap_identity"), "dynamic bootstrap identity"
    )
    release = _ordinary_stable_json(release_path, "science release")
    controller_identity = _process_identity(
        release.get("controller_identity"), "release controller identity"
    )
    bootstrap_identity = _process_identity(
        release.get("bootstrap_identity"), "release bootstrap identity"
    )
    if bootstrap_identity != dynamic_bootstrap:
        raise FormalActivationRejected("protocol bootstrap identity drifted")
    bindings = startup_bindings(authority_path, validated_dynamic=dynamic)
    command = list(dynamic["exact_command"])
    environment = _mapping(dynamic["exact_environment"], "exact environment")
    handshake = validate_startup_handshake(
        _ordinary_stable_json(paths["handshake"], "startup handshake"),
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        bindings=bindings,
        command=command,
        cwd=str(dynamic["exact_cwd"]),
        environment=environment,
    )
    ack = validate_startup_ack(
        _ordinary_stable_json(paths["bootstrap_ack"], "startup ack"),
        handshake=handshake,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    closure = _mapping(dynamic["execution_closure"], "execution closure")
    closure_sha256 = closure.get("members_sha256")
    if not _is_sha256(closure_sha256):
        raise FormalActivationRejected("dynamic closure binding is malformed")
    authority_mapping_sha256 = canonical_sha256(
        runtime_authority_mapping(authority_path, validated_dynamic=dynamic)
    )
    ready = validate_startup_ready(
        _ordinary_stable_json(paths["startup_ready"], "startup ready"),
        handshake=handshake,
        ack=ack,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        authority_mapping_sha256=authority_mapping_sha256,
        execution_closure_sha256=str(closure_sha256),
    )
    release = validate_science_release(
        release,
        ready=ready,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    acceptance_path = paths["science_release_accepted"]
    acceptance: dict[str, Any] | None = None
    acceptance_sha256: str | None = None
    if acceptance_path.exists():
        observed = _ordinary_stable_json(acceptance_path, "science release acceptance")
        acceptance = validate_science_release_acceptance(
            observed,
            release=release,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            execution_closure_sha256=str(closure_sha256),
        )
        acceptance_sha256 = sha256_file(acceptance_path)
    if release_acceptance is not None and acceptance != dict(release_acceptance):
        raise FormalActivationRejected("release acceptance disk authority drifted")
    return {
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": str(authority_path),
        "dynamic_authority_sha256": sha256_file(authority_path),
        "controller_identity": controller_identity,
        "bootstrap_identity": bootstrap_identity,
        "execution_closure_sha256": closure_sha256,
        "startup_handshake_path": str(paths["handshake"]),
        "startup_handshake_sha256": sha256_file(paths["handshake"]),
        "startup_ack_path": str(paths["bootstrap_ack"]),
        "startup_ack_sha256": sha256_file(paths["bootstrap_ack"]),
        "startup_ready_path": str(paths["startup_ready"]),
        "startup_ready_sha256": sha256_file(paths["startup_ready"]),
        "release_path": str(release_path),
        "release_sha256": sha256_file(release_path),
        "release_payload_sha256": canonical_sha256(release),
        "release": release,
        "release_acceptance_proven": acceptance is not None,
        "release_acceptance_path": str(acceptance_path),
        "release_acceptance_sha256": acceptance_sha256,
        "release_acceptance": acceptance,
        "formal_roots": {
            name: Path(str(root)).resolve()
            for name, root in _mapping(dynamic["formal_roots"], "formal roots").items()
        },
    }


def validate_spawn_receipt_payload(
    receipt: Mapping[str, Any], *, attempt_root: Path
) -> dict[str, Any]:
    """Strictly validate a prospective receipt before immutable publication."""
    receipt = dict(_mapping(receipt, "bootstrap spawn receipt payload"))
    attempt_root = attempt_root.resolve()
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    expected_keys = {
        "schema",
        "version",
        "pid",
        "create_time_ns",
        "bootstrap_identity",
        "returncode",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "command",
        "cwd",
        "environment_sha256",
        "stdout_path",
        "stderr_path",
        "startup_handshake_path",
        "startup_handshake_sha256",
        "startup_ack_path",
        "startup_ack_sha256",
        "startup_ready_path",
        "startup_ready_sha256",
        "science_release_path",
        "science_release_sha256",
        "science_release_accepted_path",
        "science_release_accepted_sha256",
        "release_acceptance_proven",
        "controller_authority_accepted",
        "exact_pid_create_time_verified",
        "formal_controller_spawned",
        "formal_started_at_controller_ready",
        "formal_start_status",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    dynamic_path = attempt_root / "authority.json"
    dynamic = validate_dynamic_authority(dynamic_path)
    controller_identity = _process_identity(
        {"pid": receipt.get("pid"), "create_time_ns": receipt.get("create_time_ns")},
        "spawn receipt controller identity",
    )
    bootstrap_identity = _process_identity(
        receipt.get("bootstrap_identity"), "spawn receipt bootstrap identity"
    )
    acceptance = _ordinary_stable_json(
        paths["science_release_accepted"], "science release acceptance"
    )
    protocol = _validated_protocol_evidence(
        attempt_root,
        paths["science_release"],
        acceptance,
        validated_dynamic=dynamic,
    )
    expected_schema = (
        "rq2_public_grid_highs_formal_activation_spawn_receipt_v7_preseal"
        if str(dynamic["schema"]).endswith("_preseal")
        else "rq2_public_grid_highs_formal_activation_spawn_receipt_v7"
    )
    if (
        set(receipt) != expected_keys
        or receipt.get("schema") != expected_schema
        or receipt.get("version") != 7
        or controller_identity != protocol["controller_identity"]
        or bootstrap_identity != protocol["bootstrap_identity"]
        or receipt.get("returncode") is not None
        or receipt.get("dynamic_authority_path") != str(dynamic_path)
        or receipt.get("dynamic_authority_sha256") != sha256_file(dynamic_path)
        or receipt.get("command") != list(dynamic["exact_command"])
        or receipt.get("cwd") != str(dynamic["exact_cwd"])
        or receipt.get("environment_sha256")
        != canonical_sha256(_mapping(dynamic["exact_environment"], "exact environment"))
        or receipt.get("stdout_path")
        != str((attempt_root / "controller.stdout.log").resolve())
        or receipt.get("stderr_path")
        != str((attempt_root / "controller.stderr.log").resolve())
        or receipt.get("startup_handshake_path") != protocol["startup_handshake_path"]
        or receipt.get("startup_handshake_sha256")
        != protocol["startup_handshake_sha256"]
        or receipt.get("startup_ack_path") != protocol["startup_ack_path"]
        or receipt.get("startup_ack_sha256") != protocol["startup_ack_sha256"]
        or receipt.get("startup_ready_path") != protocol["startup_ready_path"]
        or receipt.get("startup_ready_sha256") != protocol["startup_ready_sha256"]
        or receipt.get("science_release_path") != protocol["release_path"]
        or receipt.get("science_release_sha256") != protocol["release_sha256"]
        or receipt.get("science_release_accepted_path")
        != protocol["release_acceptance_path"]
        or receipt.get("science_release_accepted_sha256")
        != protocol["release_acceptance_sha256"]
        or receipt.get("release_acceptance_proven") is not True
        or receipt.get("controller_authority_accepted") is not True
        or receipt.get("exact_pid_create_time_verified") is not True
        or receipt.get("formal_controller_spawned") is not True
        or receipt.get("formal_started_at_controller_ready") is not False
        or receipt.get("formal_start_status")
        != "released_and_controller_acceptance_proven"
        or any(
            receipt.get(key) is not False
            for key in ("formal_result_exists", "claim", "security_certified")
        )
    ):
        raise FormalActivationRejected("bootstrap spawn receipt evidence drifted")
    return {"receipt": receipt, "protocol": protocol}


def validate_spawn_receipt(path: Path) -> dict[str, Any]:
    """Strictly bind bootstrap supervision to the complete startup protocol."""
    raw, identity = _ordinary_stable_bytes(path, "bootstrap spawn receipt")
    try:
        receipt = _mapping(json.loads(raw), "bootstrap spawn receipt")
    except json.JSONDecodeError as exc:
        raise FormalActivationRejected("bootstrap spawn receipt malformed") from exc
    attempt_root = path.resolve().parent
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    if path.resolve() != paths["spawn_receipt"]:
        raise FormalActivationRejected(
            "spawn receipt path is outside the exact attempt"
        )
    validated = validate_spawn_receipt_payload(receipt, attempt_root=attempt_root)
    digest = hashlib.sha256(raw).hexdigest()
    if canonical_sha256(receipt) != digest:
        raise FormalActivationRejected(
            "bootstrap spawn receipt canonical bytes drifted"
        )
    return {
        "receipt": validated["receipt"],
        "sha256": digest,
        "file_identity": identity,
        "protocol": validated["protocol"],
    }


def lifecycle_decision_path(attempt_root: Path) -> Path:
    return Path(startup_paths(attempt_root.resolve())["lifecycle_decision"])


def _expected_absent_root_observations(
    roots: Mapping[str, Path],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": str(path.resolve()),
            "exists": False,
            "is_directory": False,
            "is_symlink": False,
            "ordinary_file_count": 0,
        }
        for name, path in sorted(roots.items())
    }


def claim_lifecycle_decision(
    attempt_root: Path,
    *,
    lifecycle_class: str,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Atomically choose the only authority allowed to cross into science."""
    classes = set(load_config()["startup_handshake"]["lifecycle_decision_classes"])
    if classes != {"cancelled_before_science", "controller_owned_lifecycle"}:
        raise FormalActivationRejected("lifecycle decision classes drifted")
    if lifecycle_class not in classes:
        raise FormalActivationRejected("lifecycle decision class is not registered")
    attempt_root = attempt_root.resolve()
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    spawn = validate_spawn_receipt(paths["spawn_receipt"])
    protocol = spawn["protocol"]
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    if (
        protocol["controller_identity"] != controller_pair
        or protocol["bootstrap_identity"] != bootstrap_pair
    ):
        raise FormalActivationRejected("lifecycle process identity drifted")
    protocol_roots = protocol["formal_roots"]
    if (
        formal_roots_override is not None
        and {name: path.resolve() for name, path in formal_roots_override.items()}
        != protocol_roots
    ):
        raise FormalActivationRejected("lifecycle formal-root authority drifted")
    observations = _root_observations(protocol_roots)
    expected_absent = _expected_absent_root_observations(protocol_roots)
    if observations != expected_absent:
        raise FormalActivationRejected(
            "formal roots appeared before lifecycle decision"
        )
    controller_owned = lifecycle_class == "controller_owned_lifecycle"
    payload = {
        "schema": "rq2_public_grid_highs_formal_lifecycle_decision_v7",
        "version": 7,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "lifecycle_class": lifecycle_class,
        "requested_by": "controller" if controller_owned else "bootstrap_supervisor",
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": protocol["dynamic_authority_path"],
        "dynamic_authority_sha256": protocol["dynamic_authority_sha256"],
        "controller_identity": controller_pair,
        "bootstrap_identity": bootstrap_pair,
        "execution_closure_sha256": protocol["execution_closure_sha256"],
        "spawn_receipt_path": str(paths["spawn_receipt"]),
        "spawn_receipt_sha256": spawn["sha256"],
        "release_path": protocol["release_path"],
        "release_sha256": protocol["release_sha256"],
        "release_acceptance_path": protocol["release_acceptance_path"],
        "release_acceptance_sha256": protocol["release_acceptance_sha256"],
        "formal_roots": {name: str(path) for name, path in protocol_roots.items()},
        "formal_root_observations_at_decision": observations,
        "science_imported_at_decision": False,
        "formal_root_writes_at_decision": 0,
        "science_import_authorized": controller_owned,
        "formal_root_creation_authorized": controller_owned,
        "terminal_outcome_path": str(paths["terminal_outcome"]),
        "deferred_supervisor_interruption_path": str(
            paths["deferred_supervisor_interruption"]
        ),
        "decision_effect": "irrevocable_after_atomic_commit",
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    path = paths["lifecycle_decision"]
    commit_interrupted = False
    try:
        winner, created = persist_json_exclusive_stable(path, payload)
    except BaseException:
        if not path.is_file():
            raise
        commit_interrupted = True
        created = False
        winner = validate_lifecycle_decision(
            path, formal_roots_override=formal_roots_override
        )["outcome"]
    validated = validate_lifecycle_decision(
        path, formal_roots_override=formal_roots_override
    )
    if validated["outcome"] != winner:
        raise FormalActivationRejected("lifecycle decision winner drifted")
    return {
        "outcome": winner,
        "created": created,
        "requested_lifecycle_class": lifecycle_class,
        "accepted_existing_decision": not created,
        "commit_interrupted_but_disk_authority_reconstructed": commit_interrupted,
        "winner_path": str(path),
        "winner_sha256": validated["sha256"],
    }


def validate_lifecycle_decision(
    path: Path,
    *,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    raw, identity = _ordinary_stable_bytes(path, "lifecycle decision")
    try:
        decision = _mapping(json.loads(raw), "lifecycle decision")
    except json.JSONDecodeError as exc:
        raise FormalActivationRejected("lifecycle decision malformed") from exc
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "lifecycle_class",
        "requested_by",
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "controller_identity",
        "bootstrap_identity",
        "execution_closure_sha256",
        "spawn_receipt_path",
        "spawn_receipt_sha256",
        "release_path",
        "release_sha256",
        "release_acceptance_path",
        "release_acceptance_sha256",
        "formal_roots",
        "formal_root_observations_at_decision",
        "science_imported_at_decision",
        "formal_root_writes_at_decision",
        "science_import_authorized",
        "formal_root_creation_authorized",
        "terminal_outcome_path",
        "deferred_supervisor_interruption_path",
        "decision_effect",
        "retry_allowed",
        "resume_allowed",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    attempt_root = path.resolve().parent
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    if path.resolve() != paths["lifecycle_decision"]:
        raise FormalActivationRejected(
            "lifecycle decision path is outside exact attempt"
        )
    lifecycle_class = decision.get("lifecycle_class")
    controller_owned = lifecycle_class == "controller_owned_lifecycle"
    if (
        set(decision) != expected_keys
        or decision.get("schema")
        != "rq2_public_grid_highs_formal_lifecycle_decision_v7"
        or decision.get("version") != 7
        or lifecycle_class
        not in {"cancelled_before_science", "controller_owned_lifecycle"}
        or any(
            type(decision.get(key)) is not int or decision[key] <= 0
            for key in ("wall_time_ns", "monotonic_ns")
        )
        or decision.get("requested_by")
        != ("controller" if controller_owned else "bootstrap_supervisor")
        or decision.get("attempt_root") != str(attempt_root)
        or decision.get("science_imported_at_decision") is not False
        or decision.get("formal_root_writes_at_decision") != 0
        or decision.get("science_import_authorized") is not controller_owned
        or decision.get("formal_root_creation_authorized") is not controller_owned
        or decision.get("terminal_outcome_path") != str(paths["terminal_outcome"])
        or decision.get("deferred_supervisor_interruption_path")
        != str(paths["deferred_supervisor_interruption"])
        or decision.get("decision_effect") != "irrevocable_after_atomic_commit"
        or any(
            decision.get(key) is not False
            for key in (
                "retry_allowed",
                "resume_allowed",
                "formal_result_exists",
                "claim",
                "security_certified",
            )
        )
    ):
        raise FormalActivationRejected("lifecycle decision common evidence drifted")
    spawn = validate_spawn_receipt(Path(str(decision["spawn_receipt_path"])))
    protocol = spawn["protocol"]
    protocol_roots = protocol["formal_roots"]
    if (
        formal_roots_override is not None
        and {name: root.resolve() for name, root in formal_roots_override.items()}
        != protocol_roots
    ):
        raise FormalActivationRejected("lifecycle formal-root authority drifted")
    expected = {
        "dynamic_authority_path": protocol["dynamic_authority_path"],
        "dynamic_authority_sha256": protocol["dynamic_authority_sha256"],
        "controller_identity": protocol["controller_identity"],
        "bootstrap_identity": protocol["bootstrap_identity"],
        "execution_closure_sha256": protocol["execution_closure_sha256"],
        "spawn_receipt_path": str(paths["spawn_receipt"]),
        "spawn_receipt_sha256": spawn["sha256"],
        "release_path": protocol["release_path"],
        "release_sha256": protocol["release_sha256"],
        "release_acceptance_path": protocol["release_acceptance_path"],
        "release_acceptance_sha256": protocol["release_acceptance_sha256"],
        "formal_roots": {name: str(root) for name, root in protocol_roots.items()},
        "formal_root_observations_at_decision": _expected_absent_root_observations(
            protocol_roots
        ),
    }
    if any(decision.get(key) != value for key, value in expected.items()):
        raise FormalActivationRejected("lifecycle decision protocol evidence drifted")
    digest = hashlib.sha256(raw).hexdigest()
    if canonical_sha256(decision) != digest:
        raise FormalActivationRejected("lifecycle decision canonical bytes drifted")
    return {"outcome": decision, "sha256": digest, "file_identity": identity}


def persist_deferred_supervisor_interruption(
    attempt_root: Path,
    *,
    exception: BaseException,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Persist why bootstrap supervision must outlive its interrupted call."""
    attempt_root = attempt_root.resolve()
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    decision = validate_lifecycle_decision(
        paths["lifecycle_decision"], formal_roots_override=formal_roots_override
    )
    outcome = decision["outcome"]
    if outcome["lifecycle_class"] != "controller_owned_lifecycle":
        raise FormalActivationRejected(
            "deferred supervisor interruption requires controller lifecycle authority"
        )
    payload = {
        "schema": "rq2_public_grid_highs_formal_deferred_supervisor_interruption_v7",
        "version": 7,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": outcome["dynamic_authority_path"],
        "dynamic_authority_sha256": outcome["dynamic_authority_sha256"],
        "controller_identity": outcome["controller_identity"],
        "bootstrap_identity": outcome["bootstrap_identity"],
        "lifecycle_decision_path": str(paths["lifecycle_decision"]),
        "lifecycle_decision_sha256": decision["sha256"],
        "lifecycle_class": "controller_owned_lifecycle",
        "spawn_receipt_path": outcome["spawn_receipt_path"],
        "spawn_receipt_sha256": outcome["spawn_receipt_sha256"],
        "release_path": outcome["release_path"],
        "release_sha256": outcome["release_sha256"],
        "release_acceptance_path": outcome["release_acceptance_path"],
        "release_acceptance_sha256": outcome["release_acceptance_sha256"],
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        "supervision_state": "deferred_until_authoritative_controller_terminal",
        "conflicting_cancellation_forbidden": True,
        "conflicting_bootstrap_unresolved_forbidden": True,
        "controller_termination_forbidden": True,
        "terminal_outcome_path": str(paths["terminal_outcome"]),
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    path = paths["deferred_supervisor_interruption"]
    try:
        persisted, _ = persist_json_exclusive_stable(path, payload)
    except BaseException:
        if not path.is_file():
            raise
        persisted = validate_deferred_supervisor_interruption(
            path, formal_roots_override=formal_roots_override
        )["interruption"]
    validated = validate_deferred_supervisor_interruption(
        path, formal_roots_override=formal_roots_override
    )
    if persisted != validated["interruption"]:
        raise FormalActivationRejected("deferred interruption winner drifted")
    return validated["interruption"]


def validate_deferred_supervisor_interruption(
    path: Path,
    *,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    raw, identity = _ordinary_stable_bytes(path, "deferred supervisor interruption")
    try:
        interruption = _mapping(json.loads(raw), "deferred supervisor interruption")
    except json.JSONDecodeError as exc:
        raise FormalActivationRejected(
            "deferred supervisor interruption malformed"
        ) from exc
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "controller_identity",
        "bootstrap_identity",
        "lifecycle_decision_path",
        "lifecycle_decision_sha256",
        "lifecycle_class",
        "spawn_receipt_path",
        "spawn_receipt_sha256",
        "release_path",
        "release_sha256",
        "release_acceptance_path",
        "release_acceptance_sha256",
        "exception_type",
        "exception_message",
        "supervision_state",
        "conflicting_cancellation_forbidden",
        "conflicting_bootstrap_unresolved_forbidden",
        "controller_termination_forbidden",
        "terminal_outcome_path",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    attempt_root = path.resolve().parent
    paths = {name: Path(value) for name, value in startup_paths(attempt_root).items()}
    if path.resolve() != paths["deferred_supervisor_interruption"]:
        raise FormalActivationRejected(
            "deferred interruption path is outside exact attempt"
        )
    decision = validate_lifecycle_decision(
        paths["lifecycle_decision"], formal_roots_override=formal_roots_override
    )
    outcome = decision["outcome"]
    expected = {
        "attempt_root": str(attempt_root),
        "dynamic_authority_path": outcome["dynamic_authority_path"],
        "dynamic_authority_sha256": outcome["dynamic_authority_sha256"],
        "controller_identity": outcome["controller_identity"],
        "bootstrap_identity": outcome["bootstrap_identity"],
        "lifecycle_decision_path": str(paths["lifecycle_decision"]),
        "lifecycle_decision_sha256": decision["sha256"],
        "lifecycle_class": "controller_owned_lifecycle",
        "spawn_receipt_path": outcome["spawn_receipt_path"],
        "spawn_receipt_sha256": outcome["spawn_receipt_sha256"],
        "release_path": outcome["release_path"],
        "release_sha256": outcome["release_sha256"],
        "release_acceptance_path": outcome["release_acceptance_path"],
        "release_acceptance_sha256": outcome["release_acceptance_sha256"],
        "terminal_outcome_path": str(paths["terminal_outcome"]),
    }
    if (
        set(interruption) != expected_keys
        or interruption.get("schema")
        != "rq2_public_grid_highs_formal_deferred_supervisor_interruption_v7"
        or interruption.get("version") != 7
        or any(
            type(interruption.get(key)) is not int or interruption[key] <= 0
            for key in ("wall_time_ns", "monotonic_ns")
        )
        or outcome["lifecycle_class"] != "controller_owned_lifecycle"
        or any(interruption.get(key) != value for key, value in expected.items())
        or not isinstance(interruption.get("exception_type"), str)
        or not interruption["exception_type"]
        or not isinstance(interruption.get("exception_message"), str)
        or interruption.get("supervision_state")
        != "deferred_until_authoritative_controller_terminal"
        or any(
            interruption.get(key) is not True
            for key in (
                "conflicting_cancellation_forbidden",
                "conflicting_bootstrap_unresolved_forbidden",
                "controller_termination_forbidden",
            )
        )
        or any(
            interruption.get(key) is not False
            for key in ("formal_result_exists", "claim", "security_certified")
        )
    ):
        raise FormalActivationRejected("deferred interruption evidence drifted")
    digest = hashlib.sha256(raw).hexdigest()
    if canonical_sha256(interruption) != digest:
        raise FormalActivationRejected("deferred interruption canonical bytes drifted")
    return {
        "interruption": interruption,
        "sha256": digest,
        "file_identity": identity,
    }


def _persist_terminal_outcome(
    attempt_root: Path,
    *,
    terminal_class: str,
    controller_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    class_evidence: Mapping[str, Any],
    formal_roots_override: Mapping[str, Path] | None,
) -> dict[str, Any]:
    if terminal_class not in {"success", "unresolved"}:
        raise FormalActivationRejected("terminal class is not registered")
    pair = _process_identity(controller_identity, "terminal controller identity")
    attempt_root = attempt_root.resolve()
    protocol = _validated_protocol_evidence(
        attempt_root, release_path, release_acceptance
    )
    if protocol["controller_identity"] != pair:
        raise FormalActivationRejected("terminal controller identity drifted")
    protocol_roots = protocol["formal_roots"]
    if (
        formal_roots_override is not None
        and {name: path.resolve() for name, path in formal_roots_override.items()}
        != protocol_roots
    ):
        raise FormalActivationRejected("terminal formal-root authority drifted")
    roots = _root_observations(protocol_roots)
    class_fields = dict(class_evidence)
    reserved = {
        "schema",
        "version",
        "terminal_class",
        "controller_identity",
        "bootstrap_identity",
        "release_path",
        "release_sha256",
        "formal_result_exists",
        "mathematical_infeasibility_inferred",
        "claim",
        "security_certified",
    }
    if reserved & set(class_fields):
        raise FormalActivationRejected("terminal class evidence shadows authority")
    payload = {
        "schema": "rq2_public_grid_highs_formal_authoritative_terminal_outcome_v7",
        "version": 7,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "terminal_class": terminal_class,
        "attempt_root": protocol["attempt_root"],
        "dynamic_authority_path": protocol["dynamic_authority_path"],
        "dynamic_authority_sha256": protocol["dynamic_authority_sha256"],
        "controller_identity": pair,
        "bootstrap_identity": protocol["bootstrap_identity"],
        "execution_closure_sha256": protocol["execution_closure_sha256"],
        "startup_handshake_path": protocol["startup_handshake_path"],
        "startup_handshake_sha256": protocol["startup_handshake_sha256"],
        "startup_ack_path": protocol["startup_ack_path"],
        "startup_ack_sha256": protocol["startup_ack_sha256"],
        "startup_ready_path": protocol["startup_ready_path"],
        "startup_ready_sha256": protocol["startup_ready_sha256"],
        "release_path": protocol["release_path"],
        "release_sha256": protocol["release_sha256"],
        "release_payload_sha256": protocol["release_payload_sha256"],
        "release": protocol["release"],
        "release_acceptance_proven": protocol["release_acceptance_proven"],
        "release_acceptance_path": protocol["release_acceptance_path"],
        "release_acceptance_sha256": protocol["release_acceptance_sha256"],
        "release_acceptance": protocol["release_acceptance"],
        "class_evidence": dict(class_evidence),
        **class_fields,
        "formal_root_observations": roots,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    path = terminal_outcome_path(attempt_root)
    commit_interrupted = False
    try:
        winner, created = persist_json_exclusive_stable(path, payload)
    except BaseException:
        if not path.is_file():
            raise
        commit_interrupted = True
        created = False
        winner = validate_terminal_outcome(
            path, formal_roots_override=formal_roots_override
        )["outcome"]
    validated = validate_terminal_outcome(
        path, formal_roots_override=formal_roots_override
    )
    if (
        validated["outcome"] != winner
        or winner.get("controller_identity") != pair
        or winner.get("release_path") != protocol["release_path"]
        or winner.get("release_sha256") != protocol["release_sha256"]
        or winner.get("execution_closure_sha256")
        != protocol["execution_closure_sha256"]
    ):
        raise FormalActivationRejected("authoritative terminal winner drifted")
    return {
        "outcome": winner,
        "created": created,
        "requested_terminal_class": terminal_class,
        "accepted_existing_decision": not created,
        "commit_interrupted_but_disk_authority_reconstructed": commit_interrupted,
        "winner_path": str(path),
        "winner_sha256": validated["sha256"],
    }


def persist_post_release_unresolved(
    attempt_root: Path,
    *,
    reason: str,
    reporter: str,
    controller_identity: Mapping[str, int] | None,
    returncode: int | None,
    termination: Mapping[str, Any],
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    if controller_identity is None:
        raise FormalActivationRejected(
            "post-release terminal decision requires exact controller identity"
        )
    termination_value = _mapping(termination, "termination evidence")
    normalized_termination = {
        "attempted": termination_value.get("attempted"),
        "reason": termination_value.get("reason"),
        "returncode": termination_value.get("returncode", returncode),
    }
    if (
        type(normalized_termination["attempted"]) is not bool
        or not isinstance(normalized_termination["reason"], str)
        or set(termination_value) - {"attempted", "reason", "returncode"}
    ):
        raise FormalActivationRejected("termination evidence drifted")
    return _persist_terminal_outcome(
        attempt_root,
        terminal_class="unresolved",
        controller_identity=controller_identity,
        release_path=release_path,
        release_acceptance=release_acceptance,
        class_evidence={
            "reason": reason,
            "reporter": reporter,
            "controller_returncode": returncode,
            "termination": normalized_termination,
            "formal_started": None,
            "formal_start_status": "unresolved_after_science_release",
        },
        formal_roots_override=formal_roots_override,
    )


def persist_controller_terminal_success(
    attempt_root: Path,
    *,
    controller_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any],
    result: Mapping[str, Any],
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    return _persist_terminal_outcome(
        attempt_root,
        terminal_class="success",
        controller_identity=controller_identity,
        release_path=release_path,
        release_acceptance=release_acceptance,
        class_evidence={
            "controller_terminal_status": "completed_without_controller_exception",
            "result_sha256": canonical_sha256(result),
        },
        formal_roots_override=formal_roots_override,
    )


def load_terminal_outcome(attempt_root: Path) -> dict[str, Any]:
    return validate_terminal_outcome(terminal_outcome_path(attempt_root))["outcome"]


def validate_terminal_outcome(
    path: Path,
    *,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    raw, identity = _ordinary_stable_bytes(path, "authoritative terminal outcome")
    try:
        outcome = _mapping(json.loads(raw), "authoritative terminal outcome")
    except json.JSONDecodeError as exc:
        raise FormalActivationRejected(
            "authoritative terminal outcome malformed"
        ) from exc
    terminal_class = outcome.get("terminal_class")
    common = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "terminal_class",
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "controller_identity",
        "bootstrap_identity",
        "execution_closure_sha256",
        "startup_handshake_path",
        "startup_handshake_sha256",
        "startup_ack_path",
        "startup_ack_sha256",
        "startup_ready_path",
        "startup_ready_sha256",
        "release_path",
        "release_sha256",
        "release_payload_sha256",
        "release",
        "release_acceptance_proven",
        "release_acceptance_path",
        "release_acceptance_sha256",
        "release_acceptance",
        "class_evidence",
        "formal_root_observations",
        "retry_allowed",
        "resume_allowed",
        "formal_result_exists",
        "mathematical_infeasibility_inferred",
        "claim",
        "security_certified",
    }
    class_keys = {
        "success": {"controller_terminal_status", "result_sha256"},
        "unresolved": {
            "reason",
            "reporter",
            "controller_returncode",
            "termination",
            "formal_started",
            "formal_start_status",
        },
    }
    if outcome.get("attempt_root") != str(path.resolve().parent):
        raise FormalActivationRejected("terminal attempt path drifted")
    if (
        terminal_class not in class_keys
        or set(outcome) != common | class_keys[terminal_class]
    ):
        raise FormalActivationRejected("terminal exact-key contract drifted")
    if (
        outcome.get("schema")
        != "rq2_public_grid_highs_formal_authoritative_terminal_outcome_v7"
        or outcome.get("version") != 7
        or any(
            type(outcome.get(key)) is not int or outcome[key] <= 0
            for key in ("wall_time_ns", "monotonic_ns")
        )
        or not _is_sha256(outcome.get("execution_closure_sha256"))
        or any(
            outcome.get(key) is not False
            for key in (
                "retry_allowed",
                "resume_allowed",
                "formal_result_exists",
                "mathematical_infeasibility_inferred",
                "claim",
                "security_certified",
            )
        )
        or _mapping(outcome.get("class_evidence"), "terminal class evidence")
        != {key: outcome[key] for key in class_keys[terminal_class]}
    ):
        raise FormalActivationRejected("terminal common evidence drifted")
    protocol = _validated_protocol_evidence(
        path.resolve().parent,
        Path(str(outcome["release_path"])),
        outcome.get("release_acceptance"),
    )
    if outcome.get("release_acceptance_proven") is False:
        # A valid controller acceptance may be committed after the unresolved
        # envelope wins.  Validate that late artifact above, but preserve the
        # conservative proof frozen at the authoritative decision instant.
        protocol["release_acceptance_proven"] = False
        protocol["release_acceptance_sha256"] = None
        protocol["release_acceptance"] = None
    for key in (
        "attempt_root",
        "dynamic_authority_path",
        "dynamic_authority_sha256",
        "controller_identity",
        "bootstrap_identity",
        "execution_closure_sha256",
        "startup_handshake_path",
        "startup_handshake_sha256",
        "startup_ack_path",
        "startup_ack_sha256",
        "startup_ready_path",
        "startup_ready_sha256",
        "release_path",
        "release_sha256",
        "release_payload_sha256",
        "release",
        "release_acceptance_proven",
        "release_acceptance_path",
        "release_acceptance_sha256",
        "release_acceptance",
    ):
        if outcome.get(key) != protocol.get(key):
            raise FormalActivationRejected(f"terminal protocol evidence drifted: {key}")
    roots = _mapping(outcome.get("formal_root_observations"), "terminal roots")
    protocol_roots = protocol["formal_roots"]
    if (
        formal_roots_override is not None
        and {name: root.resolve() for name, root in formal_roots_override.items()}
        != protocol_roots
    ):
        raise FormalActivationRejected("terminal formal-root authority drifted")
    expected_roots = _root_observations(protocol_roots)
    if roots != expected_roots:
        raise FormalActivationRejected("terminal formal-root observations drifted")
    if terminal_class == "success":
        if (
            outcome.get("release_acceptance_proven") is not True
            or outcome.get("controller_terminal_status")
            != "completed_without_controller_exception"
            or not _is_sha256(outcome.get("result_sha256"))
        ):
            raise FormalActivationRejected("terminal success evidence drifted")
    else:
        termination = _mapping(outcome.get("termination"), "termination evidence")
        if (
            set(termination) != {"attempted", "reason", "returncode"}
            or type(termination.get("attempted")) is not bool
            or not isinstance(termination.get("reason"), str)
            or not isinstance(outcome.get("reason"), str)
            or outcome.get("reporter") not in {"bootstrap_supervisor", "controller"}
            or outcome.get("formal_started") is not None
            or outcome.get("formal_start_status") != "unresolved_after_science_release"
        ):
            raise FormalActivationRejected("terminal unresolved evidence drifted")
    digest = hashlib.sha256(raw).hexdigest()
    if canonical_sha256(outcome) != digest:
        raise FormalActivationRejected("terminal canonical bytes drifted")
    return {"outcome": outcome, "sha256": digest, "file_identity": identity}


def require_sealed_for_execution() -> dict[str, Any]:
    config = load_config()
    if config.get("status") != "SEALED_READY_FOR_INDEPENDENT_REVIEW":
        raise FormalActivationRejected(
            "V7 is a non-authoritative draft; preflight, consume, spawn, and formal run are forbidden"
        )
    validate_formal_config()
    closure = verify_execution_closure(require_frozen_expected=True)
    return _verify_sealed_bundle(validated_closure=closure)


def validate_only() -> dict[str, Any]:
    config = load_config()
    validate_formal_config()
    validate_runtime_files(config)
    if sha256_file(PREDECESSOR_OUTER) != PREDECESSOR_OUTER_SHA256:
        raise FormalActivationRejected("V4 predecessor outer drifted")
    if sha256_file(PREDECESSOR_CLOSURE) != PREDECESSOR_CLOSURE_SHA256:
        raise FormalActivationRejected("V4 predecessor closure drifted")
    if sha256_file(PREDECESSOR_ESCALATE) != PREDECESSOR_ESCALATE_SHA256:
        raise FormalActivationRejected("V4 ESCALATE receipt drifted")
    if sha256_file(SEALED_PREDECESSOR_OUTER) != SEALED_PREDECESSOR_OUTER_SHA256:
        raise FormalActivationRejected("sealed V6 predecessor outer drifted")
    if sha256_file(SEALED_PREDECESSOR_CLOSURE) != SEALED_PREDECESSOR_CLOSURE_SHA256:
        raise FormalActivationRejected("sealed V6 predecessor closure drifted")
    if (
        sha256_file(SEALED_PREDECESSOR_FORMAL_CONFIG)
        != SEALED_PREDECESSOR_FORMAL_CONFIG_SHA256
    ):
        raise FormalActivationRejected("sealed V6 predecessor formal config drifted")
    if sha256_file(SEALED_PREDECESSOR_ESCALATE) != SEALED_PREDECESSOR_ESCALATE_SHA256:
        raise FormalActivationRejected("sealed V6 ESCALATE receipt drifted")
    closure = v4.verify_execution_closure()
    if closure.get("member_count") != 77:
        raise FormalActivationRejected("V4 77-file closure semantics drifted")
    draft = config["status"] == "DRAFT_NONAUTHORITATIVE"
    production_paths = production_artifact_paths()
    if draft and production_paths:
        raise FormalActivationRejected(
            "draft unexpectedly declares production artifacts"
        )
    if not draft:
        closure_v7 = verify_execution_closure(require_frozen_expected=True)
        _verify_sealed_bundle(validated_closure=closure_v7)
        _verify_fresh_one_shot_authority()
    existing_roots = [name for name, path in formal_roots().items() if path.exists()]
    if _entry_exists(activation_audit_root()) or existing_roots:
        raise FormalActivationRejected("V7 formal roots must remain absent")
    return {
        "schema": (
            "rq2_public_grid_highs_formal_activation_v7_draft_validation"
            if draft
            else "rq2_public_grid_highs_formal_activation_v7_sealed_validation"
        ),
        "status": config["status"],
        "predecessor_v4_outer_sha256": PREDECESSOR_OUTER_SHA256,
        "predecessor_v4_closure_member_count": closure["member_count"],
        "sealed_predecessor_v6_outer_sha256": SEALED_PREDECESSOR_OUTER_SHA256,
        "sealed_predecessor_v6_closure_sha256": SEALED_PREDECESSOR_CLOSURE_SHA256,
        "sealed_predecessor_v6_escalate_sha256": SEALED_PREDECESSOR_ESCALATE_SHA256,
        "production_artifact_count": len(production_paths),
        "formal_config_sha256": sha256_file(FORMAL_CONFIG),
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_root_writes": 0,
    }
