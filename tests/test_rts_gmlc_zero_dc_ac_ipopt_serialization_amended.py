import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_zero_dc_ac_ipopt_serialization_amended import (
    _CONFIG_SHA256,
    _CORRECTED_CASE_FIELDS,
    _PARENT_OUTPUT_ROOT,
    _build_context,
    _read_config,
    prepare_preregistration,
    run_amendment,
)

CONFIG = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_serialization_amendment.yaml"
)


@pytest.fixture(scope="module")
def context():
    return _build_context(CONFIG)


def test_serialization_amendment_freezes_unique_deterministic_schema():
    config = _read_config(CONFIG)

    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == _CONFIG_SHA256
    assert len(_CORRECTED_CASE_FIELDS) == 70
    assert len(set(_CORRECTED_CASE_FIELDS)) == 70
    assert _CORRECTED_CASE_FIELDS.count("solver_objective_mw2") == 1
    assert config["observed_serialization_issue"]["parent_column_count"] == 71
    assert config["observed_serialization_issue"]["parent_unique_column_count"] == 70
    assert config["observed_serialization_issue"][
        "duplicate_values_identical_for_all_rows"
    ]
    assert config["deterministic_transformation"]["solver_call_count"] == 0
    assert not config["deterministic_transformation"][
        "numeric_cell_reformatting_allowed"
    ]


def test_serialization_context_reads_96_unambiguous_corrected_rows(context):
    assert len(context.corrected_case_rows) == 96
    assert all(len(row) == 70 for row in context.corrected_case_rows)
    assert context.parent_summary["case_count"] == 96
    assert context.parent_summary["original_multistart_feasibility_witness_count"] == 22
    assert context.parent_summary["voltage_plus_0p01_feasibility_witness_count"] == 24


def test_serialization_preregistration_is_atomic_and_idempotent(tmp_path):
    first = prepare_preregistration(CONFIG, output_directory=tmp_path)
    second = prepare_preregistration(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["solver_rerun_allowed"] is False
    assert first["parent_outcomes_observed"] is True
    assert (tmp_path / "preregistration" / "SHA256SUMS").exists()


def test_serialization_amendment_revalidates_and_preserves_detail_bytes(tmp_path):
    prepare_preregistration(CONFIG, output_directory=tmp_path)
    first = run_amendment(CONFIG, output_directory=tmp_path)
    second = run_amendment(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["scientific_outcomes_changed"] is False
    assert first["solver_rerun_count"] == 0
    assert first["corrected_case_columns_unique"] is True
    assert first["original_multistart_feasibility_witness_count"] == 22
    assert first["voltage_plus_0p01_feasibility_witness_count"] == 24
    target = tmp_path / "ipopt_diagnostic"
    for name in ("generator_results.csv", "bus_results.csv", "branch_results.csv"):
        assert (target / name).read_bytes() == (
            _PARENT_OUTPUT_ROOT / "ipopt_diagnostic" / name
        ).read_bytes()


def test_serialization_config_byte_drift_is_rejected(tmp_path):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["deterministic_transformation"]["solver_call_count"] = 1
    drifted = tmp_path / "drifted.yaml"
    drifted.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="config SHA-256 drifted"):
        _read_config(drifted)
