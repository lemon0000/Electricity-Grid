"""Draft saved-P1 F protocol; pre-import validation uses only the stdlib."""
from hashlib import sha256
from dataclasses import dataclass
from contextlib import contextmanager
import ctypes as C
from ctypes import wintypes as W
import json
import math
import os
from pathlib import Path
import secrets
import stat
import struct
import subprocess
import sys
import tempfile
from threading import get_ident
import time

ROOT = Path(__file__).absolute().parents[1]
P1 = ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
SCOPE = 'saved_P1_actual_21_and_journal_5h'
SCHEMA = 'staged_rts24_saved_P1_fresh_context_development_v1'
EXE = Path('D:/Miniconda3/envs/compute/python.exe')
OUTPUT = ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01'
ANCHOR_SHA = 'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
INHERITED = ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01/component_source_pins.json'
INHERITED_SHA = '697573785464aa37bb4d71df1956d9de1b4888dd2d26ad4a61748eff6ced3c2c'
NEW_SOURCES = ('src/staged_rts24_saved_fresh_adoption_v1.py',
    'experiments/staged_rts24_saved_fresh_adoption_v1.py',
    'tests/test_staged_rts24_saved_fresh_adoption_v1.py',
    'docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md')
TARGETS = tuple(('context.json worker/parent_startup.json worker/events.jsonl worker/parent.stdout.log '
    'worker/parent.stderr.log worker/parent_metrics.json worker/comparison_candidate.json '
    'worker/fresh/startup.json worker/fresh/events.jsonl worker/fresh/stdout.log worker/fresh/stderr.log '
    'worker/fresh/metrics.json worker/fresh/launcher.json worker/fresh_parent/parent_observation.json '
    'worker/launcher.json parent/parent_observation.json diagnostics/failure.json').split())
RECORDS = ('worker/fresh/launcher.json', 'worker/fresh_parent/parent_observation.json',
    'worker/launcher.json', 'parent/parent_observation.json')
CAPS = dict(wall_seconds=180, no_progress_seconds=65, rss_bytes=1024**3,
    process_commit_bytes=1024**3, job_commit_bytes=2*1024**3, output_bytes=8*1024**2,
    files=64, member_handles=1024, record_bytes=131072)
STAGE_SECONDS = dict(prepare=10, parent=45, fresh=40, inner_quiesce=5, inner_terminal=5,
    parent_compare=15, outer_quiesce=5, outer_terminal=10, final_check=15, final_publish=15, failure=15)
GATES = dict(native_authorized=False, resource_admission=False, formal_result=False,
    scientific_evidence_adopted=False, public_P2_execution_enabled=False)


def require(value, message):
    if not value: raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def keys(value, fields):
    require(type(value) is dict and set(value) == set(fields.split()), 'closed fields required')


def parse(raw):
    require(type(raw) is bytes and len(raw) <= 8*1024**2, 'bounded JSON bytes required')
    depth = nodes = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted, nodes = True, nodes+1
        elif byte in (91, 123): depth, nodes = depth+1, nodes+1
        elif byte in (93, 125): depth -= 1
        elif byte == 44: nodes += 1
        require(0 <= depth <= 256 and nodes <= 1000000, 'JSON complexity limit')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(value): raise ValueError('nonfinite JSON')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    require(canonical(value) == raw, 'noncanonical JSON')
    return value


def ordinary(path, *, directory=False, allow_links=False):
    info = os.lstat(path)
    require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0)&0x400, 'reparse path')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        and (allow_links or info.st_nlink == 1), 'nonordinary path')
    return info


def directories(path):
    path = Path(path).absolute()
    return tuple((str(p), s.st_dev, s.st_ino) for p in reversed((path, *path.parents))
        for s in (ordinary(p, directory=True),))


def identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read(path, *, allow_links=False):
    path = Path(path)
    parents = directories(path.parent)
    before = identity(ordinary(path, allow_links=allow_links))
    require(before[2] <= 8*1024**2, 'file byte cap')
    with path.open('rb') as stream:
        require(identity(os.fstat(stream.fileno())) == before, 'file changed before read')
        raw = stream.read(8*1024**2+1)
        require(identity(os.fstat(stream.fileno())) == before, 'file changed during read')
    require(len(raw) == before[2] and identity(ordinary(path, allow_links=allow_links)) == before
        and directories(path.parent) == parents, 'file/parent changed after read')
    return raw


def source_names():
    raw = read(INHERITED)
    require(sha256(raw).hexdigest() == INHERITED_SHA, 'frozen inherited source inventory differs')
    inherited = json.loads(raw)
    require(type(inherited) is dict and len(inherited) == 45, 'inherited source set differs')
    return tuple(sorted(set(inherited)|set(NEW_SOURCES)))


def source_pins():
    names = source_names()
    require(len(names) == 49, 'selected source count differs')
    return {name: pin(read(ROOT/name)) for name in names}


def environment():
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE',
        'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'COMMONPROGRAMFILES',
        'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV'}
    result = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    result.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTHONHASHSEED='0',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return result


def output_mode(path):
    path = Path(path).absolute()
    if path == OUTPUT: return 'saved_P1_F_validation'
    temporary = Path(tempfile.gettempdir()).resolve()
    require(path.resolve().is_relative_to(temporary) and path.name == 'output'
        and path.parent.name.startswith('test_') and path.parent.parent.name.startswith('pytest-'),
        'fixed F output or dedicated ordinary pytest output required')
    return 'ordinary_pytest_fixture'


def validate_context(value):
    keys(value, 'schema authority scope repo_root input_root output_root source_pins executable environment '
        'anchor_sha input_files invocation_started deadline stage_seconds limits inherited_sources_pin '
        'caller_core caller_sha output_mode output_parent_directories '+' '.join(GATES))
    require(value['schema'] == SCHEMA and value['authority'] == 'DRAFT_NONAUTHORITATIVE'
        and value['scope'] == SCOPE and all(value[k] is False for k in GATES), 'context authority/scope differs')
    require(value['repo_root'] == str(ROOT) and value['input_root'] == str(P1), 'fixed saved P1 root differs')
    output = Path(value['output_root'])
    require(output.is_absolute() and '..' not in output.parts and str(output.absolute()) == str(output)
        and not output.is_relative_to(P1) and not P1.is_relative_to(output), 'output overlaps saved P1')
    require(value['output_mode'] == output_mode(output), 'output mode differs')
    require(value['output_parent_directories'] == [list(row) for row in directories(output.parent)], 'output parent identity changed')
    require(value['limits'] == CAPS and value['stage_seconds'] == STAGE_SECONDS, 'fixed F budget differs')
    require(type(value['deadline']) is float and math.isfinite(value['deadline']) and value['deadline'] > 0,
        'finite absolute deadline required')
    require(type(value['invocation_started']) is float and math.isfinite(value['invocation_started'])
        and 0 < value['invocation_started'] <= time.monotonic()
        and value['deadline'] == value['invocation_started']+180, 'absolute deadline differs from invocation budget')
    require(value['anchor_sha'] == ANCHOR_SHA and type(value['input_files']) is dict
        and len(value['input_files']) == 683, 'saved anchor/input map differs')
    require(type(value['source_pins']) is dict and set(value['source_pins']) == set(source_names()), 'closed selected source group differs')
    for item in tuple(value['source_pins'].values())+tuple(value['input_files'].values())+(value['inherited_sources_pin'],):
        keys(item, 'bytes sha256')
        require(type(item['bytes']) is int and 0 <= item['bytes'] <= 8*1024**2 and type(item['sha256']) is str
            and len(item['sha256']) == 64 and all(c in '0123456789abcdef' for c in item['sha256']), 'invalid held pin')
    keys(value['executable'], 'path pin identity python')
    require(value['executable']['path'] == str(EXE) and value['executable']['python'] == sys.version,
        'bound executable/Python differs')
    require(type(value['environment']) is dict and all(type(k) is type(v) is str for k, v in value['environment'].items()),
        'controlled environment fields differ')
    require(type(value['caller_core']) is dict and value['caller_sha'] == digest(value['caller_core'])
        and value['caller_core']['files'] == value['input_files']
        and value['caller_core']['source'] == value['source_pins'], 'external caller core differs')
    canonical(value)
    return value


