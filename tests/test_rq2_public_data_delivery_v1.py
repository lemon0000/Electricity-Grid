"""Focused checks for the non-authoritative RQ2 public-data delivery."""

from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import io
import json
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from experiments.prepare_rq2_public_data_delivery_v1 import (
    DATASET_IDS,
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    DELIVERY_FILES,
    EVIDENCE_CLASSES,
    PROTOCOL_CHOICES,
    REQUIRED_FALSE_GATES,
    TRUE_GATES,
    _build_catalog,
    _build_google_flat,
    _iter_raw_records,
    _load_and_validate_config,
    _sha256,
    load_records,
    verify_existing,
)


def _json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _config_copy(tmp_path: Path, mutate) -> Path:
    config = yaml.safe_load(DEFAULT_CONFIG.read_bytes())
    mutate(config)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def test_config_inventory_and_high_risk_contract_are_exact():
    config = _load_and_validate_config(DEFAULT_CONFIG)
    assert set(config["datasets"]) == DATASET_IDS
    assert set(config["gates"]) == REQUIRED_FALSE_GATES | TRUE_GATES
    assert all(config["gates"][name] is False for name in REQUIRED_FALSE_GATES)
    assert all(config["gates"][name] is True for name in TRUE_GATES)
    assert set(config["protocol_choices"]) == PROTOCOL_CHOICES
    assert all(
        choice["value"] is None and choice["status"] == "unregistered"
        for choice in config["protocol_choices"].values()
    )


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda c: c["datasets"].pop("google_pdu17_capacity"), "dataset inventory"),
        (lambda c: c["protocol_choices"].pop("tail_handling"), "protocol-choice inventory"),
        (lambda c: c["gates"].update({"new_model_ready_alias": True}), "gate inventory"),
    ],
)
def test_config_rejects_inventory_drift(tmp_path, mutate, message):
    path = _config_copy(tmp_path, mutate)
    with pytest.raises(ValueError, match=message):
        _load_and_validate_config(path)


def test_catalog_verifies_all_sources_and_uses_two_field_axes():
    config = _load_and_validate_config(DEFAULT_CONFIG)
    catalog, dictionary, _ = _build_catalog(config)
    assert set(catalog) == DATASET_IDS
    assert len(dictionary) == sum(
        len(entry["schema_fields"]) for entry in catalog.values()
    )
    assert all(row["evidence_class"] in EVIDENCE_CLASSES for row in dictionary)
    assert all(row["role"] in {"identifier", "value", "diagnostic"} for row in dictionary)
    indexed = {(row["dataset_id"], row["field"]): row for row in dictionary}
    assert indexed[("google_power_57_domains", "bad_production_power_data")][
        "evidence_class"
    ] == "observed_source_value"
    assert indexed[("google_power_57_domains", "bad_production_power_data")][
        "role"
    ] == "diagnostic"
    assert indexed[("google_pdu17_744h_pair", "power.measured_power_util_mean")][
        "evidence_class"
    ] == "derived_from_observed_source"
    assert indexed[("alibaba_dimensionless_workload_blocks_v3", "split")][
        "evidence_class"
    ] == "derived_from_observed_source"
    assert indexed[("nlr_genai_power_profiles_v2", "mean_compute_power_w")][
        "evidence_class"
    ] == "derived_from_observed_source"
    assert indexed[("wattgpu_power_reference_v1", "reported_mean_gpu_power_w")][
        "evidence_class"
    ] == "observed_source_value"
    assert indexed[("wattgpu_power_reference_v1", "median_request_latency_s")][
        "evidence_class"
    ] == "derived_from_observed_source"


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("primary", "data/processed/does_not_exist.csv.gz", "No such file"),
        ("primary_sha256", "0" * 64, "primary hash drifted"),
        ("expected_schema", "wrong_schema", "summary schema drifted"),
    ],
)
def test_catalog_rejects_missing_hash_or_schema_drift(field, value, message):
    config = copy.deepcopy(_load_and_validate_config(DEFAULT_CONFIG))
    config["datasets"]["wattgpu_power_reference_v1"][field] = value
    with pytest.raises((FileNotFoundError, ValueError), match=message):
        _build_catalog(config)


