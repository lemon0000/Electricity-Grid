"""One-shot development normal worker and parent reconciliation, no replay seal."""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from hashlib import sha256
import math
import os
from pathlib import Path
import sys
import tempfile

from . import normal_process as process, normal_store as journal
from .source_normal import SourceNormalAssembly
from .source_pair import PairDeclaration
from .continuous_grid_normal import ContinuousNormalInputs, _encode
from .grid_carry import GridIdentity, GridCarry, UnitLimits, UnitPoint
from ..grid.chronological_dispatch import ChronologicalDispatchRequest
from ..grid.rts_gmlc_scuc import RtsGmlcInitialState
from ..grid.rts_gmlc import (RtsGmlcChronologicalData, RtsGmlcBus, RtsGmlcBranch,
    RtsGmlcDcBranch, RtsGmlcChronologicalGenerator, RtsGmlcHourlyPoint)
from ..evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from ..evaluation.chronology_inputs import GridIncident


SCHEMA = 'draft_one_normal_worker_reconciliation_v1'
ROOT = Path(__file__).resolve().parents[2]
kernel = journal.execution.kernel
_TYPES = {cls.__name__: cls for cls in (SourceNormalAssembly, PairDeclaration,
    ContinuousNormalInputs, GridIdentity, GridCarry, UnitLimits, UnitPoint,
    ChronologicalDispatchRequest, RtsGmlcInitialState, RtsGmlcChronologicalData,
    RtsGmlcBus, RtsGmlcBranch, RtsGmlcDcBranch, RtsGmlcChronologicalGenerator,
    RtsGmlcHourlyPoint, ChronologicalFlexibilityEnvelope, GridIncident,
    kernel.NormalExecutionBudget, kernel.Rq2SolverSpec, kernel.Rq2ModelScale)}


