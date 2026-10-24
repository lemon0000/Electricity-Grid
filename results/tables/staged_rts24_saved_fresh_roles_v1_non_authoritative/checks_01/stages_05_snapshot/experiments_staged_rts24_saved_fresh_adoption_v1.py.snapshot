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
    return _output_safety(root, held.output_directories)


def _output_safety(root, expected_directories):
    root_identity = directories(root)
    require(root_identity == expected_directories, 'held global output root identity changed')
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
        require(preset in ('steady', 'deadline', 'nested', 'role_graph'), 'fixed ordinary owner preset required')
        require(preset != 'nested' or role == 'parent', 'nested preset requires parent role')
        require(preset != 'role_graph' or role in ('parent', 'fresh'), 'role graph preset requires bounded child role')
        cap = (1.2 if role == 'parent' else 1.4) if preset == 'role_graph' else dict(steady=1., deadline=.2, nested=.8)[preset]
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
    result = {key: str(value[key])[:limit] for key, limit in (('type', 64), ('message', 256), ('kind', 64),
        ('phase', 64), ('expected_sha', 64), ('target', 256), ('layer', 32)) if key in value}
    if 'may_have_published' in value: result['may_have_published'] = value['may_have_published']
    for key in ('primary', 'cause', 'context', 'construction_primary', 'channel_cleanup', 'role_primary'):
        if value.get(key) is not None: result[key] = _bounded_stage_error_image(value[key], depth-1)
    if type(value.get('cleanup_errors')) is list:
        result['cleanup_errors'] = [_bounded_stage_error_image(item, depth-1) for item in value['cleanup_errors'][:4]]
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
    publication_type = globals().get('RolePublicationUnresolved')
    if publication_type is not None and isinstance(error, publication_type):
        result.update(phase=error.phase, expected_sha=error.expected_sha, may_have_published=error.may_have_published,
            target=error.target[:256], primary=_bounded_stage_error_image(error.primary_error, 3))
    construction_type = globals().get('StageConstructionUnresolved')
    if construction_type is not None and isinstance(error, construction_type):
        result['construction_primary'] = _bounded_stage_error_image(error.primary_error, 3)
        result['cleanup_errors'] = [_bounded_stage_error_image(item, 3) for item in error.cleanup_errors[:4]]
    channel_type = globals().get('StageChannelConstructionUnresolved')
    if channel_type is not None and isinstance(error, channel_type): result['channel_cleanup'] = _bounded_stage_error_image(error.cleanup_error, 3)
    execution_types = tuple(globals()[name] for name in ('RoleExecutionUnresolved', 'OwnedStageCloseUnresolved') if name in globals())
    if _depth > 0 and execution_types and isinstance(error, execution_types):
        details = []
        for index, item in enumerate(error.cleanup_errors[:4]):
            layer, secondary = item if type(item) is tuple and len(item) == 2 else ('cleanup_'+str(index), item)
            details.append(dict(layer=layer, **_stage_error(secondary, _depth=_depth-1, _seen=_seen|{id(error)})))
        result['cleanup_errors'] = details
        if isinstance(error, globals().get('RoleExecutionUnresolved', ())):
            result['role_primary'] = _stage_error(error.primary, _depth=_depth-1, _seen=_seen|{id(error)})
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
    last_image: object
    observation_commit: object

    def __init__(self, owner, channel, startup, created, real_owner):
        require(type(startup) is bytes and type(created) is float and math.isfinite(created)
            and type(real_owner) is bool, 'typed retained owner binding required')
        binding = (id(owner), id(channel), sha256(startup).hexdigest(), created, real_owner,
            owner.pid, owner.creation_filetime, channel._binding_inputs)
        for name, value in dict(owner=owner, channel=channel, startup=startup, created_at=created,
                real_owner=real_owner, _creator=(os.getpid(), get_ident()), _binding=binding,
                _attempted=False, last_observation=None, last_image=None, observation_commit=None).items():
            object.__setattr__(self, name, value)

    def _entry(self):
        require(self._creator == (os.getpid(), get_ident()), 'creating PID/thread required for stage owner')
        require((id(self.owner), id(self.channel)) == self._binding[:2], 'held owner/channel binding changed')
        require(type(self.startup) is bytes and sha256(self.startup).hexdigest() == self._binding[2]
            and type(self.created_at) is float and self.created_at == self._binding[3]
            and self.real_owner is self._binding[4]
            and (self.owner.pid, self.owner.creation_filetime, self.channel._binding_inputs) == self._binding[5:],
            'held startup/clock/evidence binding changed')
        if self.observation_commit is not None:
            current = canonical(self.last_observation)
            require(self._attempted and (len(current), sha256(current).hexdigest()) == self.observation_commit
                and (self.last_image is None or (len(self.last_image), sha256(self.last_image).hexdigest()) == self.observation_commit),
                'held terminal observation changed')

    def close(self):
        self._entry()
        errors = []
        try: self.owner.close()
        except BaseException as error: errors.append(('owner_close', error))
        try: self.channel.close()
        except BaseException as error: errors.append(('channel_close', error))
        if errors: raise OwnedStageCloseUnresolved(self, errors)

    def __reduce__(self): raise TypeError('live stage owner cannot be serialized')


class OwnedStageCloseUnresolved(StageChannelError):
    def __init__(self, stage, errors):
        self.stage, self.cleanup_errors = stage, tuple(errors)
        super().__init__('owner_close', 'owned stage resources remain unresolved', errors[0][1])

    def __reduce__(self): raise TypeError('unresolved live stage close cannot be serialized')


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
    return _construct_stage_owner(args, channel, probe_id, owner_factory=owner_factory)


def _construct_stage_owner(args, channel, label, *, owner_factory=None, started=None):
    channel._live()
    require(channel._reader and channel._header is None, 'unbound observer endpoint required')
    spec = channel.spec
    require(spec['mode'] == 'ordinary_owner_probe', 'production stage launch remains disabled')
    frozen_environment = environment()
    prospective = dict(schema='staged_saved_F_probe_CreateProcess_inputs_v1', authority='DRAFT_NONAUTHORITATIVE',
        scope='ordinary_owner_probe_only', probe_id=label, creator_pid=os.getpid(), argv=args, command_line=subprocess.list2cmdline(args),
        cwd=str(ROOT), environment_sha=digest(frozen_environment), context_sha=channel.context_sha,
        descriptor_sha=sha256(channel.descriptor).hexdigest(), channel_name=channel.name,
        owner_pid=2**32-1, owner_creation_filetime=2**64-1,
        actual_os_commandline_independently_verified=False)
    require(len(canonical(prospective)) <= 16384, 'bounded probe startup record required')
    from src.staged_rts24_process_guard_v1 import OwnedChild
    factory = owner_factory or OwnedChild
    # Allocate before __init__ so a partial constructor's actual handles remain reachable.
    owner = object.__new__(factory)
    if started is None: started = time.monotonic()
    require(type(started) is float and math.isfinite(started) and 0 < started <= time.monotonic(), 'actual reservation start required')
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
    require(type(held) is OwnedStage, 'ordinary probe owner required')
    held._entry()
    require(held.channel.spec['mode'] == 'ordinary_owner_probe', 'ordinary probe owner required')
    return _watch_stage(held, absolute_deadline=absolute_deadline)


