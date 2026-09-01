"""Permanently closed activation-transport v5 worker candidate."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

PRODUCTION_CLOSED = True


class WorkerV5Rejected(RuntimeError):
    pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-production-worker", action="store_true")
    parser.add_argument("--read-handle")
    parser.add_argument("--ack-handle")
    parser.parse_args(argv)
    raise WorkerV5Rejected(
        "v5 worker is permanently closed before handles or scientific imports"
    )


if __name__ == "__main__":
    raise SystemExit(main())
