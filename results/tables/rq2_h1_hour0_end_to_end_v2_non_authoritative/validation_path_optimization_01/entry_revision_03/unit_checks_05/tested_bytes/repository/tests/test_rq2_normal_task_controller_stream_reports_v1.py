"""Three-layer report consistency, using synthetic wire only."""
from types import SimpleNamespace

import pytest

from test_rq2_normal_task_controller_stream_v1 import (
    api, configured, task, supplied, prepared_source, bound_source, source_supplied,
    diagnostic_wire, source_diagnostic_wire, encode_report, report_claim)


def check(task, values):
    raw = encode_report(values)
    return api._report(raw, SimpleNamespace(record_sha256='1'*64, claimed_result_identity='2'*64),
        task, report_claim(values, raw))


@pytest.mark.parametrize('fault', ['identity', 'authority', 'calls_bool', 'consistent_int',
    'missing_source', 'source_type', 'source_inventory', 'source_error_type', 'source_identity',
    'assignment', 'witness', 'error_projection', 'status', 'acceptance', 'outer_extra', 'legacy_tag'])
def test_outer_report_faults_rejected(configured, fault):
    task = configured[0]
    values = diagnostic_wire(task)
    if fault == 'identity': values['replay_identity'] = '0'*64
    if fault == 'authority': values['formal_result'] = True
    if fault == 'calls_bool': values['solver_calls_by_replay'] = False
    if fault == 'consistent_int': values['archive_consistent'] = 1
    if fault == 'missing_source': values['source_replay_json'] = None
    if fault == 'source_type': values['source_replay_json'] = 1
    if fault == 'assignment': values['assignment_recomputed'] = False
    if fault == 'witness': values['normal_witness_reproduced'] = False
    if fault == 'error_projection': values['errors'] = ('source:fabricated',)
    if fault == 'status': values['status'] = 'replayed_accepted_normal_record'
    if fault == 'acceptance': values['accepted_record_reproduced'] = False
    if fault in ('source_inventory', 'source_error_type', 'source_identity'):
        nested = api.journal._decoded(values['source_replay_json'].encode())
        if fault == 'source_inventory': nested['extra'] = False
        if fault == 'source_error_type': nested['errors'] = 'not an array'
        if fault == 'source_identity': nested['record_sha256'] = '0'*64
        values['source_replay_json'] = api.journal._bytes(nested).decode()
    raw = encode_report(values)
    if fault in ('outer_extra', 'legacy_tag'):
        wire = api.journal._decoded(raw)
        if fault == 'outer_extra': wire[1].append(['extra', False])
        else: wire[0] = 'NormalRecordReplay'
        raw = api.journal._bytes(wire)
    with pytest.raises(ValueError):
        api._report(raw, SimpleNamespace(record_sha256='1'*64, claimed_result_identity='2'*64),
            task, report_claim(values, raw))


def test_successful_source_with_declared_post_failure_stays_unresolved(configured):
    task = configured[0]
    values = diagnostic_wire(task, 'unresolved', source=source_diagnostic_wire(task))
    result = check(task, values)
    assert result['archive_consistent'] and not result['accepted_record_reproduced']
    assert result['status'] == 'replayed_unresolved_declared_normal_record'


def test_absent_source_retains_unresolved_state(configured):
    task = configured[0]
    values = diagnostic_wire(task, 'unresolved')
    values.update(source_replay_json=None, assignment_recomputed=False, normal_witness_reproduced=False)
    result = check(task, values)
    assert result['archive_consistent'] and not result['accepted_record_reproduced']


def test_source_errors_cannot_be_hidden_by_outer_unresolved(configured):
    task = configured[0]
    values = diagnostic_wire(task, 'unresolved', source=source_diagnostic_wire(task, 'inconsistent'))
    with pytest.raises(ValueError, match='error projection'): check(task, values)


@pytest.mark.parametrize('fault', ['outer_unknown', 'source_unknown', 'duplicate', 'native_projection'])
def test_fabricated_replay_errors_rejected(configured, fault):
    task = configured[0]
    source = source_diagnostic_wire(task, 'unresolved')
    if fault == 'native_projection':
        native = api.journal._decoded(source['native_replay_json'].encode())
        native.update(replay_errors=['native_bound_projection_mismatch'], replay_consistent=False)
        source['native_replay_json'] = api.journal._bytes(native).decode()
        values = diagnostic_wire(task, 'unresolved', source=source)
    else:
        values = diagnostic_wire(task, 'unresolved', source=source)
        errors = ('invented_error',) if fault != 'duplicate' else ('normal_witness_mismatch',)*2
        if fault != 'outer_unknown':
            source.update(errors=errors, archive_consistent=False, status='inconsistent_normal_record')
            values['source_replay_json'] = api.journal._bytes(source).decode()
            errors = tuple('source:'+x for x in errors)
        values.update(errors=errors, archive_consistent=False, status='inconsistent_declared_normal_record')
    with pytest.raises(ValueError): check(task, values)
