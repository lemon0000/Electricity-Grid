import csv
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import experiments.run_rts24_load_conditions as subject
from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
)


@pytest.mark.parametrize(
    (
        "demand_mw",
        "commitment_model",
        "base_feasible",
        "scopf_feasible",
        "expected",
    ),
    [
        (
            900.0,
            "fixed_online",
            False,
            False,
            "demand_below_fixed_online_pmin_requires_commitment",
        ),
        (900.0, "single_snapshot_static_unit_selection", True, True, ""),
        (2100.0, "fixed_online", False, False, "demand_above_online_pmax"),
        (1500.0, "fixed_online", False, False, "base_dc_opf_infeasible"),
        (
            1500.0,
            "fixed_online",
            True,
            False,
            "security_constraints_infeasible_under_synthetic_response",
        ),
        (1500.0, "fixed_online", True, True, ""),
    ],
)
def test_load_condition_diagnosis_is_specific(
    demand_mw,
    commitment_model,
    base_feasible,
    scopf_feasible,
    expected,
):
    assert (
        subject._diagnosis(
            demand_mw=demand_mw,
            online_pmin_mw=1000.0,
            online_pmax_mw=2000.0,
            commitment_model=commitment_model,
            base_feasible=base_feasible,
            scopf_feasible=scopf_feasible,
        )
        == expected
    )


