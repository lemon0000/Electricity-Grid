"""Pure inverse projection against saved v2 bytes, not a current prepare proof."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest
from experiments import h1_group_n0_common_input_binding_development_v4 as m


@pytest.fixture
def report():
    path = Path('D:/h1_chain_06_non_authoritative/nt_non_authoritative/common_owners_non_authoritative/'
        '832eca33537d21d5cadf5015e38584b4eb01150e0ce2229cb8df394236bd43cf_non_authoritative/header.json')
    old = json.loads(path.read_bytes())['declaration']['initial_report']
    expected = m.encode(old)
    assert len(expected) == 112807
    assert sha256(expected).hexdigest() == 'a2a55c6b96fd6ed72b579b027ca926f82db3e7173b23e29588dbba5106e53488'
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
                payload_sha256=sha256(m.encode(old_exact)).hexdigest(), payload=old_exact))
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
