"""Reader races and complete pinned-inventory parity; zero solver/Job."""
import os
from pathlib import Path

import pytest

from experiments import h1_phase_dependency_verifier_development_v1 as m


@pytest.mark.parametrize('size,cap', [(0,0),(0,32*1024**2),(1,1),(1,32*1024**2),(4096,4096)])
def test_stable_reader_matches_predecessor(tmp_path,size,cap):
    path=tmp_path/'input';path.write_bytes(b'x'*size)
    assert m.read_stable(path,cap)==m.io.read_stable(path,cap)


def test_initial_cap_and_nonregular_reject(tmp_path):
    path=tmp_path/'input';path.write_bytes(b'xx')
    with pytest.raises(ValueError,match='cap'):m.read_stable(path,1)
    with pytest.raises(ValueError,match='regular'):m.read_stable(tmp_path,100)


class Stream:
    def __init__(self,stream,read):self.stream,self.read=stream,read
    def fileno(self):return self.stream.fileno()
    def __enter__(self):return self
    def __exit__(self,*args):return self.stream.__exit__(*args)


@pytest.mark.parametrize('timing',['before_open','before_read','after_read'])
@pytest.mark.parametrize('contents',[b'',b'abcd',b'longer than cap'])
def test_append_truncate_and_overcap_during_read(tmp_path,monkeypatch,timing,contents):
    path=tmp_path/'input';path.write_bytes(b'abc');original=Path.open
    def mutate():
        with original(path,'wb') as stream:stream.write(contents)
        os.utime(path,ns=(1_700_000_000_000_000_000,1_700_000_000_000_000_000))
    def opening(p,*a,**kw):
        if p!=path or a!=('rb',):return original(p,*a,**kw)
        if timing=='before_open':mutate()
        stream=original(p,*a,**kw)
        def read(n):
            if timing=='before_read':mutate()
            result=stream.read(n)
            if timing=='after_read':mutate()
            return result
        return Stream(stream,read)
    monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError):m.read_stable(path,8)


def test_small_file_allocation_and_short_read(tmp_path,monkeypatch):
    path=tmp_path/'input';path.write_bytes(b'abc');original=Path.open;requests=[]
    def opening(p,*a,**kw):
        stream=original(p,*a,**kw)
        if p!=path or a!=('rb',):return stream
        def read(n):requests.append(n);return stream.read(n)[:-1]
        return Stream(stream,read)
    monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='changed'):m.read_stable(path,32*1024**2)
    assert requests==[4]


def test_same_byte_replacement_before_open(tmp_path,monkeypatch):
    path=tmp_path/'input';path.write_bytes(b'abc');original=Path.open;armed=True
    def opening(p,*a,**kw):
        nonlocal armed
        if armed and p==path and a==('rb',):
            armed=False;path.rename(tmp_path/'retained_original')
            with original(path,'wb') as stream:stream.write(b'abc')
        return original(p,*a,**kw)
    monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='replaced'):m.read_stable(path,100)


@pytest.mark.parametrize('family,ordinal',[(f,0) for f in
    ('training_lb','training_ub','training_b6_actual','holdout')]+[('training_ub',11832353)])
def test_complete_projection_matches_old_entrypoint(family,ordinal):
    old=m.prior.prepare(family,ordinal)
    result=m.prepare_group(family,ordinal)
    assert result['predecessor_group']==old
    assert all(result[k] is False for k in m.FLAGS)
    assert result['fresh_at_return_only'] and result['detached_data']
    assert result['observed_file_count']==len(result['dependency_sha256'])
    assert result['observed_total_bytes']<=m.TOTAL_CAP
    assert sum(Path(p).is_absolute() for p in result['dependency_sha256'])==2


@pytest.mark.parametrize('changed',['bytes','short_read'])
def test_complete_exit_reread_detects_change(monkeypatch,changed):
    target=m.prior.ROOT/m.prior.PROTOCOL
    original=Path.open;count=0
    def opening(p,*a,**kw):
        nonlocal count
        stream=original(p,*a,**kw)
        if p!=target or a!=('rb',):return stream
        count+=1
        if count<3:return stream
        def read(n):
            raw=stream.read(n)
            return (b'X'+raw[1:]) if changed=='bytes' else raw[:-1]
        return Stream(stream,read)
    monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='changed'):m.prepare_group('training_ub',0)


def test_same_byte_replacement_after_close(tmp_path,monkeypatch):
    path=tmp_path/'input';path.write_bytes(b'abc');original=Path.open
    class Replace(Stream):
        def __exit__(self,*args):
            result=super().__exit__(*args)
            path.rename(tmp_path/'retained_original')
            with original(path,'wb') as stream:stream.write(b'abc')
            return result
    def opening(p,*a,**kw):
        stream=original(p,*a,**kw)
        return Replace(stream,stream.read) if p==path and a==('rb',) else stream
    monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='changed'):m.read_stable(path,100)


@pytest.mark.parametrize('name',['read_stable','_views','_scope','project','identity','digest','encode'])
@pytest.mark.parametrize('timing',['entry','during'])
def test_helper_substitution_rejected(monkeypatch,name,timing):
    owner=m.prior if name=='project' else m.io if name in ('identity','digest','encode') else m
    attribute='_project' if name=='project' else name
    calls=[]
    def replacement(*a,**kw):calls.append(1);raise AssertionError('replacement dispatched')
    if timing=='entry':monkeypatch.setattr(owner,attribute,replacement)
    else:
        original=Path.open;armed=True
        def opening(p,*a,**kw):
            nonlocal armed
            if armed:
                armed=False;monkeypatch.setattr(owner,attribute,replacement)
            return original(p,*a,**kw)
        monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='helper identity'):m.prepare_group('training_ub',0)
    assert not calls


