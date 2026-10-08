import json
import statistics
from decimal import Decimal, Inexact, ROUND_DOWN, localcontext

import pytest

import experiments.analyze_google_power_workload_23h_v1 as analysis_module
from experiments.analyze_google_power_workload_23h_v1 import (
    _analyze_rows,
    _average_ranks,
    _pearson,
    _spearman,
    _summary_bytes,
    run,
)


def _coefficient(result):
    assert result["status"] == "available"
    return Decimal(result["coefficient"])


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    (
        ([1, 2, 3], [2, 4, 6], Decimal("1")),
        ([1, 2, 3], [6, 4, 2], Decimal("-1")),
        ([-1, 0, 1], [1, 0, 1], Decimal("0")),
    ),
)
def test_analytic_correlations_cover_positive_negative_and_zero(left, right, expected):
    x = [Decimal(value) for value in left]
    y = [Decimal(value) for value in right]
    assert _coefficient(_pearson(x, y)) == expected
    assert _coefficient(_spearman(x, y)) == expected


def test_unavailable_correlations_never_encode_nan_or_false_zero():
    cases = (
        _pearson([Decimal(1)], [Decimal(2)]),
        _pearson([Decimal(1), Decimal(1)], [Decimal(2), Decimal(3)]),
        _spearman([Decimal(1), None], [Decimal(2), Decimal(3)]),
    )
    assert [case["status"] for case in cases] == [
        "unavailable_insufficient_observations",
        "unavailable_constant_series",
        "unavailable_null_observation",
    ]
    assert all(case["coefficient"] is None for case in cases)


def test_tied_rank_correlations_match_independent_standard_library_oracle():
    left = [Decimal(value) for value in (1, 1, 2, 4, 4, 5)]
    right = [Decimal(value) for value in (9, 7, 7, 3, 2, 2)]

    def independent_average_ranks(values):
        ordered = sorted(values)
        return [statistics.mean(index + 1 for index, candidate in enumerate(ordered) if candidate == value) for value in values]

    pearson_oracle = statistics.correlation([float(value) for value in left], [float(value) for value in right])
    spearman_oracle = statistics.correlation(independent_average_ranks(left), independent_average_ranks(right))
    assert float(_coefficient(_pearson(left, right))) == pytest.approx(pearson_oracle, abs=1e-15)
    assert float(_coefficient(_spearman(left, right))) == pytest.approx(spearman_oracle, abs=1e-15)
    assert [float(value) for value in _average_ranks(left)] == [1.5, 1.5, 3.0, 4.5, 4.5, 6.0]


def _synthetic_rows():
    rows = []
    for hour in range(1, 24):
        rows.append(
            {
                "source_hour_index": str(hour),
                "common_raw_start_us": str(hour * 3_600_000_000),
                "common_raw_end_us": str((hour + 1) * 3_600_000_000),
                "power_sample_count": "12",
                "cpu_source_row_count": "14",
                "measured_power_util_mean_12dp": str(Decimal(hour) / Decimal(100)),
                "bad_measurement_false_count": "12",
                "bad_measurement_true_count": "0",
                "bad_production_false_count": "0",
                "bad_production_true_count": "12",
                "observed_cpu_ncu_lower": str(hour),
                "observed_cpu_ncu_upper": str(hour + 1),
                "missing_cpu_overlap_seconds": "0",
                "cpu_conflict_overlap_seconds": "1" if hour < 23 else "0",
            }
        )
    return rows


def test_row_order_and_ambient_decimal_context_do_not_change_summary_bytes():
    rows = _synthetic_rows()
    expected = _summary_bytes(_analyze_rows(rows))
    with localcontext() as ambient:
        ambient.prec = 3
        ambient.rounding = ROUND_DOWN
        ambient.traps[Inexact] = True
        actual = _summary_bytes(_analyze_rows(reversed(rows)))
    assert actual == expected


@pytest.mark.parametrize("case", ("duplicate", "missing", "shifted_interval", "source_row_count"))
def test_row_scope_and_intervals_fail_closed(case):
    rows = _synthetic_rows()
    if case == "duplicate":
        rows[-1] = dict(rows[-2])
    elif case == "missing":
        rows.pop()
    elif case == "shifted_interval":
        rows[0]["common_raw_start_us"] = str(int(rows[0]["common_raw_start_us"]) + 1)
    else:
        rows[0]["cpu_source_row_count"] = "13"
    with pytest.raises(RuntimeError, match="hours 1 through 23|raw-hour interval drifted|fourteen CPU source strata"):
        _analyze_rows(rows)


def test_run_rejects_bound_pair_hash_drift_without_writing(tmp_path, monkeypatch):
    real_sha256 = analysis_module._sha256

    def drift_pair(path):
        if path == analysis_module.PAIR_PATH:
            return "0" * 64
        return real_sha256(path)

    monkeypatch.setattr(analysis_module, "_sha256", drift_pair)
    output = tmp_path / "diagnostic" / "summary.json"
    with pytest.raises(RuntimeError, match="source hash drifted"):
        run(output)
    assert not output.parent.exists()


def test_real_bound_source_is_23_unfiltered_hours_and_output_is_no_overwrite(tmp_path):
    output = tmp_path / "diagnostic" / "summary.json"
    summary = run(output)
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == summary
    assert summary["observation_count"] == 23
    assert summary["scope"] == "all_23_aligned_hours_unfiltered"
    assert summary["quality_flag_counts_unfiltered"] == {
        "bad_measurement_false_count": 276,
        "bad_measurement_true_count": 0,
        "bad_production_false_count": 0,
        "bad_production_true_count": 276,
    }
    assert not summary["interpretation"]["correlations_are_identification_bounds"]
    assert not summary["interpretation"]["quality_eligibility_inferred"]
    assert not summary["interpretation"]["continuous_model_input_ready"]
    assert summary["source_interval"]["trace_relative_start_minutes"] == 50
    assert summary["source_interval"]["trace_relative_end_minutes"] == 1430
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        run(output)