def check_context(raw, expected_sha):
    require(type(expected_sha) is str and len(expected_sha) == 64 and sha256(raw).hexdigest() == expected_sha,
        'held context SHA differs')
    value = validate_context(parse(raw))
    require(Path.cwd().absolute() == ROOT, 'actual working directory differs')
    require(pin(read(INHERITED)) == value['inherited_sources_pin'], 'inherited source inventory changed')
    anchor = read(P1.parent/'p1_execution_review_01/postcheck_03.stdout.json')
    require(sha256(anchor).hexdigest() == ANCHOR_SHA and json.loads(anchor)['p1_files'] == value['input_files'],
        'held full P1 map differs from frozen external anchor')
    require(source_pins() == value['source_pins'], 'selected source bytes changed')
    require(str(Path(sys.executable).absolute()) == value['executable']['path']
        and pin(read(sys.executable, allow_links=True)) == value['executable']['pin']
        and list(identity(ordinary(sys.executable, allow_links=True))) == value['executable']['identity'],
        'actual executable differs')
    require(environment() == value['environment'], 'controlled environment changed')
    require(time.monotonic() <= value['deadline'], 'whole F absolute deadline')
    return value


def make_context(output_root, *, started):
    """Build bytes only; creation/spawn need a separately held trusted invocation."""
    require(type(started) is float and math.isfinite(started) and started <= time.monotonic(), 'invocation start required')
    anchor = read(P1.parent/'p1_execution_review_01/postcheck_03.stdout.json')
    require(sha256(anchor).hexdigest() == ANCHOR_SHA, 'external saved P1 anchor differs')
    require(Path(sys.executable).absolute() == EXE, 'bound compute executable required')
    output = Path(output_root).absolute()
    mode = output_mode(output)
    require(not os.path.lexists(output), 'dedicated output already exists')
    selected = source_pins()
    require(pin(read(EXE, allow_links=True))['bytes'] > 0, 'bound executable missing')
    # Only the trusted initial capture imports scientific definitions. Its inputs
    # and selected bytes have already been checked; role bootstrap stays stdlib.
    from src import staged_rts24_saved_fresh_adoption_v1 as adapter
    captured = adapter.capture(selected)
    caller_core = parse(captured.image)
    value = dict(schema=SCHEMA, authority='DRAFT_NONAUTHORITATIVE', scope=SCOPE, repo_root=str(ROOT), input_root=str(P1),
        output_root=str(output), output_mode=mode, output_parent_directories=[list(row) for row in directories(output.parent)],
        source_pins=selected, caller_core=caller_core, caller_sha=digest(caller_core),
        executable=dict(path=str(EXE), pin=pin(read(EXE, allow_links=True)),
            identity=list(identity(ordinary(EXE, allow_links=True))), python=sys.version), environment=environment(),
        anchor_sha=ANCHOR_SHA, input_files=json.loads(anchor)['p1_files'], inherited_sources_pin=pin(read(INHERITED)),
        invocation_started=started, deadline=started+180, stage_seconds=dict(STAGE_SECONDS), limits=dict(CAPS), **GATES)
    raw = canonical(validate_context(value))
    check_context(raw, sha256(raw).hexdigest())
    return raw


def argv_for(role, context_raw, context_sha):
    require(role in ('supervise', 'parent', 'fresh'), 'unknown saved F role')
    context = check_context(context_raw, context_sha)
    output = Path(context['output_root'])
    args = [str(EXE), '-B', '-s', str(ROOT/NEW_SOURCES[1]), '--'+role,
        '--context', str(output/'context.json'), '--context-sha', context_sha]
    if role != 'supervise':
        target = output/('worker' if role == 'parent' else 'worker/fresh')
        args += ['--input-root', str(P1), '--output-root', str(target)]
    return args


def validate_actual_entry(role, context_raw, context_sha):
    expected = argv_for(role, context_raw, context_sha)
    main = sys.modules.get('__main__')
    require(main is not None and type(getattr(main, '__file__', None)) is str
        and Path(main.__file__).absolute() == ROOT/NEW_SOURCES[1]
        and list(sys.argv) == expected[3:], 'actual role entry/argv differs')
    context = parse(context_raw)
    require(pin(read(main.__file__)) == context['source_pins'][NEW_SOURCES[1]], 'actual entry bytes differ')
    return context


def execution_context(role, context_raw, context_sha):
    context = validate_actual_entry(role, context_raw, context_sha)
    require(context['output_mode'] == 'saved_P1_F_validation', 'ordinary test context cannot enter F execution/adoption')
    return context


@dataclass(frozen=True, init=False)
class HeldContext:
    """Immutable creating-process validated data; no process or run authority."""
    raw: bytes
    sha: str
    output_root: str
    output_directories: tuple
    creator: tuple

    def __reduce__(self): raise TypeError('held validation context cannot be serialized')


def hold_context(raw, expected_sha):
    value = check_context(raw, expected_sha)
    held = object.__new__(HeldContext)
    for name, data in dict(raw=raw, sha=expected_sha, output_root=value['output_root'],
            output_directories=directories(value['output_root']), creator=(os.getpid(), get_ident())).items():
        object.__setattr__(held, name, data)
    return held


