"""Create-once development timing journal; process-interruption evidence only.

Each begin is flushed and read back before entering the body. Missing end or
terminal means unknown. File fsync is not a claim of power-loss durability for
directory entries. No resume, native execution, or component-budget authority.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import threading
import time
import uuid

from experiments import h1_raw_ingress_development_v1 as io
from experiments import h1_segment_timing_development_v1 as prior_timing

PHASES = prior_timing.PHASES

SCHEMA = 'h1_durable_timing_development_v1'
MAX_SPANS = 4096
EVENT_CAP = 2048
MAX_EVENTS = 2 * MAX_SPANS + 1


def integer(x):
    if type(x) is not int or not 0 <= x < 2**63:
        raise ValueError('bounded clock integer required')
    return x


class Journal:
    def __init__(self, root, request_sha256, *, clock=time.perf_counter_ns):
        io.pin(request_sha256)
        self.root = Path(root).resolve()
        self.clock = clock
        self.owner = (os.getpid(), threading.get_ident())
        self.last = integer(clock())
        self.stack, self.count, self.sequence = [], 0, 0
        self.poisoned = self.closed = False
        self.terminal_sha256 = None
        self.root.mkdir(exist_ok=False)
        binding = dict(schema=SCHEMA, request_sha256=request_sha256,
            clock_domain=uuid.uuid4().hex, pid=self.owner[0], thread_id=self.owner[1],
            start_ns=self.last, max_spans=MAX_SPANS, event_cap=EVENT_CAP)
        self.binding_sha256 = io.write_metadata(self.root/'binding.json', binding)
        self.head = self.binding_sha256

    def _active(self):
        if self.owner != (os.getpid(), threading.get_ident()):
            self.poisoned = True
            raise ValueError('different owner')
        if self.closed or self.poisoned:
            raise ValueError('closed or poisoned journal')

    def _event(self, kind, **fields):
        self._active()
        try:
            now = integer(self.clock())
            if now < self.last or self.sequence >= MAX_EVENTS:
                raise ValueError('clock reversal or event cap')
            row = dict(kind=kind, sequence=self.sequence, previous=self.head,
                       tick_ns=now, **fields)
            self.head = io.write_metadata(self.root/f'{self.sequence:05d}.json', row)
            self.sequence += 1
            self.last = now
        except BaseException:
            self.poisoned = True
            raise

    @contextmanager
    def span(self, stage, phase):
        self._active()
        if (type(stage) is not int or not -1 <= stage < 232
                or phase not in PHASES or self.count >= MAX_SPANS):
            self.poisoned = True
            raise ValueError('invalid stage/phase or span cap')
        index = self.count
        self._event('begin', span=index, parent=self.stack[-1] if self.stack else None,
                    stage=stage, phase=phase)
        self.count += 1
        self.stack.append(index)
        try:
            yield
            if not self.stack or self.stack[-1] != index:
                raise ValueError('non-LIFO closure')
            self._event('end', span=index)
            self.stack.pop()
        except BaseException:
            self.poisoned = True
            raise

    def finish(self):
        self._active()
        if self.stack:
            self.poisoned = True
            raise ValueError('open spans')
        self._event('terminal', spans=self.count)
        self.closed = True
        result = inspect(self.root, expected_binding_sha256=self.binding_sha256,
                         expected_terminal_sha256=self.head)
        if not result['intervals_complete']:
            self.poisoned = True
            raise ValueError('fresh timing inspection failed')
        self.terminal_sha256 = self.head
        return result


def inspect(root, *, expected_binding_sha256, expected_terminal_sha256=None):
    """Bounded fresh reconstruction. A malformed/partial journal never has totals."""
    io.pin(expected_binding_sha256)
    if expected_terminal_sha256 is not None:
        io.pin(expected_terminal_sha256)
    root = Path(root).resolve()
    result = dict(schema=SCHEMA, intervals_complete=False, exclusive_phase_ns=None,
        recorded_window_wall_ns=None, unclassified_ns=None, spans_started=0,
        errors=[], observer_overhead_separated=False, instrumentation_coverage_verified=False,
        component_budget_verified=False, resource_admission=False, formal_result=False,
        terminal_sha256=None, binding_sha256=expected_binding_sha256,
        request_sha256=None)
    observed = []

    def read(path):
        raw, stamp = io.read_stable(path, EVENT_CAP)
        observed.append((path, stamp, raw))
        doc = json.loads(raw)
        if io.encode(doc) != raw:
            raise ValueError('noncanonical journal record')
        return doc, io.digest(raw)

    try:
        # Bound directory traversal as well as the number/size of records read.
        names = set()
        with os.scandir(root) as entries:
            for entry in entries:
                names.add(entry.name)
                if len(names) > MAX_EVENTS + 1:
                    raise ValueError('journal entry cap')
        binding, head = read(root/'binding.json')
        if (head != expected_binding_sha256 or type(binding) is not dict
                or set(binding) != {'schema','request_sha256','clock_domain','pid','thread_id',
                                    'start_ns','max_spans','event_cap'}
                or binding['schema'] != SCHEMA or binding['max_spans'] != MAX_SPANS
                or binding['event_cap'] != EVENT_CAP):
            raise ValueError('binding mismatch')
        io.pin(binding['request_sha256'])
        result['request_sha256'] = binding['request_sha256']
        if (type(binding['clock_domain']) is not str or len(binding['clock_domain']) != 32
                or any(c not in '0123456789abcdef' for c in binding['clock_domain'])
                or integer(binding['pid']) == 0 or integer(binding['thread_id']) == 0):
            raise ValueError('invalid clock owner')
        start = last = integer(binding['start_ns'])
        count = len(names)-1
        if names != {'binding.json'} | {f'{i:05d}.json' for i in range(count)}:
            raise ValueError('noncontiguous/unexpected journal files')
        stack, spans = [], []
        totals = {phase: 0 for phase in PHASES}
        remainder = 0
        terminal = False
        for sequence in range(count):
            row, digest = read(root/f'{sequence:05d}.json')
            if type(row) is not dict:
                raise ValueError('event object required')
            kind = row.get('kind')
            fields = {'begin': {'span','parent','stage','phase'}, 'end': {'span'},
                      'terminal': {'spans'}}
            if (kind not in fields or set(row) != {'kind','sequence','previous','tick_ns'} | fields[kind]
                    or type(row['sequence']) is not int or row['sequence'] != sequence
                    or row['previous'] != head or terminal):
                raise ValueError('invalid event chain')
            tick = integer(row['tick_ns'])
            if tick < last:
                raise ValueError('clock reversal')
            if stack:
                totals[spans[stack[-1]]] += tick-last
            else:
                remainder += tick-last
            if kind == 'begin':
                parent = stack[-1] if stack else None
                if (type(row['span']) is not int or row['span'] != len(spans)
                        or len(spans) >= MAX_SPANS or type(row['stage']) is not int
                        or not -1 <= row['stage'] < 232 or row['phase'] not in PHASES
                        or (row['parent'] is not None and type(row['parent']) is not int)
                        or row['parent'] != parent):
                    raise ValueError('invalid begin')
                stack.append(len(spans))
                spans.append(row['phase'])
                result['spans_started'] = len(spans)
            elif kind == 'end':
                if not stack or type(row['span']) is not int or row['span'] != stack[-1]:
                    raise ValueError('non-LIFO end')
                stack.pop()
            else:
                if stack or type(row['spans']) is not int or row['spans'] != len(spans):
                    raise ValueError('incomplete terminal')
                terminal = True
            last, head = tick, digest
        if not terminal:
            raise ValueError('missing terminal; intervals unknown')
        if expected_terminal_sha256 is None or head != expected_terminal_sha256:
            raise ValueError('independently retained terminal pin required')
        # Re-read the entire bounded view, not only file metadata.
        for path, stamp, raw in observed:
            fresh, fresh_stamp = io.read_stable(path, EVENT_CAP)
            if fresh_stamp != stamp or fresh != raw:
                raise ValueError('journal changed during inspection')
        final_names = set()
        with os.scandir(root) as entries:
            for entry in entries:
                final_names.add(entry.name)
                if len(final_names) > MAX_EVENTS+1:
                    raise ValueError('journal entry cap')
        if final_names != names:
            raise ValueError('journal directory changed')
        result.update(intervals_complete=True, exclusive_phase_ns=totals,
                      recorded_window_wall_ns=last-start, unclassified_ns=remainder,
                      terminal_sha256=head)
    except (ValueError, TypeError, KeyError, OSError, OverflowError) as error:
        result['errors'].append(str(error))
    return result
