"""Formal-scale batch driver for the RQ2 mechanism entry points (agent.md 4/8/9).

Why this exists
---------------
The RQ2 story needs several *formal-scale* runs of three already-reviewed entry
points -- the L5 economic stochastic sweep, the H2 generated-scenario holdout,
and the 3-source scenario-source ablation -- repeated over frozen seeds and a
frozen neighbourhood of the mechanism parameters (so a reviewer cannot dismiss
the H1/H2/H3 signs as a single hand-picked point or a single Monte-Carlo draw).
Hand-writing ~18 near-duplicate YAMLs is error-prone and hides which numbers
were actually frozen. This driver instead reads *one* batch manifest that
declares each job as ``(runner, base_config, whitelisted overrides)``, and for
every job:

1. loads the frozen base config,
2. applies only *whitelisted* scalar overrides (seed / beta / budget cap /
   trace scales) -- never an honesty flag, a path, or a parameter_status,
3. rewrites the job's ``output`` block into an isolated per-job directory,
4. **materialises the effective config to disk and records its SHA-256**, so the
   exact frozen inputs of every run are auditable rather than implied,
5. calls the entry point's own ``run(config_path)`` (the reviewed gate logic is
   reused verbatim -- this driver adds no science), and
6. records the job's ``gate_passed`` and the honesty tags it reported.

The batch **fails closed**: any job whose entry point raised, whose gate did not
pass, or which reported ``security_certified`` other than ``False`` marks the
whole batch ``batch_gate_passed=False`` and (from ``main``) exits non-zero. H2
robustness / H1 magnitude / H3 monotonicity are *scientific findings* carried in
each job's own summary.json -- they are reported, never gated here, so a seed or
a neighbourhood point that weakens a sign is disclosed, not silently dropped.

Honesty boundaries (agent.md sections 4/8)
------------------------------------------
This driver certifies nothing. It only orchestrates already-reviewed entry
points and copies their honesty tags forward. ``security_certified`` stays
``False`` for every job (asserted, not assumed); no override may set an honesty
flag, a ``parameter_status``, or an output path; and the aggregate manifest
repeats that the batch is synthetic / trace-derived mechanism evidence, never an
engineering, contract, or empirical-VMA certification.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path

import yaml

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

# Only these dotted keys may be overridden per job. Every one is a scalar that
# changes the *statistical resolution* or the *mechanism operating point* -- the
# frozen-before-results knobs the ablation is designed to sweep. Deliberately
# excluded: anything under ``output`` (the driver owns those), every honesty flag
# (``security_certified``, ``formal_vma_published``, ``formal_economic_optimum_
# published``), and every ``parameter_status`` (would let a job relabel derived
# evidence as empirical). An override outside this set fails the batch closed.
_ALLOWED_OVERRIDE_KEYS = frozenset(
    {
        "generator.seed",
        "generator.n_train",
        "generator.n_holdout",
        "generator.grid_stress_scale_mw",
        "generator.green_call_scale_mw",
        "generator.network_activation_threshold",
        "model.beta",
        "model.lambda_risk",
        "model.max_flexibility_budget_mw",
        "reduction.target_count",
    }
)

# Output keys each runner reads. The driver rewrites every present key into the
# per-job directory, preserving only the configured basename, so jobs never
# collide and the canonical formal outputs live under one auditable tree.
_OUTPUT_KEYS = (
    "root",
    "runs_path",
    "frontier_path",
    "leaves_path",
    "policies_path",
    "arms_path",
    "summary_path",
)


def _resolve_path(configured: object) -> Path:
    path = Path(str(configured))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_yaml_mapping(path: Path, label: str) -> dict:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a YAML mapping: {path}")
    return parsed


def _set_dotted(mapping: dict, dotted_key: str, value: object) -> None:
    """Set ``mapping[a][b] = value`` for a dotted ``a.b`` key.

    The parent section (``a``) must already exist and be a mapping -- an
    override may retune an existing frozen field, never invent a new section, so
    a typo fails closed instead of silently adding an ignored key.
    """

    parts = dotted_key.split(".")
    cursor: object = mapping
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            raise ValueError(
                f"override target '{dotted_key}' has no existing section '{part}'"
            )
        cursor = cursor[part]
    leaf = parts[-1]
    if not isinstance(cursor, dict) or leaf not in cursor:
        raise ValueError(
            f"override target '{dotted_key}' does not name an existing field"
        )
    cursor[leaf] = value


def _apply_overrides(config: dict, overrides: dict) -> dict:
    if not isinstance(overrides, dict):
        raise ValueError("job.overrides must be a mapping when present")
    forbidden = [k for k in overrides if k not in _ALLOWED_OVERRIDE_KEYS]
    if forbidden:
        raise ValueError(
            f"forbidden override key(s) {sorted(forbidden)}; allowed: "
            f"{sorted(_ALLOWED_OVERRIDE_KEYS)}"
        )
    for key, value in overrides.items():
        if isinstance(value, bool):
            raise ValueError(f"override '{key}' must be numeric, not boolean")
        if not isinstance(value, (int, float)):
            raise ValueError(f"override '{key}' must be a number")
        _set_dotted(config, key, value)
    return config


def _rewrite_output(config: dict, job_dir: Path) -> None:
    output = config.get("output")
    if not isinstance(output, dict):
        raise ValueError("config.output must be a mapping")
    for key in _OUTPUT_KEYS:
        if key in output:
            basename = Path(str(output[key])).name
            output[key] = str(job_dir / basename)
    if "directory" in output:
        basename = Path(str(output["directory"])).name
        output["directory"] = str(job_dir / basename)


def _assert_honest(job_id: str, summary: dict) -> None:
    """A job may never report itself certified. Fail the batch closed if it does."""

    certified = summary.get("security_certified", False)
    if certified is not False:
        raise ValueError(
            f"job '{job_id}' reported security_certified={certified!r}; "
            "the formal batch never certifies"
        )


def run(
    batch_config_path: Path,
    output_root_override: Path | None = None,
) -> dict[str, object]:
    batch_config = _load_yaml_mapping(_resolve_path(batch_config_path), "batch config")

    batch = batch_config.get("batch")
    if not isinstance(batch, dict):
        raise ValueError("batch config must contain a 'batch' mapping")
    batch_id = batch.get("id")
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("batch.id must be a nonempty string")
    # The output root can be redirected from the CLI so a cross-machine executor
    # can point every artifact into its own uploaded run directory (the frozen
    # ``run_experiment.ps1`` only publishes files under ``$runDir``, and the
    # in-repo ``results/tables`` tree is gitignored). When absent, fall back to
    # the batch config's own root (the local/self-check default).
    output_root = (
        output_root_override
        if output_root_override is not None
        else _resolve_path(batch.get("output_root", "results/tables/rq2_formal_batch"))
    )
    batch_dir = output_root / batch_id

    jobs = batch_config.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("batch config must contain a nonempty 'jobs' list")

    seen_ids: set[str] = set()
    job_records: list[dict] = []
    batch_gate_passed = True

    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"jobs[{index}] must be a mapping")
        job_id = job.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError(f"jobs[{index}].id must be a nonempty string")
        if job_id in seen_ids:
            raise ValueError(f"duplicate job id '{job_id}'")
        seen_ids.add(job_id)

        runner_name = job.get("runner")
        if not isinstance(runner_name, str) or not runner_name:
            raise ValueError(f"job '{job_id}'.runner must be a nonempty string")
        base_config_path = _resolve_path(job.get("base_config"))
        if not base_config_path.is_file():
            raise ValueError(
                f"job '{job_id}'.base_config not found: {base_config_path}"
            )
        base_config_sha256 = _sha256(base_config_path)
        expected_base_sha256 = job.get("base_config_sha256")
        if expected_base_sha256 is not None:
            if (
                not isinstance(expected_base_sha256, str)
                or len(expected_base_sha256) != 64
            ):
                raise ValueError(
                    f"job '{job_id}'.base_config_sha256 must be a SHA-256 hex string"
                )
            if expected_base_sha256 != base_config_sha256:
                raise ValueError(
                    f"job '{job_id}' base config SHA-256 drifted: "
                    f"expected {expected_base_sha256}, got {base_config_sha256}"
                )

        # Build the effective config: frozen base + whitelisted overrides + a
        # per-job output block, then materialise it so its SHA-256 is on record.
        config = copy.deepcopy(_load_yaml_mapping(base_config_path, f"job '{job_id}' base"))
        config = _apply_overrides(config, job.get("overrides", {}))
        job_dir = batch_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        _rewrite_output(config, job_dir)

        effective_path = job_dir / "effective_config.yaml"
        effective_path.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        effective_sha256 = _sha256(effective_path)

        runner_module = importlib.import_module(runner_name)
        if not hasattr(runner_module, "run"):
            raise ValueError(f"runner '{runner_name}' has no run(config_path)")
        summary = runner_module.run(effective_path)
        if not isinstance(summary, dict):
            raise ValueError(f"job '{job_id}' runner returned a non-mapping summary")
        _assert_honest(job_id, summary)

        gate_passed = bool(summary.get("gate_passed"))
        batch_gate_passed = batch_gate_passed and gate_passed

        job_records.append(
            {
                "job_id": job_id,
                "runner": runner_name,
                "base_config": str(base_config_path.relative_to(_REPOSITORY_ROOT))
                if base_config_path.is_relative_to(_REPOSITORY_ROOT)
                else str(base_config_path),
                "base_config_sha256": base_config_sha256,
                "effective_config": str(effective_path),
                "effective_config_sha256": effective_sha256,
                "overrides": dict(job.get("overrides", {})),
                "evaluation_id": summary.get("evaluation_id"),
                "gate_passed": gate_passed,
                "security_certified": summary.get("security_certified", False),
                "parameter_status": summary.get("parameter_status")
                or summary.get("base_parameter_status"),
                # Scientific findings carried forward for the analysis pass; never
                # gated here. Absent keys stay None (a job that does not report a
                # given finding is disclosed as such rather than defaulted). H1 and
                # H3 are co-equal falsifiable claims of the L5 sweep, so the H3
                # verdict AND the Pareto frontier travel with the manifest -- the
                # cross-machine analyst must be able to reproduce/verify H3 (and the
                # deliberate C1 budget=80 collapse) from the uploaded artifact alone,
                # exactly as H1/H2 already do.
                "h1_overestimation_mw": summary.get("h1_overestimation_mw"),
                "h3_monotone_cost_tail_risk_tradeoff": summary.get(
                    "h3_monotone_cost_tail_risk_tradeoff"
                ),
                "h3_cvar_non_increasing": summary.get("h3_cvar_non_increasing"),
                "h3_expected_cost_non_decreasing": summary.get(
                    "h3_expected_cost_non_decreasing"
                ),
                "frontier": summary.get("frontier"),
                "h2_b6_underdelivers_out_of_sample": summary.get(
                    "h2_b6_underdelivers_out_of_sample"
                ),
                "h2_robust_across_sources": summary.get("h2_robust_across_sources"),
                "network_methods": summary.get("methods"),
                "scenario_method_comparison": summary.get(
                    "scenario_method_comparison"
                ),
                "network_provenance": summary.get("network_provenance"),
                "method_summaries": summary.get("method_summaries"),
                "temporal_robustness_by_network_method": summary.get(
                    "robustness_by_network_method"
                ),
                "temporal_arm_results": summary.get("arm_results"),
                "shared_holdout_sha256": summary.get("shared_holdout_sha256"),
                "generated_draw_sha256": summary.get("generated_draw_sha256"),
                "summary_path": summary.get("output_paths", {}).get("summary")
                if isinstance(summary.get("output_paths"), dict)
                else None,
            }
        )
        network_keys = (
            "network_methods",
            "scenario_method_comparison",
            "network_provenance",
            "method_summaries",
        )
        temporal_keys = (
            "temporal_robustness_by_network_method",
            "temporal_arm_results",
            "shared_holdout_sha256",
            "generated_draw_sha256",
        )
        if not any(
            key in summary
            for key in (
                "methods",
                "scenario_method_comparison",
                "network_provenance",
                "method_summaries",
            )
        ):
            for key in network_keys:
                job_records[-1].pop(key)
        if not any(
            key in summary
            for key in (
                "robustness_by_network_method",
                "arm_results",
                "shared_holdout_sha256",
                "generated_draw_sha256",
            )
        ):
            for key in temporal_keys:
                job_records[-1].pop(key)

    manifest = {
        "batch_id": batch_id,
        "job_count": len(job_records),
        "batch_gate_passed": batch_gate_passed,
        "jobs": job_records,
        # Honesty gates (agent.md sections 4/8): the batch only orchestrates
        # already-reviewed synthetic / trace-derived mechanism entry points.
        "security_certified": False,
        "formal_vma_published": False,
        "empirical_holdout_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "formal_scale_batch_orchestration_of_reviewed_rq2_mechanism_entry_"
            "points_over_frozen_seeds_and_a_frozen_mechanism_parameter_"
            "neighbourhood_reusing_each_entry_points_own_correctness_gate_adds_no_"
            "science_and_certifies_nothing"
        ),
    }

    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = batch_dir / "batch_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_formal_batch.yaml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help=(
            "Override batch.output_root (e.g. a cross-machine executor's run "
            "directory). Relative paths resolve against the repository root."
        ),
    )
    args = parser.parse_args()
    output_root = (
        _resolve_path(args.output_root) if args.output_root is not None else None
    )
    manifest = run(args.config, output_root_override=output_root)
    print(json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2))
    if not manifest["batch_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
