"""One-shot development selector supervision; no resume or numerical authority."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import sys

from . import scale_selector_zero_face_worker as worker, normal_task_process as process
from . import scale_episode_controller as supervision

SCHEMA = 'draft_mixed_selector_controller_v1'
LIMIT = 16*1024**2
local = worker.store.local


def controller_identity(root, request, *, budget, host_budget, environment, max_record_bytes):
    root = local._path(root)
    if not root.name.endswith('_non_authoritative'):
        raise ValueError('non_authoritative task root required')
    if type(budget) is not process.TaskProcessBudget:
        raise ValueError('typed process budget required')
    budget.__post_init__()
    if type(environment) is not dict:
        raise ValueError('explicit environment required')
    process.process._environment_block(environment)
    if type(max_record_bytes) is not int or not 0 < max_record_bytes <= LIMIT:
        raise ValueError('bounded record bytes required')
    packet = worker.export_request(request)
    if len(packet) > LIMIT:
        raise ValueError('request exceeds transport limit')
    worker.decode_request(packet)
    if type(host_budget) is not process.resources.HostResourceBudget:
        raise ValueError('typed host budget required')
    host_budget.__post_init__()
    parent_host = process.resources.HostResourceBudget(host_budget.additional_commit_bytes,
        host_budget.commit_reserve_bytes, tuple(process.resources.DirectoryDemand(
            item.name, str(root.parent), item.additional_bytes, item.reserve_bytes)
            for item in host_budget.directories))
    host_pin = process.resources.resource_identity(parent_host)
    scratch = root/'scratch'
    directories = {os.path.normcase(str(local._path(x.directory))) for x in host_budget.directories}
    if (os.path.normcase(str(root)) not in directories
            or os.path.normcase(str(scratch)) not in directories
            or host_budget.additional_commit_bytes < budget.max_job_commit_bytes):
        raise ValueError('explicit archive/scratch and Job demand required')
    return worker.codec._digest(SCHEMA, str(root), packet.decode('ascii'), asdict(budget),
        host_pin, asdict(host_budget), environment, max_record_bytes, worker.implementation_identity(),
        tuple((str(m.__file__), sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (process, process.process, process.resources, local, supervision)),
        sha256(Path(__file__).read_bytes()).hexdigest(), str(Path(sys.executable).resolve()),
        sha256(Path(sys.executable).read_bytes()).hexdigest())


def _write(path, body):
    raw = worker.store._bytes(body)
    if len(raw) > LIMIT:
        raise ValueError('controller record exceeds limit')
    with path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise OSError('controller short write')
        stream.flush()
        os.fsync(stream.fileno())
        info = os.fstat(stream.fileno())
    identity = (info.st_dev, info.st_ino)
    if worker.store._bytes(_read(path, identity)) != raw:
        raise ValueError('controller exact readback mismatch')
    return identity, sha256(raw).hexdigest()


def _read(path, identity=None):
    before = local._file_identity(path)
    if identity is not None and before != identity:
        raise ValueError('controller record replaced')
    with path.open('rb') as stream:
        raw = stream.read(LIMIT+1)
    if len(raw) > LIMIT or local._file_identity(path) != before:
        raise ValueError('controller read limit/identity mismatch')
    return worker.store._decoded(raw)


def _inspect(root, body, request, maximum):
    lease = local._Lease(root, False)
    try:
        path = root/'selector.sqlite3'
        identity = local._file_identity(path)
        report, record = worker.store._read(path, body['store_binding_identity'], maximum)
        db = worker.store._connect(path, True)
        try:
            header = worker.store._decoded(db.execute('SELECT payload FROM metadata WHERE id=1').fetchone()[0])
        finally:
            db.close()
        if (worker.store._bytes(header['request']) != worker.store._bytes(worker.codec._encode(request))
                or record is None or record['result_identity'] != body['result_identity']
                or worker.store._fields(record['encoded_result'], worker.scale.MixedSelectionResult)['status']
                   != body['reported_status']):
            raise ValueError('receipt archived request/result mismatch')
        lease.check()
        if local._file_identity(path) != identity:
            raise ValueError('selector archive replaced')
        return report
    finally:
        lease.close()


def _validate_observation(observed, budget, host_budget, pin, pid, creation):
    if type(observed) is not process.TaskProcessObservation:
        raise ValueError('typed mixed selector process observation required')
    supervision._successful_observation(observed, budget, host_budget)
    if (observed.process_identity != pin or observed.pid != pid
            or observed.creation_filetime != creation):
        raise ValueError('mixed selector process crosslink mismatch')


def supervise_selector(root, request, *, budget, host_budget, environment,
                       max_record_bytes, expected_controller_identity):
    request, budget, host_budget, environment = deepcopy((request, budget, host_budget, environment))
    root = local._path(root)
    settings = dict(budget=budget, host_budget=host_budget, environment=environment,
                    max_record_bytes=max_record_bytes)
    def identity_check():
        if controller_identity(root, request, **settings) != expected_controller_identity:
            raise ValueError('controller input/implementation drift')
    identity_check()
    lease = object.__new__(local._Lease)
    retained = {}
    def write(name, body):
        retained[root/name] = _write(root/name, body)
    def check():
        lease.check()
        identity_check()
        for path, (identity, digest) in retained.items():
            if sha256(worker.store._bytes(_read(path, identity))).hexdigest() != digest:
                raise ValueError('controller retained record drift')
    try:
        local._Lease.__init__(lease, root, True)
        scratch = root/'scratch'
        scratch.mkdir()
        packet = worker.export_request(request)
        packet_pin = sha256(packet).hexdigest()
        impl = worker.implementation_identity()
        write('request.json', worker.store._decoded(packet))
        store_root, receipt = root/'selector_non_authoritative', root/'receipt_non_authoritative.json'
        argv = [str(Path(sys.executable).resolve()), '-I', '-B', str(Path(worker.__file__).resolve()),
            '--request-path', str(root/'request.json'), '--expected-request-sha256', packet_pin,
            '--store-root', str(store_root), '--receipt-path', str(receipt),
            '--max-request-bytes', str(LIMIT), '--max-record-bytes', str(max_record_bytes),
            '--expected-implementation-identity', impl]
        phase = dict(cwd=scratch, environment=dict(environment, TEMP=str(scratch), TMP=str(scratch)),
            budget=budget, host_budget=host_budget,
            expected_host_identity=process.resources.resource_identity(host_budget))
        pin = process.task_process_identity(argv, **phase)
        write('intent.json', dict(schema=SCHEMA, controller_identity=expected_controller_identity,
            request_sha256=packet_pin, implementation_identity=impl, process_identity=pin,
            budget=asdict(budget), host_budget=asdict(host_budget),
            planned_solver_calls=request.budget.max_solver_calls,
            reserved_solver_seconds=request.budget.max_total_solver_seconds,
            formal_result=False))
        check()
        with process.normal_task_child(argv, expected_process_identity=pin, **phase) as child:
            write('launch.json', dict(process_identity=pin, pid=child.pid,
                creation_filetime=child.creation_filetime))
            check()
            child.release()
            observed = child.wait()
            if (type(observed) is not process.TaskProcessObservation
                    or observed.process_identity != pin or observed.pid != child.pid
                    or observed.creation_filetime != child.creation_filetime
                    or observed.whole_job_quiescent is not True):
                raise ValueError('unverified process identity/quiescence')
        write('observation.json', asdict(observed))
        check()
        _validate_observation(observed, budget, host_budget, pin, child.pid, child.creation_filetime)
        body = _read(receipt)
        if (type(body) is not dict or set(body) != {'schema', 'request_sha256',
                'implementation_identity', 'store_binding_identity', 'result_identity',
                'reported_status', 'inspection', 'formal_result', 'whole_task_resources_verified'}):
            raise ValueError('exact worker receipt fields required')
        if (body.get('schema') != worker.SCHEMA or body.get('request_sha256') != packet_pin
                or body.get('implementation_identity') != impl
                or body.get('formal_result') is not False
                or body.get('whole_task_resources_verified') is not False):
            raise ValueError('worker receipt binding/authority mismatch')
        inspection = _inspect(store_root, body, request, max_record_bytes)
        if (worker.store._bytes(inspection) != worker.store._bytes(body['inspection'])
                or inspection['status'] != 'returned_unverified'):
            raise ValueError('worker receipt/store mismatch')
        check()
        result = dict(schema=SCHEMA, controller_identity=expected_controller_identity,
            status='returned_unverified', receipt_sha256=sha256(worker.store._bytes(body)).hexdigest(),
            inspection=inspection, observation=asdict(observed), formal_result=False,
            whole_task_resources_verified=False, numerical_evidence_verified=False,
            executable_resume_available=False)
        write('result.json', result)
        return result
    finally:
        if getattr(lease, 'stream', None) is not None:
            lease.close()
