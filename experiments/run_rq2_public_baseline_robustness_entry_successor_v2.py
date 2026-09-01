# ruff: noqa: E402
"""External preflight and gated entry for the public RQ2 four-arm package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.validate_rq2_public_baseline_robustness_entry_successor_v2 import (
    validate as validate_entry_authority,
)
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.evaluation.repository_paths import canonical_repository_relative_path
from src.evaluation.rq2_baseline_robustness_package_v1 import (
    build_E0_pair_checkpoint,
    build_resume_identity,
    compute_finite_pair_checkpoint,
    compute_planning_checkpoint,
    publish_final_package,
    validate_E0_pair_checkpoint,
    validate_finite_pair_checkpoint,
    validate_planning_checkpoint,
    write_checkpoint_idempotent,
)
from src.evaluation.rq2_provenance_v3 import (
    load_contract,
    load_json_strict,
    sha256_file,
    verify_checkpoint_inventory_bundle,
)
from src.scenarios.rq2_public_replay import (
    ParameterCell,
    TemporalBlock,
    envelope_for_cell,
    expand_parameter_cells,
    load_workload_blocks,
    pair_scenario,
    select_weighted_quantile_representatives,
    training_model_inputs,
)
from src.scenarios.rq2_public_replay_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    condition_on_grid_evaluable,
    load_power_blocks_with_state,
)
from src.solvers.execution_lease import ExecutionLease
from src.solvers.rq2_solver_adapter import solver_spec

CONFIG_RELATIVE = "configs/rq2_public_baseline_robustness_entry_successor_v2.yaml"
MANIFEST_RELATIVE = (
    "configs/rq2_public_baseline_robustness_entry_successor_v2.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
MANIFEST = ROOT / MANIFEST_RELATIVE
ENTRY_MANIFEST_SCHEMA = "rq2_public_baseline_robustness_entry_successor_manifest_v2"
GRID_STAGE = "grid_need_dispatch_v4"
_HEX = frozenset("0123456789abcdef")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    return list(value)


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return _mapping(loaded, f"YAML {path}")


def _repo_path(raw: object, label: str) -> Path:
    try:
        relative = canonical_repository_relative_path(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is not a safe repository-relative path") from error
    return ROOT.joinpath(*relative.split("/"))


def _path_is_reparse(path: Path) -> bool:
    information = os.lstat(path)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(
        stat.S_ISLNK(information.st_mode)
        or getattr(information, "st_file_attributes", 0) & reparse_flag
    )


def _assert_existing_components_are_regular(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if not current.exists():
            raise FileNotFoundError(current)
        if _path_is_reparse(current):
            raise ValueError(f"reparse path component is forbidden: {current}")


def _canonical_public_authority_path(
    provided: Path, canonical: Path, label: str
) -> Path:
    candidate = Path(os.path.abspath(provided))
    _assert_existing_components_are_regular(candidate)
    if candidate.resolve(strict=True) != canonical.resolve(strict=True):
        raise ValueError(f"{label} must be the canonical v2 repository authority")
    return canonical


def _activation_authority_present(config: Mapping[str, object]) -> bool:
    activation = _mapping(config.get("activation_authority"), "activation_authority")
    expected = {"path": None, "sha256": None, "activated": False}
    if activation != expected:
        raise ValueError("v2 activation authority contract drifted")
    return False


def _validate_public_authority(
    config_path: Path, manifest_path: Path
) -> dict[str, Any]:
    canonical_config = _canonical_public_authority_path(
        config_path, CONFIG, "config_path"
    )
    canonical_manifest = _canonical_public_authority_path(
        manifest_path, MANIFEST, "manifest_path"
    )
    result = validate_entry_authority(canonical_config, canonical_manifest)
    if result.get("validation_passed") is not True:
        raise ValueError("independent canonical v2 authority validation failed")
    return _load_yaml(canonical_config)


def _exact_flat_manifest_package(
    package: Path,
    *,
    expected_manifest_sha256: str,
    expected_members: Sequence[str],
    label: str,
) -> dict[str, str]:
    """Verify one flat package without following reparse or special entries."""

    _assert_existing_components_are_regular(package)
    if not package.is_dir() or _path_is_reparse(package):
        raise ValueError(f"{label} package must be a regular directory")
    members = set(expected_members)
    if not members or len(members) != len(expected_members):
        raise ValueError(f"{label} expected member inventory is invalid")
    observed: set[str] = set()
    with os.scandir(package) as entries:
        for entry in entries:
            path = Path(entry.path)
            if _path_is_reparse(path):
                raise ValueError(f"{label} package contains a reparse entry")
            if not entry.is_file(follow_symlinks=False):
                raise ValueError(f"{label} package contains a non-regular entry")
            observed.add(entry.name)
    if observed != {*members, "SHA256SUMS.json"}:
        raise ValueError(f"{label} package member inventory drifted")
    manifest_path = package / "SHA256SUMS.json"
    if _sha256(manifest_path) != _require_sha256(
        expected_manifest_sha256, f"{label} manifest SHA-256"
    ):
        raise ValueError(f"{label} manifest SHA-256 drifted")
    manifest = _mapping(load_json_strict(manifest_path), f"{label} manifest")
    if set(manifest) != members:
        raise ValueError(f"{label} manifest inventory drifted")
    for name, digest in manifest.items():
        expected = _require_sha256(digest, f"{label} member {name}")
        if _sha256(package / name) != expected:
            raise ValueError(f"{label} member hash drifted: {name}")
    return {str(name): str(digest) for name, digest in manifest.items()}


def _authority_inventory(config: Mapping[str, object]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for section_name in (
        "predecessor_authority",
        "implementation_authority",
        "frozen_scientific_authority",
    ):
        section = _mapping(config.get(section_name), section_name)
        for name, raw in section.items():
            item = _mapping(raw, f"{section_name}.{name}")
            if set(item) != {"path", "sha256"}:
                raise ValueError(f"{section_name}.{name} inventory drifted")
            relative = canonical_repository_relative_path(item["path"])
            digest = _require_sha256(item["sha256"], f"{section_name}.{name}")
            if relative in inventory:
                raise ValueError("authority path inventory contains an alias")
            inventory[relative] = digest
    return inventory


def _verify_live_entry_contract(
    config: Mapping[str, object], config_path: Path, manifest_path: Path
) -> str:
    """Bind config and all declared live authorities before any side effect."""

    manifest = _mapping(load_json_strict(manifest_path), "entry manifest")
    if set(manifest) != {"schema", "files"} or manifest.get("schema") != ENTRY_MANIFEST_SCHEMA:
        raise ValueError("entry manifest schema drifted")
    files = _mapping(manifest.get("files"), "entry manifest files")
    validation = _mapping(config.get("validation_contract"), "validation_contract")
    expected_paths = {
        CONFIG_RELATIVE,
        *_authority_inventory(config),
        canonical_repository_relative_path(validation["validator_path"]),
        canonical_repository_relative_path(validation["runner_path"]),
        canonical_repository_relative_path(validation["test_path"]),
    }
    if MANIFEST_RELATIVE in files or set(files) != expected_paths:
        raise ValueError("entry manifest exact path inventory drifted")
    config_sha256 = _sha256(config_path)
    if files.get(CONFIG_RELATIVE) != config_sha256:
        raise ValueError("entry config live hash drifted")
    for relative, digest in files.items():
        expected = _require_sha256(digest, f"entry manifest {relative}")
        path = config_path if relative == CONFIG_RELATIVE else _repo_path(relative, relative)
        if not path.is_file() or _path_is_reparse(path) or _sha256(path) != expected:
            raise ValueError(f"entry manifest live hash drifted: {relative}")
    authorities = _authority_inventory(config)
    for relative, digest in authorities.items():
        if files.get(relative) != digest:
            raise ValueError(f"entry authority disagrees with manifest: {relative}")
    return config_sha256


def _validate_workload(
    contract: Mapping[str, object],
) -> tuple[dict[str, object], tuple[TemporalBlock, ...], tuple[TemporalBlock, ...]]:
    package = _repo_path(contract.get("package"), "workload package")
    members = _sequence(contract.get("exact_members"), "workload exact_members")
    _exact_flat_manifest_package(
        package,
        expected_manifest_sha256=str(contract.get("manifest_sha256")),
        expected_members=[str(item) for item in members],
        label="workload",
    )
    summary = _mapping(load_json_strict(package / "summary.json"), "workload summary")
    expected_summary = {
        "schema": contract.get("schema"),
        "config_sha256": contract.get("config_sha256"),
        "implementation_sha256": contract.get("implementation_sha256"),
        "source_sha256": contract.get("source_sha256"),
        "training_block_count": contract.get("training_blocks"),
        "holdout_block_count": contract.get("holdout_blocks"),
        "block_hours": contract.get("block_hours"),
        "workload_fraction_is_power": False,
        "job_split_policy": "exclude_jobs_contributing_to_both_sides",
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise ValueError("workload summary contract drifted")
    training = load_workload_blocks(package, "training")
    holdout = load_workload_blocks(package, "holdout")
    if (
        len(training) != contract.get("training_blocks")
        or len(holdout) != contract.get("holdout_blocks")
        or any(
            len(block.workload) != contract.get("block_hours")
            for block in (*training, *holdout)
        )
    ):
        raise ValueError("workload split or block-hour inventory drifted")
    return (
        {
            "status": "verified",
            "package": canonical_repository_relative_path(contract["package"]),
            "manifest_sha256": contract["manifest_sha256"],
            "training_blocks": len(training),
            "holdout_blocks": len(holdout),
            "block_hours": contract["block_hours"],
        },
        training,
        holdout,
    )


def _frozen_grid_authority(config: Mapping[str, object]) -> dict[str, object]:
    frozen = _mapping(config.get("frozen_scientific_authority"), "frozen authority")
    pairwise_item = _mapping(frozen.get("pairwise_v4"), "pairwise_v4 authority")
    path = _repo_path(pairwise_item.get("path"), "pairwise_v4 path")
    if _sha256(path) != _require_sha256(pairwise_item.get("sha256"), "pairwise_v4 hash"):
        raise ValueError("pairwise_v4 live authority drifted")
    pairwise = _load_yaml(path)
    return _mapping(pairwise.get("input"), "pairwise_v4 input")


def _grid_blockers(
    contract: Mapping[str, object], frozen_input: Mapping[str, object]
) -> list[str]:
    blockers: list[str] = []
    if contract.get("frozen_authority_gate") is not True:
        blockers.append("frozen_grid_authority_gate_false")
    package = _repo_path(contract.get("package"), "grid package")
    if not package.exists():
        blockers.append("grid_package_missing")
    for field in ("manifest_sha256", "config_sha256", "provenance_sha256"):
        if contract.get(field) is None:
            blockers.append(f"grid_{field}_null")
    if frozen_input.get("grid_need_dispatch_ready") is not contract.get(
        "frozen_authority_gate"
    ):
        raise ValueError("grid readiness disagrees with frozen pairwise authority")
    if frozen_input.get("power_system_dispatch_manifest_sha256") != contract.get(
        "manifest_sha256"
    ):
        raise ValueError("grid manifest hash disagrees with frozen pairwise authority")
    if frozen_input.get("power_system_dispatch_config_sha256") != contract.get(
        "config_sha256"
    ):
        raise ValueError("grid config hash disagrees with frozen pairwise authority")
    return blockers


def _validate_grid(
    config: Mapping[str, object], contract: Mapping[str, object]
) -> tuple[
    dict[str, object],
    tuple[TemporalBlock, ...],
    tuple[TemporalBlock, ...],
    dict[str, str],
]:
    frozen_input = _frozen_grid_authority(config)
    blockers = _grid_blockers(contract, frozen_input)
    package = _repo_path(contract.get("package"), "grid package")
    if blockers:
        return (
            {
                "status": "blocked",
                "blockers": blockers,
                "package": canonical_repository_relative_path(contract["package"]),
                "package_exists": package.exists(),
                "frozen_authority_gate": contract.get("frozen_authority_gate"),
                "manifest_sha256": contract.get("manifest_sha256"),
                "config_sha256": contract.get("config_sha256"),
                "provenance_sha256": contract.get("provenance_sha256"),
            },
            (),
            (),
            {},
        )
    members = [
        str(item)
        for item in _sequence(contract.get("exact_members"), "grid exact_members")
    ]
    _exact_flat_manifest_package(
        package,
        expected_manifest_sha256=str(contract.get("manifest_sha256")),
        expected_members=members,
        label="grid",
    )
    loaded_training = load_power_blocks_with_state(package, "training")
    loaded_holdout = load_power_blocks_with_state(package, "holdout")
    training = loaded_training.blocks
    holdout = loaded_holdout.blocks
    states = {**loaded_training.state_by_block, **loaded_holdout.state_by_block}
    if (
        len(training) != contract.get("training_blocks")
        or len(holdout) != contract.get("holdout_blocks")
        or len(states) != contract.get("checkpoint_count")
        or any(
            len(block.grid_need) != contract.get("block_hours")
            for block in (*training, *holdout)
        )
    ):
        raise ValueError("grid split, checkpoint, or block-hour inventory drifted")
    if set(states.values()) - set(contract.get("allowed_states", ())):
        raise ValueError("grid package contains an unregistered state")
    training_conditioned = condition_on_grid_evaluable(
        training, {block.block_id: states[block.block_id] for block in training}
    )
    holdout_conditioned = condition_on_grid_evaluable(
        holdout, {block.block_id: states[block.block_id] for block in holdout}
    )
    summary = _mapping(load_json_strict(package / "summary.json"), "grid summary")
    expected_summary = {
        "schema": contract.get("schema"),
        "config_sha256": contract.get("config_sha256"),
        "training_block_count": contract.get("training_blocks"),
        "holdout_block_count": contract.get("holdout_blocks"),
        "all_blocks_resolved": True,
        "empirical_outage_probability_claimed": False,
        "full_N_minus_one": False,
        "AC_security": False,
        "security_certified": False,
        "exogenous_grid_infeasibility_has_finite_grid_need": False,
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise ValueError("grid summary contract drifted")
    provenance_path = package / "provenance.json"
    provenance_sha256 = sha256_file(provenance_path)
    if (
        provenance_sha256 != contract.get("provenance_sha256")
        or summary.get("provenance_sha256") != provenance_sha256
    ):
        raise ValueError("grid provenance hash drifted")
    frozen = _mapping(config.get("frozen_scientific_authority"), "frozen authority")
    provenance_contract = _mapping(
        frozen.get("provenance_contract_v3"), "provenance authority"
    )
    contract_identity = load_contract(
        ROOT,
        path=_repo_path(provenance_contract["path"], "provenance contract"),
        expected_sha256=str(provenance_contract["sha256"]),
        stage=GRID_STAGE,
    )
    checkpoint_inventory = load_json_strict(package / "checkpoint_inventory.json")
    verify_checkpoint_inventory_bundle(
        load_json_strict(provenance_path),
        checkpoint_inventory,
        summary,
        stage=GRID_STAGE,
        expected_config_sha256=str(contract.get("config_sha256")),
        contract_identity=contract_identity,
        expected_inputs={
            "power_system_blocks_manifest_sha256": frozen_input[
                "power_system_blocks_manifest_sha256"
            ],
            "rts_gmlc_source_manifest_sha256": frozen_input[
                "rts_gmlc_source_manifest_sha256"
            ],
        },
        expected_checkpoint_keys=set(states),
    )
    return (
        {
            "status": "verified",
            "blockers": [],
            "package": canonical_repository_relative_path(contract["package"]),
            "package_exists": True,
            "manifest_sha256": contract["manifest_sha256"],
            "config_sha256": contract["config_sha256"],
            "provenance_sha256": provenance_sha256,
            "training_blocks": len(training),
            "holdout_blocks": len(holdout),
            "checkpoint_count": len(states),
            "training_E0_mass": training_conditioned.exogenous_probability_mass,
            "holdout_E0_mass": holdout_conditioned.exogenous_probability_mass,
        },
        training,
        holdout,
        states,
    )


def _preflight(
    config_path: Path = CONFIG, manifest_path: Path = MANIFEST
) -> tuple[dict[str, Any], dict[str, object]]:
    config = _validate_public_authority(config_path, manifest_path)
    activation_authority_present = _activation_authority_present(config)
    config_sha256 = _verify_live_entry_contract(config, CONFIG, MANIFEST)
    external = _mapping(config.get("external_inputs"), "external_inputs")
    workload_report, workload_training, workload_holdout = _validate_workload(
        _mapping(external.get("workload"), "workload contract")
    )
    grid_report, power_training, power_holdout, power_states = _validate_grid(
        config, _mapping(external.get("grid"), "grid contract")
    )
    runtime = _mapping(config.get("runtime_design"), "runtime_design")
    cells = expand_parameter_cells(runtime)
    if len(cells) != 15:
        raise ValueError("registered parameter-cell count drifted")
    solver_specification = solver_spec(_mapping(runtime.get("solver"), "solver"))
    execution = _mapping(config.get("execution"), "execution")
    preflight_ready = grid_report["status"] == "verified"
    report = {
        "schema": "rq2_public_baseline_robustness_external_preflight_v2",
        "config_sha256": config_sha256,
        "activation_authority_present": activation_authority_present,
        "preflight_ready": preflight_ready,
        "workload": workload_report,
        "grid": grid_report,
        "parameter_cells": len(cells),
        "execution_gates": {
            key: execution.get(key)
            for key in (
                "external_inputs_ready",
                "independent_review",
                "user_execution_authorized",
                "execution_ready",
            )
        },
        "execution_host": execution_host_status(execution),
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_result": False,
        "claim": False,
    }
    return config, {
        "report": report,
        "workload_training": workload_training,
        "workload_holdout": workload_holdout,
        "power_training": power_training,
        "power_holdout": power_holdout,
        "power_states": power_states,
        "cells": cells,
        "solver_specification": solver_specification,
    }


def external_preflight(
    config_path: Path = CONFIG, manifest_path: Path = MANIFEST
) -> dict[str, object]:
    """Run the read-only external contract preflight."""

    _, context = _preflight(config_path, manifest_path)
    return dict(context["report"])


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _block_inventory_sha256(
    blocks: Sequence[TemporalBlock],
    *,
    state_by_block: Mapping[str, str] | None = None,
) -> str:
    ordered = sorted(blocks, key=lambda item: item.block_id)
    if len({block.block_id for block in ordered}) != len(ordered):
        raise ValueError("block inventory contains duplicate IDs")
    if state_by_block is not None and set(state_by_block) != {
        block.block_id for block in ordered
    }:
        raise ValueError("block-state inventory drifted")
    return _canonical_sha256(
        [
            {
                "block_id": block.block_id,
                "split": block.split,
                "probability": block.probability,
                "first_source_hour": block.first_source_hour,
                "grid_need": block.grid_need,
                "cfe_call": block.cfe_call,
                "workload": block.workload,
                **(
                    {"grid_state": state_by_block[block.block_id]}
                    if state_by_block is not None
                    else {}
                ),
            }
            for block in ordered
        ]
    )


def _safe_component(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or any(
            not (character.isascii() and (character.isalnum() or character in "._-"))
            for character in value
        )
    ):
        raise ValueError(f"{label} is not a safe path component")
    return value


def _boundary_contract(scenario: object) -> dict[str, object]:
    periods = tuple(getattr(scenario, "periods"))
    completed_periods = frozenset(getattr(scenario, "completed_periods"))
    if not periods:
        raise ValueError("holdout pair scenario must contain periods")
    terminal_period_completed = periods[-1] in completed_periods
    require_terminal_event_inactive = bool(
        getattr(scenario, "require_terminal_event_inactive")
    )
    return {
        "right_censored": bool(
            not terminal_period_completed or not require_terminal_event_inactive
        ),
        "boundary_state_status": str(getattr(scenario, "boundary_state_status")),
        "terminal_period_completed": terminal_period_completed,
        "require_terminal_event_inactive": require_terminal_event_inactive,
    }


def _expected_pairs(
    cells: Sequence[ParameterCell],
    power_holdout: Sequence[TemporalBlock],
    workload_holdout: Sequence[TemporalBlock],
    power_states: Mapping[str, str],
) -> tuple[list[dict[str, object]], dict[tuple[str, str, str], object]]:
    power_order = tuple(sorted(power_holdout, key=lambda item: item.block_id))
    workload_order = tuple(sorted(workload_holdout, key=lambda item: item.block_id))
    if not power_order or not workload_order:
        raise ValueError("holdout Cartesian inventory must be nonempty")
    holdout_ids = {block.block_id for block in power_order}
    if set(power_states) != holdout_ids:
        raise ValueError("holdout power-state inventory drifted")
    expected: list[dict[str, object]] = []
    scenarios: dict[tuple[str, str, str], object] = {}
    for cell in cells:
        cell_id = _safe_component(cell.cell_id, "cell_id")
        for power in power_order:
            power_id = _safe_component(power.block_id, "power_block_id")
            state = power_states[power.block_id]
            if state not in {FINITE_GRID_NEED, EXOGENOUS_GRID_INFEASIBILITY}:
                raise ValueError("holdout power state is unresolved")
            for workload in workload_order:
                workload_id = _safe_component(
                    workload.block_id, "workload_block_id"
                )
                key = (cell_id, power_id, workload_id)
                scenario = pair_scenario(
                    power,
                    workload,
                    cell,
                    name=f"holdout__{cell_id}__{power_id}__{workload_id}",
                )
                scenarios[key] = scenario
                expected.append(
                    {
                        "cell_id": cell_id,
                        "power_block_id": power_id,
                        "workload_block_id": workload_id,
                        "grid_state": state,
                        "power_probability": power.probability,
                        "workload_probability": workload.probability,
                        **_boundary_contract(scenario),
                    }
                )
    return expected, scenarios


def _checkpoint_relative_paths(
    cells: Sequence[ParameterCell],
    expected_pairs: Sequence[Mapping[str, object]],
) -> tuple[list[Path], dict[tuple[str, str, str], Path]]:
    planning = [
        Path("planning", f"{_safe_component(cell.cell_id, 'cell_id')}.json")
        for cell in cells
    ]
    pairs: dict[tuple[str, str, str], Path] = {}
    for item in expected_pairs:
        key = (
            _safe_component(item.get("cell_id"), "cell_id"),
            _safe_component(item.get("power_block_id"), "power_block_id"),
            _safe_component(item.get("workload_block_id"), "workload_block_id"),
        )
        path = Path("pairs", key[0], key[1], f"{key[2]}.json")
        if key in pairs or path in pairs.values():
            raise ValueError("checkpoint path inventory contains an alias")
        pairs[key] = path
    return planning, pairs


def _scan_checkpoint_root(root: Path, allowed_files: set[Path]) -> set[Path]:
    """Read one partial checkpoint tree without following aliases or extras."""

    if not os.path.lexists(root):
        return set()
    _assert_existing_components_are_regular(root)
    if not root.is_dir() or _path_is_reparse(root):
        raise ValueError("checkpoint root must be a regular directory")
    allowed_directories = {Path(".")}
    for relative in allowed_files:
        parent = relative.parent
        while parent != Path("."):
            allowed_directories.add(parent)
            parent = parent.parent
    observed: set[Path] = set()
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root)
                if _path_is_reparse(path):
                    raise ValueError("checkpoint root contains a reparse entry")
                if entry.is_dir(follow_symlinks=False):
                    if relative not in allowed_directories:
                        raise ValueError("checkpoint root contains an extra directory")
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    if relative not in allowed_files:
                        raise ValueError("checkpoint root contains an extra file")
                    observed.add(relative)
                else:
                    raise ValueError("checkpoint root contains a special entry")
    return observed


def _checkpoint_matches_common(
    checkpoint: Mapping[str, object],
    *,
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> None:
    if checkpoint.get("resume_identity") != dict(resume_identity):
        raise ValueError("existing checkpoint resume identity drifted")
    if checkpoint.get("provenance") != dict(provenance):
        raise ValueError("existing checkpoint provenance drifted")


def _load_planning_checkpoint(
    path: Path,
    *,
    cell_id: str,
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    checkpoint = validate_planning_checkpoint(load_json_strict(path))
    if checkpoint.get("cell_id") != cell_id:
        raise ValueError("existing planning checkpoint cell drifted")
    _checkpoint_matches_common(
        checkpoint,
        resume_identity=resume_identity,
        provenance=provenance,
    )
    return checkpoint


def _capacity_by_arm(planning: Mapping[str, object]) -> dict[str, object]:
    if planning.get("disposition") != "resolved":
        raise ValueError("pair replay requires a resolved planning checkpoint")
    records = _sequence(
        planning.get("four_arm_minimum_flexibility"), "planning capacity records"
    )
    capacities = {str(item["arm_id"]): item["minimum_capacity"] for item in records}
    if len(capacities) != len(records):
        raise ValueError("planning capacity inventory contains duplicates")
    return capacities


def _load_pair_checkpoint(
    path: Path,
    *,
    expected: Mapping[str, object],
    planning: Mapping[str, object],
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    loaded = load_json_strict(path)
    if expected.get("grid_state") == FINITE_GRID_NEED:
        checkpoint = validate_finite_pair_checkpoint(loaded)
    elif expected.get("grid_state") == EXOGENOUS_GRID_INFEASIBILITY:
        checkpoint = validate_E0_pair_checkpoint(loaded)
    else:
        raise ValueError("expected pair state is unresolved")
    _checkpoint_matches_common(
        checkpoint,
        resume_identity=resume_identity,
        provenance=provenance,
    )
    for field in (
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "power_probability",
        "workload_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
    ):
        if checkpoint.get(field) != expected.get(field):
            raise ValueError(f"existing pair checkpoint {field} drifted")
    if expected.get("grid_state") == FINITE_GRID_NEED:
        capacities = _capacity_by_arm(planning)
        for arm in _sequence(checkpoint.get("arms"), "finite pair arms"):
            if arm.get("committed_capacity") != capacities.get(str(arm.get("arm_id"))):
                raise ValueError("existing finite pair capacity drifted")
    elif checkpoint.get("resolved") is not True:
        raise ValueError("existing E0 checkpoint is unresolved")
    return checkpoint


def _resume_contract(
    config: Mapping[str, object],
    context: Mapping[str, object],
    *,
    selected_power: Sequence[TemporalBlock],
    selected_workload: Sequence[TemporalBlock],
) -> tuple[dict[str, object], dict[str, object]]:
    report = _mapping(context.get("report"), "preflight report")
    config_sha256 = _require_sha256(report.get("config_sha256"), "config SHA-256")
    power_training = tuple(context["power_training"])
    power_holdout = tuple(context["power_holdout"])
    workload_training = tuple(context["workload_training"])
    workload_holdout = tuple(context["workload_holdout"])
    power_states = _mapping(context.get("power_states"), "power states")
    training_states = {
        block.block_id: str(power_states[block.block_id]) for block in power_training
    }
    holdout_states = {
        block.block_id: str(power_states[block.block_id]) for block in power_holdout
    }
    authorities: dict[str, str] = {}
    for section_name in (
        "predecessor_authority",
        "implementation_authority",
        "frozen_scientific_authority",
    ):
        section = _mapping(config.get(section_name), section_name)
        for name, raw in section.items():
            item = _mapping(raw, f"{section_name}.{name}")
            key = _safe_component(f"{section_name}_{name}", "resume authority")
            authorities[key] = _require_sha256(item.get("sha256"), key)
    external = _mapping(config.get("external_inputs"), "external_inputs")
    workload_contract = _mapping(external.get("workload"), "workload contract")
    grid_contract = _mapping(external.get("grid"), "grid contract")
    authorities.update(
        {
            "workload_manifest": _require_sha256(
                workload_contract.get("manifest_sha256"), "workload manifest"
            ),
            "grid_manifest": _require_sha256(
                grid_contract.get("manifest_sha256"), "grid manifest"
            ),
            "grid_config": _require_sha256(
                grid_contract.get("config_sha256"), "grid config"
            ),
            "grid_provenance": _require_sha256(
                grid_contract.get("provenance_sha256"), "grid provenance"
            ),
            "power_training_inventory": _block_inventory_sha256(
                power_training, state_by_block=training_states
            ),
            "power_holdout_inventory": _block_inventory_sha256(
                power_holdout, state_by_block=holdout_states
            ),
            "workload_training_inventory": _block_inventory_sha256(
                workload_training
            ),
            "workload_holdout_inventory": _block_inventory_sha256(
                workload_holdout
            ),
            "selected_power_training_inventory": _block_inventory_sha256(
                selected_power,
                state_by_block={
                    block.block_id: FINITE_GRID_NEED for block in selected_power
                },
            ),
            "selected_workload_training_inventory": _block_inventory_sha256(
                selected_workload
            ),
        }
    )
    resume_identity = build_resume_identity(
        run_id="rq2-public-baseline-robustness-entry-successor-v2",
        successor_config_sha256=config_sha256,
        authority_sha256s=authorities,
    )
    provenance = {
        "schema": "rq2_public_baseline_robustness_entry_provenance_v2",
        "config_sha256": config_sha256,
        "authority_sha256s": authorities,
        "selected_power_training_block_ids": [
            block.block_id for block in selected_power
        ],
        "selected_workload_training_block_ids": [
            block.block_id for block in selected_workload
        ],
        "training_selection_uses_holdout_outcomes": False,
        "formal_result": False,
        "claim": False,
    }
    return resume_identity, provenance


def _assert_no_active_lease(root: Path) -> None:
    if os.path.lexists(root):
        _assert_existing_components_are_regular(root)
        if not root.is_dir() or _path_is_reparse(root):
            raise ValueError("lease root must be a regular directory")
    active = root / "active"
    if os.path.lexists(active):
        raise RuntimeError("existing active or terminal execution lease blocks takeover")


def _run_ready(
    config: Mapping[str, object],
    context: Mapping[str, object],
    *,
    maximum_pairs: int | None,
) -> dict[str, object]:
    if maximum_pairs is not None and (
        isinstance(maximum_pairs, bool)
        or not isinstance(maximum_pairs, int)
        or maximum_pairs < 0
    ):
        raise ValueError("maximum_pairs must be a nonnegative integer")
    runtime = _mapping(config.get("runtime_design"), "runtime_design")
    selection = _mapping(runtime.get("training_selection"), "training_selection")
    power_count = selection.get("power_system_representatives")
    workload_count = selection.get("workload_representatives")
    if (
        isinstance(power_count, bool)
        or not isinstance(power_count, int)
        or power_count <= 0
        or isinstance(workload_count, bool)
        or not isinstance(workload_count, int)
        or workload_count <= 0
        or selection.get("selection_uses_holdout_outcomes") is not False
    ):
        raise ValueError("training representative-selection contract drifted")
    power_training = tuple(context["power_training"])
    workload_training = tuple(context["workload_training"])
    power_holdout = tuple(context["power_holdout"])
    workload_holdout = tuple(context["workload_holdout"])
    power_states = _mapping(context.get("power_states"), "power states")
    all_power_ids = {
        block.block_id for block in (*power_training, *power_holdout)
    }
    if set(power_states) != all_power_ids:
        raise ValueError("power-state inventory disagrees with both splits")
    training_conditioned = condition_on_grid_evaluable(
        power_training,
        {block.block_id: power_states[block.block_id] for block in power_training},
    )
    holdout_conditioned = condition_on_grid_evaluable(
        power_holdout,
        {block.block_id: power_states[block.block_id] for block in power_holdout},
    )
    selected_power = select_weighted_quantile_representatives(
        training_conditioned.evaluable_blocks,
        power_count,
        role="power",
    )
    selected_workload = select_weighted_quantile_representatives(
        workload_training,
        workload_count,
        role="workload",
    )
    cells = tuple(context["cells"])
    expected_pairs, scenarios = _expected_pairs(
        cells,
        power_holdout,
        workload_holdout,
        {block.block_id: power_states[block.block_id] for block in power_holdout},
    )
    planning_relatives, pair_relatives = _checkpoint_relative_paths(
        cells, expected_pairs
    )
    resume_identity, provenance = _resume_contract(
        config,
        context,
        selected_power=selected_power,
        selected_workload=selected_workload,
    )
    execution = _mapping(config.get("execution"), "execution")
    checkpoint_root = _repo_path(
        execution.get("checkpoint_root"), "checkpoint root"
    )
    lease_root = _repo_path(execution.get("lease_root"), "lease root")
    output = _repo_path(execution.get("output_directory"), "output directory")
    allowed_files = {*planning_relatives, *pair_relatives.values()}
    observed = _scan_checkpoint_root(checkpoint_root, allowed_files)
    observed_planning = {path for path in observed if path.parts[0] == "planning"}
    observed_pairs = {path for path in observed if path.parts[0] == "pairs"}
    prefix_length = len(observed_planning)
    if observed_planning != set(planning_relatives[:prefix_length]):
        raise ValueError("planning checkpoint inventory is not a deterministic prefix")
    if prefix_length < len(planning_relatives) and observed_pairs:
        raise ValueError("pair checkpoints exist before planning completion")
    _assert_no_active_lease(lease_root)
    if os.path.lexists(output):
        raise FileExistsError(f"final package target already exists: {output}")

    planning_by_cell: dict[str, dict[str, object]] = {}
    planning_paths: list[Path] = []
    fixed_policy = _mapping(runtime.get("fixed_policy"), "fixed_policy")
    solver_specification = context["solver_specification"]
    with ExecutionLease.acquire(
        lease_root,
        stage="rq2_public_baseline_robustness_entry_successor_v2",
        attempt_id=str(resume_identity["identity_sha256"]),
    ):
        for cell, relative in zip(cells, planning_relatives, strict=True):
            path = checkpoint_root / relative
            if relative in observed_planning:
                checkpoint = _load_planning_checkpoint(
                    path,
                    cell_id=cell.cell_id,
                    resume_identity=resume_identity,
                    provenance=provenance,
                )
            else:
                checkpoint = compute_planning_checkpoint(
                    cell_id=cell.cell_id,
                    training_inputs=training_model_inputs(
                        selected_power, selected_workload, cell, runtime
                    ),
                    solver_specification=solver_specification,
                    power_blocks=training_conditioned.evaluable_blocks,
                    workload_blocks=workload_training,
                    cell=cell,
                    fixed_policy=fixed_policy,
                    grid_state_by_power_block={
                        block.block_id: FINITE_GRID_NEED
                        for block in training_conditioned.evaluable_blocks
                    },
                    resume_identity=resume_identity,
                    provenance=provenance,
                )
                write_checkpoint_idempotent(path, checkpoint)
            planning_by_cell[cell.cell_id] = checkpoint
            planning_paths.append(path)

        unresolved = [
            cell_id
            for cell_id, checkpoint in planning_by_cell.items()
            if checkpoint.get("disposition") == "unresolved"
        ]
        if unresolved:
            return {
                "schema": "rq2_public_baseline_robustness_entry_progress_v2",
                "published": False,
                "status": "blocked_unresolved_planning",
                "unresolved_cell_ids": unresolved,
                "completed_planning_cells": len(planning_by_cell),
                "completed_pairs": len(observed_pairs),
                "training_E0_mass": training_conditioned.exogenous_probability_mass,
                "holdout_E0_mass": holdout_conditioned.exogenous_probability_mass,
                "formal_result": False,
                "claim": False,
            }

        expected_by_key = {
            (
                str(item["cell_id"]),
                str(item["power_block_id"]),
                str(item["workload_block_id"]),
            ): item
            for item in expected_pairs
            if planning_by_cell[str(item["cell_id"])]["disposition"] == "resolved"
        }
        pair_order = [key for key in pair_relatives if key in expected_by_key]
        observed_required = {
            relative for key, relative in pair_relatives.items() if key in expected_by_key
        } & observed_pairs
        observed_extra = observed_pairs - observed_required
        if observed_extra:
            raise ValueError("pair checkpoint exists for an undefined estimand")
        observed_count = len(observed_required)
        expected_prefix = {pair_relatives[key] for key in pair_order[:observed_count]}
        if observed_required != expected_prefix:
            raise ValueError("pair checkpoint inventory is not a deterministic prefix")
        if maximum_pairs is not None and observed_count > maximum_pairs:
            raise ValueError("observed pairs exceed maximum_pairs")
        limit = len(pair_order) if maximum_pairs is None else min(
            maximum_pairs, len(pair_order)
        )
        pair_paths: list[Path] = []
        for key in pair_order[:limit]:
            expected = expected_by_key[key]
            relative = pair_relatives[key]
            path = checkpoint_root / relative
            planning = planning_by_cell[key[0]]
            if relative in observed_required:
                _load_pair_checkpoint(
                    path,
                    expected=expected,
                    planning=planning,
                    resume_identity=resume_identity,
                    provenance=provenance,
                )
            elif expected["grid_state"] == FINITE_GRID_NEED:
                checkpoint = compute_finite_pair_checkpoint(
                    cell_id=key[0],
                    power_block_id=key[1],
                    workload_block_id=key[2],
                    power_probability=expected["power_probability"],
                    workload_probability=expected["workload_probability"],
                    scenario=scenarios[key],
                    envelope=envelope_for_cell(
                        next(cell for cell in cells if cell.cell_id == key[0]),
                        policy=fixed_policy,
                    ),
                    capacity_by_arm=_capacity_by_arm(planning),
                    service_shortfall_tolerance=float(
                        fixed_policy["service_shortfall_tolerance"]
                    ),
                    resume_identity=resume_identity,
                    provenance=provenance,
                )
                write_checkpoint_idempotent(path, checkpoint)
            else:
                checkpoint = build_E0_pair_checkpoint(
                    cell_id=key[0],
                    power_block_id=key[1],
                    workload_block_id=key[2],
                    power_probability=expected["power_probability"],
                    workload_probability=expected["workload_probability"],
                    right_censored=bool(expected["right_censored"]),
                    boundary_state_status=str(expected["boundary_state_status"]),
                    terminal_period_completed=bool(
                        expected["terminal_period_completed"]
                    ),
                    require_terminal_event_inactive=bool(
                        expected["require_terminal_event_inactive"]
                    ),
                    resolved=True,
                    unresolved_reason=None,
                    resume_identity=resume_identity,
                    provenance=provenance,
                )
                write_checkpoint_idempotent(path, checkpoint)
            pair_paths.append(path)

        return publish_final_package(
            target=output,
            planning_checkpoint_paths=planning_paths,
            pair_checkpoint_paths=pair_paths,
            expected_cell_ids=[cell.cell_id for cell in cells],
            expected_pairs=expected_pairs,
            resume_identity=resume_identity,
            provenance=provenance,
            maximum_pairs=maximum_pairs,
        )


def run(
    config_path: Path = CONFIG,
    manifest_path: Path = MANIFEST,
    *,
    maximum_pairs: int | None = None,
) -> dict[str, object]:
    """Run the frozen orchestration only after every independent gate passes."""

    authority_config = _validate_public_authority(config_path, manifest_path)
    if _activation_authority_present(authority_config) is not True:
        raise RuntimeError("computation entry is blocked: activation_authority_absent")
    config, context = _preflight(config_path, manifest_path)
    execution = _mapping(config.get("execution"), "execution")
    gate_names = (
        "external_inputs_ready",
        "independent_review",
        "user_execution_authorized",
        "execution_ready",
    )
    blocked = [name for name in gate_names if execution.get(name) is not True]
    if context["report"]["preflight_ready"] is not True:
        blocked.insert(0, "external_preflight")
    if blocked:
        raise RuntimeError("computation entry is blocked: " + ", ".join(blocked))
    gates = _mapping(config.get("gates"), "gates")
    if any(gates.get(name) is not execution.get(name) for name in gate_names):
        raise ValueError("execution gates disagree with registered gates")
    if gates.get("formal_result") is not False or gates.get("claim") is not False:
        raise ValueError("entry cannot elevate formal-result or claim gates")
    require_execution_host(execution)
    return _run_ready(config, context, maximum_pairs=maximum_pairs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run"))
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--maximum-pairs", type=int)
    arguments = parser.parse_args()
    if arguments.mode == "preflight":
        result = external_preflight(arguments.config, arguments.manifest)
    else:
        result = run(
            arguments.config,
            arguments.manifest,
            maximum_pairs=arguments.maximum_pairs,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
