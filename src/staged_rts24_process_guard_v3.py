"""Draft monitor with a bounded parent-record reservation; original HANDLE owner."""
import json
import math
from pathlib import Path
import time
from src.staged_rts24_process_guard_v1 import OwnedChild,controlled_environment,scan_output


MAX_MEMBER_HANDLES = 1024
TERMINAL_RECORD_BYTES = 128*1024
PARENT_RECORD_BYTES = 128*1024
RESERVED_BYTES = TERMINAL_RECORD_BYTES+PARENT_RECORD_BYTES
RESERVED_FILES = 2


def record_image(record):
    raw = json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    if len(raw) > TERMINAL_RECORD_BYTES: raise ValueError('launcher record exceeds 128 KiB')
    return raw


def error_details(error, message_limit=256):
    try: name = type(error).__name__[:64]
    except BaseException: name = 'Exception'
    try: message = str(error)
    except BaseException: message = '[message unavailable]'
    if len(message) > message_limit: message = message[:message_limit-11]+'[truncated]'
    return dict(type=name, message=message)


def bounded_error(error):
    detail = error_details(error, 448)
    return detail['type']+': '+detail['message']


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
    if limits['output_bytes'] < RESERVED_BYTES or limits['files'] < RESERVED_FILES:
        raise ValueError('parent record reservation does not fit monitor limits')
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
            elif peak_commit > 2*1024**3: reason = 'commit_limit'
            elif size+RESERVED_BYTES > limits["output_bytes"] or files+RESERVED_FILES > limits["files"]: reason = "storage_limit"
            samples += 1
            if reason: break
            time.sleep(.2)
        exit_code = owner.poll()
        if exit_code is not None:
            terminal = owner.sample()
            peak_commit = max(peak_commit, terminal["peak_job_commit_bytes"])
            if samples: peak_rss = max(peak_rss, terminal['rss_bytes'])
            if terminal['rss_bytes'] > limits['rss_bytes']: reason = reason or 'terminal_rss_limit'
            if peak_commit > 2*1024**3: reason = reason or 'terminal_commit_limit'
            if any(pid != owner.pid for pid in terminal["pids"]): reason = reason or "root_exited_with_descendants"
        if exit_code is not None and exit_code != 0: reason = reason or "child_exit_nonzero"
    except BaseException as exc:
        reason, error = reason or "monitor_exception", bounded_error(exc)
    finally:
        if owner is not None:
            try:
                owner.quiesce(max_seconds=5)
                quiet = True
                exit_code = owner.poll()
                post_quiet = owner.sample()
                peak_commit = max(peak_commit, post_quiet['peak_job_commit_bytes'])
                if peak_commit > 2*1024**3: reason = reason or 'post_quiesce_commit_limit'
            except BaseException as exc:
                cleanup_error, reason = bounded_error(exc), reason or "cleanup_unknown"
            finally:
                try: owner.close()
                except BaseException as exc:
                    cleanup_error, reason = bounded_error(exc), reason or "close_unknown"
                    quiet = False
    # Include output produced just before exit; reserve a terminal record.
    try:
        size, files = scan_output(output, limits["output_bytes"], limits["files"])
        if time.monotonic()-start > limits["wall_seconds"]: reason = reason or "terminal_wall_limit"
        elif time.monotonic()-last_progress > limits["no_progress_seconds"]: reason = reason or "terminal_no_progress"
        elif size+RESERVED_BYTES > limits["output_bytes"] or files+RESERVED_FILES > limits["files"]: reason = reason or "terminal_storage_limit"
    except BaseException as exc:
        error, reason = bounded_error(exc), reason or "terminal_scan_error"
    result = dict(exit_code=exit_code, stop_reason=reason, monitor_error=error, cleanup_error=cleanup_error,
        job_quiet_confirmed=quiet, outer_seconds=time.monotonic()-start,
        sampled_tree_peak_rss_bytes=peak_rss if samples else None, rss_observation_available=bool(samples),
        peak_job_commit_bytes=peak_commit, samples=samples, terminal_bytes=size, terminal_files=files,
        terminal_reserved_bytes=TERMINAL_RECORD_BYTES, parent_reserved_bytes=PARENT_RECORD_BYTES,
        terminal_reserved_files=1, parent_reserved_files=1, member_handle_cap=MAX_MEMBER_HANDLES, owner_pid=owner.pid if owner else None,
        owner_creation_filetime=owner.creation_filetime if owner else None,
        quiescence_witness=getattr(owner, "quiescence_witness", None))
    record_image(result)
    return result
