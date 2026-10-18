from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

PREREGISTRATION = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v2.yaml"
)
OUTER_MANIFEST = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v2."
    "SHA256SUMS.json"
)
PACKAGE_MANIFESTS = {
    "rq2_joint_data_v1": Path(
        "data/processed/model_inputs/rq2_joint_data_v1/SHA256SUMS.json"
    ),
    "rts_gmlc_cfe_v2": Path(
        "data/processed/model_inputs/"
        "rts_gmlc_hourly_cfe_deficit_250mw_v2/SHA256SUMS.json"
    ),
    "alibaba_job_envelopes_v1": Path(
        "data/processed/model_inputs/"
        "alibaba_job_execution_envelopes_v1/SHA256SUMS.json"
    ),
    "alibaba_gpu_telemetry_v1": Path(
        "data/processed/model_inputs/alibaba_gpu_telemetry_v1/SHA256SUMS.json"
    ),
    "alibaba_dimensionless_workload_blocks_v2": Path(
        "data/processed/model_inputs/"
        "alibaba_dimensionless_workload_blocks_v2/SHA256SUMS.json"
    ),
    "wattgpu_v1": Path(
        "data/processed/model_inputs/wattgpu_power_reference_v1/SHA256SUMS.json"
    ),
    "nlr_v2": Path(
        "data/processed/model_inputs/nlr_genai_power_profiles_v2/SHA256SUMS.json"
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preregistration_v2_frozen_input_hashes_are_live():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    frozen = prereg["frozen_inputs"]

    for label in (
        "scientific_config",
        "analytic_module",
        "coupling_module",
        "identification_module",
        "bound_runner",
        "route_document",
        "workload_builder_config",
        "workload_builder",
        "workload_builder_tests",
        "preregistration_validator",
        "frozen_predecessor",
    ):
        item = frozen[label]
        assert _sha256(Path(item["path"])) == item["sha256"], label

    for path, expected in frozen["method_tests"].items():
        assert _sha256(Path(path)) == expected, path
    for label, path in PACKAGE_MANIFESTS.items():
        assert _sha256(path) == frozen["source_packages"][label], label


def test_preregistration_v2_keeps_unmet_activation_gates_closed():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    scientific = yaml.safe_load(
        Path(prereg["frozen_inputs"]["scientific_config"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    expected = {
        "hourly_outage_to_grid_need_dispatch_ready": False,
        "dimensionless_workload_blocks_ready": True,
        "complete_pairwise_outcomes_ready": False,
        "all_pairwise_optimizations_resolved": False,
        "independent_R4_review_passed": False,
        "user_formal_run_authorized": False,
    }
    assert prereg["activation_gates"] == {
        **expected,
        "formal_execution_ready": False,
    }
    assert scientific["execution"]["activation_gates"] == expected
    assert scientific["execution"]["formal_execution_ready"] is False
    assert prereg["preregistration"]["formal_execution_ready"] is False
    assert prereg["preregistration"]["formal_result"] is False
    assert prereg["preregistration"]["security_certified"] is False


def test_preregistration_v2_outer_manifest_is_live():
    manifest = json.loads(OUTER_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "rq2_public_data_preregistration_manifest_v2"
    assert all(
        _sha256(Path(path)) == expected
        for path, expected in manifest["files"].items()
    )
