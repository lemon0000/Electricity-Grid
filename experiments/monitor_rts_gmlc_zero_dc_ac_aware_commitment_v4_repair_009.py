"""Read-only status monitor for repair-009 formal successor attempts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from experiments.monitor_rts_gmlc_zero_dc_ac_aware_commitment_v3 import build_status

DEFAULT_LOG_ROOT = Path(
    "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--stale-after-seconds", type=float, default=120.0)
    args = parser.parse_args(argv)
    status = build_status(
        args.log_root,
        stale_after_seconds=args.stale_after_seconds,
    )
    print(json.dumps(status, allow_nan=False, sort_keys=True))
    return 0


__all__ = ["DEFAULT_LOG_ROOT", "build_status", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
