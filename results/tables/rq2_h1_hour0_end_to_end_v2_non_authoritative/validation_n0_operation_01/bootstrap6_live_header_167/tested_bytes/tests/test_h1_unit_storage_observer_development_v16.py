"""Monitor extraction: actual cycle/broken junctions and ordinary byte accounting."""
import ast
import os
from pathlib import Path
import stat
import subprocess

import pytest


ROOT=Path(__file__).resolve().parents[1]
MONITOR=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_unit_bounded_v16.py'


def observer(roots):
    tree=ast.parse(MONITOR.read_bytes())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='storage_observation')
    space=dict(os=os,Path=Path,stat=stat,storage_roots=roots,base=roots[-1])
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(MONITOR),'exec'),space)
    return space['storage_observation']


def test_no_follow_observer_counts_actual_owned_files_but_never_traverses_any_junction(tmp_path,monkeypatch):
    root=tmp_path/'observed_non_authoritative';root.mkdir()
    child=root/'nested';child.mkdir();(root/'a.bin').write_bytes(b'a'*10);(child/'b.bin').write_bytes(b'b'*7)
    external=tmp_path/'external_non_authoritative';external.mkdir();(external/'not_owned.bin').write_bytes(b'x'*33)
    links=[]
    for name,target in (('cycle',root),('broken',tmp_path/'missing'),('external',external)):
        link=root/name
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(target)],capture_output=True,timeout=5)
        assert result.returncode==0,result.stderr.decode(errors='replace')
        assert link.lstat().st_file_attributes&0x400;links.append(link)
    expected=17+sum(link.lstat().st_size for link in links)
    original=os.scandir;visited=[]
    def scan(path):visited.append(Path(path));return original(path)
    monkeypatch.setattr(os,'scandir',scan)
    total,errors=observer([root])()
    assert total==expected and not errors
    assert set(visited)=={root,child} and len(visited)==2


def test_storage_observer_preserves_real_permission_failure(tmp_path,monkeypatch):
    root=tmp_path/'observed_non_authoritative';root.mkdir()
    def denied(path):raise PermissionError('unit directory unavailable')
    monkeypatch.setattr(os,'scandir',denied)
    total,errors=observer([root])()
    assert total==0 and len(errors)==1 and errors[0]['path']==str(root)
    assert 'PermissionError' in errors[0]['error']


@pytest.mark.parametrize('kind',['cycle','broken','external'])
def test_reparse_storage_root_is_refused_without_following_any_target(tmp_path,monkeypatch,kind):
    root=tmp_path/'root_alias_non_authoritative'
    target=tmp_path if kind=='cycle' else tmp_path/'missing' if kind=='broken' else tmp_path/'external'
    if kind=='external':target.mkdir();(target/'outside.bin').write_bytes(b'not owned')
    result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(root),str(target)],capture_output=True,timeout=5)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    visited=[]
    def scan(path):visited.append(path);raise AssertionError('reparse root must not be traversed')
    monkeypatch.setattr(os,'scandir',scan)
    total,errors=observer([root])(final=True)
    assert total==0 and len(errors)==1 and errors[0]['path']==str(root)
    assert 'non-reparse storage root' in errors[0]['error'] and not visited


def test_only_initial_basetemp_may_be_missing_both_roots_required_at_final(tmp_path):
    out=tmp_path/'out_non_authoritative';out.mkdir();base=tmp_path/'not_created_non_authoritative'
    observe=observer([out,base])
    assert observe()==(0,[])
    total,errors=observe(final=True)
    assert total==0 and len(errors)==1 and errors[0]['path']==str(base)
    missing_out=tmp_path/'missing_out_non_authoritative'
    _,errors=observer([missing_out,out])()
    assert len(errors)==1 and errors[0]['path']==str(missing_out)


def test_queued_directory_replaced_with_junction_is_refused_before_scandir(tmp_path,monkeypatch):
    root=tmp_path/'owned_non_authoritative';root.mkdir();child=root/'queued';child.mkdir()
    external=tmp_path/'external';external.mkdir();(external/'outside.bin').write_bytes(b'not owned')
    original=os.scandir;visited=[]
    class Entry:
        def __init__(self,item):self.item=item;self.path=item.path
        def stat(self,*,follow_symlinks):
            info=self.item.stat(follow_symlinks=follow_symlinks)
            child.rmdir()
            result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(child),str(external)],capture_output=True,timeout=5)
            assert result.returncode==0,result.stderr.decode(errors='replace')
            return info
    class Scan:
        def __enter__(self):self.stream=original(root);return (Entry(item) for item in self.stream)
        def __exit__(self,*args):self.stream.close()
    def scan(path):
        visited.append(Path(path));assert Path(path)==root
        return Scan()
    monkeypatch.setattr(os,'scandir',scan)
    total,errors=observer([root])(final=True)
    assert total==0 and visited==[root]
    assert len(errors)==1 and errors[0]['path']==str(child) and 'non-reparse storage directory' in errors[0]['error']
