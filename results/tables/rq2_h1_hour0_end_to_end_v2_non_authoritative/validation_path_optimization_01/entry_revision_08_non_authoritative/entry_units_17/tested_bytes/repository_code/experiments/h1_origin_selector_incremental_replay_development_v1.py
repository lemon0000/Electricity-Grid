"""One-call selector prefix reuse with fresh, solver-free metadata bookends.

This is detached development evidence. A VerifiedPrefix is private working
state, never an execution credential, persistent owner or accepted checkpoint.
Legacy numerical mathematics and saved-record identities remain unchanged.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType
from weakref import WeakKeyDictionary

from experiments import h1_origin_selector_replay_development_v1 as legacy

SCHEMA = 'h1_origin_selector_incremental_replay_development_v1'


class VerifiedPrefix:
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('verified prefix requires numerical replay')

    def __copy__(self):
        raise TypeError('verified prefix cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('verified prefix cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('verified prefix cannot be serialized')


def _registry():
    states = WeakKeyDictionary()

    def put(state):
        token = object.__new__(VerifiedPrefix)
        states[token] = state
        return token

    def get(token):
        if type(token) is not VerifiedPrefix or token not in states:
            raise ValueError('private verified prefix required')
        state = states[token]
        if state['owner'] != (os.getpid(), get_ident()):
            raise ValueError('verified prefix process/thread changed')
        return state

    return put, get


_put, _get = _registry()


def implementation_identity(specification, limits):
    if SCHEMA != 'h1_origin_selector_incremental_replay_development_v1':
        raise ValueError('incremental replay schema drift')
    return legacy._digest(SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(legacy.__file__).read_bytes()).hexdigest(),
        legacy.implementation_identity(specification, limits))


def _bindings():
    # Detect rebinding and in-place function changes across this operation.
    # This is not a sandbox against arbitrary Python reflection or unseen ABA.
    modules = (sys.modules[__name__], legacy, legacy.native,
        legacy.native.capture, legacy.physical, legacy.physical.old)
    rows = []
    for module in modules:
        for name, function in sorted(vars(module).items()):
            if type(function) is FunctionType:
                closure = tuple(id(c.cell_contents) for c in (function.__closure__ or ()))
                rows.append((module.__name__, name, function, function.__code__,
                    repr(function.__defaults__), repr(function.__kwdefaults__), closure))
    return tuple(rows)


def _check(frame, disclosure, before, args, identity, policy):
    if (legacy.input_identity(frame, disclosure, before, lane=args['lane'], power=args.get('power')) != identity
            or legacy.policy_identity(args['lane'], args['selector'], args['specification'], args['limits']) != policy
            or before.policy_identity != policy):
        raise ValueError('selector input/policy/predecessor drift')


def _inventory(frame, disclosure, before, records, pins, args, identity, policy):
    legacy.physical._pin(identity)
    legacy.physical._pin(policy)
    labels = legacy.stage_labels(frame, args['lane'])
    limits = args['limits']
    legacy._configuration(args['lane'], args['selector'], args['specification'], limits, len(labels))
    _check(frame, disclosure, before, args, identity, policy)
    if (type(records) is not tuple or type(pins) is not tuple
            or len(records) != len(pins) or len(records) > len(labels)):
        raise ValueError('bounded record tuple and complete external pin inventory required')
    total = 0
    for data, pin in zip(records, pins, strict=True):
        legacy.physical._pin(pin)
        if type(data) is not bytes or len(data) > limits.max_record_bytes or sha256(data).hexdigest() != pin:
            raise ValueError('record bytes/size/external pin mismatch')
        total += len(data)
    if total > limits.max_total_bytes:
        raise ValueError('aggregate replay byte cap')
    return labels


def _observe(frame, disclosure, before, records, pins, args, identity, policy, result):
    """Rebuild each old context and metadata, without loading its assignment."""
    labels = _inventory(frame, disclosure, before, records, pins, args, identity, policy)
    locks = tuple(float.fromhex(x) for x in result.canonical_lock_hex)
    api = legacy.native.capture
    spec, limits = args['specification'], args['limits']
    versions = (legacy.native.version('Pyomo'),
        legacy.native.version('highspy' if spec.name == 'highs' else 'gurobipy'))
    options = tuple(sorted(api.solver_options(spec).items()))
    contexts = []
    # Include the next-stage request context as well as every old prefix stage.
    for index in range(len(records) + 1):
        frozen = locks[:index]
        context = legacy._context(frame, disclosure, before, index=index, frozen=frozen, **args)
        model = legacy.build_development_stage(frame, disclosure, before,
            lane=args['lane'], power=args.get('power'), index=index,
            frozen=frozen, expected_identity=identity)
        structure, snapshot, scale = api._structure(model), api._snapshot(model), api.model_scale(model)
        if (structure != context['model_structure_identity'] or scale.variables > limits.max_variables
                or scale.constraints > limits.max_constraints):
            raise ValueError('fresh selector model metadata differs')
        if index < len(records):
            decoded = json.loads(records[index], object_pairs_hook=legacy.native._unique_object,
                parse_constant=legacy.native._reject_constant)
            raw = legacy.native._tuples(decoded['raw'])
            if (legacy.native._encoded({k: decoded[k] for k in context}) != legacy.native._encoded(context)
                    or legacy.native._encoded((raw['structures'], raw['preload_values'], raw['versions'], raw['options']))
                    != legacy.native._encoded(((structure,) * 3, snapshot, (versions,) * 2, (options,) * 2))
                    or legacy.native._encoded(raw['initial_values']) != legacy.native._encoded(snapshot)
                    or (raw['variables'], raw['constraints']) != (scale.variables, scale.constraints)
                    or versions[1] != spec.expected_package_version):
                raise ValueError('verified prefix context/runtime metadata drift')
        contexts.append((context, snapshot, scale.variables, scale.constraints))
    _check(frame, disclosure, before, args, identity, policy)
    return legacy.native._encoded(dict(schema=SCHEMA,
        implementation=implementation_identity(spec, limits), frame=frame,
        disclosure=disclosure, before=before, args=args, labels=labels,
        records=pins, record_sizes=tuple(map(len, records)), total_bytes=sum(map(len, records)),
        replay=result, contexts=contexts, versions=versions, options=options,
        thresholds=(legacy.physical.TOLERANCE, legacy.physical.old.TOLERANCE)))


def verify_prefix(frame, disclosure, before, records, *, expected_identity,
        expected_policy_identity, expected_report_sha256, **args):
    bindings = _bindings()
    replay = legacy.replay_development_records(frame, disclosure, before, records, **args,
        expected_identity=expected_identity, expected_policy_identity=expected_policy_identity,
        expected_report_sha256=expected_report_sha256)
    if replay.verified_stages != len(records) or replay.errors != ('incomplete_stage_chain',):
        raise ValueError('accepted incomplete selector prefix required')
    observation = _observe(frame, disclosure, before, records, expected_report_sha256,
        args, expected_identity, expected_policy_identity, replay)
    if _bindings() != bindings:
        raise ValueError('selector replay function bindings changed')
    return _put(dict(owner=(os.getpid(), get_ident()), phase='verified', bindings=bindings,
        observation=observation, replay=replay, identity=expected_identity,
        policy=expected_policy_identity, pins=expected_report_sha256))


def prefix_locks(prefix):
    state = _get(prefix)
    if state['phase'] != 'verified':
        raise ValueError('verified prefix already consumed')
    return tuple(float.fromhex(x) for x in state['replay'].canonical_lock_hex)


def _fresh(state, frame, disclosure, before, records, args):
    if _bindings() != state['bindings']:
        raise ValueError('selector replay function bindings changed')
    observed = _observe(frame, disclosure, before, records, state['pins'], args,
        state['identity'], state['policy'], state['replay'])
    if observed != state['observation'] or _bindings() != state['bindings']:
        raise ValueError('verified selector prefix changed')
    return tuple(float.fromhex(x) for x in state['replay'].canonical_lock_hex)


def revalidate_prefix(prefix, frame, disclosure, before, records, **args):
    state = _get(prefix)
    if state['phase'] not in ('verified', 'appended'):
        raise ValueError('verified prefix unavailable after failure')
    previous = state['phase']
    state['phase'] = 'checking'
    try:
        if _bindings() != state['bindings']:
            raise ValueError('selector replay function bindings changed')
        locks = _fresh(state, frame, disclosure, before, records, args)
        if _bindings() != state['bindings']:
            raise ValueError('selector replay function bindings changed')
        state['phase'] = previous
        return locks
    except BaseException:
        state['phase'] = 'failed'
        raise


def _replay_one(frame, disclosure, before, data, *, index, labels, frozen, identity, args):
    """Mechanical single-stage extraction of the legacy numerical transition."""
    lane, power = args['lane'], args.get('power')
    selector, specification, limits = args['selector'], args['specification'], args['limits']

    def builder():
        return legacy.build_development_stage(frame, disclosure, before, lane=lane, index=index,
            frozen=frozen, expected_identity=identity, power=power)

    decoded = json.loads(data, object_pairs_hook=legacy.native._unique_object, parse_constant=legacy.native._reject_constant)
    if legacy.native._encoded(decoded) != data:
        raise ValueError('canonical saved raw bytes required')
    context = legacy._context(frame, disclosure, before, lane=lane, index=index, frozen=frozen,
        selector=selector, specification=specification, limits=limits, power=power)
    if (type(decoded) is not dict or set(decoded) != set(context) | {'raw', 'canonical_objective_hex'}
            or legacy.native._encoded({k: decoded[k] for k in context}) != legacy.native._encoded(context)):
        raise ValueError('exact stage context/lock envelope mismatch')
    raw_fields = legacy.native._tuples(decoded['raw'])
    purpose = f'{legacy.SCHEMA}:{lane.role}:{index}:{labels[index]}'
    diagnostic = legacy.native._replay(raw_fields, builder, specification, limits, purpose)
    if (not diagnostic['replay_consistent'] or raw_fields['calls'] != 1
            or not diagnostic['canonical_assignment_valid'] or not diagnostic['optimal_flag_reproduced']):
        raise ValueError('complete valid optimal native-record consistency required')
    canonical = diagnostic['recomputed_objective']
    if decoded['canonical_objective_hex'] != float(canonical).hex():
        raise ValueError('stored canonical objective hex differs from replay')
    raw_fields.update(objective=diagnostic['recomputed_objective'],
        maximum_residual=diagnostic['recomputed_maximum_residual'],
        maximum_integrality_violation=diagnostic['recomputed_maximum_integrality_violation'],
        assignment_valid=bool(diagnostic['canonical_assignment_valid']) and not raw_fields['errors'],
        optimal=diagnostic['optimal_flag_reproduced'], native_infeasible=diagnostic['native_infeasible_flag_reproduced'])
    raw = legacy.native.capture._make(legacy.native.capture.GridSolveEvidence, **raw_fields)
    witness, exact, lock, failures = (legacy._reference_audit_stage(frame, disclosure, before, index, frozen, raw, selector)
        if lane.role == 'Rref' else legacy._actual_audit_stage(frame, disclosure, before, power, index, frozen, raw, selector))
    if raw.lower is None or raw.upper is None or raw.objective is None:
        failures.append('stage_missing_finite_bounds')
    else:
        lower, upper, objective = map(legacy._finite, (raw.lower, raw.upper, raw.objective))
        gap = upper - lower
        if (lower < 0 or upper < 0 or objective < 0 or gap < 0 or lower > objective
                or abs(upper - objective) > min(specification.feasibility_tolerance, 1e-9)
                or gap > selector.absolute_gap_mw or gap / max(abs(upper), 1e-12) > selector.relative_gap):
            failures.append('stage_gap_or_objective_gate')
    if failures or witness is None or not witness.physical_assignment_valid:
        raise ValueError('physical/lock/gap audit failed:' + repr(failures))
    diagnostic_row = (index, labels[index], diagnostic['model_structure_identity'], float(exact), float(lock))
    return canonical, diagnostic_row, witness, raw


def _finish(frame, before, *, lane, identity, policy, pins, labels, frozen, diagnostics, errors, witness, raw):
    candidate = request = None
    if not errors and len(frozen) == len(labels):
        carry = witness.physical_witness.next_carry if lane.role == 'Rref' else witness.next_carry
        values = dict(raw.loaded_values)
        if carry.generation_mw != tuple((g.uid, values[f'generation[{g.uid}]']) for g in frame.info.network.units):
            raise ValueError('final selected generation differs from physical carry')
        request = witness.candidate_grid_request_exact if lane.role == 'Rref' else None
        candidate = legacy._owned(legacy.SelectionCandidate, physical_carry=carry, policy_identity=policy,
            previous_selection_identity=before.identity, previous_audit_identity=before.audit_identity,
            selection_identity=legacy._digest(legacy.SCHEMA, identity, policy, frozen, carry.identity, request))
    elif not errors:
        errors.append('incomplete_stage_chain')
    return legacy._owned(legacy.ReplayResult, input_identity=identity, policy_identity=policy,
        report_sha256=pins, verified_stages=len(frozen), canonical_lock_hex=tuple(float(x).hex() for x in frozen),
        stage_diagnostics=tuple(diagnostics), status='replayed_numerical_candidate' if candidate is not None else 'unresolved',
        errors=tuple(errors), candidate_request_exact=request, next_candidate=candidate, solver_calls_by_replay=0,
        source_input_binding_verified=False, normal_selection_authenticated=False,
        native_execution_authenticated=False, detached_consumer_authenticated=False, common_publication_verified=False,
        reference_or_actual_ready=False, formal_result=False, security_certified=False,
        exact_lexicographic_certificate=None, infeasibility_certificate=None, causal_certificate=None)


def append_verified_stage(prefix, frame, disclosure, before, records, new_record, *,
        expected_report_sha256, **args):
    state = _get(prefix)
    if state['phase'] != 'verified':
        raise ValueError('verified prefix already consumed')
    state['phase'] = 'busy'
    try:
        if _bindings() != state['bindings']:
            raise ValueError('selector replay function bindings changed')
        _fresh(state, frame, disclosure, before, records, args)
        combined = records + (new_record,)
        pins = expected_report_sha256
        labels = _inventory(frame, disclosure, before, combined, pins, args, state['identity'], state['policy'])
        if pins[:-1] != state['pins']:
            raise ValueError('verified prefix external pins changed')
        frozen = tuple(float.fromhex(x) for x in state['replay'].canonical_lock_hex)
        diagnostics = list(state['replay'].stage_diagnostics)
        errors = []
        witness = raw = None
        index = len(records)
        try:
            canonical, diagnostic, witness, raw = _replay_one(frame, disclosure, before, new_record,
                index=index, labels=labels, frozen=frozen, identity=state['identity'], args=args)
            frozen += (canonical,)
            diagnostics.append(diagnostic)
        except Exception as error:
            errors.append(f'{index}:{type(error).__name__}:{error}')
        _check(frame, disclosure, before, args, state['identity'], state['policy'])
        result = _finish(frame, before, lane=args['lane'], identity=state['identity'], policy=state['policy'],
            pins=pins, labels=labels, frozen=frozen, diagnostics=diagnostics,
            errors=errors, witness=witness, raw=raw)
        if _bindings() != state['bindings']:
            raise ValueError('selector replay function bindings changed')
        _fresh(state, frame, disclosure, before, records, args)
        state['phase'] = 'appended'
        return result
    except BaseException:
        state['phase'] = 'failed'
        raise
