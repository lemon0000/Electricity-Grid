"""Actual Windows code ownership plus differential regular-file failures."""
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import sys
import threading
from types import ModuleType,SimpleNamespace

import pytest

from experiments import h1_raw_ingress_development_v1 as raw

REPO=Path(__file__).resolve().parents[1]
ENTRY=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_path_optimization_01/entry_revision_07'
SOURCE=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/bounded_stable_read_entry_v1.py'
pytestmark=pytest.mark.skipif(os.name!='nt',reason='actual Windows code handles')


def load():
    if 'performance' not in sys.modules:
        package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
    if 'performance.code_read_lease' not in sys.modules:
        spec=importlib.util.spec_from_file_location('performance.code_read_lease',ENTRY/'code_read_lease.py')
        code=importlib.util.module_from_spec(spec);sys.modules[spec.name]=code;spec.loader.exec_module(code)
        sys.modules['performance'].code_read_lease=code
    name='performance.bounded_stable_read_entry'
    spec=importlib.util.spec_from_file_location(name,SOURCE)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    pins={p:sha256(p.read_bytes()).hexdigest() for p in (SOURCE,Path(raw.__file__).resolve(),ENTRY/'code_read_lease.py')}
    return module,module.BoundedStableReadLease(pins,root=Path('D:/'))


class Stream:
    def __init__(self,stream,read=None,exit_=None,enter=None,fileno=None):
        self.stream=stream;self._read=read or stream.read;self._exit=exit_;self._enter=enter;self._fileno=fileno
    def __enter__(self):
        if self._enter:self._enter()
        self.stream.__enter__();return self
    def __exit__(self,*args):
        result=self.stream.__exit__(*args)
        return self._exit(*args) if self._exit else result
    def fileno(self):return self._fileno() if self._fileno else self.stream.fileno()
    def read(self,n=-1):return self._read(n)
    def close(self):self.stream.close()


@pytest.mark.parametrize('size,cap',[(0,0),(0,2**25),(1,1),(1,2**25),(31,32),(32,32),(4096,2**25)])
def test_actual_reader_tuple_equal_and_bounded_request(tmp_path,monkeypatch,size,cap):
    path=tmp_path/'input';path.write_bytes(b'x'*size)
    expected=raw.read_stable(path,cap);original=Path.open;requests=[]
    def opening(p,*a,**kw):
        stream=original(p,*a,**kw)
        return Stream(stream,lambda n:(requests.append(n),stream.read(n))[1]) if p==path and a==('rb',) else stream
    monkeypatch.setattr(Path,'open',opening) # definition-before I/O observation seam
    module,lease=load()
    with lease:
        assert raw.read_stable(path,cap)==expected
        proof=lease.receipt()
        assert proof['exact_stable_read_calls']==1 and proof['actual_requested_bytes']==size+1
        assert proof['original_requested_bytes']==cap+1 and proof['active_streams']==0
        assert proof['code_lease']['held_handles']>3
        assert proof['formal_result'] is proof['source_or_result_cache'] is False
    assert requests==[size+1] and Path.open is opening


def test_non_target_text_write_and_rb_delegate(tmp_path):
    path=tmp_path/'input';module,lease=load();original=Path.open
    with lease:
        with path.open('w',encoding='utf-8') as stream:stream.write('abc')
        with path.open('rb') as stream:assert stream.read(1)==b'a' and stream.read()==b'bc'
        assert path.read_text(encoding='utf-8')=='abc'
        assert lease.receipt()['exact_stable_read_calls']==0
    assert Path.open is original


def test_initial_cap_and_nonregular_preserve_error(tmp_path):
    path=tmp_path/'input';path.write_bytes(b'ab');module,lease=load()
    with lease:
        with pytest.raises(ValueError,match='cap'):raw.read_stable(path,1)
        with pytest.raises(ValueError,match='regular'):raw.read_stable(tmp_path,10)
        assert lease.receipt()['exact_stable_read_calls']==0


@pytest.mark.parametrize('timing',['before_open','before_read','after_read'])
@pytest.mark.parametrize('contents',[b'',b'abcd',b'012345678'])
def test_fresh_grow_shrink_same_size_changes(tmp_path,monkeypatch,timing,contents):
    path=tmp_path/'input';path.write_bytes(b'abcd');original=Path.open
    def mutate():
        with original(path,'wb') as stream:stream.write(contents)
        os.utime(path,ns=(1_700_000_000_000_000_000,1_700_000_000_000_000_000))
    def opening(p,*a,**kw):
        if p!=path or a!=('rb',):return original(p,*a,**kw)
        if timing=='before_open':mutate()
        stream=original(p,*a,**kw)
        def read(n):
            if timing=='before_read':mutate()
            value=stream.read(n)
            if timing=='after_read':mutate()
            return value
        return Stream(stream,read)
    monkeypatch.setattr(Path,'open',opening);module,lease=load()
    with lease:
        with pytest.raises(ValueError,match='replaced|changed'):raw.read_stable(path,8)
        assert lease.receipt()['active_streams']==0


