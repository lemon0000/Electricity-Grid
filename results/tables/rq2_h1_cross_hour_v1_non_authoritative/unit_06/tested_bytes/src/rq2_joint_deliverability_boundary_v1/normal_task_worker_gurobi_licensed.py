"""Fixed development phase worker: prepare/execute/archive or prepare/replay.

The future controller owns Job supervision, phase ordering and resource budgets.
This worker never resumes a phase or restores an executable result from JSON.
"""
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import os
from pathlib import Path
import sys

from . import normal_task_inputs_stream as inputs, normal_declared_replay_gurobi_direct as replay, normal_licensed_environment as codec


journal = replay.journal
kernel = journal.execution.kernel
ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'draft_licensed_gurobi_direct_normal_compact_task_phase_v1'
PACKET_LIMIT = 64*1024


@dataclass(frozen=True)
class LicensedGurobiDirectNormalTaskRequest:
    source: inputs.legacy.NormalTaskSourceRequest
    expected_source_request_identity: str
    specification: kernel.Rq2SolverSpec
    execution_budget: kernel.NormalExecutionBudget
    expected_normal_execution_identity: str
    expected_source_execution_identity: str
    expected_declared_execution_identity: str
    expected_assembly_identity: str
    expected_binding_identity: str
    expected_source_implementation_identity: str
    expected_binding_implementation_identity: str
    expected_replay_identity: str
    max_record_bytes: int
    max_replay_bytes: int

    def __post_init__(self):
        if type(self.source) is not inputs.legacy.NormalTaskSourceRequest:
            raise ValueError('typed compact task source required')
        self.source.__post_init__()
        for name in ('expected_source_request_identity', 'expected_normal_execution_identity',
                     'expected_source_execution_identity', 'expected_replay_identity',
                     'expected_declared_execution_identity', 'expected_assembly_identity',
                     'expected_binding_identity', 'expected_source_implementation_identity',
                     'expected_binding_implementation_identity'):
            kernel._pin(getattr(self, name))
        kernel._validate(self.specification, self.execution_budget, self.source.expected_scale)
        for name in ('max_record_bytes', 'max_replay_bytes'):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= 256*1024**2:
                raise ValueError('explicit task archive byte budget in (0, 256 MiB] required')


def _construct(cls, body):
    if type(body) is not dict or set(body) != {field.name for field in fields(cls)}:
        raise ValueError('exact compact '+cls.__name__+' field inventory required')
    return cls(**body)


def decode_request(body):
    if type(body) is not dict:
        raise ValueError('compact task mapping required')
    value = dict(body)
    source = dict(value['source'])
    source['expected_scale'] = _construct(kernel.Rq2ModelScale, source['expected_scale'])
    value['source'] = _construct(inputs.legacy.NormalTaskSourceRequest, source)
    value['specification'] = _construct(kernel.Rq2SolverSpec, value['specification'])
    value['execution_budget'] = _construct(kernel.NormalExecutionBudget, value['execution_budget'])
    result = _construct(LicensedGurobiDirectNormalTaskRequest, value)
    if journal._bytes(asdict(result)) != journal._bytes(body):
        raise ValueError('canonical compact task representation required')
    return result


