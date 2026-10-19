"""Bounded diagnostic call counting; no scientific values are cached."""
from collections import Counter
import os


class CodeCallCounter:
    def __init__(self, counted_files, rows=None, *, max_codes=100000):
        if type(max_codes) is not int or max_codes <= 0:
            raise ValueError('positive code observation bound required')
        self.files = frozenset(os.path.normcase(str(path)) for path in counted_files)
        self.rows = Counter() if rows is None else rows
        self.max_codes = max_codes
        self.codes = {}
        self.call_events = self.cache_misses = self.counted_events = 0
        self.closed = False

    def __call__(self, frame, event, argument):
        if self.closed:
            raise ValueError('diagnostic profile already closed')
        if event != 'call':
            return
        code = frame.f_code
        identity = id(code)
        held = self.codes.get(identity)
        if held is None:
            if len(self.codes) >= self.max_codes:
                raise ValueError('diagnostic code observation bound exceeded')
            filename = os.path.normcase(code.co_filename)
            key = (filename, code.co_name, code.co_firstlineno) if filename in self.files else None
            held = code, key
            # Strong references prevent object-ID reuse during this invocation.
            self.codes[identity] = held
            self.cache_misses += 1
        elif held[0] is not code:
            raise ValueError('diagnostic code identity changed')
        self.call_events += 1
        if held[1] is not None:
            self.rows[held[1]] += 1
            self.counted_events += 1

    def close(self):
        entries = len(self.codes)
        self.codes.clear()
        self.closed = True
        return dict(call_events=self.call_events, counted_events=self.counted_events,
            unique_code_objects=entries, filename_normalizations=self.cache_misses,
            max_code_objects=self.max_codes, all_code_metadata_cache_entries_cleared=not self.codes,
            scientific_value_cache=False, formal_result=False)
