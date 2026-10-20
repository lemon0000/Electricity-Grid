"""Fail-closed provenance contracts for the E0-aware RQ2 successor."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import yaml

PROVENANCE_CONTRACT_SCHEMA = "rq2_public_pipeline_provenance_contract_v3"
STAGE_PROVENANCE_SCHEMA = "rq2_public_stage_provenance_v3"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json_strict(path: Path) -> Any:
    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def load_contract(
    root: Path,
    *,
    path: Path,
    expected_sha256: str,
    stage: str,
) -> dict[str, Any]:
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError("pipeline provenance contract SHA-256 drifted")
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(contract, dict)
        or contract.get("schema") != PROVENANCE_CONTRACT_SCHEMA
        or stage not in contract.get("stages", {})
    ):
        raise ValueError("pipeline provenance contract is invalid")
    stage_contract = contract["stages"][stage]
    expected_keys = {"runner", "modules", "software"}
    if set(stage_contract) != expected_keys:
        raise ValueError(f"{stage} provenance contract fields drifted")
    implementation = {
        "runner_sha256": _verified_path_hash(root, stage_contract["runner"]),
        "module_sha256": {
            name: _verified_path_hash(root, item)
            for name, item in sorted(stage_contract["modules"].items())
        },
    }
    software = {}
    for package, expected in sorted(stage_contract["software"].items()):
        try:
            observed = version(package)
        except PackageNotFoundError as error:
            raise ValueError(
                f"required provenance package is unavailable: {package}"
            ) from error
        if observed != str(expected):
            raise ValueError(
                f"{stage} software identity drifted: {package}"
            )
        software[package] = observed
    return {
        "contract_path": str(path.relative_to(root)),
        "contract_sha256": expected_sha256,
        "implementation": implementation,
        "software": software,
    }


def _verified_path_hash(root: Path, item: object) -> str:
    if (
        not isinstance(item, dict)
        or set(item) != {"path", "sha256"}
        or not isinstance(item["path"], str)
        or not isinstance(item["sha256"], str)
    ):
        raise ValueError("provenance path entry is invalid")
    path = root / item["path"]
    observed = sha256_file(path)
    if observed != item["sha256"]:
        raise ValueError(f"provenance implementation drifted: {item['path']}")
    return observed


def stage_base_provenance(
    *,
    stage: str,
    config_path: Path,
    contract_identity: dict[str, Any],
    inputs: dict[str, object],
) -> dict[str, object]:
    return {
        "schema": STAGE_PROVENANCE_SCHEMA,
        "stage": stage,
        "config_sha256": sha256_file(config_path),
        **contract_identity,
        "inputs": inputs,
    }


def verify_stage_provenance(
    payload: object,
    *,
    stage: str,
    expected_config_sha256: str,
    contract_identity: dict[str, Any],
    expected_inputs: dict[str, object],
    expected_checkpoint_keys: Collection[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError(f"{stage} provenance must be an object")
    if set(payload) != {
        "base",
        "checkpoint_inventory",
        "checkpoint_inventory_sha256",
    }:
        raise ValueError(f"{stage} stage provenance fields drifted")
    expected = {
        "schema": STAGE_PROVENANCE_SCHEMA,
        "stage": stage,
        "config_sha256": expected_config_sha256,
        **contract_identity,
        "inputs": expected_inputs,
    }
    base = payload.get("base")
    if base != expected:
        raise ValueError(f"{stage} stage provenance drifted")
    expected_keys = set(expected_checkpoint_keys)
    if (
        not expected_keys
        or len(expected_keys) != len(expected_checkpoint_keys)
        or any(not isinstance(name, str) or not name for name in expected_keys)
    ):
        raise ValueError(f"{stage} expected checkpoint keys are invalid")
    checkpoint_inventory = payload.get("checkpoint_inventory")
    if (
        not isinstance(checkpoint_inventory, dict)
        or not checkpoint_inventory
        or any(
            not isinstance(name, str)
            or not name
            or not isinstance(digest, str)
            or _SHA256_PATTERN.fullmatch(digest) is None
            for name, digest in checkpoint_inventory.items()
        )
    ):
        raise ValueError(f"{stage} checkpoint inventory is invalid")
    if set(checkpoint_inventory) != expected_keys:
        raise ValueError(f"{stage} checkpoint inventory keys drifted")
    if payload.get("checkpoint_inventory_sha256") != canonical_sha256(
        checkpoint_inventory
    ):
        raise ValueError(f"{stage} checkpoint inventory hash drifted")
    return payload


def verify_checkpoint_inventory_bundle(
    payload: object,
    checkpoint_inventory: object,
    summary: object,
    *,
    stage: str,
    expected_config_sha256: str,
    contract_identity: dict[str, Any],
    expected_inputs: dict[str, object],
    expected_checkpoint_keys: Collection[str],
) -> dict[str, Any]:
    verified = verify_stage_provenance(
        payload,
        stage=stage,
        expected_config_sha256=expected_config_sha256,
        contract_identity=contract_identity,
        expected_inputs=expected_inputs,
        expected_checkpoint_keys=expected_checkpoint_keys,
    )
    if checkpoint_inventory != verified["checkpoint_inventory"]:
        raise ValueError(f"{stage} checkpoint inventory copy drifted")
    inventory_sha256 = canonical_sha256(checkpoint_inventory)
    if (
        verified["checkpoint_inventory_sha256"] != inventory_sha256
        or not isinstance(summary, dict)
        or summary.get("checkpoint_inventory_sha256") != inventory_sha256
    ):
        raise ValueError(f"{stage} checkpoint inventory summary drifted")
    return verified