def _watch_stage(held, *, absolute_deadline=None, relay=None):
    """Active loop: kernel queries and fixed RAM only; no artifact/source I/O."""
    require(type(held) is OwnedStage, 'actual creating-thread probe owner required')
    held._entry(); require(not held._attempted, 'stage observation already attempted')
    owner, channel = held.owner, held.channel
    channel._live()
    spec = channel.spec
    require(spec['mode'] == 'ordinary_owner_probe', 'production stage observation remains disabled')
    relay_phases = None
    if relay is not None:
        require(type(relay) is StageChannel, 'actual stage writer relay required')
        relay._live()
        pair = spec['role'], relay.spec['role']
        require(not relay._reader and relay.context_sha == channel.context_sha and relay.descriptor != channel.descriptor
            and relay.spec['mode'] == spec['mode'] and pair in (('fresh', 'parent'), ('parent', 'controller')),
            'fixed same-context role relay required')
        relay_phases = ('inner_quiesce', 'inner_terminal') if pair[0] == 'fresh' else ('outer_quiesce', 'outer_terminal')
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
    primary = monitor_error = termination_error = quiesce_error = close_error = channel_error = channel_close_error = final_bookend_error = relay_error = None
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
                                if relay is not None:
                                    try: relay.enter(phase)
                                    except BaseException as error:
                                        relay_error = _stage_error(error); raise
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
        if relay is not None:
            try: relay.enter(relay_phases[0])
            except BaseException as error:
                relay_error = relay_error or _stage_error(error); termination('relay_unknown')
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
        close_completed_at = time.monotonic()
        if (relay is not None and relay_error is None and quiet
                and all(error is None for error in (quiesce_error, close_error, channel_error, final_bookend_error, channel_close_error))):
            try: relay.enter(relay_phases[1])
            except BaseException as error:
                relay_error = _stage_error(error); primary = primary or 'relay_unknown'
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
        relay_error=relay_error,
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
        quiesce_started_at=quiesce_started, quiesce_completed_at=quiesce_completed_at, close_attempts_finished_at=close_completed_at,
        observation_finished_at=closed_at,
        active_io_scope='kernel_and_fixed_shared_memory_only', artifact_contents_read=False,
        external_constructor_and_monitor_interrupt_bound_proved=False, terminal_publication_bound_proved=False,
        clock=dict(implementation=time.get_clock_info('monotonic').implementation,
            resolution=time.get_clock_info('monotonic').resolution), poll_interval_seconds=poll_interval,
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
    object.__setattr__(held, 'last_observation', record)
    if len(canonical(record)) > 131072:
        record['stage_process_observed_successfully'] = False
        record['record_encoding_error'] = 'stage process record exceeds128KiB; original observation retained'
        raw = canonical(record)
        object.__setattr__(held, 'observation_commit', (len(raw), sha256(raw).hexdigest()))
        raise StageChannelError('record_byte_cap', 'original observation retained on live capability')
    object.__setattr__(held, 'last_image', canonical(record))
    object.__setattr__(held, 'observation_commit', (len(held.last_image), sha256(held.last_image).hexdigest()))
    return record


ROLE_PROBE_SCHEMA = 'staged_saved_F_ordinary_role_graph_v1'
ROLE_PROBE_SCOPE = 'ordinary_role_algebra_only'
ROLE_PROBE_CASES = ('normal', 'fresh_error', 'mismatch', 'g0_error', 'g1_error', 'g2_error', 'g3_error')


def role_target_caps():
    caps = {name: 64*1024 for name in TARGETS}
    caps.update({'context.json': 2*1024**2, 'worker/parent_metrics.json': 1024**2,
        'worker/fresh/metrics.json': 1024**2, 'worker/comparison_candidate.json': 256*1024,
        'worker/parent_startup.json': 16384, 'worker/fresh/startup.json': 16384,
        'diagnostics/failure.json': 131072})
    caps.update({name: 131072 for name in RECORDS})
    require(sum(caps.values()) == 5537792 and len(caps) == 17, 'fixed role target reservations differ')
    return caps


def role_targets(role):
    ownership = dict(external=('context.json',), controller=('worker/parent_startup.json', 'worker/launcher.json',
        'parent/parent_observation.json', 'diagnostics/failure.json'),
        parent=('worker/events.jsonl', 'worker/parent.stdout.log', 'worker/parent.stderr.log', 'worker/parent_metrics.json',
            'worker/comparison_candidate.json', 'worker/fresh/startup.json', 'worker/fresh/launcher.json',
            'worker/fresh_parent/parent_observation.json'),
        fresh=('worker/fresh/events.jsonl', 'worker/fresh/stdout.log', 'worker/fresh/stderr.log', 'worker/fresh/metrics.json'))
    require(role in ownership, 'closed output writer role required')
    return ownership[role]


def _role_tree(root):
    return tuple((name, directories(root/name)) for name in ('', 'worker', 'worker/fresh', 'worker/fresh_parent', 'parent', 'diagnostics'))+(
        ('context_file_identity', identity(ordinary(root/'context.json'))),)


