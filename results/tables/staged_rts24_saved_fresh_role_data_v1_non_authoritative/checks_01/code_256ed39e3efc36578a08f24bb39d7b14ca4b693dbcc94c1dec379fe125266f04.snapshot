"""Draft bounded parent record and final storage accounting; no launcher."""
from hashlib import sha256
import json
import math
import os
from pathlib import Path

from src import staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_p2_outer_observation_v1 as old
from src.staged_rts24_process_guard_v3 import (
    MAX_MEMBER_HANDLES, TERMINAL_RECORD_BYTES, PARENT_RECORD_BYTES, RESERVED_BYTES, RESERVED_FILES, record_image, error_details, bounded_error,
)

CAPS = old.CAPS
U32, U64 = 2**32-1, 2**64-1
PARTIAL_WITNESS = {'observed_unique_member_handles', 'all_handles_signaled', 'member_identities'}
FULL_WITNESS = PARTIAL_WITNESS | {'active_processes', 'complete_inventory', 'final_pids', 'total_processes'}
require = old.require


class OuterObservationUnresolved(OSError):
    def __init__(self, phase, expected_sha, may_have_published, cause):
        super().__init__(phase+': '+bounded_error(cause))
        self.phase, self.expected_sha, self.may_have_published = phase, expected_sha, may_have_published
        self.publication_outcome = 'unknown' if may_have_published else 'not_published'
        self.scientific_evidence_adopted = False
        self.worker_terminal_status = 'not_independently_replayed'


def uint(value, maximum=U64, minimum=0):
    return type(value) is int and minimum <= value <= maximum


def canonical_context(value):
    require(type(value) is dict and set(value) == old.CONTEXT_KEYS | {
        'terminal_record_cap_bytes', 'parent_record_cap_bytes', 'terminal_reserved_files', 'parent_reserved_files', 'max_member_handles'},
        'closed bounded development context required')
    require(value['schema'] == 'staged_rts24_P2_parent_observation_development_v2', 'context schema differs')
    require(type(value['terminal_record_cap_bytes']) is int and value['terminal_record_cap_bytes'] == TERMINAL_RECORD_BYTES
        and type(value['max_member_handles']) is int and value['max_member_handles'] == MAX_MEMBER_HANDLES, 'fixed terminal budget differs')
    for key, expected in dict(parent_record_cap_bytes=PARENT_RECORD_BYTES, terminal_reserved_files=1, parent_reserved_files=1).items():
        require(type(value[key]) is int and value[key] == expected, 'fixed independent parent budget differs')
    prior = {k: value[k] for k in old.CONTEXT_KEYS}
    prior['schema'] = 'staged_rts24_P2_parent_observation_development_v1'
    old.canonical_context(prior)
    return codec.canonical(value)


def process_snapshot(record):
    """Validate finite field domains before encoding; never trim member evidence."""
    require(type(record) is dict and set(record) == old.PROCESS_KEYS | {
        'parent_reserved_bytes', 'parent_reserved_files', 'terminal_reserved_files', 'member_handle_cap'}, 'closed supervisor record required')
    require(record['exit_code'] is None or uint(record['exit_code'], U32), 'invalid exit code')
    for name in ('stop_reason', 'monitor_error', 'cleanup_error'):
        require(record[name] is None or type(record[name]) is str and len(record[name]) <= 514, 'process error text exceeds bound')
    require(type(record['job_quiet_confirmed']) is bool and type(record['rss_observation_available']) is bool, 'invalid process flags')
    wall = record['outer_seconds']
    require(type(wall) is float and math.isfinite(wall) and wall >= 0, 'invalid wall observation')
    for name in ('samples', 'peak_job_commit_bytes', 'terminal_bytes', 'terminal_files', 'terminal_reserved_bytes'):
        require(uint(record[name]), 'invalid process counter')
    require(record['terminal_reserved_bytes'] == TERMINAL_RECORD_BYTES, 'bounded record reserve differs')
    for key, value in dict(parent_reserved_bytes=PARENT_RECORD_BYTES, parent_reserved_files=1,
            terminal_reserved_files=1, member_handle_cap=MAX_MEMBER_HANDLES).items():
        require(type(record[key]) is int and record[key] == value, 'fixed parent/launcher budget differs')
    require(record['sampled_tree_peak_rss_bytes'] is None or uint(record['sampled_tree_peak_rss_bytes']), 'invalid RSS observation')
    owner = record['owner_pid'], record['owner_creation_filetime']
    require(owner == (None, None) or uint(owner[0], U32, 1) and uint(owner[1], U64, 1), 'invalid owner identity')
    w = record['quiescence_witness']
    if w is not None:
        require(type(w) is dict and set(w) in (PARTIAL_WITNESS, FULL_WITNESS), 'closed complete or partial witness required')
        require(type(w['all_handles_signaled']) is bool and uint(w['observed_unique_member_handles'], U32), 'invalid witness counters')
        members = w['member_identities']
        require(type(members) is list and len(members) <= MAX_MEMBER_HANDLES, 'retained member HANDLE cap')
        for m in members:
            require(type(m) is dict and set(m) == {'pid', 'creation_filetime'} and uint(m['pid'], U32, 1)
                and uint(m['creation_filetime'], U64, 1), 'invalid retained member identity')
        require(len({(m['pid'], m['creation_filetime']) for m in members}) == len(members), 'duplicate retained identity')
        if set(w) == FULL_WITNESS:
            require(type(w['complete_inventory']) is bool and uint(w['active_processes'], U32) and uint(w['total_processes'], U32), 'invalid full witness')
            require(type(w['final_pids']) is list and len(w['final_pids']) <= MAX_MEMBER_HANDLES
                and all(uint(pid, U32, 1) for pid in w['final_pids']), 'invalid final PID inventory')
    return json.loads(codec.canonical(record))


