"""One constructor traversal per independent historical Reader.

DRAFT_NONAUTHORITATIVE. The predecessor and its two-traversal caller remain
unchanged. All predecessor post-observation checks and cleanup are retained.
"""
from dataclasses import asdict, fields
from pathlib import Path
import sys
import time
from types import FunctionType
from uuid import uuid4

from experiments import h1_constructor_rejection_support_development_v1 as support
from experiments import h1_constructor_runtime_guard_development_v1 as runtime
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source as packet_source

from experiments import h1_phase_historical_batch_development_v1 as prior
from experiments import h1_constructor_inspection_capture_development_v1 as capture
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as model

SCHEMA = 'h1_phase_historical_batch_development_v3'
io, binding, bridge, base = prior.io, prior.binding, prior.bridge, prior.base
old, history, current, predecessor = prior.old, prior.history, prior.current, prior.predecessor
HistoricalTimedSnapshot = prior.HistoricalTimedSnapshot
ConstructorInspectionCapture = capture.ConstructorInspectionCapture
MAX_RETAINED_BYTES = prior.MAX_RETAINED_BYTES
retained_size, prefix_evidence = prior.retained_size, prior.prefix_evidence
_observe, _observe_sources, _observe_prefix = prior._observe, prior._observe_sources, prior._observe_prefix
_obligation_inventory = prior._obligation_inventory
# A private closure retains an independent copy even after an exported helper
# alias, code, defaults, closure cell, or its private function graph changes.
_SAFE_CLOSE = runtime.frozen_teardown(support.close_replay)
_RUNTIME = runtime.NamedRuntimeSnapshot(runtime.runtime_roots(model, packet_source, support))
_RUNTIME_CHECK = runtime.NamedRuntimeSnapshot.check


def _make_close_replay(safe_close):
    def close_replay(reader, leases, captured, completed, primary):
        return safe_close(reader, leases, captured, completed, primary)
    return close_replay


_close_replay = _make_close_replay(_SAFE_CLOSE)


def implementation_identity():
    return io.digest(io.encode([SCHEMA, prior.implementation_identity(),
        io.digest(Path(__file__).read_bytes()), io.digest(Path(capture.__file__).read_bytes()),
        io.digest(Path(support.__file__).read_bytes()), io.digest(Path(runtime.__file__).read_bytes())]))


def _function_state(value):
    if type(value) is not FunctionType:
        return None
    return (value.__code__, value.__globals__, value.__defaults__, repr(value.__defaults__),
        value.__kwdefaults__, repr(value.__kwdefaults__), value.__closure__,
        tuple(cell.cell_contents for cell in value.__closure__ or ()))


def _model_dependency_snapshot():
    _check_dependencies()
    value = model._dependencies()
    _check_dependencies()
    if (type(value) is not tuple or len(value) != 2
            or any(type(group) is not tuple for group in value)
            or any(type(pair) is not tuple or len(pair) != 2
                or any(type(item) is not str for item in pair) for group in value for pair in group)
            or tuple(pair[0] for pair in value[0]) != model.SOURCE_DEPENDENCIES
            or tuple(pair[0] for pair in value[1]) != ('python', 'implementation', *model.RUNTIME_DISTRIBUTIONS)):
        raise ValueError('exact normal model dependency snapshot required')
    for _, checksum in value[0]:
        io.pin(checksum)
    return value


def _model_dependencies_unchanged(before):
    if _model_dependency_snapshot() != before:
        raise ValueError('normal model dependencies changed during historical replay')


def _packet_digest(packet):
    names=('network','before','relative_hour','inputs','input_identity','source_timestamp',
           'source_time_basis','workload_projection_payload','audit_identity')
    if (type(packet) is not packet_source.H1CurrentNormal or tuple(f.name for f in fields(packet))!=names
            or type(packet.workload_projection_payload) is not bytes):
        raise ValueError('exact full-packet digest schema required')
    # The original numerical encoder deliberately excludes bytes. Tag and hex
    # this one exact bytes field; every other declared packet field is retained.
    return packet_source._digest(SCHEMA+'/full_packet_hex_v1',packet.network,packet.before,
        packet.relative_hour,packet.inputs,packet.input_identity,packet.source_timestamp,
        packet.source_time_basis,('bytes.hex',packet.workload_projection_payload.hex()),packet.audit_identity)