def test_csv_loader_preserves_zero_and_maps_only_empty_to_null(tmp_path):
    path = tmp_path / "values.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(["missing", "zero", "above_one", "nan_text"])
        writer.writerow(["", "0", "1.070370705271957780430251624", "nan"])
    row = next(_iter_raw_records(path, "csv_gzip"))
    assert row == {
        "missing": None,
        "zero": "0",
        "above_one": "1.070370705271957780430251624",
        "nan_text": "nan",
    }


def test_public_loader_preserves_actual_unclipped_values_and_nulls():
    rows = load_records(
        "alibaba_dimensionless_workload_blocks_v3", limit=None, verify=False
    )
    values = [Decimal(row["workload_fraction"]) for row in rows]
    assert max(values) == Decimal("1.070370705271957780430251624")
    assert sum(value > 1 for value in values) == 6
    wattgpu = load_records("wattgpu_power_reference_v1", limit=1, verify=False)
    assert wattgpu[0]["arrival_rate_qps"] is None
    assert wattgpu[0]["median_time_to_first_token_s"] is None


def test_google_flattening_is_deterministic_and_keeps_diagnostics():
    config = _load_and_validate_config(DEFAULT_CONFIG)
    pair_path = Path(config["datasets"]["google_pdu17_744h_pair"]["primary"])
    first_bytes, first_blocks = _build_google_flat(pair_path)
    second_bytes, second_blocks = _build_google_flat(pair_path)
    assert first_bytes == second_bytes
    assert first_blocks == second_blocks
    assert len(first_blocks) == 31
    with gzip.GzipFile(fileobj=io.BytesIO(first_bytes), mode="rb") as source:
        rows = [json.loads(line) for line in source]
    assert len(rows) == 744
    assert all(row["cpu_source_strata_count"] == 14 for row in rows)
    assert all(row["power_sample_count"] == 12 for row in rows)
    assert sum(
        Decimal(row["capacity"]["unknown_active_machine_seconds"]) > 0
        for row in rows
    ) == 16
    assert all(not row["power_quality_filter_applied"] for row in rows)


def test_generated_delivery_verifies_and_loader_is_bounded():
    summary = verify_existing()
    assert summary["scope"]["local_data_delivery_software_scope_complete"]
    assert not summary["scope"]["model_ready"]
    assert set(
        json.loads((DEFAULT_OUTPUT / "FILE_HASHES.json").read_text(encoding="utf-8"))
    ) == DELIVERY_FILES
    rows = load_records("alibaba_gpu_telemetry", limit=2)
    assert len(rows) == 2
    assert all(isinstance(row, dict) for row in rows)


def test_verify_rejects_coherently_rehashed_gate_tampering(tmp_path):
    target = tmp_path / "delivery"
    shutil.copytree(DEFAULT_OUTPUT, target)
    input_path = target / "input_status.json"
    input_status = json.loads(input_path.read_text(encoding="utf-8"))
    input_status["gates"]["formal_result"] = True
    _json_write(input_path, input_status)
    summary_path = target / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["output_bindings"]["input_status.json"] = _sha256(input_path)
    _json_write(summary_path, summary)
    hashes_path = target / "FILE_HASHES.json"
    hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    hashes["input_status.json"] = _sha256(input_path)
    hashes["summary.json"] = _sha256(summary_path)
    _json_write(hashes_path, hashes)
    with pytest.raises(ValueError, match="input status is stale"):
        verify_existing(delivery_root=target)


def test_verify_rejects_missing_hash_inventory_entry(tmp_path):
    target = tmp_path / "delivery"
    shutil.copytree(DEFAULT_OUTPUT, target)
    hashes_path = target / "FILE_HASHES.json"
    hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    hashes.pop("google_pdu17_hourly_flat.jsonl.gz")
    _json_write(hashes_path, hashes)
    with pytest.raises(ValueError, match="file-hash inventory drifted"):
        verify_existing(delivery_root=target)


def test_delivery_hashes_match_bytes():
    hashes = json.loads(
        (DEFAULT_OUTPUT / "FILE_HASHES.json").read_text(encoding="utf-8")
    )
    assert all(_sha256(DEFAULT_OUTPUT / name) == digest for name, digest in hashes.items())
    assert hashlib.sha256(
        (DEFAULT_OUTPUT / "google_pdu17_hourly_flat.jsonl.gz").read_bytes()
    ).hexdigest() == hashes["google_pdu17_hourly_flat.jsonl.gz"]
