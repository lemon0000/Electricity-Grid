"""Rref/A capsule-to-selector replay bridge; detached development evidence.

Versioned single-stage composition with one prefix numerical replay per audit.
Legacy-shaped records are explicit reconstructions, not original solve records.
"""
from importlib.metadata import version
from pathlib import Path
from types import MappingProxyType, FunctionType
import sys

from pyomo.environ import Var
from pyomo.opt import SolverStatus, TerminationCondition, SolutionStatus, ProblemSense

from experiments import h1_native_raw_science_development_v1 as science
from experiments import h1_origin_selector_replay_development_v1 as selector

from experiments import h1_origin_selector_incremental_replay_development_v1 as incremental

io = science.io
capture = science.capture
SCHEMA = 'h1_selector_raw_science_development_v2'
FLAGS = MappingProxyType(dict(native_execution_authenticated=False, source_input_binding_verified=False,
    normal_selection_authenticated=False, common_publication_verified=False,
    formal_result=False, resource_admission=False, native_execution_authorized=False,
    collector_integrated=False,native_export_coverage=False,producer_coverage_proven=False,
    formal_execution_ready=False,scientific_acceptance=False,detached_consumer_authenticated=False,
    reference_or_actual_ready=False,security_certified=False))


def _scope():
    expected={'native_execution_authenticated','source_input_binding_verified',
        'normal_selection_authenticated','common_publication_verified','formal_result',
        'resource_admission','native_execution_authorized','collector_integrated',
        'native_export_coverage','producer_coverage_proven','formal_execution_ready',
        'scientific_acceptance','detached_consumer_authenticated','reference_or_actual_ready',
        'security_certified'}
    if (SCHEMA!='h1_selector_raw_science_development_v2' or type(FLAGS) is not MappingProxyType
            or set(FLAGS)!=expected or any(v is not False for v in FLAGS.values())):
        raise ValueError('selector development scope changed')


def implementation_identity():
    _scope()
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),
        science.implementation_identity(),io.digest(Path(selector.__file__).read_bytes()),
        io.digest(Path(incremental.__file__).read_bytes())]))


def _prefix(frame,disclosure,before,records,args):
    key=selector.input_identity(frame,disclosure,before,lane=args['lane'],power=args.get('power'))
    pins=tuple(io.digest(r) for r in records)
    prefix=incremental.verify_prefix(frame,disclosure,before,records,**args,
        expected_identity=key,expected_policy_identity=before.policy_identity,expected_report_sha256=pins)
    locks=incremental.prefix_locks(prefix)
    context=selector._context(frame,disclosure,before,index=len(records),frozen=locks,**args)
    request=io.digest(selector.native._encoded([SCHEMA,implementation_identity(),context,pins]))
    return request,key,locks,prefix


def _bindings():
    rows=[]
    for module in (sys.modules[__name__],science,incremental):
        for name,function in sorted(vars(module).items()):
            if type(function) is FunctionType:
                rows.append((module.__name__,name,function,function.__code__,
                    repr(function.__defaults__),repr(function.__kwdefaults__),
                    tuple(id(c.cell_contents) for c in (function.__closure__ or ()))))
    return tuple(rows)


def revalidate_request(prefix,expected_key,frame,disclosure,before,records,**args):
    _scope()
    locks=incremental.revalidate_prefix(prefix,frame,disclosure,before,records,**args)
    context=selector._context(frame,disclosure,before,index=len(records),frozen=locks,**args)
    pins=tuple(io.digest(r) for r in records)
    request=io.digest(selector.native._encoded([SCHEMA,implementation_identity(),context,pins]))
    if request!=expected_key:
        raise ValueError('selector inputs changed during capsule audit')
    _scope()
    return request


def request_key(frame,disclosure,before,records,**args):
    return _prefix(frame,disclosure,before,records,args)[0]


def _admit_model(model,limits):
    if any(not v.is_continuous() for v in model.component_data_objects(Var)):
        raise ValueError('continuous selector model required')
    scale=selector.native.capture.model_scale(model)
    if scale.variables>limits.max_variables or scale.constraints>limits.max_constraints:
        raise ValueError('selector model exceeds replay limits')
    capture.export._canonical(model)


