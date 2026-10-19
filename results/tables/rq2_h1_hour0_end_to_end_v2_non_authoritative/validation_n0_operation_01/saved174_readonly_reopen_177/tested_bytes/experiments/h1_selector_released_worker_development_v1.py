"""Source-rebuilt selector worker transport; no launcher, CLI or Job authority.

Real execute requires new native authority and enclosing owned Job supervision.
Persisted results alone cannot establish parent acceptance or phase consumption.
"""
import ctypes as c
from dataclasses import asdict,dataclass,fields
import json
from math import isfinite
import os
from pathlib import Path
import sys
from threading import Lock,get_ident
from types import MappingProxyType

from experiments import h1_selector_input_snapshot_development_v1 as snapshot
from experiments import h1_timed_selector_sequence_development_v1 as sequence
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as runtime

io=sequence.io
SCHEMA='h1_selector_released_worker_development_v1'
CAP=1024**2
FLAGS=MappingProxyType(dict(sequence.FLAGS,worker_job_membership_verified=False,
    cross_process_clock_bridge_verified=False,selector_producer_connected=False))
INPUTS={'request.json','selector_snapshot.json','launch.json','initial_observation.json',
    'child.json','release_intent.json','scratch_non_authoritative'}
OUTPUTS={'consumed.json','science_sequence_non_authoritative','timing_sequence_non_authoritative',
    'worker_result.json','worker_timing_terminal.json'}
PHASES=('released_handshake','snapshot_rebuild_before','sequence_prepare','sequence_run',
    'sequence_validate','sequence_fresh_inspect','snapshot_rebuild_after','result_publication')
_TOKEN=object()
_CLAIMS=set()
_CLAIM_GUARD=Lock()


def implementation_identity():
    if SCHEMA!='h1_selector_released_worker_development_v1' or any(v is not False for v in FLAGS.values()):
        raise ValueError('selector worker scope changed')
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),snapshot.implementation_identity(),
        sequence.implementation_identity(),[(m.__name__,io.digest(Path(m.__file__).read_bytes()))
        for m in (process,process.process,process.resources,runtime)]]))


def _object(value,names):
    if type(value) is not dict or set(value)!=set(names):raise ValueError('exact selector worker fields required')
    return value


def _read(path,cap=CAP):return sequence._read(path,cap)


def _doc(raw):return sequence._doc(raw)


def write(path,value):
    raw=io.encode(value)
    if len(raw)>CAP:raise ValueError('selector worker metadata cap')
    io.write_new(path,raw)
    if _read(path)[0]!=raw:raise ValueError('selector worker publication readback differs')
    return io.digest(raw)


def _projection(item,timing_bytes):
    if type(item) is not snapshot.RebuiltInput:raise ValueError('exact source rebuilt input required')
    configuration=sequence._configuration((item.frame,item.disclosure,item.before),item.arguments,
        item.max_archive_bytes,timing_bytes,item.run_configuration)
    role={'Rref':'reference','A':'actual'}.get(item.arguments['lane'].role)
    if role is None:raise ValueError('selector role required')
    binding=item.run_configuration.binding()
    return dict(role=role,lane=asdict(item.arguments['lane']),run_configuration=binding,
        run_configuration_sha256=io.digest(io.encode(binding)),max_archive_bytes=item.max_archive_bytes,
        max_timing_archive_bytes=timing_bytes,budget=asdict(getattr(item.run_configuration,role+'_job_budget')),
        non_solver_seconds=getattr(item.run_configuration,role+'_non_solver_seconds'),
        sequence_request_sha256=io.digest(io.encode(configuration)),sequence_configuration=configuration)