def _decode(value):
    """Input-only allowlist; cannot manufacture owned solver/witness objects."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is not list or len(value) != 2 or type(value[0]) is not str:
        raise ValueError('invalid typed normal input encoding')
    tag, body = value
    if tag == 'float':
        result = float.fromhex(body)
        if not math.isfinite(result):
            raise ValueError('nonfinite normal input')
    elif tag == 'datetime':
        result = datetime.fromisoformat(body)
    elif tag in ('tuple', 'list', 'set'):
        result = {'tuple': tuple, 'list': list, 'set': frozenset}[tag](_decode(x) for x in body)
    elif tag == 'mapping':
        pairs = [(_decode(k), _decode(v)) for k, v in body]
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError('duplicate normal input mapping key')
    elif tag in _TYPES:
        cls = _TYPES[tag]
        if [row[0] for row in body] != [f.name for f in fields(cls)]:
            raise ValueError('exact ordered normal input fields required')
        result = cls(**{key: _decode(x) for key, x in body})
    else:
        raise ValueError('normal input type not allowed: '+tag)
    if _encode(result) != value:
        raise ValueError('noncanonical typed normal input')
    return result


@dataclass(frozen=True)
class NormalWorkerBudget:
    max_child_seconds: float
    max_process_commit_bytes: int
    max_job_commit_bytes: int
    max_request_bytes: int
    max_record_bytes: int
    max_quiescence_seconds: float

    def __post_init__(self):
        for name, cap in (('max_child_seconds', 60), ('max_quiescence_seconds', 5)):
            x = getattr(self, name)
            if type(x) not in (int, float) or not math.isfinite(x) or not 0 < x <= cap:
                raise ValueError('invalid development worker time budget')
        for name in ('max_process_commit_bytes', 'max_job_commit_bytes', 'max_request_bytes', 'max_record_bytes'):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError('positive explicit worker byte budget required')
        if (self.max_process_commit_bytes > self.max_job_commit_bytes
                or self.max_job_commit_bytes > process.SIZE_T(-1).value
                or self.max_request_bytes > 256*1024**2):
            raise ValueError('worker process/job/request budget mismatch')


def development_environment():
    """Explicit Windows/Python runtime paths; no wholesale parent inheritance."""
    prefix = Path(sys.executable).resolve().parent
    windows = Path(os.environ['SYSTEMROOT']).resolve()
    scratch = str(Path(tempfile.gettempdir()).resolve())
    return dict(SYSTEMROOT=str(windows), WINDIR=str(windows), TEMP=scratch, TMP=scratch,
        PATH=os.pathsep.join(map(str, (prefix, prefix/'Library'/'bin', windows/'System32', windows))),
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
        KMP_DUPLICATE_LIB_OK='True')


def _environment(environment):
    process._environment_block(environment)
    required = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH', 'OMP_NUM_THREADS',
                'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'KMP_DUPLICATE_LIB_OK'}
    if (set(environment) != required or environment['KMP_DUPLICATE_LIB_OK'] != 'True'
            or any(environment[k] != '1' for k in required if k.endswith('_NUM_THREADS'))):
        raise ValueError('exact explicit development runtime environment required')


def supervision_identity(source_execution_identity, budget, environment):
    kernel._pin(source_execution_identity)
    if type(budget) is not NormalWorkerBudget:
        raise ValueError('typed worker budget required')
    budget.__post_init__()
    _environment(environment)
    sources = tuple((str(Path(m.__file__).relative_to(ROOT)), sha256(Path(m.__file__).read_bytes()).hexdigest())
        for m in (process, journal, journal.local))
    return kernel._digest(SCHEMA, source_execution_identity, asdict(budget), environment,
        sha256(Path(__file__).read_bytes()).hexdigest(), sources,
        str(Path(sys.executable).resolve()), sha256(Path(sys.executable).read_bytes()).hexdigest())


def _write_once(path, raw):
    journal.local._path(path)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    journal.local._file_identity(path)
    if path.read_bytes() != raw:
        raise ValueError('worker record readback mismatch')


def _read_request(path, digest, max_bytes):
    kernel._pin(digest)
    identity = journal.local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(max_bytes+1)
    if len(raw) > max_bytes or sha256(raw).hexdigest() != digest:
        raise ValueError('worker request size/hash mismatch')
    if journal.local._file_identity(path) != identity:
        raise ValueError('worker request file replaced')
    return journal._decoded(raw)


def _worker_argv(request, digest, max_bytes):
    script = ('import sys; sys.path.insert(0, '+repr(str(ROOT))+'); '
              'from src.rq2_joint_deliverability_boundary_v1.normal_worker import main; main()')
    return [str(Path(sys.executable).resolve()), '-I', '-B', '-c', script,
            str(request), digest, str(max_bytes)]


def worker(request_path, digest, max_bytes):
    if type(max_bytes) is not int or not 0 < max_bytes <= 256*1024**2:
        raise ValueError('bounded worker request required')
    path = journal.local._path(request_path)
    packet = _read_request(path, digest, max_bytes)
    if set(packet) != {'schema', 'root', 'genesis', 'inputs', 'budget', 'environment', 'supervision_identity'}:
        raise ValueError('exact worker packet schema required')
    if packet['schema'] != SCHEMA or path != Path(packet['root'])/'request.json':
        raise ValueError('worker request location/schema mismatch')
    budget = NormalWorkerBudget(**packet['budget'])
    if budget.max_request_bytes != max_bytes:
        raise ValueError('worker request byte budget drift')
    assembly, upstream, declaration, arguments = _decode(packet['inputs'])
    expected = packet['supervision_identity']
    if supervision_identity(arguments['expected_source_execution_identity'], budget, packet['environment']) != expected:
        raise ValueError('worker implementation identity drift')
    if dict(os.environ) != packet['environment']:
        raise ValueError('worker environment differs from declared block')
    root = path.parent
    launch = journal._decoded((root/'launch.json').read_bytes())
    if (launch['pid'] != os.getpid() or launch['request_sha256'] != digest
            or launch['supervision_identity'] != expected or launch['argv'] != sys.orig_argv
            or launch['argv_sha256'] != sha256(journal._bytes(sys.orig_argv)).hexdigest()):
        raise ValueError('worker launch identity mismatch')
    launch_digest = sha256(journal._bytes(launch)).hexdigest()
    # Exclusive claim remains even if the process dies before normal intent.
    _write_once(root/'worker_claim.json', journal._bytes(dict(pid=os.getpid(), request_sha256=digest,
        launch_sha256=launch_digest)))
    try:
        with journal.DevelopmentNormalStore(root/'normal_non_authoritative', assembly, upstream, declaration,
                create=False, expected_head=packet['genesis'], max_record_bytes=budget.max_record_bytes,
                **arguments) as store:
            store.execute()
    except BaseException as error:
        _write_once(root/'worker_error.json', journal._bytes(dict(type=type(error).__name__, message=str(error))))
        raise


def main():
    worker(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]))


@dataclass(frozen=True)
class NormalWorkerObservation:
    request_sha256: str
    launch_sha256: str
    supervision_identity: str
    process: process.ProcessObservation
    store: journal.NormalStoreInspection
    whole_job_quiescent: bool
    status: str
    numerical_evidence_replayed: bool = False
    native_execution_authenticated: bool = False
    formal_result: bool = False


def supervise_normal(root, assembly, upstream_root, declaration, *, worker_budget, environment,
                     expected_supervision_identity, **arguments):
    """Fresh one-shot development attempt; never resumes an existing directory."""
    assembly, declaration, arguments, environment = deepcopy((assembly, declaration, arguments, environment))
    budget = worker_budget
    upstream = str(Path(upstream_root).resolve())
    arguments['config_path'] = str(Path(arguments.get('config_path', journal.execution.source_window.audit.DEFAULT_CONFIG)).resolve())
    expected = supervision_identity(arguments['expected_source_execution_identity'], budget, environment)
    if expected != expected_supervision_identity:
        raise ValueError('external normal supervision identity mismatch')
    encoded = _encode((assembly, upstream, declaration, arguments))
    # Roundtrip before acquiring a new directory or allowing child execution.
    if _encode(_decode(encoded)) != encoded:
        raise ValueError('normal worker input roundtrip mismatch')
    with_lease = journal.local._Lease(root, True)
    try:
        root = with_lease.root
        normal_root = root/'normal_non_authoritative'
        with journal.DevelopmentNormalStore(normal_root, assembly, upstream, declaration, create=True,
                max_record_bytes=budget.max_record_bytes, **arguments) as store:
            genesis = store.inspect().head
        packet = dict(schema=SCHEMA, root=str(root), genesis=genesis, inputs=encoded,
            budget=asdict(budget), environment=environment, supervision_identity=expected)
        raw = journal._bytes(packet)
        if len(raw) > budget.max_request_bytes:
            raise ValueError('complete worker request exceeds byte budget')
        digest = sha256(raw).hexdigest()
        request = root/'request.json'
        _write_once(request, raw)
        # Even an attempt that dies before launch cannot reuse this outer root.
        intent_raw = journal._bytes(dict(request_sha256=digest,
            supervision_identity=expected, normal_genesis=genesis))
        _write_once(root/'launch_intent.json', intent_raw)
        argv = _worker_argv(request, digest, budget.max_request_bytes)
        with process.DevelopmentNormalChild(argv,
                cwd=ROOT, max_process_commit_bytes=budget.max_process_commit_bytes,
                max_job_commit_bytes=budget.max_job_commit_bytes, environment=environment) as child:
            launch_raw = journal._bytes(dict(pid=child.pid,
                creation_filetime=child.creation_filetime, request_sha256=digest,
                supervision_identity=expected, argv=argv, argv_sha256=sha256(journal._bytes(argv)).hexdigest()))
            _write_once(root/'launch.json', launch_raw)
            child.release()
            observed = child.wait(max_elapsed_seconds=budget.max_child_seconds)
            child.quiesce(max_seconds=budget.max_quiescence_seconds)
        # No result reads occur unless the whole Job was confirmed inactive.
        with_lease.check()
        if (_read_request(request, digest, budget.max_request_bytes) != packet
                or supervision_identity(arguments['expected_source_execution_identity'], budget, environment) != expected):
            raise ValueError('post-worker request or implementation drift')
        for name, expected_raw in (('launch_intent.json', intent_raw), ('launch.json', launch_raw)):
            journal.local._file_identity(root/name)
            if (root/name).read_bytes() != expected_raw:
                raise ValueError('post-worker launch record drift')
        claimed = (root/'worker_claim.json').exists()
        if claimed:
            journal.local._file_identity(root/'worker_claim.json')
            if (root/'worker_claim.json').read_bytes() != journal._bytes(dict(pid=observed.pid,
                    request_sha256=digest, launch_sha256=sha256(launch_raw).hexdigest())):
                raise ValueError('worker claim differs from launched process')
        with journal.DevelopmentNormalStore(normal_root, assembly, upstream, declaration, create=False,
                expected_head=genesis, max_record_bytes=budget.max_record_bytes, **arguments) as store:
            inspection = store.inspect()
        status = ('returned_record_unreplayed' if observed.reason == 'child_exited' and observed.exit_code == 0
            and observed.elapsed_seconds <= budget.max_child_seconds and claimed and inspection.result_present
            else 'unresolved_worker_attempt')
        outcome = NormalWorkerObservation(digest, sha256(launch_raw).hexdigest(), expected, observed, inspection, True, status)
        _write_once(root/'observation.json', journal._bytes(asdict(outcome)))
        return outcome
    finally:
        with_lease.close()
