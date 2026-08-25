from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src.evaluation.rq2_provenance import (
    canonical_sha256,
    load_contract,
    verify_stage_provenance,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/rq2_public_pipeline_provenance_contract_v1.yaml"
CONTRACT_SHA256 = (
    "08e8c96e28d1b0d5553c218a19eb8a720c53465fb88341a491a7d47bb1767c9f"
)


@pytest.mark.parametrize(
    "stage",
    (
        "grid_need_dispatch_v2",
        "pairwise_replay_v2",
        "identification_grid_v2",
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
    payload["stages"]["grid_need_dispatch_v2"]["runner"]["sha256"] = "0" * 64
    altered = tmp_path / "contract.yaml"
    altered.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="implementation drifted"):
        load_contract(
            ROOT,
            path=altered,
            expected_sha256=__import__("hashlib").sha256(
                altered.read_bytes()
            ).hexdigest(),
            stage="grid_need_dispatch_v2",
        )


def test_upstream_provenance_rejects_config_or_checkpoint_drift():
    identity = load_contract(
        ROOT,
        path=CONTRACT,
        expected_sha256=CONTRACT_SHA256,
        stage="grid_need_dispatch_v2",
    )
    inventory = {"training_s1_0000": "1" * 64}
    payload = {
        "base": {
            "schema": "rq2_public_stage_provenance_v1",
            "stage": "grid_need_dispatch_v2",
            "config_sha256": "2" * 64,
            **identity,
            "inputs": {"source": "3" * 64},
        },
        "checkpoint_inventory": inventory,
        "checkpoint_inventory_sha256": canonical_sha256(inventory),
    }

    verify_stage_provenance(
        json.loads(json.dumps(payload)),
        stage="grid_need_dispatch_v2",
        expected_config_sha256="2" * 64,
        contract_identity=identity,
        expected_inputs={"source": "3" * 64},
    )
    payload["checkpoint_inventory"]["training_s1_0000"] = "4" * 64
    with pytest.raises(ValueError, match="checkpoint inventory hash drifted"):
        verify_stage_provenance(
            payload,
            stage="grid_need_dispatch_v2",
            expected_config_sha256="2" * 64,
            contract_identity=identity,
            expected_inputs={"source": "3" * 64},
        )