def request_document(root,snapshot_bytes,*,max_timing_archive_bytes):
    """Pure parent preparation; writes no files and grants no native authority."""
    root=sequence.legacy._root(root)
    if type(snapshot_bytes) is not bytes or not 0<len(snapshot_bytes)<=snapshot.CAP:
        raise ValueError('bounded immutable selector snapshot required')
    with sequence.legacy.bridge.science.prior.guard.solver_calls_forbidden():
        pin=io.digest(snapshot_bytes)
        item=snapshot.rebuild(snapshot_bytes,expected_sha256=pin)
        value=dict(schema=SCHEMA,root=str(root),implementation=implementation_identity(),
            snapshot=dict(name='selector_snapshot.json',size=len(snapshot_bytes),sha256=pin,
                implementation=snapshot.implementation_identity()),
            route='source_rebuilt_timed_selector',**_projection(item,max_timing_archive_bytes),**FLAGS)
        if len(io.encode(value))>CAP:raise ValueError('selector request cap')
        return value


def content_bound(request):
    # Five parent metadata files plus consumed, result and timing terminal.
    return request['max_archive_bytes']+request['max_timing_archive_bytes']+request['snapshot']['size']+8*CAP


def _current_process():
    native=process.process;k=native._api()
    creation,end,kernel,user=(native.w.FILETIME() for _ in range(4))
    native._check(k.GetProcessTimes(native.HANDLE(-1),c.byref(creation),c.byref(end),c.byref(kernel),c.byref(user)))
    return os.getpid(),creation.dwLowDateTime | (creation.dwHighDateTime<<32)


def _validate_initial(initial,host):
    """Generic initial headroom checks; no N-specific request or saved schema."""
    resources=process.resources
    _object(initial,(f.name for f in fields(resources.HostHeadroomObservation)))
    if (initial['request_identity']!=resources.resource_identity(host)
            or initial['observed_headroom_sufficient'] is not True or initial['errors']!=[]
            or any(initial[k] is not False for k in ('resource_reservation_held','hard_resource_limits_enforced',
                'whole_task_resources_verified','formal_run_authorized','formal_result'))):
        raise ValueError('initial headroom claim or authority differs')
    start,end=initial['started_monotonic_seconds'],initial['finished_monotonic_seconds']
    if any(type(x) not in (int,float) or not isfinite(x) or x<0 for x in (start,end)) or end<start:
        raise ValueError('finite ordered initial observation clock required')
    commit=resources.CommitObservation(**_object(initial['commit'],(f.name for f in fields(resources.CommitObservation))))
    if (any(type(v) is not int for v in asdict(commit).values()) or commit.committed_pages<0
            or commit.limit_pages<=0 or commit.limit_pages<commit.committed_pages or commit.page_size_bytes<=0
            or commit.available_bytes<host.additional_commit_bytes+host.commit_reserve_bytes):
        raise ValueError('initial commit headroom differs')
    if type(initial['disks']) is not list or len(initial['disks'])!=len(host.directories):
        raise ValueError('exact initial disk inventory required')
    groups={}
    for value,demand in zip(initial['disks'],host.directories,strict=True):
        disk=resources.DiskObservation(**_object(value,(f.name for f in fields(resources.DiskObservation))))
        volume=resources._directory_binding(demand.directory)[3]
        if ((disk.name,disk.directory,disk.volume_guid)!=(demand.name,demand.directory,volume)
                or any(type(v) is not int or v<0 for v in (disk.caller_available_bytes,disk.caller_total_bytes,disk.volume_free_bytes))
                or disk.caller_available_bytes>min(disk.caller_total_bytes,disk.volume_free_bytes)):
            raise ValueError('initial caller disk observation differs')
        total,reserve,available=groups.get(volume,(0,0,disk.caller_available_bytes))
        groups[volume]=(total+demand.additional_bytes,max(reserve,demand.reserve_bytes),min(available,disk.caller_available_bytes))
    expected=[(volume,*values) for volume,values in sorted(groups.items())]
    if (not io.same(initial['volume_requirements'],expected)
            or any(available<total+reserve for total,reserve,available in groups.values())):
        raise ValueError('initial per-volume headroom differs')


def _roots(root,names):
    directory=sequence.legacy.stage._directory(root,names)
    return directory[:2],sequence.timed.capture.directory(root/'scratch_non_authoritative')