def _remember_packet(packets, packet, completed_hours):
    if type(packet) is not packet_source.H1CurrentNormal:
        raise ValueError('one exact all-hour packet per chronological N hour required')
    hour=packet.relative_hour
    if (type(hour) is not int
            or hour!=len(packets) or not 0<=hour<completed_hours or hour in packets):
        raise ValueError('one exact all-hour packet per chronological N hour required')
    pin=(packet.input_identity,packet.audit_identity,_packet_digest(packet))
    size=retained_size((packet,pin))
    packets[hour]=(packet,pin)
    return size


def _validate_all_packets(packets, completed_hours):
    if tuple(packets)!=tuple(range(completed_hours)):
        raise ValueError('complete chronological all-hour packet inventory required')
    for hour,(packet,pin) in packets.items():
        packet_source.validate_current(packet)
        if ((packet.input_identity,packet.audit_identity,_packet_digest(packet))!=pin
                or packet.relative_hour!=hour):
            raise ValueError('all-hour packet identity changed during historical replay')


def _finish_replay(close_reader, reader, leases, captured, completed, primary, packets, seen_hours):
    try:
        close_reader(reader,leases,captured,completed,primary)
    finally:
        packets.clear()
        seen_hours.clear()


def _check_dependencies():
    if any(_LOCAL_NAMESPACE.get(name) is not value for name, value in _LOCAL_BINDINGS):
        raise ValueError('historical successor local dependency alias changed')
    for obj, name, value, before in _DEPENDENCIES:
        if getattr(obj, name) is not value:
            raise ValueError('historical successor dependency alias changed')
        after = None if before is None else (value.__code__, value.__globals__, value.__defaults__, repr(value.__defaults__),
            value.__kwdefaults__, repr(value.__kwdefaults__), value.__closure__,
            tuple(cell.cell_contents for cell in value.__closure__ or ()))
        if before is not None and (any(after[i] is not before[i] for i in (0, 1, 2, 4, 6))
                or any(after[i] != before[i] for i in (3, 5))
                or any(a is not b for a, b in zip(after[7], before[7]))):
            raise ValueError('historical successor callable changed')
    for kind, keys, bases, mro in _CLASS_SHAPES:
        if tuple(vars(kind)) != keys or kind.__bases__ is not bases or kind.__mro__ is not mro:
            raise ValueError('historical successor class layout changed')
    if any(vars(kind).get(name) is not value for kind, name, value in _CLASS_VALUES):
        raise ValueError('historical successor class descriptor changed')
    _RUNTIME_CHECK(_RUNTIME)


_DEPENDENCIES = tuple((prior, name, getattr(prior, name), _function_state(getattr(prior, name)))
    for name in ('retained_size', 'prefix_evidence', '_observe', '_observe_sources', '_observe_prefix',
                 '_obligation_inventory', '_close_replay', 'HistoricalTimedSnapshot', 'implementation_identity'))
_CLASS_SHAPES = tuple((kind, tuple(vars(kind)), kind.__bases__, kind.__mro__)
    for kind in (*HistoricalTimedSnapshot.__mro__, ConstructorInspectionCapture)
    if kind.__module__.startswith(('experiments.', 'src.')))
_CLASS_VALUES = tuple((kind, name, value) for kind, _, _, _ in _CLASS_SHAPES
    for name, value in vars(kind).items())
_DEPENDENCIES += tuple((kind, name, getattr(kind, name), _function_state(getattr(kind, name)))
    for kind, _, _, _ in _CLASS_SHAPES for name, value in vars(kind).items()
    if type(value) is FunctionType)
_DEPENDENCIES += ((capture, '_check_definition', capture._check_definition, _function_state(capture._check_definition)),)
_DEPENDENCIES += ((runtime.NamedRuntimeSnapshot, 'check', _RUNTIME_CHECK, _function_state(_RUNTIME_CHECK)),)
_DEPENDENCIES += tuple((sys.modules[__name__], name, globals()[name], _function_state(globals()[name]))
    for name in ('implementation_identity', '_SAFE_CLOSE', '_close_replay',
                 '_model_dependency_snapshot', '_model_dependencies_unchanged',
                 '_packet_digest', '_remember_packet', '_validate_all_packets', '_finish_replay'))
_DEPENDENCIES += tuple((model, name, getattr(model, name), _function_state(getattr(model, name)))
    for name in ('_dependencies', 'normal_input_identity', '_validate', '_number', '_digest', '_encode',
                 '_validate_request', 'version', 'Path', '__file__', 'sha256', 'platform',
                 'SOURCE_DEPENDENCIES', 'RUNTIME_DISTRIBUTIONS', 'CONTRACT', 'TOLERANCE'))
