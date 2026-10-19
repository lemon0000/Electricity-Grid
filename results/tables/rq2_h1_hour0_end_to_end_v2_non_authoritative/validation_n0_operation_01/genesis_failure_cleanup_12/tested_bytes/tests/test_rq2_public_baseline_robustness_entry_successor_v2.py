from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import run_rq2_public_baseline_robustness_entry_successor_v2 as runner

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_baseline_robustness_entry_successor_v2.yaml"
MANIFEST = (
    ROOT
    / "configs/rq2_public_baseline_robustness_entry_successor_v2.SHA256SUMS.json"
)
VALIDATOR = (
    ROOT
    / "experiments/validate_rq2_public_baseline_robustness_entry_successor_v2.py"
)
ARM_IDS = (
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
)


def _validator_namespace() -> dict[str, object]:
    source = VALIDATOR.read_text(encoding="utf-8")
    namespace: dict[str, object] = {
        "__name__": "entry_validator_test",
        "__file__": str(VALIDATOR),
    }
    exec(compile(source, str(VALIDATOR), "exec"), namespace)
    return namespace


def _write_flat_package(path: Path, members: dict[str, bytes]) -> str:
    path.mkdir()
    inventory = {}
    for name, payload in members.items():
        destination = path / name
        destination.write_bytes(payload)
        inventory[name] = hashlib.sha256(payload).hexdigest()
    manifest = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    manifest_path = path / "SHA256SUMS.json"
    manifest_path.write_text(manifest, encoding="utf-8")
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def _block(
    block_id: str,
    split: str,
    probability: float,
    *,
    power: bool,
) -> runner.TemporalBlock:
    return runner.TemporalBlock(
        block_id=block_id,
        split=split,
        probability=probability,
        first_source_hour=0,
        grid_need=(0.2, 0.3) if power else (),
        cfe_call=(0.1, 0.1) if power else (),
        workload=() if power else (0.5, 0.6),
    )


def _ready_contract(tmp_path: Path) -> tuple[dict, dict, dict[str, Path]]:
    config = copy.deepcopy(yaml.safe_load(CONFIG.read_text(encoding="utf-8")))
    for name in (
        "external_inputs_ready",
        "independent_review",
        "user_execution_authorized",
        "execution_ready",
    ):
        config["execution"][name] = True
        config["gates"][name] = True
    config["runtime_design"]["training_selection"][
        "power_system_representatives"
    ] = 1
    config["runtime_design"]["training_selection"][
        "workload_representatives"
    ] = 1
    config["external_inputs"]["grid"].update(
        {
            "frozen_authority_gate": True,
            "manifest_sha256": "c" * 64,
            "config_sha256": "d" * 64,
            "provenance_sha256": "e" * 64,
        }
    )
    paths = {
        "checkpoint-root": tmp_path / "checkpoints",
        "lease-root": tmp_path / "leases",
        "output": tmp_path / "output",
    }
    config["execution"]["checkpoint_root"] = "checkpoint-root"
    config["execution"]["lease_root"] = "lease-root"
    config["execution"]["output_directory"] = "output"
    power_training = (
        _block("training-finite", "training", 0.8, power=True),
        _block("training-E0", "training", 0.2, power=True),
    )
    power_holdout = (
        _block("holdout-finite", "holdout", 0.25, power=True),
        _block("holdout-E0", "holdout", 0.75, power=True),
    )
    workload_training = (
        _block("workload-training", "training", 1.0, power=False),
    )
    workload_holdout = (
        _block("workload-holdout", "holdout", 1.0, power=False),
    )
    cell = runner.ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=0.2,
        recovery_efficiency=0.85,
        normalized_recovery_headroom=0.1,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_energy_budget=0.4,
        normalized_debt_limit=0.2,
    )
    states = {
        "training-finite": runner.FINITE_GRID_NEED,
        "training-E0": runner.EXOGENOUS_GRID_INFEASIBILITY,
        "holdout-finite": runner.FINITE_GRID_NEED,
        "holdout-E0": runner.EXOGENOUS_GRID_INFEASIBILITY,
    }
    context = {
        "report": {"preflight_ready": True, "config_sha256": "a" * 64},
        "power_training": power_training,
        "power_holdout": power_holdout,
        "workload_training": workload_training,
        "workload_holdout": workload_holdout,
        "power_states": states,
        "cells": (cell,),
        "solver_specification": object(),
    }
    return config, context, paths


