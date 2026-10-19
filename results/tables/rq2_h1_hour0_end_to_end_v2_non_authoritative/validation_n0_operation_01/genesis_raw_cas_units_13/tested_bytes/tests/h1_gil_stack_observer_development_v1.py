"""Bounded Python-frame observations for non-authoritative diagnostics."""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import sys
from threading import Event, Thread, get_ident
from time import monotonic


@contextmanager
def observe_owner_stack(path, *, interval_seconds=60., max_samples=16384,
                        max_frames=128, max_bytes=16*1024**2):
    """Observe the creating thread under the GIL; never inspect source or locals.

    The writer owns its stream. Cleanup signals, joins and confirms its exit;
    a stuck writer keeps its own descriptor until it exits and fails teardown.
    No C watchdog, profiling hook or trace hook is installed.
    """
    if (type(interval_seconds) not in (int, float) or not math.isfinite(interval_seconds)
            or not 0 < interval_seconds <= 60
            or type(max_samples) is not int or not 1 <= max_samples <= 16384
            or type(max_frames) is not int or not 1 <= max_frames <= 128
            or type(max_bytes) is not int or not 1024 <= max_bytes <= 16*1024**2):
        raise ValueError('bounded exact stack-observer declaration required')
    owner = get_ident()
    frame_view = sys._current_frames
    stop = Event()
    errors = []
    start = monotonic()
    receipt = dict(schema='h1_python_stack_observer_development_v1',
        owner_pid=os.getpid(), owner_thread=owner, samples=0, bytes_written=0,
        interval_seconds=interval_seconds, max_frames=max_frames,
        max_samples=max_samples, max_bytes=max_bytes,
        observer_installs_c_watchdog=False, source_or_locals_read=False,
        sampler_stopped=False, formal_result=False)
    stream = Path(path).open('x', encoding='utf-8', newline='\n')

    def sample():
        frame = None
        try:
            # sys._current_frames creates strong frame references while the
            # Python thread holds the GIL; no borrowed interpreter-frame walk.
            frames = frame_view()
            frame = frames.get(owner)
            del frames
            if frame is None:
                raise RuntimeError('creating thread has no observable frame')
            rows = []
            while frame is not None and len(rows) < max_frames:
                code = frame.f_code
                rows.append(dict(file=code.co_filename[:500], function=code.co_name[:200],
                    line=frame.f_lineno))
                frame = frame.f_back
            row = dict(elapsed_seconds=monotonic()-start, owner_thread=owner,
                frames=rows, truncated=frame is not None)
            raw = json.dumps(row, ensure_ascii=True)+'\n'
            size = len(raw.encode('utf-8'))
            if receipt['samples'] >= max_samples or receipt['bytes_written']+size > max_bytes:
                raise RuntimeError('stack-observer sample or byte budget exceeded')
            stream.write(raw)
            stream.flush()
            receipt['samples'] += 1
            receipt['bytes_written'] += size
        finally:
            # Never retain a snapshot of the running owner between samples.
            del frame

    def worker():
        try:
            while not stop.wait(interval_seconds):
                sample()
        except BaseException as error:
            errors.append(repr(error))
            stop.set()
        finally:
            try:
                stream.close()
            except BaseException as error:
                errors.append('stream close: '+repr(error))

    thread = Thread(target=worker, name='h1-diagnostic-stack-observer', daemon=True)
    try:
        thread.start()
    except BaseException:
        stream.close()
        raise
    try:
        yield receipt
    finally:
        stop.set()
        join_errors = []
        for attempt in range(2):
            try:
                thread.join(timeout=1.)
            except BaseException as error:
                join_errors.append(error)
            if not thread.is_alive() and not (attempt == 0 and join_errors):
                break
        receipt['sampler_stopped'] = not thread.is_alive()
        receipt['errors'] = list(errors)
        receipt['join_errors'] = [repr(error) for error in join_errors]
        if thread.is_alive():
            raise RuntimeError('stack-observer thread did not stop within two seconds')
        if join_errors:
            raise RuntimeError('stack-observer join failed: '+repr(receipt['join_errors'])) from join_errors[0]
        if errors:
            # A body exception remains the implicit exception context.
            raise RuntimeError('stack-observer failed: '+repr(errors))