_DEPENDENCIES += tuple((model.platform, name, getattr(model.platform, name), _function_state(getattr(model.platform, name)))
    for name in ('python_version', 'python_implementation'))
_LOCAL_NAMESPACE = globals()
_LOCAL_BINDINGS = tuple((name, _LOCAL_NAMESPACE[name]) for name in (
    'prior', 'capture', 'support', 'runtime', 'packet_source', '_RUNTIME', '_RUNTIME_CHECK', 'io', 'binding', 'bridge', 'base', 'old', 'history', 'current', 'predecessor',
    'HistoricalTimedSnapshot', 'ConstructorInspectionCapture', 'MAX_RETAINED_BYTES', 'retained_size',
    'prefix_evidence', '_observe', '_observe_sources', '_observe_prefix', '_obligation_inventory',
    '_close_replay', '_function_state', '_check_dependencies', 'SCHEMA', 'implementation_identity',
    '_SAFE_CLOSE', 'model', '_model_dependency_snapshot', '_model_dependencies_unchanged',
    '_packet_digest', '_remember_packet', '_validate_all_packets', '_finish_replay'))


def replay_prefixes(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_terminals,selected_hours,_observed=None):
    close_reader=_close_replay
    _check_dependencies()
    old.additional_content_bound(completed_hours)
    if (type(expected_terminals) is not dict or not expected_terminals
            or any(type(h) is not int or not 0 <= h < completed_hours for h in expected_terminals)
            or set(expected_terminals) != set(range(completed_hours))):
        raise ValueError('bounded selected historical terminal map required')
    if (type(selected_hours) is not tuple or not selected_hours or any(type(h) is not int for h in selected_hours)
            or selected_hours != tuple(sorted(set(selected_hours))) or not set(selected_hours)<=set(expected_terminals)):
        raise ValueError('bounded sorted selected hours required')
    expected_terminals = {h:io.pin(pin) for h,pin in expected_terminals.items()}
    if io.pin(expected_terminal_sha256) != expected_terminals[completed_hours-1]:
        raise ValueError('latest and selected terminal pins differ')
    root=history.chunks.base.local._path(Path(root).absolute())
    own=implementation_identity();old_identity=old.implementation_identity()
    directory=root/'obligation_non_authoritative';clock=root/'clock_bridge_non_authoritative'
    observed={} if _observed is None else _observed
    leases=[];views=observed.setdefault('views',{});topology=observed.setdefault('topology',{})
    obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})
    parent_names=observed.setdefault('parent_names',{})
    captured={};evidence={};seen_hours=[];retained_bytes=0;packet_bytes=0;all_packets={}
    began=time.perf_counter();observation_token=uuid4().hex;traversals=0
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
    reader=None;completed=False
    try:
        for path in (root,directory,clock,root/'source_parent_non_authoritative'):
            lease=history.prior.ReadView(path);leases.append(lease)
            _observe(identities,'lease '+str(path),(lease.directory_identity,lease.lock_identity))
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
            if hour in expected_terminals and next_pin != expected_terminals[hour]:
                raise ValueError('selected terminal does not belong to the pinned N chain')
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

        class Reader(ConstructorInspectionCapture, HistoricalTimedSnapshot):
            def inspect(self):
                nonlocal traversals
                traversals+=1
                return super().inspect()

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
                bridge.inspect(clock,hour,packet,self._spec,self._limits,binding_pin=header['clock_binding_sha256'],
                    intent_pin=ct['intent_sha256'],terminal_pin=terminal['clock_terminal_sha256'])
                return super()._child(hour,packet,intent_head,lineage,expected_head=expected_head,create=create)

            def _after(self,packet,result):
                nonlocal retained_bytes,packet_bytes
                if type(result) is not current.parent.ChildInspection or result.status!='accepted':
                    raise ValueError('accepted timed child required')
                count=len(binding.replay.native.model_api.stage_order(packet.inputs))
                if (result.stored_reports!=count or type(result.projection) is not current.parent.Projection
                        or result.projection.projection_identity!=io.digest(io.encode([current.parent.CHILD_SCHEMA,io.digest(result.projection.payload)]))):
                    raise ValueError('complete normal projection differs')
                after=super()._after(packet,result)
                hour=packet.relative_hour
                if type(hour) is not int or hour!=len(seen_hours) or not 0<=hour<completed_hours:
                    raise ValueError('one captured frame per chronological N hour required')
                packet_bytes+=_remember_packet(all_packets,packet,completed_hours)
                if packet_bytes+retained_bytes>MAX_RETAINED_BYTES:
                    raise ValueError('combined batch retained data byte cap exceeded')
                seen_hours.append(hour)
                if hour in selected_hours:
                    value=dict(packet=packet,result=result,after=after,count=count)
                    retained_bytes+=retained_size(value)
                    if packet_bytes+retained_bytes>MAX_RETAINED_BYTES:raise ValueError('combined batch retained data byte cap exceeded')
                    captured[hour]=value

                return after

        terminal=records[completed_hours-1][0]
        with history.replay.guard.solver_calls_forbidden():
            first_request=read(root/'job_000_non_authoritative'/'request.json',records[0][1]['job_pins']['request.json'])
            stages=first_request['input_receipt']['stage_slots']
            if type(stages) is not int or not 1<=stages<=232:raise ValueError('bounded stage count required')
            _observe_prefix(identities,root,completed_hours,stages)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            _check_dependencies()
            model_before=_model_dependency_snapshot()
            reader=Reader(declaration,completed_hours=completed_hours,expected_parent_identity=header['parent_identity'],
                expected_parent_head=terminal['parent_head'],expected_anchor_record=terminal['parent_anchor_sha256'])
            _check_dependencies()
            state=reader._take_constructor_inspection()
            if traversals!=1:raise ValueError('one constructor traversal required')
            if (state.completed_hours!=completed_hours or state.status!=('complete' if completed_hours==192 else 'ready')
                    or state.head!=terminal['parent_head'] or seen_hours!=list(range(completed_hours))
                    or set(captured)!=set(selected_hours) or tuple(all_packets)!=tuple(range(completed_hours))):
                raise ValueError('historical accepted controller prefix differs')
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            _check_dependencies()
            _model_dependencies_unchanged(model_before)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            _check_dependencies()
            _validate_all_packets(all_packets,completed_hours)
            _check_dependencies()
            # The long all-H loop has its own final filesystem/namespace and
            # runtime bookends. None of the success flags precedes these.
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            support.observe_parent_names(Path(declaration['root']),completed_hours=completed_hours,
                declared_hours=declaration['hours'],retained=parent_names)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            _model_dependencies_unchanged(model_before)
            _check_dependencies()
            proofs={}
            for hour in selected_hours:
                selected=prefix_evidence(evidence,hour)
                proofs[hour]=dict(completed_hours=hour+1,parent_head=records[hour][0]['parent_head'],
                    evidence_identity=io.digest(io.encode(selected)),historical_parent_prefix_verified=True,
                    historical_obligation_prefix_verified=True,historical_job_clock_prefix_verified=True,
                    suffix_chain_verified=False,current_latest_parent_verified=False,current_latest_obligation_verified=False,
                    live_release_authenticated=False,live_handoff_authenticated=False,writer_lock_authenticated=False,
                    persistent_lane_owner_implemented=False,detached_consumer_authenticated=False,
                    common_prefix_publication_verified=False,reference_or_actual_ready=False,
                    replay_contract=SCHEMA,**old.FLAGS)
            completed=True
            metrics=dict(completed_hours=completed_hours,selected_hours=list(selected_hours),
                parent_inspect_traversals=traversals,constructor_inspection_reused=True,
                normal_model_dependency_bookends_verified=True,observation_token=observation_token,
                all_hour_packet_revalidation_verified=True,all_hour_packet_count=len(all_packets),
                all_hour_packet_bytes=packet_bytes,combined_retained_bytes=packet_bytes+retained_bytes,
                retained_cap_bytes=MAX_RETAINED_BYTES,parent_namespace_bookends_verified=True,
                parent_namespace_observations=3,final_post_revalidation_bookends_verified=True,
                named_runtime_bookends_verified=True,named_runtime_inventory=dict(_RUNTIME.summary),
                complete_dynamic_input_closure_proved=False,unobserved_between_bookends_ABA_covered=False,
                selected_frame_bytes=retained_bytes,seconds=time.perf_counter()-began)
            return proofs,captured,header,metrics
    finally:
        _finish_replay(close_reader,reader,leases,captured,completed,sys.exception(),all_packets,seen_hours)

