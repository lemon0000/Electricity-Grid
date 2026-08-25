"""Build a fail-closed machine-readable readiness report for RQ2 inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


def _summary_value(summary: dict[str, object], dotted_key: str) -> object:
    value: object = summary
    for component in dotted_key.split("."):
        if not isinstance(value, dict) or component not in value:
            raise ValueError(f"summary is missing provenance key {dotted_key}")
        value = value[component]
    return value


def _verify_package(name: str, package: dict[str, object]) -> dict[str, object]:
    directory = _path(package["directory"], f"inputs.{name}.directory")
    manifest_path = directory / "SHA256SUMS.json"
    if _sha256(manifest_path) != package["manifest_sha256"]:
        raise ValueError(f"{name} package manifest identity drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.items():
        if _sha256(directory / relative) != expected:
            raise ValueError(f"{name} package artifact drifted: {relative}")
    summary_path = directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["schema"] != package["expected_schema"]:
        raise ValueError(f"{name} package schema drifted")
    live_provenance = {}
    for summary_key, raw_path in package.get("live_provenance", {}).items():
        live_path = _path(
            raw_path, f"inputs.{name}.live_provenance.{summary_key}"
        )
        live_sha256 = _sha256(live_path)
        if _summary_value(summary, summary_key) != live_sha256:
            raise ValueError(
                f"{name} package provenance drifted for {summary_key}"
            )
        live_provenance[summary_key] = {
            "path": str(live_path.relative_to(_ROOT)),
            "sha256": live_sha256,
        }
    return {
        "directory": str(directory.relative_to(_ROOT)),
        "manifest_sha256": str(package["manifest_sha256"]),
        "summary_sha256": _sha256(summary_path),
        "schema": summary["schema"],
        "live_provenance": live_provenance,
        "summary": summary,
    }


def _verify_source_manifest(
    name: str, source_manifest: dict[str, object]
) -> dict[str, object]:
    manifest_path = _path(
        source_manifest["path"], f"source_manifests.{name}.path"
    )
    expected_manifest_sha256 = str(source_manifest["sha256"])
    if _sha256(manifest_path) != expected_manifest_sha256:
        raise ValueError(f"{name} source manifest identity drifted")
    entries = 0
    for row in manifest_path.read_text(encoding="ascii").splitlines():
        expected, relative = row.split("  ", maxsplit=1)
        if _sha256(manifest_path.parent / relative) != expected:
            raise ValueError(f"{name} source artifact drifted: {relative}")
        entries += 1
    if entries == 0:
        raise ValueError(f"{name} source manifest is empty")
    return {
        "path": str(manifest_path.relative_to(_ROOT)),
        "manifest_sha256": expected_manifest_sha256,
        "entries": entries,
    }


def _validate_gate_logic(
    packages: dict[str, dict[str, object]],
    gates: dict[str, bool],
) -> None:
    alibaba = packages["alibaba_job_execution_envelopes"]["summary"]
    telemetry = packages["alibaba_gpu_telemetry"]["summary"]
    joint = packages["rts_gmlc_joint_data"]["summary"]
    nlr = packages["nlr_genai_power_profiles"]["summary"]
    wattgpu = packages["wattgpu_power_reference"]["summary"]
    cfe = packages["rts_gmlc_cfe_deficit"]["summary"]

    required_false = (
        "direct_job_to_power_mapping_ready",
        "flexibility_contract_parameters_ready",
        "empirical_joint_distribution_ready",
        "allocated_cfe_portfolio_ready",
        "outage_to_grid_need_dispatch_ready",
        "full_rq2_experiment_input_ready",
        "formal_experiment_authorized",
    )
    if any(gates[gate] for gate in required_false):
        raise ValueError("Unimplemented or unauthorized gates must remain false")

    expected_true = (
        "source_archives_verified",
        "job_execution_envelopes_ready",
        "observed_gpu_utilization_covariate_ready",
        "synchronized_grid_cfe_reliability_benchmark_ready",
        "measured_power_calibration_reference_ready",
        "t4_hardware_overlap_power_reference_ready",
    )
    if not all(gates[gate] for gate in expected_true):
        raise ValueError("Implemented data preparation gates must remain true")
    if not wattgpu["evidence_status"]["t4_exact_hardware_reference_ready"]:
        raise ValueError("T4 overlap gate lacks WattGPU package evidence")
    if not telemetry["evidence_status"][
        "gpu_work_utilization_percent_units_observed"
    ]:
        raise ValueError("GPU-utilization gate lacks Alibaba telemetry evidence")
    forbidden_claims = (
        alibaba["evidence_status"]["power_conversion_applied"],
        alibaba["evidence_status"]["deadline_observed"],
        alibaba["evidence_status"]["checkpoint_state_observed"],
        alibaba["evidence_status"]["recoverable_fraction_inferred"],
        telemetry["evidence_status"]["power_observed"],
        telemetry["evidence_status"]["direct_job_to_power_mapping_ready"],
        nlr["evidence_status"]["direct_pai_gpu_to_power_mapping_ready"],
        wattgpu["evidence_status"]["direct_pai_job_to_power_mapping_ready"],
        joint["evidence_status"]["empirical_outage_probability_claimed"],
        cfe["procurement_or_delivery_claimed"],
    )
    if any(forbidden_claims):
        raise ValueError("A source package overstates currently unavailable evidence")
    if (
        joint["evidence_status"]["cfe_contract"]
        != "eligible_resource_universe_not_allocated_portfolio"
    ):
        raise ValueError("CFE contract boundary drifted")


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    packages = {
        name: _verify_package(name, package)
        for name, package in config["inputs"].items()
    }
    source_manifests = {
        name: _verify_source_manifest(name, source_manifest)
        for name, source_manifest in config["source_manifests"].items()
    }
    gates = {name: bool(value) for name, value in config["gates"].items()}
    _validate_gate_logic(packages, gates)

    predecessor = config.get("predecessor")
    predecessor_record = None
    if predecessor is not None:
        predecessor_path = _path(
            predecessor["manifest_path"], "predecessor.manifest_path"
        )
        if _sha256(predecessor_path) != predecessor["manifest_sha256"]:
            raise ValueError("readiness predecessor manifest identity drifted")
        predecessor_record = {
            "schema": predecessor["schema"],
            "manifest_path": str(predecessor_path.relative_to(_ROOT)),
            "manifest_sha256": predecessor["manifest_sha256"],
            "status": predecessor["status"],
        }

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        report = {
            "schema": config["output"].get("schema", "rq2_data_readiness_v1"),
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "packages": {
                name: {
                    key: value
                    for key, value in package.items()
                    if key != "summary"
                }
                for name, package in packages.items()
            },
            "source_manifests": source_manifests,
            "gates": gates,
            "unresolved_requirements": list(config["unresolved_requirements"]),
            "decision": (
                "prepared_for_mapping_model_and_short_validation_only;"
                "formal_rq2_experiment_blocked"
            ),
        }
        if predecessor_record is not None:
            report["predecessor"] = predecessor_record
        report_path = staging / "data_readiness.json"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest = {"data_readiness.json": _sha256(report_path)}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_data_readiness_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
