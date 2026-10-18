"""One standalone post-negative window over completed owned input and a saved full-field oracle.

The declared synthetic source fixture and test-only code-identity scope match
the full target. Parent transport is an explicit fake; no real Parent credential or Job is created.
"""
from contextlib import ExitStack
from dataclasses import fields,is_dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType,SimpleNamespace

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
ENTRY=HERE.parent/'validation_path_optimization_01/entry_revision_07'
plan_name,expected_pin=sys.argv[1:]
if Path(plan_name).name!=plan_name:raise ValueError('local exact plan filename required')
plan_raw=(HERE/plan_name).read_bytes()
if sha256(plan_raw).hexdigest()!=expected_pin:raise ValueError('fixed reader plan differs')
plan=json.loads(plan_raw);OUT=Path(plan['inner_output']);OUT.mkdir(exist_ok=False)
sys.pycache_prefix=str(OUT/'empty_pycache');Path(sys.pycache_prefix).mkdir()
sources=plan['source_sha256'];started=perf_counter();patch=None;proof=None;parsed=None;identity_patch=None;identity_originals={};identity_pins={};identity_calls={}
result=dict(exit_code=1,formal_result=False,resource_admission=False,native_execution_authorized=False,
    full_hour0_chain_passed=False,live_Parent_credential_issued=False,complete_Parent_validation=False,
    parent_host_and_transport_are_explicit_fakes=True,synthetic_jobs=0,real_native_calls=0)

def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)

def load(name,path):
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=sources[str(path)]:raise ValueError('fixed diagnostic source differs')
    target=ModuleType(name);target.__file__=str(path);target.__package__=name.rpartition('.')[0]
    sys.modules[name]=target;exec(compile(raw,str(path),'exec'),vars(target));return target

def stable(value):
    if type(value) in (str,int,bool,type(None)):return [type(value).__name__,value]
    if type(value) is float:return ['float',value.hex()]
    if type(value) is bytes:return ['bytes',value.hex()]
    if isinstance(value,Fraction):return ['fraction',value.numerator,value.denominator]
    if is_dataclass(value):return ['dataclass',type(value).__module__,type(value).__qualname__,
        [[field.name,stable(getattr(value,field.name))] for field in fields(value)]]
    if type(value) in (tuple,list):return [type(value).__name__,[stable(item) for item in value]]
    if type(value) is dict:return ['dict',sorted([[stable(k),stable(v)] for k,v in value.items()],key=repr)]
    if type(value) in (set,frozenset):return [type(value).__name__,sorted([stable(item) for item in value],key=repr)]
    raise TypeError('complete stable source projection does not support '+str(type(value)))