@dataclass(frozen=True,init=False)
class ConsumedSelectorRequest:
    root: Path
    request_sha256: str
    consumed_sha256: str
    pid: int
    creation_filetime: int
    thread_id: int
    directory_identities: tuple
    records: tuple
    implementation: str

    def __init__(self,values,*,_token=None):
        if _token is not _TOKEN:raise TypeError('live consumed selector request required')
        for name,value in zip(self.__annotations__,values,strict=True):object.__setattr__(self,name,value)

    def _no_copy(self,*args):raise TypeError('consumed selector request cannot be copied')
    __copy__=__deepcopy__=__reduce_ex__=_no_copy


def _fingerprint(ticket):
    return io.digest(io.encode([str(ticket.root),ticket.request_sha256,ticket.consumed_sha256,ticket.pid,
        ticket.creation_filetime,ticket.thread_id,ticket.directory_identities,ticket.implementation,
        [(str(p),cap,io.digest(raw),stamp) for p,cap,raw,stamp in ticket.records]]))


def _check(ticket,pin,names):
    if (type(ticket) is not ConsumedSelectorRequest or _fingerprint(ticket)!=pin
            or _current_process()!=(ticket.pid,ticket.creation_filetime) or get_ident()!=ticket.thread_id
            or implementation_identity()!=ticket.implementation or _roots(ticket.root,names)!=ticket.directory_identities
            or any(_read(path,cap)!=(raw,stamp) for path,cap,raw,stamp in ticket.records)):
        raise ValueError('consumed selector identity or retained evidence changed')
    request=_doc(ticket.records[0][2]);launch=_doc(next(raw for p,cap,raw,stamp in ticket.records if p.name=='launch.json'))
    if _process_identity(launch,process.TaskProcessBudget(**request['budget']),ticket.root)!=launch['process_identity']:
        raise ValueError('released selector execution environment changed')


def _process_identity(launch,budget,root):
    environment=dict(sorted(os.environ.items()));runtime._environment(environment)
    if (Path.cwd()!=root/'scratch_non_authoritative' or launch['argv']!=sys.orig_argv
            or launch['cwd']!=str(Path.cwd()) or launch['environment_sha256']!=io.digest(io.encode(environment))):
        raise ValueError('released selector argv cwd or environment differs')
    hv=launch['host'];resources=process.resources
    host=resources.HostResourceBudget(hv['additional_commit_bytes'],hv['commit_reserve_bytes'],
        tuple(resources.DirectoryDemand(**d) for d in hv['directories']))
    return process.task_process_identity(launch['argv'],cwd=Path.cwd(),environment=environment,budget=budget,
        host_budget=host,expected_host_identity=resources.resource_identity(host))


