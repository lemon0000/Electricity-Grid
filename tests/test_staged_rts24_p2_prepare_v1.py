"""Create-only metadata/failure boundaries, never a P2 native controller."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def tool(tmp_path,monkeypatch):
    source=Path(__file__).resolve().parents[1]/'experiments/staged_rts24_p2_prepare_v1.py'
    spec=importlib.util.spec_from_file_location('p2_preparation_under_test',source)
    d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
    root=tmp_path/'repo';root.mkdir();tables=root/'results/tables';tables.mkdir(parents=True)
    p1=tables/'p1';p1.mkdir();(p1/'start.json').write_text(json.dumps(dict(pins={'original':'runtime'},preserved={'old':'bytes'})))
    anchor=p1/'anchor.json';anchor.write_text('{}')
    monkeypatch.setattr(d,'ROOT',root);monkeypatch.setattr(d,'BASE',tables/'prepare');monkeypatch.setattr(d,'OUTPUT',d.BASE/'packet_01')
    monkeypatch.setattr(d,'PROPOSED_EXECUTION',tables/'native/p2_01')
    monkeypatch.setattr(d,'sys',SimpleNamespace(flags=SimpleNamespace(no_user_site=1),dont_write_bytecode=True,modules=sys.modules))
    monkeypatch.setattr(d,'runtime_snapshot',lambda:({'runtime':'stable'},{}))
    monkeypatch.setattr(d,'runtime_unchanged',lambda before,refs:before)
    monkeypatch.setattr(d.support,'P1',p1);monkeypatch.setattr(d.support,'PRIOR',anchor)
    monkeypatch.setattr(d,'check_inputs',lambda:d.require(not d.PROPOSED_EXECUTION.exists(),'P2 output exists'))
    monkeypatch.setattr(d.p1,'require_compute',lambda:None)
    monkeypatch.setattr(d.p1,'fingerprints',lambda:{'original':'runtime'})
    monkeypatch.setattr(d.p1,'preserve',lambda:{'old':'bytes'})
    monkeypatch.setattr(d,'source_pins',lambda:{'source':'fixed'})
    monkeypatch.setattr(d,'cost_basis',lambda:{'saved':'cost'})
    monkeypatch.setattr(d.prep.c,'load_fixture',lambda:None)
    monkeypatch.setattr(d.prep,'packet',lambda fixture:{'native_authorized':False,'execution_supported':False})
    monkeypatch.setattr(d.prep,'validate_packet',lambda value,fixture:None)
    return d


def test_prepare_is_create_only_and_never_creates_execution_directory(tool):
    d=tool;assert d.prepare()==0
    assert not d.PROPOSED_EXECUTION.exists()
    assert d.read(d.OUTPUT/'observation.json')['execution_supported'] is False
    before={p.name:p.read_bytes() for p in d.OUTPUT.iterdir()}
    with pytest.raises(FileExistsError):d.prepare()
    assert before=={p.name:p.read_bytes() for p in d.OUTPUT.iterdir()}


@pytest.mark.parametrize('fault',['inputs','runtime','source','packet','write'])
def test_partial_preparation_or_drift_is_not_adopted(tool,monkeypatch,fault):
    d=tool
    if fault=='inputs':
        def check():
            if d.OUTPUT.exists():raise ValueError('P1 changed')
        monkeypatch.setattr(d,'check_inputs',check)
    elif fault=='runtime':
        calls=[]
        def pins():calls.append(1);return {'original':'runtime'} if len(calls)==1 else {'changed':True}
        monkeypatch.setattr(d.p1,'fingerprints',pins)
    elif fault=='source':monkeypatch.setattr(d,'source_pins',lambda:{'source':'changed' if d.OUTPUT.exists() else 'fixed'})
    else:
        save=d.save
        def altered(path,value):
            if path.name=='packet.json':
                if fault=='write':raise OSError('storage failed')
                value={'different':'packet'}
            return save(path,value)
        monkeypatch.setattr(d,'save',altered)
    with pytest.raises((ValueError,OSError)):d.prepare()
    assert d.read(d.OUTPUT/'failure.json')['preparation_completed'] is False
    assert not (d.OUTPUT/'observation.json').exists() and not d.PROPOSED_EXECUTION.exists()


def test_existing_execution_directory_refuses_preparation(tool):
    d=tool;d.PROPOSED_EXECUTION.mkdir(parents=True)
    with pytest.raises(ValueError):d.prepare()
    assert not d.OUTPUT.exists()


def test_cli_has_no_execute_command():
    script=Path(__file__).resolve().parents[1]/'experiments/staged_rts24_p2_prepare_v1.py'
    result=subprocess.run([sys.executable,'-B','-s',str(script),'--execute'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    assert result.returncode==2 and b'--prepare' in result.stderr


def test_real_preparation_runtime_has_canonical_source_and_function_pins():
    from experiments import staged_rts24_p2_prepare_v1 as d
    before,refs=d.runtime_snapshot()
    assert d.runtime_unchanged(before,refs)==before
    assert len(before['application_modules'])==40
    assert set(before['preparation_sources'])==d.SOURCES


@pytest.mark.parametrize('fault',['module','sources','argv','cwd'])
def test_preparation_identity_or_fresh_scope_faults_are_refused(monkeypatch,fault,tmp_path):
    from experiments import staged_rts24_p2_prepare_v1 as d
    if fault=='module':
        monkeypatch.setattr(d.prep,'__file__',str(tmp_path/'elsewhere.py'))
        with pytest.raises(ValueError):d.runtime_snapshot()
    elif fault=='sources':
        monkeypatch.setattr(d,'SOURCES',frozenset(sorted(d.SOURCES)[:-1]))
        with pytest.raises(ValueError):d.runtime_snapshot()
    else:
        script=Path(d.__file__)
        if fault=='cwd':argv=[sys.executable,'-B','-s',str(script),'--prepare'];cwd=tmp_path
        else:
            code='import src,runpy; runpy.run_path('+repr(str(script))+',run_name="__main__")'
            argv=[sys.executable,'-B','-s','-c',code];cwd=d.ROOT
        result=subprocess.run(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        assert result.returncode!=0 and b'fresh repository CLI scope' in result.stderr


@pytest.mark.parametrize('fault',['extra','reparse','observation'])
def test_final_output_or_observation_drift_is_not_adopted(tool,monkeypatch,fault):
    d=tool;save=d.save
    def changed(path,value):
        result=save(path,value)
        if path.name=='observation.json':
            if fault=='extra':(d.OUTPUT/'extra.json').write_text('{}')
            elif fault=='observation':path.write_text('{}')
            else:
                original=Path.lstat;target=d.OUTPUT/'packet.json'
                def lstat(self,*a,**kw):
                    info=original(self,*a,**kw)
                    return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400,st_nlink=1) if self==target else info
                monkeypatch.setattr(Path,'lstat',lstat)
        return result
    monkeypatch.setattr(d,'save',changed)
    with pytest.raises(ValueError):d.prepare()
    assert d.read(d.OUTPUT/'failure.json')['preparation_completed'] is False


@pytest.mark.parametrize('name',['src.p2_rogue','experiments.p2_rogue','third_party_rogue'])
def test_warmup_additional_unregistered_module_is_refused(tool,monkeypatch,name):
    from types import ModuleType
    d=tool
    def pins():
        monkeypatch.setitem(sys.modules,name,ModuleType(name))
        return {'original':'runtime'}
    monkeypatch.setattr(d.p1,'fingerprints',pins)
    with pytest.raises(ValueError,match='module inventory'):d.prepare()
    assert not d.OUTPUT.exists()


@pytest.mark.parametrize('phase',['warmup','terminal'])
def test_existing_module_replacement_is_refused(tool,monkeypatch,phase):
    from types import ModuleType
    d=tool
    if phase=='warmup':
        def cost():monkeypatch.setitem(sys.modules,'json',ModuleType('json'));return {'saved':'cost'}
        monkeypatch.setattr(d,'cost_basis',cost)
    else:
        def ending(before,refs):monkeypatch.setitem(sys.modules,'json',ModuleType('json'));return before
        monkeypatch.setattr(d,'runtime_unchanged',ending)
    with pytest.raises(ValueError,match='module inventory'):d.prepare()
    assert not (d.OUTPUT/'observation.json').exists() if phase=='warmup' else (d.OUTPUT/'failure.json').exists()
