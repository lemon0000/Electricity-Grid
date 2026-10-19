import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ingress_dev', ROOT/'experiments/h1_raw_ingress_development_v1.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def inspect(writer):
    return api.inspect(writer.root, expected_request=writer.request,
        expected_binding_sha256=api.digest(api.encode(writer.binding)))


def test_durable_raw_precedes_consumer_and_no_scientific_claim(tmp_path):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=2)
    def consume(raw):
        seen = inspect(writer)
        assert seen['retained_complete_raw'] == 1
        assert seen['consumer_returned'] == 0
        return {'arbitrary_result': 'not a certificate'}
    assert writer.deliver(0, lambda: b'raw', consume)['arbitrary_result'] == 'not a certificate'
    writer.deliver(1, lambda: b'next', lambda raw: raw)
    result = writer.finish()
    assert result['callback_sequence_complete']
    assert result['retained_complete_raw'] == 2
    assert not result['formal_result'] and not result['native_execution_authenticated']
    assert not result['retry_authorized'] and not result['resource_admission']
    with pytest.raises(ValueError): writer.deliver(2, lambda: b'x', lambda r: r)
    with pytest.raises(FileExistsError): api.Ingress(writer.root, 'a'*64, stages=2)


@pytest.mark.parametrize('window', ['producer', 'consumer', 'intent', 'raw', 'receipt', 'outcome', 'terminal'])
def test_failure_windows_preserve_files_poison_and_never_retry(tmp_path, monkeypatch, window):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    calls = []
    original = api.write_new
    target = {'intent':'intent.json','raw':'raw.bin','receipt':'raw_receipt.json',
              'outcome':'outcome.json','terminal':'terminal.json'}.get(window)
    def fault(path, raw):
        if path.name == target:
            # Represents interrupted/short write, not a completed event.
            path.write_bytes(raw[:1])
            raise OSError('injected')
        original(path, raw)
    monkeypatch.setattr(api, 'write_new', fault)
    def producer():
        calls.append('producer')
        if window == 'producer': raise RuntimeError('injected producer')
        return b'complete raw witness'
    def consumer(raw):
        calls.append('consumer')
        if window == 'consumer': raise RuntimeError('injected consumer')
    with pytest.raises((RuntimeError, OSError)):
        writer.deliver(0, producer, consumer)
        writer.finish()
    result = inspect(writer)
    assert not result['callback_sequence_complete'] and writer.poisoned
    before = list(calls)
    with pytest.raises(ValueError): writer.deliver(0, producer, consumer)
    assert calls == before
    if window in ('consumer', 'outcome', 'terminal', 'receipt'):
        assert (writer.root/'000/raw.bin').read_bytes() == b'complete raw witness'
    if window in ('intent', 'raw', 'receipt', 'producer'):
        assert 'consumer' not in calls


@pytest.mark.parametrize('size', [0, 1, 16, 17])
def test_raw_boundaries_no_truncation(tmp_path, monkeypatch, size):
    monkeypatch.setattr(api, 'RAW_CAP', 16)
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    calls = []
    if size in (0, 17):
        with pytest.raises(ValueError): writer.deliver(0, lambda: b'x'*size, calls.append)
        assert not calls and not (writer.root/'000/raw.bin').exists()
    else:
        writer.deliver(0, lambda: b'x'*size, calls.append)
        assert writer.finish()['callback_sequence_complete']
        assert calls == [b'x'*size]


@pytest.mark.parametrize('index', [True, -1, 1])
def test_bad_stage_stops_before_producer(tmp_path, index):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    with pytest.raises(ValueError): writer.deliver(index, lambda: pytest.fail('must not call'), lambda r: r)
    assert writer.poisoned


def test_incomplete_finish_owner_and_mutation(tmp_path, monkeypatch):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    with pytest.raises(ValueError): writer.finish()
    other = api.Ingress(tmp_path/'other', 'b'*64, stages=1)
    monkeypatch.setattr(api.os, 'getpid', lambda: other.owner[0]+1)
    with pytest.raises(ValueError, match='owner'): other.deliver(0, lambda: b'x', lambda r: r)


def test_consumer_mutation_rejected(tmp_path):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    with pytest.raises(OSError, match='changed during'):
        writer.deliver(0, lambda: b'x', lambda r: (writer.root/'000/raw.bin').write_bytes(b'y'))
    assert not inspect(writer)['callback_sequence_complete']


