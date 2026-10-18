"""Guard scheduling regressions, including all unchanged v1 reader observations."""
import importlib.util
from pathlib import Path
import sys
from types import FunctionType

import pytest


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/bounded_stable_read_entry_v3.py'
SUPPORT = REPO / 'tests/test_h1_bounded_stable_read_entry_development_v1.py'
spec = importlib.util.spec_from_file_location('bounded_entry_v1_test_support', SUPPORT)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
pytestmark = prior.pytestmark

# Reuse the same differential/fault cases against the successor implementation.
globals().update((name, value) for name, value in vars(prior).items() if name.startswith('test_'))


@pytest.fixture(autouse=True)
def successor_source(monkeypatch):
    monkeypatch.setattr(prior, 'SOURCE', SOURCE)


def test_non_target_opens_do_not_run_full_guard(tmp_path):
    path = tmp_path / 'plain'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    with lease:
        before = lease.receipt()
        for _ in range(64):
            with path.open('rb') as stream:
                assert stream.read(2) == b'ab'
        with pytest.raises(FileNotFoundError):
            (tmp_path / 'absent').open('rb')
        after = lease.receipt()
        assert after['full_checks'] - before['full_checks'] == 1  # receipt only
        assert after['route_checks'] - before['route_checks'] == 66
        assert after['fallback_opens'] - before['fallback_opens'] == 65
        assert after['exact_stable_read_calls'] == 0
        assert after['light_checks'] == before['light_checks']
    assert lease.closed_receipt()['remaining_code_handles'] == 0


def test_one_canonical_read_keeps_two_full_and_forward_dispatch_guards(tmp_path):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    with lease:
        before = lease.receipt()
        assert prior.raw.read_stable(path, 32)[0] == b'abcd'
        after = lease.receipt()
        assert after['full_checks'] - before['full_checks'] == 3  # open/exit/receipt
        assert after['light_checks'] - before['light_checks'] == 4  # enter/fstat1/read/fstat2
        assert after['route_checks'] - before['route_checks'] == 8
        assert after['frontier_checks'] - before['frontier_checks'] == 10
        assert after['raw_scientific_io_observations_preserved']
        assert not after['entry_self_guard_failure_order_identical_to_v2']
        assert after['exact_stable_read_calls'] == 1
        assert after['active_streams'] == 0
    closed = lease.closed_receipt()
    assert closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_streams'] == closed['remaining_proxies'] == 0


@pytest.mark.parametrize('field', ['raw_function', 'raw_code', 'raw_defaults', 'raw_keywords', 'wrapper_defaults', 'code_read'])
def test_non_target_route_rejects_dispatch_drift(tmp_path, monkeypatch, field):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    original_open, original_read = Path.open, Path.read_bytes
    marker = RuntimeError('body retained')
    try:
        with pytest.raises(RuntimeError) as caught:
            with lease:
                if field == 'raw_function':
                    monkeypatch.setattr(prior.raw, 'read_stable', lambda *a: None)
                elif field == 'raw_code':
                    monkeypatch.setattr(prior.raw.read_stable, '__code__', (lambda *a, **k: None).__code__)
                elif field == 'raw_defaults':
                    monkeypatch.setattr(prior.raw.read_stable, '__defaults__', (1,))
                elif field == 'raw_keywords':
                    monkeypatch.setattr(prior.raw.read_stable, '__kwdefaults__', {'cap': 8})
                elif field == 'wrapper_defaults':
                    monkeypatch.setattr(Path.open, '__defaults__', (object(),))
                else:
                    monkeypatch.setattr(Path, 'read_bytes', lambda p: b'')
                with pytest.raises(ValueError, match='route|poisoned'):
                    path.open('rb')
                raise marker
        assert caught.value is marker and caught.value.__notes__
        assert lease.closed_receipt()['remaining_code_handles'] == 0
    finally:
        monkeypatch.undo()
        Path.open, Path.read_bytes = original_open, original_read


@pytest.mark.parametrize('edge', ['open', 'enter', 'fileno1', 'read', 'fileno2', 'exit'])
def test_callback_drift_rejected_at_next_boundary_and_stream_closed(tmp_path, monkeypatch, edge):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    original_open = Path.open
    original_defaults = prior.raw.read_stable.__defaults__
    opened = []
    exits = []

    def mutate():
        prior.raw.read_stable.__defaults__ = (object(),)

    def opening(p, *args, **kwargs):
        stream = original_open(p, *args, **kwargs)
        if p != path or args != ('rb',):
            return stream
        opened.append(stream)
        calls = 0
        if edge == 'open':
            mutate()

        def enter():
            if edge == 'enter':
                mutate()

        def fileno():
            nonlocal calls
            calls += 1
            if edge == 'fileno' + str(calls):
                mutate()
            return stream.fileno()

        def read(n):
            result = stream.read(n)
            if edge == 'read':
                mutate()
            return result

        def exit_(*a):
            exits.append(1)
            if edge == 'exit':
                mutate()

        return prior.Stream(stream, read, exit_=exit_, enter=enter, fileno=fileno)

    monkeypatch.setattr(Path, 'open', opening)
    module, lease = prior.load()
    marker = RuntimeError('body retained')
    try:
        with pytest.raises(RuntimeError) as caught:
            with lease:
                with pytest.raises(ValueError, match='route|poisoned|dispatch|lifetime'):
                    prior.raw.read_stable(path, 8)
                assert len(opened) == 1 and opened[0].closed
                raise marker
        assert caught.value is marker
        assert len(opened) == 1 and opened[0].closed
        assert len(exits) == (0 if edge == 'open' else 1)
        closed = lease.closed_receipt()
        assert closed['remaining_streams'] == closed['remaining_proxies'] == closed['remaining_code_handles'] == 0
    finally:
        prior.raw.read_stable.__defaults__ = original_defaults


