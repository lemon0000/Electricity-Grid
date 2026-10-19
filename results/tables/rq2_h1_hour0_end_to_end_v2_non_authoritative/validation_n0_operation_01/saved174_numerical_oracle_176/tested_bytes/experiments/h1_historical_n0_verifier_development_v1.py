"""Versioned N0 historical revalidation with explicit predecessor projection.

The audit payload is a scientific projection in the predecessor schema; the
outer envelope identifies this verifier and never claims old execution identity.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
import json
import sys
import types
from experiments import h1_phase_historical_controller_development_v1 as legacy
from experiments import h1_historical_hour_witness_development_v1 as witness

old,history,current=legacy.old,legacy.history,legacy.current
io,binding,bridge,base=legacy.io,legacy.binding,legacy.bridge,legacy.base
SCHEMA=legacy.SCHEMA
_observe,_observe_sources,_observe_prefix=legacy._observe,legacy._observe_sources,legacy._observe_prefix
_obligation_inventory=legacy._obligation_inventory
implementation_identity=legacy.implementation_identity
VERIFIER_SCHEMA='h1_historical_n0_verifier_development_v1'
_ENVELOPE_TOKEN=object()


def verifier_identity():
    return io.digest(io.encode([VERIFIER_SCHEMA,io.digest(Path(__file__).read_bytes()),
        witness.implementation_identity(),legacy.implementation_identity()]))


@dataclass(frozen=True,init=False)
class VerifiedHistoricalEnvelope(witness._PrivateResult):
    decision: current.H1CurrentInformation
    audit_payload: bytes
    verifier_identity: str
    predecessor_schema: str
    full_numerical_hour_replays: int
    fresh_byte_context_revalidations: int
    recomputed_on_revalidation: bool

    def __init__(self,decision,audit_payload,verifier_identity,predecessor_schema,
            full_numerical_hour_replays,fresh_byte_context_revalidations,*,_token=None):
        if _token is not _ENVELOPE_TOKEN:raise TypeError('owned historical construction required')
        if type(decision) is not current.H1CurrentInformation or type(audit_payload) is not bytes:
            raise TypeError('exact historical decision and audit required')
        audit=json.loads(audit_payload)
        if (io.encode(audit)!=audit_payload or predecessor_schema!=legacy.SCHEMA
                or audit['schema']!=predecessor_schema or audit['implementation']!=legacy.implementation_identity()
                or audit['decision_identity']!=decision.decision_identity
                or verifier_identity!=globals()['verifier_identity']()
                or type(full_numerical_hour_replays) is not int or full_numerical_hour_replays!=4
                or type(fresh_byte_context_revalidations) is not int or fresh_byte_context_revalidations!=4
                or any(audit[k] is not False for k in ('policy_visible','common_prefix_publication_verified',
                    'detached_consumer_authenticated','reference_or_actual_ready','formal_execution_ready',
                    'formal_result','resource_admission','native_execution_authorized'))):
            raise ValueError('historical envelope fields differ')
        io.pin(verifier_identity)
        for name,value in (('decision',decision),('audit_payload',audit_payload),
                ('verifier_identity',verifier_identity),('predecessor_schema',predecessor_schema),
                ('full_numerical_hour_replays',full_numerical_hour_replays),
                ('fresh_byte_context_revalidations',fresh_byte_context_revalidations),
                ('recomputed_on_revalidation',False)):
            object.__setattr__(self,name,value)

    @property
    def audit_identity(self):return io.digest(self.audit_payload)


def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):
    own=verifier_identity()
    decision,audit=_projection(root,expected_binding_sha256=expected_binding_sha256,
        expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)
    if verifier_identity()!=own:raise ValueError('historical verifier changed during preparation')
    return VerifiedHistoricalEnvelope(decision,audit,own,legacy.SCHEMA,4,4,_token=_ENVELOPE_TOKEN)


def _replay_prefix(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,_observed=None):
    if type(completed_hours) is not int or completed_hours != 1: raise ValueError('N0 witness only')
    old.additional_content_bound(completed_hours)
    root=history.chunks.base.local._path(Path(root).absolute())
    own=implementation_identity();old_identity=old.implementation_identity()
    directory=root/'obligation_non_authoritative';clock=root/'clock_bridge_non_authoritative'
    observed={} if _observed is None else _observed
    leases=[];views=observed.setdefault('views',{});topology=observed.setdefault('topology',{})
    obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})
    captured={};evidence={}
    def read(path,pin):
        before=history.chunks.base.local._file_identity(path)
        value,view=base.entry.read(path,pin,old.CAP)
        if history.chunks.base.local._file_identity(path)!=before:raise ValueError('historical evidence replaced')
        if path in views and views[path]!=(old.CAP,view):raise ValueError('retained evidence changed')
        views[path]=(old.CAP,view)
        evidence[str(path.relative_to(root))]=pin
        return value
    def inventory():
        for lease in leases:lease.check()
        _obligation_inventory(directory,completed_hours,obligation_names)
        for path,base_names,pattern,low in (
            (root,{'execution.lock','source_parent_non_authoritative','obligation_non_authoritative','clock_bridge_non_authoritative'},r'job_([0-9]{3})_non_authoritative',0),
            (clock,{'execution.lock','binding.json'},r'([0-9]{3})',0),
        ):
            found=history._inventory(path,base_names,pattern=pattern,low=low,high=191,directories=True,retained=topology)
            if not set(range(completed_hours))<=found:raise ValueError('historical Job/clock prefix missing')
    reader=None;scope=None
    try:
        for path in (root,directory,clock,root/'source_parent_non_authoritative'):
            lease=history.prior.ReadView(path);leases.append(lease)
            _observe(identities,'lease '+str(path),(lease.directory_identity,lease.lock_identity))
        scope=witness._HourScope(root,leases,caller=sys.modules[__name__])
        inventory()
        header=read(directory/'binding.json',expected_binding_sha256)
        declaration=header['parent_declaration'];budget=base.old.process.TaskProcessBudget(**header['budget'])
        budget.__post_init__()
        _observe_sources(identities,declaration)
        resolver=binding.open_manifest()
        node=binding.precheck(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        if not io.same(header,dict(schema=old.SCHEMA,implementation=old_identity,parent_declaration=declaration,
                parent_identity=io.digest(io.encode(declaration)),manifest_sha256=resolver.identity,
                family=header['family'],ordinal=header['ordinal'],hours=192,budget=asdict(budget),
                clock_binding_sha256=io.pin(header['clock_binding_sha256']),**old.FLAGS)):
            raise ValueError('historical obligation header differs')
        if declaration['hours']!=192 or Path(declaration['root'])!=root/'source_parent_non_authoritative':
            raise ValueError('historical obligation parent path/horizon differs')
        enrollment=binding.prevalidate_enrollment(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        records={};next_pin=io.pin(expected_terminal_sha256)
        for hour in reversed(range(completed_hours)):
            terminal=read(directory/f'{hour:03d}.terminal.json',next_pin)
            link=read(directory/f'{hour:03d}.job.json',terminal['job_link_sha256'])
            joined=read(directory/f'{hour:03d}.binding.json',link['obligation_binding_sha256'])
            if (not io.same(link,dict(schema=old.SCHEMA,obligation_binding_sha256=link['obligation_binding_sha256'],job_pins=link['job_pins'],**old.FLAGS))
                    or not io.same(terminal,dict(schema=old.SCHEMA,previous_sha256=terminal['previous_sha256'],
                        job_link_sha256=terminal['job_link_sha256'],clock_terminal_sha256=terminal['clock_terminal_sha256'],
                        parent_head=terminal['parent_head'],parent_anchor_sha256=terminal['parent_anchor_sha256'],
                        relative_hour=hour,controller_live_join_checked=True,**old.FLAGS))):
                raise ValueError('historical obligation chain differs')
            records[hour]=terminal,link,joined;next_pin=terminal['previous_sha256']
        if next_pin!=expected_binding_sha256:raise ValueError('historical obligation genesis differs')

        class Reader(legacy.HistoricalTimedSnapshot):
            def _outcome(self,hour,intent_head,result):
                return witness.outcome(self,hour,intent_head,result,scope=scope)
            def _child(self,hour,packet,intent_head,lineage,*,expected_head,create=False):
                terminal,link,joined=records[hour]
                request=read(root/f'job_{hour:03d}_non_authoritative'/'request.json',link['job_pins']['request.json'])
                if not io.same(request['budget'],header['budget']):raise ValueError('historical episode budget differs')
                expected=old._historical_binding(packet,request,node,enrollment)
                if not io.same(joined,dict(schema=old.SCHEMA,implementation=old_identity,obligation=expected,
                        expected_worker_request_sha256=link['job_pins']['request.json'],**old.FLAGS)):
                    raise ValueError('historical obligation packet/request differs')
                ct=read(clock/f'{hour:03d}'/'terminal.json',terminal['clock_terminal_sha256'])
                if (ct['job_pins']!=link['job_pins'] or ct['outcome_head']!=terminal['parent_head']
                        or ct['outcome_anchor_sha256']!=terminal['parent_anchor_sha256']):
                    raise ValueError('historical obligation clock/outcome differs')
                witness.inspect_bridge(clock,hour,packet,self._spec,self._limits,scope=scope,binding_pin=header['clock_binding_sha256'],
                    intent_pin=ct['intent_sha256'],terminal_pin=terminal['clock_terminal_sha256'])
                if create is not False: raise ValueError('historical reference is read only')
                return witness.ChildReference(self._root/f'hour_{hour:03d}_non_authoritative',
                    self._root.parent/f'job_{hour:03d}_non_authoritative',packet,self._spec,self._limits,
                    parent_declaration=self._declaration,intent_head=intent_head,lineage=lineage,
                    expected_head=expected_head,scope=scope)

            def _after(self,packet,result):
                if type(result) is not witness.RevalidatedChildInspection or result.status!='accepted':
                    raise ValueError('accepted timed child required')
                count=len(binding.replay.native.model_api.stage_order(packet.inputs))
                if (result.stored_reports!=count or type(result.projection) is not current.parent.Projection
                        or result.projection.projection_identity!=io.digest(io.encode([current.parent.CHILD_SCHEMA,io.digest(result.projection.payload)]))):
                    raise ValueError('complete normal projection differs')
                after=witness.after(self,packet,result,scope=scope)
                scope.promote(result)
                if packet.relative_hour==completed_hours-1:captured.update(packet=packet,result=result,after=after,count=count)
                return after

        terminal=records[completed_hours-1][0]
        with history.replay.guard.solver_calls_forbidden():
            first_request=read(root/'job_000_non_authoritative'/'request.json',records[0][1]['job_pins']['request.json'])
            stages=first_request['input_receipt']['stage_slots']
            if type(stages) is not int or not 1<=stages<=232:raise ValueError('bounded stage count required')
            _observe_prefix(identities,root,completed_hours,stages)
            reader=Reader(declaration,completed_hours=completed_hours,expected_parent_identity=header['parent_identity'],
                expected_parent_head=terminal['parent_head'],expected_anchor_record=terminal['parent_anchor_sha256'])
            state=reader.inspect()
            if (state.completed_hours!=completed_hours or state.status!=('complete' if completed_hours==192 else 'ready')
                    or state.head!=terminal['parent_head'] or not captured):
                raise ValueError('historical accepted controller prefix differs')
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            result=dict(completed_hours=completed_hours,parent_head=state.head,
                evidence_identity=io.digest(io.encode(evidence)),historical_parent_prefix_verified=True,
                historical_obligation_prefix_verified=True,historical_job_clock_prefix_verified=True,
                suffix_chain_verified=False,current_latest_parent_verified=False,current_latest_obligation_verified=False,
                live_release_authenticated=False,live_handoff_authenticated=False,writer_lock_authenticated=False,
                persistent_lane_owner_implemented=False,detached_consumer_authenticated=False,
                common_prefix_publication_verified=False,reference_or_actual_ready=False,**old.FLAGS)
            if (scope.full_calls,scope.revalidation_calls)!=(2,2): raise ValueError('complete prefix verification count differs')
            return result,captured,header
    finally:
        try:
            if scope is not None:scope.close()
        finally:
            try:
                if reader is not None:reader.close()
            finally:
                for lease in reversed(leases):lease.close()


def _projection(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):
    """Current-only information rebuilt twice from externally pinned N history."""
    own=implementation_identity()
    args=dict(expected_binding_sha256=expected_binding_sha256,expected_terminal_sha256=expected_terminal_sha256,
        completed_hours=completed_hours)
    observed={}
    first,captured,header=_replay_prefix(root,**args,_observed=observed)
    packet,result,after=captured['packet'],captured['result'],captured['after']
    decision=current._decision(packet,after)
    projection=current.json.loads(result.projection.payload)
    audit=io.encode(dict(schema=SCHEMA,implementation=own,decision_identity=decision.decision_identity,
        parent_declaration=header['parent_declaration'],controller_header_sha256=expected_binding_sha256,
        controller_terminal_sha256=expected_terminal_sha256,normal_input_identity=packet.input_identity,
        packet_audit_identity=packet.audit_identity,source_timestamp=packet.source_timestamp,
        source_time_basis=packet.source_time_basis,child_head=result.head,child_archive_identity=result.archive_identity,
        projection_identity=result.projection.projection_identity,projection_payload_sha256=io.digest(result.projection.payload),
        normal_request_key=binding.replay.request_key(packet,history.prior.Rq2SolverSpec(**header['parent_declaration']['specification']),
            history.replay.H1HourReplayLimits(**header['parent_declaration']['limits'])),
        normal_before=asdict(packet.before),normal_after=asdict(after),canonical_locks=projection['value']['canonical_locks'],
        completed_stages=captured['count'],policy_visible=False,historical_controller=first,
        common_prefix_publication_verified=False,detached_consumer_authenticated=False,
        reference_or_actual_ready=False,formal_execution_ready=False,formal_result=False,resource_admission=False,
        native_execution_authorized=False))
    if len(audit)>binding.CAP:raise ValueError('historical information audit byte cap')
    second,fresh,fresh_header=_replay_prefix(root,**args,_observed=observed)
    if (first!=second or header!=fresh_header or decision.decision_bytes!=current._decision(fresh['packet'],fresh['after']).decision_bytes
            or implementation_identity()!=own):
        raise ValueError('historical current prefix changed during preparation')
    return decision,audit


def _guard_prepare(operation):
    """Pin this verifier's dispatch before any scope can accept a baseline."""
    module=sys.modules[__name__]
    names=('old','history','current','io','binding','bridge','base','legacy','witness',
        '_observe','_observe_sources','_observe_prefix','_obligation_inventory',
        'implementation_identity','verifier_identity','_replay_prefix','_projection',
        'VerifiedHistoricalEnvelope','_ENVELOPE_TOKEN','SCHEMA','VERIFIER_SCHEMA')
    bindings=tuple((name,getattr(module,name)) for name in names)
    codes=tuple((value,value.__code__) for _,value in bindings if type(value) is types.FunctionType)
    operation_code=operation.__code__
    def check():
        if (module.prepare is not guarded or operation.__code__ is not operation_code
                or any(getattr(module,name) is not value for name,value in bindings)
                or any(value.__code__ is not code for value,code in codes)):
            raise ValueError('historical verifier dispatch changed')
    def guarded(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):
        check()
        result=operation(root,expected_binding_sha256=expected_binding_sha256,
            expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)
        check()
        return result
    return guarded


prepare=_guard_prepare(prepare)