try:
    if not sys.flags.isolated or not sys.dont_write_bytecode:raise ValueError('-I -B required')
    for name,pin in {**sources,**plan['old_chain_sha256'],**plan['saved_sha256']}.items():
        if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('fixed input differs: '+name)
    save('request.json',plan)
    package=ModuleType('performance');package.__path__=[str(ENTRY)];sys.modules['performance']=package
    load('performance.code_read_lease',ENTRY/'code_read_lease.py')
    metadata=load('performance.metadata_parse_lease',ENTRY/'metadata_parse_lease.py')
    policy=load('performance.interpreter_path_policy',ENTRY/'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY/'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    vendor=load('performance.vendor_code_policy',ENTRY/'vendor_code_policy.py');vendor.assert_unloaded(sys.modules)
    bounded=load('performance.bounded_stable_read_entry',HERE/plan['reader_entry'])
    with ExitStack() as stack:
        lease=stack.enter_context(bounded.BoundedStableReadLease(
            {Path(k):v for k,v in plan['code_lease_sha256'].items()},root=Path('D:/')))
        paths=load('experiments.h1_canonical_path_lease_development_v1',ENTRY/'canonical_path_lease.py')
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        original_path=episode_store._path
        path_lease=stack.enter_context(paths.CanonicalPathLease(episode_store,[Path(p) for p in plan['path_roots']]))
        # Match the full target's test-only pure code-identity scope before
        # source/Parent verifier definition. No source or dependency-data cache.
        import pytest
        from experiments import h1_bootstrap_integration_development_v2 as bootstrap
        from src.solvers import rq2_gurobi_declared_normal as adapter
        identity_originals={adapter:adapter.implementation_identity,bootstrap:bootstrap.implementation_identity}
        identity_pins={module:fn() for module,fn in identity_originals.items()}
        identity_calls={module:0 for module in identity_originals}
        identity_patch=pytest.MonkeyPatch()
        def cached_identity(module):
            def read():
                identity_calls[module]+=1
                return identity_pins[module]
            return read
        for module in identity_originals:identity_patch.setattr(module,'implementation_identity',cached_identity(module))
        # Import the two legacy helper dependencies under the configured path
        # before the helper can insert duplicate paths in the opposite order.
        from tests import h1_hour0_saved_replay_v2 as checked_saved
        from experiments import h1_group_n0_common_input_binding_development_v2 as checked_common
        direct_modules=((checked_saved,REPO/'tests/h1_hour0_saved_replay_v2.py'),
            (checked_common,REPO/'experiments/h1_group_n0_common_input_binding_development_v2.py'))
        source_paths={Path(name):pin for name,pin in sources.items()}
        def check_direct_origins():
            for module,path in direct_modules:
                if (sys.modules.get(module.__name__) is not module or Path(module.__file__)!=path
                        or Path(module.__spec__.origin)!=path
                        or sha256(path.read_bytes()).hexdigest()!=source_paths[path]):
                    raise ValueError('fixed legacy helper dependency origin differs')
        check_direct_origins();policy.admit('legacy_dependencies_preloaded')
        modules_before=dict(sys.modules);before_fixture_paths=tuple(sys.path)
        fixture=load('post_negative_source_saved_fixture',HERE.parent/'replay_saved_with_fixture_v1.py')
        after_fixture_paths=tuple(sys.path)
        if set(sys.modules)-set(modules_before)!={'post_negative_source_saved_fixture'}:
            raise ValueError('legacy helper imported undeclared modules under duplicate paths')
        if any(sys.modules.get(name) is not module for name,module in modules_before.items()):
            raise ValueError('legacy helper replaced existing modules')
        check_direct_origins()
        expected_raw=(str(REPO/'tests'),str(REPO),*before_fixture_paths)
        if after_fixture_paths!=expected_raw:raise ValueError('unexpected legacy helper path insertion')
        if tuple(dict.fromkeys(sys.path))!=(policy.paths[1],policy.paths[0],*policy.paths[2:]):
            raise ValueError('unexpected configured legacy duplicate order')
        sys.path.insert(0,policy.paths[0])
        save('fixture_path_observation.json',dict(before=before_fixture_paths,after=after_fixture_paths,
            corrected_paths=tuple(sys.path),expected_configured_paths=policy.paths,
            root_duplicate_counts=dict(before={root:before_fixture_paths.count(root) for root in policy.paths},
                after={root:after_fixture_paths.count(root) for root in policy.paths},
                corrected={root:sys.path.count(root) for root in policy.paths}),
            imported_modules=['post_negative_source_saved_fixture'],
            direct_origins={module.__name__:dict(file=str(path),sha256=source_paths[path]) for module,path in direct_modules}))
        # The saved installer asserts these original assets byte-for-byte and
        # suppresses only its two identical writes; it does not create a fixture.
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(Path(plan['fixture_base']))
        policy.admit('saved_fixture_prepared')
        if tuple(sys.path)!=policy.paths:raise ValueError('final configured fixture paths differ')
        save('fixture_path_admitted.json',dict(paths=tuple(sys.path),configured_paths=policy.paths,
            root_duplicate_counts={root:sys.path.count(root) for root in policy.paths}))
        parsed=stack.enter_context(metadata.MetadataParseLease({Path(k):v for k,v in json.loads(
            (ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}))
        from experiments import h1_phase_exact_source_current_development_v2 as core
        from experiments import h1_selector_parent_validation_operation_development_v2 as original_window
        from tests import test_h1_selector_post_negative_validation_development_v1 as unit
        request=json.loads(Path(plan['saved_source_cost_report']).read_bytes())['source_arguments']
        root=Path(request['root']);args={key:value for key,value in request.items() if key!='root'}
        oracle_raw=Path(plan['saved_source_fields_path']).read_bytes()
        if sha256(oracle_raw).hexdigest()!=plan['expected_complete_projection_sha256']:
            raise ValueError('independent saved complete source oracle differs')
        # No new reference prepare: current files are pinned, and the independent
        # source projection from the completed own-root is reused byte-for-byte.
        fixed_prepare=core.prepare
        unit_patch=pytest.MonkeyPatch();case=None
        try:
            binding=dict(root=str(root),binding_sha256=args['expected_binding_sha256'],
                genesis_terminal_sha256=args['expected_terminal_sha256'],registry_identity=args['expected_registry_identity'])
            parsed.begin_discovery_window()
            with unit.make_post_case(OUT/'explicit_fake_parent_transport_non_authoritative',unit_patch,
                    exact_source=core,source_binding=binding) as case:
                begin=perf_counter();observation=case.invoke();window_seconds=perf_counter()-begin
                windows=observation['source_windows']
                if (not observation['complete'] or not observation['outer_cleanup_complete']
                        or observation['parent_validations']!=10 or observation['borrowed_source_returns']!=160
                        or observation['source_prepares']!=2 or len(windows)!=1
                        or windows[0]['complete_source_signature_sha256']!=plan['expected_complete_projection_sha256']
                        or not windows[0]['window_cache_entry_cleared'] or not observation['source_window_cache_cleared']
                        or [site['retained_bodies'] for site in observation['parent_sites']]!=[7,1,1,1]
                        or core.prepare is not fixed_prepare):
                    raise ValueError('one standalone genuine-source window with complete saved field agreement required')
                if (case.operation._capture_source_guard is not case.module._capture_source_guard
                        or case.operation._capture_source_guard.__code__.co_code
                            !=original_window._capture_source_guard.__code__.co_code):
                    raise ValueError('original source dispatch guard must be retained')
                unit.released(case)
                save('window_receipt.json',observation)
                result.update(exit_code=0,complete_window_seconds=window_seconds,
                    original_source_prepares=2,window_source_prepares=2,logical_borrowed_source_returns=160,
                    complete_source_fields_equal=True,decision_audit_bytes_equal=True,
                    decision_audit_equality_basis='entry and tail canonical typed-source SHA256 equal independently saved complete projection SHA256, including decision and audit bytes',
                    equality_validation='complete_typed_projection_sha256_equality',
                    complete_source_projection_sha256=windows[0]['complete_source_signature_sha256'],
                    parent_host_and_transport_are_explicit_fakes=True,actual_source_dispatch_guard_retained=True,
                    complete_dynamic_input_closure_proved=False,unobserved_between_bookends_ABA_covered=False,
                    full_Parent_or_Handoff_acceptance=False,complete_workflow_speedup_measured=False,
                    saved_oracle_reused_without_new_baseline=True)
                print(json.dumps(dict(stage='post_negative_real_source_window_complete',seconds=window_seconds,
                    logical_returns=160,full_source_prepares=2)),flush=True)
        finally:unit_patch.undo()
        if (case is None or case.host._guard.locked() or any(g.locked() for g in case.bundle.held)
                or core.prepare is not fixed_prepare):raise ValueError('fake transport guards or source dispatch leaked')
        result['fake_transport_guards_released']=True
        save('metadata_receipt.json',parsed.receipt())
        save('bounded_read_receipt.json',lease.receipt())
        save('path_receipt.json',path_lease.receipt())
    closed=lease.closed_receipt()
    if (not closed['code_owner_closed'] or not closed['path_open_restored'] or not closed['path_read_bytes_restored']
            or closed['remaining_code_handles'] or closed['remaining_streams'] or closed['remaining_proxies']
            or closed['cleanup_errors']):raise ValueError('all private code handles and routes must close')
    if episode_store._path is not original_path or path_lease._state!='closed':raise ValueError('path lease not restored')
    save('bounded_closed_receipt.json',closed)
    path_closed=dict(dispatch_restored=episode_store._path is original_path,state=path_lease._state,
        remaining_directory_handles=len(path_lease._directories),remaining_paths=len(path_lease._paths))
    if path_closed!=dict(dispatch_restored=True,state='closed',remaining_directory_handles=0,remaining_paths=0):
        raise ValueError('path handles or retained paths leaked')
    save('path_closed_receipt.json',path_closed)
    for name in plan['code_lease_sha256']:
        with Path(name).open('r+b'):pass
    policy.admit('closed');save('interpreter_receipt.json',policy.receipt())
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc())
finally:
    if proof is not None:
        try:
            proof._cleanup_original()
            save('final_proof_receipt.json',proof.receipt())
        except BaseException:result.update(exit_code=1,proof_cleanup_error=traceback.format_exc())
    if patch is not None:
        try:patch.undo()
        except BaseException:result.update(exit_code=1,fixture_cleanup_error=traceback.format_exc())
    if identity_patch is not None:
        try:
            identity_patch.undo()
            after={module:module.implementation_identity() for module in identity_originals}
            if any(module.implementation_identity is not fn or after[module]!=identity_pins[module]
                    for module,fn in identity_originals.items()):raise ValueError('original identity bookend differs')
            save('identity_bookends.json',dict(test_only_identity_cache=True,production_overhead_measured=False,
                transient_code_or_package_ABA_covered=False,source_identity_cache=False,
                identities={module.__name__:dict(before=identity_pins[module],after=after[module],calls=identity_calls[module])
                    for module in identity_originals}))
        except BaseException:result.update(exit_code=1,identity_cleanup_error=traceback.format_exc())
    result['elapsed_seconds']=perf_counter()-started
    save('terminal.json',result)
    print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
