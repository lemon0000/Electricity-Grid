"""Non-authoritative persistence of a replayable same-policy capacity prefix.

The caller supplies the expected zero origin and a separately retained digest.
No physical snapshot is deserialized into executable state.
"""
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys

from .boundary import ContinuationHour
from .causal_policy import CurrentObservation, HourlyLimits
from .capacity_policy import (
    CapacityObservation, CapacityPolicyCursor, initialize_capacity_policy, advance_capacity_policy,
)

SCHEMA = 'rq2_continuous_verified_prefix_handoff_v1'
ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION = ('src/__init__.py', *(
    f'src/rq2_joint_deliverability_boundary_v1/{name}.py' for name in (
        '__init__', 'boundary', 'multiday', 'debt_cohorts', 'four_arm_replay',
        'causal_policy', 'actual_actions', 'aggregate_response', 'capacity_policy', 'prefix_handoff')))


def _plain(value):
    if isinstance(value, Q):
        return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        if any(type(k) is not str for k in value):
            raise ValueError('string mapping keys required')
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if value is None or type(value) in (bool, int, float, str):
        return value
    raise ValueError('unsupported handoff scalar type')


def _encoded(value):
    return (json.dumps(_plain(value), sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':'))+'\n').encode('utf-8')


def prefix_digest(data):
    if type(data) is not bytes:
        raise ValueError('handoff must be immutable bytes')
    return hashlib.sha256(data).hexdigest()


def _origin(cursor):
    if not isinstance(cursor, CapacityPolicyCursor):
        raise ValueError('typed capacity cursor required')
    track = cursor.initial.tracks[0][1]
    origin = initialize_capacity_policy(cursor.spec, anchor=track.physical.anchor,
        envelope=dict(track.physical.envelope), accounting_period_id=track.ledger.accounting_period_id,
        zero_carry_in_assumption=True)
    if cursor.initial != origin.initial or cursor.policy_id != origin.policy_id:
        raise ValueError('canonical zero origin and matching policy required')
    return origin


def _snapshot(cursor):
    return {'arm_id': cursor.arm_id, 'mode': cursor.mode, 'tracks': dict(cursor.tracks)}


def _entry(record):
    response = record.response
    action = response.action
    observation = record.current.observation
    projection = replace(observation, hour=replace(observation.hour,
        grid_request=action.grid_served, cfe_request=action.cfe_served),
        due_hour=observation.due_hour if action.grid_served+action.cfe_served else None)
    return {'original_current': record.current, 'executed_request_projection': projection,
        'declared_action': action, 'stage': record.stage, 'error': record.error,
        'response_stage': response.stage, 'response_status': response.status,
        'grid_shortfall': response.grid_shortfall, 'cfe_shortfall': response.cfe_shortfall,
        'committed': record.committed}


def _payload(cursor):
    return {
        'schema': SCHEMA, 'status': 'DRAFT_NONAUTHORITATIVE',
        'evidence_class': 'derived_mechanism_state', 'observed_carry_in': False,
        'formal_result': False, 'security_certified': False, 'completion_claim_allowed': False,
        'training_capacity_certificate': None,
        'policy_id': cursor.policy_id, 'spec': cursor.spec,
        'canonical_zero_origin': _snapshot(cursor.initial),
        'prefix_record_count': len(cursor.records),
        'records': [_entry(record) for record in cursor.records],
        'terminal_execution': _snapshot(cursor.execution),
        'implementation_sha256': {name: prefix_digest((ROOT/name).read_bytes()) for name in IMPLEMENTATION},
        'python': sys.version,
    }


def export_prefix_handoff(cursor):
    """Recheck a nonempty committed prefix and export its exact replay witness."""
    replayed = _origin(cursor)
    if not cursor.records or cursor.stopped:
        raise ValueError('nonempty fully committed prefix required')
    for record in cursor.records:
        replayed = advance_capacity_policy(replayed, record.current)
        if replayed.stopped:
            raise ValueError('prefix replay did not commit')
    if cursor != replayed:
        raise ValueError('cursor differs from full prefix replay')
    return _encoded(_payload(replayed))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('nonfinite JSON constant')


def _restore_numbers(value):
    # Only original input fields are restored. Execution state is always replayed.
    if isinstance(value, dict):
        if set(value) == {'numerator', 'denominator'}:
            n, d = value['numerator'], value['denominator']
            if type(n) is not str or type(d) is not str:
                raise ValueError('Fraction integers must be strings')
            try:
                exact = Q(int(n), int(d))
            except (ValueError, ZeroDivisionError) as error:
                raise ValueError('invalid Fraction encoding') from error
            if _plain(exact) != value:
                raise ValueError('canonical reduced Fraction required')
            return exact
        return {k: _restore_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_restore_numbers(v) for v in value]
    return value


def _current(raw):
    raw = _restore_numbers(raw)
    if set(raw) != {'observation', 'available_flexibility'}:
        raise ValueError('original current inventory mismatch')
    observation = raw['observation']
    if set(observation) != {'hour', 'limits', 'due_hour'}:
        raise ValueError('original observation inventory mismatch')
    return CapacityObservation(CurrentObservation(ContinuationHour(**observation['hour']),
        HourlyLimits(**observation['limits']), observation['due_hour']), raw['available_flexibility'])


def import_prefix_handoff(data, *, expected_sha256, expected_origin):
    """Restore the original full cursor only after pinned identity and replay checks.

    expected_origin must be an independently supplied canonical zero cursor of
    the same policy, split, trace, source offset, envelope and accounting period.
    The digest is a local integrity pin, not an authenticated source signature.
    """
    if (type(expected_sha256) is not str or len(expected_sha256) != 64
        or any(c not in '0123456789abcdef' for c in expected_sha256)
        or prefix_digest(data) != expected_sha256):
        raise ValueError('handoff digest mismatch')
    origin = _origin(expected_origin)
    if expected_origin.records or expected_origin != origin:
        raise ValueError('expected origin must have canonical zero history')
    try:
        payload = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if (type(payload) is not dict or payload.get('schema') != SCHEMA
            or type(payload.get('records')) is not list or not payload['records']):
            raise ValueError('nonempty versioned prefix required')
        # Bind the caller's expectation before processing the historical inputs.
        if (_encoded(payload.get('spec')) != _encoded(origin.spec)
            or payload.get('policy_id') != origin.policy_id
            or _encoded(payload.get('canonical_zero_origin')) != _encoded(_snapshot(origin.initial))):
            raise ValueError('expected policy or source origin mismatch')
        cursor = origin
        for record in payload['records']:
            cursor = advance_capacity_policy(cursor, _current(record['original_current']))
            if cursor.stopped:
                raise ValueError('uncommitted prefix cannot be imported')
        if _encoded(_payload(cursor)) != data:
            raise ValueError('handoff canonical replay mismatch')
    except (KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ValueError('invalid handoff input structure') from error
    return cursor


def write_prefix_handoff(cursor, path):
    """Create an explicit draft artifact; preserve any existing or partial file."""
    path = Path(path)
    if not path.name.endswith('_non_authoritative.json'):
        raise ValueError('explicit non_authoritative filename required')
    data = export_prefix_handoff(cursor)
    with path.open('xb') as stream:
        stream.write(data)
    return prefix_digest(data)


def read_prefix_handoff(path, *, expected_sha256, expected_origin):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular handoff file required')
    return import_prefix_handoff(path.read_bytes(), expected_sha256=expected_sha256,
                                 expected_origin=expected_origin)