def _patch_ready_runtime(
    monkeypatch: pytest.MonkeyPatch,
    config: dict,
    context: dict,
    paths: dict[str, Path],
) -> dict[str, object]:
    calls: dict[str, object] = {
        "planning": 0,
        "finite": 0,
        "E0": 0,
        "publish": [],
        "planning_power_ids": (),
        "planning_workload_ids": (),
        "training_scenario_names": (),
    }
    monkeypatch.setattr(
        runner, "_preflight", lambda *args, **kwargs: (config, context)
    )
    monkeypatch.setattr(runner, "require_execution_host", lambda execution: None)
    monkeypatch.setattr(
        runner, "_repo_path", lambda raw, label: paths[str(raw)]
    )

    def fake_planning(**kwargs: object) -> dict[str, object]:
        calls["planning"] = int(calls["planning"]) + 1
        calls["planning_power_ids"] = tuple(
            block.block_id for block in kwargs["power_blocks"]
        )
        calls["planning_workload_ids"] = tuple(
            block.block_id for block in kwargs["workload_blocks"]
        )
        calls["training_scenario_names"] = tuple(
            scenario.name for scenario in kwargs["training_inputs"].scenarios
        )
        return {
            "cell_id": kwargs["cell_id"],
            "disposition": "resolved",
            "resume_identity": kwargs["resume_identity"],
            "provenance": kwargs["provenance"],
            "four_arm_minimum_flexibility": [
                {"arm_id": arm_id, "minimum_capacity": 0.25}
                for arm_id in ARM_IDS
            ],
        }

    def fake_finite(**kwargs: object) -> dict[str, object]:
        calls["finite"] = int(calls["finite"]) + 1
        boundary = runner._boundary_contract(kwargs["scenario"])
        return {
            "cell_id": kwargs["cell_id"],
            "power_block_id": kwargs["power_block_id"],
            "workload_block_id": kwargs["workload_block_id"],
            "grid_state": runner.FINITE_GRID_NEED,
            "power_probability": kwargs["power_probability"],
            "workload_probability": kwargs["workload_probability"],
            **boundary,
            "resume_identity": kwargs["resume_identity"],
            "provenance": kwargs["provenance"],
            "arms": [
                {"arm_id": arm_id, "committed_capacity": 0.25}
                for arm_id in ARM_IDS
            ],
        }

    real_E0 = runner.build_E0_pair_checkpoint

    def counted_E0(**kwargs: object) -> dict[str, object]:
        calls["E0"] = int(calls["E0"]) + 1
        return real_E0(**kwargs)

    def fake_publish(**kwargs: object) -> dict[str, object]:
        calls["publish"].append(kwargs)
        completed = len(kwargs["pair_checkpoint_paths"])
        required = len(kwargs["expected_pairs"])
        maximum = kwargs["maximum_pairs"]
        return {
            "schema": "fake-publication",
            "published": maximum is None or maximum >= required,
            "completed_pairs": completed,
            "required_pairs": required,
            "maximum_pairs": maximum,
            "formal_result": False,
            "claim": False,
        }

    monkeypatch.setattr(runner, "compute_planning_checkpoint", fake_planning)
    monkeypatch.setattr(runner, "compute_finite_pair_checkpoint", fake_finite)
    monkeypatch.setattr(runner, "build_E0_pair_checkpoint", counted_E0)
    monkeypatch.setattr(runner, "publish_final_package", fake_publish)
    monkeypatch.setattr(runner, "validate_planning_checkpoint", lambda value: value)
    monkeypatch.setattr(
        runner, "validate_finite_pair_checkpoint", lambda value: value
    )
    return calls