def assess_process(record, limits):
    snapshot = process_snapshot(record)
    w = snapshot['quiescence_witness']
    quiet = False
    if w is not None and set(w) == FULL_WITNESS:
        identities = {(m['pid'], m['creation_filetime']) for m in w['member_identities']}
        quiet = (snapshot['job_quiet_confirmed'] and snapshot['cleanup_error'] is None and w['active_processes'] == 0
            and not w['final_pids'] and w['all_handles_signaled'] and w['complete_inventory']
            and 1 <= w['total_processes'] <= MAX_MEMBER_HANDLES
            and w['total_processes'] == w['observed_unique_member_handles'] == len(identities)
            and (snapshot['owner_pid'], snapshot['owner_creation_filetime']) in identities)
    exit_ok = snapshot['exit_code'] == 0 and all(snapshot[n] is None for n in ('stop_reason', 'monitor_error', 'cleanup_error'))
    caps_ok = (snapshot['outer_seconds'] <= limits['wall_seconds'] and snapshot['terminal_files']+RESERVED_FILES <= limits['files']
        and snapshot['terminal_bytes']+RESERVED_BYTES <= limits['output_bytes']
        and snapshot['peak_job_commit_bytes'] <= 2*1024**3 and snapshot['rss_observation_available']
        and snapshot['samples'] > 0 and uint(snapshot['sampled_tree_peak_rss_bytes'])
        and snapshot['sampled_tree_peak_rss_bytes'] <= limits['rss_bytes'])
    return dict(execution_status='successful_exit' if exit_ok else 'failed_or_unknown',
        ownership_status='quiet_verified' if quiet else 'unknown', proposal_caps_satisfied=bool(caps_ok),
        inspection_permitted=bool(quiet and exit_ok and caps_ok), process_snapshot=snapshot)


def worker_accounting(worker, limits):
    """Complete bounded metadata count, including over-budget files; no prefix totals."""
    directories = codec.directory_identity(worker)
    counts = [0, 0, 0]
    files, tree = {}, {}
    def identity(info): return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
    def file_stamp(path):
        before = codec.ordinary(path)
        with path.open('rb') as stream:
            require(identity(os.fstat(stream.fileno())) == identity(before), 'worker file changed before accounting')
            require(identity(os.fstat(stream.fileno())) == identity(before), 'worker file changed during accounting')
        require(identity(codec.ordinary(path)) == identity(before), 'worker file changed after accounting')
        return identity(before)
    def children_of(path, initial=False):
        children = set()
        for child in path.iterdir():
            require(len(children) < 16384, 'worker accounting directory entry cap')
            if initial:
                counts[2] += 1
                require(counts[2] <= 16384, 'worker accounting entry cap')
            children.add(child)
        return children
    def visit(path, depth):
        require(depth <= 12, 'worker accounting depth cap')
        before = codec.directory_identity(path)
        children = children_of(path, initial=True)
        tree[path] = before, children
        for child in children:
            info = child.lstat()
            if child.is_dir():
                codec.ordinary(child, directory=True)
                visit(child, depth+1)
            else:
                files[child] = file_stamp(child)
                counts[0] += files[child][2]
                counts[1] += 1
                require(counts[0] <= U64, 'worker accounting byte domain')
        require(codec.directory_identity(path) == before, 'worker accounting directory changed')
    visit(worker, 0)
    for path, expected in files.items(): require(file_stamp(path) == expected, 'worker file accounting bookend differs')
    for path, (expected, children) in tree.items():
        require(codec.directory_identity(path) == expected and children_of(path) == children, 'worker accounting inventory changed')
    require(codec.directory_identity(worker) == directories, 'worker root accounting changed')
    return counts[0], counts[1]


