from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import fetch_google_power_workload_multiday_v1 as target


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/google_power_workload_multiday_v1.DRAFT.yaml"


def _config() -> dict:
    return target._load_config(CONFIG_PATH)


def _audit() -> dict:
    return {
        "pdu_machine_count": 1295,
        "usage_source_rows": 1,
        "distinct_usage_value_groups": 1,
        "incomplete_or_invalid_key_rows": 0,
        "invalid_cpu_source_rows": 0,
        "coverage_mismatch_groups": 0,
        "overlapping_fragments": 0,
        "future_priority_rows": 0,
        "out_of_window_fragment_rows": 0,
        "inconsistent_cpu_variant_fragments": 0,
        "invalid_cpu_usage_groups": 0,
        "unexpected_collection_type_fragments": 0,
        "invalid_priority_fragments": 0,
    }


def _rows(config: dict) -> list[dict]:
    rows = []
    for hour in reversed(range(744)):
        for collection in (1, 0):
            for tier in reversed(config["expected"]["priority_tiers"]):
                rows.append(
                    {
                        "record_type": "hourly_usage",
                        "hour_index": hour,
                        "raw_interval_start_us": 600_000_000 + hour * target.HOUR_US,
                        "raw_interval_end_us": 600_000_000 + (hour + 1) * target.HOUR_US,
                        "collection_type": collection,
                        "priority_tier": tier,
                        "observed_cpu_ncu_lower": "0.000000000000",
                        "observed_cpu_ncu_upper": "0.000000000000",
                        "observed_cpu_time_ncu_seconds_lower": "0.000000000000",
                        "observed_cpu_time_ncu_seconds_upper": "0.000000000000",
                        "observed_cpu_overlap_seconds": "0.000000",
                        "missing_cpu_overlap_seconds": "0.000000",
                        "cpu_conflict_overlap_seconds": "0.000000",
                        "fragment_piece_count": 0,
                        "usage_group_count": 0,
                        "cpu_conflict_usage_group_count": 0,
                        "exact_duplicate_usage_group_count": 0,
                        "synthesized_cpu_time_ncu_seconds_lower": "0.000000000000",
                        "synthesized_cpu_time_ncu_seconds_upper": "0.000000000000",
                        "audit_json": None,
                    }
                )
    rows.append({"record_type": "audit", "audit_json": json.dumps(_audit())})
    return rows


def test_config_and_query_contract_is_fixed() -> None:
    config = _config()
    assert config["parameters"] == {
        "cell": "f",
        "pdu": "pdu17",
        "window_start_us": 600_000_000,
        "window_end_us": 2_679_000_000_000,
        "hours": 744,
        "expected_machine_count": 1295,
        "population": "official_notebook_non_nested_usage_with_machine_aware_asof_priority",
        "population_rule": "alloc_collection_id_is_null_or_zero_on_usage_and_instance_events",
    }
    sql_path = ROOT / config["source"]["query_path"]
    assert target._sha256(sql_path) == config["source"]["query_sha256"]
    sql = sql_path.read_text(encoding="utf-8")
    assert "SAFE_CAST(average_usage_cpus_float AS BIGNUMERIC)" in sql
    assert sql.count("alloc_collection_id IS NULL OR") == 2
    assert "event.machine_id" in sql
    assert "event.priority IS NOT NULL" not in sql
    assert "priority_event_prefilter" in sql
    assert "unusable_priority_event_rows" in sql
    assert "COUNTIF(priority IS NULL) = 0" in sql
    assert "source.pdu_machine_count = @expected_machine_count" in sql
    assert "hour_index * 3600000000" in sql


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cell", "a"),
        ("pdu", "pdu6"),
        ("window_start_us", 0),
        ("window_end_us", 86_400_000_000),
        ("expected_machine_count", 1294),
    ],
)
def test_config_rejects_population_or_clock_drift(tmp_path: Path, field: str, value) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["parameters"][field] = value
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(RuntimeError):
        target._load_config(path)


def test_job_config_preserves_query_parameters_and_billing_cap() -> None:
    config = _config()
    job_config = target._job_config(config, dry_run=False)
    assert job_config.use_query_cache is False
    assert job_config.maximum_bytes_billed == 600_000_000_000
    assert [(p.name, p.type_, p.value) for p in job_config.query_parameters] == [
        ("cell", "STRING", "f"),
        ("pdu", "STRING", "pdu17"),
        ("window_start_us", "INT64", 600_000_000),
        ("window_end_us", "INT64", 2_679_000_000_000),
        ("expected_machine_count", "INT64", 1295),
    ]


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("cost_gate", "task_cumulative_billed_cap_bytes", 2_000_000_000_000),
        ("cost_gate", "maximum_bytes_billed", 700_000_000_000),
        ("cost_gate", "query_job_id", "another-job"),
        ("cost_gate", "connectivity_job_id", "another-connectivity-job"),
        ("cost_gate", "oracle_job_id", "another-oracle-job"),
        ("source", "billing_project", "another-project"),
        ("source", "location", "EU"),
    ],
)
def test_config_rejects_billing_or_job_identity_drift(
    tmp_path: Path, section: str, field: str, value
) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config[section][field] = value
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(RuntimeError):
        target._load_config(path)


