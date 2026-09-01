"""Fail-closed contract for the block-zero HiGHS formal activation successor."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_v1.json"
FORMAL_CONFIG = (
    ROOT
    / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v2.yaml"
)
INNER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v1.SHA256SUMS.json"
)
OUTER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v1.OUTER.SHA256SUMS.json"
)
POST_RESULT_PASS = (
    ROOT
    / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_post_result_review_pass_v8.json"
)
ACTIVATION_REVIEW_PASS = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_review_pass_v1.json"
)
GIB = 1024**3
PREFLIGHT_THRESHOLD_BYTES = 10 * GIB
CHILD_PRIVATE_COMMIT_STOP_BYTES = 8 * GIB
SYSTEM_COMMIT_AVAILABLE_STOP_BYTES = 2 * GIB


class FormalActivationRejected(RuntimeError):
    """The successor cannot prove a required activation invariant."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FormalActivationRejected(f"{label} must be a mapping")
    return dict(value)


def _repo_path(raw: object, label: str) -> Path:
    if (
        not isinstance(raw, str)
        or not raw
        or Path(raw).is_absolute()
        or ".." in Path(raw).parts
    ):
        raise FormalActivationRejected(f"{label} must be repository-relative")
    return ROOT / Path(raw)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FormalActivationRejected(f"{label} is not an ordinary file")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise FormalActivationRejected(f"{label} is unreadable") from exc
    return _mapping(value, label)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FormalActivationRejected(f"{label} is not an ordinary file")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FormalActivationRejected(f"{label} is unreadable") from exc
    return _mapping(value, label)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_stable(path: Path) -> bytes:
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise FormalActivationRejected(f"stable readback drifted: {path}")
    return first


def verify_file_binding(path: Path, expected: object, *, label: str) -> str:
    if not _is_sha256(expected):
        raise FormalActivationRejected(f"{label} expected hash is malformed")
    if not path.is_file() or path.is_symlink() or sha256_file(path) != expected:
        raise FormalActivationRejected(f"{label} drifted")
    return str(expected)


def load_config() -> dict[str, Any]:
    config = _load_json(CONFIG, "formal activation config")
    if (
        config.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v1"
        or config.get("version") != 1
        or config.get("status")
        != "READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW"
        or config.get("gates", {}).get(
            "formal_activation_successor_implementation_complete"
        )
        is not True
    ):
        raise FormalActivationRejected("formal activation config identity drifted")
    return config


def _verify_sealed_bundle() -> None:
    inner = _load_json(INNER, "formal activation inner manifest")
    outer = _load_json(OUTER, "formal activation outer manifest")
    members = _mapping(inner.get("members"), "formal activation members")
    if (
        inner.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v1_inner"
        or inner.get("version") != 1
        or outer
        != {
            "schema": (
                "rq2_public_grid_highs_formal_activation_successor_v1_outer"
            ),
            "version": 1,
            "inner": {
                "path": INNER.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(INNER),
            },
        }
    ):
        raise FormalActivationRejected("formal activation bundle drifted")
    for raw, expected in members.items():
        verify_file_binding(_repo_path(raw, raw), expected, label=raw)


def _verify_fresh_one_shot_authority() -> None:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    consumed = _repo_path(lease["consumed_path"], "consumed authority")
    verify_file_binding(fresh, lease["fresh_sha256"], label="fresh authority")
    value = _load_json(fresh, "fresh one-shot authority")
    if (
        consumed.exists()
        or value.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v1_one_shot_authority"
        or value.get("version") != 1
        or value.get("authority_id") != lease["authority_id"]
        or value.get("state") != "fresh"
        or value.get("one_shot") is not True
        or value.get("formal_execution_authorized") is not False
        or value.get("security_certified") is not False
    ):
        raise FormalActivationRejected("fresh one-shot authority drifted")


