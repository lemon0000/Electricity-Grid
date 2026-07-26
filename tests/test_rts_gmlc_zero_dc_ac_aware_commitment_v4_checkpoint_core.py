from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import (
    rts_gmlc_zero_dc_ac_aware_commitment_v4_checkpoint_core as runner,
)


def _context(
    output_root: Path | None = None,
    log_root: Path | None = None,
    *,
    deltas: tuple[float, ...] = (0.1,),
) -> SimpleNamespace:
    return SimpleNamespace(
        config_path=Path("test-config.yaml"),
        config={
            "preregistration": {"id": "experiment-v4"},
            "formal_solver": {
                "algorithm": "exact_selected_state_constraint_generation",
                "solver": {"name": "highs", "threads": 4},
                "progress_logging": {
                    "log_directory": str(log_root or Path("unused-logs"))
                },
                "time_limits_seconds": {"per_candidate_total": 10.0},
            },
            "candidate_frontier": {
                "relative_cost_budget_deltas": list(deltas),
            },
            "evidence": {"formal_candidate_result": False},
        },
        output_root=output_root or Path("unused-results"),
        input_contract_sha256="a" * 64,
        request=SimpleNamespace(
            timestamps=(datetime(2020, 1, 1, tzinfo=timezone.utc),)
        ),
    )


def _candidate(requested_id: str, delta: float = 0.1) -> runner._Candidate:
    commitment = ({"g1": True},)
    generation = ({"g1": 1.2345678901234567},)
    branch_flows = ({"b1": -987.6543210987654},)
    dc_flows = ({"d1": 0.12345678901234568},)
    return runner._Candidate(
        requested_candidate_id=requested_id,
        source="test",
        relative_cost_budget_delta=delta,
        cost_budget_usd=200.12345678901235,
        operating_cost_usd=100.98765432109876,
        reactive_proxy_fraction=0.5000000001234568,
        commitment_sha256=runner._commitment_sha256(commitment),
        dispatch_sha256=runner._dispatch_sha256(generation, branch_flows, dc_flows),
        commitment=commitment,
        startup=({"g1": False},),
        shutdown=({"g1": False},),
        generation_mw=generation,
        branch_flows_mw=branch_flows,
        dc_flows_mw=dc_flows,
        reserve_up_mw=({"g1": 2.345678901234567},),
        stage_audits={"test_value": 3.456789012345678},
        residual_audit={"maximum_residual": 4.567890123456789},
    )


def _checkpoint_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _frontier_stubs(
    monkeypatch: pytest.MonkeyPatch,
    context: SimpleNamespace,
    baseline: runner._Candidate,
) -> None:
    monkeypatch.setattr(runner, "_build_context", lambda _path: context)
    monkeypatch.setattr(
        runner,
        "_require_preregistration",
        lambda _context, _root: {
            "input_contract_sha256": context.input_contract_sha256
        },
    )
    monkeypatch.setattr(runner, "_baseline_candidate", lambda _context: baseline)


def test_full_precision_checkpoint_round_trip_preserves_float_identity(
    tmp_path: Path,
) -> None:
    context = _context()
    candidate = _candidate("delta_1")

    saved = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    loaded = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert saved == candidate
    assert loaded == candidate
    assert loaded is not None
    original_dispatch = (
        candidate.generation_mw[0]["g1"],
        candidate.branch_flows_mw[0]["b1"],
        candidate.dc_flows_mw[0]["d1"],
    )
    loaded_dispatch = (
        loaded.generation_mw[0]["g1"],
        loaded.branch_flows_mw[0]["b1"],
        loaded.dc_flows_mw[0]["d1"],
    )
    assert [value.hex() for value in loaded_dispatch] == [
        value.hex() for value in original_dispatch
    ]
    assert runner._dispatch_sha256(
        loaded.generation_mw,
        loaded.branch_flows_mw,
        loaded.dc_flows_mw,
    ) == runner._dispatch_sha256(
        candidate.generation_mw,
        candidate.branch_flows_mw,
        candidate.dc_flows_mw,
    )
    document = json.loads(
        (
            tmp_path / "candidate_checkpoints" / "01_delta_1" / "candidate.json"
        ).read_text(encoding="utf-8")
    )
    assert document["float_serialization"] == runner._CHECKPOINT_FLOAT_SERIALIZATION
    assert document["candidate"]["operating_cost_usd"].hex() == (
        candidate.operating_cost_usd.hex()
    )


def test_checkpoint_normalizes_nested_audit_tuples_before_identity_check(
    tmp_path: Path,
) -> None:
    context = _context()
    candidate = replace(
        _candidate("delta_1"),
        stage_audits={"nested": {"state_ids": ("normal", "branch_A11")}},
        residual_audit={"commitment_feasible_by_step": (True,)},
    )

    saved = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    loaded = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert saved == loaded
    assert saved != candidate
    assert saved.stage_audits["nested"]["state_ids"] == ["normal", "branch_A11"]
    assert saved.residual_audit["commitment_feasible_by_step"] == [True]


