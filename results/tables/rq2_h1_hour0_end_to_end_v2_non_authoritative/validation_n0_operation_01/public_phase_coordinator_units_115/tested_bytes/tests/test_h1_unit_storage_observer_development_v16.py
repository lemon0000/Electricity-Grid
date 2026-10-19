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
    space=dict(os=os,Path=Path,stat=stat,storage_roots=roots)
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