@pytest.mark.parametrize('when',['before_open','after_close'])
def test_same_bytes_path_replacement(tmp_path,monkeypatch,when):
    path=tmp_path/'input';path.write_bytes(b'abcd');original=Path.open
    def replace():
        path.rename(tmp_path/'retained_original')
        with original(path,'wb') as stream:stream.write(b'abcd')
    def opening(p,*a,**kw):
        if p!=path or a!=('rb',):return original(p,*a,**kw)
        if when=='before_open':replace()
        stream=original(p,*a,**kw)
        def exit_(*args):replace()
        return Stream(stream,exit_=exit_ if when=='after_close' else None)
    monkeypatch.setattr(Path,'open',opening);module,lease=load()
    with lease:
        with pytest.raises(ValueError,match='replaced|changed'):raw.read_stable(path,8)


@pytest.mark.parametrize('edge',['open','enter','fileno','read','exit','short_read'])
def test_underlying_errors_and_short_read(tmp_path,monkeypatch,edge):
    path=tmp_path/'input';path.write_bytes(b'abcd');original=Path.open
    marker=OSError('injected '+edge)
    def reject(*a,**kw):raise marker
    def opening(p,*a,**kw):
        if p!=path or a!=('rb',):return original(p,*a,**kw)
        if edge=='open':raise marker
        stream=original(p,*a,**kw)
        read=reject if edge=='read' else (lambda n:stream.read(n)[:-1]) if edge=='short_read' else None
        return Stream(stream,read,exit_=reject if edge=='exit' else None,
            enter=reject if edge=='enter' else None,fileno=reject if edge=='fileno' else None)
    monkeypatch.setattr(Path,'open',opening);module,lease=load()
    with lease:
        with pytest.raises(ValueError if edge=='short_read' else OSError) as captured:raw.read_stable(path,8)
        if edge!='short_read':assert captured.value is marker
        assert lease.receipt()['active_streams']==0


def test_second_fstat_change(tmp_path,monkeypatch):
    path=tmp_path/'input';path.write_bytes(b'abcd');original=os.fstat;calls=0
    def fstat(fd):
        nonlocal calls
        value=original(fd);calls+=1
        if calls==2:
            names=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
            data={k:getattr(value,k) for k in names};data['st_mtime_ns']+=1
            return SimpleNamespace(**data)
        return value
    module,lease=load()
    with lease:
        monkeypatch.setattr(os,'fstat',fstat)
        with pytest.raises(ValueError,match='changed'):raw.read_stable(path,8)


@pytest.mark.parametrize('field',['raw_function','raw_code','raw_defaults','Path_open','io_open','code_read','code_method'])
def test_dispatch_failure_sticky_and_cleanup(tmp_path,monkeypatch,field):
    path=tmp_path/'input';path.write_bytes(b'abcd');module,lease=load();original_open=Path.open
    marker=RuntimeError('body retained')
    with pytest.raises(RuntimeError) as captured:
        with lease:
            if field=='raw_function':monkeypatch.setattr(raw,'read_stable',lambda *a:None)
            elif field=='raw_code':monkeypatch.setattr(raw.read_stable,'__code__',(lambda *a,**kw:None).__code__)
            elif field=='raw_defaults':monkeypatch.setattr(raw.read_stable,'__defaults__',(1,))
            elif field=='Path_open':monkeypatch.setattr(Path,'open',lambda p,*a,**kw:original_open(p,*a,**kw))
            elif field=='io_open':monkeypatch.setattr(module.io,'open',lambda *a,**kw:None)
            elif field=='code_read':monkeypatch.setattr(Path,'read_bytes',lambda p:b'')
            else:monkeypatch.setattr(module.code.CodeReadLease,'receipt',lambda self:{})
            with pytest.raises(ValueError):lease.receipt()
            raise marker
    assert captured.value is marker and captured.value.__notes__
    # Restore test seams before checking that ordinary pathname opens work.
    monkeypatch.undo()
    Path.open=original_open
    with original_open(Path(raw.__file__),'r+b'):pass


def test_nonnested_single_use_and_foreign_thread(tmp_path):
    path=tmp_path/'input';path.write_bytes(b'abcd');module,lease=load()
    pins={p:sha256(p.read_bytes()).hexdigest() for p in (SOURCE,Path(raw.__file__).resolve(),ENTRY/'code_read_lease.py')}
    other=module.BoundedStableReadLease(pins,root=Path('D:/'))
    with pytest.raises(ValueError,match='poisoned'):
        with lease:
            with pytest.raises(ValueError,match='nonnested'):other.__enter__()
            errors=[]
            def foreign():
                try:raw.read_stable(path,8)
                except ValueError as error:errors.append(error)
            thread=threading.Thread(target=foreign);thread.start();thread.join(timeout=5)
            assert not thread.is_alive() and errors
            lease.receipt()
    with pytest.raises(ValueError,match='single-use'):lease.__enter__()


def test_nontarget_background_writes_supported(tmp_path):
    path=tmp_path/'observer';module,lease=load()
    with lease:
        errors=[]
        def observer():
            try:path.write_text('heartbeat',encoding='utf-8')
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=observer);thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and not errors and path.read_text()=='heartbeat'
        assert lease.receipt()['exact_stable_read_calls']==0
