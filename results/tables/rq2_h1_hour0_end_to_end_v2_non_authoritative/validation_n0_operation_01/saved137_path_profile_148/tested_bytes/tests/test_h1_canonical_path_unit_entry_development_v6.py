"""Exercise entry6 composition and combined primary/receipt failure in children."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_unit_entry_v6.py'


@pytest.mark.parametrize('case',['normal','body_error','body_and_reader_error'])
def test_path_entry_closes_and_retains_primary(tmp_path,case):
    target=tmp_path/'test_probe.py';base=tmp_path/'child_non_authoritative'
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
    if CASE=='body_and_reader_error':
        def refused():raise ValueError('expected receipt runtime failure')
        resolver._RUNTIME=refused
    if CASE!='normal':raise RuntimeError('expected original body primary')
'''.replace('CASE',repr(case))
    target.write_text(source,encoding='utf-8')
    entry=ENTRY.read_bytes();(tmp_path/'tested_child_entry.py').write_bytes(entry)
    result=subprocess.run([sys.executable,'-B',str(ENTRY),'-p','no:faulthandler',
        '--basetemp',str(base),str(target)],cwd=ROOT,capture_output=True,text=True,timeout=40,check=False)
    (tmp_path/'child_stdout.txt').write_text(result.stdout,encoding='utf-8')
    (tmp_path/'child_stderr.txt').write_text(result.stderr,encoding='utf-8')
    assert ENTRY.read_bytes()==entry
    (tmp_path/'child_entry_source_sha256.txt').write_text(sha256(entry).hexdigest(),encoding='utf-8')
    assert result.returncode==(0 if case=='normal' else 1),result.stdout+result.stderr
    value=json.loads((base/'unit_code_read_lease_closed.json').read_bytes())
    assert value['all_code_handles_closed'] and value['all_metadata_handles_closed']
    assert value['all_path_handles_closed'] and value['canonical_paths_cleared']
    assert value['canonical_path_alias_restored'] and value['canonical_path_state']=='closed'
    assert value['original_read_alias_restored'] and value['original_metadata_version_alias_restored']
    assert value['canonical_path_receipt']['hits']>0
    assert value['canonical_path_receipt']['leaf_lstat_fresh']
    assert len(value['distribution_resolver_receipts'])==1
    row=value['distribution_resolver_receipts'][0]
    if case=='normal':
        assert row['reader_error'] is None and row['receipt']['fast_path_calls']==1
        assert not value['diagnostic_validation_errors']
    else:
        assert 'RuntimeError: expected original body primary' in result.stdout
        assert value['diagnostic_validation_errors']
        if case=='body_and_reader_error':
            assert row['receipt'] is None and 'expected receipt runtime failure' in row['reader_error']
        else:
            assert row['reader_error'] is None and row['receipt']['first_failure']
