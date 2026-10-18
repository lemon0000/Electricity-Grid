"""Bounded, historical-only diagnostic; saved bytes are read, never produced."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
E=HERE.parent
PACKAGE=E/'validation_path_optimization_01/entry_revision_03'
SAVED=Path('D:/h1_chain_06_non_authoritative')
mode,supplied,diagnostic_pin=sys.argv[1:]
if mode not in ('full_only','operation'):raise ValueError('two declared diagnostic modes only')
out=Path(supplied)
if (not out.is_absolute() or str(out)!=str(out.resolve(strict=False)) or not out.is_relative_to(HERE)
        or out.name!='attempt_non_authoritative' or out.parent.parent!=HERE
        or not out.parent.name.startswith(mode+'_') or not out.parent.is_dir()):
    raise ValueError('owned monitor output child required')
out.mkdir(exist_ok=False)
sys.pycache_prefix=str(out/'empty_pycache');Path(sys.pycache_prefix).mkdir()
if not sys.dont_write_bytecode or not sys.flags.isolated or sys.getprofile() is not None:
    raise ValueError('fixed isolated -B entry without a profiler required')


def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def pin(paths):return {str(p):sha256(p.read_bytes()).hexdigest() for p in paths}


def load(name,path,expected):
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected:raise ValueError('source pin differs: '+str(path))
    module=ModuleType(name);module.__file__=str(path);module.__package__=name.rpartition('.')[0]
    sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),vars(module))
    return module


start=perf_counter();source_pins={};saved_pins={};measurements=[];patch=None;policy=None
result=dict(mode=mode,formal_result=False,full_chain_passed=False,resource_admission=False,
    formal_execution_ready=False,native_execution_authorized=False,real_native_calls=0,
    production_handoff_integrated=False,validation_scope='one saved arm; two historical prepares only')
try:
    candidate_name='experiments.h1_operation_historical_witness_development_v1'
    if candidate_name in sys.modules:raise ValueError('diagnostic candidate already loaded before fixture')
    diagnostic_path=HERE/'diagnostic_source_manifest_v1.json'
    diagnostic_raw=diagnostic_path.read_bytes()
    if sha256(diagnostic_raw).hexdigest()!=diagnostic_pin:raise ValueError('fixed diagnostic manifest differs')
    diagnostic=json.loads(diagnostic_raw)['files_sha256']
    for name,h in diagnostic.items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha256((REPO/name).read_bytes()).hexdigest()!=h:
            raise ValueError('fixed diagnostic member differs: '+name)
    manifest=(PACKAGE/'package_manifest_v1.json').read_bytes()
    manifest_pin=sha256(manifest).hexdigest()
    if manifest_pin!='e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139':
        raise ValueError('fixed configured package differs')
    members=json.loads(manifest)['files_sha256']
    if pin(PACKAGE/name for name in members)!={str(PACKAGE/name):h for name,h in members.items()}:
        raise ValueError('fixed configured package member differs')
    expected={Path(p):h for p,h in json.loads((PACKAGE/'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
    tests={REPO/p:h for p,h in json.loads((PACKAGE/'test_closure_v1.json').read_bytes())['files_sha256'].items()}
    expected.update({REPO/p:h for p,h in diagnostic.items() if p.endswith('.py')})
    source_pins={str(p):h for p,h in {**expected,**tests}.items()}
    source_pins.update({str(REPO/p):h for p,h in diagnostic.items()})
    source_pins[str(diagnostic_path)]=diagnostic_pin
    source_pins.update({str(PACKAGE/name):h for name,h in members.items()})
    source_pins[str(PACKAGE/'package_manifest_v1.json')]=manifest_pin
    if pin(map(Path,source_pins))!=source_pins:raise ValueError('source/test pins differ before import')
    saved_pins=pin(p for p in SAVED.rglob('*') if p.is_file())
    headers=list(SAVED.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json'))
    if len(headers)!=1:raise ValueError('one externally saved common owner expected')
    report=json.loads(headers[0].read_bytes())['declaration']['initial_report']
    arm=report['canonical_arm']
    if arm!='network-only':raise ValueError('fixed representative arm differs')
    body=report['arm_audits'][arm]['reference']['local_terminal']['body']
    root=Path(body['controller_root'])
    if str(root)!=str(root.resolve(strict=True)) or not root.is_relative_to(SAVED):
        raise ValueError('saved arm controller root differs')
    args=dict(expected_binding_sha256=body['controller_binding_sha256'],
        expected_terminal_sha256=body['controller_terminal_sha256'],completed_hours=1)
    if args['expected_binding_sha256']!='782bef7d5268e46b7d5b767f310433e956868e515eccf1d718dfdd4bf3a1af03' or args['expected_terminal_sha256']!='81855c029bb9c334a0be07ebbbcb8d7e3f85b3f2f34c654c4ed5c13e1b46a6d9':
        raise ValueError('externally fixed representative pins differ')
    save('request.json',dict(mode=mode,source_sha256=source_pins,saved_sha256=saved_pins,
        declared_arm_label=arm,controller_root=str(root),historical_arguments=args,
        oracle_prepares=1,diagnostic_prepares=2,original_context_evaluations_per_prepare=16,
        package_manifest_sha256=manifest_pin,static_identity_shortcut=False,
        distribution_discovery_cached=False,selected_locked_metadata_version_value_cached=True,
        metadata_parse_window='reset before oracle and each diagnostic prepare',
        candidate_loaded_before_fixture=False,formal_result=False,resource_admission=False))
    performance=ModuleType('performance');performance.__path__=[str(PACKAGE)]
    sys.modules['performance']=performance
    code=load('performance.code_read_lease',PACKAGE/'code_read_lease.py',members['code_read_lease.py'])
    parsed=load('performance.metadata_parse_lease',PACKAGE/'metadata_parse_lease.py',members['metadata_parse_lease.py'])
    interpreter=load('performance.interpreter_path_policy',PACKAGE/'interpreter_path_policy.py',members['interpreter_path_policy.py'])
    policy=interpreter.InterpreterPathPolicy(json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    with ExitStack() as stack:
        code_lease=stack.enter_context(code.CodeReadLease(expected,root=REPO))
        metadata=json.loads((PACKAGE/'metadata_allowlist_v1.json').read_bytes())['files_sha256']
        parse_lease=stack.enter_context(parsed.MetadataParseLease(metadata))
        fixture_path=E/'replay_saved_with_fixture_v1.py'
        fixture=load('operation_saved_fixture',fixture_path,source_pins[str(fixture_path)])
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(SAVED/'test_complete_independent_N0_r0')
        # Repository fixture imports may prepend exact repo/test duplicates.
        # The fixed policy still rejects unknown entries and any remaining order drift.
        sys.path.insert(0,str(REPO));policy.admit('after_explicit_saved_fixture')
        parse_lease.begin_discovery_window()
        from experiments import h1_historical_n0_verifier_development_v1 as oracle
        begin=perf_counter()
        with oracle.witness.hour.prior.guard.solver_calls_forbidden():
            reference=oracle.prepare(root,**args)
        if (type(reference) is not oracle.VerifiedHistoricalEnvelope
                or (reference.full_numerical_hour_replays,reference.fresh_byte_context_revalidations)!=(4,4)
                or reference.recomputed_on_revalidation is not False):
            raise ValueError('original oracle execution contract differs')
        authority=('formal_result','resource_admission','formal_execution_ready','native_execution_authorized')
        if any(json.loads(reference.audit_payload)[key] is not False for key in authority):
            raise ValueError('oracle scientific authority flags differ')
        result['oracle_seconds']=perf_counter()-begin
        save('oracle_scientific.json',dict(decision_sha256=sha256(reference.decision.decision_bytes).hexdigest(),
            audit_sha256=sha256(reference.audit_payload).hexdigest()))
        (out/'oracle_audit.json').write_bytes(reference.audit_payload)
        # All authorized fixture seams and byte/parse leases precede the immutable
        # diagnostic module's definition-time dispatch/source baseline.
        if candidate_name in sys.modules:raise ValueError('diagnostic candidate loaded before explicit definition baseline')
        from experiments import h1_operation_historical_witness_development_v1 as candidate
        result['candidate_source_sha256']=source_pins[str(Path(candidate.__file__))]
        result['candidate_first_loaded_after_fixture_leases_and_oracle']=True
        if candidate._CONTEXT is not candidate.prior_witness._HourScope._context or Path(candidate._CONTEXT.__code__.co_filename).resolve()!=Path(candidate.prior_witness.__file__).resolve():
            raise ValueError('original context was replaced')
        if Path(candidate.hour.inspect.__code__.co_filename).resolve()!=Path(candidate.hour.__file__).resolve():
            raise ValueError('original numerical inspector was replaced')
        policy.admit('before_diagnostic_operation')
        owner=candidate.OperationHistoricalWitness(root,arm_id=arm,**args,reuse_numerical_proof=mode=='operation')
        with owner:
            for ordinal in range(1,3):
                policy.admit('before_prepare_'+str(ordinal));parse_lease.begin_discovery_window();begin=perf_counter()
                with candidate.hour.prior.guard.solver_calls_forbidden():envelope=owner.prepare()
                elapsed=perf_counter()-begin
                if envelope.decision.decision_bytes!=reference.decision.decision_bytes or envelope.audit_payload!=reference.audit_payload:
                    raise ValueError('diagnostic scientific bytes differ from original verifier')
                execution=json.loads(envelope.execution_receipt)
                if execution['context_evaluations']!=16:raise ValueError('original context observations missing')
                expected_counts=(0,8) if mode=='operation' and ordinal==2 else (4,4)
                if (envelope.full_numerical_hour_replays,envelope.fresh_byte_context_revalidations)!=expected_counts:
                    raise ValueError('actual numerical execution counts differ from declared mode')
                expected_role='produced' if ordinal==1 else ('consumed' if mode=='operation' else 'reconfirmed')
                if (execution['proof_role']!=expected_role or execution['prepare']!=ordinal or execution['mode']!=mode
                        or execution['within_prefix_revalidations']!=(4 if expected_counts[0] else 0)
                        or execution['cross_prepare_proof_reuses']!=(0 if expected_counts[0] else 8)
                        or execution['full_numerical_hour_replays']!=expected_counts[0]
                        or execution['reused_numerical_inspections_total']!=expected_counts[1]
                        or any(execution[key] is not False for key in ('formal_result','resource_admission',
                            'native_execution_authorized','production_handoff_integrated'))):
                    raise ValueError('diagnostic execution role/authority differs')
                if measurements and any(execution[key]!=measurements[0]['execution'][key] for key in (
                        'proof_basis_identity','active_validation_identity','session_identity')):
                    raise ValueError('two diagnostic receipts are not bound to one complete proof/session')
                measured=dict(prepare=ordinal,elapsed_seconds=elapsed,
                    full_numerical_hour_replays=envelope.full_numerical_hour_replays,
                    reused_numerical_inspections_total=envelope.fresh_byte_context_revalidations,
                    execution=execution,envelope_identity=envelope.envelope_identity,
                    execution_receipt_sha256=sha256(envelope.execution_receipt).hexdigest())
                save('prepare_'+str(ordinal)+'.json',measured);measurements.append(measured)
                policy.admit('after_prepare_'+str(ordinal))
                print(json.dumps(dict(mode=mode,prepare=ordinal,elapsed_seconds=elapsed,
                    full=envelope.full_numerical_hour_replays,reuses=envelope.fresh_byte_context_revalidations)),flush=True)
        receipt=owner.receipt();save('operation_receipt.json',receipt)
        if not receipt['complete'] or not receipt['public_envelopes_complete'] or not receipt['closed'] or not receipt['proof_cleared']:
            raise ValueError('diagnostic operation did not close and clear complete proof')
        if (receipt['session_identity']!=measurements[0]['execution']['session_identity']
                or receipt['active_validation_identity']!=measurements[0]['execution']['active_validation_identity']
                or [row['proof_basis_identity'] for row in receipt['prepares']]!=[
                    row['execution']['proof_basis_identity'] for row in measurements]
                or [row['envelope_identity'] for row in receipt['prepares']]!=[
                    row['envelope_identity'] for row in measurements]
                or [row['execution_receipt_sha256'] for row in receipt['prepares']]!=[
                    row['execution_receipt_sha256'] for row in measurements]
                or receipt['context_observations']!=32):
            raise ValueError('closed session receipt does not bind both measured envelopes')
        save('code_receipt.json',code_lease.receipt());save('metadata_receipt.json',parse_lease.receipt())
        result.update(measurements=measurements,scientific_bytes_equal_original=True,
            original_context_unchanged=True,original_numerical_inspector_unchanged=True,
            operation_closed_and_proof_cleared=True,context_observations=receipt['context_observations'])
    patch.undo();patch=None;policy.admit('after_fixture_cleanup')
    result.update(exit_code=0)
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc(),measurements=measurements)
finally:
    final_errors=[]
    if patch is not None:
        try:patch.undo()
        except BaseException:result.update(exit_code=1,fixture_cleanup_error=traceback.format_exc())
    if policy is not None:
        try:save('interpreter_receipt.json',policy.receipt())
        except BaseException:final_errors.append(dict(stage='interpreter_receipt',error=traceback.format_exc()))
    try:
        drift=[p for p,h in source_pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest()!=h]
        result.update(source_unchanged=not drift)
        if drift:result.update(exit_code=1,source_drift=drift)
    except BaseException:final_errors.append(dict(stage='source_postcheck',error=traceback.format_exc()))
    try:
        after=pin(p for p in SAVED.rglob('*') if p.is_file())
        result.update(saved_unchanged=bool(saved_pins) and after==saved_pins,saved_files=len(after))
        if not result['saved_unchanged']:result['exit_code']=1
    except BaseException:final_errors.append(dict(stage='saved_postcheck',error=traceback.format_exc()))
    if final_errors:result.update(exit_code=1,finalization_errors=final_errors)
    result.update(elapsed_seconds=perf_counter()-start)
    try:save('terminal.json',result)
    except BaseException:
        result.update(exit_code=1,terminal_write_error=traceback.format_exc())
    print(json.dumps({k:v for k,v in result.items() if k!='measurements'}),flush=True)
sys.exit(result['exit_code'])
