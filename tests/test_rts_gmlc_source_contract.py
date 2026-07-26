from pathlib import Path

import pytest
import yaml

import experiments.run_rts24_load_conditions as load_conditions
import experiments.validate_rts_gmlc_data as validation
from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
    validate_rts_gmlc_source_identity,
)


def _canonical_source(path: Path) -> dict[str, object]:
    return {
        "repository": RTS_GMLC_REPOSITORY,
        "release": RTS_GMLC_RELEASE,
        "commit": RTS_GMLC_COMMIT,
        "path": str(path),
        "manifest_sha256": RTS_GMLC_MANIFEST_SHA256,
    }


def _write_validation_config(path: Path, source: dict[str, object]) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "source": source,
                "expected": {},
                "legacy_rts24_proxy": {},
                "output": {},
            }
        ),
        encoding="utf-8",
    )


def _write_load_condition_config(path: Path, source: dict[str, object]) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "source": source,
                "legacy_rts24_proxy": {},
                "security_snapshot_audit": {},
                "output": {},
            }
        ),
        encoding="utf-8",
    )


def test_rts_gmlc_source_identity_accepts_only_the_pinned_tuple(tmp_path):
    validate_rts_gmlc_source_identity(_canonical_source(tmp_path))


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("repository", "https://github.com/example/RTS-GMLC"),
        ("release", "v0.2.4"),
        ("commit", "0" * 40),
    ],
)
def test_rts_gmlc_source_identity_rejects_drift(tmp_path, field, replacement):
    source = _canonical_source(tmp_path)
    source[field] = replacement

    with pytest.raises(ValueError, match=rf"identity drifted: {field}"):
        validate_rts_gmlc_source_identity(source)


@pytest.mark.parametrize("field", ["repository", "release", "commit"])
def test_rts_gmlc_source_identity_rejects_missing_fields(tmp_path, field):
    source = _canonical_source(tmp_path)
    del source[field]

    with pytest.raises(ValueError, match=rf"identity drifted: {field}"):
        validate_rts_gmlc_source_identity(source)


def test_validation_rejects_identity_drift_before_source_io(tmp_path):
    source = _canonical_source(tmp_path / "missing")
    source["release"] = "v0.2.4"
    config_path = tmp_path / "validation.yaml"
    _write_validation_config(config_path, source)

    with pytest.raises(ValueError, match="identity drifted: release"):
        validation.run(config_path)


def test_validation_rejects_a_configured_manifest_lock_drift_before_io(tmp_path):
    source = _canonical_source(tmp_path / "missing")
    source["manifest_sha256"] = "0" * 64
    config_path = tmp_path / "validation.yaml"
    _write_validation_config(config_path, source)

    with pytest.raises(ValueError, match="manifest lock drifted"):
        validation.run(config_path)


def test_validation_rejects_the_observed_manifest_hash_before_data_io(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "SHA256SUMS").write_text("tampered\n", encoding="ascii")
    config_path = tmp_path / "validation.yaml"
    _write_validation_config(config_path, _canonical_source(source_root))

    with pytest.raises(ValueError, match="manifest SHA-256 drifted"):
        validation.run(config_path)


def test_load_condition_runner_rejects_identity_drift_before_source_io(tmp_path):
    source = _canonical_source(tmp_path / "missing")
    source["repository"] = "https://github.com/example/RTS-GMLC"
    config_path = tmp_path / "load_conditions.yaml"
    _write_load_condition_config(config_path, source)

    with pytest.raises(ValueError, match="identity drifted: repository"):
        load_conditions.run(config_path)


def test_load_condition_runner_rejects_manifest_hash_before_grid_loading(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "SHA256SUMS").write_text("tampered\n", encoding="ascii")
    config_path = tmp_path / "load_conditions.yaml"
    _write_load_condition_config(config_path, _canonical_source(source_root))

    with pytest.raises(ValueError, match="manifest SHA-256 drifted"):
        load_conditions.run(config_path)
