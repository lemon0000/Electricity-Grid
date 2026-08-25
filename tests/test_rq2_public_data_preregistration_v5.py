from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

PREREGISTRATION = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v5.yaml"
)
OUTER_MANIFEST = Path(
    "configs/rq2_public_data_robust_identification_preregistration_v5."
    "SHA256SUMS.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preregistration_v5_frozen_hashes_are_live():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    for label, item in prereg["frozen_inputs"].items():
        if label == "source_packages":
            continue
        assert _sha256(Path(item["path"])) == item["sha256"], label
    for label, item in prereg["frozen_inputs"]["source_packages"].items():
        assert _sha256(Path(item["manifest_path"])) == item["sha256"], label


def test_preregistration_v5_keeps_every_formal_gate_closed():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    gates = prereg["activation_gates"]

    assert gates == {
        "grid_need_dispatch_ready": False,
        "pairwise_replay_ready": False,
        "complete_pairwise_outcomes_ready": False,
        "all_pairwise_optimizations_resolved": False,
        "independent_R4_review_passed": False,
        "user_formal_run_authorized": True,
        "formal_execution_ready": False,
    }
    for config_key in (
        "grid_need_config",
        "pairwise_config",
        "identification_config",
    ):
        config = yaml.safe_load(
            Path(prereg["frozen_inputs"][config_key]["path"]).read_text(
                encoding="utf-8"
            )
        )
        assert config["execution"]["formal_execution_ready"] is False
        assert config["execution"]["user_formal_run_authorized"] is True


def test_preregistration_v5_outer_manifest_is_live():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    manifest = json.loads(OUTER_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "rq2_public_data_preregistration_manifest_v5"
    expected_paths = {str(PREREGISTRATION)}
    for label, item in prereg["frozen_inputs"].items():
        if label == "source_packages":
            expected_paths.update(
                source["manifest_path"] for source in item.values()
            )
        else:
            expected_paths.add(item["path"])
    assert set(manifest["files"]) == expected_paths
    assert all(
        _sha256(Path(path)) == expected
        for path, expected in manifest["files"].items()
    )
