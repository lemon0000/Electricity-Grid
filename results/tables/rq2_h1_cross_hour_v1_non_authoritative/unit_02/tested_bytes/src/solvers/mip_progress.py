from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CertifiedBoundInterval:
    lower_bound: float
    upper_bound: float
    absolute_gap: float
    relative_gap: float


def certified_bound_interval(
    lower_bound: object,
    upper_bound: object,
) -> CertifiedBoundInterval:
    lower = float(lower_bound)
    upper = float(upper_bound)
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("MIP bounds must be finite")
    scale = max(abs(lower), abs(upper), 1.0)
    if lower > upper:
        raise ValueError("MIP lower bound exceeds upper bound")
    gap = max(upper - lower, 0.0)
    return CertifiedBoundInterval(
        lower_bound=lower,
        upper_bound=upper,
        absolute_gap=gap,
        relative_gap=gap / scale,
    )


def highs_runtime_options(
    *,
    mip_relative_gap: float,
    threads: int,
    random_seed: int,
    feasibility_tolerance: float,
    time_limit_seconds: float,
    log_file: Path,
    mip_min_logging_interval_seconds: float,
) -> dict[str, object]:
    if not 0.0 <= float(mip_relative_gap) <= 1.0e-3:
        raise ValueError("mip_relative_gap must lie in [0, 1e-3]")
    if isinstance(threads, bool) or int(threads) <= 0:
        raise ValueError("threads must be a positive integer")
    if float(feasibility_tolerance) <= 0.0:
        raise ValueError("feasibility_tolerance must be positive")
    if float(time_limit_seconds) <= 0.0:
        raise ValueError("time_limit_seconds must be positive")
    if float(mip_min_logging_interval_seconds) <= 0.0:
        raise ValueError("mip_min_logging_interval_seconds must be positive")
    resolved_log = log_file.resolve()
    resolved_log.parent.mkdir(parents=True, exist_ok=True)
    return {
        "mip_rel_gap": float(mip_relative_gap),
        "mip_abs_gap": 0.0,
        "random_seed": int(random_seed),
        "threads": int(threads),
        "primal_feasibility_tolerance": float(feasibility_tolerance),
        "dual_feasibility_tolerance": float(feasibility_tolerance),
        "mip_feasibility_tolerance": float(feasibility_tolerance),
        "time_limit": float(time_limit_seconds),
        "output_flag": True,
        "log_to_console": False,
        "log_file": str(resolved_log),
        "mip_report_level": 2,
        "mip_min_logging_interval": float(mip_min_logging_interval_seconds),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class JsonlProgressWriter:
    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        preregistration_id: str,
        input_contract_sha256: str,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError(f"Progress log already exists: {self.path}")
        self._started = time.perf_counter()
        self._lock = threading.Lock()
        self._base = {
            "schema": "mip_progress_event_v1",
            "run_id": run_id,
            "preregistration_id": preregistration_id,
            "input_contract_sha256": input_contract_sha256,
            "pid": os.getpid(),
        }

    def emit(self, event: str, **payload: Any) -> dict[str, Any]:
        reserved = {
            *self._base,
            "timestamp_utc",
            "monotonic_elapsed_seconds",
            "event",
        }
        overlap = reserved.intersection(payload)
        if overlap:
            raise ValueError(
                "Progress payload overrides reserved fields: "
                + ", ".join(sorted(overlap))
            )
        record = {
            **self._base,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_elapsed_seconds": time.perf_counter() - self._started,
            "event": str(event),
            **payload,
        }
        encoded = json.dumps(
            record,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as output:
                output.write(encoded + "\n")
                output.flush()
                os.fsync(output.fileno())
        return record


class ProgressHeartbeat:
    def __init__(
        self,
        writer: JsonlProgressWriter,
        *,
        interval_seconds: float,
        payload: dict[str, Any],
    ) -> None:
        if float(interval_seconds) <= 0.0:
            raise ValueError("heartbeat interval must be positive")
        self._writer = writer
        self._interval_seconds = float(interval_seconds)
        self._payload = dict(payload)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> ProgressHeartbeat:
        def run() -> None:
            while not self._stop.wait(self._interval_seconds):
                self._writer.emit("heartbeat", **self._payload)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds)
