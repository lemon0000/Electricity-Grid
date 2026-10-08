"""H1 reference/actual stage mathematics and solver-free saved-record replay.

Detached numerical candidates only: no native executor or publication owner.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

from pyomo.environ import ConstraintList, NonNegativeReals, Var
from experiments import h1_current_grid_step_development_v1 as physical
from src.rq2_joint_deliverability_boundary_v1 import reference_selector as reference
from src.rq2_joint_deliverability_boundary_v1 import actual_dispatch_selector as actual
from src.rq2_joint_deliverability_boundary_v1 import reference_grid as old_reference
from src.rq2_joint_deliverability_boundary_v1 import grid_evidence_replay as native

_owned, _Owned, _digest, _finite = physical._owned, physical._Owned, physical._digest, physical._finite
SCHEMA = 'h1_selector_saved_replay_development_v1'
RREF = physical.Lane('Rref',None)


@dataclass(frozen=True)
class ReplayLimits:
    max_stages: int
    max_variables: int
    max_constraints: int
    max_record_bytes: int
    max_total_bytes: int
    max_seconds_per_solve: int
    max_threads: int
    max_solver_calls: int
    max_total_solver_seconds: int

    def __post_init__(self):
        for field in self.__dataclass_fields__:
            if type(getattr(self,field)) is not int or getattr(self,field)<=0:
                raise ValueError('positive explicit replay limits required')
        if self.max_record_bytes>16*1024**2 or self.max_stages>1024:
            raise ValueError('development replay envelope exceeded')


def _configuration(lane,selector,spec,limits,count):
    if type(lane) is not physical.Lane or type(limits) is not ReplayLimits:
        raise ValueError('typed lane and replay limits required')
    lane.__post_init__();limits.__post_init__()
    cls=reference.ReferenceSelectorSpec if lane.role=='Rref' else actual.ActualDispatchSpec
    if type(selector) is not cls or type(spec) is not native.capture.Rq2SolverSpec:
        raise ValueError('matching selector and solver specification required')
    selector.__post_init__()
    if spec!=native.capture.solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if any(getattr(spec,k)>1e-6 for k in ('feasibility_tolerance','optimality_tolerance','integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds selector applicability')
    if count>limits.max_stages:
        raise ValueError('complete UID selector exceeds replay stage limit')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds>limits.max_seconds_per_solve
            or spec.threads>limits.max_threads or count>limits.max_solver_calls
            or count*spec.time_limit_seconds>limits.max_total_solver_seconds):
        raise ValueError('complete selector exceeds declared historical budget')


def implementation_identity(spec,limits):
    return _digest(SCHEMA,physical.implementation_identity(),native._identity(spec,limits),
        tuple((m.__name__,sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (reference,actual,old_reference)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def policy_identity(lane,selector,spec,limits):
    _configuration(lane,selector,spec,limits,0)
    return _digest(implementation_identity(spec,limits),lane,selector,spec,limits)


@dataclass(frozen=True,init=False)
class SelectionCandidate(_Owned):
    physical_carry: physical.PhysicalCandidateCarry
    policy_identity: str
    previous_selection_identity: str | None
    selection_identity: str | None

    @property
    def identity(self):return _digest(self)


def initialize_development_selection(frame,disclosure,*,lane,selector,specification,limits):
    _configuration(lane,selector,specification,limits,len(stage_labels(frame,lane)))
    policy=policy_identity(lane,selector,specification,limits)
    carry=physical.initialize_development_carry(frame,disclosure,lane=lane)
    return _owned(SelectionCandidate,physical_carry=carry,policy_identity=policy,
        previous_selection_identity=None,selection_identity=None)


def _power(frame,lane,power):
    if lane.role=='Rref':
        if power is not None:raise ValueError('reference power is selected, not prescribed')
        return physical.RelativeDcPower(frame.info.relative_hour,'0','1','mechanism_assumption')
    if type(power) is not physical.RelativeDcPower:
        raise ValueError('actual requires prescribed relative-hour power')
    return power


def input_identity(frame,disclosure,before,*,lane,power=None):
    if type(before) is not SelectionCandidate or type(lane) is not physical.Lane:
        raise ValueError('detached typed selection candidate and lane required')
    lane.__post_init__();physical._pin(before.policy_identity)
    key=physical.development_step_identity(frame,disclosure,before.physical_carry,_power(frame,lane,power),lane=lane)
    return _digest(SCHEMA,before,key)


def stage_labels(frame,lane):
    physical._information(frame)
    if type(lane) is not physical.Lane:raise ValueError('typed lane required')
    lane.__post_init__()
    uids=tuple(g.uid for g in frame.info.network.units)
    if not uids or uids!=tuple(sorted(set(uids))):raise ValueError('complete sorted UID inventory required')
    return (('grid_request',) if lane.role=='Rref' else ())+('l1_normal_deviation',)+tuple('generation:'+u for u in uids)


def _base(frame,disclosure,before,lane,power):
    p=_power(frame,lane,power);carry=before.physical_carry
    model=physical.build_development_model(frame,disclosure,carry,p,lane=lane,
        expected_identity=physical.development_step_identity(frame,disclosure,carry,p,lane=lane))
    if lane.role=='Rref':
        info=frame.info
        model.reference_power=Var(domain=NonNegativeReals,bounds=(0.,info.current.dc_baseline_mw))
        model.balance.clear()
        n,c=info.network,info.current
        for bus in n.buses:
            generated=sum(model.generation[g.uid] for g in n.units if g.bus==bus)
            exported=sum(model.branch_flow[b.uid]*((b.from_bus==bus)-(b.to_bus==bus)) for b in n.ac_branches)
            exported+=sum(model.dc_flow[b.uid]*((b.from_bus==bus)-(b.to_bus==bus)) for b in n.dc_branches)
            demand=dict(c.demand_by_bus_mw)[bus]+(model.reference_power if bus==n.dc_bus else 0.)
            model.balance.add(generated-demand==exported)
        model.objective.set_value(c.dc_baseline_mw-model.reference_power)
    return model


def build_development_stage(frame,disclosure,before,*,lane,index,frozen,expected_identity,power=None):
    physical._pin(expected_identity)
    if input_identity(frame,disclosure,before,lane=lane,power=power)!=expected_identity:
        raise ValueError('selector input identity mismatch')
    labels=stage_labels(frame,lane)
    if type(index) is not int or not 0<=index<len(labels) or type(frozen) is not tuple or len(frozen)!=index:
        raise ValueError('exact stage index and predecessor lock count required')
    for x in frozen:
        if _finite(x)<0:raise ValueError('nonnegative canonical locks required')
    model=_base(frame,disclosure,before,lane,power)
    model.selector_deviation=Var(model.GEN,domain=NonNegativeReals)
    model.selector_constraints=ConstraintList()
    for uid,planned in frame.info.normal.generation_mw:
        model.selector_constraints.add(model.selector_deviation[uid]>=model.generation[uid]-planned)
        model.selector_constraints.add(model.selector_deviation[uid]>=planned-model.generation[uid])
    objectives=((frame.info.current.dc_baseline_mw-model.reference_power,) if lane.role=='Rref' else ())
    objectives+=(sum(model.selector_deviation[uid] for uid in model.GEN),*(model.generation[uid] for uid in model.GEN))
    model.selector_fixed=ConstraintList()
    for expression,fixed in zip(objectives,frozen):model.selector_fixed.add(expression==fixed)
    model.objective.set_value(objectives[index])
    return model


@dataclass(frozen=True,init=False)
class ReferenceWitness(_Owned):
    physical_witness: physical.PhysicalCandidateWitness | None
    candidate_grid_request_exact: tuple | None
    physical_assignment_valid: bool
    errors: tuple


def _reference_assignment(frame,disclosure,before,assignment):
    values=dict(assignment)
    p=Q(str(_finite(values.pop('reference_power'))))
    baseline=Q(str(frame.info.current.dc_baseline_mw))
    if not 0<=p<=baseline:
        return _owned(ReferenceWitness,physical_witness=None,candidate_grid_request_exact=None,
            physical_assignment_valid=False,errors=('reference_power_outside_exact_domain',))
    power=physical.RelativeDcPower(frame.info.relative_hour,str(p.numerator),str(p.denominator),'mechanism_assumption')
    w=physical.audit_development_assignment(frame,disclosure,before.physical_carry,power,values,lane=RREF,
        expected_identity=physical.development_step_identity(frame,disclosure,before.physical_carry,power,lane=RREF))
    g=baseline-p
    return _owned(ReferenceWitness,physical_witness=w,
        candidate_grid_request_exact=(str(g.numerator),str(g.denominator)) if w.physical_assignment_valid else None,
        physical_assignment_valid=w.physical_assignment_valid,errors=w.errors)


def _actual_assignment(frame,disclosure,before,power,assignment):
    lane=before.physical_carry.lane
    return physical.audit_development_assignment(frame,disclosure,before.physical_carry,power,assignment,lane=lane,
        expected_identity=physical.development_step_identity(frame,disclosure,before.physical_carry,power,lane=lane))


@dataclass(frozen=True,init=False)
class ReplayResult(_Owned):
    input_identity: str
    policy_identity: str
    report_sha256: tuple
    verified_stages: int
    canonical_lock_hex: tuple
    stage_diagnostics: tuple
    status: str
    errors: tuple
    candidate_request_exact: tuple | None
    next_candidate: SelectionCandidate | None
    solver_calls_by_replay: int
    source_input_binding_verified: bool
    normal_selection_authenticated: bool
    native_execution_authenticated: bool
    detached_consumer_authenticated: bool
    common_publication_verified: bool
    reference_or_actual_ready: bool
    formal_result: bool
    security_certified: bool
    exact_lexicographic_certificate: None
    infeasibility_certificate: None
    causal_certificate: None


def _context(frame,disclosure,before,*,lane,index,frozen,selector,specification,limits,power=None):
    identity=input_identity(frame,disclosure,before,lane=lane,power=power)
    labels=stage_labels(frame,lane)
    _configuration(lane,selector,specification,limits,len(labels))
    policy=policy_identity(lane,selector,specification,limits)
    if before.policy_identity!=policy:raise ValueError('predecessor selector policy mismatch')
    model=build_development_stage(frame,disclosure,before,lane=lane,index=index,frozen=frozen,
        expected_identity=identity,power=power)
    return dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',index=index,label=labels[index],
        purpose=f'{SCHEMA}:{lane.role}:{index}:{labels[index]}',input_identity=identity,policy_identity=policy,
        implementation_identity=implementation_identity(specification,limits),lane=lane,power=power,
        specification=specification,limits=limits,model_structure_identity=native.capture._structure(model),
        frozen=frozen,frozen_hex=tuple(float(x).hex() for x in frozen),native_execution_authenticated=False)


def encode_development_record(frame,disclosure,before,raw,*,lane,index,frozen,selector,specification,limits,power=None):
    """Bind saved evidence to one stage; this serialization grants no trust."""
    if type(raw) is not native.capture.GridSolveEvidence:raise ValueError('typed saved raw required')
    context=_context(frame,disclosure,before,lane=lane,index=index,frozen=frozen,selector=selector,
        specification=specification,limits=limits,power=power)
    if raw.purpose!=context['purpose']:raise ValueError('raw stage purpose mismatch')
    result=native._encoded(dict(**context,raw=raw,
        canonical_objective_hex=None if raw.objective is None else float(raw.objective).hex()))
    if len(result)>limits.max_record_bytes:raise ValueError('encoded record exceeds cap')
    return result


def replay_development_records(frame,disclosure,before,records,*,lane,selector,specification,limits,
        expected_identity,expected_policy_identity,expected_report_sha256,power=None):
    """Reconstruct full saved native-shaped records; do not authenticate execution.

    No external builder/executor is accepted. A prefix or any failed stage gives
    no successor. The caller retains original bytes, including failed records.
    """
    physical._pin(expected_identity);physical._pin(expected_policy_identity)
    labels=stage_labels(frame,lane);_configuration(lane,selector,specification,limits,len(labels))
    def check():
        if (input_identity(frame,disclosure,before,lane=lane,power=power)!=expected_identity
                or policy_identity(lane,selector,specification,limits)!=expected_policy_identity
                or before.policy_identity!=expected_policy_identity):
            raise ValueError('selector input/policy/predecessor drift')
    check()
    if (type(records) is not tuple or type(expected_report_sha256) is not tuple
            or len(records)!=len(expected_report_sha256) or len(records)>len(labels)):
        raise ValueError('bounded record tuple and complete external pin inventory required')
    total=0
    for data,pin in zip(records,expected_report_sha256,strict=True):
        physical._pin(pin)
        if type(data) is not bytes or len(data)>limits.max_record_bytes or sha256(data).hexdigest()!=pin:
            raise ValueError('record bytes/size/external pin mismatch')
        total+=len(data)
    if total>limits.max_total_bytes:raise ValueError('aggregate replay byte cap')
    frozen=();diagnostics=[];errors=[];witness=None
    for index,data in enumerate(records):
        check()
        def builder():
            return build_development_stage(frame,disclosure,before,lane=lane,index=index,frozen=frozen,
                expected_identity=expected_identity,power=power)
        try:
            decoded=json.loads(data,object_pairs_hook=native._unique_object,parse_constant=native._reject_constant)
            if native._encoded(decoded)!=data:raise ValueError('canonical saved raw bytes required')
            context=_context(frame,disclosure,before,lane=lane,index=index,frozen=frozen,selector=selector,
                specification=specification,limits=limits,power=power)
            if (type(decoded) is not dict or set(decoded)!=set(context)|{'raw','canonical_objective_hex'}
                    or native._encoded({k:decoded[k] for k in context})!=native._encoded(context)):
                raise ValueError('exact stage context/lock envelope mismatch')
            raw_fields=native._tuples(decoded['raw'])
            purpose=f'{SCHEMA}:{lane.role}:{index}:{labels[index]}'
            diagnostic=native._replay(raw_fields,builder,specification,limits,purpose)
            if (not diagnostic['replay_consistent'] or raw_fields['calls']!=1
                    or not diagnostic['canonical_assignment_valid'] or not diagnostic['optimal_flag_reproduced']):
                raise ValueError('complete valid optimal native-record consistency required')
            canonical=diagnostic['recomputed_objective']
            if decoded['canonical_objective_hex']!=float(canonical).hex():
                raise ValueError('stored canonical objective hex differs from replay')
            # Objective/residuals are independently recomputed, never renamed ObjVal.
            raw_fields.update(objective=diagnostic['recomputed_objective'],
                maximum_residual=diagnostic['recomputed_maximum_residual'],
                maximum_integrality_violation=diagnostic['recomputed_maximum_integrality_violation'],
                assignment_valid=bool(diagnostic['canonical_assignment_valid']) and not raw_fields['errors'],
                optimal=diagnostic['optimal_flag_reproduced'],native_infeasible=diagnostic['native_infeasible_flag_reproduced'])
            raw=native.capture._make(native.capture.GridSolveEvidence,**raw_fields)
            witness,exact,lock,failures=(_reference_audit_stage(frame,disclosure,before,index,frozen,raw,selector)
                if lane.role=='Rref' else _actual_audit_stage(frame,disclosure,before,power,index,frozen,raw,selector))
            if raw.lower is None or raw.upper is None or raw.objective is None:
                failures.append('stage_missing_finite_bounds')
            else:
                lower,upper,objective=map(_finite,(raw.lower,raw.upper,raw.objective));gap=upper-lower
                if (lower<0 or upper<0 or objective<0 or gap<0 or lower>objective
                        or abs(upper-objective)>min(specification.feasibility_tolerance,1e-9)
                        or gap>selector.absolute_gap_mw or gap/max(abs(upper),1e-12)>selector.relative_gap):
                    failures.append('stage_gap_or_objective_gate')
            if failures or witness is None or not witness.physical_assignment_valid:
                raise ValueError('physical/lock/gap audit failed:'+repr(failures))
            diagnostics.append((index,labels[index],diagnostic['model_structure_identity'],float(exact),float(lock)))
            frozen+=(canonical,)
        except Exception as error:
            if index!=len(records)-1:
                raise ValueError('failed stage has forbidden suffix records') from error
            errors.append(f'{index}:{type(error).__name__}:{error}');break
        check()
    check()
    candidate=request=None
    if not errors and len(frozen)==len(labels):
        carry=witness.physical_witness.next_carry if lane.role=='Rref' else witness.next_carry
        values=dict(raw.loaded_values)
        if carry.generation_mw!=tuple((g.uid,values[f'generation[{g.uid}]']) for g in frame.info.network.units):
            raise ValueError('final selected generation differs from physical carry')
        request=witness.candidate_grid_request_exact if lane.role=='Rref' else None
        candidate=_owned(SelectionCandidate,physical_carry=carry,policy_identity=expected_policy_identity,
            previous_selection_identity=before.identity,
            selection_identity=_digest(SCHEMA,expected_identity,expected_policy_identity,frozen,carry,request))
    elif not errors:errors.append('incomplete_stage_chain')
    return _owned(ReplayResult,input_identity=expected_identity,policy_identity=expected_policy_identity,
        report_sha256=expected_report_sha256,verified_stages=len(frozen),canonical_lock_hex=tuple(float(x).hex() for x in frozen),
        stage_diagnostics=tuple(diagnostics),status='replayed_numerical_candidate' if candidate is not None else 'unresolved',
        errors=tuple(errors),candidate_request_exact=request,next_candidate=candidate,solver_calls_by_replay=0,
        source_input_binding_verified=False,normal_selection_authenticated=False,
        native_execution_authenticated=False,detached_consumer_authenticated=False,common_publication_verified=False,
        reference_or_actual_ready=False,formal_result=False,security_certified=False,
        exact_lexicographic_certificate=None,infeasibility_certificate=None,causal_certificate=None)


def _reference_audit_stage(frame, disclosure, before, index, frozen, raw, selector):
    info = frame.info
    errors = list(raw.errors)
    witness = None
    exact = None
    lock = None
    if not raw.optimal or raw.solution_count != 1 or raw.calls != 1 or not raw.assignment_valid:
        errors.append('selector_stage_requires_owned_optimal_assignment')
    if raw.loaded_values:
        try:
            values = dict(raw.loaded_values)
            physical = {name: number for name, number in values.items() if not name.startswith('selector_deviation[')}
            witness = _reference_assignment(frame, disclosure, before, physical)
            errors.extend(witness.errors)
            exact = Q(0)
            deviations = []
            actual_deviations = []
            for uid, plan in info.normal.generation_mw:
                d = Q(str(values[f'selector_deviation[{uid}]']))
                actual = abs(Q(str(values[f'generation[{uid}]']))-Q(str(plan)))
                deviations.append(d)
                actual_deviations.append(actual)
                exact = max(exact, -d, actual-d)
            objectives = (Q(str(info.current.dc_baseline_mw))-Q(str(values['reference_power'])),
                sum(actual_deviations, Q(0)), *(Q(str(values[f'generation[{g.uid}]'])) for g in info.network.units))
            lock = Q(0)
            for prior, fixed in zip(objectives, frozen):
                lock = max(lock, abs(prior-Q(str(fixed))))
            if index >= 1:
                lock = max(lock, abs(sum(deviations, Q(0))-sum(actual_deviations, Q(0))))
            if raw.objective is not None:
                lock = max(lock, abs(objectives[index]-Q(str(raw.objective))))
            if exact > Q('1e-6') or lock > Q(str(selector.lock_tolerance_mw)):
                errors.append('selector_exact_lock_or_deviation_violation')
            exact = max(exact, lock)
        except (ValueError, KeyError, OverflowError) as error:
            errors.append(f'selector_projection_audit:{type(error).__name__}:{error}')
    else:
        errors.append('selector_stage_missing_loaded_assignment')
    return witness, exact, lock, errors


def _actual_audit_stage(frame, disclosure, before, power, index, frozen, raw, selector):
    info = frame.info
    errors = list(raw.errors)
    witness = exact = lock = None
    if not raw.optimal or raw.solution_count != 1 or raw.calls != 1 or not raw.assignment_valid:
        errors.append('dispatch_stage_requires_owned_optimal_assignment')
    if raw.loaded_values:
        try:
            values = dict(raw.loaded_values)
            assignment = {name: number for name, number in values.items() if not name.startswith('selector_deviation[')}
            witness = _actual_assignment(frame, disclosure, before, power, assignment)
            errors.extend(witness.errors)
            exact = Q(0)
            deviations, actual_deviations = [], []
            for uid, plan in info.normal.generation_mw:
                d = Q(str(values[f'selector_deviation[{uid}]']))
                actual = abs(Q(str(values[f'generation[{uid}]']))-Q(str(plan)))
                deviations.append(d)
                actual_deviations.append(actual)
                exact = max(exact, -d, actual-d)
            actual_l1 = sum(actual_deviations, Q(0))
            objectives = (actual_l1, *(Q(str(values[f'generation[{g.uid}]'])) for g in info.network.units))
            lock = abs(sum(deviations, Q(0))-actual_l1)
            for prior, fixed in zip(objectives, frozen):
                lock = max(lock, abs(prior-Q(str(fixed))))
            if raw.objective is not None:
                lock = max(lock, abs(objectives[index]-Q(str(raw.objective))))
            if exact > Q('1e-6') or lock > Q(str(selector.lock_tolerance_mw)):
                errors.append('dispatch_exact_lock_or_deviation_violation')
            exact = max(exact, lock)
        except (ValueError, KeyError, OverflowError) as error:
            errors.append(f'dispatch_projection_audit:{type(error).__name__}:{error}')
    else:
        errors.append('dispatch_stage_missing_loaded_assignment')
    return witness, exact, lock, errors
