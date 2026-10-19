"""Outer CLI with tiny fake inputs and one explicit short-root literal seam.

This exercises real subprocess/descendant cleanup and final storage accounting.
Fake entries do no model, native, fixture, source replay or experiment work.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace,ModuleType

import psutil
import pytest

REPO=Path(__file__).resolve().parents[1]
PATH=REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_path_optimization_01/run_bounded_configured_entry_v4.py'
EXPECTED_SHA='f35732e7e1fade7e3053fc6be02b6b69a6984f6209b5bfd4ea36fce33bf4b65e'
TARGET='tests/test_h1_guarded_common_slice_development_v1.py'


def source():
    raw=PATH.read_bytes();assert sha256(raw).hexdigest()==EXPECTED_SHA
    return raw


def helpers():
    parsed=ast.parse(source(),filename=str(PATH))
    nodes=[node for node in parsed.body if isinstance(node,ast.FunctionDef)]
    ns=dict(psutil=psutil,time=time,os=__import__('os'),Path=Path,json=json,
        subprocess=subprocess,owned={},events=[],errors=[],result={},proc=None)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(PATH),'exec'),ns)
    return ns


def fixture_entry(tmp_path,body):
    repo=tmp_path/'repo';here=repo/'results/tables/evidence/path';here.mkdir(parents=True)
    monitor=here/PATH.name;raw=source()
    anchor=b"SLICE_BASE=Path('D:/h1_cs01_non_authoritative')"
    assert raw.count(anchor)==1
    # Unit-only pre-definition literal replacement; the public CLI accepts no
    # root override. All control-flow/helper definitions are the original AST.
    raw=raw.replace(anchor,('SLICE_BASE=Path('+repr(str(tmp_path/'short_non_authoritative'))+')').encode())
    monitor.write_bytes(raw)
    entry=here/'entry_revision_05';entry.mkdir()
    launcher=entry/'launch_validation.py'
    launcher.write_text('import sys\nfrom pathlib import Path\n'
        'root=Path(__file__).parent/sys.argv[3]\nroot.mkdir()\n'+body,encoding='utf-8')
    for name in ('code_allowlist_v3.json','test_closure_v1.json'):
        (entry/name).write_text('{"files_sha256":{}}',encoding='utf-8')
    for name in ('experiments/h1_canonical_path_lease_development_v1.py',
            'tests/test_h1_canonical_path_lease_development_v1.py'):
        path=repo/name;path.parent.mkdir(exist_ok=True);path.write_text('# explicit monitor unit input\n',encoding='utf-8')
    return here,entry,monitor,launcher


def run(here,monitor,launcher,*,kind='pytest',mode='parse_path',child='common_slice_01',targets=None,seconds=5):
    if targets is None:targets=[TARGET]
    command=[sys.executable,'-B',str(monitor),'owned_unit_outer',str(seconds),'512','1','--',
        '-I',str(launcher),kind,mode,child,*targets]
    return subprocess.run(command,cwd=here,capture_output=True,text=True,timeout=20)


def test_full_outer_final_rescan_rejects_fast_successful_child_storage_overflow(tmp_path):
    here,entry,monitor,launcher=fixture_entry(tmp_path,"(root/'fast.bin').write_bytes(b'x'*(1024**2))\n")
    done=run(here,monitor,launcher)
    assert done.returncode==1,done.stdout+done.stderr
    terminal=json.loads((here/'owned_unit_outer/terminal.json').read_bytes())
    assert terminal['stop_reason']=='storage' and terminal['exit_code']!=0
    assert terminal['final_storage_observation_complete'] and not terminal['storage_read_errors']
    total=sum(path.stat().st_size for root in (here/'owned_unit_outer',entry/'common_slice_01')
        for path in root.rglob('*') if path.is_file())
    assert terminal['observed_storage_bytes']==total and total>1024**2


def test_full_outer_wall_stop_waits_observed_child_and_grandchild(tmp_path):
    body=('import subprocess,time,json\n'
        'child=subprocess.Popen([sys.executable,"-B","-c","import time; time.sleep(30)"])\n'
        '(root/"grandchild.json").write_text(json.dumps(child.pid))\ntime.sleep(30)\n')
    here,entry,monitor,launcher=fixture_entry(tmp_path,body)
    done=run(here,monitor,launcher,kind='unit',mode='parse',child='unit_checks_03',targets=[],seconds=1)
    assert done.returncode==1,done.stdout+done.stderr
    terminal=json.loads((here/'owned_unit_outer/terminal.json').read_bytes())
    assert terminal['stop_reason']=='wall' and terminal['observed_owned_processes_absent']
    assert len(terminal['observed_owned_processes'])>=2 and not terminal['cleanup_errors']
    ns=helpers()
    assert all(ns['live'](row['pid'],row['creation_time']) is None
        for row in terminal['observed_owned_processes'])


@pytest.mark.parametrize('kind,mode,child,targets',[
    ('pytest','parse_path','common_slice_01',['tests/test_h1_hour0_end_to_end_development_v2.py']),
    ('pytest','parse_path','common_slice_01',[TARGET,TARGET]),
    ('pytest','parse','common_slice_01',[TARGET]),
    ('unit','parse','unit_checks_03',[TARGET]),
    ('arm','parse','common_slice_01',[])])
def test_invalid_role_or_target_is_rejected_before_output_creation(tmp_path,kind,mode,child,targets):
    here,entry,monitor,launcher=fixture_entry(tmp_path,'raise AssertionError("must not launch")\n')
    done=run(here,monitor,launcher,kind=kind,mode=mode,child=child,targets=targets)
    assert done.returncode!=0 and not (here/'owned_unit_outer').exists()
    assert not (entry/child).exists()


def test_creation_identity_fence_never_kills_foreign_current_process():
    ns=helpers();current=psutil.Process()
    ns['owned'][current.pid]=current.create_time()-1
    ns['finish_children']()
    assert current.is_running() and not ns['events'] and ns['result']['observed_owned_processes_absent']


def test_descendant_discovery_error_records_failure_and_still_kills_known_owner():
    ns=helpers();calls=[]
    class Process:
        pid=43210;running=True
        def create_time(self):return 123.
        def is_running(self):return self.running
        def children(self,recursive):raise psutil.AccessDenied(self.pid)
        def kill(self):self.running=False;calls.append('kill')
    owner=Process()
    ns['psutil']=SimpleNamespace(Process=lambda pid:owner,Error=psutil.Error,
        NoSuchProcess=psutil.NoSuchProcess,wait_procs=lambda *a,**k:calls.append('wait'))
    ns['owned'][owner.pid]=123.
    ns['finish_children']()
    assert calls==['kill','wait'] and ns['result']['observed_owned_processes_absent']
    assert ns['errors'] and ns['errors'][0]['stage']=='discover'
    assert not ns['result']['descendant_discovery_complete']
    assert not ns['result']['complete_process_tree_absence_proven']


def test_final_storage_reports_scan_errors_and_terminal_itself_counts(tmp_path):
    ns=helpers();ns['storage_roots']=[tmp_path]
    first=ns['storage_observation']();assert first==(0,[])
    (tmp_path/'late.bin').write_bytes(b'x'*100)
    total,errors=ns['storage_observation']();assert total==100 and not errors
    final=ns['include_terminal_storage'](dict(exit_code=0,stop_reason=None),total,120)
    assert final['exit_code']==1 and final['stop_reason']=='storage'
    assert final['observed_storage_bytes']==total+len(json.dumps(final,indent=2).encode())
    def denied(*args,**kwargs):
        kwargs['onerror'](PermissionError(13,'denied',str(tmp_path/'hidden')))
        return iter(())
    ns['os']=SimpleNamespace(walk=denied)
    assert ns['storage_observation']()[1]


@pytest.mark.parametrize('name',['experiments.h1_selector_phase_handoff_development_v2',
    'tests.h1_hour0_synthetic_harness_v2','tests.h1_group_selector_integration_helpers_v2',
    'tests.test_h1_timed_selector_sequence_development_v1'])
def test_initial_import_guard_rejects_preloaded_selector_modules_before_setup(monkeypatch,name):
    from tests.h1_guarded_common_slice_helpers_development_v1 import assert_initial_imports
    monkeypatch.setitem(sys.modules,name,ModuleType(name))
    with pytest.raises(ValueError,match='must not precede'):assert_initial_imports()
