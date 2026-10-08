"""Fixed, create-once driver call envelope; no CLI or execution authority.

run() is native-capable and requires new explicit authority for a real adapter.
The entry tick excludes imports/caller setup. The persisted end excludes final
accounting persistence, return and process exit. Unknown work stays in the wall.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
import threading

from experiments import h1_overshoot_accounting_development_v1 as accounting

bridge, io, base, worker = accounting.bridge, accounting.io, accounting.base, accounting.worker
SCHEMA = 'h1_lifecycle_driver_development_v1'
CAP = 2 * bridge.CAP
FLAGS = dict(accounting.FLAGS, declared_driver_call_window_complete=False)
_TOKEN = object()


def implementation_identity():
    return io.digest(io.encode([SCHEMA, accounting.implementation_identity(),
                               io.digest(Path(__file__).read_bytes())]))


def content_bound(hours):
    if type(hours) is not int or not 1 <= hours <= 192: raise ValueError('bounded hours required')
    return dict(logical_bytes=(2 * hours + 3) * CAP + 1, files=2 * hours + 4,
                directories=1, controller_tree_included=False,
                filesystem_allocation_bound_proven=False, resource_admission=False)


def _save(path, value):
    raw = io.encode(value)
    if len(raw) > CAP: raise ValueError('lifecycle record cap')
    io.write_new(path, raw)
    pin = io.digest(raw)
    _, view = base.entry.read(path, pin, CAP)
    if view[0] != raw: raise ValueError('lifecycle confirmation differs')
    return pin, (CAP, view)


def _read(path, pin):
    return base.entry.read(path, pin, CAP)


def _owner():
    return worker.job._current_process() + (threading.get_ident(),)


def _evidence_view(root, hours, stages):
    """Bounded complete parent/Job view; held lock bytes are never read."""
    dirs, files, locks = [], [], []
    def directory(path, names):
        dirs.append((str(path), worker.hour._directory(path, names)))
    def file(path, cap):
        raw, stamp = io.read_stable(path, cap)
        files.append((str(path), stamp, io.digest(raw)))
    def lock(path):
        identity = io.identity(path)
        if identity[2] != 1: raise ValueError('one-byte evidence lock required')
        locks.append((str(path), identity))
    directory(root, {'execution.lock','source_parent_non_authoritative','clock_bridge_non_authoritative',
                     *(f'job_{i:03d}_non_authoritative' for i in range(hours))})
    lock(root/'execution.lock')
    parent = root/'source_parent_non_authoritative'
    directory(parent, {'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative',
                       *(f'hour_{i:03d}_non_authoritative' for i in range(hours))})
    lock(parent/'execution.lock')
    events = parent/'parent_events_non_authoritative'
    directory(events, {'execution.lock','header.json',*(f'{i:03d}' for i in range(1,2*hours+1))})
    lock(events/'execution.lock'); file(events/'header.json', io.META_CAP)
    for i in range(1,2*hours+1):
        path = events/f'{i:03d}'
        directory(path, {'metadata.bin','payload.bin','commit.json'})
        for name, cap in (('metadata.bin',base.old.bounded.journal.CONTENT_CAP),
                          ('payload.bin',base.old.bounded.journal.CONTENT_CAP),('commit.json',io.META_CAP)):
            file(path/name, cap)
    anchor = parent/'parent_anchor_non_authoritative'
    directory(anchor, {'execution.lock','header.json',*(f'{i:03d}.json' for i in range(2*hours+1))})
    lock(anchor/'execution.lock')
    for name in ('header.json',*(f'{i:03d}.json' for i in range(2*hours+1))):
        file(anchor/name, base.old.snapshot.anchor.MAX_RECORD_BYTES)
    clock = root/'clock_bridge_non_authoritative'
    directory(clock, {'execution.lock','binding.json',*(f'{i:03d}' for i in range(hours))})
    lock(clock/'execution.lock'); file(clock/'binding.json',bridge.CAP)
    for i in range(hours):
        child = parent/f'hour_{i:03d}_non_authoritative'
        directory(child, {'reference.json'}); file(child/'reference.json', base.entry.CAP)
        path = clock/f'{i:03d}'
        directory(path, {'intent.json','job.json','terminal.json'})
        for name in ('intent.json','job.json','terminal.json'): file(path/name,bridge.CAP)
    jobs = tuple(base.parent.job_view(root/f'job_{i:03d}_non_authoritative',stages) for i in range(hours))
    return tuple(dirs), tuple(files), tuple(locks), jobs


def _headroom(root, hours, index, stages, budget):
    r = base.old.process.resources
    demands = (
        r.DirectoryDemand('lifecycle_remaining', str(root), content_bound(hours)['logical_bytes'], 32*base.old.MIB),
        r.DirectoryDemand('current_job', str(root), base.job_content_bound(stages)['logical_bytes'], 32*base.old.MIB),
        r.DirectoryDemand('parent_update', str(root), base.parent_update_bound(), 32*base.old.MIB),
        r.DirectoryDemand('clock_remaining', str(root), bridge.additional_content_bound(hours-index)['logical_bytes'], 32*base.old.MIB),
        r.DirectoryDemand('scratch', str(root), 8*base.old.MIB, 32*base.old.MIB))
    request = r.HostResourceBudget(budget.max_job_commit_bytes + 256*base.old.MIB, 32*base.old.MIB, demands)
    identity = r.resource_identity(request)
    result = r.observe_headroom(request, expected_request_identity=identity)
    if (type(result) is not r.HostHeadroomObservation or result.request_identity != identity
            or result.errors or not result.observed_headroom_sufficient
            or any(getattr(result, k) is not False for k in ('resource_reservation_held',
                'hard_resource_limits_enforced','whole_task_resources_verified','formal_run_authorized','formal_result'))):
        raise ValueError('exact combined development headroom required')


def _summary(wall, reports):
    worker._integer(wall)
    if type(reports) is not list or not 1 <= len(reports) <= 192: raise ValueError('bounded hour reports required')
    for r in reports:
        worker._integer(r['arithmetic']['native_total_ns'])
        pair = r['arithmetic']['stagewise_overshoot_ns_ratio']
        if (type(pair) is not list or len(pair) != 2 or any(type(x) is not int for x in pair)
                or pair[0] < 0 or pair[1] <= 0 or any(x.bit_length() > 2048 for x in pair)
                or accounting.ratio(accounting.Fraction(*pair)) != pair):
            raise ValueError('canonical bounded overshoot ratio required')
    native = sum(r['arithmetic']['native_total_ns'] for r in reports)
    excess = sum((accounting.Fraction(*r['arithmetic']['stagewise_overshoot_ns_ratio']) for r in reports),
                 accounting.Fraction(0))
    if native > wall: raise ValueError('native time exceeds enclosing wall')
    return dict(wall_ns=wall, native_total_ns=native, outside_native_ns=wall-native,
                stagewise_overshoot_ns_ratio=accounting.ratio(excess),
                stagewise_charge_contract_candidate_ns_ratio=accounting.ratio(wall-native+excess))


@dataclass(frozen=True, init=False)
class Completion:
    root: str
    binding_sha256: str
    terminal_sha256: str
    final_accounting_persistence_tail_ns: int
    declared_driver_call_window_complete: bool

    def __init__(self, values, *, _token=None):
        if _token is not _TOKEN: raise TypeError('owned driver return required')
        for name, value in zip(self.__annotations__, values, strict=True): object.__setattr__(self, name, value)


def run(root, network, specification, limits, *, source_identities, origin,
        upstream_root, config_path, dc_bus, budget):
    """Fixed H-hour loop. Existing roots reject retry; failures retain all bytes."""
    start = bridge.tick(0)
    owner, profile, own = _owner(), bridge.profile(), implementation_identity()
    if type(source_identities) is not tuple: raise ValueError('fixed source identity tuple required')
    hours = len(source_identities)
    content_bound(hours)
    for pin in source_identities: io.pin(pin)
    if type(budget) is not base.old.process.TaskProcessBudget: raise ValueError('exact Job budget required')
    budget.__post_init__()
    if budget.max_elapsed_seconds > 300: raise ValueError('short development ceiling is 300 seconds')
    declaration = dict(network_identity=network.identity, specification=asdict(specification), limits=asdict(limits),
        origin=asdict(origin), upstream_root=str(Path(upstream_root).resolve()), config_path=str(Path(config_path).resolve()),
        dc_bus=dc_bus, budget=asdict(budget), source_identities=list(source_identities))
    declaration_raw = io.encode(declaration)
    lease = base.old.bounded.chunks.base.local._Lease(Path(root), True)
    root = lease.root
    controller = None
    views, reports, result_pins = {}, [], []
    evidence = None
    stages = None

    def check():
        if lease is not None: lease.check()
        if (_owner() != owner or not io.same(bridge.profile(), profile) or implementation_identity() != own
                or io.encode(dict(network_identity=network.identity, specification=asdict(specification), limits=asdict(limits),
                    origin=asdict(origin), upstream_root=str(Path(upstream_root).resolve()), config_path=str(Path(config_path).resolve()),
                    dc_bus=dc_bus, budget=asdict(budget), source_identities=list(source_identities))) != declaration_raw):
            raise ValueError('driver owner/input/implementation changed')
        base.entry.unchanged(views)
        if evidence is not None and _evidence_view(root/'controller_non_authoritative',hours,stages) != evidence:
            raise ValueError('complete driver evidence changed')

    def save(name, value):
        pin, view = _save(root/name, value)
        views[root/name] = view
        return pin

    try:
        binding_pin = save('binding.json', dict(schema=SCHEMA, implementation=own, request=declaration,
            start_ns=start, pid=owner[0], creation_filetime=owner[1], thread_id=owner[2], clock=profile, **FLAGS))
        construct_start = bridge.tick(start)
        controller = bridge.Controller(root/'controller_non_authoritative', network, specification, limits,
            origin=origin, upstream_root=upstream_root, config_path=config_path, dc_bus=dc_bus, hours=hours, budget=budget)
        state = controller.inspect()
        construct_end = bridge.tick(construct_start)
        if state.completed_hours != 0 or state.status != 'ready': raise ValueError('fresh initial parent required')
        controller_pin = save('controller.json', dict(binding_sha256=binding_pin,
            parent_declaration=controller._parent._declaration, parent_identity=controller._parent.identity,
            initial_head=state.head, clock_binding_sha256=controller.binding_pin,
            initialization_interval_ns=[construct_start, construct_end]))
        previous_end = construct_end
        for index, source_pin in enumerate(source_identities):
            check()
            preparation_start = bridge.tick(previous_end)
            _headroom(root, hours, index, controller._parent._stages, budget)
            restored, before, previous = controller._parent._restore()
            if restored != state: raise ValueError('parent state changed before driver step')
            source = controller._parent._load(index, source_pin)
            packet = controller._parent._packet(source, index, before, previous)
            intent_pin = save(f'{index:03d}.intent.json', dict(binding_sha256=binding_pin, index=index,
                source_identity=source_pin, expected_head=state.head, previous_sha256=result_pins[-1] if result_pins else controller_pin))
            step_start = bridge.tick(preparation_start)
            state = controller.step(expected_source_identity=source_pin, expected_head=state.head)
            observation = controller.last_observation
            step_end = bridge.tick(step_start)
            if (type(observation) is not bridge.Observation or observation.index != index
                    or observation.outcome_head != state.head or observation.live_clock_profile_and_containment_checked is not True
                    or state.completed_hours != index+1 or state.status != ('complete' if index+1 == hours else 'ready')):
                raise ValueError('owned bridge completion differs')
            clock = controller.clock_root/f'{index:03d}'
            clock_intent_pin = io.digest(io.read_stable(clock/'intent.json', bridge.CAP)[0])
            report = accounting.inspect_window(controller.clock_root, index, packet, specification, limits,
                binding_pin=controller.binding_pin, intent_pin=clock_intent_pin, terminal_pin=observation.terminal_sha256)
            ci, _ = base.entry.read(clock/'intent.json', clock_intent_pin)
            ct, _ = base.entry.read(clock/'terminal.json', observation.terminal_sha256)
            if not step_start <= ci['start_ns'] <= ct['end_ns'] <= step_end:
                raise ValueError('bridge outside driver step')
            if (report['arithmetic']['native_total_ns'] != observation.native_total_ns
                    or report['arithmetic']['window_wall_ns'] != observation.transaction_wall_ns
                    or report['arithmetic']['outside_native_ns'] != observation.observed_non_native_ns):
                raise ValueError('live/fresh native totals differ')
            observer_end = bridge.tick(step_end)
            reports.append(report)
            result_pins.append(save(f'{index:03d}.result.json', dict(intent_sha256=intent_pin, index=index,
                outcome_head=state.head, preparation_interval_ns=[preparation_start, step_start],
                step_interval_ns=[step_start, step_end], accounting_observer_interval_ns=[step_end, observer_end],
                clock_interval_ns=[ci['start_ns'], ct['end_ns']], report=report)))
            previous_end = observer_end
        check()
        replay_start = bridge.tick(previous_end)
        stages = controller._parent._stages
        evidence = _evidence_view(root/'controller_non_authoritative',hours,stages)
        if controller.inspect() != state: raise ValueError('final complete source prefix changed')
        anchor_pin = controller._parent._anchor.inspect().record_sha256
        replay_end = bridge.tick(replay_start)
        check()
        closing, controller = controller, None
        closing.close()
        close_end = bridge.tick(replay_end)
        check()
        end = bridge.tick(close_end)
        terminal_pin = save('terminal.json', dict(schema=SCHEMA, binding_sha256=binding_pin,
            controller_sha256=controller_pin, result_sha256=result_pins, end_ns=end,
            final_replay_interval_ns=[replay_start, replay_end], close_interval_ns=[replay_end, close_end],
            final_parent=asdict(state), final_anchor_sha256=anchor_pin,
            arithmetic=_summary(end-start, reports), **FLAGS))
        inspect(root, binding_pin=binding_pin, terminal_pin=terminal_pin)
        check()
        closing, lease = lease, None
        closing.close()
        check()
        final = bridge.tick(end)
        return Completion((str(root), binding_pin, terminal_pin, final-end, True), _token=_TOKEN)
    finally:
        try:
            if controller is not None:
                closing, controller = controller, None
                closing.close()
        finally:
            closing, lease = lease, None
            if closing is not None: closing.close()


def _report(report, index, request):
    fields = {'schema','implementation','clock_pins','hour_request_sha256','relative_hour','stage_order',
        'stage_order_sha256','specification_sha256','stage_specification_sha256','interval_vector_sha256',
        'declared_seconds_per_stage_ratio','arithmetic','scope','reservation_role','acceptance_policy_selected',
        'threshold_comparison_performed','live_authority_reconstructed',*accounting.FLAGS}
    if (type(report) is not dict or set(report) != fields or report['schema'] != accounting.SCHEMA
            or report['implementation'] != accounting.implementation_identity()
            or type(report['relative_hour']) is not int or report['relative_hour'] != index
            or any(report[k] is not False for k in (*accounting.FLAGS,'acceptance_policy_selected',
                    'threshold_comparison_performed','live_authority_reconstructed'))
            or report['scope'] != 'single persisted transaction window'
            or report['reservation_role'] != 'declared TimeLimit, not hard runtime enforcement'):
        raise ValueError('exact nonauthoritative accounting report required')
    for key in ('hour_request_sha256','stage_order_sha256','specification_sha256','interval_vector_sha256'):
        io.pin(report[key])
    if type(report['clock_pins']) is not dict or set(report['clock_pins']) != {'binding','intent','terminal'}:
        raise ValueError('exact accounting clock pins required')
    for value in report['clock_pins'].values(): io.pin(value)
    order = report['stage_order']
    spec = base.old.snapshot.Rq2SolverSpec(**request['specification'])
    count, seconds = accounting.contract.validate_work(accounting.contract.H1NormalWork(
        'observed_clock_window',1,tuple(tuple(row) for row in order),spec))
    if (type(order) is not list or report['stage_order_sha256'] != io.digest(io.encode(order))
            or report['specification_sha256'] != io.digest(io.encode(request['specification']))
            or not io.same(report['declared_seconds_per_stage_ratio'], accounting.ratio(seconds))
            or type(report['stage_specification_sha256']) is not list or len(report['stage_specification_sha256']) != count):
        raise ValueError('accounting specification/stage declaration differs')
    for pin in report['stage_specification_sha256']: io.pin(pin)
    arithmetic = report['arithmetic']
    rows = arithmetic['stages']
    if type(rows) is not list or len(rows) != count: raise ValueError('complete arithmetic stage vector required')
    actual = tuple(row['actual_ns'] for row in rows)
    expected = accounting.account(wall_ns=arithmetic['window_wall_ns'], actual_ns=actual,
                                  reserved_ns=(seconds*10**9,)*count)
    if not io.same(arithmetic, expected): raise ValueError('stage arithmetic differs')


def inspect(root, *, binding_pin, terminal_pin):
    """Conditional metadata chronology only; does not reconstruct live/science authority."""
    root = Path(root).absolute()
    binding, bv = _read(root/'binding.json', binding_pin)
    terminal, tv = _read(root/'terminal.json', terminal_pin)
    own = implementation_identity()
    if (set(binding) != {'schema','implementation','request','start_ns','pid','creation_filetime','thread_id','clock',*FLAGS}
            or set(terminal) != {'schema','binding_sha256','controller_sha256','result_sha256','end_ns',
                'final_replay_interval_ns','close_interval_ns','final_parent','final_anchor_sha256','arithmetic',*FLAGS}
            or binding.get('schema') != SCHEMA or binding.get('implementation') != own
            or terminal.get('schema') != SCHEMA or terminal.get('binding_sha256') != binding_pin
            or not io.same(binding['clock'], bridge.profile())
            or any(binding.get(k) is not False or terminal.get(k) is not False for k in FLAGS)):
        raise ValueError('lifecycle binding/terminal differs')
    for name in ('pid','creation_filetime','thread_id'):
        if worker._integer(binding[name]) == 0: raise ValueError('driver owner required')
    request = binding['request']
    if (type(request) is not dict or set(request) != {'network_identity','specification','limits','origin',
            'upstream_root','config_path','dc_bus','budget','source_identities'}
            or type(request['dc_bus']) is not int or any(type(request[k]) is not str for k in ('upstream_root','config_path'))):
        raise ValueError('exact driver request required')
    io.pin(request['network_identity'])
    budget = base.old.process.TaskProcessBudget(**request['budget'])
    if budget.max_elapsed_seconds > 300 or not io.same(asdict(budget),request['budget']):
        raise ValueError('exact short Job budget required')
    base.old.snapshot.Rq2SolverSpec(**request['specification'])
    base.old.replay.H1HourReplayLimits(**request['limits'])
    base.old.snapshot.binding.H1SourceDeclaration(**request['origin'])
    pins = binding['request']['source_identities']
    if type(pins) is not list: raise ValueError('source manifest list required')
    content_bound(len(pins))
    for pin in pins: io.pin(pin)
    expected = {'execution.lock','binding.json','controller.json','terminal.json','controller_non_authoritative'}
    expected |= {f'{i:03d}.{kind}.json' for i in range(len(pins)) for kind in ('intent','result')}
    identity = worker.hour._directory(root, expected)
    control, cv = _read(root/'controller.json', terminal['controller_sha256'])
    if (set(control) != {'binding_sha256','parent_declaration','parent_identity','initial_head',
                        'clock_binding_sha256','initialization_interval_ns'}
            or control['binding_sha256'] != binding_pin
            or control['parent_identity'] != io.digest(io.encode(control['parent_declaration']))
            or type(control['parent_declaration']['hours']) is not int
            or control['parent_declaration']['hours'] != len(pins)):
        raise ValueError('controller binding differs')
    for key in ('network_identity','specification','limits','origin','upstream_root','config_path','dc_bus'):
        if not io.same(control['parent_declaration'][key], binding['request'][key]):
            raise ValueError('driver/parent request differs')
    io.pin(control['initial_head']); io.pin(terminal['final_anchor_sha256'])
    parent_root = root/'controller_non_authoritative/source_parent_non_authoritative'
    if control['parent_declaration']['root'] != str(parent_root): raise ValueError('fixed driver parent root required')
    clock_root = root/'controller_non_authoritative/clock_bridge_non_authoritative'
    clock_names = {'binding.json','execution.lock'} | {f'{i:03d}' for i in range(len(pins))}
    clock_identity = worker.hour._directory(clock_root, clock_names)
    cb, cbv = base.entry.read(clock_root/'binding.json', control['clock_binding_sha256'])
    if (set(cb) != {'schema','implementation','parent_identity','pid','creation_filetime','thread_id','clock','hours',*bridge.FLAGS}
            or cb['schema'] != bridge.SCHEMA or cb['implementation'] != bridge.implementation_identity()
            or any(cb[k] is not False for k in bridge.FLAGS)
            or cb['parent_identity'] != control['parent_identity'] or not io.same(cb['clock'], binding['clock'])
            or any(cb[n] != binding[n] or type(cb[n]) is not int for n in ('pid','creation_filetime','thread_id'))
            or type(cb['hours']) is not int or cb['hours'] != len(pins)):
        raise ValueError('driver/bridge identity differs')
    start, end = worker._integer(binding['start_ns']), worker._integer(terminal['end_ns'])
    views = {root/'binding.json':(CAP,bv),root/'terminal.json':(CAP,tv),root/'controller.json':(CAP,cv),
             clock_root/'binding.json':(bridge.CAP,cbv)}
    previous, head, cursor = terminal['controller_sha256'], control['initial_head'], start
    reports, directories = [], {}
    previous_clock = control['clock_binding_sha256']

    def interval(pair):
        nonlocal cursor
        if type(pair) is not list or len(pair) != 2: raise ValueError('interval pair required')
        left, right = map(worker._integer, pair)
        if not cursor <= left <= right <= end: raise ValueError('ordered contained driver intervals required')
        cursor = right
        return left, right

    interval(control['initialization_interval_ns'])
    if len(terminal['result_sha256']) != len(pins): raise ValueError('incomplete driver results')
    for index, pin in enumerate(terminal['result_sha256']):
        result, rv = _read(root/f'{index:03d}.result.json', pin)
        intent, iv = _read(root/f'{index:03d}.intent.json', result['intent_sha256'])
        if (set(result) != {'intent_sha256','index','outcome_head','preparation_interval_ns','step_interval_ns',
                           'accounting_observer_interval_ns','clock_interval_ns','report'}
                or not io.same(intent, dict(binding_sha256=binding_pin, index=index, source_identity=pins[index],
                expected_head=head, previous_sha256=previous)) or type(result['index']) is not int or result['index'] != index):
            raise ValueError('driver hour chronology differs')
        interval(result['preparation_interval_ns'])
        left, right = interval(result['step_interval_ns'])
        _report(result['report'],index,request)
        cp = result['report']['clock_pins']
        if cp['binding'] != control['clock_binding_sha256']: raise ValueError('report bridge binding differs')
        directory = clock_root/f'{index:03d}'
        directories[directory] = worker.hour._directory(directory, {'intent.json','job.json','terminal.json'})
        ci, civ = base.entry.read(directory/'intent.json', cp['intent'])
        ct, ctv = base.entry.read(directory/'terminal.json', cp['terminal'])
        job, jv = base.entry.read(directory/'job.json', ct['job_record_sha256'])
        if (not io.same(ci,dict(schema=bridge.SCHEMA,binding_sha256=cp['binding'],index=index,start_ns=ci['start_ns'],
                expected_head=head,source_identity=pins[index],previous_sha256=previous_clock))
                or set(ct) != {'schema','intent_sha256','end_ns','job_start_ns','job_end_ns','job_pins','outcome_head',
                              'job_record_sha256','outcome_anchor_sha256',*bridge.FLAGS}
                or ct['schema'] != bridge.SCHEMA or any(ct[k] is not False for k in bridge.FLAGS)
                or type(ct['job_pins']) is not dict or set(ct['job_pins']) != set(base.parent.RECORDS)
                or ct['outcome_head'] != result['outcome_head'] or ct['intent_sha256'] != cp['intent']
                or not io.same(job,dict(schema=bridge.SCHEMA,intent_sha256=cp['intent'],start_ns=ct['job_start_ns'],
                        end_ns=ct['job_end_ns'],job_pins=ct['job_pins']))
                or not io.same(result['clock_interval_ns'], [ci['start_ns'], ct['end_ns']])):
            raise ValueError('driver/bridge hour differs')
        for value in (*ct['job_pins'].values(),ct['outcome_anchor_sha256']): io.pin(value)
        js, je = worker._integer(ct['job_start_ns']), worker._integer(ct['job_end_ns'])
        for name, view in (('intent.json',civ),('terminal.json',ctv),('job.json',jv)):
            views[directory/name] = (bridge.CAP, view)
        a, b = map(worker._integer, result['clock_interval_ns'])
        if not left <= a <= js <= je <= b <= right: raise ValueError('stored bridge containment differs')
        if result['report']['arithmetic']['window_wall_ns'] != b-a: raise ValueError('report window differs')
        interval(result['accounting_observer_interval_ns'])
        reports.append(result['report'])
        previous, head = pin, io.pin(result['outcome_head'])
        previous_clock = cp['terminal']
        views[root/f'{index:03d}.result.json'] = (CAP, rv)
        views[root/f'{index:03d}.intent.json'] = (CAP, iv)
    interval(terminal['final_replay_interval_ns']); interval(terminal['close_interval_ns'])
    state = terminal['final_parent']
    if (state['head'] != head or type(state['completed_hours']) is not int or state['completed_hours'] != len(pins)
            or state['parent_identity'] != control['parent_identity'] or state['status'] != 'complete'
            or any(v is not False for k,v in state.items() if k in ('native_execution_authenticated','source_authenticated',
                'published','independent_hour_jobs_integrated','producer_coverage_proven','resource_admission','formal_execution_ready','formal_result'))
            or not io.same(terminal['arithmetic'], _summary(end-start, reports))):
        raise ValueError('driver final state/arithmetic differs')
    anchor_path = parent_root/'parent_anchor_non_authoritative'/f'{2*len(pins):03d}.json'
    anchor, av = base.entry.read(anchor_path,terminal['final_anchor_sha256'],base.old.snapshot.anchor.MAX_RECORD_BYTES)
    if (set(anchor) != {'schema','anchor_identity','sequence','previous_record_sha256',
                       'previous_registry_head','registry_head','event_sha256'}
            or anchor['schema'] != base.old.snapshot.anchor.SCHEMA or type(anchor['sequence']) is not int
            or anchor['sequence'] != 2*len(pins) or anchor['registry_head'] != head
            or terminal['final_anchor_sha256'] != ct['outcome_anchor_sha256']):
        raise ValueError('final parent anchor differs')
    for name in ('anchor_identity','previous_record_sha256','previous_registry_head','registry_head','event_sha256'):
        io.pin(anchor[name])
    views[anchor_path] = (base.old.snapshot.anchor.MAX_RECORD_BYTES,av)
    base.entry.unchanged(views)
    if (worker.hour._directory(root, expected) != identity
            or worker.hour._directory(clock_root, clock_names) != clock_identity
            or any(worker.hour._directory(p,{'intent.json','job.json','terminal.json'}) != v for p,v in directories.items())
            or implementation_identity() != own): raise ValueError('lifecycle root/implementation changed')
    return dict(arithmetic=terminal['arithmetic'], final_accounting_persistence_tail_ns=None,
                fresh_scientific_replay_performed=False, live_return_observed=False, **FLAGS)