def _derived_record(model,numerical,assignment,post,purpose,observations):
    """Reconstructed metadata for the legacy consistency checker, not history."""
    api=selector.native.capture
    scale=api.model_scale(model)
    lower,upper=map(float.fromhex,(post['lower'],post['upper']))
    return api._make(api.GridSolveEvidence,purpose=purpose,variables=scale.variables,constraints=scale.constraints,
        solver_records=((api._enum(SolverStatus.ok),api._enum(TerminationCondition.optimal)),),
        problem_records=((api._enum(ProblemSense.minimize),*(api._raw_number(v) for v in
            (lower,upper,scale.variables,scale.constraints,1))),),
        solution_statuses=(api._enum(SolutionStatus.optimal),),solution_count=1,
        structures=tuple(o['structure'] for o in observations),
        versions=(observations[0]['versions'],observations[2]['versions']),
        options=(observations[0]['options'],observations[2]['options']),
        initial_values=observations[0]['snapshot'],preload_values=observations[1]['snapshot'],
        native_values=tuple((n,float.fromhex(x)) for n,x in post['reported_values']),
        canonical_completed_values=tuple((n,float.fromhex(x),why) for n,x,why in post['completions']),
        loaded_values=tuple(sorted(assignment.items())),native_objectives=(),
        objective=float.fromhex(numerical['provenance']['canonical_objective_hex']),lower=lower,upper=upper,
        maximum_residual=numerical['maximum_residual'],
        maximum_integrality_violation=numerical['maximum_integrality_violation'],
        calls=1,assignment_valid=numerical['assignment_valid'],optimal=True,native_infeasible=False,errors=())


def _audit_stage(native_raw,postsolve_raw,frame,disclosure,before,records,*,
                expected_key,expected_binding,expected_export,observations,**args):
    """Conditional numerical replay, called only after owned capture completion."""
    _scope()
    bindings=_bindings()
    with science.prior.guard.solver_calls_forbidden():
        key,identity,locks,prefix=_prefix(frame,disclosure,before,records,args)
        if key!=expected_key:raise ValueError('selector capsule request differs')
        model=selector.build_development_stage(frame,disclosure,before,lane=args['lane'],
            power=args.get('power'),index=len(records),frozen=locks,expected_identity=identity)
        _admit_model(model,args['limits'])
        fresh=model.clone()
        assignment,attrs,constant,terms=science.decode_native(native_raw,model,
            expected_binding=expected_binding,expected_export=expected_export)
        post=science._postsolve(postsolve_raw,model,assignment,key=key,native_sha=io.digest(native_raw))
        if (attrs['Status']!=2 or attrs['SolCount']!=1 or post['status']!='ok'
                or post['termination']!='optimal' or post['solution_status']!='optimal'
                or attrs['ObjBound'].hex()!=post['lower'] or attrs['ObjVal'].hex()!=post['upper']
                or attrs['ObjBoundC'].hex()!=attrs['ObjBound'].hex()):
            raise ValueError('native/Pyomo optimal status or bound correspondence differs')
        if any(v<0 for n,v in assignment.items() if n.startswith('generation[')):
            raise ValueError('negative selector generation retained without conversion')
        numerical=science._numerical(model,args['specification'],assignment,attrs,constant,terms,post)
        if not numerical['provenance']['native_algebra_equals_canonical_algebra']:
            raise ValueError('native objective algebra differs')
        purpose=f'{selector.SCHEMA}:{args["lane"].role}:{len(records)}:{selector.stage_labels(frame,args["lane"])[len(records)]}'
        derived=_derived_record(fresh,numerical,assignment,post,purpose,observations)
        raw=selector.encode_development_record(frame,disclosure,before,derived,
            index=len(records),frozen=locks,**args)
        combined=records+(raw,)
        replay=incremental.append_verified_stage(prefix,frame,disclosure,before,records,raw,**args,
            expected_report_sha256=tuple(io.digest(r) for r in combined))
        if replay.verified_stages!=len(combined) or replay.errors not in ((),('incomplete_stage_chain',)):
            raise ValueError('selector physical/gap/lock replay rejected:'+repr(replay.errors))
        revalidate_request(prefix,key,frame,disclosure,before,records,**args)
        if _bindings()!=bindings:
            raise ValueError('selector raw bridge function bindings changed')
        _scope()
        return dict(selector_record=raw,lock_hex=replay.canonical_lock_hex[-1],
            selector_chain_complete=replay.next_candidate is not None,
            completion_scope='selector_replay_chain_only',derived_replay_record=True,
            native_sha256=io.digest(native_raw),postsolve_sha256=io.digest(postsolve_raw),**FLAGS)


def _observe(model,spec):
    api=selector.native.capture
    return dict(structure=api._structure(model),snapshot=api._snapshot(model),
        versions=(version('Pyomo'),version('gurobipy')),
        options=tuple(sorted(api.solver_options(spec).items())))


