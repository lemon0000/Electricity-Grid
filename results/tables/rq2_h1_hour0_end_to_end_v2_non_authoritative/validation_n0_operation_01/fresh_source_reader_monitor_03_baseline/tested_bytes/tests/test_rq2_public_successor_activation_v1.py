from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments import activate_rq2_public_successor_v1 as activation


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_preflight(root: Path, report: dict[str, object]) -> str:
    root.mkdir()
    (root / "config.yaml").write_text("schema: test\n", encoding="utf-8")
    (root / "preflight.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        name: _sha256(root / name)
        for name in ("config.yaml", "preflight.json")
    }
    (root / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _sha256(root / "SHA256SUMS.json")


def _preflight_report(bundle_manifest: Path) -> dict[str, object]:
    smoke = {
        "termination_condition": "optimal",
        "objective_incumbent": 1.0,
        "lower_bound": 1.0,
        "upper_bound": 1.0,
        "model_variables": 1,
        "model_constraints": 1,
    }
    return {
        "schema": "rq2_public_executor_preflight_v1",
        "config_sha256": "handoff",
        "bundle": {
            "bundle_manifest_path": str(bundle_manifest),
            "bundle_manifest_sha256": _sha256(bundle_manifest),
        },
        "formal_execution_started": False,
        "environment": {"matches_executor_lock": True},
        "execution_host": {
            "hostname_allowed": True,
            "environment_authorized": True,
        },
        "solver_smokes": [
            {**smoke, "solver_name": "highs"},
            {**smoke, "solver_name": "gurobi"},
        ],
    }


def test_runtime_preflight_requires_complete_bound_receipt(tmp_path):
    bundle_manifest = tmp_path / "bundle.json"
    bundle_manifest.write_text("{}\n", encoding="utf-8")
    root = tmp_path / "preflight"
    report = _preflight_report(bundle_manifest)
    manifest_sha = _write_preflight(root, report)
    payload = {
        "successor": {"executor_handoff_sha256": "handoff"},
        "runtime_preflight": {
            "required": True,
            "passed": True,
            "result_directory": str(root),
            "result_manifest_sha256": manifest_sha,
        },
    }

    activation._verify_runtime_preflight(payload)

    report["environment"]["matches_executor_lock"] = False
    manifest_sha = _write_preflight(tmp_path / "invalid", report)
    payload["runtime_preflight"]["result_directory"] = str(
        tmp_path / "invalid"
    )
    payload["runtime_preflight"]["result_manifest_sha256"] = manifest_sha
    with pytest.raises(RuntimeError, match="preflight evidence is invalid"):
        activation._verify_runtime_preflight(payload)


def test_stage_template_hash_is_bound_by_activation():
    handoff = yaml.safe_load(
        Path("configs/rq2_public_executor_handoff_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload = yaml.safe_load(
        Path("configs/rq2_public_successor_activation_v1.yaml").read_text(
            encoding="utf-8"
        )
    )

    path, config = activation._template(
        handoff,
        "grid_config_template",
        payload,
        "grid",
    )
    assert path == Path(
        "configs/rts_gmlc_public_grid_need_dispatch_v4.yaml"
    ).resolve()
    assert config["output"]["schema"] == "rts_gmlc_public_grid_need_dispatch_v4"

    payload["successor"]["stage_templates"]["grid"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="template authority drifted"):
        activation._template(
            handoff,
            "grid_config_template",
            payload,
            "grid",
        )
