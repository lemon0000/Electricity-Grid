"""Tests for the RQ2 formal-scale batch driver (agent.md sections 4/8/9).

These pin ``experiments.run_rq2_formal_batch.run``: a driver that reads *one*
batch manifest declaring each formal-scale job as ``(runner, base_config,
whitelisted overrides)``, materialises a per-job effective config (recording its
SHA-256), calls each already-reviewed entry point's own ``run`` and copies its
honesty tags / gate forward. The scope here is the driver's contract, not the
entry points' science (covered by their own tests):

* the driver runs the three real formal base configs end-to-end at a tiny
  overridden scale and writes an aggregate manifest with a per-job record,
  materialised effective config and its SHA-256;
* only whitelisted numeric scalars may be overridden -- an honesty flag, a path,
  a non-existent section, or a boolean fails the batch closed;
* the batch fails closed if any job's gate does not pass, and refuses any job
  that reports itself ``security_certified`` other than ``False``;
* every output path is rewritten into an isolated per-job directory so jobs
  never collide, and the aggregate manifest never certifies.

The formal statistical tier (n_train=200, three seeds, the full mechanism
neighbourhood) is deliberately *not* run here -- that is the execution machine's
job under user authorisation. These tests shrink the generator draw via
whitelisted overrides so the pipeline is verified in seconds.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
pytest.importorskip("pyomo")

from experiments import run_rq2_formal_batch as batch


_L5_BASE = "configs/rq2_l5_economic_stochastic_formal.yaml"
_H2_BASE = "configs/rq2_h2_stochastic_holdout_generated_formal.yaml"
_ABLATION_BASE = "configs/rq2_h2_scenario_source_ablation_formal.yaml"


def _tiny_batch(tmp_path: Path) -> dict:
    """A 3-job batch (one per runner) at a tiny overridden generator scale.

    Exercises every runner and the whole materialise -> hash -> run -> collect
    path without paying for the formal n_train=200 draw.
    """

    return {
        "batch": {
            "id": "rq2_formal_batch_test",
            "output_root": str(tmp_path / "out"),
        },
        "jobs": [
            {
                "id": "l5_frontier",
                "runner": "experiments.run_rq2_l5_economic_stochastic",
                "base_config": _L5_BASE,
            },
            {
                "id": "h2_generated",
                "runner": "experiments.run_rq2_h2_stochastic_holdout",
                "base_config": _H2_BASE,
                "overrides": {
                    "generator.n_train": 12,
                    "generator.n_holdout": 6,
                    "generator.seed": 20260822,
                },
            },
            {
                "id": "ablation",
                "runner": "experiments.run_rq2_h2_scenario_source_ablation",
                "base_config": _ABLATION_BASE,
                "overrides": {
                    "generator.n_train": 12,
                    "generator.n_holdout": 6,
                    "reduction.target_count": 6,
                },
            },
        ],
    }


def _write_batch(tmp_path: Path, config: dict) -> Path:
    path = tmp_path / "batch.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# End-to-end orchestration of the real formal configs (tiny scale)
# ---------------------------------------------------------------------------
def test_batch_runs_all_reviewed_entry_points_and_writes_manifest(tmp_path):
    manifest = batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))

    assert manifest["batch_id"] == "rq2_formal_batch_test"
    assert manifest["job_count"] == 3
    assert manifest["batch_gate_passed"] is True
    assert manifest["security_certified"] is False
    assert manifest["formal_vma_published"] is False

    batch_dir = tmp_path / "out" / "rq2_formal_batch_test"
    # The aggregate manifest is on disk and matches the returned mapping (minus
    # the manifest_path the driver adds after writing).
    on_disk = json.loads((batch_dir / "batch_manifest.json").read_text("utf-8"))
    returned = dict(manifest)
    returned.pop("manifest_path", None)
    assert on_disk == returned

    ids = [j["job_id"] for j in manifest["jobs"]]
    assert ids == ["l5_frontier", "h2_generated", "ablation"]
    for record in manifest["jobs"]:
        # Every job materialised an effective config whose SHA-256 is recorded.
        effective = Path(record["effective_config"])
        assert effective.is_file()
        assert record["effective_config_sha256"] == batch._sha256(effective)
        # A recorded base-config SHA and a passing gate, never self-certified.
        assert len(record["base_config_sha256"]) == 64
        assert record["gate_passed"] is True
        assert record["security_certified"] is False


def test_h2_findings_are_carried_forward_not_gated(tmp_path):
    manifest = batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))
    by_id = {j["job_id"]: j for j in manifest["jobs"]}
    # The H2 under-delivery flag and H1 overestimation are reported per job as
    # scientific findings (never gated by the driver).
    assert by_id["h2_generated"]["h2_b6_underdelivers_out_of_sample"] is not None
    assert by_id["ablation"]["h2_robust_across_sources"] is not None
    assert by_id["l5_frontier"]["h1_overestimation_mw"] is not None


def test_l5_h3_verdict_and_frontier_travel_with_the_manifest(tmp_path):
    # H1 and H3 are co-equal falsifiable claims of the L5 sweep, and the whole
    # reason its lambda grid was densified is the H3 Pareto frontier. The
    # cross-machine analyst only receives batch_manifest.json, so the H3 verdict
    # AND the frontier must be self-contained in the L5 job record -- otherwise
    # H3 (and the deliberate budget=80 collapse) cannot be reproduced downstream.
    manifest = batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))
    l5 = {j["job_id"]: j for j in manifest["jobs"]}["l5_frontier"]

    assert l5["h3_monotone_cost_tail_risk_tradeoff"] is not None
    assert l5["h3_cvar_non_increasing"] is not None
    assert l5["h3_expected_cost_non_decreasing"] is not None

    frontier = l5["frontier"]
    assert isinstance(frontier, list) and len(frontier) == 13  # 13-point lambda grid
    for point in frontier:
        assert {
            "lambda_risk",
            "expected_planning_cost",
            "conditional_value_at_risk",
            "provisioned_flexibility_mw",
        } <= set(point)
    # Non-L5 jobs simply do not report H3 -- disclosed as None, not defaulted.
    ablation = {j["job_id"]: j for j in manifest["jobs"]}["ablation"]
    assert ablation["h3_monotone_cost_tail_risk_tradeoff"] is None
    assert ablation["frontier"] is None


def test_outputs_are_rewritten_into_isolated_per_job_dirs(tmp_path):
    batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))
    batch_dir = tmp_path / "out" / "rq2_formal_batch_test"
    # Each job owns a directory; the L5 job's canonical outputs live under it,
    # not under the base config's results/tables path.
    assert (batch_dir / "l5_frontier" / "effective_config.yaml").is_file()
    assert (batch_dir / "l5_frontier" / "summary.json").is_file()
    assert (batch_dir / "l5_frontier" / "frontier.csv").is_file()
    assert (batch_dir / "ablation" / "arms.csv").is_file()


def test_output_root_override_redirects_every_artifact(tmp_path):
    # A cross-machine executor redirects the whole batch into its uploaded run
    # directory; the config's own output_root is ignored when overridden.
    config = _tiny_batch(tmp_path)
    config["batch"]["output_root"] = str(tmp_path / "ignored")
    run_dir = tmp_path / "run_dir"
    manifest = batch.run(
        _write_batch(tmp_path, config), output_root_override=run_dir
    )
    batch_dir = run_dir / "rq2_formal_batch_test"
    assert Path(manifest["manifest_path"]) == batch_dir / "batch_manifest.json"
    assert (batch_dir / "batch_manifest.json").is_file()
    assert (batch_dir / "l5_frontier" / "summary.json").is_file()
    # The ignored config root was never written.
    assert not (tmp_path / "ignored").exists()


# ---------------------------------------------------------------------------
# Whitelist / honesty fail-closed behaviour
# ---------------------------------------------------------------------------
def test_forbidden_override_key_fails_closed(tmp_path):
    config = _tiny_batch(tmp_path)
    config["jobs"] = [
        {
            "id": "bad",
            "runner": "experiments.run_rq2_l5_economic_stochastic",
            "base_config": _L5_BASE,
            # An output path is never overridable (the driver owns those).
            "overrides": {"output.summary_path": 1},
        }
    ]
    with pytest.raises(ValueError, match="forbidden override"):
        batch.run(_write_batch(tmp_path, config))


def test_boolean_override_is_rejected(tmp_path):
    config = _tiny_batch(tmp_path)
    config["jobs"] = [
        {
            "id": "bad",
            "runner": "experiments.run_rq2_h2_scenario_source_ablation",
            "base_config": _ABLATION_BASE,
            "overrides": {"model.beta": True},
        }
    ]
    with pytest.raises(ValueError, match="numeric, not boolean"):
        batch.run(_write_batch(tmp_path, config))


def test_override_of_missing_field_fails_closed(tmp_path):
    # A whitelisted key must still name an existing frozen field; a base config
    # without a generator section cannot be handed a generator override.
    config = _tiny_batch(tmp_path)
    config["jobs"] = [
        {
            "id": "bad",
            "runner": "experiments.run_rq2_l5_economic_stochastic",
            "base_config": _L5_BASE,  # has no generator section
            "overrides": {"generator.seed": 1},
        }
    ]
    with pytest.raises(ValueError, match="no existing section"):
        batch.run(_write_batch(tmp_path, config))


def test_duplicate_job_id_is_rejected(tmp_path):
    config = _tiny_batch(tmp_path)
    config["jobs"] = [config["jobs"][0], copy.deepcopy(config["jobs"][0])]
    with pytest.raises(ValueError, match="duplicate job id"):
        batch.run(_write_batch(tmp_path, config))


def test_missing_base_config_is_rejected(tmp_path):
    config = _tiny_batch(tmp_path)
    config["jobs"] = [
        {
            "id": "bad",
            "runner": "experiments.run_rq2_l5_economic_stochastic",
            "base_config": "configs/does_not_exist.yaml",
        }
    ]
    with pytest.raises(ValueError, match="base_config not found"):
        batch.run(_write_batch(tmp_path, config))


def test_batch_fails_closed_when_a_job_gate_fails(tmp_path, monkeypatch):
    # A non-passing gate in any job must mark the whole batch not-passed, without
    # the driver reinterpreting it (the finding stays the job's).
    import experiments.run_rq2_l5_economic_stochastic as l5

    real_run = l5.run

    def failing_run(config_path):
        summary = real_run(config_path)
        summary["gate_passed"] = False
        return summary

    monkeypatch.setattr(l5, "run", failing_run)
    manifest = batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))
    assert manifest["batch_gate_passed"] is False
    assert manifest["jobs"][0]["gate_passed"] is False


def test_self_certifying_job_fails_the_batch(tmp_path, monkeypatch):
    import experiments.run_rq2_l5_economic_stochastic as l5

    real_run = l5.run

    def certifying_run(config_path):
        summary = real_run(config_path)
        summary["security_certified"] = True
        return summary

    monkeypatch.setattr(l5, "run", certifying_run)
    with pytest.raises(ValueError, match="never certifies"):
        batch.run(_write_batch(tmp_path, _tiny_batch(tmp_path)))


def test_main_exits_nonzero_when_batch_gate_fails(tmp_path, monkeypatch):
    import experiments.run_rq2_l5_economic_stochastic as l5

    real_run = l5.run

    def failing_run(config_path):
        summary = real_run(config_path)
        summary["gate_passed"] = False
        return summary

    monkeypatch.setattr(l5, "run", failing_run)
    config_path = _write_batch(tmp_path, _tiny_batch(tmp_path))
    monkeypatch.setattr("sys.argv", ["run", "--config", str(config_path)])
    with pytest.raises(SystemExit) as excinfo:
        batch.main()
    assert excinfo.value.code == 1
