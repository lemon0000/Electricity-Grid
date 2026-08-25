from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.evaluation.rq2_provenance_v2 import (
    canonical_sha256,
    load_contract,
    load_json_strict,
    verify_checkpoint_inventory_bundle,
    verify_stage_provenance,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/rq2_public_pipeline_provenance_contract_v2.yaml"
CONTRACT_SHA256 = (
    "b219f2d7da2a03d9026f4ac72accf565bfd7c39b16c2b42b7283ea7e6ee6b877"
)


@pytest.mark.parametrize(
    "stage",
    (
        "grid_need_dispatch_v3",
        "pairwise_replay_v3",
        "identification_grid_v3",
    ),
)
def test_live_pipeline_contract_verifies_all_stage_identities(stage: str):
    identity = load_contract(
        ROOT,
        path=CONTRACT,
        expected_sha256=CONTRACT_SHA256,
        stage=stage,
    )

    assert identity["contract_sha256"] == CONTRACT_SHA256
    assert identity["implementation"]["runner_sha256"]
    assert identity["implementation"]["module_sha256"]
    assert identity["software"]


def test_contract_rejects_implementation_drift(tmp_path: Path):
    payload = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    payload["stages"]["grid_need_dispatch_v3"]["runner"]["sha256"] = "0" * 64
    altered = tmp_path / "contract.yaml"
    altered.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="implementation drifted"):
        load_contract(
            ROOT,
            path=altered,
            expected_sha256=__import__("hashlib").sha256(
                altered.read_bytes()
            ).hexdigest(),
            stage="grid_need_dispatch_v3",
        )


def _payload() -> tuple[dict[str, object], dict[str, object]]:
    identity = load_contract(
        ROOT,
        path=CONTRACT,
        expected_sha256=CONTRACT_SHA256,
        stage="grid_need_dispatch_v3",
    )
    inventory = {
        "training_s1_0000": "1" * 64,
        "holdout_s1_0000": "2" * 64,
    }
    payload = {
        "base": {
            "schema": "rq2_public_stage_provenance_v2",
            "stage": "grid_need_dispatch_v3",
            "config_sha256": "2" * 64,
            **identity,
            "inputs": {"source": "3" * 64},
        },
        "checkpoint_inventory": inventory,
        "checkpoint_inventory_sha256": canonical_sha256(inventory),
    }
    return payload, identity


def test_upstream_provenance_rejects_config_or_checkpoint_drift():
    payload, identity = _payload()
    expected_keys = {"training_s1_0000", "holdout_s1_0000"}
    verify_stage_provenance(
        json.loads(json.dumps(payload)),
        stage="grid_need_dispatch_v3",
        expected_config_sha256="2" * 64,
        contract_identity=identity,
        expected_inputs={"source": "3" * 64},
        expected_checkpoint_keys=expected_keys,
    )
    payload["checkpoint_inventory"]["training_s1_0000"] = "4" * 64
    with pytest.raises(ValueError, match="checkpoint inventory hash drifted"):
        verify_stage_provenance(
            payload,
            stage="grid_need_dispatch_v3",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
            expected_checkpoint_keys=expected_keys,
        )


def test_rehashed_inventory_cannot_omit_an_expected_checkpoint():
    payload, identity = _payload()
    del payload["checkpoint_inventory"]["holdout_s1_0000"]
    payload["checkpoint_inventory_sha256"] = canonical_sha256(
        payload["checkpoint_inventory"]
    )

    with pytest.raises(ValueError, match="checkpoint inventory keys drifted"):
        verify_stage_provenance(
            payload,
            stage="grid_need_dispatch_v3",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
            expected_checkpoint_keys={
                "training_s1_0000",
                "holdout_s1_0000",
            },
        )


@pytest.mark.parametrize("digest", ("A" * 64, "g" * 64, "1" * 63))
def test_checkpoint_digest_must_be_lowercase_sha256(digest: str):
    payload, identity = _payload()
    payload["checkpoint_inventory"]["training_s1_0000"] = digest
    payload["checkpoint_inventory_sha256"] = canonical_sha256(
        payload["checkpoint_inventory"]
    )

    with pytest.raises(ValueError, match="checkpoint inventory is invalid"):
        verify_stage_provenance(
            payload,
            stage="grid_need_dispatch_v3",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
            expected_checkpoint_keys={
                "training_s1_0000",
                "holdout_s1_0000",
            },
        )


def test_checkpoint_inventory_bundle_checks_copy_and_summary():
    payload, identity = _payload()
    inventory = payload["checkpoint_inventory"]
    summary = {
        "checkpoint_inventory_sha256": canonical_sha256(inventory),
    }
    verified = verify_checkpoint_inventory_bundle(
        payload,
        inventory,
        summary,
        stage="grid_need_dispatch_v3",
        expected_config_sha256="2" * 64,
        contract_identity=identity,
        expected_inputs={"source": "3" * 64},
        expected_checkpoint_keys={
            "training_s1_0000",
            "holdout_s1_0000",
        },
    )
    assert verified is payload

    with pytest.raises(ValueError, match="inventory copy drifted"):
        verify_checkpoint_inventory_bundle(
            payload,
            {"training_s1_0000": "1" * 64},
            summary,
            stage="grid_need_dispatch_v3",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
            expected_checkpoint_keys={
                "training_s1_0000",
                "holdout_s1_0000",
            },
        )

    with pytest.raises(ValueError, match="inventory summary drifted"):
        verify_checkpoint_inventory_bundle(
            payload,
            inventory,
            {"checkpoint_inventory_sha256": "0" * 64},
            stage="grid_need_dispatch_v3",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
            expected_checkpoint_keys={
                "training_s1_0000",
                "holdout_s1_0000",
            },
        )


def test_strict_json_loader_rejects_duplicate_object_keys(tmp_path: Path):
    payload = tmp_path / "inventory.json"
    payload.write_text(
        '{"same":"' + "A" * 64 + '","same":"' + "1" * 64 + '"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON object key: same"):
        load_json_strict(payload)
