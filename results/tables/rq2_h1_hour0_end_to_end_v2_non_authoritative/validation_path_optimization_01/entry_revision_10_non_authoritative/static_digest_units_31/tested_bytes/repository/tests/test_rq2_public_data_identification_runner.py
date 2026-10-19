from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments.run_rq2_public_data_identification import run


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _config(tmp_path: Path) -> Path:
    grid = tmp_path / "grid.csv"
    cfe = tmp_path / "cfe.csv"
    pairwise = tmp_path / "pairwise.csv"
    _write_csv(
        grid,
        ["id", "probability"],
        [{"id": "g0", "probability": 0.5}, {"id": "g1", "probability": 0.5}],
    )
    _write_csv(
        cfe,
        ["id", "probability"],
        [{"id": "c0", "probability": 0.5}, {"id": "c1", "probability": 0.5}],
    )
    _write_csv(
        pairwise,
        [
            "row_id",
            "column_id",
            "correct_failure",
            "b6_failure",
            "correct_shortfall",
            "b6_shortfall",
        ],
        [
            {
                "row_id": g,
                "column_id": c,
                "correct_failure": 0,
                "b6_failure": int(g[-1] != c[-1]),
                "correct_shortfall": 0,
                "b6_shortfall": 2 * int(g[-1] != c[-1]),
            }
            for g in ("g0", "g1")
            for c in ("c0", "c1")
        ],
    )
    config = {
        "evaluation": {"id": "test_identification"},
        "execution": {"formal_execution_ready": True},
        "inputs": {
            "power_system_marginal": {
                "path": str(grid),
                "sha256": _sha256(grid),
            },
            "workload_marginal": {
                "path": str(cfe),
                "sha256": _sha256(cfe),
            },
            "pairwise_outcomes": {
                "path": str(pairwise),
                "sha256": _sha256(pairwise),
            },
        },
        "fixed_policy": {
            "flexibility_underprovisioning": {"lower": 0.0, "upper": 0.0}
        },
        "classification": {
            "probability_tolerance": 1.0e-9,
            "outcome_tolerance": 1.0e-6,
        },
        "output": {"directory": str(tmp_path / "output")},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_runner_publishes_sharp_partial_identification_bounds(tmp_path: Path):
    config = _config(tmp_path)

    report = run(config)

    assert report["bounds"]["delta_failure_probability"]["lower"] == pytest.approx(0)
    assert report["bounds"]["delta_failure_probability"]["upper"] == pytest.approx(1)
    assert report["identification"]["classification"] == "partially_identified"
    assert not report["empirical_joint_distribution_claimed"]
    output = tmp_path / "output"
    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert _sha256(output / "identification_bounds.json") == manifest[
        "identification_bounds.json"
    ]


def test_runner_rejects_incomplete_pairwise_cartesian_product(tmp_path: Path):
    config_path = _config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    pairwise = Path(config["inputs"]["pairwise_outcomes"]["path"])
    rows = list(csv.DictReader(pairwise.open(encoding="utf-8", newline="")))
    _write_csv(pairwise, list(rows[0]), rows[:-1])
    config["inputs"]["pairwise_outcomes"]["sha256"] = _sha256(pairwise)
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="complete Cartesian product"):
        run(config_path)


def test_runner_fails_closed_until_formal_execution_is_authorized(tmp_path: Path):
    config_path = _config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["execution"]["formal_execution_ready"] = False
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="formal_execution_ready"):
        run(config_path)