def test_same_code_foreign_globals_rejected_before_open(tmp_path):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    foreign = FunctionType(prior.raw.read_stable.__code__, dict(vars(prior.raw)), 'foreign_reader',
        prior.raw.read_stable.__defaults__)
    with pytest.raises(ValueError, match='poisoned'):
        with lease:
            with pytest.raises(ValueError, match='globals changed'):
                foreign(path, 8)
            lease.receipt()
    closed = lease.closed_receipt()
    assert closed['remaining_streams'] == closed['remaining_proxies'] == closed['remaining_code_handles'] == 0


@pytest.mark.parametrize('body_error', [False, True])
def test_guard_and_original_exit_error_precedence(tmp_path, monkeypatch, body_error):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    original_open = Path.open
    original_defaults = prior.raw.read_stable.__defaults__
    original_error = OSError('original underlying exit failure')
    read_error = OSError('original read failure')
    opened = []

    def opening(p, *args, **kwargs):
        stream = original_open(p, *args, **kwargs)
        if p != path or args != ('rb',):
            return stream
        opened.append(stream)
        calls = 0

        def fileno():
            nonlocal calls
            calls += 1
            if calls == 2:
                prior.raw.read_stable.__defaults__ = (object(),)
            return stream.fileno()

        def read(n):
            if body_error:
                prior.raw.read_stable.__defaults__ = (object(),)
                raise read_error
            return stream.read(n)

        def exit_(*args):
            raise original_error

        return prior.Stream(stream, read, exit_=exit_, fileno=fileno)

    monkeypatch.setattr(Path, 'open', opening)
    module, lease = prior.load()
    try:
        with pytest.raises(OSError if body_error else ValueError) as caught:
            with lease:
                prior.raw.read_stable(path, 8)
        if body_error:
            assert caught.value is original_error  # unchanged original stream exit precedence
            assert caught.value.__context__ is read_error
            assert any('stable-read exit guard' in item for item in caught.value.__notes__)
        else:
            assert caught.value is not original_error
            assert any('original underlying exit failure' in item for item in caught.value.__notes__)
        assert opened[0].closed
        assert lease.closed_receipt()['remaining_code_handles'] == 0
    finally:
        prior.raw.read_stable.__defaults__ = original_defaults


def test_read_error_with_guard_drift_preserves_primary(tmp_path, monkeypatch):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    original_open = Path.open
    original_defaults = prior.raw.read_stable.__defaults__
    marker = OSError('original read failure')
    opened = []

    def opening(p, *args, **kwargs):
        stream = original_open(p, *args, **kwargs)
        if p != path or args != ('rb',):
            return stream
        opened.append(stream)

        def read(n):
            prior.raw.read_stable.__defaults__ = (object(),)
            raise marker

        return prior.Stream(stream, read)

    monkeypatch.setattr(Path, 'open', opening)
    module, lease = prior.load()
    try:
        with pytest.raises(OSError) as caught:
            with lease:
                prior.raw.read_stable(path, 8)
        assert caught.value is marker and marker.__notes__
        assert len(opened) == 1 and opened[0].closed
        assert lease.closed_receipt()['remaining_code_handles'] == 0
    finally:
        prior.raw.read_stable.__defaults__ = original_defaults


def _cell(fn,name):
    return dict(zip(fn.__code__.co_freevars,(cell.cell_contents for cell in fn.__closure__ or ())))[name]


@pytest.mark.parametrize('edge,method',[
    ('open','__init__'),('open','__enter__'),('enter','read'),('enter','__exit__'),
    ('fileno1','read'),('fileno1','__exit__'),('read','fileno'),
    ('read','__exit__'),('fileno2','__exit__')])