def released_input(request_path,request_pin):
    """Validate exact release then consume before the first source reconstruction."""
    path=Path(request_path);root=sequence.legacy._root(path.parent);io.pin(request_pin)
    if path!=root/'request.json' or path!=path.resolve():raise ValueError('canonical selector request path required')
    if any((root/name).exists() for name in OUTPUTS):raise FileExistsError('selector request already consumed or partial')
    # A failed first write may leave no durable bytes. This creating process must
    # still not retry; a different process cannot match the retained launch PID.
    with _CLAIM_GUARD:
        claim=(os.getpid(),str(root))
        if claim in _CLAIMS:raise FileExistsError('selector request already attempted in this process')
        _CLAIMS.add(claim)
    directories=_roots(root,INPUTS);records=[]
    def keep(name,pin=None,cap=CAP):
        raw,stamp=_read(root/name,cap)
        if pin is not None and io.digest(raw)!=io.pin(pin):raise ValueError('selector transport external pin differs')
        records.append((root/name,cap,raw,stamp))
        if name=='selector_snapshot.json':
            value=json.loads(raw)
            if type(value) is not dict or snapshot.encode(value)!=raw:raise ValueError('canonical selector snapshot required')
            return value
        return _doc(raw)
    request=keep('request.json',request_pin)
    names={'schema','root','implementation','snapshot','route','role','lane','run_configuration',
        'run_configuration_sha256','max_archive_bytes','max_timing_archive_bytes','budget','non_solver_seconds',
        'sequence_request_sha256','sequence_configuration'}|set(FLAGS)
    _object(request,names);declaration=_object(request['snapshot'],('name','size','sha256','implementation'))
    if (request['schema']!=SCHEMA or request['root']!=str(root) or request['implementation']!=implementation_identity()
            or request['route']!='source_rebuilt_timed_selector' or request['role'] not in ('reference','actual')
            or any(request[k] is not False for k in FLAGS) or Path.cwd()!=root/'scratch_non_authoritative'
            or declaration['name']!='selector_snapshot.json' or type(declaration['size']) is not int
            or not 0<declaration['size']<=snapshot.CAP or declaration['implementation']!=snapshot.implementation_identity()):
        raise ValueError('exact selector worker request required')
    for name in ('max_archive_bytes','max_timing_archive_bytes'):
        if type(request[name]) is not int or not 0<request[name]<=2**63-1:raise ValueError('bounded selector archive cap required')
    for name in ('run_configuration_sha256','sequence_request_sha256'):io.pin(request[name])
    budget=process.TaskProcessBudget(**_object(request['budget'],(f.name for f in fields(process.TaskProcessBudget))))
    if io.encode(asdict(budget))!=io.encode(request['budget']):raise ValueError('exact role budget required')
    keep('selector_snapshot.json',declaration['sha256'],snapshot.CAP)
    if len(records[-1][2])!=declaration['size']:raise ValueError('snapshot byte size differs')
    release=keep('release_intent.json');_object(release,('request_sha256','launch_sha256','child_sha256'))
    launch=keep('launch.json',release['launch_sha256'])
    _object(launch,('request_sha256','process_identity','argv','cwd','environment_sha256','budget','host'))
    child=keep('child.json',release['child_sha256'])
    _object(child,('pid','creation_filetime','process_identity','request_sha256','initial_observation_sha256'))
    hv=_object(launch['host'],('additional_commit_bytes','commit_reserve_bytes','directories'))
    if type(hv['directories']) is not list:raise ValueError('exact host directory vector required')
    resources=process.resources
    host=resources.HostResourceBudget(hv['additional_commit_bytes'],hv['commit_reserve_bytes'],
        tuple(resources.DirectoryDemand(**_object(d,(f.name for f in fields(resources.DirectoryDemand)))) for d in hv['directories']))
    if io.encode(asdict(host))!=io.encode(hv):raise ValueError('exact host declaration required')
    if not any(d.directory==str(root) and d.additional_bytes>=content_bound(request) for d in host.directories):
        raise ValueError('host declaration must cover complete selector logical archive')
    environment=dict(sorted(os.environ.items()));runtime._environment(environment)
    identity=process.task_process_identity(launch['argv'],cwd=Path.cwd(),environment=environment,budget=budget,
        host_budget=host,expected_host_identity=resources.resource_identity(host))
    pid,creation=_current_process()
    initial=keep('initial_observation.json',child['initial_observation_sha256']);_validate_initial(initial,host)
    if (release['request_sha256']!=request_pin or launch['request_sha256']!=request_pin
            or io.encode(child)!=io.encode(dict(pid=pid,creation_filetime=creation,process_identity=identity,
                request_sha256=request_pin,initial_observation_sha256=child['initial_observation_sha256']))
            or launch['process_identity']!=identity or launch['argv']!=sys.orig_argv
            or launch['cwd']!=str(Path.cwd()) or launch['environment_sha256']!=io.digest(io.encode(environment))
            or io.encode(launch['budget'])!=io.encode(request['budget'])):
        raise ValueError('released selector process identity differs')
    if _roots(root,INPUTS)!=directories or any(_read(p,cap)!=(raw,stamp) for p,cap,raw,stamp in records):
        raise ValueError('selector handshake changed before consumption')
    consumed=dict(schema=SCHEMA,request_sha256=request_pin,release_sha256=io.digest(records[2][2]),
        child_sha256=release['child_sha256'],pid=pid,creation_filetime=creation,**FLAGS)
    consume_pin=write(root/'consumed.json',consumed)
    if io.encode(keep('consumed.json',consume_pin))!=io.encode(consumed):raise ValueError('consumed record differs')
    ticket=ConsumedSelectorRequest((root,request_pin,consume_pin,pid,creation,get_ident(),directories,
        tuple(records),request['implementation']),_token=_TOKEN)
    _check(ticket,_fingerprint(ticket),INPUTS|{'consumed.json'})
    return ticket


