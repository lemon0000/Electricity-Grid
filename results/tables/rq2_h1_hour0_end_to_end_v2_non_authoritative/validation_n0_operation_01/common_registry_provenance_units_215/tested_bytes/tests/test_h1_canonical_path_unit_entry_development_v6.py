"""Exercise entry6 composition and combined primary/receipt failure in children."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_unit_entry_v6.py'


@pytest.mark.parametrize('case',['normal','body_error','body_and_reader_error','extra_root',
    'relative_root','missing_root','duplicate_root','cleanup_false','cleanup_raise','cleanup_persistent'])
def test_path_entry_closes_and_retains_primary(tmp_path,case):
    target=tmp_path/'test_probe.py';base=tmp_path/'child_non_authoritative'
    extra=tmp_path/'extra_non_authoritative';extra.mkdir()
    source='''
import importlib.metadata as metadata
from pathlib import Path
import pytest
import performance.pinned_distribution_resolver_v1 as resolver
from src.rq2_joint_deliverability_boundary_v1 import episode_store as store
ORIGINAL=metadata.Distribution.from_name.__func__
@pytest.fixture
def prepared():
    # A same-name, unrelated fixture retains the original metadata resolver.
    assert metadata.Distribution.from_name.__func__ is ORIGINAL
    assert metadata.version('numpy')
    return True
def test_flow(prepared,tmp_path):
    assert prepared
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    assert metadata.version('numpy')
    path=tmp_path/'fresh.json';path.write_bytes(b'first')
    assert store._path(path).read_bytes()==b'first'
    path.write_bytes(b'second')
    assert store._path(path).read_bytes()==b'second'
    if CASE=='extra_root':
        outside=Path(OUTSIDE);outside.write_bytes(b'outside')
        assert store._path(outside).read_bytes()==b'outside'
        outside.write_bytes(b'outside changed')
        assert store._path(outside).read_bytes()==b'outside changed'
    if CASE=='body_and_reader_error':
        def refused():raise ValueError('expected receipt runtime failure')
        resolver._RUNTIME=refused
    if CASE not in ('normal','extra_root'):raise RuntimeError('expected original body primary')
'''.replace('CASE',repr(case)).replace('OUTSIDE',repr(str(extra/'fresh.json')))
    target.write_text(source,encoding='utf-8')
    entry=ENTRY.read_bytes();(tmp_path/'tested_child_entry.py').write_bytes(entry)
    arguments=[str(ENTRY),'-p','no:faulthandler','--basetemp',str(base),str(target)]
    if case=='extra_root':arguments.extend(['--canonical-path-root',str(extra)])
    elif case=='relative_root':arguments.extend(['--canonical-path-root','relative_non_authoritative'])
    elif case=='missing_root':arguments.append('--canonical-path-root')
    elif case=='duplicate_root':arguments.extend(['--canonical-path-root',str(extra),'--canonical-path-root',str(extra)])
    launcher=None
    if case.startswith('cleanup_'):
        launcher=tmp_path/'launch_with_close_fault.py'
        launcher.write_text('''
import ctypes
from ctypes import wintypes
import runpy
import sys
ORIGINAL=ctypes.WinDLL
def load(*args,**kwargs):
    library=ORIGINAL(*args,**kwargs)
    caller=sys._getframe(1)
    if caller.f_code.co_name!='_kernel_api' or not caller.f_code.co_filename.endswith('h1_canonical_path_lease_development_v1.py'):
        return library
    actual_close=library.CloseHandle
    actual_close.argtypes=(wintypes.HANDLE,);actual_close.restype=wintypes.BOOL
    calls=[0]
    def close(handle):
        calls[0]+=1
        if CASE=='cleanup_persistent' or calls[0]==1:
            if CASE=='cleanup_raise':raise OSError('expected injected path CloseHandle raise')
            return False
        return actual_close(handle)
    class Proxy:
        def __getattr__(self,name):return getattr(library,name)
    proxy=Proxy();proxy.CloseHandle=close
    return proxy
ctypes.WinDLL=load
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''.replace('CASE',repr(case)),encoding='utf-8')
    result=subprocess.run([sys.executable,'-B',*([str(launcher)] if launcher else []),*arguments],
        cwd=ROOT,capture_output=True,text=True,timeout=40,check=False)
    (tmp_path/'child_stdout.txt').write_text(result.stdout,encoding='utf-8')
    (tmp_path/'child_stderr.txt').write_text(result.stderr,encoding='utf-8')
    assert ENTRY.read_bytes()==entry
    (tmp_path/'child_entry_source_sha256.txt').write_text(sha256(entry).hexdigest(),encoding='utf-8')
    if case in ('relative_root','missing_root','duplicate_root'):
        assert result.returncode!=0 and 'ValueError' in result.stderr
        assert not (base/'unit_code_read_lease_closed.json').exists()
        return
    assert result.returncode==(0 if case in ('normal','extra_root') else 1),result.stdout+result.stderr
    value=json.loads((base/'unit_code_read_lease_closed.json').read_bytes())
    assert value['all_code_handles_closed'] and value['all_metadata_handles_closed']
    persistent=case=='cleanup_persistent'
    assert value['all_path_handles_closed'] is (not persistent)
    assert value['canonical_paths_cleared'] and value['canonical_path_alias_restored']
    assert value['canonical_path_state']==('cleanup_failed' if persistent else 'closed')
    assert value['original_read_alias_restored'] and value['original_metadata_version_alias_restored']
    assert value['canonical_path_receipt']['hits']>0
    assert value['canonical_path_receipt']['leaf_lstat_fresh']
    assert len(value['distribution_resolver_receipts'])==1
    row=value['distribution_resolver_receipts'][0]
    if case in ('normal','extra_root'):
        assert row['reader_error'] is None and row['receipt']['fast_path_calls']==1
        assert not value['diagnostic_validation_errors']
        if case=='extra_root':assert str(extra) in value['canonical_path_roots']
    else:
        assert 'RuntimeError: expected original body primary' in result.stdout
        assert value['diagnostic_validation_errors']
        if case=='body_and_reader_error':
            assert row['receipt'] is None and 'expected receipt runtime failure' in row['reader_error']
        elif not case.startswith('cleanup_'):
            assert row['reader_error'] is None and row['receipt']['first_failure']
        if case.startswith('cleanup_'):
            assert value['entry_error'] and len(value['path_cleanup_retry'])==1
            retry=value['path_cleanup_retry'][0]
            assert retry['pending_before']>0
            if persistent:assert retry['error'] and retry['pending_after']>0
            else:assert retry['error'] is None and retry['pending_after']==0