def test_checkpoint_save_is_idempotent_without_rewriting_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context()
    candidate = _candidate("delta_1")
    runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    before = _checkpoint_files(target)

    monkeypatch.setattr(
        runner,
        "_write_exact_json",
        lambda *_args, **_kwargs: pytest.fail("idempotent save rewrote JSON"),
    )
    monkeypatch.setattr(
        runner,
        "_write_manifest",
        lambda *_args, **_kwargs: pytest.fail("idempotent save rewrote manifest"),
    )
    saved = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)

    assert saved == candidate
    assert _checkpoint_files(target) == before


def test_existing_different_checkpoint_is_not_overwritten(tmp_path: Path) -> None:
    context = _context()
    candidate = _candidate("delta_1")
    runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    before = _checkpoint_files(target)
    different = replace(
        candidate,
        operating_cost_usd=candidate.operating_cost_usd + 0.0000000000001,
    )

    with pytest.raises(RuntimeError, match="Existing candidate checkpoint drifted"):
        runner._save_candidate_checkpoint(context, tmp_path, 1, different)

    assert _checkpoint_files(target) == before


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_checkpoint_is_rejected_before_publication(
    tmp_path: Path, nonfinite: float
) -> None:
    context = _context()
    candidate = replace(_candidate("delta_1"), operating_cost_usd=nonfinite)
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")

    with pytest.raises(ValueError, match="Out of range float values"):
        runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)

    assert not target.exists()


def test_rounded_writer_fails_staging_audit_without_publishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = _context()
    candidate = _candidate("delta_1")
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    monkeypatch.setattr(runner, "_write_exact_json", runner._v3._write_json)

    with pytest.raises(RuntimeError, match="staging round-trip drifted"):
        runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)

    assert not target.exists()
    assert not tuple(target.parent.glob(".*.processing-*"))


def test_v1_rounded_checkpoint_is_rejected_and_cannot_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "results"
    log_root = tmp_path / "logs"
    context = _context(output_root, log_root)
    requested_id = runner._requested_candidate_id(0.1)
    candidate = _candidate(requested_id)
    target = runner._candidate_checkpoint_path(output_root, 1, requested_id)
    payload = runner._v3._stable_json(
        {
            "schema": "rts_gmlc_zero_dc_ac_aware_candidate_checkpoint_v1",
            "preregistration_id": context.config["preregistration"]["id"],
            "input_contract_sha256": context.input_contract_sha256,
            "ordinal": 1,
            "candidate": asdict(candidate),
        }
    )
    runner._publish_checkpoint_without_overwrite(
        target,
        lambda staging: runner._write_exact_json(staging / "candidate.json", payload),
    )

    with pytest.raises(RuntimeError, match="serialization contract drifted"):
        runner._load_candidate_checkpoint(context, output_root, 1, requested_id)

    _frontier_stubs(monkeypatch, context, _candidate("parent", 0.0))
    solve_called = False

    def unexpected_solve(*_args: object, **_kwargs: object) -> runner._Candidate:
        nonlocal solve_called
        solve_called = True
        raise AssertionError("legacy checkpoint reached the solver")

    monkeypatch.setattr(runner, "_solve_frontier_candidate", unexpected_solve)
    with pytest.raises(RuntimeError, match="serialization contract drifted"):
        runner.generate_candidate_frontier(
            Path("test-config.yaml"), attempt_id="legacy-resume"
        )

    assert not solve_called
    assert not (output_root / "candidate_frontier").exists()


def test_completed_v4_checkpoint_resume_skips_solver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "results"
    log_root = tmp_path / "logs"
    context = _context(output_root, log_root)
    requested_id = runner._requested_candidate_id(0.1)
    checkpoint = _candidate(requested_id)
    runner._save_candidate_checkpoint(context, output_root, 1, checkpoint)
    _frontier_stubs(monkeypatch, context, _candidate("parent", 0.0))

    def unexpected_solve(*_args: object, **_kwargs: object) -> runner._Candidate:
        pytest.fail("completed checkpoint was solved again")

    monkeypatch.setattr(runner, "_solve_frontier_candidate", unexpected_solve)
    summary = runner.generate_candidate_frontier(
        Path("test-config.yaml"), attempt_id="resume-v4"
    )

    assert summary["requested_candidate_count"] == 2
    assert summary["checkpoint_schema"] == runner._CHECKPOINT_SCHEMA
    assert list(summary["candidate_checkpoint_manifest_sha256s"]) == [requested_id]
    progress = (log_root / "resume-v4" / "progress.jsonl").read_text(encoding="utf-8")
    assert "candidate_checkpoint_loaded" in progress
    assert "candidate_started" not in progress