def _match(item,raw,request):
    expected={k:request[k] for k in
            ('role','lane','run_configuration','run_configuration_sha256','max_archive_bytes','max_timing_archive_bytes',
             'budget','non_solver_seconds','sequence_request_sha256','sequence_configuration')}
    if item.snapshot!=raw or io.encode(_projection(item,request['max_timing_archive_bytes']))!=io.encode(expected):
        raise ValueError('rebuilt selector input differs from released declaration')


def execute(request_path,request_pin):
    worker=sys.modules[__name__]
    dependencies=((worker,('_match','_projection','_check','_fingerprint','_read','_roots',
        '_process_identity','_doc','_object','write','content_bound','implementation_identity',
        '_current_process','_validate_initial','released_input')),
        (snapshot,('rebuild','implementation_identity')),
        (sequence,('OwnedTimedSelectorSequence','inspect','_snapshot','_snapshot_pin','_read','_doc',
            'implementation_identity')),
        (sequence.OwnedTimedSelectorSequence,('run','validate_completion','_receipt_snapshot')),
        (sequence.timed,('_run_stage','inspect')),
        (sequence.timed.capture,('_CLOCK','clock_profile')),
        (process,('task_process_identity',)),(runtime,('_environment',)))
    originals=tuple((obj,name,getattr(obj,name)) for obj,names in dependencies for name in names)
    rebuild=snapshot.rebuild;owner_type=sequence.OwnedTimedSelectorSequence
    run=owner_type.run;validate=owner_type.validate_completion;receipt_snapshot=owner_type._receipt_snapshot
    inspect=sequence.inspect;archive_snapshot=sequence._snapshot;archive_pin=sequence._snapshot_pin
    match=_match;validate_ticket=_check;fingerprint=_fingerprint;read=_read;publish=write
    release=released_input;decode=_doc;clock=sequence.timed.capture._CLOCK
    clock_profile=sequence.timed.capture.clock_profile
    def closure_check():
        if any(getattr(obj,name) is not original for obj,name,original in originals):
            raise ValueError('selector worker callback changed')
    ticks=[clock()]
    profile=clock_profile()
    closure_check()
    ticket=release(request_path,request_pin);closure_check();pin=fingerprint(ticket)
    request=decode(ticket.records[0][2]);raw=ticket.records[1][2];root=ticket.root
    names=INPUTS|{'consumed.json'}
    def check():
        closure_check()
        validate_ticket(ticket,pin,names)
        closure_check()
        if clock_profile()!=profile:raise ValueError('selector worker clock changed')
    def tick():
        value=sequence.timed.capture.timing.integer(clock())
        if value<ticks[-1]:raise ValueError('selector worker clock reversal')
        ticks.append(value)
    check();tick()
    item=rebuild(raw,expected_sha256=request['snapshot']['sha256']);check();match(item,raw,request);check();tick()
    owner=owner_type(root/'science_sequence_non_authoritative',root/'timing_sequence_non_authoritative',
        item.frame,item.disclosure,item.before,max_archive_bytes=item.max_archive_bytes,
        max_timing_archive_bytes=request['max_timing_archive_bytes'],run_configuration=item.run_configuration,**item.arguments)
    names|={'science_sequence_non_authoritative','timing_sequence_non_authoritative'};check();tick()
    receipt=run(owner);check();tick()
    checked=validate(owner,receipt);check();tick()
    fresh=inspect(owner.root,owner.side,item.frame,item.disclosure,item.before,
        expected_terminal_sha256=receipt.terminal_sha256,max_archive_bytes=item.max_archive_bytes,
        max_timing_archive_bytes=request['max_timing_archive_bytes'],run_configuration=item.run_configuration,**item.arguments)
    check()
    if fresh!=checked or receipt.request_sha256!=request['sequence_request_sha256']:
        raise ValueError('fresh selector result differs from owned completion')
    receipt_bytes=receipt_snapshot(receipt)
    vector_bytes=io.encode(fresh['stage_vector']);native_interval=fresh['native_interval_ns']
    def output_check():
        check()
        if (receipt_snapshot(receipt)!=receipt_bytes or io.encode(fresh['stage_vector'])!=vector_bytes
                or fresh['native_interval_ns']!=native_interval
                or archive_pin(archive_snapshot(owner.root,owner.side,owner.count,item.arguments['limits'],True,True),
                    owner.root,owner.side)!=receipt.archive_view_sha256):
            raise ValueError('selector output changed after owned return')
        check()
    output_check();check();tick()
    after=rebuild(raw,expected_sha256=request['snapshot']['sha256']);check();match(after,raw,request)
    output_check();check();tick()
    vector=fresh['stage_vector']
    if (any(v['pid']!=ticket.pid or v['thread_id']!=ticket.thread_id
            or not ticks[3]<=v['stage_start_ns']<=v['native_start_ns']<=v['native_end_ns']<=v['stage_end_ns']<=ticks[4]
            for v in vector) or fresh['native_interval_ns']!=sum(v['native_interval_ns'] for v in vector)):
        raise ValueError('selector native vector outside worker run phase')
    result=dict(schema=SCHEMA,implementation=ticket.implementation,request_sha256=request_pin,
        snapshot_sha256=request['snapshot']['sha256'],consumed_sha256=ticket.consumed_sha256,
        pid=ticket.pid,creation_filetime=ticket.creation_filetime,thread_id=ticket.thread_id,
        scientific_root=str(owner.root),timing_root=str(owner.side),sequence_request_sha256=receipt.request_sha256,
        scientific_terminal_sha256=receipt.scientific_terminal_sha256,sequence_terminal_sha256=receipt.terminal_sha256,
        archive_view_sha256=receipt.archive_view_sha256,record_sha256=tuple(io.digest(r) for r in receipt.records),
        native_interval_ns=fresh['native_interval_ns'],clock=profile,**FLAGS)
    check();result_pin=publish(root/'worker_result.json',result);names.add('worker_result.json');check()
    result_view=read(root/'worker_result.json')
    if result_view[0]!=io.encode(result) or io.digest(result_view[0])!=result_pin:
        raise ValueError('published worker result differs')
    output_check();check();tick()
    terminal=dict(schema=SCHEMA,implementation=ticket.implementation,request_sha256=request_pin,
        consumed_sha256=ticket.consumed_sha256,result_sha256=result_pin,pid=ticket.pid,
        creation_filetime=ticket.creation_filetime,thread_id=ticket.thread_id,clock=profile,
        phases=tuple(dict(name=name,start_ns=ticks[i],end_ns=ticks[i+1]) for i,name in enumerate(PHASES)),
        entry_to_result_readback_ns=ticks[-1]-ticks[0],
        window_scope='execute_entry_to_result_readback_excludes_timing_terminal_and_exit',**FLAGS)
    check();terminal_pin=publish(root/'worker_timing_terminal.json',terminal);names.add('worker_timing_terminal.json')
    output_check();check()
    if (read(root/'worker_result.json')!=result_view or read(root/'worker_timing_terminal.json')[0]!=io.encode(terminal)
            or io.digest(io.encode(terminal))!=terminal_pin):raise ValueError('worker result or timing publication differs')
    return dict(result_sha256=result_pin,timing_terminal_sha256=terminal_pin,**FLAGS)