def test_load_condition_run_selects_snapshots_and_writes_auditable_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_path = tmp_path / "load_conditions.csv"
    generator_output_path = tmp_path / "load_condition_generators.csv"
    config_path = tmp_path / "config.yaml"
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "SHA256SUMS").write_text("test manifest\n", encoding="ascii")
    config_path.write_text(
        yaml.safe_dump(
            {
                "source": {
                    "repository": RTS_GMLC_REPOSITORY,
                    "release": RTS_GMLC_RELEASE,
                    "commit": RTS_GMLC_COMMIT,
                    "path": str(source_root),
                    "manifest_sha256": RTS_GMLC_MANIFEST_SHA256,
                },
                "legacy_rts24_proxy": {
                    "load_region": 1,
                    "static_peak_mw": 2850.0,
                },
                "security_snapshot_audit": {
                    "quantiles": ["minimum", "median", "p95", "maximum"],
                    "quantile_method": "lower_order_statistic",
                    "commitment_model": "single_snapshot_static_unit_selection",
                    "base_ac_restoration": True,
                    "redispatch_fraction_pmax": 0.25,
                    "response_parameter_status": "synthetic_test_response",
                    "load_parameter_status": "test_load_proxy",
                    "immediate_branch_rating": "rate_c",
                    "sustained_rating": "rate_a",
                    "cost_breakpoints": 9,
                    "solver": "highs",
                    "excluded_islanding_policy": "report_as_failure",
                },
                "output": {
                    "security_snapshots": str(output_path),
                    "security_snapshot_generators": str(generator_output_path),
                },
            }
        ),
        encoding="utf-8",
    )
    start = datetime(2020, 1, 1)
    hourly = tuple(
        (start + timedelta(hours=index), multiplier)
        for index, multiplier in enumerate((1.0, 0.2, 0.8, 0.4, 0.6))
    )
    loader_calls = []
    scopf_calls = []
    ac_calls = []
    fake_solutions = []

    monkeypatch.setattr(subject, "verify_sha256_manifest", lambda _path: True)
    monkeypatch.setattr(subject, "_sha256", lambda _path: RTS_GMLC_MANIFEST_SHA256)

    def fake_load_multipliers(path, *, static_peak_mw):
        loader_calls.append((path, static_peak_mw))
        return hourly

    def fake_dc_opf(data, **_kwargs):
        return SimpleNamespace(feasible=True, termination_condition="optimal")

    def fake_scopf(data, **kwargs):
        scopf_calls.append((data, kwargs))
        state_results = {str(index): object() for index in range(3)}
        candidates = sorted(
            (
                generator
                for generator in data.generators
                if generator.in_service and generator.p_max_mw > 0.0
            ),
            key=lambda generator: (-generator.p_max_mw, generator.index),
        )
        selected = []
        for generator in candidates:
            selected.append(generator)
            if sum(item.p_max_mw for item in selected) >= data.total_demand_mw:
                break
        selected_indices = {generator.index for generator in selected}
        commitment = {
            generator.index: generator.index in selected_indices
            for generator in data.generators
        }
        generation = {
            generator.index: (
                generator.p_min_mw if generator.index in selected_indices else 0.0
            )
            for generator in data.generators
        }
        remaining = data.total_demand_mw - sum(generation.values())
        for generator in selected:
            addition = min(
                remaining,
                generator.p_max_mw - generator.p_min_mw,
            )
            generation[generator.index] += addition
            remaining -= addition
        assert remaining == pytest.approx(0.0)
        objective = sum(
            generator.cost_quadratic * generation[generator.index] ** 2
            + generator.cost_linear * generation[generator.index]
            + generator.cost_constant
            for generator in data.generators
            if commitment[generator.index]
        )
        fake_solutions.append(
            {
                "commitment": commitment,
                "generation": generation,
                "objective": objective,
            }
        )
        return SimpleNamespace(
            feasible=True,
            termination_condition="optimal",
            objective=objective,
            states=(object(), object(), object()),
            state_results=state_results,
            excluded_branch_indices=(10,),
            commitment_model="single_snapshot_static_unit_selection",
            generator_commitment=commitment,
            base_result=SimpleNamespace(generation_mw=generation),
        )

    def fake_restore(data, dc_result, **kwargs):
        ac_calls.append((data, dc_result, kwargs))
        active_indices = tuple(
            generator.index
            for generator in data.generators
            if kwargs["generator_commitment"][generator.index]
            or generator.p_max_mw == 0.0
        )
        return SimpleNamespace(
            evaluated=True,
            converged=True,
            secure=True,
            status="secure",
            reference_bus=18,
            active_generator_indices=active_indices,
            ac_losses_mw=0.0,
            max_voltage_violation_pu=0.0,
            max_branch_loading_fraction=0.5,
            max_active_power_violation_mw=0.0,
            max_reactive_power_violation_mvar=0.0,
            generation_mw=dc_result.generation_mw,
            reactive_generation_mvar={
                generator.index: 0.0 for generator in data.generators
            },
        )

    monkeypatch.setattr(
        subject,
        "load_rts24_area1_load_multipliers",
        fake_load_multipliers,
    )
    monkeypatch.setattr(subject, "solve_dc_opf", fake_dc_opf)
    monkeypatch.setattr(subject, "solve_security_constrained_dc_opf", fake_scopf)
    monkeypatch.setattr(subject, "restore_ac_feasibility", fake_restore)

    rows = subject.run(config_path)

    assert loader_calls == [(tmp_path / "source", 2850.0)]
    assert [row["condition"] for row in rows] == [
        "minimum",
        "median",
        "p95",
        "maximum",
    ]
    assert [row["load_multiplier"] for row in rows] == [0.2, 0.6, 0.8, 1.0]
    assert [call[0].total_demand_mw for call in scopf_calls] == pytest.approx(
        [570.0, 1710.0, 2280.0, 2850.0]
    )
    for data, kwargs in scopf_calls:
        expected = {
            generator.index: 0.25 * generator.p_max_mw for generator in data.generators
        }
        assert kwargs["redispatch_up_mw"] == pytest.approx(expected)
        assert kwargs["redispatch_down_mw"] == pytest.approx(expected)
        assert kwargs["immediate_rating"] == "rate_c"
        assert kwargs["sustained_rating"] == "rate_a"
        assert kwargs["cost_breakpoints"] == 9
        assert kwargs["optimize_unit_selection"] is True
    assert len(ac_calls) == 4
    for (_data, dc_result, kwargs), solution in zip(ac_calls, fake_solutions):
        assert kwargs["generator_commitment"] == solution["commitment"]
        assert kwargs["reference_generation_mw"] == dc_result.generation_mw

    assert rows[0]["diagnosis"] == ""
    assert rows[0]["base_snapshot_feasible"]
    assert rows[0]["dc_scopf_feasible"]
    assert rows[0]["termination_condition"] == "optimal"
    assert rows[0]["states_modeled"] == 3
    assert rows[0]["states_solved"] == 3
    assert rows[0]["annual_hours_below_fixed_online_pmin"] == 1
    assert rows[0]["commitment_method"] == ("single_snapshot_static_unit_selection")
    for row, solution, (data, _kwargs) in zip(rows, fake_solutions, scopf_calls):
        committed_indices = tuple(
            index for index, committed in solution["commitment"].items() if committed
        )
        assert row["committed_real_power_units"] == len(committed_indices)
        assert row["committed_generator_indices"] == ";".join(
            str(index) for index in committed_indices
        )
        assert row["committed_pmin_mw"] == pytest.approx(
            sum(data.generators[index].p_min_mw for index in committed_indices)
        )
        assert row["committed_pmax_mw"] == pytest.approx(
            sum(data.generators[index].p_max_mw for index in committed_indices)
        )
        assert row["base_production_cost_usd_per_hour_exact"] == pytest.approx(
            solution["objective"]
        )
    assert not rows[0]["load_shedding_allowed"]
    assert rows[1]["diagnosis"] == ""
    assert rows[1]["states_solved"] == 3
    assert rows[1]["excluded_branch_indices"] == "10"
    assert all(not row["security_certified"] for row in rows)
    for row in rows:
        blockers = row["certification_blockers"]
        assert "chronological_commitment_not_modeled" in blockers
        assert "startup_cost_not_applied_no_prior_state" in blockers
        assert "minimum_up_down_times_not_modeled" in blockers
        assert "intertemporal_ramps_not_modeled" in blockers
        assert "contingency_ac_not_run_for_load_snapshots" in blockers
    assert all(row["base_ac_secure"] for row in rows)
    assert all(row["base_ac_status"] == "secure" for row in rows)
    assert all(
        row["ac_validation_scope"] == "base_snapshot_restoration_only" for row in rows
    )

    with output_path.open(encoding="utf-8", newline="") as output:
        csv_rows = list(csv.DictReader(output))
    assert [row["condition"] for row in csv_rows] == [
        "minimum",
        "median",
        "p95",
        "maximum",
    ]
    assert csv_rows[0]["dc_scopf_feasible"] == "True"
    assert csv_rows[1]["states_solved"] == "3"
    with generator_output_path.open(encoding="utf-8", newline="") as output:
        generator_rows = list(csv.DictReader(output))
    assert len(generator_rows) == 4 * 33
    for condition_index, solution in enumerate(fake_solutions):
        condition_rows = generator_rows[
            condition_index * 33 : (condition_index + 1) * 33
        ]
        assert sum(float(row["base_generation_mw"]) for row in condition_rows) == (
            pytest.approx(rows[condition_index]["total_demand_mw"])
        )
        assert sum(
            float(row["base_production_cost_usd_per_hour_exact"])
            for row in condition_rows
        ) == pytest.approx(solution["objective"])
        for generator_row in condition_rows:
            index = int(generator_row["generator_index"])
            assert (generator_row["committed"] == "True") is solution["commitment"][
                index
            ]
            assert float(generator_row["base_generation_mw"]) == pytest.approx(
                solution["generation"][index]
            )
            assert float(generator_row["base_ac_generation_mw"]) == pytest.approx(
                solution["generation"][index]
            )
            assert float(
                generator_row["base_ac_reactive_generation_mvar"]
            ) == pytest.approx(0.0)
    assert generator_rows[14]["real_power_capable"] == "False"
    assert generator_rows[14]["committed"] == "False"
