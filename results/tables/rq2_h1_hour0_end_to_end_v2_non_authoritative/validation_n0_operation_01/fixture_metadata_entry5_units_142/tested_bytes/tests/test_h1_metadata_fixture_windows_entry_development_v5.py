"""Verify real entry cleanup and native fallback around temporary fixtures."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_unit_entry_v5.py'


@pytest.mark.parametrize('case',['normal','fixture_error','discovery_drift'])
def test_fixture_window_has_its_own_original_resolver_and_cleanup(tmp_path,case):
    target=tmp_path/'test_probe.py';base=tmp_path/'child_non_authoritative'
    source='''
import importlib.metadata as metadata
import sys
import pytest
ORIGINAL=metadata.Distribution.from_name.__func__
@pytest.fixture
def prepared(tmp_path):
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    if CASE=='discovery_drift':sys.path.insert(0,str(tmp_path))
    assert metadata.version('numpy')
    with pytest.raises(metadata.PackageNotFoundError):metadata.version('electricity_grid_no_such_distribution_139')
    if CASE=='fixture_error':raise RuntimeError('expected fixture setup error')
    return metadata.Distribution.from_name.__func__
def test_flow(prepared):
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    assert metadata.Distribution.from_name.__func__ is not prepared
    assert metadata.version('numpy')
'''.replace('CASE',repr(case))
    target.write_text(source,encoding='utf-8')
    result=subprocess.run([sys.executable,'-B',str(ENTRY),'-p','no:faulthandler','--basetemp',str(base),str(target)],
        cwd=ROOT,capture_output=True,text=True,timeout=40,check=False)
    (tmp_path/'child_stdout.txt').write_text(result.stdout,encoding='utf-8')
    (tmp_path/'child_stderr.txt').write_text(result.stderr,encoding='utf-8')
    assert result.returncode==(1 if case=='fixture_error' else 0),result.stdout+result.stderr
    receipt=json.loads((base/'unit_code_read_lease_closed.json').read_bytes())
    assert receipt['all_code_handles_closed'] and receipt['all_metadata_handles_closed']
    assert receipt['original_read_alias_restored'] and receipt['original_metadata_version_alias_restored']
    rows=receipt['distribution_resolver_receipts'];fixture=[r for r in rows if r.get('scope')=='fixture']
    body=[r for r in rows if r.get('scope')=='body']
    assert len(fixture)==1 and fixture[0]['fixture']=='prepared'
    value=fixture[0]['receipt']
    assert value['original_alias_restored'] and value['all_resolver_cached_paths_cleared']
    assert value['original_discovery_oracles']=={'entry':1,'exit':1}
    assert value['fallback_calls']>0  # Unknown package always keeps native behavior.
    if case=='discovery_drift':assert value['fast_path_calls']==0
    else:assert value['fast_path_calls']==1
    if case=='fixture_error':
        assert not body and value['first_failure'] is not None
    else:
        assert len(body)==1 and body[0]['receipt']['fast_path_calls']==1
        assert value['first_failure'] is None