@pytest.mark.parametrize('damage', ['raw','binding','request','bool','extra','gap','terminal'])
def test_fresh_reader_refuses_tamper_and_wrong_binding(tmp_path, damage):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=2)
    for i in range(2): writer.deliver(i, lambda: b'x', lambda r: None)
    writer.finish()
    if damage == 'raw': (writer.root/'000/raw.bin').write_bytes(b'y')
    elif damage == 'binding': (writer.root/'binding.json').write_bytes(b'{}')
    elif damage == 'request': writer.request = 'b'*64
    elif damage == 'bool':
        path = writer.root/'001/intent.json'
        doc = json.loads(path.read_bytes()); doc['stage'] = True
        path.write_bytes(api.encode(doc))
    elif damage == 'extra': (writer.root/'extra').write_bytes(b'x')
    elif damage == 'gap': (writer.root/'000').rename(writer.root/'unexpected')
    elif damage == 'terminal': (writer.root/'terminal.json').write_bytes(b'{}')
    result = inspect(writer)
    assert not result['callback_sequence_complete'] and result['errors']


def test_all_232_saved_reports_through_ingress_zero_solver(tmp_path):
    path = ROOT/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative/collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    assert api.digest(path.read_bytes()) == 'bc9ff4270ec834347f440444fdbf0d0d328705b4d4a6c4c7aad8114e8fcd2115'
    writer = api.Ingress(tmp_path/'saved_raw', 'a'*64, stages=232)
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        for seq, count, pin in db.execute('SELECT seq,payload_bytes,payload_sha FROM events WHERE payload_bytes>0 ORDER BY seq'):
            raw = b''.join(r[0] for r in db.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index', (seq,)))
            assert len(raw) == count and api.digest(raw) == pin
            assert writer.deliver(seq-1, lambda raw=raw: raw, api.digest) == pin
    assert writer.finish()['retained_complete_raw'] == 232


def test_writer_short_write_and_fsync_failure(tmp_path, monkeypatch):
    class Short:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def write(self, raw): return len(raw)-1
    with monkeypatch.context() as ctx:
        ctx.setattr(api.Path, 'open', lambda *a, **k: Short())
        with pytest.raises(OSError, match='short'): api.write_new(tmp_path/'short', b'x')
    monkeypatch.setattr(api.os, 'fsync', lambda fd: (_ for _ in ()).throw(OSError('fsync')))
    with pytest.raises(OSError, match='fsync'): api.write_new(tmp_path/'fsync', b'raw')
    assert (tmp_path/'fsync').read_bytes() == b'raw'


def test_external_abort_prevents_further_delivery(tmp_path):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=2)
    writer.deliver(0, lambda: b'raw', lambda r: r)
    writer.abort()
    state = inspect(writer)
    assert state['retained_complete_raw'] == 1
    assert 'external_consumer_failed' in state['errors']
    with pytest.raises(ValueError, match='poisoned'):
        writer.deliver(1, lambda: pytest.fail('must not call'), lambda r: r)
    with pytest.raises(ValueError): writer.finish()


def test_replace_between_stat_and_open_is_rejected(tmp_path, monkeypatch):
    path, other = tmp_path/'raw', tmp_path/'replacement'
    path.write_bytes(b'x'); other.write_bytes(b'y')
    original = api.Path.open
    def replace(p, *args, **kwargs):
        if p == path and args == ('rb',): other.replace(path)
        return original(p, *args, **kwargs)
    monkeypatch.setattr(api.Path, 'open', replace)
    with pytest.raises(ValueError, match='replaced'):
        api.read_stable(path, 16)


def test_growth_during_handle_read_is_bounded_and_rejected(tmp_path, monkeypatch):
    path = tmp_path/'raw'; path.write_bytes(b'x')
    original = api.Path.open
    requested = []
    class Growing:
        def __init__(self): self.stream = original(path, 'rb')
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def fileno(self): return self.stream.fileno()
        def read(self, count):
            requested.append(count)
            with original(path, 'ab') as writer: writer.write(b'y'*32)
            return self.stream.read(count)
    monkeypatch.setattr(api.Path, 'open', lambda p,*a,**kw: Growing() if p == path and a == ('rb',) else original(p,*a,**kw))
    with pytest.raises(ValueError, match='changed or exceeded'):
        api.read_stable(path, 16)
    assert requested == [17]


def test_inspector_view_change_after_valid_terminal_stays_unresolved(tmp_path, monkeypatch):
    writer = api.Ingress(tmp_path/'new', 'a'*64, stages=1)
    writer.deliver(0, lambda: b'x', lambda r: r); writer.finish()
    original = api.read_stable
    def change(path, cap):
        result = original(path, cap)
        if path.name == 'terminal.json':
            (writer.root/'000/raw.bin').write_bytes(b'changed')
        return result
    monkeypatch.setattr(api, 'read_stable', change)
    assert not inspect(writer)['callback_sequence_complete']
