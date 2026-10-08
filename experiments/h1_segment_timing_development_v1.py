"""Development-only single-thread span ledger; no runner or budget authority.

Snapshots are bounded, exclusive-created diagnostic files. This ledger is not a
crash-durable journal: absence/incomplete spans means unknown, never zero time.
Observer work before finish's final tick is in a span or the remainder. Final
snapshot serialization and persistence are outside that recorded window.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

SCHEMA = 'h1_segment_timing_development_v1'
PHASES = ('source', 'build', 'native_optimize', 'capture', 'audit', 'sqlite',
          'anchor', 'terminal', 'fresh_reopen', 'telemetry_io')
MAX_SPANS = 4096
MAX_BYTES = 2 * 1024 * 1024


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value < 2**63:
        raise ValueError('bounded exact integer required')
    return value


def _identity(value, size):
    if type(value) is not str or re.fullmatch('[0-9a-f]{%d}' % size, value) is None:
        raise ValueError('hex identity required')
    return value


def analyse(document):
    """Reconstruct exclusive durations independently from serialized intervals."""
    keys = {'schema', 'request_sha256', 'clock_domain', 'pid', 'thread_id',
            'start_ns', 'end_ns', 'fault', 'spans'}
    if type(document) is not dict or set(document) != keys or document['schema'] != SCHEMA:
        raise ValueError('exact timing schema required')
    _identity(document['request_sha256'], 64)
    _identity(document['clock_domain'], 32)
    _integer(document['pid'], 1)
    _integer(document['thread_id'], 1)
    start = _integer(document['start_ns'])
    end = document['end_ns']
    if end is not None and _integer(end) < start:
        raise ValueError('clock reversal')
    if document['fault'] not in (None, 'clock', 'exception', 'usage'):
        raise ValueError('bounded fault code required')
    spans = document['spans']
    if type(spans) is not list or len(spans) > MAX_SPANS:
        raise ValueError('span count bound')
    seen, children, durations = set(), {}, {}
    previous_start = start
    for index, span in enumerate(spans):
        if type(span) is not dict or set(span) != {'id', 'parent', 'stage', 'phase', 'start_ns', 'end_ns', 'status'}:
            raise ValueError('exact span schema required')
        if _integer(span['id']) != index:
            raise ValueError('ordered contiguous span ids required')
        stage = span['stage']
        if type(stage) is not int or not -1 <= stage < 232 or span['phase'] not in PHASES:
            raise ValueError('bounded stage and phase required')
        key = stage, span['phase']
        if key in seen:
            raise ValueError('duplicate stage/phase')
        seen.add(key)
        left = _integer(span['start_ns'])
        right = span['end_ns']
        if span['status'] not in ('open', 'complete', 'unknown') or ((right is not None) != (span['status'] == 'complete')):
            raise ValueError('span status/closure mismatch')
        if left < previous_start or (end is not None and left > end):
            raise ValueError('unordered/outside worker span')
        previous_start = left
        if right is not None and (_integer(right) < left or (end is not None and right > end)):
            raise ValueError('invalid interval')
        parent = span['parent']
        if parent is not None:
            if _integer(parent) >= index:
                raise ValueError('parent must precede child')
            owner = spans[parent]
            if left < owner['start_ns'] or (owner['end_ns'] is not None and
                    (right is None or right > owner['end_ns'])):
                raise ValueError('child outside parent')
        siblings = children.setdefault(parent, [])
        if siblings:
            last = spans[siblings[-1]]
            if last['end_ns'] is None or left < last['end_ns']:
                raise ValueError('overlapping siblings')
        siblings.append(index)
        durations[index] = None if right is None else right-left
    complete = end is not None and document['fault'] is None and all(v is not None for v in durations.values())
    totals = {phase: None for phase in PHASES}
    wall = None
    remainder = None
    if complete:
        totals = {phase: 0 for phase in PHASES}
        for index, span in enumerate(spans):
            exclusive = durations[index] - sum(durations[i] for i in children.get(index, []))
            if exclusive < 0:
                raise ValueError('negative exclusive duration')
            totals[span['phase']] += exclusive
        wall = end-start
        remainder = wall - sum(totals.values())
        if remainder < 0:
            raise ValueError('accounting exceeds worker wall')
    return {'schema': 'h1_segment_timing_analysis_development_v1',
            'intervals_complete': complete, 'recorded_window_wall_ns': wall,
            'exclusive_phase_ns': totals, 'unclassified_ns': remainder,
            'recorded_phase_counts': {phase: sum(s['phase'] == phase for s in spans) for phase in PHASES},
            'observer_overhead_separated': False, 'instrumentation_coverage_verified': False,
            'component_budget_verified': False, 'formal_result': False}


class Ledger:
    """One owner/thread/domain, unique (stage, phase), nested synchronous spans."""
    def __init__(self, request_sha256, *, clock=time.perf_counter_ns):
        self._clock = clock
        self._thread = threading.get_ident()
        self._pid = os.getpid()
        self._stack = []
        self._seen = set()
        self._last = _integer(clock())
        self._doc = dict(schema=SCHEMA, request_sha256=_identity(request_sha256, 64),
            clock_domain=uuid.uuid4().hex, pid=self._pid, thread_id=self._thread,
            start_ns=self._last, end_ns=None, fault=None, spans=[])

    def _owner(self):
        if os.getpid() != self._pid or threading.get_ident() != self._thread:
            raise ValueError('different process/thread clock domain')

    def _tick(self):
        try:
            current = _integer(self._clock())
            if current < self._last:
                raise ValueError('clock reversal')
            self._last = current
            return current
        except BaseException:
            self._doc['fault'] = 'clock'
            raise

    def _active(self):
        self._owner()
        if self._doc['fault'] is not None or self._doc['end_ns'] is not None:
            raise ValueError('ledger closed or poisoned')

    @contextmanager
    def span(self, stage, phase):
        self._active()
        if (type(stage) is not int or not -1 <= stage < 232 or phase not in PHASES
                or (stage, phase) in self._seen or len(self._doc['spans']) >= MAX_SPANS):
            self._doc['fault'] = 'usage'
            raise ValueError('invalid or duplicate stage/phase')
        index = len(self._doc['spans'])
        row = dict(id=index, parent=self._stack[-1] if self._stack else None,
                   stage=stage, phase=phase, start_ns=self._tick(), end_ns=None, status='open')
        self._doc['spans'].append(row)
        self._seen.add((stage, phase))
        self._stack.append(index)
        try:
            yield
        except BaseException:
            self._doc['fault'] = self._doc['fault'] or 'exception'
            raise
        else:
            self._active()
            if self._stack[-1] != index:
                self._doc['fault'] = 'usage'
                raise ValueError('non-LIFO span closure')
            row['end_ns'] = self._tick()
            row['status'] = 'complete'
        finally:
            if row['end_ns'] is None and self._doc['fault'] is not None:
                row['status'] = 'unknown'
            if self._stack and self._stack[-1] == index:
                self._stack.pop()

    def finish(self):
        self._active()
        if self._stack:
            self._doc['fault'] = 'usage'
            raise ValueError('open span')
        self._doc['end_ns'] = self._tick()
        return self.snapshot()

    def snapshot(self):
        self._owner()
        return json.loads(json.dumps(self._doc, allow_nan=False))


def write_snapshot(path, document, *, clock=time.perf_counter_ns):
    """Bound external observer interval separately; no cross-domain subtraction.

    No overwrite. Failed writes retain any bytes but return no observer receipt.
    Receipt construction/return/persistence are outside this observer interval.
    """
    observer_start = _integer(clock())
    observer_domain = uuid.uuid4().hex
    analyse(document)
    raw = json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    if len(raw) > MAX_BYTES:
        raise ValueError('snapshot byte bound exceeded')
    path = Path(path)
    with path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise OSError('short timing write')
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise OSError('timing readback differs')
    digest = sha256(raw).hexdigest()
    observer_end = _integer(clock())
    if observer_end < observer_start:
        raise ValueError('observer clock reversal')
    return {'sha256': digest, 'bytes': len(raw),
            'request_sha256': document['request_sha256'],
            'observer_clock_domain': observer_domain, 'pid': os.getpid(),
            'observer_start_ns': observer_start, 'observer_end_ns': observer_end,
            'observer_interval_ns': observer_end-observer_start,
            'receipt_overhead_included': False, 'component_budget_verified': False}
