"""Bounded one-shot watchdog for the registered no-solver journal probe."""
import json
import os
from pathlib import Path
import subprocess
import stat
import sys
import time
import psutil

ROOT = Path(__file__).absolute().parents[1]
OUTPUT = ROOT/"results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01"
LIMITS = dict(wall_seconds=180, no_progress_seconds=30, rss_bytes=512*1024**2, output_bytes=64*1024**2, files=5000)


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def scan_output(root):
    size, files = 0, 0
    for path in root.rglob("*"):
        try: info = path.stat()
        except FileNotFoundError: continue  # A pending file may just have been renamed.
        if stat.S_ISREG(info.st_mode): size, files = size+info.st_size, files+1
        if files > LIMITS["files"] or size > LIMITS["output_bytes"]: break
    return size, files


def kill_tree(process):
    try:
        children = psutil.Process(process.pid).children(recursive=True)
        for child in reversed(children):
            try: child.kill()
            except psutil.NoSuchProcess: pass
    except psutil.NoSuchProcess: pass
    finally:
        try: process.kill()
        except ProcessLookupError: pass


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    write(OUTPUT/"launcher_start.json", dict(limits=LIMITS, argv=[sys.executable, "-B", "experiments/staged_rts24_journal_diagnostic_v1.py"],
                                           authority="DRAFT_NONAUTHORITATIVE"))
    reason, peak, samples, last_progress, size, files = None, 0, 0, start, 0, 0
    error, cleanup_error, exit_code, process = None, None, None, None
    prior_event_size = -1
    with (OUTPUT/"stdout.log").open("xb") as stdout, (OUTPUT/"stderr.log").open("xb") as stderr:
        try:
            process = subprocess.Popen([sys.executable, "-B", "experiments/staged_rts24_journal_diagnostic_v1.py"],
                cwd=ROOT, stdout=stdout, stderr=stderr, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            while process.poll() is None:
                now = time.perf_counter()
                try:
                    parent = psutil.Process(process.pid)
                    rss = sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)] if p.is_running())
                    peak = max(peak, rss)
                except psutil.NoSuchProcess: pass
                size, files = scan_output(OUTPUT)
                try: event_size = (OUTPUT/"events.jsonl").stat().st_size
                except FileNotFoundError: event_size = 0
                if event_size != prior_event_size: last_progress, prior_event_size = now, event_size
                if now-start > LIMITS["wall_seconds"]: reason = "wall_limit"
                elif now-last_progress > LIMITS["no_progress_seconds"]: reason = "no_progress"
                elif peak > LIMITS["rss_bytes"]: reason = "rss_limit"
                elif size > LIMITS["output_bytes"] or files > LIMITS["files"]: reason = "storage_limit"
                samples += 1
                if reason: break
                time.sleep(.2)
        except BaseException as exception:
            reason, error = "launcher_exception", f"{type(exception).__name__}: {exception}"
        finally:
            if process is not None:
                try:
                    if process.poll() is None: kill_tree(process)
                    exit_code = process.wait(timeout=10)
                except BaseException as exception:
                    cleanup_error = f"{type(exception).__name__}: {exception}"
                    reason = reason or "cleanup_error"
                    try:
                        kill_tree(process)
                        exit_code = process.wait(timeout=5)
                    except BaseException as final_error: cleanup_error += f"; {type(final_error).__name__}: {final_error}"
    # The child can finish between samples. Include its final report/completion and
    # reserve the watchdog's own small terminal file before deciding success.
    reservation = 16*1024
    try:
        size, files = scan_output(OUTPUT)
        if time.perf_counter()-start > LIMITS["wall_seconds"]: reason = reason or "terminal_wall_limit"
        elif time.perf_counter()-last_progress > LIMITS["no_progress_seconds"]: reason = reason or "terminal_no_progress"
        elif size+reservation > LIMITS["output_bytes"] or files+1 > LIMITS["files"]: reason = reason or "terminal_storage_limit"
    except BaseException as exception:
        reason = reason or "terminal_scan_exception"
        error = (error or "")+f"; {type(exception).__name__}: {exception}"
    report = dict(authority="DRAFT_NONAUTHORITATIVE", exit_code=exit_code, stop_reason=reason,
        outer_seconds=time.perf_counter()-start, sampled_tree_peak_rss_bytes=peak, samples=samples,
        terminal_files_excluding_launcher=files, terminal_bytes_excluding_launcher=size,
        launcher_reserved_bytes=reservation, pid=process.pid if process else None, limits=LIMITS,
        launcher_error=error, cleanup_error=cleanup_error,
        child_running_after_cleanup=process.poll() is None if process else False)
    if len((json.dumps(report, sort_keys=True, indent=2, allow_nan=False)+"\n").encode("utf-8")) > reservation:
        report["stop_reason"] = reason = reason or "launcher_record_budget"
        report["launcher_error"], report["cleanup_error"] = str(error)[:512], str(cleanup_error)[:512]
    write(OUTPUT/"launcher.json", report)
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if exit_code == 0 and reason is None and not report["child_running_after_cleanup"] else 1


if __name__ == "__main__": sys.exit(main())