def test_current_real_external_preflight_is_read_only_and_honestly_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: pytest.fail("mkdir"))
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))

    report = runner.external_preflight(CONFIG, MANIFEST)

    assert report["workload"]["status"] == "verified"
    assert report["grid"]["status"] == "blocked"
    assert report["grid"]["blockers"] == [
        "frozen_grid_authority_gate_false",
        "grid_package_missing",
        "grid_manifest_sha256_null",
        "grid_config_sha256_null",
        "grid_provenance_sha256_null",
    ]
    assert not any(
        "infeasible" in reason.casefold() or reason == "exogenous_grid_infeasibility"
        for reason in report["grid"]["blockers"]
    )
    assert report["preflight_ready"] is False
    assert report["activation_authority_present"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0


def test_flat_package_rejects_tampered_member_and_extra_entry(tmp_path: Path) -> None:
    package = tmp_path / "package"
    digest = _write_flat_package(package, {"summary.json": b"{}\n"})
    (package / "summary.json").write_bytes(b'{"tampered":true}\n')
    with pytest.raises(ValueError, match="member hash drifted"):
        runner._exact_flat_manifest_package(
            package,
            expected_manifest_sha256=digest,
            expected_members=["summary.json"],
            label="fake",
        )
    (package / "summary.json").write_bytes(b"{}\n")
    (package / "extra.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="member inventory drifted"):
        runner._exact_flat_manifest_package(
            package,
            expected_manifest_sha256=digest,
            expected_members=["summary.json"],
            label="fake",
        )


def test_grid_blockers_distinguish_gate_missing_and_null_hashes() -> None:
    contract = {
        "frozen_authority_gate": False,
        "package": "configs",
        "manifest_sha256": None,
        "config_sha256": None,
        "provenance_sha256": None,
    }
    frozen = {
        "grid_need_dispatch_ready": False,
        "power_system_dispatch_manifest_sha256": None,
        "power_system_dispatch_config_sha256": None,
    }
    blockers = runner._grid_blockers(contract, frozen)
    assert blockers == [
        "frozen_grid_authority_gate_false",
        "grid_manifest_sha256_null",
        "grid_config_sha256_null",
        "grid_provenance_sha256_null",
    ]


def test_ready_grid_requires_exact_eight_members_and_1071_provenance_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "grid-package"
    package.mkdir()
    provenance_contract = tmp_path / "provenance-contract.yaml"
    provenance_contract.write_text("schema: fake\n", encoding="utf-8")
    exact_members = [
        "block_status.csv.gz",
        "checkpoint_inventory.json",
        "config.yaml",
        "dispatched_power_system_blocks.csv.gz",
        "holdout_marginal.csv.gz",
        "provenance.json",
        "summary.json",
        "training_marginal.csv.gz",
    ]
    contract = {
        "frozen_authority_gate": True,
        "package": "grid-package",
        "manifest_sha256": "c" * 64,
        "config_sha256": "d" * 64,
        "provenance_sha256": "e" * 64,
        "exact_members": exact_members,
        "schema": "grid-schema",
        "training_blocks": 541,
        "holdout_blocks": 530,
        "block_hours": 1,
        "checkpoint_count": 1071,
        "allowed_states": [
            runner.FINITE_GRID_NEED,
            runner.EXOGENOUS_GRID_INFEASIBILITY,
        ],
    }
    config = {
        "frozen_scientific_authority": {
            "provenance_contract_v3": {
                "path": "provenance-contract",
                "sha256": "f" * 64,
            }
        }
    }
    frozen = {
        "grid_need_dispatch_ready": True,
        "power_system_dispatch_manifest_sha256": "c" * 64,
        "power_system_dispatch_config_sha256": "d" * 64,
        "power_system_blocks_manifest_sha256": "1" * 64,
        "rts_gmlc_source_manifest_sha256": "2" * 64,
    }

    def power_split(split: str, count: int) -> SimpleNamespace:
        blocks = tuple(
            runner.TemporalBlock(
                block_id=f"{split}-{index:04d}",
                split=split,
                probability=1.0 / count,
                first_source_hour=index,
                grid_need=(0.0,),
                cfe_call=(0.0,),
                workload=(),
            )
            for index in range(count)
        )
        states = {
            block.block_id: (
                runner.EXOGENOUS_GRID_INFEASIBILITY
                if index == 0
                else runner.FINITE_GRID_NEED
            )
            for index, block in enumerate(blocks)
        }
        return SimpleNamespace(blocks=blocks, state_by_block=states)

    loaded = {
        "training": power_split("training", 541),
        "holdout": power_split("holdout", 530),
    }
    summary = {
        "schema": "grid-schema",
        "config_sha256": "d" * 64,
        "training_block_count": 541,
        "holdout_block_count": 530,
        "all_blocks_resolved": True,
        "empirical_outage_probability_claimed": False,
        "full_N_minus_one": False,
        "AC_security": False,
        "security_certified": False,
        "exogenous_grid_infeasibility_has_finite_grid_need": False,
        "provenance_sha256": "e" * 64,
    }
    captured: dict[str, object] = {}
    monkeypatch.setattr(runner, "_frozen_grid_authority", lambda value: frozen)
    monkeypatch.setattr(
        runner,
        "_repo_path",
        lambda raw, label: {
            "grid-package": package,
            "provenance-contract": provenance_contract,
        }[str(raw)],
    )

    def exact_package(*args: object, **kwargs: object) -> dict[str, str]:
        captured["members"] = tuple(kwargs["expected_members"])
        return {name: "0" * 64 for name in exact_members}

    monkeypatch.setattr(runner, "_exact_flat_manifest_package", exact_package)
    monkeypatch.setattr(
        runner,
        "load_power_blocks_with_state",
        lambda path, split: loaded[split],
    )

    def fake_json(path: Path) -> object:
        if path.name == "summary.json":
            return summary
        if path.name == "provenance.json":
            return {"schema": "fake-provenance"}
        if path.name == "checkpoint_inventory.json":
            return {"schema": "fake-checkpoint-inventory"}
        raise AssertionError(path)

    monkeypatch.setattr(runner, "load_json_strict", fake_json)
    monkeypatch.setattr(runner, "sha256_file", lambda path: "e" * 64)
    monkeypatch.setattr(runner, "load_contract", lambda *args, **kwargs: {"fake": 1})

    def verify_bundle(*args: object, **kwargs: object) -> None:
        captured["checkpoint_keys"] = set(kwargs["expected_checkpoint_keys"])
        captured["expected_inputs"] = kwargs["expected_inputs"]

    monkeypatch.setattr(runner, "verify_checkpoint_inventory_bundle", verify_bundle)

    report, training, holdout, states = runner._validate_grid(config, contract)

    assert report["status"] == "verified"
    assert len(training) == 541
    assert len(holdout) == 530
    assert len(states) == 1071
    assert captured["members"] == tuple(exact_members)
    assert len(captured["checkpoint_keys"]) == 1071
    assert captured["expected_inputs"] == {
        "power_system_blocks_manifest_sha256": "1" * 64,
        "rts_gmlc_source_manifest_sha256": "2" * 64,
    }

    monkeypatch.setattr(runner, "sha256_file", lambda path: "9" * 64)
    with pytest.raises(ValueError, match="grid provenance hash drifted"):
        runner._validate_grid(config, contract)


def test_canonical_v2_activation_absence_blocks_before_any_side_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for name in (
        "external_inputs_ready",
        "independent_review",
        "user_execution_authorized",
        "execution_ready",
    ):
        config["execution"][name] = True
        config["gates"][name] = True
    context = {"report": {"preflight_ready": True}}
    monkeypatch.setattr(runner, "_preflight", lambda *args, **kwargs: (config, context))
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: pytest.fail("mkdir"))
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(
        runner.ExecutionLease,
        "acquire",
        lambda *args, **kwargs: pytest.fail("lease"),
    )
    monkeypatch.setattr(
        runner, "compute_planning_checkpoint", lambda **kwargs: pytest.fail("solver")
    )
    monkeypatch.setattr(
        runner, "require_execution_host", lambda execution: pytest.fail("host")
    )
    with pytest.raises(RuntimeError, match="activation_authority_absent"):
        runner.run(CONFIG, MANIFEST)


def test_alternate_self_signed_authority_is_rejected_by_preflight_and_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for name in (
        "external_inputs_ready",
        "independent_review",
        "user_execution_authorized",
        "execution_ready",
    ):
        config["execution"][name] = True
        config["gates"][name] = True
    activation_path = tmp_path / "caller-controlled-activation.yaml"
    activation_path.write_text("activated: true\n", encoding="utf-8")
    config["activation_authority"] = {
        "path": activation_path.name,
        "sha256": hashlib.sha256(activation_path.read_bytes()).hexdigest(),
        "activated": True,
    }
    live_runner_sha256 = hashlib.sha256(Path(runner.__file__).read_bytes()).hexdigest()
    config["implementation_authority"]["runner"]["sha256"] = live_runner_sha256
    config_path = tmp_path / "caller-config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["files"][runner.CONFIG_RELATIVE] = hashlib.sha256(
        config_path.read_bytes()
    ).hexdigest()
    manifest["files"][
        "experiments/run_rq2_public_baseline_robustness_entry_successor_v2.py"
    ] = live_runner_sha256
    manifest_path = tmp_path / "caller-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: pytest.fail("mkdir"))
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(
        runner.ExecutionLease,
        "acquire",
        lambda *args, **kwargs: pytest.fail("lease"),
    )
    monkeypatch.setattr(
        runner, "compute_planning_checkpoint", lambda **kwargs: pytest.fail("solver")
    )
    monkeypatch.setattr(
        runner, "compute_finite_pair_checkpoint", lambda **kwargs: pytest.fail("solver")
    )

    with pytest.raises(ValueError, match="canonical v2 repository authority"):
        runner._preflight(config_path, manifest_path)
    with pytest.raises(ValueError, match="canonical v2 repository authority"):
        runner.external_preflight(config_path, manifest_path)
    with pytest.raises(ValueError, match="canonical v2 repository authority"):
        runner.run(config_path, manifest_path)


