from pathlib import Path

import pytest

from experiments.validate_alibaba_gpu_2020_data import run


UPSTREAM_ROOT = Path("data/raw/alibaba_gpu_2020/v2020/upstream")


pytestmark = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_alibaba_gpu_2020.ps1 to enable source-data tests",
)


def test_alibaba_gpu_2020_stage1_is_complete_and_verified():
    summary = run(
        Path("configs/alibaba_gpu_2020.yaml"),
        write_output=False,
    )

    assert all(summary["checks"].values())
    assert summary["profile"] == "stage1_core"
    assert summary["archives"] == 4
    assert summary["compressed_bytes"] == 152674779
    assert not summary["evidence"]["continuous_power_available"]
    assert not summary["evidence"]["calendar_dates_real"]
