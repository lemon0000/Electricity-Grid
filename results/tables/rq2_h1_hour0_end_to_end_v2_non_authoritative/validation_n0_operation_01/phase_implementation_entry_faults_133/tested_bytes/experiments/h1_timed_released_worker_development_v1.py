"""Released-request consumer for an owned timed hour; development API only.

No launcher or CLI. Calling execute with a real adapter needs new explicit native
authority and Job/resource supervision. Tests use a synthetic adapter in a short
Windows Job. Stored output is not parent acceptance or a formal result.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from experiments import h1_timed_worker_hour_development_v1 as worker

old, io = worker.job, worker.io
SCHEMA = 'h1_timed_released_worker_development_v1'
CAP = old.CONTENT_CAP
FLAGS = dict(worker.FLAGS, collector_integrated=False, independent_hour_jobs_integrated=False)
REQUEST_FIELDS = {'schema','root','implementation','parent_declaration','parent_identity',
    'anchor_record','pending_arguments','input_receipt','input_receipt_sha256','budget','route',*FLAGS}


def implementation_identity():
    return io.digest(io.encode([SCHEMA,worker.implementation_identity(),
                               io.digest(Path(__file__).read_bytes())]))


def write(path,doc):
    raw = io.encode(doc)
    if len(raw) > CAP: raise ValueError('released worker record cap')
    io.write_new(path,raw)
    return io.digest(raw)


def read(path,pin,cap=CAP):
    raw,stamp = io.read_stable(path,cap)
    if io.digest(raw) != io.pin(pin): raise ValueError('released worker record pin differs')
    doc = json.loads(raw)
    if io.encode(doc) != raw: raise ValueError('canonical released worker record required')
    return doc,(raw,stamp)


def unchanged(views):
    for path,(cap,view) in views.items():
        if io.read_stable(path,cap) != view:
            raise ValueError('released worker evidence changed')


def worker_view(root,count):
    return (worker._root(root),
        tuple(io.read_stable(root/name,cap) for name,cap in
              (('binding.json',io.META_CAP),('terminal.json',io.META_CAP),('execution.lock',1))),
        worker.hour._snapshot(root/'hour_non_authoritative',count,True))


def released_input(request_path,request_pin):
    """Validate launch identity, then consume exactly once before source rebuild."""
    path = old.bounded.chunks.base.local._path(request_path)
    request,request_view = read(path,request_pin)
    root = path.parent
    if not root.name.endswith('_non_authoritative'):
        raise ValueError('explicit non_authoritative released worker root required')
    if (type(request) is not dict or set(request) != REQUEST_FIELDS
            or request['schema'] != SCHEMA or request['root'] != str(root)
            or request['implementation'] != implementation_identity()
            or request['route'] != 'owned_timed_hour_development'
            or path.name != 'request.json' or Path.cwd().resolve() != root/'scratch_non_authoritative'
            or any(request[k] is not False for k in FLAGS)):
        raise ValueError('exact timed worker request required')
    if (type(request['pending_arguments']) is not dict or set(request['pending_arguments']) != {
            'expected_head','expected_source_identity','expected_request_key','expected_packet_audit'}
            or type(request['parent_declaration']) is not dict or type(request['input_receipt']) is not dict):
        raise ValueError('typed source request required')
    for pin in request['pending_arguments'].values(): io.pin(pin)
    for key in ('parent_identity','anchor_record','input_receipt_sha256'): io.pin(request[key])
    if (io.digest(io.encode(request['parent_declaration'])) != request['parent_identity']
            or io.digest(io.encode(request['input_receipt'])) != request['input_receipt_sha256']):
        raise ValueError('source declaration/receipt differs')
    budget = old.process.TaskProcessBudget(**request['budget'])
    if budget.max_elapsed_seconds > 300 or not io.same(asdict(budget),request['budget']):
        raise ValueError('short exact development budget required')
    views = {path:(CAP,request_view)}
    def keep(name,pin,cap=io.META_CAP):
        doc,view = read(root/name,pin,cap)
        views[root/name] = (cap,view)
        return doc
    release_view = io.read_stable(root/'release_intent.json',io.META_CAP)
    release_pin = io.digest(release_view[0])
    release = keep('release_intent.json',release_pin)
    if views[root/'release_intent.json'][1] != release_view: raise ValueError('release identity changed')
    launch = keep('launch.json',release['launch_sha256'],CAP)
    child = keep('child.json',release['child_sha256'])
    if type(launch) is not dict or set(launch) != {'request_sha256','process_identity','argv',
            'cwd','environment_sha256','budget','host'}:
        raise ValueError('exact launch required')
    pid,creation = old._current_process()
    environment = dict(sorted(os.environ.items()));old.runtime._environment(environment)
    hv = launch['host']
    if type(hv) is not dict or set(hv) != {'additional_commit_bytes','commit_reserve_bytes','directories'}:
        raise ValueError('exact host request required')
    if type(hv['directories']) is not list: raise ValueError('exact host directories required')
    resources = old.process.resources
    host = resources.HostResourceBudget(hv['additional_commit_bytes'],hv['commit_reserve_bytes'],
        tuple(resources.DirectoryDemand(**d) for d in hv['directories']))
    if not io.same(asdict(host),hv): raise ValueError('host request differs')
    identity = old.process.task_process_identity(launch['argv'],cwd=Path.cwd(),environment=environment,
        budget=budget,host_budget=host,expected_host_identity=resources.resource_identity(host))
    initial = keep('initial_observation.json',child['initial_observation_sha256'],CAP)
    old._validate_initial(initial,host)
    if (not io.same(release,dict(request_sha256=request_pin,launch_sha256=release['launch_sha256'],child_sha256=release['child_sha256']))
            or launch['request_sha256'] != request_pin
            or not io.same(child,dict(pid=pid,creation_filetime=creation,process_identity=identity,
                request_sha256=request_pin,initial_observation_sha256=child['initial_observation_sha256']))
            or launch['process_identity'] != identity or launch['argv'] != sys.orig_argv
            or launch['cwd'] != str(Path.cwd().resolve())
            or launch['environment_sha256'] != io.digest(io.encode(environment))
            or not io.same(launch['budget'],request['budget'])):
        raise ValueError('released exact timed worker identity required')
    consumed = dict(schema=SCHEMA,request_sha256=request_pin,release_sha256=release_pin,
        child_sha256=release['child_sha256'],pid=pid,creation_filetime=creation,**FLAGS)
    unchanged(views)
    consume_pin = write(root/'consumed.json',consumed)
    keep('consumed.json',consume_pin,CAP)
    reader = old.snapshot.open_snapshot(request['parent_declaration'],
        expected_parent_identity=request['parent_identity'],expected_anchor_record=request['anchor_record'])
    try: item = reader.pending_input(**request['pending_arguments'])
    finally: reader.close()
    item.validate(expected_receipt_sha256=request['input_receipt_sha256'])
    if item.receipt != io.encode(request['input_receipt']): raise ValueError('reconstructed worker input differs')
    unchanged(views)
    return request,item,consume_pin,pid,creation,views


def execute(request_path,request_pin):
    request,item,consume_pin,pid,creation,views = released_input(request_path,request_pin)
    root = Path(request['root'])
    unchanged(views)
    owner = worker.OwnedWorkerHour(root/'worker_non_authoritative',item.packet,item.specification,item.limits,
        controller_request_sha256=request_pin,expected_pid=pid,expected_creation_filetime=creation)
    try: result = owner.run()
    finally: owner.close()
    if (type(result) is not worker.Completion or not owner.complete or owner.poisoned
            or result.root != str(owner.root) or result.authority_flags != tuple(worker.FLAGS.items())
            or result.local_clock_binding_checked is not True):
        raise ValueError('owned worker completion required')
    count = len(worker.hour.prior.native.model_api.stage_order(item.packet.inputs))
    before = worker_view(owner.root,count)
    checked = worker.inspect(owner.root,item.packet,item.specification,item.limits,
        expected_binding_sha=owner.binding_pin,expected_terminal_sha=result.terminal_sha256,
        expected_implementation=owner.implementation)
    reader = old.snapshot.open_snapshot(request['parent_declaration'],
        expected_parent_identity=request['parent_identity'],expected_anchor_record=request['anchor_record'])
    try: fresh = reader.pending_input(**request['pending_arguments'])
    finally: reader.close()
    fresh.validate(expected_receipt_sha256=request['input_receipt_sha256'])
    if (fresh.receipt != item.receipt or fresh.packet != item.packet
            or checked['projection_payload'] != result.projection_payload
            or read(Path(request_path),request_pin)[0] != request
            or implementation_identity() != request['implementation']):
        raise ValueError('worker source/result changed')
    unchanged(views)
    if worker_view(owner.root,count) != before: raise ValueError('worker output changed before publication')
    result_pin = write(root/'worker_result.json',dict(schema=SCHEMA,request_sha256=request_pin,
        consume_sha256=consume_pin,input_receipt_sha256=request['input_receipt_sha256'],
        pid=pid,creation_filetime=creation,worker_binding_sha256=owner.binding_pin,
        worker_terminal_sha256=result.terminal_sha256,worker_implementation=owner.implementation,
        projection_sha256=io.digest(result.projection_payload),**FLAGS))
    unchanged(views)
    if worker_view(owner.root,count) != before: raise ValueError('worker output changed during publication')
    read(root/'worker_result.json',result_pin)
    return result_pin