@pytest.mark.parametrize('mutation',['slot','code','defaults','keywords'])
def test_next_dispatch_drift_rejected_before_foreign_method(tmp_path,monkeypatch,edge,method,mutation):
    path=tmp_path/'input';path.write_bytes(b'abcd');original_open=Path.open
    streams=[];foreign=[];proxy_type=None
    def mutate():
        fn=vars(proxy_type)[method]
        if mutation=='slot':
            def spy(*args,**kwargs):foreign.append(1);raise AssertionError('foreign proxy method called')
            monkeypatch.setattr(proxy_type,method,spy)
        elif mutation=='code':monkeypatch.setattr(fn,'__code__',fn.__code__.replace(co_filename='foreign_proxy_code'))
        elif mutation=='defaults':monkeypatch.setattr(fn,'__defaults__',(object(),))
        else:monkeypatch.setattr(fn,'__kwdefaults__',{'foreign':object()})
    def opening(p,*args,**kwargs):
        stream=original_open(p,*args,**kwargs)
        if p!=path or args!=('rb',):return stream
        streams.append(stream);calls=0
        if edge=='open':mutate()
        def enter():
            if edge=='enter':mutate()
        def fileno():
            nonlocal calls
            calls+=1
            if edge=='fileno'+str(calls):mutate()
            return stream.fileno()
        def read(n):
            value=stream.read(n)
            if edge=='read':mutate()
            return value
        return prior.Stream(stream,read,enter=enter,fileno=fileno)
    monkeypatch.setattr(Path,'open',opening)
    module,lease=prior.load()
    with pytest.raises(ValueError):
        with lease:
            proxy_type=_cell(Path.open,'Proxy')
            with pytest.raises(ValueError,match='dispatch|poisoned'):
                prior.raw.read_stable(path,8)
            assert not foreign and len(streams)==1 and streams[0].closed
            lease.receipt()
    assert not foreign and lease.closed_receipt()['remaining_code_handles']==0


@pytest.mark.parametrize('field',['kernel','code_helper','handles','entry_method'])
def test_nonroute_drift_after_open_rejected_by_terminal_guard(tmp_path,monkeypatch,field):
    path=tmp_path/'input';path.write_bytes(b'abcd');original_open=Path.open
    streams=[];reads=[];foreign=[];lease=None
    code=sys.modules['performance.code_read_lease'] if 'performance.code_read_lease' in sys.modules else None
    def mutate():
        row=_cell(type(lease).receipt,'row')(lease)
        if field=='handles':monkeypatch.setitem(row,'handles',())
        elif field=='entry_method':
            monkeypatch.setattr(type(lease).closed_receipt,'__code__',type(lease).closed_receipt.__code__.replace(co_filename='foreign_entry_code'))
        elif field=='kernel':
            monkeypatch.setattr(code._kernel.GetFileSizeEx,'argtypes',())
        else:
            def spy(*args):foreign.append(1);raise AssertionError('foreign identity called')
            monkeypatch.setattr(code,'_identity',spy)
    def opening(p,*args,**kwargs):
        stream=original_open(p,*args,**kwargs)
        if p!=path or args!=('rb',):return stream
        streams.append(stream)
        def read(n):
            mutate();reads.append(1);return stream.read(n)
        return prior.Stream(stream,read)
    monkeypatch.setattr(Path,'open',opening)
    module,lease=prior.load();code=sys.modules['performance.code_read_lease']
    with pytest.raises(ValueError):
        with lease:
            with pytest.raises(ValueError,match='changed|poisoned'):
                prior.raw.read_stable(path,8)
            assert reads==[1] and not foreign and streams[0].closed
            lease.receipt()
    assert lease.closed_receipt()['remaining_code_handles']==0


@pytest.mark.parametrize('edge',['post_open','enter','exit'])
@pytest.mark.parametrize('persistent',[False,True])
def test_failure_before_actual_close_keeps_primary_and_tracks_orphan(tmp_path,monkeypatch,edge,persistent):
    path=tmp_path/'input';path.write_bytes(b'abcd');original_open=Path.open
    primary=RuntimeError('original '+edge+' failure');secondary=OSError('secondary close failure')
    calls=[];actual=[];proxy_type=None;allow_close=False
    class Broken(prior.Stream):
        def __enter__(self):
            if edge=='enter':raise primary
            return super().__enter__()
        def __exit__(self,*args):
            if edge=='exit':raise primary
            return super().__exit__(*args)
        def close(self):
            calls.append(1)
            if not allow_close and (persistent or len(calls)==1):raise secondary
            self.stream.close()
    def opening(p,*args,**kwargs):
        stream=original_open(p,*args,**kwargs)
        if p!=path or args!=('rb',):return stream
        actual.append(stream)
        if edge=='post_open':monkeypatch.setattr(proxy_type,'__enter__',lambda *a:None)
        return Broken(stream)
    monkeypatch.setattr(Path,'open',opening)
    module,lease=prior.load()
    try:
        with pytest.raises(ValueError if edge=='post_open' else RuntimeError) as caught:
            with lease:
                proxy_type=_cell(Path.open,'Proxy')
                prior.raw.read_stable(path,8)
        if edge!='post_open':assert caught.value is primary
        assert caught.value is not secondary and any('secondary close failure' in note for note in caught.value.__notes__)
        closed=lease.closed_receipt()
        assert len(calls)==2 and closed['stream_close_attempts']==2
        assert closed['remaining_code_handles']==0 and closed['path_open_restored'] and closed['path_read_bytes_restored']
        assert closed['remaining_streams']==int(persistent)
        assert actual[0].closed is (not persistent)
    finally:
        allow_close=True
        row=_cell(type(lease).receipt,'row')(lease)
        close_owned=_cell(type(lease).__exit__,'close_owned')
        for pending in tuple(row['streams']):assert close_owned(pending) is None
        assert not row['streams'] and all(stream.closed for stream in actual)
