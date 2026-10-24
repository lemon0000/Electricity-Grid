"""Draft saved-P1 F protocol; pre-import validation uses only the stdlib."""
from hashlib import sha256
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import stat
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


if __name__ == '__main__':
    raise SystemExit('Saved F protocol helpers are draft; stage supervision and trusted invocation are not implemented. F launch remains disabled.')
