"""Validate the H2 temporal executor-entry successor without running jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from experiments import validate_rq2_h2_temporal_successor_preregistration as v1


_ROOT = Path(__file__).resolve().parents[1]
_SUCCESSOR_CONFIG = (
    _ROOT / "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
)
_SUCCESSOR_MANIFEST = (
    _ROOT
    / "configs/rq2_h2_temporal_executor_entry_successor_v2.SHA256SUMS.json"
)
_PREDECESSOR_AUTHORITY = {
    "configs/rq2_h2_temporal_successor_preregistration_v1.yaml": (
        "3f519f1fe33169585eea6561ff0d2fd26a761af553529a58b4288b16a5ba00d2"
    ),
    "configs/rq2_h2_temporal_successor_preregistration_v1.SHA256SUMS.json": (
        "bdd8d10b234852ed00a2b4a70919ee102731f0d421e01b97a528c732f1619d79"
    ),
    "experiments/validate_rq2_h2_temporal_successor_preregistration.py": (
        "4566c21f1a741b0d97813c6e0fc9ca0cd05bb1ae6860c4f81342e566c240c761"
    ),
    "tests/test_rq2_formal_batch.py": (
        "349ca9c0e798f5561b746181840a79181526120a3e189d67cea622c680366550"
    ),
}
_RUNNER = "scripts/run_experiment.ps1"
_SUCCESSOR_CONFIG_RELATIVE = (
    "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
)
_SUCCESSOR_VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_h2_temporal_executor_entry_successor_v2.py"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def validate(
    successor_config_path: Path = _SUCCESSOR_CONFIG,
    successor_manifest_path: Path = _SUCCESSOR_MANIFEST,
) -> dict[str, object]:
    """Replay every v1 scientific check with only the executor binding replaced."""

    for relative, expected in _PREDECESSOR_AUTHORITY.items():
        observed = _sha256(_ROOT / relative)
        if observed != expected:
            raise ValueError(
                f"H2 predecessor authority drifted for {relative}: "
                f"expected {expected}, observed {observed}"
            )

    successor_config_path = successor_config_path.resolve()
    successor_manifest_path = successor_manifest_path.resolve()
    successor = _mapping(
        yaml.safe_load(successor_config_path.read_text(encoding="utf-8")),
        "successor config",
    )
    if successor.get("schema") != "rq2_h2_temporal_executor_entry_successor_v2":
        raise ValueError("H2 executor-entry successor schema drifted")
    predecessor = _mapping(successor.get("predecessor"), "predecessor")
    for relative, expected in _PREDECESSOR_AUTHORITY.items():
        if relative.endswith("preregistration_v1.yaml"):
            declared = predecessor.get("preregistration_sha256")
        elif relative.endswith("preregistration_v1.SHA256SUMS.json"):
            declared = predecessor.get("manifest_sha256")
        elif relative.endswith("preregistration.py"):
            declared = predecessor.get("validator_sha256")
        else:
            declared = successor["predecessor_validator_retirement"].get(
                "test_file_sha256"
            )
        if declared != expected:
            raise ValueError(f"H2 predecessor binding drifted for {relative}")
    if predecessor.get("immutable") is not True:
        raise ValueError("H2 predecessor must remain immutable")

    amendment = _mapping(successor.get("successor"), "successor")
    if amendment.get("change_scope") != "executor_tag_entry_only":
        raise ValueError("H2 successor change scope drifted")
    if amendment.get("executor_path") != _RUNNER:
        raise ValueError("H2 successor executor path drifted")
    if amendment.get("executor_sha256") != _sha256(_ROOT / _RUNNER):
        raise ValueError("H2 successor executor binding drifted")
    if amendment.get("validator_path") != _SUCCESSOR_VALIDATOR_RELATIVE:
        raise ValueError("H2 successor validator path drifted")
    if amendment.get("validator_sha256") != _sha256(Path(__file__).resolve()):
        raise ValueError("H2 successor validator binding drifted")
    if amendment.get("manifest_path") != str(
        successor_manifest_path.relative_to(_ROOT)
    ).replace("\\", "/"):
        raise ValueError("H2 successor manifest path drifted")
    for field in (
        "scientific_design_changed",
        "thresholds_changed",
        "seeds_changed",
        "sample_sizes_changed",
        "model_or_solver_semantics_changed",
        "prior_results_changed",
    ):
        if amendment.get(field) is not False:
            raise ValueError(f"H2 successor must keep {field}=false")

    predecessor_manifest = json.loads(
        (_ROOT / predecessor["manifest_path"]).read_text(encoding="utf-8")
    )
    successor_manifest = json.loads(
        successor_manifest_path.read_text(encoding="utf-8")
    )
    expected_manifest = dict(predecessor_manifest)
    expected_manifest[_RUNNER] = amendment["executor_sha256"]
    expected_manifest[_SUCCESSOR_CONFIG_RELATIVE] = _sha256(
        successor_config_path
    )
    expected_manifest[_SUCCESSOR_VALIDATOR_RELATIVE] = _sha256(
        Path(__file__).resolve()
    )
    if successor_manifest != expected_manifest:
        raise ValueError(
            "H2 successor manifest must equal the predecessor inventory with "
            "only the current executor plus versioned config/validator bindings"
        )
    for relative, expected in predecessor_manifest.items():
        if relative != _RUNNER and successor_manifest.get(relative) != expected:
            raise ValueError(f"H2 non-executor predecessor hash drifted: {relative}")

    original_hash_paths = v1._HASH_PATHS
    if original_hash_paths.get("executor_script_sha256") != _RUNNER:
        raise ValueError("H2 predecessor validator executor key drifted")
    successor_hash_paths = {
        key: value
        for key, value in original_hash_paths.items()
        if key != "executor_script_sha256"
    }
    v1._HASH_PATHS = successor_hash_paths
    try:
        report = v1.validate(
            _ROOT / predecessor["preregistration_path"],
            successor_manifest_path,
        )
    finally:
        v1._HASH_PATHS = original_hash_paths

    if report.get("validation_passed") is not True:
        raise ValueError("H2 predecessor scientific validation did not pass")
    return {
        **report,
        "predecessor_scientific_validation_replayed": True,
        "executor_entry_successor_validated": True,
        "successor_manifest_file_count": len(successor_manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--successor-config", type=Path, default=_SUCCESSOR_CONFIG
    )
    parser.add_argument(
        "--successor-manifest", type=Path, default=_SUCCESSOR_MANIFEST
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.successor_config, args.successor_manifest),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
