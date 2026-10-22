"""One constructor traversal per independent historical Reader.

DRAFT_NONAUTHORITATIVE. The predecessor and its two-traversal caller remain
unchanged. All predecessor post-observation checks and cleanup are retained.
"""
from dataclasses import asdict
from pathlib import Path
import sys
import time
from types import FunctionType
from uuid import uuid4

from experiments import h1_phase_historical_batch_development_v1 as prior
from experiments import h1_constructor_inspection_capture_development_v1 as capture

SCHEMA = 'h1_phase_historical_batch_development_v2'
io, binding, bridge, base = prior.io, prior.binding, prior.bridge, prior.base
old, history, current, predecessor = prior.old, prior.history, prior.current, prior.predecessor
HistoricalTimedSnapshot = prior.HistoricalTimedSnapshot
ConstructorInspectionCapture = capture.ConstructorInspectionCapture
MAX_RETAINED_BYTES = prior.MAX_RETAINED_BYTES
retained_size, prefix_evidence = prior.retained_size, prior.prefix_evidence
_observe, _observe_sources, _observe_prefix = prior._observe, prior._observe_sources, prior._observe_prefix
_obligation_inventory, _close_replay = prior._obligation_inventory, prior._close_replay


def implementation_identity():
    return io.digest(io.encode([SCHEMA, prior.implementation_identity(),
        io.digest(Path(__file__).read_bytes()), io.digest(Path(capture.__file__).read_bytes())]))


def _function_state(value):
    if type(value) is not FunctionType:
        return None
    return (value.__code__, value.__globals__, value.__defaults__, repr(value.__defaults__),
        value.__kwdefaults__, repr(value.__kwdefaults__), value.__closure__,
        tuple(cell.cell_contents for cell in value.__closure__ or ()))


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
_LOCAL_NAMESPACE = globals()
_LOCAL_BINDINGS = tuple((name, _LOCAL_NAMESPACE[name]) for name in (
    'prior', 'capture', 'io', 'binding', 'bridge', 'base', 'old', 'history', 'current', 'predecessor',
    'HistoricalTimedSnapshot', 'ConstructorInspectionCapture', 'MAX_RETAINED_BYTES', 'retained_size',
    'prefix_evidence', '_observe', '_observe_sources', '_observe_prefix', '_obligation_inventory',
    '_close_replay', '_function_state', '_check_dependencies'))


def replay_prefixes(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_terminals,selected_hours,_observed=None):
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
    captured={};evidence={};seen_hours=[];retained_bytes=0
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
                nonlocal retained_bytes
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
                seen_hours.append(hour)
                if hour in selected_hours:
                    value=dict(packet=packet,result=result,after=after,count=count)
                    retained_bytes+=retained_size(value)
                    if retained_bytes>MAX_RETAINED_BYTES:raise ValueError('batch retained data byte cap exceeded')
                    captured[hour]=value

                return after

        terminal=records[completed_hours-1][0]
        with history.replay.guard.solver_calls_forbidden():
            first_request=read(root/'job_000_non_authoritative'/'request.json',records[0][1]['job_pins']['request.json'])
            stages=first_request['input_receipt']['stage_slots']
            if type(stages) is not int or not 1<=stages<=232:raise ValueError('bounded stage count required')
            _observe_prefix(identities,root,completed_hours,stages)
            reader=Reader(declaration,completed_hours=completed_hours,expected_parent_identity=header['parent_identity'],
                expected_parent_head=terminal['parent_head'],expected_anchor_record=terminal['parent_anchor_sha256'])
            _check_dependencies()
            state=reader._take_constructor_inspection()
            if traversals!=1:raise ValueError('one constructor traversal required')
            if (state.completed_hours!=completed_hours or state.status!=('complete' if completed_hours==192 else 'ready')
                    or state.head!=terminal['parent_head'] or seen_hours!=list(range(completed_hours))
                    or set(captured)!=set(selected_hours)):
                raise ValueError('historical accepted controller prefix differs')
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
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
                parent_inspect_traversals=traversals,constructor_inspection_reused=True,observation_token=observation_token,
                selected_frame_bytes=retained_bytes,seconds=time.perf_counter()-began)
            return proofs,captured,header,metrics
    finally:
        _close_replay(reader,leases,captured,completed,sys.exception())

