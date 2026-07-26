"""Read-only status monitor entry point for V4 AC-aware commitment attempts."""

from experiments.monitor_rts_gmlc_zero_dc_ac_aware_commitment_v3 import (
    build_status,
    main,
)

__all__ = ["build_status", "main"]


if __name__ == "__main__":
    main()
