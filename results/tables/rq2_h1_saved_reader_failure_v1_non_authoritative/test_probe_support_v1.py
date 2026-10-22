"""Only probe support: actual Windows sharing behavior and exact AST landmarks."""
from importlib.util import spec_from_file_location,module_from_spec
from pathlib import Path
import ast
from copy import deepcopy
import sys

import pytest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
spec=spec_from_file_location('saved_Reader_fault_support',HERE/'fault_worker_v1.py')
worker=module_from_spec(spec);spec.loader.exec_module(worker)


def test_windows_read_only_sharing_denial_restores_read_and_bytes(tmp_path):
    path=tmp_path/'preserved.bin';raw=b'fixed saved bytes\x00\xff'
    path.write_bytes(raw)
    before=worker.pin(path)
    denial=worker.ReadSharingDenial(path)
    denial.open()
    try:
        assert denial.conflict_error()==32
        with pytest.raises(PermissionError) as error:path.read_bytes()
        assert error.value.errno==13
    finally:denial.close()
    assert denial.handle is None and denial.close_confirmed
    assert path.read_bytes()==raw and worker.pin(path)==before
    denial.close()  # Idempotent after successful close.


@pytest.mark.parametrize('relative,cls,function,target,attribute',[
    ('experiments/h1_historical_parent_prefix_development_v1.py','HistoricalSnapshot','__init__','state','inspect'),
    ('experiments/h1_phase_historical_batch_development_v3.py',None,'replay_prefixes','state','_take_constructor_inspection'),
])
def test_landmark_is_a_single_actual_assignment(relative,cls,function,target,attribute):
    path=REPO/relative
    line=worker.assignment_line(path,cls,function,target,attribute)
    assert target in path.read_text(encoding='utf-8').splitlines()[line-1]
    assert attribute in path.read_text(encoding='utf-8').splitlines()[line-1]


def test_missing_or_ambiguous_landmark_is_refused(tmp_path):
    path=tmp_path/'program.py'
    path.write_text('def run():\n    state=self.inspect()\n    state=self.inspect()\n',encoding='utf-8')
    with pytest.raises(ValueError,match='exact one'):worker.assignment_line(path,None,'run','state','inspect')


def test_probe_does_not_install_hooks_on_import():
    assert sys.gettrace() is None and sys.getprofile() is None
    assert len(worker.CASES)==9 and len(set(worker.CASES))==9


def test_profile_observer_records_instrumentation_error_without_raising():
    observer=object.__new__(worker.FaultWindow)
    observer.instrumentation_errors=[]
    observer.profile(sys._getframe(),'call',None)
    assert len(observer.instrumentation_errors)==1
    assert observer.instrumentation_errors[0].startswith('profile AttributeError:')


def suite_acceptance():
    tree=ast.parse((HERE/'run_faults_v1.py').read_text(encoding='utf-8'))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='accepted_worker')
    namespace={}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<actual suite acceptance>','exec'),namespace)
    return namespace['accepted_worker']


@pytest.mark.parametrize('field,value',[
    ('prior_trace_and_profile_restored',False),('guard_usable_after_fault_restored',None),
    ('saved_case_sha256_equal',False),('injection_count',True),('injection_count',2),
    ('instrumentation_errors',['failure']),('cleanup_errors',['failure']),
    ('activity',{'rejected_mutations':1}),('read_only_sharing_handle_closed',False),
    ('sharing_target_identity_before_after_equal',False),
])
def test_suite_refuses_incomplete_failure_cleanup_evidence(field,value):
    expected=dict(case='final_read_sharing_error',expected_runtime_counts={'job_inspections':2},namespace_round_expected=2)
    row=dict(exit_code=0,case=expected['case'],observed_replay_call_counts=expected['expected_runtime_counts'],
        namespace_observations_reached=2,prior_trace_and_profile_restored=True,
        guard_usable_after_fault_restored=True,saved_case_sha256_equal=True,injection_reached=True,
        injection_count=1,instrumentation_errors=[],cleanup_errors=[],activity={'rejected_mutations':0},
        read_only_sharing_handle_closed=True,sharing_target_identity_before_after_equal=True)
    accept=suite_acceptance()
    assert accept(row,expected)
    bad=deepcopy(row);bad[field]=value
    assert not accept(bad,expected)