def _run_stage(root,frame,disclosure,before,records,*,expected_key,**args):
    """Future owned-producer primitive; no CLI, authority, retry or owner commit.

    Tests substitute the exact direct adapter. Calling this with a real adapter
    requires separate native authority and an enclosing owned Job integration.
    """
    _scope()
    spec=args['specification']
    if spec.name!='gurobi':raise ValueError('selector capture requires Gurobi direct')
    key,identity,locks,prefix=_prefix(frame,disclosure,before,records,args)
    if key!=expected_key:raise ValueError('selector capsule request differs')
    model=selector.build_development_stage(frame,disclosure,before,lane=args['lane'],
        power=args.get('power'),index=len(records),frozen=locks,expected_identity=identity)
    observations=[_observe(model,spec)]
    # Check the inherited fixed caps before allocating any capture or solver.
    _admit_model(model,args['limits'])
    root=Path(root).resolve();root.mkdir(exist_ok=False)
    owned=capture.StageCapture(root/'capture',request_sha256=key,
        expected_structure=observations[0]['structure'],
        expected_implementation=capture.implementation_identity())
    views={};listings={}
    def retain(path,cap):
        path=Path(path)
        view=io.read_stable(path,cap)
        if path in views and views[path]!=(cap,view):raise ValueError('selector retained view changed')
        views[path]=(cap,view)
        return view[0]
    def check():
        _scope()
        owned._check()
        if request_key(frame,disclosure,before,records,**args)!=key:
            raise ValueError('selector request changed')
        for path,(cap,view) in tuple(views.items()):
            if io.read_stable(path,cap)!=view:raise ValueError('selector retained view changed')
        for path,names in listings.items():
            if {p.name for p in path.iterdir()}!=names:raise ValueError('selector namespace changed')
    def provisional(native,results,owned_model):
        if owned_model is not model:raise ValueError('selector model owner differs')
        raw=retain(owned.raw.root/'000/raw.bin',io.RAW_CAP)
        if raw!=native:raise ValueError('selector raw differs')
        post=science.capture_postsolve(model,results,native_sha=io.digest(raw),key=key)
        io.write_new(root/'postsolve.json',post)
        retain(root/'postsolve.json',science.POST_CAP)
        observations.append(_observe(model,spec))
        check()
        # No audit, saved record or successor lock exists at this boundary.
    owned.run(lambda:model,spec,provisional)
    if not owned.complete or owned.poisoned or len(observations)!=2:
        raise ValueError('selector capture did not complete')
    observations.append(_observe(model,spec))
    if any(o!=observations[0] for o in observations[1:]):
        raise ValueError('selector observed metadata drift')
    native=retain(owned.raw.root/'000/raw.bin',io.RAW_CAP)
    post=retain(root/'postsolve.json',science.POST_CAP)
    complete=retain(owned.root/'complete.json',io.META_CAP)
    terminal=retain(owned.raw.root/'terminal.json',io.META_CAP)
    for name in ('binding.json','specification.json','export.json'):
        retain(owned.root/name,io.META_CAP)
    raw_binding=retain(owned.raw.root/'binding.json',io.META_CAP)
    for name in ('intent.json','raw_receipt.json','outcome.json'):
        retain(owned.raw.root/'000'/name,io.META_CAP)
    expected=dict(schema=capture.SCHEMA,binding_sha256=owned.binding_sha,
        raw_sha256=io.digest(native),raw_terminal_sha256=io.digest(terminal),
        callback_sequence_complete=True,**capture.FLAGS)
    if complete!=io.encode(expected):raise ValueError('selector capture completion differs')
    inspected=io.inspect(owned.raw.root,expected_request=key,expected_binding_sha256=io.digest(raw_binding))
    if not inspected['callback_sequence_complete'] or inspected['errors']:
        raise ValueError('selector raw chain incomplete')
    listings.update({root:{'capture','postsolve.json'},
        owned.root:{'binding.json','specification.json','export.json','complete.json','native_raw'},
        owned.raw.root:{'binding.json','terminal.json','000'},
        owned.raw.root/'000':{'intent.json','raw.bin','raw_receipt.json','outcome.json'}})
    check()
    result=_audit_stage(native,post,frame,disclosure,before,records,expected_key=key,
        expected_binding=owned.binding_sha,expected_export=owned.records['export.json'],
        observations=observations,**args)
    observation_raw=io.encode(dict(schema=SCHEMA+'_observations',observations=observations,
        option_basis='declared options checked by completed StageCapture before apply',
        call_basis='one intercepted apply in completed StageCapture',
        evidence_role='reconstructed_selector_view',capture_complete_sha256=io.digest(complete)))
    io.write_new(root/'observations.json',observation_raw)
    listings[root].add('observations.json')
    retain(root/'observations.json',io.RAW_CAP)
    check()
    io.write_new(root/'selector_record.json',result['selector_record'])
    listings[root].add('selector_record.json')
    retain(root/'selector_record.json',args['limits'].max_record_bytes)
    check()
    receipt={k:v for k,v in result.items() if k!='selector_record'}
    receipt.update(schema=SCHEMA,request_key=key,evidence_role='reconstructed_selector_view',
        capture_complete_sha256=io.digest(complete),binding_sha256=owned.binding_sha,
        export_sha256=owned.records['export.json'],observations_sha256=io.digest(observation_raw),
        selector_record_sha256=io.digest(result['selector_record']))
    terminal_raw=io.encode(receipt)
    io.write_new(root/'terminal.json',terminal_raw)
    listings[root].add('terminal.json')
    retain(root/'terminal.json',io.RAW_CAP)
    check()
    return dict(result,bridge_terminal_sha256=io.digest(terminal_raw))
