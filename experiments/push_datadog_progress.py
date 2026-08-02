"""Push MIP solver progress as gauges to Datadog via DogStatsD.

Usage — run in a second terminal alongside the solver:

    python -m experiments.push_datadog_progress ^
        --log-root results\\logs\\rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009

Prerequisites:
* Datadog Agent running locally (localhost:5002 → Agent Manager).
* No API key needed here — the Agent handles auth and forwarding.
* Log collection enabled (see configs/datadog/README.md).

The script exits automatically when the run reaches a terminal status
(completed / failed / malformed).
"""
from __future__ import annotations

import argparse
import logging
import re
import socket
import time
from collections.abc import Sequence
from pathlib import Path

from experiments.monitor_rts_gmlc_zero_dc_ac_aware_commitment_v3 import build_status

_LOG = logging.getLogger(__name__)
_NAMESPACE = "mip.solver"
_TERMINAL_STATUSES = frozenset({"completed", "failed", "malformed"})
_DEFAULT_INTERVAL_SECONDS = 30.0
_STATSD_ADDR = ("127.0.0.1", 8125)


def _experiment_tag(log_root: Path) -> str:
    """Return a stable, low-cardinality experiment tag from the log root name.

    Extracts the repair suffix (e.g. 'repair_008') where present.
    Never uses attempt IDs or run IDs, which would grow unboundedly.
    """
    name = log_root.resolve().name
    match = re.search(r"(repair_\d+)$", name)
    return f"experiment:{match.group(1) if match else name}"


def _send_gauge(
    sock: socket.socket,
    name: str,
    value: float,
    tags: list[str],
) -> None:
    tag_str = ",".join(tags)
    payload = f"{name}:{value}|g|#{tag_str}" if tag_str else f"{name}:{value}|g"
    try:
        sock.sendto(payload.encode(), _STATSD_ADDR)
    except OSError as exc:
        _LOG.debug("DogStatsD send failed (%s): %s", name, exc)


def push_once(
    sock: socket.socket,
    log_root: Path,
    fixed_tags: list[str],
) -> str:
    """Read current solver status, push available gauges, return status string."""
    snapshot = build_status(log_root, stale_after_seconds=120.0)
    status_value = str(snapshot["status"])

    tags: list[str] = [*fixed_tags, f"status:{status_value}"]
    if candidate := snapshot.get("current_candidate"):
        tags.append(f"current_candidate:{candidate}")

    # MIP bound metrics — only populated once the solver starts reporting
    if (gap := snapshot.get("latest_gap")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.relative_gap_pct", gap, tags)
    if (abs_gap := snapshot.get("latest_absolute_gap")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.absolute_gap", abs_gap, tags)
    if (incumbent := snapshot.get("latest_incumbent")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.incumbent", incumbent, tags)
    if (lb := snapshot.get("latest_lower_bound")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.lower_bound", lb, tags)
    if (nodes := snapshot.get("latest_nodes")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.nodes", float(nodes), tags)

    # Progress counters — always emitted
    if (elapsed := snapshot.get("elapsed_seconds")) is not None:
        _send_gauge(sock, f"{_NAMESPACE}.elapsed_seconds", elapsed, tags)
    _send_gauge(
        sock,
        f"{_NAMESPACE}.completed_candidates",
        float(snapshot.get("completed_candidate_count") or 0),
        tags,
    )
    _send_gauge(
        sock,
        f"{_NAMESPACE}.requested_candidates",
        float(snapshot.get("requested_budget_candidate_count") or 0),
        tags,
    )

    _LOG.info(
        "pushed  status=%-8s  gap=%-12s  elapsed=%5ss  candidate=%s",
        status_value,
        str(snapshot.get("latest_gap")),
        f"{snapshot.get('elapsed_seconds', 0):.0f}" if snapshot.get("elapsed_seconds") else "—",
        snapshot.get("current_candidate") or "—",
    )
    return status_value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-root",
        type=Path,
        required=True,
        help="Log root directory for the repair run (contains attempt subdirs).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=_DEFAULT_INTERVAL_SECONDS,
        metavar="SECONDS",
        help=f"Poll interval in seconds (default: {_DEFAULT_INTERVAL_SECONDS}).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        dest="extra_tags",
        metavar="KEY:VALUE",
        help="Extra tag to attach to every metric (repeatable).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-5s  %(message)s",
        datefmt="%H:%M:%S",
    )

    fixed_tags = [_experiment_tag(args.log_root), *args.extra_tags]
    _LOG.info(
        "DogStatsD pusher started  log_root=%s  tags=%s",
        args.log_root,
        fixed_tags,
    )

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            try:
                status = push_once(sock, args.log_root, fixed_tags)
                if status in _TERMINAL_STATUSES:
                    _LOG.info("Run reached terminal status '%s', stopping.", status)
                    break
            except Exception as exc:
                _LOG.warning("push_once raised %s: %s", type(exc).__name__, exc)
            time.sleep(args.interval)

    return 0


__all__ = ["push_once", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