def formal_roots() -> dict[str, Path]:
    paths = _mapping(load_config()["paths"], "formal paths")
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
    return _repo_path(load_config()["paths"]["activation_audit_root"], "audit root")


def _verify_checkpoint_inventory(value: Mapping[str, Any]) -> None:
    directory = _repo_path(value.get("directory"), "protected checkpoint directory")
    files = _mapping(value.get("files"), "protected checkpoint files")
    observed = {
        path.name: sha256_file(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and not path.is_symlink()
    }
    if observed != files or value.get("count") != len(files):
        raise FormalActivationRejected("protected checkpoint inventory drifted")
    rows = [f"{name}:{files[name]}" for name in sorted(files)]
    aggregate = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    if aggregate != value.get("inventory_sha256"):
        raise FormalActivationRejected("protected checkpoint aggregate drifted")


def _verify_reviewed_v8_receipt() -> dict[str, Any]:
    receipt = _load_json(POST_RESULT_PASS, "V8 post-result PASS receipt")
    if (
        receipt.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_post_result_review_pass_v8"
        or receipt.get("reviewed_on") != "2026-09-01"
        or receipt.get("reviewer_agent") != "/root/pilot_post_result_review"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or receipt.get("findings") != []
        or receipt.get("materialized_from_review_report") is not True
        or receipt.get("cryptographic_reviewer_signature_present") is not False
    ):
        raise FormalActivationRejected("V8 post-result PASS receipt drifted")
    bindings = [receipt["reviewed_v8_outer"], receipt["pre_run_review_pass"]]
    reviewed = _mapping(receipt["reviewed_result"], "reviewed result")
    bindings.extend(
        reviewed[name]
        for name in (
            "result_manifest",
            "result_tree",
            "published_tree",
            "published_success",
            "controller_receipt",
            "controller_attestation",
            "secret_free_tombstone",
        )
    )
    protected = _mapping(receipt["protected_formal_artifacts"], "protected formal")
    bindings.extend(
        protected[name]
        for name in (
            "base_science_runner",
            "process_isolated_predecessor_runner",
            "original_highs_candidate_config",
            "existing_activated_gurobi_config",
        )
    )
    for binding in bindings:
        item = _mapping(binding, "review binding")
        verify_file_binding(
            _repo_path(item.get("path"), "review binding path"),
            item.get("sha256"),
            label=str(item.get("path")),
        )
    tombstone = _mapping(reviewed["secret_free_tombstone"], "V8 tombstone")
    tombstone_value = _load_json(
        _repo_path(tombstone["path"], "V8 tombstone path"), "V8 tombstone"
    )
    if (
        tombstone.get("seed_present") is not False
        or tombstone.get("one_time_key_reusable") is not False
        or tombstone_value.get("seed_present") is not False
        or tombstone_value.get("one_time_key_reusable") is not False
    ):
        raise FormalActivationRejected("V8 tombstone is not secret-free/nonreusable")
    result_manifest = _load_json(
        _repo_path(reviewed["result_manifest"]["path"], "result manifest path"),
        "V8 result manifest",
    )
    attestation = _load_json(
        _repo_path(
            reviewed["controller_attestation"]["path"], "attestation path"
        ),
        "V8 controller attestation",
    )
    if (
        result_manifest.get("nonformal") is not True
        or result_manifest.get("claim") is not False
        or result_manifest.get("security_certified") is not False
        or result_manifest.get("controller_attestation_payload_sha256")
        != reviewed.get("lamport_attestation_payload_sha256")
        or result_manifest.get("controller_signature_sha256")
        != reviewed.get("lamport_signature_sha256")
        or attestation.get("payload_sha256")
        != reviewed.get("lamport_attestation_payload_sha256")
        or attestation.get("signature_sha256")
        != reviewed.get("lamport_signature_sha256")
    ):
        raise FormalActivationRejected("V8 Lamport/result binding drifted")
    _verify_checkpoint_inventory(protected["existing_gurobi_checkpoint_inventory"])
    effect = _mapping(receipt["effect"], "post-result effect")
    expected_effect = {
        "v8_post_result_independent_review_passed": True,
        "opens_formal_activation_successor_review_only": True,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    if effect != expected_effect:
        raise FormalActivationRejected("V8 post-result review effect drifted")
    return receipt


def _verify_formal_science_config(config: Mapping[str, Any]) -> dict[str, Any]:
    science = _mapping(config["formal_science"], "formal science")
    verify_file_binding(
        FORMAL_CONFIG, science["formal_config_sha256"], label="formal science config"
    )
    formal = _load_yaml(FORMAL_CONFIG, "formal science config")
    predecessor = _load_yaml(
        _repo_path(
            science["original_highs_candidate_config_path"], "original candidate"
        ),
        "original HiGHS candidate",
    )
    expected_solver = dict(_mapping(formal["solver"], "formal solver"))
    expected_solver["expected_runtime_api_version"] = "1.15.1"
    for key in ("input", "grid_source", "model", "solver", "provenance"):
        if formal.get(key) != predecessor.get(key):
            raise FormalActivationRejected(f"formal science section drifted: {key}")
    execution = _mapping(formal["execution"], "formal execution")
    process = _mapping(execution["process_isolation"], "formal process isolation")
    if (
        formal.get("schema")
        != "rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v2"
        or execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not False
        or execution.get("starts_from_block_zero") is not True
        or execution.get("resume_allowed") is not False
        or execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is not False
        or execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
        or process.get("expected_block_count") != 1071
        or process.get("starts_from_block_zero") is not True
        or process.get("resume_allowed") is not False
        or process.get("resource_sample_interval_seconds") != 5.0
        or process.get("observation_jitter_budget_seconds") != 1.0
        or process.get("maximum_detection_overrun_seconds") != 1.0
        or process.get("owned_termination_grace_seconds") != 2.0
        or process.get("private_commit_limit_gib") != 8.0
        or process.get("minimum_system_commit_available_gib") != 2.0
        or process.get("external_watchdog_seconds") != 21600
        or process.get("two_block_full_process_pilot_post_result_passed") is not True
        or process.get("timeout_or_failure_is_mathematical_infeasibility") is not False
        or science.get("solver") != expected_solver
    ):
        raise FormalActivationRejected("formal process/science gate drifted")
    return formal


def static_authority_mapping() -> dict[str, str]:
    config = load_config()
    mapping: dict[str, str] = {
        CONFIG.relative_to(ROOT).as_posix(): sha256_file(CONFIG),
        POST_RESULT_PASS.relative_to(ROOT).as_posix(): sha256_file(POST_RESULT_PASS),
        FORMAL_CONFIG.relative_to(ROOT).as_posix(): sha256_file(FORMAL_CONFIG),
    }
    if INNER.is_file() and OUTER.is_file():
        mapping[INNER.relative_to(ROOT).as_posix()] = sha256_file(INNER)
        mapping[OUTER.relative_to(ROOT).as_posix()] = sha256_file(OUTER)
    for section_name in ("v8_evidence_authority",):
        for item in _mapping(config[section_name], section_name).values():
            binding = _mapping(item, "static V8 binding")
            mapping[str(binding["path"])] = str(binding["sha256"])
    science = _mapping(config["formal_science"], "formal science")
    for path_key, hash_key in (
        ("base_science_runner_path", "base_science_runner_sha256"),
        (
            "process_isolated_predecessor_runner_path",
            "process_isolated_predecessor_runner_sha256",
        ),
        ("original_highs_candidate_config_path", "original_highs_candidate_config_sha256"),
    ):
        mapping[str(science[path_key])] = str(science[hash_key])
    predecessor = _mapping(config["protected_predecessor_state"], "predecessor")
    mapping[str(predecessor["existing_activated_gurobi_config_path"])] = str(
        predecessor["existing_activated_gurobi_config_sha256"]
    )
    return dict(sorted(mapping.items()))


def preflight_authority_mapping() -> dict[str, str]:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    mapping = dict(static_authority_mapping())
    mapping[ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()] = sha256_file(
        ACTIVATION_REVIEW_PASS
    )
    mapping[str(lease["fresh_path"])] = str(lease["fresh_sha256"])
    return dict(sorted(mapping.items()))


def validate_static_authority(
    *, require_activation_review: bool = False
) -> dict[str, Any]:
    config = load_config()
    _verify_sealed_bundle()
    _verify_fresh_one_shot_authority()
    _verify_reviewed_v8_receipt()
    _verify_formal_science_config(config)
    for raw, expected in static_authority_mapping().items():
        verify_file_binding(_repo_path(raw, raw), expected, label=raw)
    runtime = _mapping(config["runtime"], "runtime")
    for path_key, hash_key in (
        ("locked_python_executable", "locked_python_sha256"),
        ("highspy_package_init_path", "highspy_package_init_sha256"),
        ("highspy_python_source_path", "highspy_python_source_sha256"),
        ("highspy_binary_path", "highspy_binary_sha256"),
    ):
        verify_file_binding(
            Path(runtime[path_key]), runtime[hash_key], label=path_key
        )
    if metadata.version("highspy") != "1.15.1":
        raise FormalActivationRejected("installed highspy version drifted")
    review_present = ACTIVATION_REVIEW_PASS.is_file() and not ACTIVATION_REVIEW_PASS.is_symlink()
    if require_activation_review:
        require_activation_review_pass()
    return {
        "schema": "rq2_public_grid_highs_formal_activation_static_validation_v1",
        "validation_passed": True,
        "v8_post_result_independent_review_passed": True,
        "formal_activation_review_receipt_present": review_present,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "static_authority_mapping_sha256": canonical_sha256(
            static_authority_mapping()
        ),
    }


def require_activation_review_pass() -> dict[str, Any]:
    if not ACTIVATION_REVIEW_PASS.is_file() or ACTIVATION_REVIEW_PASS.is_symlink():
        raise FormalActivationRejected(
            "independent formal activation review PASS receipt is absent"
        )
    receipt = _load_json(ACTIVATION_REVIEW_PASS, "activation review PASS receipt")
    config = load_config()
    if (
        receipt.get("schema")
        != config["independent_formal_activation_review"]["schema"]
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer", {}).get("path")
        != config["bundle"]["outer_path"]
        or receipt.get("reviewed_outer", {}).get("sha256") != sha256_file(OUTER)
        or receipt.get("effect")
        != {
            "formal_activation_successor_independent_review_passed": True,
            "formal_execution_authorized": True,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
    ):
        raise FormalActivationRejected("activation review PASS receipt drifted")
    return receipt


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
    attempt_root.mkdir(parents=True, exist_ok=False)
    observed = observed_available_commit_bytes()
    wall = wall_time_ns()
    monotonic = monotonic_ns()
    if type(observed) is not int or observed < 0 or wall <= 0 or monotonic <= 0:
        raise FormalActivationRejected("system commit preflight observation malformed")
    mapping = dict(sorted(authority_mapping.items()))
    if any(not _is_sha256(value) for value in mapping.values()):
        raise FormalActivationRejected("preflight authority mapping malformed")
    payload = {
        "schema": "rq2_public_grid_highs_formal_activation_preflight_v1",
        "version": 1,
        "wall_time_ns": wall,
        "monotonic_ns": monotonic,
        "observed_available_commit_bytes": observed,
        "preflight_threshold_bytes": PREFLIGHT_THRESHOLD_BYTES,
        "child_private_commit_stop_bytes": CHILD_PRIVATE_COMMIT_STOP_BYTES,
        "system_commit_available_stop_bytes": SYSTEM_COMMIT_AVAILABLE_STOP_BYTES,
        "authority_mapping": mapping,
        "authority_mapping_sha256": canonical_sha256(mapping),
        "comparison": (
            "observed_available_commit_bytes >= preflight_threshold_bytes"
        ),
        "threshold_passed": observed >= PREFLIGHT_THRESHOLD_BYTES,
        "formal_roots_created": False,
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "mathematical_infeasibility_inferred": False,
    }
    path = attempt_root / "preflight.json"
    raw = canonical_bytes(payload)
    _atomic_write(path, raw)
    if _read_stable(path) != raw:
        raise FormalActivationRejected("preflight stable readback failed")
    return {
        **payload,
        "persisted_path": str(path),
        "persisted_sha256": hashlib.sha256(raw).hexdigest(),
        "stable_readback_verified": True,
    }


def _powershell_related_processes(module_name: str) -> list[dict[str, object]]:
    escaped = module_name.replace("'", "''")
    script = (
        "$selfPid=$PID; Get-CimInstance Win32_Process | "
        f"Where-Object {{$_.ProcessId -ne $selfPid -and ([string]$_.CommandLine).Contains('{escaped}')}} | "
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


def ensure_formal_roots_absent() -> None:
    existing = [name for name, path in formal_roots().items() if path.exists()]
    if existing:
        raise FormalActivationRejected(
            "formal roots must not preexist: " + ", ".join(existing)
        )


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


def exact_controller_command(authority_path: Path) -> list[str]:
    prefix = list(load_config()["runtime"]["controller_command_prefix"])
    return [*prefix, str(authority_path.resolve())]


def exact_controller_environment() -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in load_config()["runtime"]["sanitized_environment"].items()
    }


def publish_dynamic_authority(
    preflight: Mapping[str, Any], *, review_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    preflight_path = Path(str(preflight["persisted_path"])).resolve()
    attempt_root = preflight_path.parent
    if (
        preflight.get("stable_readback_verified") is not True
        or sha256_file(preflight_path) != preflight.get("persisted_sha256")
    ):
        raise FormalActivationRejected("preflight persistence binding drifted")
    command = exact_controller_command(attempt_root / "authority.json")
    environment = exact_controller_environment()
    payload = {
        "schema": "rq2_public_grid_highs_formal_dynamic_activation_authority_v1",
        "version": 1,
        "preflight": {
            "path": str(preflight_path),
            "sha256": preflight["persisted_sha256"],
            "wall_time_ns": preflight["wall_time_ns"],
            "monotonic_ns": preflight["monotonic_ns"],
            "observed_available_commit_bytes": preflight[
                "observed_available_commit_bytes"
            ],
            "threshold_passed": preflight["threshold_passed"],
        },
        "preflight_authority_mapping": dict(preflight["authority_mapping"]),
        "preflight_authority_mapping_sha256": preflight[
            "authority_mapping_sha256"
        ],
        "activation_review_receipt": {
            "path": str(ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()),
            "sha256": sha256_file(ACTIVATION_REVIEW_PASS),
            "verdict": review_receipt["verdict"],
        },
        "exact_command": command,
        "exact_cwd": str(ROOT),
        "exact_environment": environment,
        "exact_environment_sha256": canonical_sha256(environment),
        "formal_roots": {
            name: str(path) for name, path in formal_roots().items()
        },
        "starts_from_block_zero": True,
        "resume_allowed": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    authority_path = attempt_root / "authority.json"
    raw = canonical_bytes(payload)
    _atomic_write(authority_path, raw)
    if _read_stable(authority_path) != raw:
        raise FormalActivationRejected("dynamic authority stable readback failed")
    receipt_payload = {
        "schema": "rq2_public_grid_highs_formal_activation_attempt_receipt_v1",
        "version": 1,
        "preflight_path": str(preflight_path),
        "preflight_sha256": preflight["persisted_sha256"],
        "authority_path": str(authority_path),
        "authority_sha256": hashlib.sha256(raw).hexdigest(),
        "threshold_passed": preflight["threshold_passed"],
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    receipt_path = attempt_root / "activation_receipt.json"
    receipt_raw = canonical_bytes(receipt_payload)
    _atomic_write(receipt_path, receipt_raw)
    if _read_stable(receipt_path) != receipt_raw:
        raise FormalActivationRejected("activation receipt stable readback failed")
    return {
        **payload,
        "authority_path": str(authority_path),
        "authority_sha256": hashlib.sha256(raw).hexdigest(),
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
    }


def validate_dynamic_authority(path: Path) -> dict[str, Any]:
    value = _load_json(path, "dynamic activation authority")
    preflight = _mapping(value["preflight"], "dynamic preflight")
    preflight_path = Path(str(preflight["path"])).resolve()
    if (
        value.get("schema")
        != "rq2_public_grid_highs_formal_dynamic_activation_authority_v1"
        or preflight.get("threshold_passed") is not True
        or sha256_file(preflight_path) != preflight.get("sha256")
        or value.get("preflight_authority_mapping")
        != preflight_authority_mapping()
        or value.get("preflight_authority_mapping_sha256")
        != canonical_sha256(preflight_authority_mapping())
        or value.get("exact_command") != exact_controller_command(path)
        or value.get("exact_cwd") != str(ROOT)
        or value.get("exact_environment") != exact_controller_environment()
        or value.get("exact_environment_sha256")
        != canonical_sha256(exact_controller_environment())
        or value.get("starts_from_block_zero") is not True
        or value.get("resume_allowed") is not False
        or value.get("formal_result_exists") is not False
        or value.get("claim") is not False
        or value.get("security_certified") is not False
    ):
        raise FormalActivationRejected("dynamic activation authority drifted")
    review = require_activation_review_pass()
    binding = _mapping(value["activation_review_receipt"], "review binding")
    if (
        binding.get("path") != ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()
        or binding.get("sha256") != sha256_file(ACTIVATION_REVIEW_PASS)
        or binding.get("verdict") != review.get("verdict")
    ):
        raise FormalActivationRejected("dynamic review receipt binding drifted")
    return value


def consume_one_shot_authority(dynamic: Mapping[str, Any]) -> dict[str, Any]:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    fresh = _repo_path(lease["fresh_path"], "fresh authority")
    consumed = _repo_path(lease["consumed_path"], "consumed authority")
    if (
        not fresh.is_file()
        or fresh.is_symlink()
        or consumed.exists()
        or sha256_file(fresh) != lease["fresh_sha256"]
    ):
        raise FormalActivationRejected("fresh one-shot authority is unavailable")
    value = _load_json(fresh, "fresh one-shot authority")
    if (
        value.get("authority_id") != lease["authority_id"]
        or value.get("state") != "fresh"
        or value.get("one_shot") is not True
    ):
        raise FormalActivationRejected("fresh one-shot authority drifted")
    authority_path = Path(str(dynamic["authority_path"])).resolve()
    if sha256_file(authority_path) != dynamic["authority_sha256"]:
        raise FormalActivationRejected("dynamic authority changed before consume")
    os.replace(fresh, consumed)
    tombstone = {
        "schema": "rq2_public_grid_highs_formal_activation_successor_v1_consumed_authority",
        "version": 1,
        "authority_id": lease["authority_id"],
        "state": "consumed",
        "one_shot_reusable": False,
        "dynamic_authority_path": str(authority_path),
        "dynamic_authority_sha256": dynamic["authority_sha256"],
        "activation_receipt_path": dynamic["activation_receipt_path"],
        "activation_receipt_sha256": dynamic["activation_receipt_sha256"],
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    raw = canonical_bytes(tombstone)
    try:
        _atomic_write(consumed, raw)
        if fresh.exists() or _read_stable(consumed) != raw:
            raise FormalActivationRejected("one-shot authority tombstone failed")
    except Exception:
        fresh.unlink(missing_ok=True)
        raise
    return tombstone
