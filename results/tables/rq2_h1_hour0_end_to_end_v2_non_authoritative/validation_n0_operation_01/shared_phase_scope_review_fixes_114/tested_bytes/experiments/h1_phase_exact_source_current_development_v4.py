"""Operation-owned exact source composition with honest execution receipts.

The unchanged v2 core performs every original source/registry observation.
Its objects remain private compatibility intermediates. New public objects use
new audits; predecessor execution metadata never describes this call's work.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from pathlib import Path
import json
import sys
import types

from experiments import h1_phase_exact_source_current_development_v2 as predecessor
from experiments import h1_operation_historical_witness_development_v3 as witness

normal,io=predecessor.normal,predecessor.io
SCHEMA='h1_phase_exact_source_current_development_v4'
_EXECUTION_FIELDS=('historical_verifier_schema','historical_verifier_identity',
    'full_numerical_hour_replays','fresh_byte_context_revalidations','recomputed_on_revalidation')


def implementation_identity():
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),
        predecessor.implementation_identity(),witness.verifier_identity()]))


@dataclass(frozen=True,init=False)
class ExactSourceCurrent(normal._Owned):
    prepared_current: predecessor.origin_join.PreparedCurrent
    workload_exact: Q
    source_cfe_at_alpha_one_exact: Q
    exogenous_scientific_payload: bytes
    source_observation_identity: str
    source_projection_audit_payload: bytes

    @property
    def exogenous_scientific_identity(self):return io.digest(self.exogenous_scientific_payload)

    @property
    def source_projection_audit_identity(self):return io.digest(self.source_projection_audit_payload)


@dataclass(frozen=True,init=False)
class CommonSourceBundle(normal._Owned):
    current: ExactSourceCurrent
    historical: witness.VerifiedHistoricalEnvelope
    decision: normal.H1CurrentInformation
    audit_payload: bytes
    verification_execution_payload: bytes


def _scientific_audit(compatibility,own):
    raw=compatibility.source_projection_audit_payload
    value=json.loads(raw)
    if io.encode(value)!=raw or value['schema']!=predecessor.SCHEMA:
        raise ValueError('canonical predecessor source compatibility audit required')
    if (value['implementation_identity']!=predecessor.implementation_identity()
            or value['full_numerical_hour_replays']!=4
            or value['fresh_byte_context_revalidations']!=4
            or value['recomputed_on_revalidation'] is not False):
        raise ValueError('predecessor compatibility projection metadata differs')
    result={key:item for key,item in value.items() if key not in _EXECUTION_FIELDS}
    result.update(schema=SCHEMA,implementation_identity=own,
        predecessor_compatibility=dict(compatibility_payload_scope='predecessor_projection_metadata_only',
            compatibility_counts_describe_actual_execution=False,
            schema=predecessor.SCHEMA,implementation_identity=predecessor.implementation_identity(),
            payload_sha256=io.digest(raw),payload=value))
    return io.encode(result)


def prepare_common_bundle(arm,*,expected_registry_identity):
    """Only the original authenticated arm slot can enter the protected core."""
    if type(arm) is not witness.ArmWitness:
        raise TypeError('exact operation-owned historical arm required')
    try:
        _FIXED(full=True);arm._check()
        ticket=arm._start();own=implementation_identity()
        root,arm_id,binding_pin,terminal_pin,hours,reuse=arm._fixed_declaration
        io.pin(expected_registry_identity)
        with predecessor.historical.history.replay.guard.solver_calls_forbidden():
            baseline=witness.prior_witness._dispatch_view(sys.modules[__name__])
            old_identity=predecessor.historical.verifier_identity()
            verifier_identity=witness.verifier_identity()
            prefix=[0]

            def check():
                _FIXED();arm._check()
                if (witness.prior_witness._dispatch_view(sys.modules[__name__])!=baseline
                        or implementation_identity()!=own or witness.verifier_identity()!=verifier_identity
                        or predecessor.historical.verifier_identity()!=old_identity):
                    raise ValueError('operation exact-source verification context changed')
                return old_identity

            def replay(root_,**arguments):
                if prefix[0] not in (0,1) or root_!=root or arm._ticket is not ticket:
                    raise ValueError('owned exact-source independent prefix route required')
                index=prefix[0]
                result=witness._replay_prefix(root_,**arguments,
                    _operation=arm,_ticket=ticket,_prefix_index=index)
                prefix[0]+=1
                return result

            check()
            compatibility=predecessor._prepare(root,
                expected_binding_sha256=binding_pin,expected_terminal_sha256=terminal_pin,
                completed_hours=hours,expected_registry_identity=expected_registry_identity,
                _check=check,_replay=replay,_common_bundle=True)
            check()
            if type(compatibility) is not predecessor.CommonSourceBundle or prefix[0]!=2:
                raise ValueError('complete original exact-source core result required')
            full=sum(row[3] for row in arm._pending)
            fresh=sum(row[4] for row in arm._pending)
            historical_execution=arm._execution(compatibility.decision,compatibility.audit_payload,
                verifier_identity,full,fresh)
            historical=witness.VerifiedHistoricalEnvelope(compatibility.decision,
                compatibility.audit_payload,verifier_identity,full,fresh,historical_execution,
                _token=witness._ENVELOPE_TOKEN,_operation=arm,_ticket=ticket)
            audit=_scientific_audit(compatibility.current,own)
            original=compatibility.current.prepared_current
            prepared=normal._owned(predecessor.origin_join.PreparedCurrent,
                decision=original.decision,frame=original.frame,source_origin=original.source_origin,
                source_action=original.source_action,audit_payload=audit)
            current=normal._owned(ExactSourceCurrent,prepared_current=prepared,
                workload_exact=compatibility.current.workload_exact,
                source_cfe_at_alpha_one_exact=compatibility.current.source_cfe_at_alpha_one_exact,
                exogenous_scientific_payload=compatibility.current.exogenous_scientific_payload,
                source_observation_identity=compatibility.current.source_observation_identity,
                source_projection_audit_payload=audit)
            execution=io.encode(dict(schema=SCHEMA,active_validation_identity=own,
                active_historical_verifier_identity=verifier_identity,
                protected_core_identity=predecessor.implementation_identity(),
                predecessor_compatibility_counts_describe_actual_execution=False,
                historical_execution=json.loads(historical_execution),
                historical_envelope_identity=historical.envelope_identity,
                exact_source_audit_sha256=io.digest(audit),
                prepared_current_audit_sha256=io.digest(prepared.audit_payload),
                historical_projection_sha256=io.digest(historical.audit_payload),
                full_numerical_hour_replays=full,
                within_prefix_revalidations=4 if full else 0,
                cross_common_numerical_proof_reuses=0 if full else fresh,
                context_evaluations=16,registry_preparations=2,
                production_handoff_integrated=False,formal_result=False,
                resource_admission=False,native_execution_authorized=False))
            result=normal._owned(CommonSourceBundle,current=current,historical=historical,
                decision=historical.decision,audit_payload=historical.audit_payload,
                verification_execution_payload=execution)
            check()
            if (result.current.prepared_current.audit_payload!=result.current.source_projection_audit_payload
                    or any(key in json.loads(audit) for key in _EXECUTION_FIELDS)):
                raise ValueError('new source audit exposes predecessor work counts')
            arm._finish(ticket,historical.decision,historical.audit_payload,envelope=historical)
            arm._session._record_source(arm,result)
            check();_FIXED(full=True)
            return result
    except BaseException as error:
        _POISON(arm,error)
        raise


def _install():
    module=sys.modules[__name__]
    expected=[]
    owner_type=witness.ArmWitness
    original_poison=owner_type._poison
    poison_call=types.FunctionType(original_poison.__code__,original_poison.__globals__,
        original_poison.__name__,original_poison.__defaults__,original_poison.__closure__)
    def poison(owner,error):
        if type(owner) is owner_type:
            try:poison_call(owner,error)
            except BaseException as failure:error.add_note('operation exact-source poison: '+repr(failure))
    module._POISON=poison
    # Include the entire original guard inventory plus original private core and
    # public entries. The full project dispatch additionally covers every old
    # module edge, function code/default, class method, protocol and source file.
    owners=(module,predecessor,predecessor.historical,
        predecessor.source,predecessor.registry,predecessor.origin_join,
        predecessor.origin_join.predecessor,normal,predecessor.physical,io,json,
        predecessor.source.h1.workload_projection,predecessor.historical.old,
        predecessor.historical.binding.replay,predecessor.historical.history.prior,
        predecessor.historical.history.replay,
        predecessor.historical.history.prior.Rq2SolverSpec,
        predecessor.historical.history.replay.H1HourReplayLimits,
        predecessor.historical.history.replay.guard,witness.prior_witness,
        predecessor.historical.binding,ExactSourceCurrent,CommonSourceBundle)
    for owner in owners:
        for name,value in tuple(vars(owner).items()):
            if isinstance(value,(types.FunctionType,types.ModuleType,type,property,staticmethod,classmethod)):
                identity=(value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)) if type(value) is types.FunctionType else None
                expected.append((owner,name,value,identity))
    dispatch=witness.prior_witness._dispatch_view
    baseline=None

    def fixed(full=False):
        if (module._FIXED is not fixed or module._POISON is not poison or any(vars(owner).get(name) is not value
                or identity is not None and (value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))!=identity
                for owner,name,value,identity in expected)):
            raise ValueError('definition-time operation exact-source dispatch changed')
        if full:
            with predecessor.historical.history.replay.guard.solver_calls_forbidden():observed=dispatch(module)
            if observed!=baseline:
                raise ValueError('definition-time operation exact-source project/source view changed')
    module._FIXED=fixed
    with predecessor.historical.history.replay.guard.solver_calls_forbidden():baseline=dispatch(module)
    return fixed


_FIXED=_install()