def encode_observation(observation):
    raw = codec.canonical(observation)
    require(len(raw) <= PARENT_RECORD_BYTES, 'parent record exceeds 128 KiB')
    return raw


def save_observation(parent_root, context_bytes, expected_context_sha, process_record, inspect_after_quiet, hook=None):
    require(type(context_bytes) is bytes and sha256(context_bytes).hexdigest() == expected_context_sha, 'held context SHA differs')
    context = codec.parse(context_bytes)
    require(canonical_context(context) == context_bytes, 'held context is not canonical')
    parent, worker = Path(parent_root).absolute(), Path(context['worker_root'])
    require(str(parent) == context['parent_root'], 'parent path differs from held context')
    assessment = assess_process(process_record, context['limits'])
    snapshot = assessment['process_snapshot']
    directories = codec.directory_identity(parent)
    require(not list(parent.iterdir()), 'dedicated parent directory must be empty')
    target = parent/'parent_observation.json'
    claims = error = accounting_error = None
    inspection, worker_counts, worker_identity = 'skipped', None, None
    def worker_bookend():
        require(codec.directory_identity(worker) == worker_identity, 'held worker directory changed')
        require(codec.read_bytes(worker/'launcher.json') == record_image(snapshot), 'launcher process bytes changed')
    if assessment['ownership_status'] == 'quiet_verified':
        try:
            require(not worker.resolve().is_relative_to(parent.resolve()) and not parent.resolve().is_relative_to(worker.resolve()), 'physical worker and parent roots overlap')
            worker_identity = codec.directory_identity(worker)
            worker_bookend()
            worker_counts = worker_accounting(worker, context['limits'])
            require(worker_counts == (snapshot['terminal_bytes']+len(record_image(snapshot)), snapshot['terminal_files']+1), 'worker accounting differs from supervisor')
            worker_bookend()
        except Exception as exc:
            worker_counts = None
            accounting_error = error_details(exc)
    if assessment['inspection_permitted'] and worker_counts is not None:
        try:
            claims = old.mechanical_claims(inspect_after_quiet(worker))
            worker_bookend()
            require(worker_accounting(worker, context['limits']) == worker_counts, 'worker accounting changed during inspection')
            worker_bookend()
            inspection = 'returned'
        except Exception as exc:
            claims = None
            inspection = 'failed'
            error = error_details(exc)
    require(codec.directory_identity(parent) == directories and not list(parent.iterdir()), 'parent directory changed during inspection')
    observation = dict(authority='DRAFT_NONAUTHORITATIVE', scope='bounded parent process and caller-supplied mechanical observation only',
        context_sha=expected_context_sha, **assessment, inspection_status=inspection, inspection_error=error,
        accounting_error=accounting_error, worker_accounting_at_entry_verified=worker_counts is not None,
        terminal_record_cap_bytes=TERMINAL_RECORD_BYTES, max_member_handles=MAX_MEMBER_HANDLES,
        caller_supplied_mechanical_claims=claims, worker_terminal_status='not_independently_replayed',
        source_freshness_independently_verified=False, scientific_audit_replayed=False, scientific_evidence_adopted=False,
        full_139_independently_verified=False, fx_temporal_backing=False, resource_admission=False, formal_result=False)
    raw = encode_observation(observation)
    expected = sha256(raw).hexdigest()
    def safe_hook(stage, path):
        if hook is not None:
            try: hook(stage, path)
            except Exception as exc: raise OSError(bounded_error(exc)) from exc
    try:
        if worker_counts is not None: worker_bookend()
        actual = codec.publish(target, raw, safe_hook)
        require(actual == expected and codec.read_bytes(target) == raw and codec.directory_identity(parent) == directories,
            'parent record post-publication readback differs')
        require(set(parent.iterdir()) == {target}, 'parent final inventory differs')
        totals = None
        if worker_counts is not None:
            worker_bookend()
            require(worker_accounting(worker, context['limits']) == worker_counts, 'worker accounting changed after publication')
            worker_bookend()
            totals = dict(bytes=worker_counts[0]+len(raw), files=worker_counts[1]+1)
            totals['within_limits'] = totals['bytes'] <= context['limits']['output_bytes'] and totals['files'] <= context['limits']['files']
        require(codec.read_bytes(target) == raw and codec.directory_identity(parent) == directories and set(parent.iterdir()) == {target},
            'parent final accounting bookend differs')
    except codec.PublicationError as exc:
        raise OuterObservationUnresolved(exc.phase, expected, exc.may_have_published, exc) from exc
    except Exception as exc:
        raise OuterObservationUnresolved('parent_record_bookend', expected, os.path.lexists(target), exc) from exc
    return dict(parent_record_sha=expected, parent_record_saved=True, parent_record_bytes=len(raw), observation=observation,
        final_storage_accounting=totals, scientific_evidence_adopted=False, resource_admission=False, formal_result=False)