def safety_accounting(held, global_output_root):
    """Metadata only, permitted while quiet is unknown; never reads artifacts."""
    require(type(held) is HeldContext and held.creator == (os.getpid(), get_ident())
        and sha256(held.raw).hexdigest() == held.sha, 'creating-process held context required')
    root = Path(global_output_root).absolute()
    require(str(root) == held.output_root, 'global F output root required for safety accounting')
    root_identity = directories(root)
    require(root_identity == held.output_directories, 'held global output root identity changed')
    allowed_dirs = {Path('.')}
    for name in TARGETS:
        allowed_dirs.update(Path(name).parents)
    total = entries = 0
    files = {}
    def visit(path, depth):
        nonlocal total, entries
        require(depth <= 12, 'output depth cap')
        ordinary(path, directory=True)
        with os.scandir(path) as stream:
            for item in stream:
                entries += 1
                require(entries <= 16384, 'output metadata entry cap')
                child = Path(item.path)
                info = os.lstat(child)
                require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0)&0x400, 'linked output')
                relative = child.relative_to(root).as_posix()
                if stat.S_ISDIR(info.st_mode):
                    require(Path(relative) in allowed_dirs, 'unexpected output directory')
                    visit(child, depth+1)
                else:
                    base = relative.removesuffix('.pending')
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and base in TARGETS
                        and (base == relative or base.endswith('.json')), 'unexpected output file')
                    files[relative] = identity(info)
                    total += info.st_size
                    require(info.st_size <= 8*1024**2 and total <= CAPS['output_bytes'] and len(files) <= CAPS['files'],
                        'output storage cap')
    visit(root, 0)
    reserved_bytes = reserved_files = 0
    for name in RECORDS:
        present = [n for n in (name, name+'.pending') if n in files]
        require(len(present) <= 1, 'terminal final/pending conflict')
        actual = files[present[0]][2] if present else 0
        require(actual <= CAPS['record_bytes'], 'terminal record byte cap')
        reserved_bytes += CAPS['record_bytes']-actual
        reserved_files += int(not present)
    require(total+reserved_bytes <= CAPS['output_bytes'] and len(files)+reserved_files <= CAPS['files'],
        'remaining terminal reservations do not fit')
    require(directories(root) == root_identity, 'output root identity changed')
    return dict(bytes=total, files=len(files), remaining_reserved_bytes=reserved_bytes,
        remaining_reserved_files=reserved_files, metadata_entries=entries,
        safety_only=True, worker_accounting='unknown', content_read=False)


STAGE_SLOT_BYTES = 4096
STAGE_SLOTS = 16
STAGE_MAP_BYTES = STAGE_SLOT_BYTES*(STAGE_SLOTS+1)
STAGE_COMMIT = b'GRIDFRM1'
STAGE_HEADER_COMMIT = b'GRIDHDR1'
STAGE_PREFIX = 'Local\\electricity_grid_saved_F_'
STAGE_PHASES = dict(fresh=('fresh',), parent=('parent', 'fresh', 'inner_quiesce', 'inner_terminal', 'parent_compare'),
    controller=('prepare', 'parent', 'fresh', 'inner_quiesce', 'inner_terminal', 'parent_compare',
        'outer_quiesce', 'outer_terminal', 'final_check', 'final_publish'))


def _stage_spec_value(role, preset):
    require(role in STAGE_PHASES, 'unknown owner-stage role')
    phases = STAGE_PHASES[role]
    if preset is None:
        caps = tuple(float(STAGE_SECONDS[name]) for name in phases)
        total, cleanup, terminal = dict(fresh=(50., 5., 5.), parent=(125., 5., 10.), controller=(180., 5., 5.))[role]
        mode, rss, commit = 'production_descriptor_only', 1024**3, 1024**3
    else:
        require(preset in ('steady', 'deadline', 'nested'), 'fixed ordinary owner preset required')
        require(preset != 'nested' or role == 'parent', 'nested preset requires parent role')
        cap = dict(steady=1., deadline=.2, nested=.8)[preset]
        if role == 'controller': cap = min(cap, .5)
        caps = (cap,)*len(phases)
        cleanup, terminal = 1., .5
        total = sum(caps)+cleanup+terminal
        mode, rss, commit = 'ordinary_owner_probe', 256*1024**2, 256*1024**2
    require(len(phases)+2 <= STAGE_SLOTS, 'normal and error frame reservation does not fit')
    return dict(schema='staged_saved_F_owner_descriptor_v1', authority='DRAFT_NONAUTHORITATIVE', mode=mode,
        role=role, preset=preset, phases=list(phases), phase_seconds=list(caps), total_seconds=total,
        quiesce_seconds=cleanup, terminal_seconds=terminal, rss_bytes=rss,
        process_commit_bytes=commit, job_commit_bytes=2*commit, member_handles=1024)


def stage_descriptor(role): return canonical(_stage_spec_value(role, None))


def ordinary_stage_descriptor(role='fresh', preset='steady'): return canonical(_stage_spec_value(role, preset))


def checked_stage_descriptor(raw):
    value = parse(raw)
    require(type(value) is dict and value == _stage_spec_value(value.get('role'), value.get('preset')),
        'owner-stage descriptor differs')
    require(canonical(value) == canonical(_stage_spec_value(value['role'], value['preset'])), 'owner-stage scalar domains differ')
    return value


def _bounded_stage_error_image(value, depth):
    if type(value) is not dict or depth <= 0: return None
    result = {key: str(value[key])[:limit] for key, limit in (('type', 64), ('message', 256), ('kind', 64)) if key in value}
    for key in ('primary', 'cause', 'context'):
        if value.get(key) is not None: result[key] = _bounded_stage_error_image(value[key], depth-1)
    return result


def _stage_error(error, *, _depth=3, _seen=frozenset()):
    try: kind = type(error).__name__[:64]
    except BaseException: kind = 'Exception'
    try: message = str(error)
    except BaseException: message = '[message unavailable]'
    result = dict(type=kind, message=message[:256])
    if id(error) in _seen:
        result['chain_cycle'] = True; return result
    if isinstance(error, StageChannelError):
        result.update(kind=error.kind[:64], primary=_bounded_stage_error_image(error.primary, 3))
    if _depth > 0:
        seen = _seen|{id(error)}
        for key, related in (('cause', error.__cause__), ('context', error.__context__)):
            if related is not None:
                result[key] = _stage_error(related, _depth=_depth-1, _seen=seen)
    return result


class StageChannelError(RuntimeError):
    def __init__(self, kind, message, primary=None):
        self.kind, self.primary = kind, None if primary is None else _stage_error(primary)
        super().__init__(kind+': '+message[:256])


class StageChannelConstructionUnresolved(StageChannelError):
    def __init__(self, channel, primary, cleanup, kind):
        self.channel = channel
        self.cleanup_error = _stage_error(cleanup)
        super().__init__(kind, 'partial channel retained for creating-thread cleanup', primary)

    def __reduce__(self): raise TypeError('partial live stage channel cannot be serialized')