def make_role_probe_context(output, case='normal'):
    output = Path(output).absolute()
    require(output_mode(output) == 'ordinary_pytest_fixture' and not os.path.lexists(output), 'fresh dedicated ordinary output required')
    require(case in ROLE_PROBE_CASES, 'closed ordinary role fixture required')
    started = time.monotonic()
    value = dict(schema=ROLE_PROBE_SCHEMA, authority='DRAFT_NONAUTHORITATIVE', scope=ROLE_PROBE_SCOPE,
        repo_root=str(ROOT), output_root=str(output), output_parent_directories=directories(output.parent), source_pins=source_pins(),
        executable=dict(path=str(EXE), pin=pin(read(EXE, allow_links=True)), python=sys.version), environment=environment(),
        fixture=dict(left=2, right=3, expected=5), case=case, started=started, deadline=started+8., nonce=secrets.token_hex(32),
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
    return canonical(value)


def check_role_probe_context(raw, expected_sha):
    require(type(raw) is bytes and sha256(raw).hexdigest() == expected_sha, 'held ordinary role context SHA differs')
    value = parse(raw)
    keys(value, 'schema authority scope repo_root output_root output_parent_directories source_pins executable environment fixture case '
        'started deadline nonce F_launch_admitted saved_P1_fresh_process_verified saved_P1_parent_adoption_verified '+' '.join(GATES))
    require(value['schema'] == ROLE_PROBE_SCHEMA and value['authority'] == 'DRAFT_NONAUTHORITATIVE'
        and value['scope'] == ROLE_PROBE_SCOPE and all(value[k] is False for k in GATES)
        and value['F_launch_admitted'] is value['saved_P1_fresh_process_verified'] is value['saved_P1_parent_adoption_verified'] is False,
        'ordinary role authority differs')
    root = Path(value['output_root'])
    require(str(root.absolute()) == str(root) and '..' not in root.parts and output_mode(root) == 'ordinary_pytest_fixture',
        'ordinary role output differs')
    require(value['output_parent_directories'] == [list(row) for row in directories(root.parent)], 'ordinary output parent identity differs')
    require(value['fixture'] == dict(left=2, right=3, expected=5)
        and canonical(value['fixture']) == b'{"expected":5,"left":2,"right":3}'
        and value['case'] in ROLE_PROBE_CASES, 'closed ordinary fixture differs')
    require(type(value['started']) is float and type(value['deadline']) is float
        and math.isfinite(value['started']) and math.isfinite(value['deadline'])
        and 0 < value['started'] <= time.monotonic() <= value['deadline'] == value['started']+8., 'ordinary graph deadline')
    require(type(value['nonce']) is str and len(value['nonce']) == 64 and all(c in '0123456789abcdef' for c in value['nonce']), 'role nonce domain')
    require(value['repo_root'] == str(ROOT) and value['source_pins'] == source_pins() and value['environment'] == environment()
        and value['executable'] == dict(path=str(EXE), pin=pin(read(EXE, allow_links=True)), python=sys.version)
        and Path(sys.executable).absolute() == EXE and Path.cwd().absolute() == ROOT, 'ordinary role actual source/runtime differs')
    for name in value['source_pins']:
        if not name.endswith('.py'): continue
        module = sys.modules.get(name[:-3].replace('/', '.').removesuffix('.__init__'))
        if module is not None:
            require(type(getattr(module, '__file__', None)) is str and Path(module.__file__).absolute() == ROOT/name
                and pin(read(module.__file__)) == value['source_pins'][name], 'ordinary loaded selected module differs')
    return value


def _role_context(raw, expected_sha):
    value = parse(raw)
    return check_role_probe_context(raw, expected_sha) if value.get('schema') == ROLE_PROBE_SCHEMA else check_context(raw, expected_sha)


class RolePublicationUnresolved(OSError):
    def __init__(self, target, raw, phase, may, primary):
        self.target, self.expected_sha, self.phase = str(target), sha256(raw).hexdigest(), phase
        self.may_have_published, self.primary_error = may, _stage_error(primary)
        super().__init__('role publication unresolved at '+phase)


class RoleExecutionUnresolved(RuntimeError):
    def __init__(self, primary, stage=None, diagnostic=None, cleanup_errors=()):
        self.primary, self.stage, self.diagnostic = primary, stage, diagnostic
        self.cleanup_errors = tuple(cleanup_errors)
        super().__init__('role execution unresolved; original errors and capabilities retained')

    def __reduce__(self): raise TypeError('unresolved role capabilities cannot be serialized')


def _role_error_holds_capability(error):
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen: continue
        if len(seen) >= 256: return True
        seen.add(id(current))
        if isinstance(current, (StageConstructionUnresolved, StageChannelConstructionUnresolved, RoleExecutionUnresolved, OwnedStageCloseUnresolved)): return True
        pending.extend((current.__cause__, current.__context__))
    return False


def _role_stage_still_open(stage):
    return stage is not None and (any(getattr(stage.owner, name, None) is not None for name in ('_job', '_process', '_thread'))
        or bool(getattr(stage.owner, '_members', {}))
        or any(getattr(getattr(stage.owner, '_info', None), name, None) is not None for name in ('process', 'thread'))
        or any(getattr(stage.channel, name, None) is not None for name in ('_view', '_map', '_mutex'))
        or stage.last_observation is not None and stage.last_image is None)


def _publish_role_file(target, raw, *, hook=None):
    """Private fault seam; production uses closed role paths with no callback."""
    target = Path(target)
    require(type(raw) is bytes and len(raw) <= 8*1024**2, 'bounded role publication bytes required')
    pending = target.with_name(target.name+'.pending')
    phase, may = 'before_open', False
    def step(name):
        nonlocal phase
        phase = name
        if hook is not None: hook(name, target)
    try:
        expected_parent = directories(target.parent)
        require(not os.path.lexists(target), 'create-only role target required')
        require(not os.path.lexists(pending), 'role pending already exists')
        step('before_open')
        with pending.open('xb') as stream:
            stream.write(raw); step('after_write')
            stream.flush(); os.fsync(stream.fileno()); step('after_fsync')
        published_identity = identity(ordinary(pending))
        require(read(pending) == raw, 'role pending readback differs'); step('after_pending_readback')
        step('before_rename')
        require(directories(target.parent) == expected_parent, 'role directory changed before rename')
        phase, may = 'rename', True
        os.rename(pending, target); step('after_rename')
        require(read(target) == raw, 'role final readback differs'); step('after_final_readback')
        require(directories(target.parent) == expected_parent and identity(ordinary(target)) == published_identity,
            'role directory/file identity changed after publish')
        return dict(pin(raw), identity=published_identity)
    except BaseException as error:
        raise RolePublicationUnresolved(target, raw, phase, may, error) from error


@dataclass(frozen=True, init=False)
class RoleStore:
    root: Path
    raw: bytes
    sha: str
    tree: tuple
    creator: tuple
    binding: tuple
    writer: str
    receipts: tuple
    receipt_commit: str
    child_reservation: object
    child_consumed: bool
    reservation_commit: str
    target_attempts: tuple
    attempt_commit: str

    def __init__(self, raw, expected_sha, expected_tree_sha, writer='controller'):
        context = _role_context(raw, expected_sha)
        require(writer in ('controller', 'parent', 'fresh'), 'closed role store writer required')
        root = Path(context['output_root']); tree = _role_tree(root)
        require(digest(tree) == expected_tree_sha and read(root/'context.json') == raw, 'external output/context binding differs')
        values = dict(root=root, raw=raw, sha=expected_sha, tree=tree, writer=writer, creator=(os.getpid(), get_ident()),
            receipts=(), receipt_commit=digest(()))
        values.update(child_reservation=None, child_consumed=False, reservation_commit=digest([None, False]))
        values.update(target_attempts=(), attempt_commit=digest(()))
        values['binding'] = str(root), expected_sha, tree, writer
        for name, value in values.items(): object.__setattr__(self, name, value)

    def check(self):
        require(self.creator == (os.getpid(), get_ident()) and (str(self.root), self.sha, self.tree, self.writer) == self.binding
            and type(self.raw) is bytes and sha256(self.raw).hexdigest() == self.sha, 'creating held role store required')
        require(_role_tree(self.root) == self.tree and read(self.root/'context.json') == self.raw, 'role output/context bookend differs')
        require(digest(self.receipts) == self.receipt_commit, 'held role publication receipts changed')
        require(type(self.child_consumed) is bool and digest([self.child_reservation, self.child_consumed]) == self.reservation_commit,
            'held one-shot role reservation changed')
        require(digest(self.target_attempts) == self.attempt_commit, 'held role target attempts changed')
        for name, _, _, expected_identity in self.receipts:
            require(identity(ordinary(self.root/name)) == expected_identity, 'published role file identity changed')

    def accounting(self):
        self.check(); safety = _output_safety(self.root, self.tree[0][1])
        caps = role_target_caps(); remaining_bytes = remaining_files = 0
        for name, cap in caps.items():
            present = [self.root/n for n in (name, name+'.pending') if os.path.lexists(self.root/n)]
            require(len(present) <= 1, 'role final/pending conflict')
            used = ordinary(present[0]).st_size if present else 0
            require(used <= cap, 'role per-target byte cap')
            remaining_bytes += cap-used; remaining_files += int(not present)
        require(safety['bytes']+remaining_bytes == sum(caps.values()) <= CAPS['output_bytes']
            and safety['files']+remaining_files == len(caps) <= CAPS['files'], 'all role reservations do not fit')
        self.check()
        return dict(safety, all_targets_reserved_bytes=remaining_bytes, all_targets_reserved_files=remaining_files,
            reservation_envelope_bytes=sum(caps.values()))

    def publish(self, role, name, value):
        return _publish_role_target(self, role, name, canonical(value))

    def reserve_child(self, role):
        self.check()
        require((self.writer, role) in (('controller', 'parent'), ('parent', 'fresh'))
            and self.child_reservation is None, 'single nested role reservation required')
        reservation = (role, time.monotonic(), secrets.token_hex(32), self.creator)
        object.__setattr__(self, 'child_reservation', reservation)
        object.__setattr__(self, 'reservation_commit', digest([reservation, False]))
        return reservation

    def consume_child(self, role, reservation):
        self.check()
        require(reservation is self.child_reservation and reservation[0] == role and reservation[3] == self.creator
            and not self.child_consumed, 'creating one-shot role reservation required')
        object.__setattr__(self, 'child_consumed', True)
        object.__setattr__(self, 'reservation_commit', digest([reservation, True]))

    def read_after_quiet(self, name, held_owner):
        record = _held_role_process(held_owner, self)
        role = held_owner.channel.spec['role']
        require(name in TARGETS and name.startswith('worker/fresh/' if role == 'fresh' else 'worker/')
            and role in ('parent', 'fresh') and record['stage_process_observed_successfully'] is True,
            'successful retained owner quiet required before child content')
        _checked_role_process_record(self, record, role)
        self.accounting(); raw = read(self.root/name)
        require(len(raw) <= role_target_caps()[name], 'bounded child target required')
        self.accounting(); return raw

    def read_diagnostic_after_quiet(self, name, held_owner):
        _held_role_process(held_owner, self)
        require(name in ('worker/events.jsonl', 'worker/parent.stdout.log', 'worker/parent.stderr.log',
            'worker/fresh/events.jsonl', 'worker/fresh/stdout.log', 'worker/fresh/stderr.log'), 'application diagnostic target required')
        self.accounting(); raw = read(self.root/name)
        require(len(raw) <= role_target_caps()[name], 'bounded diagnostic required')
        self.accounting(); return raw

    def __reduce__(self): raise TypeError('live role store cannot be serialized')


def _held_role_process(held, store):
    require(type(held) is OwnedStage, 'direct retained owner capability required')
    held._entry()
    require(held._attempted and held.real_owner and type(held.last_image) is bytes
        and canonical(held.last_observation) == held.last_image and held.channel.context_sha == store.sha,
        'held process observation changed or unavailable')
    record = parse(held.last_image)
    require(canonical(record['startup']) == held.startup, 'held actual startup image differs')
    role = held.channel.spec['role']
    require((role, store.writer) in (('fresh', 'parent'), ('parent', 'controller'))
        and record['startup']['probe_id'] == 'role_graph_'+role
        and record['startup']['creator_pid'] == store.creator[0]
        and record['startup']['argv'] == _role_child_argv(role, store, held.channel), 'exact role owner/output binding differs')
    require(record['owner_evidence'] == 'direct_owned_child' and record['job_quiet_confirmed'] is True
        and held.owner._process is held.owner._job is held.owner._thread is None and not held.owner._members
        and _stage_complete_witness(held.owner.quiescence_witness, held.owner.pid, held.owner.creation_filetime)
        and canonical(held.owner.quiescence_witness) == canonical(record['quiescence_witness'])
        and held.channel._map is held.channel._mutex is held.channel._view is None,
        'closed retained owner quiet required before content')
    return record


def _checked_role_process_record(store, value, role):
    keys(value, 'authority scope owner_evidence startup descriptor exit_code primary_stop_reason monitor_error '
        'termination_requested termination_call_succeeded termination_error quiesce_error close_error channel_error '
        'final_bookend_error channel_close_error quiet_witness_consistent relay_error job_quiet_confirmed quiescence_witness '
        'stage_process_observed_successfully logic_path_completed stage_transcript_complete frames_observed phases_observed '
        'transcript_sha stage_header transcript_frames samples sampled_tree_peak_rss_bytes terminal_tree_rss_bytes peak_job_commit_bytes '
        'release_attempted construction_seconds observation_seconds remaining_total_seconds total_deadline terminal_accepted '
        'terminal_exit_deadline terminal_exit_cap_seconds terminal_exit_limiting_deadline root_exit_observed_at termination_requested_at '
        'quiesce_started_at quiesce_completed_at close_attempts_finished_at observation_finished_at active_io_scope artifact_contents_read '
        'external_constructor_and_monitor_interrupt_bound_proved terminal_publication_bound_proved clock poll_interval_seconds '
        'F_launch_admitted saved_P1_fresh_process_verified saved_P1_parent_adoption_verified '+' '.join(GATES))
    spec = checked_stage_descriptor(canonical(value['descriptor']))
    require(canonical(spec) == ordinary_stage_descriptor(role, 'role_graph'), 'role process fixed descriptor differs')
    require(value['authority'] == 'DRAFT_NONAUTHORITATIVE' and value['scope'] == 'ordinary_retained_owner_stage_process_only'
        and value['owner_evidence'] == 'direct_owned_child' and value['exit_code'] == 0
        and all(value[name] is True for name in ('stage_process_observed_successfully', 'job_quiet_confirmed',
            'quiet_witness_consistent', 'logic_path_completed', 'stage_transcript_complete', 'release_attempted')),
        'successful direct role process required')
    require(all(value[name] is None for name in ('primary_stop_reason', 'monitor_error', 'termination_error', 'quiesce_error',
        'close_error', 'channel_error', 'final_bookend_error', 'channel_close_error', 'relay_error')), 'role process error remains')
    require(all(value[name] is False for name in (*GATES, 'F_launch_admitted', 'saved_P1_fresh_process_verified',
        'saved_P1_parent_adoption_verified', 'external_constructor_and_monitor_interrupt_bound_proved', 'terminal_publication_bound_proved',
        'artifact_contents_read', 'termination_requested', 'termination_call_succeeded')), 'role process authority differs')
    startup, header = value['startup'], value['stage_header']
    keys(startup, 'schema authority scope probe_id creator_pid argv command_line cwd environment_sha context_sha descriptor_sha '
        'channel_name owner_pid owner_creation_filetime actual_os_commandline_independently_verified')
    require(startup['schema'] == 'staged_saved_F_probe_CreateProcess_inputs_v1'
        and startup['authority'] == 'DRAFT_NONAUTHORITATIVE' and startup['scope'] == 'ordinary_owner_probe_only', 'role startup schema differs')
    keys(header, 'schema context_sha nonce descriptor owner_pid owner_creation_filetime slots slot_bytes')
    require(header['context_sha'] == startup['context_sha'] == store.sha and header['descriptor'] == spec
        and header['slots'] == 16 and header['slot_bytes'] == 4096 and header['schema'] == 'staged_saved_F_memory_header_v1', 'role frame header differs')
    require(startup['probe_id'] == 'role_graph_'+role and startup['owner_pid'] == header['owner_pid']
        and startup['owner_creation_filetime'] == header['owner_creation_filetime'], 'role startup owner differs')
    require(type(header['owner_pid']) is int and 0 < header['owner_pid'] < 2**32
        and type(header['owner_creation_filetime']) is int and 0 < header['owner_creation_filetime'] < 2**64
        and type(startup['owner_pid']) is int and type(startup['owner_creation_filetime']) is int
        and type(startup['creator_pid']) is int and 0 < startup['creator_pid'] < 2**32
        and type(header['nonce']) is str and len(header['nonce']) == 64 and all(c in '0123456789abcdef' for c in header['nonce'])
        and type(startup['channel_name']) is str and startup['channel_name'].startswith(STAGE_PREFIX)
        and len(startup['channel_name']) == len(STAGE_PREFIX)+64
        and all(c in '0123456789abcdef' for c in startup['channel_name'][len(STAGE_PREFIX):]), 'role startup/header scalar domains differ')
    class Channel:
        name, nonce, descriptor = startup['channel_name'], header['nonce'], canonical(spec)
    require(startup['argv'] == _role_child_argv(role, store, Channel)
        and startup['command_line'] == subprocess.list2cmdline(startup['argv']) and startup['cwd'] == str(ROOT)
        and startup['environment_sha'] == digest(parse(store.raw)['environment'])
        and startup['descriptor_sha'] == sha256(canonical(spec)).hexdigest()
        and startup['actual_os_commandline_independently_verified'] is False, 'role exact CreateProcess inputs differ')
    require(_stage_complete_witness(value['quiescence_witness'], header['owner_pid'], header['owner_creation_filetime']), 'role complete inventory required')
    require(type(value['samples']) is int and value['samples'] > 0 and type(value['sampled_tree_peak_rss_bytes']) is int
        and 0 <= value['sampled_tree_peak_rss_bytes'] <= spec['rss_bytes'] and type(value['peak_job_commit_bytes']) is int
        and 0 <= value['peak_job_commit_bytes'] <= spec['job_commit_bytes'], 'role resource observation differs')
    frames = value['transcript_frames']; require(type(frames) is list and len(frames) == len(spec['phases'])+1, 'complete role frames required')
    previous, slots = '0'*64, []; header_sha = sha256(_stage_slot(canonical(header), STAGE_HEADER_COMMIT)).hexdigest()
    for index, frame in enumerate(frames):
        keys(frame, 'schema sequence phase binding_sha previous_sha producer_pid producer_creation_filetime stamp error_code')
        require(frame['schema'] == 'staged_saved_F_memory_frame_v1' and type(frame['sequence']) is int and frame['sequence'] == index
            and frame['phase'] == (spec['phases']+['terminal'])[index] and frame['binding_sha'] == header_sha
            and frame['previous_sha'] == previous and frame['error_code'] is None
            and frame['producer_pid'] == header['owner_pid'] and frame['producer_creation_filetime'] == header['owner_creation_filetime']
            and type(frame['stamp']) is float and math.isfinite(frame['stamp']) and frame['stamp'] > 0, 'role transcript binding differs')
        raw = canonical(frame); slots.append(_stage_slot(raw, STAGE_COMMIT)); previous = sha256(raw).hexdigest()
    require(value['frames_observed'] == len(frames) and value['transcript_sha'] == sha256(b''.join(slots)).hexdigest(), 'role transcript digest differs')
    for key in ('root_exit_observed_at', 'quiesce_started_at', 'quiesce_completed_at', 'close_attempts_finished_at', 'observation_finished_at', 'total_deadline'):
        require(type(value[key]) is float and math.isfinite(value[key]), 'finite role observer time required')
    require(value['root_exit_observed_at'] <= value['quiesce_started_at'] <= value['quiesce_completed_at']
        <= value['close_attempts_finished_at'] <= value['observation_finished_at'] <= value['total_deadline']
        and value['remaining_total_seconds'] == value['total_deadline']-value['observation_finished_at'], 'role observer time order differs')
    require(value['active_io_scope'] == 'kernel_and_fixed_shared_memory_only' and value['poll_interval_seconds'] == .01
        and value['clock'] == dict(implementation=time.get_clock_info('monotonic').implementation,
            resolution=time.get_clock_info('monotonic').resolution), 'role monitor contract differs')
    entries = value['phases_observed']
    require(type(entries) is list and len(entries) == len(spec['phases']), 'complete observer phase entries required')
    for index, entry in enumerate(entries):
        keys(entry, 'phase observer_entered')
        require(entry['phase'] == spec['phases'][index] and type(entry['observer_entered']) is float
            and math.isfinite(entry['observer_entered']) and entry['observer_entered'] > 0
            and (index == 0 or entries[index-1]['observer_entered'] <= entry['observer_entered']), 'observer phase order differs')
    require(type(value['terminal_accepted']) is float and type(value['terminal_exit_deadline']) is float
        and math.isfinite(value['terminal_accepted']) and math.isfinite(value['terminal_exit_deadline'])
        and entries[-1]['observer_entered'] <= value['terminal_accepted'] <= value['terminal_exit_deadline']
        and value['terminal_exit_cap_seconds'] == spec['terminal_seconds']
        and value['terminal_exit_limiting_deadline'] in ('active', 'phase', 'exit_cap'), 'role terminal clock differs')
    require(type(value['construction_seconds']) is float and 0 <= value['construction_seconds'] <= spec['total_seconds']
        and type(value['observation_seconds']) is float and 0 <= value['observation_seconds'] <= spec['total_seconds']
        and value['termination_requested_at'] is None, 'role duration or success termination differs')
    return value


def _publish_role_target(store, role, name, raw, *, hook=None):
    require(type(store) is RoleStore and role == store.writer and name in role_targets(role), 'fixed target writer required')
    parse(raw); require(len(raw) <= role_target_caps()[name], 'role target exceeds reserved bytes')
    store.accounting()
    require(name not in store.target_attempts, 'single role target attempt required')
    attempts = store.target_attempts+(name,)
    object.__setattr__(store, 'target_attempts', attempts); object.__setattr__(store, 'attempt_commit', digest(attempts))
    result = _publish_role_file(store.root/name, raw, hook=hook)
    try:
        store.accounting(); require(read(store.root/name) == raw, 'role publication final bytes differ')
        require(identity(ordinary(store.root/name)) == result['identity'], 'role publication receipt differs')
        receipts = store.receipts+((name, len(raw), sha256(raw).hexdigest(), result['identity']),)
        object.__setattr__(store, 'receipts', receipts); object.__setattr__(store, 'receipt_commit', digest(receipts))
        store.check()
    except BaseException as error:
        raise RolePublicationUnresolved(name, raw, 'store_final_bookend', True, error) from error
    return pin(raw)


def prepare_role_probe_output(raw, expected_sha):
    """Ordinary harness simulates external root/context, then controller setup."""
    context = check_role_probe_context(raw, expected_sha); root = Path(context['output_root'])
    require(not os.path.lexists(root), 'external role root already exists')
    require(len(raw) <= role_target_caps()['context.json'], 'context reserve exceeded')
    root.mkdir(); root_identity = directories(root)
    context_receipt = _publish_role_file(root/'context.json', raw)
    require(directories(root) == root_identity and set(root.iterdir()) == {root/'context.json'}, 'controller requires external context only')
    for name in ('worker', 'worker/fresh', 'worker/fresh_parent', 'parent', 'diagnostics'):
        (root/name).mkdir()
    require(identity(ordinary(root/'context.json')) == context_receipt['identity'], 'external context identity changed')
    store = RoleStore(raw, expected_sha, digest(_role_tree(root)))
    store.accounting(); return store


def _role_child_argv(role, store, channel):
    require(role in ('parent', 'fresh'), 'closed child role required')
    body = ("from experiments import staged_rts24_saved_fresh_adoption_v1 as e; "
        f"e._ordinary_role_entry({role!r},{str(store.root/'context.json')!r},{store.sha!r},"
        f"{digest(store.tree)!r},{channel.name!r},{channel.nonce!r})")
    return [str(EXE), '-B', '-s', '-c', body]


def _create_role_owner(role, store, reservation=None):
    store.check()
    if reservation is None: reservation = store.reserve_child(role)
    store.consume_child(role, reservation)
    context = check_role_probe_context(store.raw, store.sha)
    require((store.writer, role) in (('controller', 'parent'), ('parent', 'fresh')), 'fixed nested role owner required')
    descriptor = ordinary_stage_descriptor(role, 'role_graph')
    channel = StageChannel.create(store.sha, descriptor)
    try: return _construct_stage_owner(_role_child_argv(role, store, channel), channel, 'role_graph_'+role, started=reservation[1])
    except BaseException as primary:
        try: channel.close()
        except BaseException as cleanup:
            raise StageChannelConstructionUnresolved(channel, primary, cleanup, 'role_owner_channel_cleanup') from primary
        raise


def _role_fixture_payload(context, role):
    fixture = context['fixture']
    computed = fixture['left']+fixture['right']
    if context['case'] == 'mismatch' and role == 'fresh': computed += 1
    return dict(schema='staged_saved_F_ordinary_algebra_payload_v1', authority='DRAFT_NONAUTHORITATIVE',
        scope=ROLE_PROBE_SCOPE, fixture_sha=digest(fixture), operands=[fixture['left'], fixture['right']], result=computed)


def _disable_saved_effects(adapter):
    import highspy
    import pyomo.environ as pyo
    def denied(*args, **kwargs): raise RuntimeError('saved F read-only role requested a forbidden effect')
    for module, name in ((pyo, 'SolverFactory'), (highspy, 'Highs'), (subprocess, 'Popen'),
            (adapter.prefix.point.backend, 'make_model'), (adapter.prefix.point.backend, 'call_highs'),
            (adapter.codec.EvidenceStore, 'put'), (adapter.codec, 'publish'), (adapter.journal, 'publish')):
        setattr(module, name, denied)
    for name in ('create_session', 'begin_step', 'commit_step', 'finish'): setattr(adapter.journal, name, denied)


def _role_reconstruct(store, role):
    store.check(); context = parse(store.raw)
    if context['schema'] == ROLE_PROBE_SCHEMA:
        if context['case'] == 'fresh_error' and role == 'fresh': raise ValueError('fixed ordinary fresh error')
        return canonical(_role_fixture_payload(context, role)), None
    execution_context(role, store.raw, store.sha)
    from src import staged_rts24_saved_fresh_adoption_v1 as adapter
    _disable_saved_effects(adapter)
    held = adapter.hold(context['source_pins'], canonical(context['caller_core']))
    return canonical(adapter.replay(held, store.sha)), held


def _role_input_bookend(store, stage, held=None):
    require(stage in ('G0', 'G1', 'G2', 'G3'), 'closed input bookend stage required')
    context = _role_context(store.raw, store.sha); store.check()
    if context['schema'] == ROLE_PROBE_SCHEMA:
        if context['case'] == stage.lower()+'_error': raise ValueError('fixed ordinary '+stage+' bookend error')
    else:
        execution_context('supervise' if store.writer == 'controller' else store.writer, store.raw, store.sha)
        from src import staged_rts24_saved_fresh_adoption_v1 as adapter
        if held is None: held = adapter.hold(context['source_pins'], canonical(context['caller_core']))
        else: adapter.bookend(held)
    return held, dict(stage=stage, context_sha=store.sha, source_sha=digest(context['source_pins']),
        observed_at=time.monotonic(), scope=context['scope'])


def _role_compare(store, parent_raw, fresh_raw):
    store.check(); context = parse(store.raw)
    if context['schema'] == ROLE_PROBE_SCHEMA:
        expected = canonical(_role_fixture_payload(dict(context, case='normal'), 'parent'))
        require(parent_raw == fresh_raw == expected, 'independent ordinary payloads differ from external fixture')
        return dict(payload_byte_equality_verified=True, payload_sha=sha256(expected).hexdigest())
    execution_context('parent' if store.writer == 'parent' else 'supervise', store.raw, store.sha)
    from src import staged_rts24_saved_fresh_adoption_v1 as adapter
    return adapter.compare_payloads(parent_raw, fresh_raw, context_sha=store.sha,
        source_sha=digest(context['source_pins']), input_pins_sha=digest(context['input_files']),
        caller_sha=context['caller_sha'], caller_image=canonical(context['caller_core']))


def _check_role_candidates(store, outer, candidate_raw, parent_raw, fresh_raw, inner_raw, inner_observation_raw):
    outer_record = _held_role_process(outer, store)
    _checked_role_process_record(store, outer_record, 'parent')
    require(store.read_after_quiet('worker/launcher.json', outer) == outer.last_image, 'saved outer process differs from live owner')
    inner = _checked_role_process_record(store, parse(inner_raw), 'fresh')
    require(read(store.root/'worker/parent_startup.json') == outer.startup
        and store.read_after_quiet('worker/fresh/startup.json', outer) == canonical(inner['startup']), 'role startup file differs from actual capture')
    outer_members = {(item['pid'], item['creation_filetime']) for item in outer_record['quiescence_witness']['member_identities']}
    inner_members = {(item['pid'], item['creation_filetime']) for item in inner['quiescence_witness']['member_identities']}
    require(inner_members <= outer_members and inner['startup']['creator_pid'] == outer_record['startup']['owner_pid'], 'nested role identities differ')
    candidate, observation, context = parse(candidate_raw), parse(inner_observation_raw), parse(store.raw)
    keys(candidate, 'schema authority scope context_sha parent_payload_pin fresh_payload_pin comparison G1 inner_process_sha '
        'inner_observation_pin F_launch_admitted saved_P1_fresh_process_verified saved_P1_parent_adoption_verified '+' '.join(GATES))
    keys(observation, 'schema authority scope context_sha process_record_sha startup_sha metrics_pin ownership_status execution_status '
        'F_launch_admitted saved_P1_fresh_process_verified saved_P1_parent_adoption_verified '+' '.join(GATES))
    for item in (candidate, observation):
        require(item['authority'] == 'DRAFT_NONAUTHORITATIVE' and item['scope'] == context['scope'] and item['context_sha'] == store.sha
            and all(item[key] is False for key in (*GATES, 'F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified')),
            'role candidate/observation authority differs')
    require(candidate['schema'] == 'staged_saved_F_role_comparison_candidate_v1'
        and observation['schema'] == 'staged_saved_F_inner_role_observation_v1'
        and candidate['parent_payload_pin'] == pin(parent_raw) and candidate['fresh_payload_pin'] == pin(fresh_raw)
        and candidate['inner_process_sha'] == observation['process_record_sha'] == sha256(inner_raw).hexdigest()
        and candidate['inner_observation_pin'] == pin(inner_observation_raw)
        and observation['startup_sha'] == sha256(canonical(inner['startup'])).hexdigest()
        and observation['metrics_pin'] == pin(fresh_raw) and observation['ownership_status'] == 'quiet_verified'
        and observation['execution_status'] == 'successful_exit', 'role candidate/record pins differ')
    require(canonical(candidate['comparison']) == canonical(_role_compare(store, parent_raw, fresh_raw)), 'complete role comparison differs')
    g1 = candidate['G1']; keys(g1, 'stage context_sha source_sha observed_at scope')
    require(g1['stage'] == 'G1' and g1['context_sha'] == store.sha and g1['source_sha'] == digest(context['source_pins'])
        and g1['scope'] == context['scope'] and type(g1['observed_at']) is float and math.isfinite(g1['observed_at']), 'parent G1 reference differs')


def _role_content_inventory(store, outer, *, include_observation=True):
    process = _held_role_process(outer, store)
    _checked_role_process_record(store, process, 'parent')
    store.accounting(); inventory = {}
    expected_names = set(TARGETS)-{'diagnostics/failure.json'}
    if not include_observation: expected_names.remove('parent/parent_observation.json')
    for name in sorted(expected_names):
        target = store.root/name; before = identity(ordinary(target))
        raw = read(target)
        require(len(raw) <= role_target_caps()[name], 'inventory target byte cap')
        inventory[name] = dict(pin=pin(raw), identity=before)
    store.accounting()
    for name, expected in inventory.items():
        require(identity(ordinary(store.root/name)) == expected['identity'] and pin(read(store.root/name)) == expected['pin'], 'role content inventory bookend differs')
    for name, count, expected_sha, expected_identity in store.receipts:
        if name in inventory:
            require(inventory[name] == dict(pin=dict(bytes=count, sha256=expected_sha), identity=expected_identity), 'saved role receipt bytes differ')
    require(not os.path.lexists(store.root/'diagnostics/failure.json')
        and sum(row['pin']['bytes'] for row in inventory.values()) == store.accounting()['bytes'], 'role success inventory differs')
    require(canonical(_held_role_process(outer, store)) == canonical(process), 'held outer inventory permission changed')
    return inventory


def _role_auxiliary(store, role):
    names = ('worker/events.jsonl', 'worker/parent.stdout.log', 'worker/parent.stderr.log') if role == 'parent' else (
        'worker/fresh/events.jsonl', 'worker/fresh/stdout.log', 'worker/fresh/stderr.log')
    store.accounting()
    for name in names:
        require(store.writer == role and name in role_targets(role), 'fixed application log writer required')
        target = store.root/name
        raw = canonical(dict(event='application_role_entered', role=role, context_sha=store.sha))+b'\n' if name.endswith('.jsonl') else b''
        with target.open('xb') as stream: stream.write(raw)
    store.accounting()


def _role_error_event(store, error):
    role = store.writer
    name = 'worker/events.jsonl' if role == 'parent' else 'worker/fresh/events.jsonl'
    require(role in ('parent', 'fresh') and name in role_targets(role), 'role application error writer required')
    store.accounting(); target = store.root/name
    old = read(target) if os.path.lexists(target) else b''
    event = canonical(dict(event='application_role_error', role=role, context_sha=store.sha, error=_stage_error(error)))+b'\n'
    require(len(old)+len(event) <= role_target_caps()[name], 'application event reserve exceeded')
    before = identity(ordinary(target)) if old else None
    with target.open('ab' if os.path.lexists(target) else 'xb') as stream:
        if before is not None: require(identity(os.fstat(stream.fileno())) == before, 'application event changed before append')
        stream.write(event); stream.flush(); os.fsync(stream.fileno())
    require(read(target) == old+event, 'application event changed after append'); store.accounting()


def _inner_observation(store, held, metrics_pin):
    held._entry()
    require(type(held.last_image) is bytes and canonical(held.last_observation) == held.last_image, 'held inner process image required')
    record = parse(held.last_image)
    return dict(schema='staged_saved_F_inner_role_observation_v1', authority='DRAFT_NONAUTHORITATIVE',
        scope=parse(store.raw)['scope'], context_sha=store.sha, process_record_sha=sha256(held.last_image).hexdigest(),
        startup_sha=sha256(held.startup).hexdigest(), metrics_pin=metrics_pin,
        ownership_status='quiet_verified' if record['job_quiet_confirmed'] else 'unknown',
        execution_status='successful_exit' if record['stage_process_observed_successfully'] else 'failed_or_unknown',
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)


def _run_fresh_role(store, writer):
    writer.enter('fresh'); _role_auxiliary(store, 'fresh')
    raw, _ = _role_reconstruct(store, 'fresh')
    _publish_role_target(store, 'fresh', 'worker/fresh/metrics.json', raw)
    writer.enter('terminal')


def _run_parent_role(store, writer):
    writer.enter('parent'); _role_auxiliary(store, 'parent')
    parent_raw, parent_input = _role_reconstruct(store, 'parent')
    parent_pin = _publish_role_target(store, 'parent', 'worker/parent_metrics.json', parent_raw)
    # Entering fresh means reservation began, charging capture to its active cap.
    reservation = store.reserve_child('fresh'); writer.enter('fresh')
    fresh = _create_role_owner('fresh', store, reservation)
    try:
        store.publish('parent', 'worker/fresh/startup.json', parse(fresh.startup))
        process = _watch_stage(fresh, absolute_deadline=parse(store.raw)['deadline'], relay=writer)
    except BaseException as primary:
        try: fresh.close()
        except BaseException as cleanup: raise RoleExecutionUnresolved(primary, fresh, cleanup_errors=(('fresh_stage_close', cleanup),)) from primary
        raise
    metrics_pin = None
    if process['job_quiet_confirmed']:
        store.publish('parent', 'worker/fresh/launcher.json', process)
        if process['stage_process_observed_successfully']:
            fresh_raw = store.read_after_quiet('worker/fresh/metrics.json', fresh); metrics_pin = pin(fresh_raw)
    store.publish('parent', 'worker/fresh_parent/parent_observation.json', _inner_observation(store, fresh, metrics_pin))
    require(process['stage_process_observed_successfully'] and metrics_pin is not None, 'fresh role unsuccessful or unknown')
    writer.enter('parent_compare')
    _, g1 = _role_input_bookend(store, 'G1', parent_input)
    comparison = _role_compare(store, parent_raw, fresh_raw)
    candidate = dict(schema='staged_saved_F_role_comparison_candidate_v1', authority='DRAFT_NONAUTHORITATIVE',
        scope=parse(store.raw)['scope'], context_sha=store.sha, parent_payload_pin=parent_pin, fresh_payload_pin=metrics_pin,
        comparison=comparison, G1=g1, inner_process_sha=sha256(fresh.last_image).hexdigest(),
        inner_observation_pin=pin(read(store.root/'worker/fresh_parent/parent_observation.json')),
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
    store.publish('parent', 'worker/comparison_candidate.json', candidate)
    writer.enter('terminal')


def _ordinary_role_entry(role, context_path, context_sha, tree_sha, channel_name, channel_nonce):
    require(role in ('parent', 'fresh'), 'closed ordinary role entry required')
    raw = read(context_path); require(sha256(raw).hexdigest() == context_sha, 'held role entry context differs')
    context = parse(raw)
    require(context.get('schema') == ROLE_PROBE_SCHEMA and Path(context_path) == Path(context['output_root'])/'context.json', 'fixed ordinary role context path required')
    descriptor = ordinary_stage_descriptor(role, 'role_graph')
    writer = StageChannel.attach(channel_name, channel_nonce, context_sha, descriptor)
    store = None
    try:
        store = RoleStore(raw, context_sha, tree_sha, role)
        expected = _role_child_argv(role, store, writer)
        require(sys.argv == ['-c'], 'ordinary role actual entry differs')
        require(expected[:4] == [str(EXE), '-B', '-s', '-c'], 'fixed ordinary interpreter required')
        (_run_parent_role if role == 'parent' else _run_fresh_role)(store, writer)
    except BaseException as primary:
        cleanup_errors = []
        if store is not None:
            try: _role_error_event(store, primary)
            except BaseException as error: cleanup_errors.append(('application_event', error))
        try: writer.fail('role_diagnostic_failed' if cleanup_errors else 'role_execution_failed')
        except BaseException as error: cleanup_errors.append(('failure_signal', error))
        try: writer.close()
        except BaseException as error: cleanup_errors.append(('writer_close', error))
        raise RoleExecutionUnresolved(primary, cleanup_errors=cleanup_errors) from primary
    writer.close()


def run_ordinary_role_graph(output, case='normal'):
    raw = make_role_probe_context(output, case); context_sha = sha256(raw).hexdigest()
    store = prepare_role_probe_output(raw, context_sha)
    return _run_role_controller(store)


def _run_role_controller(store):
    held_input = None; marks = []; outer = None; observation_pin = None
    try:
        held_input, g0 = _role_input_bookend(store, 'G0'); marks.append(g0)
        outer = _create_role_owner('parent', store)
        try:
            store.publish('controller', 'worker/parent_startup.json', parse(outer.startup))
            process = _watch_stage(outer, absolute_deadline=parse(store.raw)['deadline'])
        except BaseException as primary:
            try: outer.close()
            except BaseException as cleanup: raise RoleExecutionUnresolved(primary, outer, cleanup_errors=(('outer_stage_close', cleanup),)) from primary
            raise
        store.publish('controller', 'worker/launcher.json', process)
        require(process['stage_process_observed_successfully'], 'parent role unsuccessful or unknown')
        candidate_raw = store.read_after_quiet('worker/comparison_candidate.json', outer)
        parent_raw = store.read_after_quiet('worker/parent_metrics.json', outer)
        fresh_raw = store.read_after_quiet('worker/fresh/metrics.json', outer)
        inner_raw = store.read_after_quiet('worker/fresh/launcher.json', outer)
        inner_observation_raw = store.read_after_quiet('worker/fresh_parent/parent_observation.json', outer)
        _check_role_candidates(store, outer, candidate_raw, parent_raw, fresh_raw, inner_raw, inner_observation_raw)
        core_inventory = _role_content_inventory(store, outer, include_observation=False)
        held_input, g2 = _role_input_bookend(store, 'G2', held_input); marks.append(g2)
        observation = dict(schema='staged_saved_F_final_role_observation_v1', authority='DRAFT_NONAUTHORITATIVE',
            scope=parse(store.raw)['scope'], context_sha=store.sha, candidate_pin=pin(candidate_raw),
            outer_process_sha=sha256(outer.last_image).hexdigest(), inner_process_pin=pin(inner_raw),
            inner_observation_pin=pin(inner_observation_raw), core_output_inventory_sha=digest(core_inventory),
            input_bookends_before_publication=marks,
            F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
        observation_pin = store.publish('controller', 'parent/parent_observation.json', observation)
        _, g3 = _role_input_bookend(store, 'G3', held_input); marks.append(g3)
        output_inventory = _role_content_inventory(store, outer)
        require(all(output_inventory.get(name) == expected for name, expected in core_inventory.items()), 'validated role core changed after final publication')
        _role_context(store.raw, store.sha)
        require(pin(read(store.root/'parent/parent_observation.json')) == observation_pin, 'final role observation changed')
        return dict(authority='DRAFT_NONAUTHORITATIVE', scope=parse(store.raw)['scope'], ordinary_graph_completed=True,
            observation_pin=observation_pin, input_bookends=marks, output_inventory=output_inventory, output_root=str(store.root),
            F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False, **GATES)
    except BaseException as error:
        application_reports = []
        if outer is not None and type(outer.last_image) is bytes and outer.last_observation['job_quiet_confirmed']:
            for name in ('worker/events.jsonl', 'worker/fresh/events.jsonl'):
                if not os.path.lexists(store.root/name): continue
                try:
                    reported = store.read_diagnostic_after_quiet(name, outer)
                    events = [parse(line) for line in reported.splitlines()]
                    application_reports.append(dict(path=name, pin=pin(reported), report_scope='application_reported_only',
                        event_count=len(events), last_error=_bounded_stage_error_image(events[-1].get('error'), 3)
                            if events and type(events[-1]) is dict else None))
                except BaseException as diagnostic_error:
                    application_reports.append(dict(path=name, report_scope='unavailable', error=_stage_error(diagnostic_error)))
        diagnostic = dict(schema='staged_saved_F_role_failure_v1', authority='DRAFT_NONAUTHORITATIVE',
            scope=parse(store.raw)['scope'], context_sha=store.sha, error=_stage_error(error), input_bookends=marks,
            application_reports=application_reports,
            outer_process_sha=sha256(outer.last_image).hexdigest() if outer is not None and type(outer.last_image) is bytes else None,
            observation_pin=observation_pin, F_launch_admitted=False, saved_P1_fresh_process_verified=False,
            saved_P1_parent_adoption_verified=False, **GATES)
        try: failure_pin = store.publish('controller', 'diagnostics/failure.json', diagnostic)
        except BaseException as publication_error:
            raise RoleExecutionUnresolved(error, outer, diagnostic, (('diagnostic_publication', publication_error),)) from error
        if _role_error_holds_capability(error) or _role_stage_still_open(outer):
            raise RoleExecutionUnresolved(error, outer, dict(diagnostic, failure_pin=failure_pin)) from error
        return dict(diagnostic, ordinary_graph_completed=False, failure_pin=failure_pin, output_root=str(store.root))


if __name__ == '__main__':
    raise SystemExit('Saved F role execution and trusted invocation remain draft. F launch remains disabled.')
