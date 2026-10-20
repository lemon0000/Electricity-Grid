from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import experiments.diagnose_rq2_grid_need_gurobi_block as diagnostic
from experiments.diagnose_rq2_grid_need_gurobi_block import (
    _classify_memory_growth,
    _diagnostic_solver_payload,
    _display_path,
    _ensure_diagnostic_roots_are_isolated,
    _gurobi_probe_options,
    _parse_gurobi_log,
    _parse_highs_log,
    _resource_stop_reason,
    _worker,
    run_diagnostic,
)

FORMAL_SOLVER = {
    "name": "gurobi",
    "expected_package_version": "13.0.2",
    "threads": 4,
    "mip_relative_gap": 1.0e-6,
    "feasibility_tolerance": 1.0e-6,
    "optimality_tolerance": 1.0e-6,
    "integer_feasibility_tolerance": 1.0e-6,
    "random_seed": 0,
    "time_limit_seconds": None,
    "tolerance_mw": 1.0e-6,
    "tee": False,
}


def test_diagnostic_solver_payload_only_adds_observability_limit():
    diagnostic = _diagnostic_solver_payload(
        FORMAL_SOLVER,
        time_limit_seconds=600.0,
    )

    assert diagnostic == {
        **FORMAL_SOLVER,
        "time_limit_seconds": 600.0,
        "tee": True,
    }
    assert FORMAL_SOLVER["time_limit_seconds"] is None
    assert FORMAL_SOLVER["tee"] is False


def test_highs_route_changes_only_solver_identity_and_observability_limit():
    diagnostic = _diagnostic_solver_payload(
        FORMAL_SOLVER,
        time_limit_seconds=600.0,
        gurobi_probe_profile="highs_route",
    )

    assert diagnostic == {
        **FORMAL_SOLVER,
        "name": "highs",
        "expected_package_version": "1.15.1",
        "time_limit_seconds": 600.0,
        "tee": True,
    }
    for key in (
        "threads",
        "mip_relative_gap",
        "feasibility_tolerance",
        "optimality_tolerance",
        "integer_feasibility_tolerance",
        "random_seed",
        "tolerance_mw",
    ):
        assert diagnostic[key] == FORMAL_SOLVER[key]


def test_gurobi_probe_profiles_are_explicit_and_do_not_relax_gates():
    assert _gurobi_probe_options("formal_default") == {}
    assert _gurobi_probe_options("symmetry_aggressive") == {"Symmetry": 2}
    assert _gurobi_probe_options("incumbent_focus") == {"MIPFocus": 1}
    assert _gurobi_probe_options("bound_focus") == {"MIPFocus": 3}
    assert _gurobi_probe_options("highs_route") == {}

    with pytest.raises(ValueError, match="unknown Gurobi probe profile"):
        _gurobi_probe_options("relax_gap")


def test_diagnostic_roots_cannot_overlap_formal_artifacts(tmp_path: Path):
    formal_checkpoints = tmp_path / "formal" / "checkpoints"
    formal_output = tmp_path / "formal" / "output"
    safe_tables = tmp_path / "diagnostic" / "tables"
    safe_logs = tmp_path / "diagnostic" / "logs"

    _ensure_diagnostic_roots_are_isolated(
        table_root=safe_tables,
        log_root=safe_logs,
        formal_checkpoint_root=formal_checkpoints,
        formal_output_root=formal_output,
    )

    with pytest.raises(ValueError, match="formal artifact"):
        _ensure_diagnostic_roots_are_isolated(
            table_root=formal_checkpoints / "probe",
            log_root=safe_logs,
            formal_checkpoint_root=formal_checkpoints,
            formal_output_root=formal_output,
        )


def test_display_path_allows_diagnostic_root_outside_repository(tmp_path: Path):
    external = tmp_path / "diagnostic.json"

    assert _display_path(external) == str(external.resolve()).replace("\\", "/")


