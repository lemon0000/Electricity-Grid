"""Saved numerical/source oracle with explicit fake host authority, no Parent credential.

All historical/source/registry arithmetic and context observations are genuine
under the original declared synthetic source fixture. Only the host lease and
complete-Parent signal are fake. This cannot close genuine Handoff integration.
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
plan_raw=(HERE/'parent_source_scientific_oracle_plan_02.json').read_bytes()
if len(sys.argv)!=2 or sha256(plan_raw).hexdigest()!=sys.argv[1]:
    raise ValueError('one fixed scientific oracle plan required')
plan=json.loads(plan_raw);OUT=Path(plan['inner_output']);OUT.mkdir(exist_ok=False)
sys.pycache_prefix=str(OUT/'empty_pycache');Path(sys.pycache_prefix).mkdir()
sources=plan['source_sha256'];started=perf_counter();patch=None;proof=None;parsed=None;identity_patch=None;identity_originals={};identity_pins={};identity_calls={}
result=dict(exit_code=1,formal_result=False,resource_admission=False,native_execution_authorized=False,
    full_hour0_chain_passed=False,live_Parent_credential_issued=False,complete_Parent_validation=False,
    host_lease_and_activation_are_explicit_fakes=True,synthetic_jobs=0,real_native_calls=0)

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
    bounded=load('performance.bounded_stable_read_entry',HERE/'bounded_stable_read_entry_v2.py')
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
        fixture=load('parent_source_saved_fixture',HERE.parent/'replay_saved_with_fixture_v1.py')
        patch=fixture.complete_fixture(fixture.saved.synthetic_source)(Path(plan['fixture_base']))
        policy.admit('saved_fixture_prepared')
        parsed=stack.enter_context(metadata.MetadataParseLease({Path(k):v for k,v in json.loads(
            (ENTRY/'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}))
        from experiments import h1_phase_exact_source_current_development_v2 as core
        from experiments import h1_selector_parent_validation_operation_development_v1 as bridge
        snapshot_raw=Path(plan['snapshot']).read_bytes()
        binding=json.loads(snapshot_raw)['declaration']['source_binding']
        root=Path(binding['root'])
        args=dict(expected_binding_sha256=binding['binding_sha256'],
            expected_terminal_sha256=binding['genesis_terminal_sha256'],completed_hours=1,
            expected_registry_identity=binding['registry_identity'])
        parsed.begin_discovery_window();begin=perf_counter()
        reference=core.prepare(root,**args)
        baseline_seconds=perf_counter()-begin
        baseline_projection=stable(reference)
        save('baseline_complete_source_projection.json',baseline_projection)
        baseline=dict(seconds=baseline_seconds,decision_sha256=core.io.digest(reference.prepared_current.decision.decision_bytes),
            audit_sha256=core.io.digest(reference.source_projection_audit_payload),full_numerical_replays=4)
        save('baseline.json',baseline)
        print(json.dumps(dict(stage='baseline_source_complete',**baseline)),flush=True)
        owner=SimpleNamespace(root=Path(plan['fixture_base'])/'parent_non_authoritative')
        token=object();activation=[False]
        original_lease_check,original_confirmed=bridge._lease_check,bridge._parent_confirmed
        def unit_lease_check(issued,parent):
            if issued is not token or parent is not owner:raise ValueError('explicit oracle lease differs')
        def unit_confirmed(issued,parent,value):
            unit_lease_check(issued,parent)
            return activation[0] and value is proof
        patch.setattr(bridge,'_lease_check',unit_lease_check)
        patch.setattr(bridge,'_parent_confirmed',unit_confirmed)
        witness=load('experiments._parent_source_scientific_oracle_v1',
            REPO/'experiments/h1_parent_source_n0_witness_development_v1.py')
        proof=witness.ParentSourceWitness(root,arm_id='explicit-saved-source-oracle',
            expected_binding_sha256=args['expected_binding_sha256'],
            expected_terminal_sha256=args['expected_terminal_sha256'],_parent_lease=token,_parent_owner=owner)
        fixed=bridge._capture_source_guard(core)
        own,verifier=core.implementation_identity(),core.historical.verifier_identity()
        measurements=[]
        with proof:
            for ordinal in range(17):
                parsed.begin_discovery_window();begin=perf_counter();ticket=proof._start();prefix=[0]
                with core.historical.history.replay.guard.solver_calls_forbidden():
                    dispatch=core.historical.witness._dispatch_view(core)
                    def fresh():
                        fixed();proof._check(ticket)
                        if (core.implementation_identity()!=own or core.historical.verifier_identity()!=verifier
                                or core.historical.witness._dispatch_view(core)!=dispatch):
                            raise ValueError('genuine source oracle context changed')
                        return verifier
                    def replay(root_,**pins):
                        value=witness._replay_prefix(root_,**pins,_operation=proof,_ticket=ticket,_prefix_index=prefix[0])
                        prefix[0]+=1
                        return value
                    fresh()
                    value=core._prepare(root,**args,_check=fresh,_replay=replay)
                    fresh()
                    if prefix[0]!=2:raise ValueError('two complete genuine prefixes required')
                    if (value.prepared_current.decision.decision_bytes!=reference.prepared_current.decision.decision_bytes
                            or value.source_projection_audit_payload!=reference.source_projection_audit_payload
                            or stable(value)!=baseline_projection):
                        raise ValueError('candidate source scientific bytes differ from predecessor')
                    counts=proof._finish(ticket,value.prepared_current.decision,value.source_projection_audit_payload)
                elapsed=perf_counter()-begin
                row=dict(prepare=ordinal+1,seconds=elapsed,full=counts[0],reused=counts[1],
                    scientific_decision_and_audit_bytes_equal=True,complete_source_fields_equal=True,
                    complete_source_projection_sha256=core.io.digest(core.io.encode(stable(value))))
                measurements.append(row);save('candidate_'+str(ordinal+1)+'.json',row)
                print(json.dumps(dict(stage='candidate_source_complete',**row)),flush=True)
                if ordinal==15:
                    activation[0]=True;proof.activate()
                if ordinal==0 and perf_counter()-started+16*max(baseline_seconds,elapsed)>plan['early_stop_projected_seconds']:
                    raise RuntimeError('representative source cost exceeds remaining registered 17-prepare budget')
        receipt=proof.receipt();save('operation_receipt.json',receipt)
        if (not receipt['complete'] or receipt['full_numerical_hour_replays']!=64
                or receipt['reused_numerical_inspections']!=72 or receipt['context_observations']!=272):
            raise ValueError('complete deferred activation and original context counts required')
        result.update(exit_code=0,decision_and_audit_bytes_equal=True,complete_source_fields_equal=True,
            complete_source_projection_scope='all declared source dataclass fields; canonical typed structural projection',
            baseline=baseline,measurements=measurements,
            source_scope_17_prepare_seconds=sum(row['seconds'] for row in measurements),
            first_sixteen_source_prepares_full=True,last_prepare_reused_after_fake_activation=True)
        save('metadata_receipt.json',parsed.receipt())
        save('bounded_read_receipt.json',lease.receipt())
        save('path_receipt.json',path_lease.receipt())
    closed=lease.closed_receipt()
    if (not closed['code_owner_closed'] or not closed['path_open_restored'] or not closed['path_read_bytes_restored']
            or closed['remaining_code_handles'] or closed['remaining_streams'] or closed['remaining_proxies']
            or closed['cleanup_errors']):raise ValueError('all private code handles and routes must close')
    if episode_store._path is not original_path or path_lease._state!='closed':raise ValueError('path lease not restored')
    save('bounded_closed_receipt.json',closed)
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