def test_extra_false_flag_rejected(monkeypatch):
    monkeypatch.setitem(m.FLAGS,'extra',False)
    with pytest.raises(ValueError,match='scope'):m.prepare_group('training_ub',0)


def test_exit_metadata_change_rejected(monkeypatch):
    from types import SimpleNamespace
    target=m.prior.ROOT/m.prior.PROTOCOL
    original=Path.stat;count=0
    def stat(p,*a,**kw):
        nonlocal count
        value=original(p,*a,**kw)
        if p==target:
            count+=1
            if count==5:
                fields={k:getattr(value,k) for k in dir(value) if k.startswith('st_')}
                fields['st_mtime_ns']+=1
                return SimpleNamespace(**fields)
        return value
    monkeypatch.setattr(Path,'stat',stat)
    with pytest.raises(ValueError):m.prepare_group('training_ub',0)


def test_inventory_and_total_exact_bounds(monkeypatch):
    import json
    symbolic=m.prior.symbolic
    baseline=json.loads((m.prior.ROOT/symbolic.BASELINE).read_bytes())
    count=6+len(baseline['files_sha256'])
    views=m._views();total=sum(len(v[0]) for v in views.values())
    monkeypatch.setattr(m,'MAX_FILES',count)
    monkeypatch.setattr(m,'TOTAL_CAP',total)
    assert m._views()==views
    monkeypatch.setattr(m,'MAX_FILES',count-1)
    with pytest.raises(ValueError,match='inventory'):m._views()
    monkeypatch.setattr(m,'MAX_FILES',count)
    monkeypatch.setattr(m,'TOTAL_CAP',total-1)
    with pytest.raises(ValueError,match='total'):m._views()


@pytest.mark.parametrize('field',['SCHEMA','PROTOCOL_PIN','ROOT','__file__','proof_pin','baseline','cap','resolver','flags'])
@pytest.mark.parametrize('timing',['entry','exit'])
def test_nested_predecessor_substitution_rejected(monkeypatch,field,timing):
    symbolic=m.prior.symbolic;proof=symbolic.proof
    owner,attribute,value={
        'SCHEMA':(m.prior,'SCHEMA','changed'),
        'PROTOCOL_PIN':(m.prior,'PROTOCOL_PIN','0'*64),
        'ROOT':(m.prior,'ROOT',Path('changed')),
        '__file__':(symbolic,'__file__','changed'),
        'proof_pin':(symbolic,'PROOF_PIN','0'*64),
        'baseline':(symbolic,'BASELINE','changed'),
        'cap':(proof,'CAP',1),
        'resolver':(proof,'_resolver',lambda *a:None),
        'flags':(m.prior,'FLAGS',dict(m.prior.FLAGS,extra=False)),
    }[field]
    if timing=='entry':monkeypatch.setattr(owner,attribute,value)
    else:
        original=Path.open;target=m.prior.ROOT/m.prior.PROTOCOL;count=0
        def opening(p,*a,**kw):
            nonlocal count
            if p==target and a==('rb',):
                count+=1
                if count==3:monkeypatch.setattr(owner,attribute,value)
            return original(p,*a,**kw)
        monkeypatch.setattr(Path,'open',opening)
    with pytest.raises(ValueError,match='scope changed|helper identity'):
        m.prepare_group('training_ub',0)


def test_separate_implementation_identity():
    result=m.prepare_group('training_ub',0)
    implementation=result['verifier_implementation']
    assert result['verifier_implementation_sha256']==m.io.digest(m.io.encode(implementation))
    assert implementation['schema']==m.SCHEMA
    assert implementation['verifier_sha256']==m.io.digest(Path(m.__file__).read_bytes())
    modules=(m.prior,m.prior.symbolic,m.prior.symbolic.proof,m.io)
    assert implementation['predecessor_files_sha256']=={
        Path(x.__file__).as_posix():m.io.digest(Path(x.__file__).read_bytes()) for x in modules}


@pytest.mark.parametrize('field',['class','family','encode','resolve','node','io','schema','catalog','missing','json','loads'])
@pytest.mark.parametrize('timing',['entry','exit'])
def test_resolver_reachable_layer_replacement(monkeypatch,field,timing):
    proof=m.prior.symbolic.proof
    owner,attribute,value={
        'class':(proof,'Resolver',object),
        'family':(proof.Resolver,'_family',lambda *a:None),
        'encode':(proof.Resolver,'encode_coordinate',lambda *a:0),
        'resolve':(proof.Resolver,'resolve',lambda *a:{}),
        'node':(proof,'_node',lambda *a:{}),
        'io':(proof,'io',object()),
        'schema':(proof,'SCHEMA','changed'),
        'catalog':(proof,'CATALOG_PIN','0'*64),
        'missing':(proof,'MISSING',dict(proof.MISSING,training_ub='changed')),
        'json':(proof,'json',object()),
        'loads':(proof.json,'loads',lambda *a,**kw:{}),
    }[field]
    with monkeypatch.context() as patch:
        if timing=='entry':patch.setattr(owner,attribute,value)
        else:
            original=Path.open;target=m.prior.ROOT/m.prior.PROTOCOL;count=0
            def opening(p,*a,**kw):
                nonlocal count
                if p==target and a==('rb',):
                    count+=1
                    if count==3:patch.setattr(owner,attribute,value)
                return original(p,*a,**kw)
            patch.setattr(Path,'open',opening)
        with pytest.raises(ValueError,match='scope changed|helper identity'):
            m.prepare_group('training_ub',0)