def test_gurobi_log_parser_extracts_tree_and_final_certificate():
    parsed = _parse_gurobi_log(
        """
 Expl Unexpl |  Obj  Depth IntInf | Incumbent BestBd Gap | It/Node Time
     0     0 1813500.00    0   125 1814000.00 1813500.00 0.03%     -    2s
  1200   875 1813593.98   31    17 1813595.37 1813593.98 0.00%  42.1  600s
Explored 1200 nodes (50520 simplex iterations) in 600.00 seconds
Best objective 1.813595368660e+06, best bound 1.813593987986e+06, gap 0.0001%
"""
    )

    assert parsed["maximum_explored_nodes"] == 1200
    assert parsed["maximum_unexplored_nodes"] == 875
    assert parsed["last_progress_elapsed_seconds"] == 600.0
    assert parsed["final_explored_nodes"] == 1200
    assert parsed["final_simplex_iterations"] == 50520
    assert parsed["final_best_objective"] == pytest.approx(1813595.36866)
    assert parsed["final_best_bound"] == pytest.approx(1813593.987986)
    assert parsed["final_gap_percent"] == pytest.approx(0.0001)


def test_highs_log_parser_extracts_tree_and_final_certificate():
    parsed = _parse_highs_log(
        """
      4026      62      1872  99.80%   1813314.385864  1813595.36866  0.02%  2038 101 8905 222494 172.0s
Solving report
  Status            Optimal
  Primal bound      1813595.36866
  Dual bound        1813594.61139
  Gap               4.2e-05% (tolerance: 0.0001%)
  Timing            185.55
  Nodes             4115
  LP iterations     242265
"""
    )

    assert parsed["status"] == "Optimal"
    assert parsed["maximum_explored_nodes"] == 4115
    assert parsed["maximum_unexplored_nodes"] == 62
    assert parsed["last_progress_elapsed_seconds"] == 172.0
    assert parsed["final_explored_nodes"] == 4115
    assert parsed["final_simplex_iterations"] == 242265
    assert parsed["final_elapsed_seconds"] == pytest.approx(185.55)
    assert parsed["final_best_objective"] == pytest.approx(1813595.36866)
    assert parsed["final_best_bound"] == pytest.approx(1813594.61139)
    assert parsed["final_gap_percent"] == pytest.approx(4.2e-05)
    assert parsed["time_limit_reached"] is False


def test_memory_classifier_distinguishes_tree_growth_from_flat_node_growth():
    tree = _classify_memory_growth(
        memory_samples=[
            {"elapsed_seconds": 0.0, "private_bytes": 1_000_000_000},
            {"elapsed_seconds": 600.0, "private_bytes": 5_000_000_000},
        ],
        gurobi_log={
            "maximum_explored_nodes": 1200,
            "maximum_unexplored_nodes": 875,
        },
    )
    flat = _classify_memory_growth(
        memory_samples=[
            {"elapsed_seconds": 0.0, "private_bytes": 1_000_000_000},
            {"elapsed_seconds": 600.0, "private_bytes": 5_000_000_000},
        ],
        gurobi_log={
            "maximum_explored_nodes": 0,
            "maximum_unexplored_nodes": 0,
        },
    )

    assert tree["classification"] == "branch_and_bound_tree_growth_supported"
    assert flat["classification"] == "native_memory_growth_not_explained_by_nodes"
    assert tree["private_bytes_delta"] == 4_000_000_000


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        (
            {
                "sampling_available": True,
                "private_bytes": 9 * 1024**3,
                "system_commit_available_bytes": 20 * 1024**3,
            },
            "private_commit_limit_reached",
        ),
        (
            {
                "sampling_available": True,
                "private_bytes": 1 * 1024**3,
                "system_commit_available_bytes": 1 * 1024**3,
            },
            "system_commit_reserve_reached",
        ),
        (
            {
                "sampling_available": True,
                "private_bytes": 1 * 1024**3,
                "system_commit_available_bytes": 20 * 1024**3,
            },
            None,
        ),
    ],
)
def test_resource_stop_is_explicit_and_not_solver_infeasibility(sample, expected):
    assert (
        _resource_stop_reason(
            sample,
            private_commit_limit_bytes=8 * 1024**3,
            minimum_system_commit_available_bytes=2 * 1024**3,
        )
        == expected
    )