def test_submission_is_budget_guarded_and_existing_job_is_reused(monkeypatch) -> None:
    config = _config()

    class Client:
        calls = 0

        def query(self, *_args, **_kwargs):
            self.calls += 1
            return "submitted"

    client = Client()
    monkeypatch.setattr(target, "_get_job_or_none", lambda *_args: None)
    with pytest.raises(RuntimeError, match="cumulative billing cap"):
        target._get_or_submit_query_job(
            client,
            "SELECT 1",
            config,
            target.TASK_CUMULATIVE_BILLED_CAP_BYTES,
        )
    assert client.calls == 0

    existing = object()
    monkeypatch.setattr(target, "_get_job_or_none", lambda *_args: existing)
    assert target._get_or_submit_query_job(
        client,
        "SELECT 1",
        config,
        target.TASK_CUMULATIVE_BILLED_CAP_BYTES,
    ) is existing
    assert client.calls == 0


def test_result_grid_is_fail_closed_and_byte_stable(tmp_path: Path) -> None:
    config = _config()
    ordered, audit = target._validate_and_sort_rows(_rows(config), config)
    assert len(ordered) == 10_417
    assert audit["pdu_machine_count"] == 1295
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"
    target._write_csv_gzip(first, ordered, config["expected"]["fields"])
    target._write_csv_gzip(second, ordered, config["expected"]["fields"])
    assert first.read_bytes() == second.read_bytes()
    incomplete = _rows(config)
    incomplete.pop(0)
    with pytest.raises(RuntimeError, match="row counts"):
        target._validate_and_sort_rows(incomplete, config)


def test_verification_payload_accepts_nullable_optional_metadata() -> None:
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    job = SimpleNamespace(
        job_id="zero",
        query="SELECT 1",
        destination=None,
        created=now,
        started=now,
        ended=now,
        cache_hit=False,
        total_bytes_processed=0,
        total_bytes_billed=0,
        maximum_bytes_billed=None,
        labels=None,
    )
    payload = target._verification_job_payload(job)
    assert payload["maximum_bytes_billed"] is None
    assert payload["destination_table"] is None
    assert payload["labels"] == {}


def _write_bound_existing_output(root: Path, config: dict) -> None:
    query = ROOT / config["source"]["query_path"]
    oracle = ROOT / config["source"]["oracle_query_path"]
    (root / "query.sql").write_bytes(query.read_bytes())
    (root / "oracle_query.sql").write_bytes(oracle.read_bytes())
    (root / "config.yaml").write_bytes(CONFIG_PATH.read_bytes())
    (root / target.RAW_FILENAME).write_bytes(b"fixed-result")
    snapshots = {}
    for relative, frozen in config["expected"]["table_snapshots"].items():
        snapshots[relative] = {
            **frozen,
            "table_id": f"{config['source']['public_project']}.{relative}",
        }
    metadata = {
        "status": "DRAFT_NONAUTHORITATIVE_PUBLIC_DATA_ACQUISITION",
        "schema": "google_power_workload_multiday_bigquery_v1",
        "query_sha256": target._sha256(query),
        "oracle_query_sha256": target._sha256(oracle),
        "config_sha256": target._sha256(CONFIG_PATH),
        "implementation_sha256": target._sha256(Path(target.__file__)),
        "shared_helper_sha256": target._sha256(target.LEGACY_HELPER),
        "query_parameters": config["parameters"],
        "source_tables": snapshots,
        "query_job": {"job_id": config["cost_gate"]["query_job_id"]},
        "zero_byte_verification_jobs": {
            "connectivity": {"job_id": config["cost_gate"]["connectivity_job_id"]},
            "oracle": {"job_id": config["cost_gate"]["oracle_job_id"]},
        },
        "result_sha256": target._sha256(root / target.RAW_FILENAME),
    }
    (root / target.METADATA_FILENAME).write_text(
        json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8"
    )
    files = sorted(path for path in root.iterdir() if path.is_file())
    (root / target.MANIFEST_FILENAME).write_text(
        "".join(f"{target._sha256(path)}  {path.name}\n" for path in files),
        encoding="ascii",
    )


def test_existing_output_rejects_stale_metadata(tmp_path: Path) -> None:
    config = _config()
    root = tmp_path / "output"
    root.mkdir()
    _write_bound_existing_output(root, config)
    query = ROOT / config["source"]["query_path"]
    oracle = ROOT / config["source"]["oracle_query_path"]
    assert target._validate_existing_output(root, CONFIG_PATH, query, oracle, config)["schema"] == (
        "google_power_workload_multiday_bigquery_v1"
    )

    metadata_path = root / target.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["implementation_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in root.iterdir() if path.is_file() and path.name != target.MANIFEST_FILENAME)
    (root / target.MANIFEST_FILENAME).write_text(
        "".join(f"{target._sha256(path)}  {path.name}\n" for path in files), encoding="ascii"
    )
    with pytest.raises(RuntimeError, match="implementation_sha256"):
        target._validate_existing_output(root, CONFIG_PATH, query, oracle, config)
