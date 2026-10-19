"""Pure inverse projection against saved v2 bytes, not a current prepare proof."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest
from experiments import h1_group_n0_common_input_binding_development_v4 as m


@pytest.fixture
def report():
    path = Path(__file__).resolve().parents[1] / ('results/tables/'
        'rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/'
        'common_v2_report_oracle_01_non_authoritative/initial_report.json')
    raw = path.read_bytes()
    old = json.loads(raw)
    expected = m.encode(old)
    assert raw == expected and len(expected) == 115311
    assert sha256(expected).hexdigest() == 'a23f37589d049cdba62959cd4cb0546d50079174ae9e6973fa99e35eacf26798'
    first = next(iter(old['arm_audits'].values()))['exact_current_audit']
    identities = dict(common_identity='c'*64, source_identity='d'*64,
        predecessor_identity=old['implementation'], predecessor_source_identity=first['implementation_identity'])
    current = deepcopy(old)
    current.update(schema=m.SCHEMA, implementation=identities['common_identity'])
    for audit in current['arm_audits'].values():
        old_exact = audit['exact_current_audit']
        projected = {key: value for key, value in old_exact.items() if key not in m.source._EXECUTION_FIELDS}
        projected.update(schema=m.source.SCHEMA, implementation_identity=identities['source_identity'],
            predecessor_compatibility=dict(compatibility_payload_scope='predecessor_projection_metadata_only',
                compatibility_counts_describe_actual_execution=False, schema=m.source.predecessor.SCHEMA,
                implementation_identity=identities['predecessor_source_identity'],
                payload_sha256=sha256(m.source.io.encode(old_exact)).hexdigest(), payload=old_exact))
        audit['exact_current_audit'] = projected
        del audit['verification_execution']
    return current, identities, expected


def test_pure_projection_rebuilds_every_saved_v2_report_byte(report):
    current, identities, expected = report
    assert m._compatibility_report(current, **identities) == expected


@pytest.mark.parametrize('fault', ['payload', 'compatibility_hash', 'historical', 'old_identity',
    'current_identity', 'common_identity', 'scope', 'actual_count_claim', 'extra_arm_field'])
def test_changed_compatibility_or_historical_projection_rejected(report, fault):
    current, identities, _ = report
    audit = next(iter(current['arm_audits'].values()))
    exact = audit['exact_current_audit']
    compatibility = exact['predecessor_compatibility']
    if fault == 'payload':
        compatibility['payload']['unit_corruption'] = True
    elif fault == 'compatibility_hash':
        compatibility['payload_sha256'] = 'f'*64
    elif fault == 'historical':
        audit['historical_audit']['unit_corruption'] = True
    elif fault == 'old_identity':
        compatibility['payload']['implementation_identity'] = 'f'*64
    elif fault == 'current_identity':
        exact['implementation_identity'] = 'f'*64
    elif fault == 'common_identity':
        current['implementation'] = 'f'*64
    elif fault == 'scope':
        compatibility['compatibility_payload_scope'] = 'execution'
    elif fault == 'actual_count_claim':
        compatibility['compatibility_counts_describe_actual_execution'] = True
    else:
        audit['unit_corruption'] = True
    with pytest.raises(ValueError):
        m._compatibility_report(current, **identities)