def test_worker_rejects_formal_result_path_before_write_or_solver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    checkpoint_root = tmp_path / "formal" / "checkpoints"
    output_root = tmp_path / "formal" / "output"
    config_path = tmp_path / "grid.yaml"
    config_path.write_text("schema: test\n", encoding="utf-8")
    config = {
        "execution": {"checkpoint_directory": str(checkpoint_root)},
        "output": {"directory": str(output_root)},
    }
    monkeypatch.setattr(
        diagnostic.v4,
        "_preflight",
        lambda _path: (config, Path("grid"), {"block": []}, {}, {}),
    )
    solver_called = {"value": False}

    def forbidden_solver(*_args, **_kwargs):
        solver_called["value"] = True
        raise AssertionError("solver path must not be reached")

    monkeypatch.setattr(
        diagnostic,
        "load_rts_gmlc_chronological_data",
        forbidden_solver,
    )
    result_path = checkpoint_root / "overwrite.json"

    with pytest.raises(ValueError, match="formal artifact"):
        _worker(
            config_path=config_path,
            block_id="block",
            time_limit_seconds=5.0,
            gurobi_probe_profile="formal_default",
            result_path=result_path,
        )

    assert not result_path.exists()
    assert solver_called["value"] is False


def test_controller_propagates_probe_profile_to_children_and_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path = tmp_path / "grid.yaml"
    config_path.write_text(yaml.safe_dump({"schema": "test"}), encoding="utf-8")
    config = {
        "solver": FORMAL_SOLVER,
        "execution": {
            "checkpoint_directory": str(tmp_path / "formal" / "checkpoints")
        },
        "output": {"directory": str(tmp_path / "formal" / "output")},
    }
    blocks = {block_id: [] for block_id in diagnostic._DEFAULT_BLOCKS}
    monkeypatch.setattr(
        diagnostic.v4,
        "_preflight",
        lambda _path: (config, Path("grid"), blocks, {}, {}),
    )
    monkeypatch.setattr(
        diagnostic,
        "_windows_memory_sample",
        lambda _pid: {
            "sampling_available": True,
            "system_commit_available_bytes": 16 * 1024**3,
        },
    )
    observed_profiles = []

    def fake_child(**kwargs):
        observed_profiles.append(kwargs["gurobi_probe_profile"])
        return {
            "block_id": kwargs["block_id"],
            "exit_code": 0,
            "memory_growth": {"classification": "test"},
            "command": [
                "--gurobi-probe-profile",
                kwargs["gurobi_probe_profile"],
            ],
            "worker": {
                "gurobi_probe_profile": kwargs["gurobi_probe_profile"],
                "gurobi_probe_options": {"Symmetry": 2},
            },
        }

    monkeypatch.setattr(diagnostic, "_run_child", fake_child)

    summary = run_diagnostic(
        config_path=config_path,
        block_ids=diagnostic._DEFAULT_BLOCKS,
        time_limit_seconds=5.0,
        sample_interval_seconds=1.0,
        private_commit_limit_gib=1.0,
        minimum_system_commit_available_gib=0.5,
        gurobi_probe_profile="symmetry_aggressive",
        table_root=tmp_path / "diagnostic" / "tables",
        log_root=tmp_path / "diagnostic" / "logs",
    )

    assert observed_profiles == ["symmetry_aggressive", "symmetry_aggressive"]
    assert summary["gurobi_probe_profile"] == "symmetry_aggressive"
    assert summary["gurobi_probe_options"] == {"Symmetry": 2}
    assert all(
        block["command"][-1] == block["worker"]["gurobi_probe_profile"]
        == "symmetry_aggressive"
        for block in summary["blocks"]
    )
