"""One bounded four-prepare differential diagnostic on retained synthetic bytes."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];E=HERE.parent
ENTRY=E/'validation_path_optimization_01/entry_revision_07'
SAVED=Path('D:/h1_chain_06_non_authoritative')
label,=sys.argv[1:]
if label!='saved_four_01_non_authoritative':raise ValueError('one fixed diagnostic attempt only')
OUT=HERE/label;OUT.mkdir(exist_ok=False)
if not sys.flags.isolated or not sys.dont_write_bytecode:raise ValueError('-I -B required')
sys.pycache_prefix=str(OUT/'empty_pycache');Path(sys.pycache_prefix).mkdir()

def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def pins(paths):return {str(p):sha256(p.read_bytes()).hexdigest() for p in paths}
def load(name,path):
    module=ModuleType(name);module.__file__=str(path);module.__package__=name.rpartition('.')[0]
    sys.modules[name]=module;exec(compile(path.read_bytes(),str(path),'exec'),vars(module));return module

start=perf_counter();source_pins={};saved_pins={};old_pins={};patch=None;result=dict(
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False,
    resource_admission=False,full_hour0_chain_passed=False,actual_bootstrap_registration=False,
    scope='one saved arm; predecessor four prepares versus diagnostic four confirmed builds; one full fallback',
    static_identity_shortcut=False,real_native_calls=0)
try:
    manifest=json.loads((ENTRY/'package_manifest_v1.json').read_bytes())['files_sha256']
    if pins(ENTRY/name for name in manifest)!={str(ENTRY/name):pin for name,pin in manifest.items()}:
        raise ValueError('configured predecessor members changed')
    expected={Path(k):v for k,v in json.loads((ENTRY/'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
    package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
    vendor=load('performance.vendor_code_policy',ENTRY/'vendor_code_policy.py')
    expected.update(vendor.vendor_files((ENTRY/'code_allowlist_v3.json').read_bytes(),
        (ENTRY/'vendor_code_allowlist_v1.json').read_bytes()))
    successor=[REPO/'experiments'/name for name in ('h1_historical_n0_verifier_development_v2.py',
        'h1_bootstrap_integration_development_v3.py','h1_owned_bootstrap_controller_development_v3.py')]
    expected.update({Path(k):v for k,v in pins(successor).items()})
    tests={REPO/k:v for k,v in json.loads((ENTRY/'test_closure_v1.json').read_bytes())['files_sha256'].items()}
    tests.update({Path(k):v for k,v in pins(REPO/'tests'/name for name in (
        'test_h1_historical_n0_verifier_development_v2.py','test_h1_bootstrap_n0_operation_development_v3.py')).items()})
    source_pins={str(k):v for k,v in {**expected,**tests}.items()}
    source_pins.update(pins([Path(__file__),HERE/'run_unit_bounded_v1.py',
        E/'replay_saved_with_fixture_v1.py',ENTRY/'package_manifest_v1.json',
        *(ENTRY/name for name in manifest)]))
    if pins(map(Path,source_pins))!=source_pins:raise ValueError('source closure drift')
    for name,pin in source_pins.items():
        path=Path(name);relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
        dest=OUT/'tested_bytes'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(path.read_bytes())
    saved_pins=pins(p for p in SAVED.rglob('*') if p.is_file())
    old_pins=json.loads((E/'chain_07/request.json').read_bytes())['before']
    if pins(map(Path,old_pins))!=old_pins:raise ValueError('old active-chain pin drift before diagnostic')
    headers=list(SAVED.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json'))
    if len(headers)!=1:raise ValueError('one saved common owner required')
    report=json.loads(headers[0].read_bytes())['declaration']['initial_report'];arm=report['canonical_arm']
    if arm!='network-only':raise ValueError('fixed representative arm differs')
    body=report['arm_audits'][arm]['reference']['local_terminal']['body'];root=Path(body['controller_root'])
    args=dict(expected_binding_sha256=body['controller_binding_sha256'],
        expected_terminal_sha256=body['controller_terminal_sha256'],completed_hours=1)
    if (not root.is_relative_to(SAVED) or args['expected_binding_sha256']!='782bef7d5268e46b7d5b767f310433e956868e515eccf1d718dfdd4bf3a1af03'
            or args['expected_terminal_sha256']!='81855c029bb9c334a0be07ebbbcb8d7e3f85b3f2f34c654c4ed5c13e1b46a6d9'):
        raise ValueError('fixed saved controller/pins differ')
    save('request.json',dict(source_sha256=source_pins,saved_sha256=saved_pins,old_chain_sha256=old_pins,
        controller_root=str(root),historical_arguments=args,predecessor_prepares=4,candidate_builds=4,
        fallback_prepares=1,context_evaluations_per_prepare=16,formal_result=False))
    code=load('performance.code_read_lease',ENTRY/'code_read_lease.py')
    metadata=load('performance.metadata_parse_lease',ENTRY/'metadata_parse_lease.py')
    policy=load('performance.interpreter_path_policy',ENTRY/'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY/'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    with ExitStack() as stack:
        vendor.assert_unloaded(sys.modules)
        lease=stack.enter_context(code.CodeReadLease(expected,root=Path('D:/')))
        fixture=load('n0_saved_fixture',E/'replay_saved_with_fixture_v1.py')
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(SAVED/'test_complete_independent_N0_r0')
        policy.admit('after_saved_fixture')
        parsed=stack.enter_context(metadata.MetadataParseLease({Path(k):v for k,v in json.loads(
            (ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}))
        from experiments import h1_historical_n0_verifier_development_v1 as oracle
        baseline=[];reference=None
        for ordinal in range(4):
            parsed.begin_discovery_window();begin=perf_counter()
            with oracle.witness.hour.prior.guard.solver_calls_forbidden():value=oracle.prepare(root,**args)
            elapsed=perf_counter()-begin
            if reference is None:reference=value
            if value.audit_payload!=reference.audit_payload or value.decision.decision_bytes!=reference.decision.decision_bytes:
                raise ValueError('predecessor science changed between prepares')
            baseline.append(elapsed)
            save('baseline_'+str(ordinal+1)+'.json',dict(seconds=elapsed,full=4,fresh=4,
                decision_sha256=sha256(value.decision.decision_bytes).hexdigest(),audit_sha256=sha256(value.audit_payload).hexdigest()))
            print(json.dumps(dict(stage='baseline',prepare=ordinal+1,seconds=elapsed)),flush=True)
        from experiments import h1_historical_n0_verifier_development_v2 as candidate
        operation=candidate.N0ValidationOperation(root,arm_id=arm,**args,diagnostic_only=True)
        measurements=[]
        with operation:
            for ordinal,site in enumerate(candidate.BUILD_SITES):
                parsed.begin_discovery_window();begin=perf_counter()
                ticket=operation.begin_build(None,site)
                with candidate.hour.prior.guard.solver_calls_forbidden():value=operation.prepare()
                if value.audit_payload!=reference.audit_payload or value.decision.decision_bytes!=reference.decision.decision_bytes:
                    raise ValueError('candidate science differs from predecessor exact bytes')
                stable_body=dict(controller_root=str(root),historical_verifier_schema=candidate.VERIFIER_SCHEMA,
                    historical_validation_contract=candidate.VERIFIER_SCHEMA,
                    historical_verifier_identity=value.verifier_identity,audit_payload_sha256=sha256(value.audit_payload).hexdigest())
                operation.confirm_build(ticket,stable_body)
                elapsed=perf_counter()-begin
                measurement=dict(site=site,seconds=elapsed,execution=json.loads(value.execution_receipt),
                    envelope_identity=value.envelope_identity,scientific_bytes_equal=True)
                measurements.append(measurement);save('candidate_'+str(ordinal+1)+'.json',measurement)
                print(json.dumps(dict(stage='candidate',site=site,seconds=elapsed)),flush=True)
        receipt=operation.receipt();save('operation_receipt.json',receipt)
        if not receipt['complete'] or receipt['context_observations']!=64:raise ValueError('incomplete four-build proof receipt')
        parsed.begin_discovery_window();begin=perf_counter()
        with candidate.hour.prior.guard.solver_calls_forbidden():fallback=candidate.prepare(root,**args)
        fallback_seconds=perf_counter()-begin
        if fallback.audit_payload!=reference.audit_payload or fallback.decision.decision_bytes!=reference.decision.decision_bytes:
            raise ValueError('full fallback science differs from predecessor exact bytes')
        if (fallback.full_numerical_hour_replays,fallback.fresh_byte_context_revalidations)!=(4,4):
            raise ValueError('full fallback counts differ')
        save('fallback.json',dict(seconds=fallback_seconds,execution=json.loads(fallback.execution_receipt),scientific_bytes_equal=True))
        save('code_receipt.json',lease.receipt());save('metadata_receipt.json',parsed.receipt())
        save('interpreter_receipt.json',policy.receipt())
        result.update(exit_code=0,baseline_prepare_seconds=baseline,candidate_measurements=measurements,
            baseline_four_seconds=sum(baseline),candidate_four_seconds=sum(v['seconds'] for v in measurements),
            fallback_seconds=fallback_seconds,scientific_bytes_equal_predecessor=True,
            numerical_counts_before=[16,16],numerical_counts_after=[4,28],context_evaluations_before=64,
            context_evaluations_after=64,code_lease_files=len(expected),vendor_module_origins=vendor.origins(sys.modules,required=True))
except BaseException:result.update(exit_code=1,error=traceback.format_exc())
finally:
    if patch is not None:
        try:patch.undo()
        except BaseException:result.update(exit_code=1,cleanup_error=traceback.format_exc())
    for key,before in (('sources',source_pins),('saved',saved_pins),('old_chain',old_pins)):
        try:
            after=pins(p for p in SAVED.rglob('*') if p.is_file()) if key=='saved' else pins(map(Path,before))
            clean=bool(before) and before==after;result[key+'_unchanged']=clean
            if not clean:result.update(exit_code=1,**{key+'_drift':True})
        except BaseException:result.update(exit_code=1,**{key+'_postcheck_error':traceback.format_exc()})
    result['elapsed_seconds']=perf_counter()-start
    save('terminal.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='candidate_measurements'}),flush=True)
sys.exit(result['exit_code'])