def task_identity(request):
    if type(request) is not LicensedGurobiDirectNormalTaskRequest:
        raise ValueError('typed compact normal task request required')
    request.__post_init__()
    if (inputs.task_source_identity(request.source) != request.expected_source_request_identity
            or kernel.normal_execution_identity(request.source.expected_input_identity,
                request.source.expected_scale, request.specification, request.execution_budget)
                != request.expected_normal_execution_identity
            or inputs.source_normal.implementation_identity() != request.expected_source_implementation_identity
            or inputs.stream_binding.implementation_identity() != request.expected_binding_implementation_identity
            or journal.execution.declared_execution_identity(request.source,
                expected_request_identity=request.expected_source_request_identity,
                expected_source_execution_identity=request.expected_source_execution_identity)
                != request.expected_declared_execution_identity
            or replay.replay_identity(request.expected_declared_execution_identity,
                request.specification, request.execution_budget) != request.expected_replay_identity):
        raise ValueError('compact task external implementation pins differ')
    raw = journal._bytes(asdict(request))
    if len(raw) > PACKET_LIMIT:
        raise ValueError('compact normal task request too large')
    return sha256(journal._bytes((SCHEMA, raw.decode('ascii'),
        tuple((str(Path(m.__file__).resolve()), sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (inputs, replay, codec, codec.legacy, codec.process, journal, journal.local)),
        sha256(Path(__file__).read_bytes()).hexdigest(), str(Path(sys.executable).resolve()),
        sha256(Path(sys.executable).read_bytes()).hexdigest()))).hexdigest()


def worker_argv(packet_path, digest):
    kernel._pin(digest)
    script = ('import sys; sys.path.insert(0, '+repr(str(ROOT))+'); '
        'from src.rq2_joint_deliverability_boundary_v1.normal_task_worker_gurobi_licensed import main; main()')
    return [str(Path(sys.executable).resolve()), '-I', '-B', '-c', script, str(packet_path), digest]


def phase_packet(root, phase, request, environment, *, expected_task_identity, replay_pins=None):
    """Build only a small declaration; no source files, models or child processes."""
    root = journal.local._path(root)
    if not root.name.endswith('_non_authoritative') or phase not in ('execute', 'replay'):
        raise ValueError('explicit development root and task phase required')
    if task_identity(request) != expected_task_identity:
        raise ValueError('external compact task identity mismatch')
    codec._environment(environment)
    scratch = root/(phase+'_non_authoritative')
    if any(os.path.normcase(environment[name]) != os.path.normcase(str(scratch)) for name in ('TEMP', 'TMP')):
        raise ValueError('task phase needs its dedicated scratch cwd/TEMP/TMP')
    if phase == 'execute':
        if replay_pins is not None:
            raise ValueError('execution phase cannot take replay pins')
    else:
        if type(replay_pins) is not dict or set(replay_pins) != {
                'store_identity', 'head', 'record_sha256', 'claimed_result_identity'}:
            raise ValueError('complete independently captured replay pins required')
        for value in replay_pins.values(): kernel._pin(value)
    packet = dict(schema=SCHEMA, root=str(root), phase=phase, request=asdict(request),
        task_identity=expected_task_identity, environment=environment, replay_pins=replay_pins)
    raw = journal._bytes(packet)
    if len(raw) > PACKET_LIMIT:
        raise ValueError('compact phase packet too large')
    return raw


def _read(path, expected_digest=None):
    before = journal.local._file_identity(path)
    with path.open('rb') as stream: raw = stream.read(PACKET_LIMIT+1)
    if (len(raw) > PACKET_LIMIT or journal.local._file_identity(path) != before
            or (expected_digest is not None and sha256(raw).hexdigest() != expected_digest)):
        raise ValueError('phase file size/identity/digest mismatch')
    return journal._decoded(raw)


def _write(path, body, maximum=PACKET_LIMIT):
    raw = journal._bytes(body)
    if len(raw) > maximum:
        raise ValueError('complete task phase artifact exceeds byte budget')
    codec._write_once(path, raw)
    return sha256(raw).hexdigest(), len(raw)


def _creation_filetime():
    process = codec.process
    creation, end, cpu_kernel, user = (process.w.FILETIME() for _ in range(4))
    process._check(process._api().GetProcessTimes(process.HANDLE(-1), process.c.byref(creation),
        process.c.byref(end), process.c.byref(cpu_kernel), process.c.byref(user)))
    return creation.dwLowDateTime | (creation.dwHighDateTime << 32)


def _execution_arguments(request):
    return dict(expected_request_identity=request.expected_source_request_identity,
        expected_declared_execution_identity=request.expected_declared_execution_identity,
        expected_assembly_identity=request.expected_assembly_identity,
        expected_binding_identity=request.expected_binding_identity,
        expected_source_implementation_identity=request.expected_source_implementation_identity,
        expected_binding_implementation_identity=request.expected_binding_implementation_identity,
        expected_normal_execution_identity=request.expected_normal_execution_identity,
        expected_source_execution_identity=request.expected_source_execution_identity,
        specification=request.specification, budget=request.execution_budget)


def worker(packet_path, digest):
    kernel._pin(digest)
    path = journal.local._path(packet_path)
    packet = _read(path, digest)
    if type(packet) is not dict or set(packet) != {
            'schema', 'root', 'phase', 'request', 'task_identity', 'environment', 'replay_pins'}:
        raise ValueError('exact phase packet inventory required')
    request = decode_request(packet['request'])
    raw = phase_packet(packet['root'], packet['phase'], request, packet['environment'],
        expected_task_identity=packet['task_identity'], replay_pins=packet['replay_pins'])
    root, phase = journal.local._path(packet['root']), packet['phase']
    scratch = journal.local._path(root/(phase+'_non_authoritative'))
    journal.local._local_ntfs(root)
    if (sha256(raw).hexdigest() != digest or path != root/(phase+'.request.json')
            or Path.cwd() != scratch or dict(os.environ) != packet['environment']
            or sys.orig_argv != worker_argv(path, digest)):
        raise ValueError('task phase runtime differs from fixed request')
    intent = dict(schema=SCHEMA, phase=phase, packet_sha256=digest, task_identity=packet['task_identity'])
    intent_path, launch_path = root/(phase+'.intent.json'), root/(phase+'.launch.json')
    if _read(intent_path) != intent:
        raise ValueError('persisted phase intent mismatch')
    root_info, scratch_info = root.stat(), scratch.stat()
    launch = dict(**intent, pid=os.getpid(), creation_filetime=_creation_filetime(),
        argv_sha256=sha256(journal._bytes(sys.orig_argv)).hexdigest(),
        root_identity=[root_info.st_dev, root_info.st_ino],
        scratch_identity=[scratch_info.st_dev, scratch_info.st_ino])
    if journal._bytes(_read(launch_path)) != journal._bytes(launch):
        raise ValueError('persisted phase launch mismatch')
    retained_files = {file: journal.local._file_identity(file) for file in (path, intent_path, launch_path)}
    launch_sha = sha256(journal._bytes(launch)).hexdigest()
    claim = dict(**intent, pid=os.getpid(), launch_sha256=launch_sha)
    _write(root/(phase+'.claim.json'), claim)  # Exclusive, durable before preparation.
    claim_path = root/(phase+'.claim.json')
    retained_files[claim_path] = journal.local._file_identity(claim_path)

    def postcheck():
        if (Path.cwd() != scratch or dict(os.environ) != packet['environment']
                or sys.orig_argv != worker_argv(path, digest) or os.getpid() != launch['pid']
                or _creation_filetime() != launch['creation_filetime']
                or task_identity(request) != packet['task_identity'] or _read(path, digest) != packet
                or _read(intent_path) != intent or _read(launch_path) != launch or _read(claim_path) != claim
                or any(journal.local._file_identity(file) != identity for file, identity in retained_files.items())
                or (root.stat().st_dev, root.stat().st_ino) != tuple(launch['root_identity'])
                or (scratch.stat().st_dev, scratch.stat().st_ino) != tuple(launch['scratch_identity'])):
            raise ValueError('task phase request/implementation/path drift')

    # Exceptions deliberately leave intent/claim and any old store records.
    # No best-effort diagnostic write can obscure the original failure.
    arguments = _execution_arguments(request)
    postcheck()
    normal_root = root/'normal_non_authoritative'
    if phase == 'execute':
        with journal.DevelopmentDeclaredGurobiDirectNormalStore(normal_root, request.source, create=True, max_record_bytes=request.max_record_bytes, **arguments) as store:
            _, inspection = store.execute(before_source=postcheck)
        completion = dict(store_identity=inspection.store_identity, head=inspection.head,
            record_sha256=inspection.archived_result_sha256, claimed_result_identity=inspection.result_identity)
    else:
        pins = packet['replay_pins']
        result = replay.replay_normal_store(normal_root, request.source, expected_head=pins['head'], expected_record_sha256=pins['record_sha256'],
            expected_result_identity=pins['claimed_result_identity'], expected_replay_identity=request.expected_replay_identity,
            max_record_bytes=request.max_record_bytes, **arguments)
        # The existing replay store API validates its own source/header binding;
        # also retain the controller's independently captured store identity.
        with journal.DevelopmentDeclaredGurobiDirectNormalStore(normal_root, request.source, create=False, expected_head=pins['head'],
                max_record_bytes=request.max_record_bytes, **arguments) as store:
            if store.inspect().store_identity != pins['store_identity']:
                raise ValueError('captured store identity differs during task replay')
        postcheck()
        report_sha, report_size = _write(root/'replay.result.json', kernel._encode(result), request.max_replay_bytes)
        completion = dict(replay_result_sha256=report_sha, replay_result_bytes=report_size,
            status=result.status, archive_consistent=result.archive_consistent,
            accepted_record_reproduced=result.accepted_record_reproduced)
    postcheck()
    _write(root/(phase+'.complete.json'), dict(**claim, completion=completion,
        numerical_acceptance_by_controller=False, formal_result=False))


def main():
    if len(sys.argv) != 3:
        raise ValueError('fixed task worker requires packet path and digest')
    worker(Path(sys.argv[1]), sys.argv[2])
