"""P2 monitor admission successor; original HANDLE owner and old caps preserved."""
import math
from pathlib import Path
import time
from src.staged_rts24_process_guard_v1 import OwnedChild,controlled_environment,scan_output


def supervise(argv, *, cwd, output, progress, limits, owner_factory=OwnedChild):
    """No scientific result inspection until the complete owned Job is quiet."""
    caps = dict(wall_seconds=3600, no_progress_seconds=65, rss_bytes=1024**3, output_bytes=64*1024**2, files=8192)
    if type(limits) is not dict or set(limits) != set(caps): raise ValueError("explicit monitor limits required")
    for name, cap in caps.items():
        v = limits[name]
        if type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= cap:
            raise ValueError("monitor limit outside P2 proposal cap")
        if name in ("rss_bytes", "output_bytes", "files") and type(v) is not int:
            raise ValueError("integer monitor byte/file limits required")
    start = last_progress = time.monotonic()
    prior, owner, exit_code, reason, error, cleanup_error = -1, None, None, None, None, None
    peak_rss = peak_commit = samples = 0
    quiet = False
    size = files = 0
    try:
        owner = owner_factory(argv, cwd=cwd, max_process_commit_bytes=1024**3,
            max_job_commit_bytes=2*1024**3, environment=controlled_environment())
        owner.release()
        while owner.poll() is None:
            now = time.monotonic()
            measurement = owner.sample()
            peak_rss, peak_commit = max(peak_rss, measurement["rss_bytes"]), max(peak_commit, measurement["peak_job_commit_bytes"])
            size, files = scan_output(output, limits["output_bytes"], limits["files"])
            try: event_size = Path(progress).stat().st_size
            except FileNotFoundError: event_size = 0
            if event_size < prior: raise ValueError("progress history shrank")
            if event_size != prior: prior, last_progress = event_size, now
            if now-start > limits["wall_seconds"]: reason = "wall_limit"
            elif now-last_progress > limits["no_progress_seconds"]: reason = "no_progress"
            elif peak_rss > limits["rss_bytes"]: reason = "rss_limit"
            elif size > limits["output_bytes"] or files > limits["files"]: reason = "storage_limit"
            samples += 1
            if reason: break
            time.sleep(.2)
        exit_code = owner.poll()
        if exit_code is not None:
            terminal = owner.sample()
            peak_commit = max(peak_commit, terminal["peak_job_commit_bytes"])
            if any(pid != owner.pid for pid in terminal["pids"]): reason = reason or "root_exited_with_descendants"
        if exit_code is not None and exit_code != 0: reason = reason or "child_exit_nonzero"
    except BaseException as exc:
        reason, error = reason or "monitor_exception", f"{type(exc).__name__}: {exc}"
    finally:
        if owner is not None:
            try:
                owner.quiesce(max_seconds=5)
                quiet = True
                exit_code = owner.poll()
            except BaseException as exc:
                cleanup_error, reason = f"{type(exc).__name__}: {exc}", reason or "cleanup_unknown"
            finally:
                try: owner.close()
                except BaseException as exc:
                    cleanup_error, reason = f"{type(exc).__name__}: {exc}", reason or "close_unknown"
                    quiet = False
    # Include output produced just before exit; reserve a terminal record.
    try:
        size, files = scan_output(output, limits["output_bytes"], limits["files"])
        if time.monotonic()-start > limits["wall_seconds"]: reason = reason or "terminal_wall_limit"
        elif time.monotonic()-last_progress > limits["no_progress_seconds"]: reason = reason or "terminal_no_progress"
        elif size+16384 > limits["output_bytes"] or files+1 > limits["files"]: reason = reason or "terminal_storage_limit"
    except BaseException as exc:
        error, reason = f"{type(exc).__name__}: {exc}", reason or "terminal_scan_error"
    return dict(exit_code=exit_code, stop_reason=reason, monitor_error=error, cleanup_error=cleanup_error,
        job_quiet_confirmed=quiet, outer_seconds=time.monotonic()-start,
        sampled_tree_peak_rss_bytes=peak_rss if samples else None, rss_observation_available=bool(samples),
        peak_job_commit_bytes=peak_commit, samples=samples, terminal_bytes=size, terminal_files=files,
        terminal_reserved_bytes=16384, owner_pid=owner.pid if owner else None,
        owner_creation_filetime=owner.creation_filetime if owner else None,
        quiescence_witness=getattr(owner, "quiescence_witness", None))