def _stage_api():
    require(os.name == 'nt', 'Windows retained-owner protocol required')
    api = C.WinDLL('kernel32', use_last_error=True)
    definitions = {
        'CreateFileMappingW': ([W.HANDLE, C.c_void_p, W.DWORD, W.DWORD, W.DWORD, W.LPCWSTR], W.HANDLE),
        'OpenFileMappingW': ([W.DWORD, W.BOOL, W.LPCWSTR], W.HANDLE),
        'MapViewOfFile': ([W.HANDLE, W.DWORD, W.DWORD, W.DWORD, C.c_size_t], C.c_void_p),
        'UnmapViewOfFile': ([C.c_void_p], W.BOOL),
        'CreateMutexW': ([C.c_void_p, W.BOOL, W.LPCWSTR], W.HANDLE),
        'OpenMutexW': ([W.DWORD, W.BOOL, W.LPCWSTR], W.HANDLE),
        'WaitForSingleObject': ([W.HANDLE, W.DWORD], W.DWORD),
        'ReleaseMutex': ([W.HANDLE], W.BOOL), 'CloseHandle': ([W.HANDLE], W.BOOL),
        'GetHandleInformation': ([W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        'GetCurrentProcess': ([], W.HANDLE),
        'GetProcessTimes': ([W.HANDLE]+[C.POINTER(W.FILETIME)]*4, W.BOOL),
    }
    for name, (args, result) in definitions.items():
        function = getattr(api, name); function.argtypes, function.restype = args, result
    return api


def _native(value):
    if not value: raise C.WinError(C.get_last_error())
    return value


def _own_process_identity(api):
    created, ended, kernel, user = (W.FILETIME() for _ in range(4))
    _native(api.GetProcessTimes(api.GetCurrentProcess(), C.byref(created), C.byref(ended), C.byref(kernel), C.byref(user)))
    return os.getpid(), created.dwLowDateTime | created.dwHighDateTime << 32


def _stage_slot(raw, marker):
    require(type(raw) is bytes and len(raw) <= STAGE_SLOT_BYTES-44, 'whole slot byte limit')
    return struct.pack('<I', len(raw))+raw+b'\0'*(STAGE_SLOT_BYTES-44-len(raw))+sha256(raw).digest()+marker


def _stage_decode(slot, marker):
    if slot[-8:] != marker: return None
    length = struct.unpack('<I', slot[:4])[0]
    if not 0 < length <= STAGE_SLOT_BYTES-44: return None
    raw = slot[4:4+length]
    if slot[4+length:-40] != b'\0'*(STAGE_SLOT_BYTES-44-length) or sha256(raw).digest() != slot[-40:-8]: return None
    return raw


class StageChannel:
    """Single-writer fixed slots; progress/corruption detection, never authority."""
    def __init__(self): raise TypeError('use create or attach')

    @classmethod
    def _open(cls, name, nonce, context_sha, descriptor, create):
        require(type(name) is str and name.startswith(STAGE_PREFIX) and len(name) == len(STAGE_PREFIX)+64
            and all(c in '0123456789abcdef' for c in name[len(STAGE_PREFIX):]), 'fixed Local stage tag required')
        require(type(nonce) is str and len(nonce) == 64 and all(c in '0123456789abcdef' for c in nonce), 'stage nonce differs')
        require(type(context_sha) is str and len(context_sha) == 64 and all(c in '0123456789abcdef' for c in context_sha), 'stage context SHA differs')
        checked_stage_descriptor(descriptor)
        obj = object.__new__(cls)
        obj._api = _stage_api(); obj._map = obj._mutex = obj._view = None
        obj._creator = os.getpid(), get_ident(); obj._reader = create; obj._in_lock = False
        obj._poison = None; obj._header = None; obj._history = []; obj._terminal = False
        obj.pending_data = False
        obj.name, obj.nonce, obj.context_sha, obj.descriptor = name, nonce, context_sha, descriptor
        obj._binding_inputs = name, nonce, context_sha, descriptor
        try:
            if create:
                C.set_last_error(0)
                obj._map = _native(obj._api.CreateFileMappingW(C.c_void_p(-1), None, 4, 0, STAGE_MAP_BYTES, name))
                mapping_error = C.get_last_error()
                if mapping_error == 183: raise StageChannelError('collision', 'mapping already exists')
                C.set_last_error(0)
                obj._mutex = _native(obj._api.CreateMutexW(None, False, name+'_mutex'))
                mutex_error = C.get_last_error()
                if mutex_error == 183: raise StageChannelError('collision', 'mutex already exists')
            else:
                obj._map = _native(obj._api.OpenFileMappingW(6, False, name))
                obj._mutex = _native(obj._api.OpenMutexW(0x100001, False, name+'_mutex'))
            for handle in (obj._map, obj._mutex):
                flags = W.DWORD(); _native(obj._api.GetHandleInformation(handle, C.byref(flags)))
                require(not flags.value&1, 'stage handles must not be inherited')
            obj._view = _native(obj._api.MapViewOfFile(obj._map, 6, 0, 0, STAGE_MAP_BYTES))
            if create: require(C.string_at(obj._view, STAGE_MAP_BYTES) == b'\0'*STAGE_MAP_BYTES, 'new mapping not zero')
            return obj
        except BaseException as primary:
            try: obj.close()
            except BaseException as cleanup: raise StageChannelConstructionUnresolved(obj, primary, cleanup, 'construction_cleanup') from primary
            raise

    @classmethod
    def create(cls, context_sha, descriptor, *, name=None, nonce=None):
        return cls._open(name or STAGE_PREFIX+secrets.token_hex(32), nonce or secrets.token_hex(32), context_sha, descriptor, True)

    @classmethod
    def attach(cls, name, nonce, context_sha, descriptor):
        obj = cls._open(name, nonce, context_sha, descriptor, False)
        try:
            with obj._locked(100) as acquired:
                require(acquired, 'writer could not acquire initial stage mutex')
                initial = C.string_at(obj._view, STAGE_MAP_BYTES); header = initial[:STAGE_SLOT_BYTES]
                require(initial[STAGE_SLOT_BYTES:] == b'\0'*(STAGE_MAP_BYTES-STAGE_SLOT_BYTES), 'writer episode already contains frames')
            raw = _stage_decode(header, STAGE_HEADER_COMMIT)
            require(raw is not None, 'stage header not committed')
            value = parse(raw)
            obj._validate_header(value)
            require(tuple(value[n] for n in ('owner_pid', 'owner_creation_filetime')) == _own_process_identity(obj._api), 'wrong stage writer process')
            obj._header = header
            return obj
        except BaseException as primary:
            try: obj.close()
            except BaseException as cleanup: raise StageChannelConstructionUnresolved(obj, primary, cleanup, 'attach_cleanup') from primary
            raise

    @property
    def spec(self): return checked_stage_descriptor(self.descriptor)

    def _live(self, *, poisoned=False):
        require(self._creator == (os.getpid(), get_ident()), 'creating PID/thread required for stage channel')
        require(self._view is not None and self._map is not None and self._mutex is not None, 'closed stage channel')
        require((self.name, self.nonce, self.context_sha, self.descriptor) == self._binding_inputs, 'frozen channel inputs changed')
        if self._poison is not None and not poisoned: raise StageChannelError(self._poison, 'stage channel remains unresolved')

    @contextmanager
    def _locked(self, milliseconds):
        self._live(); require(not self._in_lock, 'recursive stage lock forbidden')
        result = self._api.WaitForSingleObject(self._mutex, milliseconds)
        if result == 258:
            yield False; return
        if result not in (0, 128):
            self._poison = 'mutex_wait'; raise StageChannelError('mutex_wait', str(C.WinError(C.get_last_error())))
        self._in_lock = True
        primary = None
        try:
            if result == 128:
                self._poison = 'abandoned'; raise StageChannelError('abandoned', 'writer mutex abandoned')
            yield True
        except BaseException as error:
            primary = error; raise
        finally:
            self._in_lock = False
            if not self._api.ReleaseMutex(self._mutex):
                self._poison = 'mutex_release'
                raise StageChannelError('mutex_release', str(C.WinError(C.get_last_error())), primary) from primary

    def _validate_header(self, value):
        keys(value, 'schema context_sha nonce descriptor owner_pid owner_creation_filetime slots slot_bytes')
        require(value['schema'] == 'staged_saved_F_memory_header_v1' and value['context_sha'] == self.context_sha
            and value['nonce'] == self.nonce and canonical(value['descriptor']) == self.descriptor
            and type(value['slots']) is int and value['slots'] == STAGE_SLOTS
            and type(value['slot_bytes']) is int and value['slot_bytes'] == STAGE_SLOT_BYTES, 'stage header binding differs')
        require(type(value['owner_pid']) is int and 0 < value['owner_pid'] < 2**32
            and type(value['owner_creation_filetime']) is int and 0 < value['owner_creation_filetime'] < 2**64, 'stage owner identity domain')

    def bind_owner(self, owner):
        self._live(); require(self._reader and self._header is None, 'stage owner already bound')
        owner._live_owner(); require(not owner._released, 'suspended owner required')
        value = dict(schema='staged_saved_F_memory_header_v1', context_sha=self.context_sha, nonce=self.nonce,
            descriptor=self.spec, owner_pid=owner.pid, owner_creation_filetime=owner.creation_filetime,
            slots=STAGE_SLOTS, slot_bytes=STAGE_SLOT_BYTES)
        self._validate_header(value); header = _stage_slot(canonical(value), STAGE_HEADER_COMMIT)
        with self._locked(0) as acquired:
            require(acquired and C.string_at(self._view, STAGE_MAP_BYTES) == b'\0'*STAGE_MAP_BYTES, 'new stage map changed before bind')
            C.memmove(self._view, header[:-8], len(header)-8)
            C.memmove(self._view+STAGE_SLOT_BYTES-8, STAGE_HEADER_COMMIT, 8)
        self._header = header

    def _snapshot(self, milliseconds):
        self._live(); require(self._header is not None, 'stage owner header missing')
        with self._locked(milliseconds) as acquired:
            if not acquired: return None
            first = C.string_at(self._view, STAGE_MAP_BYTES); second = C.string_at(self._view, STAGE_MAP_BYTES)
        require(first == second, 'stage map changed under mutex')
        if first[:STAGE_SLOT_BYTES] != self._header:
            self._poison = 'header'; raise StageChannelError('header', 'frozen header changed')
        return first

    def read_available(self):
        try:
            require(self._reader, 'stage observer endpoint required')
            image = self._snapshot(0)
            if image is None: return None
            frames = []
            self.pending_data = False
            for index in range(STAGE_SLOTS):
                slot = image[(index+1)*STAGE_SLOT_BYTES:(index+2)*STAGE_SLOT_BYTES]
                if index < len(self._history) and slot != self._history[index]: raise StageChannelError('history', 'accepted stage slot changed')
                raw = _stage_decode(slot, STAGE_COMMIT)
                if raw is None:
                    self.pending_data = image[(index+1)*STAGE_SLOT_BYTES:] != b'\0'*(STAGE_MAP_BYTES-(index+1)*STAGE_SLOT_BYTES)
                    break
                value = parse(raw)
                keys(value, 'schema sequence phase binding_sha previous_sha producer_pid producer_creation_filetime stamp error_code')
                binding = parse(_stage_decode(self._header, STAGE_HEADER_COMMIT))
                previous = sha256(_stage_decode(self._history[index-1], STAGE_COMMIT)).hexdigest() if index else '0'*64
                require(value['schema'] == 'staged_saved_F_memory_frame_v1' and type(value['sequence']) is int
                    and value['sequence'] == index and value['binding_sha'] == sha256(self._header).hexdigest()
                    and value['previous_sha'] == previous
                    and (value['producer_pid'], value['producer_creation_filetime']) == (binding['owner_pid'], binding['owner_creation_filetime'])
                    and type(value['stamp']) is float and math.isfinite(value['stamp']) and value['stamp'] > 0, 'stage frame binding differs')
                require((value['phase'] == 'error' and type(value['error_code']) is str and 0 < len(value['error_code']) <= 64)
                    or (value['phase'] != 'error' and value['error_code'] is None), 'stage error domain differs')
                if index >= len(self._history): self._history.append(slot)
                frames.append(value)
            return frames
        except BaseException as error:
            if not isinstance(error, (KeyboardInterrupt, SystemExit)) and self._poison is None: self._poison = 'protocol'
            raise

    def enter(self, phase):
        return self._publish(phase, None)

    def fail(self, error_code):
        require(type(error_code) is str and 0 < len(error_code) <= 64, 'bounded stage error code required')
        return self._publish('error', error_code)

    def _publish(self, phase, error_code):
        try: return self._publish_once(phase, error_code)
        except BaseException as error:
            if self._poison is None: self._poison = 'writer'
            raise

    def _publish_once(self, phase, error_code):
        self._live(); require(not self._reader and not self._terminal, 'single live stage writer required')
        index = len(self._history)
        phases = self.spec['phases']
        expected = phases[index] if index < len(phases) else 'terminal'
        require(index < STAGE_SLOTS and (phase == expected or phase == 'error'), 'strict next phase required')
        binding = parse(_stage_decode(self._header, STAGE_HEADER_COMMIT))
        previous = sha256(_stage_decode(self._history[-1], STAGE_COMMIT)).hexdigest() if self._history else '0'*64
        raw = canonical(dict(schema='staged_saved_F_memory_frame_v1', sequence=index, phase=phase,
            binding_sha=sha256(self._header).hexdigest(), previous_sha=previous,
            producer_pid=binding['owner_pid'], producer_creation_filetime=binding['owner_creation_filetime'],
            stamp=time.monotonic(), error_code=error_code))
        slot = _stage_slot(raw, STAGE_COMMIT)
        with self._locked(100) as acquired:
            require(acquired, 'writer stage mutex busy')
            current = C.string_at(self._view, STAGE_MAP_BYTES)
            require(current[:STAGE_SLOT_BYTES] == self._header, 'writer frozen header changed')
            for n, old in enumerate(self._history):
                require(current[(n+1)*STAGE_SLOT_BYTES:(n+2)*STAGE_SLOT_BYTES] == old, 'writer old slot changed')
            offset = (index+1)*STAGE_SLOT_BYTES
            require(current[offset:offset+STAGE_SLOT_BYTES] == b'\0'*STAGE_SLOT_BYTES, 'next stage slot already used')
            C.memmove(self._view+offset, slot[:-8], len(slot)-8)
            C.memmove(self._view+offset+STAGE_SLOT_BYTES-8, STAGE_COMMIT, 8)
        self._history.append(slot); self._terminal = phase in ('terminal', 'error')

    def close(self):
        require(self._creator == (os.getpid(), get_ident()), 'creating PID/thread required for stage close')
        errors = []
        if self._view is not None:
            if self._api.UnmapViewOfFile(self._view): self._view = None
            else: errors.append(C.WinError(C.get_last_error()))
        for name in ('_mutex', '_map'):
            value = getattr(self, name)
            if value is not None:
                if self._api.CloseHandle(value): setattr(self, name, None)
                else: errors.append(C.WinError(C.get_last_error()))
        if errors: raise StageChannelError('close', str(_stage_error(errors[0])))

    def __reduce__(self): raise TypeError('live stage channel cannot be serialized')


class StageConstructionUnresolved(RuntimeError):
    def __init__(self, owner, primary, cleanup):
        self.owner = owner
        self.primary_error = _stage_error(primary)
        self.cleanup_errors = cleanup
        super().__init__('ordinary stage construction unresolved')

    def __reduce__(self): raise TypeError('live stage cleanup capability cannot be serialized')


@dataclass(frozen=True, init=False)
class OwnedStage:
    """Creating-thread probe owner capability; never a production lease."""
    owner: object
    channel: StageChannel
    startup: bytes
    created_at: float
    real_owner: bool
    _creator: tuple
    _binding: tuple
    _attempted: bool
    last_observation: object

    def __init__(self, owner, channel, startup, created, real_owner):
        require(type(startup) is bytes and type(created) is float and math.isfinite(created)
            and type(real_owner) is bool, 'typed retained owner binding required')
        binding = (id(owner), id(channel), sha256(startup).hexdigest(), created, real_owner,
            owner.pid, owner.creation_filetime, channel._binding_inputs)
        for name, value in dict(owner=owner, channel=channel, startup=startup, created_at=created,
                real_owner=real_owner, _creator=(os.getpid(), get_ident()), _binding=binding,
                _attempted=False, last_observation=None).items():
            object.__setattr__(self, name, value)

    def _entry(self):
        require(self._creator == (os.getpid(), get_ident()), 'creating PID/thread required for stage owner')
        require((id(self.owner), id(self.channel)) == self._binding[:2], 'held owner/channel binding changed')
        require(type(self.startup) is bytes and sha256(self.startup).hexdigest() == self._binding[2]
            and type(self.created_at) is float and self.created_at == self._binding[3]
            and self.real_owner is self._binding[4]
            and (self.owner.pid, self.owner.creation_filetime, self.channel._binding_inputs) == self._binding[5:],
            'held startup/clock/evidence binding changed')

    def close(self):
        self._entry()
        errors = []
        try: self.owner.close()
        except BaseException as error: errors.append(_stage_error(error))
        try: self.channel.close()
        except BaseException as error: errors.append(_stage_error(error))
        if errors: raise StageChannelError('owner_close', str(errors))

    def __reduce__(self): raise TypeError('live stage owner cannot be serialized')


def _stop_owned_job(owner):
    """Private-ABI bridge: request kill before quiesce's member enumeration."""
    owner._live_owner()
    _native(owner._k.TerminateJobObject(owner._job, 0xE0F1))


def _ordinary_probe_argv(probe_id, channel):
    """Closed, source-bound tiny programs; caller code and paths are rejected."""
    probes = {
        'normal': ('fresh', 'steady', "w.enter('fresh'); time.sleep(.15); w.enter('terminal'); w.close()"),
        'no_first_frame': ('fresh', 'deadline', 'time.sleep(20)'),
        'hang': ('fresh', 'deadline', "w.enter('fresh'); time.sleep(20)"),
        'terminal_hang': ('fresh', 'deadline', "w.enter('fresh'); w.enter('terminal'); time.sleep(20)"),
        'terminal_exit_hang': ('fresh', 'steady', "w.enter('fresh'); w.enter('terminal'); time.sleep(20)"),
        'late_terminal_hang': ('fresh', 'steady', "w.enter('fresh'); time.sleep(.75); w.enter('terminal'); time.sleep(20)"),
        'missing_terminal': ('fresh', 'steady', "w.enter('fresh'); time.sleep(.1); w.close()"),
        'exit_nonzero': ('fresh', 'steady', "w.enter('fresh'); time.sleep(.1); w.enter('terminal'); os._exit(7)"),
        'reported_error': ('fresh', 'steady', "w.enter('fresh'); time.sleep(.1); w.fail('probe_error'); w.close()"),
        'nested_quiet': ('parent', 'nested', "from src.staged_rts24_process_guard_v1 import OwnedChild; "
            "w.enter('parent'); child=OwnedChild([str(d.EXE),'-B','-s','-c','import time; time.sleep(20)'],"
            "cwd=d.ROOT,max_process_commit_bytes=128*1024**2,max_job_commit_bytes=256*1024**2,environment=d.environment()); "
            "child.release(); w.enter('fresh'); time.sleep(.3); w.enter('inner_quiesce'); child.quiesce(max_seconds=1); "
            "w.enter('inner_terminal'); child.close(); w.enter('parent_compare'); w.enter('terminal'); w.close()"),
        'root_exited_with_descendants': ('parent', 'nested', "import subprocess; w.enter('parent'); "
            "child=subprocess.Popen([str(d.EXE),'-B','-s','-c','import time; time.sleep(20)']); "
            "w.enter('fresh'); time.sleep(.3); w.enter('inner_quiesce'); w.enter('inner_terminal'); "
            "w.enter('parent_compare'); w.enter('terminal'); os._exit(0)"),
    }
    require(type(probe_id) is str and probe_id in probes, 'closed ordinary probe identifier required')
    role, preset, body = probes[probe_id]
    require(channel.descriptor == ordinary_stage_descriptor(role, preset), 'probe and fixed descriptor differ')
    preamble = ('import time,os,sys; from experiments import staged_rts24_saved_fresh_adoption_v1 as d; '
        f'w=d.StageChannel.attach({channel.name!r},{channel.nonce!r},{channel.context_sha!r},{channel.descriptor!r}); ')
    return [str(EXE), '-B', '-s', '-c', preamble+body]


def create_probe_owner(probe_id, channel):
    return _create_probe_owner(probe_id, channel)


def _create_probe_owner(probe_id, channel, *, owner_factory=None):
    """Private owner injection is logic-only; public real probes use a closed ID."""
    channel._live()
    require(channel._reader and channel._header is None, 'unbound observer endpoint required')
    spec = channel.spec
    require(spec['mode'] == 'ordinary_owner_probe', 'production stage launch remains disabled')
    args = _ordinary_probe_argv(probe_id, channel)
    frozen_environment = environment()
    prospective = dict(schema='staged_saved_F_probe_CreateProcess_inputs_v1', authority='DRAFT_NONAUTHORITATIVE',
        scope='ordinary_owner_probe_only', probe_id=probe_id, creator_pid=os.getpid(), argv=args, command_line=subprocess.list2cmdline(args),
        cwd=str(ROOT), environment_sha=digest(frozen_environment), context_sha=channel.context_sha,
        descriptor_sha=sha256(channel.descriptor).hexdigest(), channel_name=channel.name,
        owner_pid=2**32-1, owner_creation_filetime=2**64-1,
        actual_os_commandline_independently_verified=False)
    require(len(canonical(prospective)) <= 16384, 'bounded probe startup record required')
    from src.staged_rts24_process_guard_v1 import OwnedChild
    factory = owner_factory or OwnedChild
    # Allocate before __init__ so a partial constructor's actual handles remain reachable.
    owner = object.__new__(factory)
    started = time.monotonic()
    try:
        factory.__init__(owner, args, cwd=ROOT, max_process_commit_bytes=spec['process_commit_bytes'],
            max_job_commit_bytes=spec['job_commit_bytes'], environment=frozen_environment)
        channel.bind_owner(owner)
        prospective.update(owner_pid=owner.pid, owner_creation_filetime=owner.creation_filetime)
        raw = canonical(prospective)
        require(len(raw) <= 16384, 'probe startup bytes exceed cap')
        return OwnedStage(owner, channel, raw, started, owner_factory is None)
    except BaseException as primary:
        cleanup = []
        if getattr(owner, '_job', None) is not None:
            try: _stop_owned_job(owner)
            except BaseException as error: cleanup.append(dict(layer='termination', **_stage_error(error)))
            try: owner.quiesce(max_seconds=1)
            except BaseException as error: cleanup.append(dict(layer='quiesce', **_stage_error(error)))
        try: owner.close()
        except BaseException as error: cleanup.append(dict(layer='close', **_stage_error(error)))
        raise StageConstructionUnresolved(owner, primary, cleanup) from primary


def _stage_complete_witness(value, owner_pid, owner_creation):
    if type(value) is not dict or set(value) != {'observed_unique_member_handles', 'all_handles_signaled', 'member_identities',
            'total_processes', 'final_pids', 'active_processes', 'complete_inventory'}: return False
    members = value['member_identities']
    if type(members) is not list or not 1 <= len(members) <= 1024: return False
    identities = []
    for item in members:
        if type(item) is not dict or set(item) != {'pid', 'creation_filetime'}: return False
        if type(item['pid']) is not int or not 0 < item['pid'] < 2**32: return False
        if type(item['creation_filetime']) is not int or not 0 < item['creation_filetime'] < 2**64: return False
        identities.append((item['pid'], item['creation_filetime']))
    return (len(set(identities)) == len(identities) and (owner_pid, owner_creation) in identities
        and value['all_handles_signaled'] is value['complete_inventory'] is True
        and type(value['active_processes']) is int and value['active_processes'] == 0 and value['final_pids'] == []
        and type(value['total_processes']) is type(value['observed_unique_member_handles']) is int
        and value['total_processes'] == value['observed_unique_member_handles'] == len(identities))


def watch_probe_stage(held, *, absolute_deadline=None):
    """Active loop: kernel queries and fixed RAM only; no artifact/source I/O."""
    require(type(held) is OwnedStage, 'actual creating-thread probe owner required')
    held._entry(); require(not held._attempted, 'stage observation already attempted')
    owner, channel = held.owner, held.channel
    channel._live()
    spec = channel.spec
    require(spec['mode'] == 'ordinary_owner_probe', 'production stage observation remains disabled')
    total_deadline = held.created_at+spec['total_seconds']
    if absolute_deadline is not None:
        require(type(absolute_deadline) is float and math.isfinite(absolute_deadline), 'finite earlier stage deadline required')
        total_deadline = min(total_deadline, absolute_deadline)
    object.__setattr__(held, '_attempted', True)
    active_deadline = total_deadline-spec['quiesce_seconds']-spec['terminal_seconds']
    phases, caps = spec['phases'], spec['phase_seconds']
    poll_interval = .01
    start = time.monotonic(); phase_entered = start; phase_index = 0; seen = 0
    phase_deadline = min(start+caps[0], active_deadline)
    primary = monitor_error = termination_error = quiesce_error = close_error = channel_error = channel_close_error = final_bookend_error = None
    exit_code = None; terminal = False; released = False; kill_requested = False; kill_succeeded = False
    samples = peak_rss = peak_commit = 0
    terminal_rss = None
    terminal_accepted = terminal_exit_deadline = None
    terminal_exit_limiting_deadline = None
    root_exit_observed_at = termination_requested_at = quiesce_completed_at = None
    phase_entries = [dict(phase=phases[0], observer_entered=start)]
    frames = []

    def termination(reason):
        nonlocal primary, termination_error, kill_requested, kill_succeeded, termination_requested_at
        primary = primary or reason
        if kill_requested: return
        kill_requested = True
        termination_requested_at = time.monotonic()
        try: _stop_owned_job(owner); kill_succeeded = True
        except BaseException as error: termination_error = _stage_error(error)

    def sample():
        nonlocal samples, peak_rss, peak_commit, terminal_rss
        data = owner.sample()
        if exit_code is None:
            samples += 1; peak_rss = max(peak_rss, data['rss_bytes'])
        else: terminal_rss = data['rss_bytes']
        peak_commit = max(peak_commit, data['peak_job_commit_bytes'])
        if data['rss_bytes'] > spec['rss_bytes']: termination('rss_limit' if exit_code is None else 'terminal_rss_limit')
        elif peak_commit > spec['job_commit_bytes']: termination('commit_limit')
        return data

    try:
        owner._live_owner()
        require(not owner._released, 'unreleased owner required for phase clock')
        if start >= active_deadline: termination('construction_or_total_budget')
        else:
            released = True; owner.release()
            while primary is None:
                now = time.monotonic()
                if terminal_exit_deadline is not None and now >= terminal_exit_deadline: termination('terminal_exit_limit'); break
                if now >= active_deadline: termination('total_active_limit'); break
                if now >= phase_deadline: termination('phase_limit'); break
                exit_code = owner.poll()
                if exit_code is not None and root_exit_observed_at is None: root_exit_observed_at = time.monotonic()
                data = sample()
                if primary is not None: break
                new_frames = channel.read_available()
                if new_frames is not None:
                    frames = new_frames
                    for frame in frames[seen:]:
                        now = time.monotonic()
                        if now >= min(active_deadline, phase_deadline): termination('phase_limit'); break
                        phase = frame['phase']
                        if phase == 'error': termination('child_reported_error'); break
                        if seen < len(phases):
                            if phase != phases[seen]: termination('phase_protocol'); break
                            if seen:
                                phase_index = seen; phase_entered = now
                                phase_deadline = min(now+caps[seen], active_deadline)
                                phase_entries.append(dict(phase=phase, observer_entered=now))
                        elif seen == len(phases) and phase == 'terminal':
                            terminal = True; terminal_accepted = now
                            candidates = dict(active=active_deadline, phase=phase_deadline, exit_cap=now+spec['terminal_seconds'])
                            terminal_exit_limiting_deadline = min(candidates, key=candidates.get)
                            terminal_exit_deadline = candidates[terminal_exit_limiting_deadline]
                        else: termination('phase_protocol'); break
                        seen += 1
                if primary is not None: break
                if exit_code is not None:
                    # A root exit never substitutes for a final descendant sample.
                    last = sample()
                    if any(pid != owner.pid for pid in set(data['pids'])|set(last['pids'])): termination('root_exited_with_descendants')
                    elif exit_code != 0: termination('child_exit_nonzero')
                    elif not terminal or seen != len(phases)+1 or channel.pending_data: termination('incomplete_terminal')
                    break
                remaining = min(active_deadline, phase_deadline)-time.monotonic()
                if terminal_exit_deadline is not None: remaining = min(remaining, terminal_exit_deadline-time.monotonic())
                if remaining > 0: time.sleep(min(poll_interval, remaining))
    except BaseException as error:
        monitor_error = _stage_error(error)
        if isinstance(error, StageChannelError): channel_error = _stage_error(error)
        termination('monitor_or_channel_error')
    finally:
        quiesce_started = time.monotonic()
        quiet = False
        try:
            remaining = min(spec['quiesce_seconds'], total_deadline-spec['terminal_seconds']-quiesce_started)
            if remaining <= 0:
                termination('quiesce_reservation_exhausted')
                # Cleanup still attempted, but cannot turn an over-budget run into success.
                remaining = spec['quiesce_seconds']
            owner.quiesce(max_seconds=remaining)
            quiesce_completed_at = time.monotonic()
            exit_code = owner.poll()
            if exit_code is not None and root_exit_observed_at is None: root_exit_observed_at = time.monotonic()
            post = owner.sample(); peak_commit = max(peak_commit, post['peak_job_commit_bytes'])
            quiet = _stage_complete_witness(getattr(owner, 'quiescence_witness', None), owner.pid, owner.creation_filetime)
            if not quiet: primary = primary or 'complete_inventory_unknown'
            if peak_commit > spec['job_commit_bytes']: primary = primary or 'post_quiesce_commit_limit'
            if time.monotonic()-quiesce_started > spec['quiesce_seconds']: primary = primary or 'quiesce_budget'
        except BaseException as error:
            quiesce_error = _stage_error(error); primary = primary or 'quiesce_unknown'
        try:
            final = channel.read_available()
            if final is None: raise StageChannelError('busy_final', 'final channel bookend unavailable')
            if len(final) != len(frames): raise StageChannelError('late_frame', 'transcript changed after exit observation')
        except BaseException as error:
            final_bookend_error = _stage_error(error); primary = primary or 'channel_bookend_unknown'
        try: owner.close()
        except BaseException as error:
            close_error = _stage_error(error); quiet = False; primary = primary or 'close_unknown'
        try: channel.close()
        except BaseException as error:
            channel_close_error = _stage_error(error); primary = primary or 'channel_close_unknown'
        closed_at = time.monotonic()
        if closed_at > total_deadline: primary = primary or 'total_budget'
        if samples == 0: primary = primary or 'rss_observation_unavailable'
    completed = terminal and seen == len(phases)+1 and channel_error is final_bookend_error is None and not channel.pending_data
    success = primary is None and exit_code == 0 and quiet and completed and samples > 0
    startup = parse(held.startup)
    record = dict(authority='DRAFT_NONAUTHORITATIVE', scope='ordinary_retained_owner_stage_process_only',
        owner_evidence='direct_owned_child' if held.real_owner else 'injected_unit_owner', startup=startup,
        descriptor=spec, exit_code=exit_code, primary_stop_reason=primary, monitor_error=monitor_error,
        termination_requested=kill_requested, termination_call_succeeded=kill_succeeded, termination_error=termination_error,
        quiesce_error=quiesce_error, close_error=close_error, channel_error=channel_error, final_bookend_error=final_bookend_error,
        channel_close_error=channel_close_error, quiet_witness_consistent=quiet,
        job_quiet_confirmed=quiet and held.real_owner, quiescence_witness=getattr(owner, 'quiescence_witness', None),
        stage_process_observed_successfully=success and held.real_owner, logic_path_completed=success, stage_transcript_complete=completed,
        frames_observed=seen, phases_observed=phase_entries, transcript_sha=sha256(b''.join(channel._history)).hexdigest(),
        stage_header=parse(_stage_decode(channel._header, STAGE_HEADER_COMMIT)),
        transcript_frames=[parse(_stage_decode(slot, STAGE_COMMIT)) for slot in channel._history],
        samples=samples, sampled_tree_peak_rss_bytes=peak_rss if samples else None, terminal_tree_rss_bytes=terminal_rss,
        peak_job_commit_bytes=peak_commit, release_attempted=released,
        construction_seconds=start-held.created_at, observation_seconds=closed_at-start,
        remaining_total_seconds=max(0., total_deadline-closed_at), total_deadline=total_deadline,
        terminal_accepted=terminal_accepted, terminal_exit_deadline=terminal_exit_deadline,
        terminal_exit_cap_seconds=spec['terminal_seconds'], terminal_exit_limiting_deadline=terminal_exit_limiting_deadline,
        root_exit_observed_at=root_exit_observed_at, termination_requested_at=termination_requested_at,
        quiesce_started_at=quiesce_started, quiesce_completed_at=quiesce_completed_at, close_attempts_finished_at=closed_at,
        active_io_scope='kernel_and_fixed_shared_memory_only', artifact_contents_read=False,
        external_constructor_and_monitor_interrupt_bound_proved=False, terminal_publication_bound_proved=False,
        clock=dict(implementation=time.get_clock_info('monotonic').implementation,
            resolution=time.get_clock_info('monotonic').resolution), poll_interval_seconds=poll_interval,
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
    object.__setattr__(held, 'last_observation', record)
    if len(canonical(record)) > 131072:
        record['stage_process_observed_successfully'] = False
        record['record_encoding_error'] = 'stage process record exceeds128KiB; original observation retained'
        raise StageChannelError('record_byte_cap', 'original observation retained on live capability')
    return record


if __name__ == '__main__':
    raise SystemExit('Saved F role execution and trusted invocation remain draft. F launch remains disabled.')
