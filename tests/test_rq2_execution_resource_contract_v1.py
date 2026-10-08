from dataclasses import replace

import pytest

from src.rq2_joint_deliverability_boundary_v1.execution_workload import NormalWork, EpisodeWork
from src.rq2_joint_deliverability_boundary_v1.execution_resource_contract import (
    TaskEnvelope, SerialResourceBudget, check_resource_contract)


def example():
    uids, hours = tuple(f'g{i:03}' for i in range(158)), tuple(range(25))
    normals = (NormalWork('n', 'training', 'a'*64, uids, hours, 15),)
    episodes = (EpisodeWork('e', 'training', 'n', 'a'*64, uids, hours, 1, (1, 1, 1, 1)),)
    envelopes = (TaskEnvelope('n', 100, 85, 800, 100, 50, 1, 22275, 28004),
                 TaskEnvelope('e', 20000, 100, 900, 1000, 500, 1, 2000, 3000))
    budget = SerialResourceBudget(20110, 10, 50, 50, 1000, 100, 1750, 1)
    return normals, episodes, envelopes, budget


def test_full_h25_declaration_without_old_short_caps_or_execution_authority():
    report = check_resource_contract(*example())
    assert report['declaration_consistent']
    assert report['workload']['solver_calls'] == 19901
    assert report['reserved_total_wall_seconds'] == 20110
    assert report['required_additional_commit_bytes'] == 1000  # max jobs, not sum
    assert report['required_additional_disk_bytes'] == 1750  # keep all scratch
    assert not report['whole_task_resources_verified']
    assert not report['execution_authorized'] and not report['formal_ready']
    assert 'envelope_measurements' in report['unresolved']


@pytest.mark.parametrize('field,error', [
    ('max_total_wall_seconds', 'total_wall_reservation_shortfall'),
    ('max_additional_commit_bytes', 'commit_reservation_shortfall'),
    ('max_additional_disk_bytes', 'disk_reservation_shortfall'),
])
def test_one_unit_resource_shortfall_is_not_consistent(field, error):
    normals, episodes, envelopes, budget = example()
    budget = replace(budget, **{field: getattr(budget, field)-1})
    report = check_resource_contract(normals, episodes, envelopes, budget)
    assert report['errors'] == (('serial_plan', error),)
    assert not report['declaration_consistent']


def test_task_time_allowance_and_threads_cannot_hide_in_total_budget():
    normals, episodes, envelopes, budget = example()
    envelopes = (replace(envelopes[0], max_wall_seconds=99, max_threads=2), envelopes[1])
    report = check_resource_contract(normals, episodes, envelopes, budget)
    assert report['errors'] == (('n', 'task_wall_reservation_shortfall'), ('n', 'thread_cap_exceeds_plan'))


@pytest.mark.parametrize('changed', ['missing', 'extra', 'duplicate'])
def test_task_envelope_inventory_must_match(changed):
    normals, episodes, envelopes, budget = example()
    if changed == 'missing':
        envelopes = envelopes[:1]
    elif changed == 'extra':
        envelopes += (replace(envelopes[0], task_id='unknown'),)
    else:
        envelopes += envelopes[:1]
    with pytest.raises(ValueError):
        check_resource_contract(normals, episodes, envelopes, budget)


@pytest.mark.parametrize('bad', [None, 0, -1, True, float('inf'), 1.5])
def test_missing_or_invalid_resource_is_rejected(bad):
    normals, episodes, envelopes, budget = example()
    with pytest.raises(ValueError):
        check_resource_contract(normals, episodes,
                                (replace(envelopes[0], archive_bytes=bad), envelopes[1]), budget)
    with pytest.raises(ValueError):
        check_resource_contract(normals, episodes, envelopes,
                                replace(budget, supervisor_additional_commit_bytes=bad))


def test_complete_declarations_are_retained_and_reconstructable():
    normals, episodes, envelopes, budget = example()
    report = check_resource_contract(normals, episodes, envelopes, budget)
    again = check_resource_contract(
        tuple(NormalWork(**x) for x in report['workload']['normal_declarations']),
        tuple(EpisodeWork(**x) for x in report['workload']['episode_declarations']),
        tuple(TaskEnvelope(**x) for x in report['envelopes']), SerialResourceBudget(**report['budget']))
    assert again == report
    changed = check_resource_contract(normals, episodes,
                                     (replace(envelopes[0], max_variables=22276), envelopes[1]), budget)
    assert changed != report


def test_source_split_mismatch_rejected_before_resource_check():
    normals, episodes, envelopes, budget = example()
    with pytest.raises(ValueError, match='split'):
        check_resource_contract(normals, (replace(episodes[0], split='holdout'),), envelopes, budget)