def test_runner_imports_only_registered_public_scientific_apis() -> None:
    tree = ast.parse(
        (ROOT / "experiments/run_rq2_public_baseline_robustness_entry_successor_v2.py")
        .read_text(encoding="utf-8")
    )
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {
        "load_workload_blocks",
        "load_power_blocks_with_state",
        "condition_on_grid_evaluable",
        "expand_parameter_cells",
        "select_weighted_quantile_representatives",
        "training_model_inputs",
        "pair_scenario",
        "envelope_for_cell",
        "solver_spec",
        "compute_planning_checkpoint",
        "compute_finite_pair_checkpoint",
        "build_E0_pair_checkpoint",
        "write_checkpoint_idempotent",
        "publish_final_package",
    }.issubset(imported)
    experiment_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("experiments.")
    }
    assert experiment_imports == {
        "experiments.validate_rq2_public_baseline_robustness_entry_successor_v2"
    }


def test_training_only_partial_resume_and_complete_E0_cartesian(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, context, paths = _ready_contract(tmp_path)
    calls = _patch_ready_runtime(monkeypatch, config, context, paths)

    partial = runner._run_ready(config, context, maximum_pairs=1)

    assert partial["published"] is False
    assert partial["completed_pairs"] == 1
    assert calls["planning"] == 1
    assert calls["planning_power_ids"] == ("training-finite",)
    assert calls["planning_workload_ids"] == ("workload-training",)
    assert all(
        "holdout" not in name for name in calls["training_scenario_names"]
    )
    assert calls["E0"] == 1
    assert calls["finite"] == 0
    assert not paths["output"].exists()

    complete = runner._run_ready(config, context, maximum_pairs=2)

    assert complete["published"] is True
    assert complete["completed_pairs"] == 2
    assert calls["planning"] == 1
    assert calls["E0"] == 1
    assert calls["finite"] == 1
    publications = calls["publish"]
    assert [len(item["pair_checkpoint_paths"]) for item in publications] == [1, 2]
    assert {
        item["grid_state"] for item in publications[-1]["expected_pairs"]
    } == {
        runner.FINITE_GRID_NEED,
        runner.EXOGENOUS_GRID_INFEASIBILITY,
    }
    assert len(list(paths["lease-root"].glob("history/*.released"))) == 2


def test_existing_identity_drift_and_active_terminal_lease_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, context, paths = _ready_contract(tmp_path)
    calls = _patch_ready_runtime(monkeypatch, config, context, paths)
    runner._run_ready(config, context, maximum_pairs=1)
    planning_path = paths["checkpoint-root"] / "planning/base.json"
    planning = json.loads(planning_path.read_text(encoding="utf-8"))
    planning["resume_identity"]["identity_sha256"] = "f" * 64
    planning_path.write_text(json.dumps(planning), encoding="utf-8")

    with pytest.raises(ValueError, match="resume identity drifted"):
        runner._run_ready(config, context, maximum_pairs=2)
    assert calls["planning"] == 1

    planning["resume_identity"] = json.loads(
        (
            paths["checkpoint-root"]
            / "pairs/base/holdout-E0/workload-holdout.json"
        ).read_text(encoding="utf-8")
    )["resume_identity"]
    planning_path.write_text(json.dumps(planning), encoding="utf-8")
    active = paths["lease-root"] / "active"
    active.mkdir()
    (active / "terminal.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="blocks takeover"):
        runner._run_ready(config, context, maximum_pairs=2)
    assert calls["planning"] == 1


def test_solver_exception_creates_only_failed_lease_not_final_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, context, paths = _ready_contract(tmp_path)
    _patch_ready_runtime(monkeypatch, config, context, paths)
    monkeypatch.setattr(
        runner,
        "compute_planning_checkpoint",
        lambda **kwargs: (_ for _ in ()).throw(TimeoutError("synthetic timeout")),
    )

    with pytest.raises(TimeoutError, match="synthetic timeout"):
        runner._run_ready(config, context, maximum_pairs=None)

    assert not paths["output"].exists()
    assert not paths["checkpoint-root"].exists()
    failed = list(paths["lease-root"].glob("history/*.failed"))
    assert len(failed) == 1
    terminal = json.loads((failed[0] / "terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "failed"
    assert "timeout" in terminal["error_message"]


def test_unresolved_planning_is_progress_not_infeasibility_or_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config, context, paths = _ready_contract(tmp_path)
    calls = _patch_ready_runtime(monkeypatch, config, context, paths)

    def unresolved(**kwargs: object) -> dict[str, object]:
        calls["planning"] = int(calls["planning"]) + 1
        return {
            "cell_id": kwargs["cell_id"],
            "disposition": "unresolved",
            "resume_identity": kwargs["resume_identity"],
            "provenance": kwargs["provenance"],
            "four_arm_minimum_flexibility": [],
        }

    monkeypatch.setattr(runner, "compute_planning_checkpoint", unresolved)
    progress = runner._run_ready(config, context, maximum_pairs=None)

    assert progress["status"] == "blocked_unresolved_planning"
    assert "infeasible" not in json.dumps(progress).casefold()
    assert progress["published"] is False
    assert calls["publish"] == []
    assert not paths["output"].exists()


def test_checkpoint_root_rejects_extra_and_reparse_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "checkpoints"
    root.mkdir()
    extra = root / "extra.json"
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="extra file"):
        runner._scan_checkpoint_root(root, {Path("planning/base.json")})
    extra.unlink()
    alias = root / "planning"
    alias.mkdir()
    real_reparse = runner._path_is_reparse
    monkeypatch.setattr(
        runner,
        "_path_is_reparse",
        lambda path: Path(path) == alias or real_reparse(Path(path)),
    )
    with pytest.raises(ValueError, match="reparse entry"):
        runner._scan_checkpoint_root(root, {Path("planning/base.json")})


def test_pure_validator_is_read_only_and_does_not_import_runtime_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("src") for name in imports)
    namespace = _validator_namespace()
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))
    result = namespace["validate"](CONFIG, MANIFEST)
    assert result["validation_passed"] is True
    assert result["activation_authority_present"] is False
    assert result["solver_calls"] == 0
    assert result["result_files_written"] == 0


def test_validator_rejects_gate_elevation_even_with_recomputed_manifest(
    tmp_path: Path,
) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["execution"]["execution_ready"] = True
    config["gates"]["execution_ready"] = True
    config_path = tmp_path / "mutated.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["files"][runner.CONFIG_RELATIVE] = hashlib.sha256(
        config_path.read_bytes()
    ).hexdigest()
    manifest_path = tmp_path / "mutated.SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    namespace = _validator_namespace()
    with pytest.raises(ValueError, match="execution gate execution_ready"):
        namespace["validate"](config_path, manifest_path)


def test_validator_rejects_activation_authority_even_with_recomputed_manifest(
    tmp_path: Path,
) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["activation_authority"] = {
        "path": "caller-activation.yaml",
        "sha256": "7" * 64,
        "activated": True,
    }
    config_path = tmp_path / "activated.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["files"][runner.CONFIG_RELATIVE] = hashlib.sha256(
        config_path.read_bytes()
    ).hexdigest()
    manifest_path = tmp_path / "activated.SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    namespace = _validator_namespace()
    with pytest.raises(ValueError, match="activation authority"):
        namespace["validate"](config_path, manifest_path)
