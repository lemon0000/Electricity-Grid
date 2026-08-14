"""Update implementation.runner_sha256 and republish ifocus4 preregistration."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

import yaml

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments.process_google_power_workload_day0 import _verify_manifest
from experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal import (
    _assert_implementation_only_contract_amendment,
    _sha256,
    _write_nested_manifest,
    common_input_signature_sha256,
)

CONFIG = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
)
ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4"
)
RUNNER = Path(
    "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"
)
BASELINE_ARCHIVE = (
    ROOT
    / "preregistration_amendments"
    / "0b34bfe901d054ff_to_b1c3044f339bdbdb_20260811T185447237514Z"
    / "previous_preregistration"
)


def main() -> None:
    runner_sha = _sha256(RUNNER)
    text = CONFIG.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_implementation = False
    replaced = False
    for line in lines:
        if line.startswith("implementation:"):
            in_implementation = True
        elif in_implementation and line and not line.startswith(" ") and not line.startswith("\t"):
            in_implementation = False
        if (
            in_implementation
            and line.startswith("  runner_sha256: ")
            and not replaced
        ):
            out.append(f"  runner_sha256: {runner_sha}\n")
            replaced = True
            continue
        out.append(line)
    if not replaced:
        raise SystemExit("failed to locate implementation.runner_sha256")
    CONFIG.write_text("".join(out), encoding="utf-8")

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["implementation"]["runner_sha256"] == runner_sha

    target = ROOT / "preregistration"
    frontier = ROOT / "candidate_frontier"
    _verify_manifest(target)
    _verify_manifest(frontier)
    baseline = v4._load_json(BASELINE_ARCHIVE, "registration.json")
    expected = copy.deepcopy(baseline)
    contract = expected["input_contract"]
    contract["successor_config_sha256"] = _sha256(CONFIG)
    for key, value in config["implementation"].items():
        if key.endswith("_sha256"):
            contract["implementation"][key] = value
    expected["input_contract_sha256"] = common_input_signature_sha256(contract)
    changed = _assert_implementation_only_contract_amendment(baseline, expected)

    current = v4._load_json(target, "registration.json")
    if (
        v4._exact_json_text(current) == v4._exact_json_text(expected)
        and (target / "config.yaml").read_bytes() == CONFIG.read_bytes()
    ):
        print("ALREADY_CURRENT", expected["input_contract_sha256"])
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = ROOT / "preregistration_amendments" / (
        f"runnerfix_{current['input_contract_sha256'][:16]}_to_"
        f"{expected['input_contract_sha256'][:16]}_{stamp}"
    )
    archive.mkdir(parents=False)
    v4._write_exact_json(
        archive / "amendment.json",
        {
            "schema": "rts_gmlc_v4_repair_009_preregistration_implementation_amendment_v1",
            "amended_utc": datetime.now(timezone.utc).isoformat(),
            "method": "surgical_implementation_hash_only",
            "scientific_protocol_changed": False,
            "joint_ac_not_yet_started": True,
            "candidate_frontier_preserved": True,
            "published_frontier_input_contract_sha256": v4._load_json(
                frontier, "summary.json"
            )["input_contract_sha256"],
            "previous_input_contract_sha256": current["input_contract_sha256"],
            "amended_input_contract_sha256": expected["input_contract_sha256"],
            "changed_fields_vs_generation_baseline": changed,
            "reason": "bridge_round_artifact_contract_sha_for_joint_ac_reload",
        },
    )
    _write_nested_manifest(archive)
    _verify_manifest(archive)

    retired = target.with_name(f".preregistration.retired-{stamp}")
    target.rename(retired)
    try:

        def writer(staging: Path) -> None:
            (staging / "config.yaml").write_bytes(CONFIG.read_bytes())
            v4._write_exact_json(staging / "registration.json", expected)

        v4._publish_immutable_payload(target, writer)
    except Exception:
        import shutil

        if target.exists():
            shutil.rmtree(target)
        retired.rename(target)
        raise
    import shutil

    shutil.rmtree(retired)
    _verify_manifest(target)
    observed = v4._load_json(target, "registration.json")
    assert observed["input_contract"]["implementation"]["runner_sha256"] == runner_sha
    print("PREREG_OK", observed["input_contract_sha256"])
    print("runner", runner_sha)


if __name__ == "__main__":
    main()
