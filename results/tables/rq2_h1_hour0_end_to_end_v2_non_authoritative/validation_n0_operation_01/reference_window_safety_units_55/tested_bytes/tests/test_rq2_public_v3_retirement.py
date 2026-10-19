from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import experiments.run_rts_gmlc_public_grid_need_dispatch_v3 as runner

FORMAL_CONFIG = Path(
    "configs/rts_gmlc_public_grid_need_dispatch_v3_formal.yaml"
)


def test_v3_formal_resume_is_rejected_before_grid_data_or_solver(
    monkeypatch: pytest.MonkeyPatch,
):
    config = yaml.safe_load(FORMAL_CONFIG.read_text(encoding="utf-8"))
    execution = config["execution"]
    assert execution["formal_execution_ready"] is False
    assert execution["independent_R4_review_passed"] is False
    assert execution["user_formal_run_authorized"] is False
    assert execution["predecessor_checkpoint_reuse_allowed"] is False

    contract_identity = {
        "contract_path": "configs/rq2_public_pipeline_provenance_contract_v2.yaml",
        "contract_sha256": config["provenance"]["contract_sha256"],
        "implementation": {},
        "software": {},
    }
    def fake_preflight(path: Path):
        assert path == FORMAL_CONFIG.resolve()
        return (
            config,
            Path("."),
            {},
            {"training": [], "holdout": []},
            contract_identity,
        )

    monkeypatch.setattr(runner, "_preflight", fake_preflight)

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "retired v3 entry reached grid data or solver work: "
            f"{len(_args)} positional, {len(_kwargs)} keyword arguments"
        )

    monkeypatch.setattr(
        runner,
        "load_rts_gmlc_chronological_data",
        forbidden,
    )
    monkeypatch.setattr(runner, "_process_block", forbidden)

    with pytest.raises(ValueError, match="must all be true"):
        runner.run(FORMAL_CONFIG)
