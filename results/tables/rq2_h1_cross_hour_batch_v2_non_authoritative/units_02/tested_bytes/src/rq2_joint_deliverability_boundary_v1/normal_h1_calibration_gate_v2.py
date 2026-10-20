"""Exact sealed-package gates for one H1 calibration attempt.

Receipts and authorization are independently pinned local records. They are not
cryptographic signatures. The caller retains those pins in the local trust root.
"""
from hashlib import sha256
import json
import os
from pathlib import Path

SCHEMA = 'h1_single_hour_calibration_sealed_package_v2'
LIMIT = 2 * 1024**2
ROOT = Path(__file__).resolve().parents[2]


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def _pin(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('independently retained SHA256 required')


def _read(path, expected):
    from . import normal_h1_full_job_v2 as job
    _pin(expected)
    path = job.process.legacy.resources.local._path(path)
    before = job.process.legacy.resources.local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if (len(raw) > LIMIT or sha256(raw).hexdigest() != expected
            or job.process.legacy.resources.local._file_identity(path) != before):
        raise ValueError('sealed calibration record drift')
    return job.collector.base.replay.old._decode(raw, LIMIT)


def _repo_path(value):
    from . import normal_h1_full_job_v2 as job
    if type(value) is not str or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('canonical repository-relative member required')
    path = job.process.legacy.resources.local._path(ROOT/value)
    if not path.is_relative_to(ROOT) or path.relative_to(ROOT).as_posix() != value:
        raise ValueError('sealed member outside canonical repository')
    return path


def required_code_members():
    # Freeze the full local Python source closure; no dynamic import omissions.
    members = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src').rglob('*.py')]
    members += ['experiments/run_rq2_normal_h1_full_job_worker_v2.py',
        'experiments/verify_rq2_normal_h1_generation_projection_v2.py',
        'experiments/prepare_rq2_normal_h1_full_job_v2.py',
        'tests/test_rq2_normal_h1_full_job_v2.py', 'tests/test_rq2_normal_h1_full_collector_v2.py',
        'tests/test_rq2_normal_h1_calibration_gate_v2.py',
        'tests/test_rq2_normal_h1_generation_projection_v2.py']
    return tuple(sorted(members))


def verify_package(outer_path, outer_sha256):
    from . import normal_h1_full_job_v2 as job
    outer = _read(outer_path, outer_sha256)
    fields = {'schema', 'state', 'request_path', 'request_sha256', 'lease_path', 'lease_sha256',
              'claim_path', 'members', 'preseal_evidence_path', 'preseal_evidence_sha256', 'inner_path', 'inner_sha256'}
    if (type(outer) is not dict or set(outer) != fields or outer['schema'] != SCHEMA
            or outer['state'] != 'SEALED_READY_FOR_INDEPENDENT_REVIEW'):
        raise ValueError('exact sealed calibration outer required')
    members = outer['members']
    if type(members) is not dict or not set(required_code_members()) <= set(members):
        raise ValueError('complete local source closure required')
    for name, expected in members.items():
        _pin(expected)
        path = _repo_path(name)
        before = path.stat()
        actual = sha256(path.read_bytes()).hexdigest()
        after = path.stat()
        if actual != expected or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('sealed member drift: '+name)
    for field in ('request', 'lease', 'preseal_evidence', 'inner'):
        if members.get(outer[field+'_path']) != outer[field+'_sha256']:
            raise ValueError('outer member binding mismatch')
    inner = _read(_repo_path(outer['inner_path']), outer['inner_sha256'])
    expected_members = {name: pin for name, pin in members.items() if name != outer['inner_path']}
    if inner != dict(schema=SCHEMA, files=expected_members, source_closure=list(required_code_members())):
        raise ValueError('independent inner manifest/closure mismatch')
    request = _read(_repo_path(outer['request_path']), outer['request_sha256'])
    work, resource, serial, limits, budget, plan = job._validate_request(request)
    if (work.hours != 1 or len(work.stage_order) != 232
            or sum(kind=='commitment' for kind, _ in work.stage_order) != 73
            or sum(kind=='generation' for kind, _ in work.stage_order) != 158
            or request['source_declaration']['split'] != 'training'):
        raise ValueError('calibration requires complete 1+73+158 training inventory')
    lease = _read(_repo_path(outer['lease_path']), outer['lease_sha256'])
    if lease != dict(schema=SCHEMA, request_sha256=outer['request_sha256'],
                     root=request['root'], claim_path=outer['claim_path'], one_shot=True):
        raise ValueError('sealed one-shot lease binding mismatch')
    _repo_path(outer['claim_path'])
    evidence = _read(_repo_path(outer['preseal_evidence_path']), outer['preseal_evidence_sha256'])
    if (evidence.get('status') != 'PRE_SEAL_AUDIT' or evidence.get('findings_closed') is not True
            or evidence.get('official_verdict') is not None):
        raise ValueError('closed non-authoritative pre-seal evidence required')
    return outer, request


GATE_FIELDS = {'outer_path', 'outer_sha256', 'review_path', 'review_sha256', 'authority_path', 'authority_sha256'}


def verify_gate(gate):
    if type(gate) is not dict or set(gate) != GATE_FIELDS:
        raise ValueError('separate exact seal/review/run-authority pins required')
    outer, request = verify_package(gate['outer_path'], gate['outer_sha256'])
    review = _read(gate['review_path'], gate['review_sha256'])
    fields = {'schema', 'outer_sha256', 'verdict', 'reviewer', 'independent_read_only', 'fresh_official_context'}
    if (type(review) is not dict or set(review) != fields or review['schema'] != SCHEMA
            or review['outer_sha256'] != gate['outer_sha256'] or review['verdict'] != 'PASS'
            or type(review['reviewer']) is not str or not review['reviewer']
            or review['independent_read_only'] is not True or review['fresh_official_context'] is not True):
        raise ValueError('independently pinned official PASS for exact outer required')
    authority = _read(gate['authority_path'], gate['authority_sha256'])
    fields = {'schema', 'outer_sha256', 'request_sha256', 'action', 'user_instruction', 'root', 'retry_authorized'}
    if (type(authority) is not dict or set(authority) != fields or authority['schema'] != SCHEMA
            or authority['outer_sha256'] != gate['outer_sha256']
            or authority['request_sha256'] != outer['request_sha256']
            or authority['action'] != 'single_hour_native_calibration_once'
            or authority['root'] != request['root'] or authority['retry_authorized'] is not False
            or type(authority['user_instruction']) is not str or not authority['user_instruction'].strip()):
        raise ValueError('separate explicit single-attempt calibration authority required')
    return outer, request


def consume(gate):
    from . import normal_h1_full_job_v2 as job
    outer, request = verify_gate(gate)
    claim = dict(schema=SCHEMA, outer_sha256=gate['outer_sha256'], request_sha256=outer['request_sha256'],
                 root=request['root'], review_sha256=gate['review_sha256'], authority_sha256=gate['authority_sha256'])
    # Immutable exclusive claim; any uncertainty permanently consumes this path.
    job._write(_repo_path(outer['claim_path']), claim)
    return request


def verify_consumed(gate):
    outer, request = verify_gate(gate)
    claim = dict(schema=SCHEMA, outer_sha256=gate['outer_sha256'], request_sha256=outer['request_sha256'],
                 root=request['root'], review_sha256=gate['review_sha256'], authority_sha256=gate['authority_sha256'])
    if _read(_repo_path(outer['claim_path']), sha256(_bytes(claim)).hexdigest()) != claim:
        raise ValueError('durable consumed calibration claim required')
    return request
