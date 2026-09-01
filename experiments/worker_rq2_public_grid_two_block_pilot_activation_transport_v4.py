"""Closed v4 worker boundary.

The only runnable mode is a non-accepting review-only pre-loader boundary.
Production is rejected before handles are opened or any scientific module is
imported.  A future execution worker must be a new reviewed successor module.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

PRODUCTION_CLOSED = True


class WorkerV4Rejected(RuntimeError):
    pass


def _review_only_preloader_worker(read_handle: int, ack_handle: int) -> int:
    # This candidate retains only the already reviewed non-accepting v3 probe.
    # It deliberately has no scientific import or accepting branch.
    from experiments import (
        worker_rq2_public_grid_two_block_pilot_activation_transport_v3 as v3,
    )

    read_descriptor = read_handle
    ack_descriptor = ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(ack_handle, os.O_WRONLY)
    return v3._worker(
        read_descriptor,
        ack_descriptor,
        read_handle=read_handle,
        ack_handle=ack_handle,
    )


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only-preloader-worker", action="store_true")
    parser.add_argument("--internal-production-worker", action="store_true")
    parser.add_argument("--read-handle", type=int)
    parser.add_argument("--ack-handle", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if args.internal_production_worker:
        raise WorkerV4Rejected(
            "v4 production worker is permanently closed; use a new reviewed successor"
        )
    if (
        not args.review_only_preloader_worker
        or args.read_handle is None
        or args.ack_handle is None
    ):
        raise WorkerV4Rejected("public or malformed worker invocation is forbidden")
    return _review_only_preloader_worker(int(args.read_handle), int(args.ack_handle))


if __name__ == "__main__":
    raise SystemExit(main())
