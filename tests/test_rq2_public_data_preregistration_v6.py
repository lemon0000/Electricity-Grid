from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import yaml

from experiments.preflight_rq2_public_executor_v1 import run as run_preflight

PREREGISTRATION = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v6.yaml"
)
OUTER_MANIFEST = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v6."
    "SHA256SUMS.json"
)
BUNDLE_MANIFEST = Path(
    "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json"
)
ACTIVATION = Path("configs/rq2_public_successor_activation_v1.yaml")
HANDOFF = Path("configs/rq2_public_executor_handoff_v1.yaml")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frozen_paths(preregistration: dict[str, object]) -> set[str]:
    paths = {str(PREREGISTRATION)}
    for label, item in preregistration["frozen_inputs"].items():
        if label == "source_packages":
            paths.update(
                source["manifest_path"] for source in item.values()
            )
        else:
            paths.add(item["path"])
    return paths


def test_preregistration_v6_frozen_hashes_and_outer_manifest_are_live():
    preregistration = yaml.safe_load(
        PREREGISTRATION.read_text(encoding="utf-8")
    )
    manifest = json.loads(OUTER_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "rq2_public_data_preregistration_manifest_v6"
    assert set(manifest["files"]) == _frozen_paths(preregistration)
    assert all(
        _sha256(Path(path)) == expected
        for path, expected in manifest["files"].items()
    )


def test_v6_isolates_unverifiable_predecessor_from_execution():
    preregistration = yaml.safe_load(
        PREREGISTRATION.read_text(encoding="utf-8")
    )
    historical = preregistration["historical_predecessor_records"]
    assert historical["execution_dependency"] is False
    assert historical["formal_resume_allowed"] is False
    assert historical["unavailable_formulation_sha256"] == (
        "dad0fe7e59f611dc627cd697e06049e7f349cb9e6b92ff7b433514704843a3fb"
    )
    historical_paths = {
        historical["preregistration"]["path"],
        historical["preregistration_manifest"]["path"],
    }
    outer = json.loads(OUTER_MANIFEST.read_text(encoding="utf-8"))
    bundle = json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))
    assert historical_paths.isdisjoint(outer["files"])
    assert historical_paths.isdisjoint(bundle["files"])
    retired = historical["retired_formal_config"]
    assert _sha256(Path(retired["path"])) == retired["sha256"]
    assert retired["path"] in outer["files"]
    assert retired["path"] in bundle["files"]
    retired_config = yaml.safe_load(
        Path(retired["path"]).read_text(encoding="utf-8")
    )
    assert retired_config["execution"]["formal_execution_ready"] is False
    assert retired_config["execution"]["independent_R4_review_passed"] is False
    assert retired_config["execution"]["user_formal_run_authorized"] is False
    assert (
        retired_config["execution"]["predecessor_checkpoint_reuse_allowed"]
        is False
    )


def test_preregistration_v6_keeps_executor_and_formal_gates_closed():
    preregistration = yaml.safe_load(
        PREREGISTRATION.read_text(encoding="utf-8")
    )
    gates = preregistration["activation_gates"]
    assert gates["executor_bundle_verified"] is False
    assert gates["executor_runtime_preflight_passed"] is False
    assert gates["cross_solver_pilot_passed"] is False
    assert gates["independent_R4_review_passed"] is False
    assert gates["grid_need_dispatch_ready"] is False
    assert gates["pairwise_replay_ready"] is False
    assert gates["identification_ready"] is False
    assert gates["formal_execution_ready"] is False

    activation = yaml.safe_load(ACTIVATION.read_text(encoding="utf-8"))
    successor = activation["successor"]
    assert (
        _sha256(Path(successor["executor_handoff_path"]))
        == successor["executor_handoff_sha256"]
    )
    for template in successor["stage_templates"].values():
        assert _sha256(Path(template["path"])) == template["sha256"]
    assert activation["review"]["independent_R4_review_passed"] is False
    assert activation["runtime_preflight"]["passed"] is False
    assert activation["runtime_preflight"]["result_manifest_sha256"] is None
    pilot_config = activation["solver_pilot"]
    assert _sha256(Path(pilot_config["config_path"])) == pilot_config[
        "config_sha256"
    ]
    assert activation["solver_pilot"]["result_manifest_sha256"] is None
    assert (
        activation["solver_pilot"]["gurobi_eligible_for_formal_successor"]
        is False
    )
    assert activation["formal_execution"]["grid_need_dispatch_ready"] is False
    assert activation["formal_execution"]["pairwise_replay_ready"] is False
    assert activation["formal_execution"]["identification_ready"] is False
    assert activation["formal_execution"]["formal_execution_ready"] is False
    assert activation["claims"]["formal_result_exists"] is False


def test_executor_bundle_has_the_exact_frozen_execution_inventory():
    outer = json.loads(OUTER_MANIFEST.read_text(encoding="utf-8"))
    contract = yaml.safe_load(
        Path(
            "configs/rq2_public_pipeline_provenance_contract_v3.yaml"
        ).read_text(encoding="utf-8")
    )
    expected_paths = set(outer["files"])
    expected_paths.add(str(OUTER_MANIFEST))
    for stage in contract["stages"].values():
        expected_paths.add(stage["runner"]["path"])
        expected_paths.update(
            module["path"] for module in stage["modules"].values()
        )

    bundle = json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))
    assert bundle["schema"] == "rq2_public_executor_bundle_manifest_v1"
    assert set(bundle["files"]) == expected_paths
    for name, expected in bundle["files"].items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        path = Path(name)
        assert path.is_file()
        assert not path.is_symlink()
        assert _sha256(path) == expected


def test_executor_static_verify_checks_bundle_and_nested_manifests():
    report = run_preflight(HANDOFF, verify_only=True)
    assert report["schema"] == "rq2_public_executor_bundle_verification_v1"
    assert report["formal_execution_started"] is False
    assert report["bundle"]["bundle_file_count"] == 53
    assert report["bundle"]["nested_package_member_counts"] == {
        "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3": 4,
        "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4": 5,
        "data/raw/rts_gmlc/v0.2.3/upstream": 25,
    }
