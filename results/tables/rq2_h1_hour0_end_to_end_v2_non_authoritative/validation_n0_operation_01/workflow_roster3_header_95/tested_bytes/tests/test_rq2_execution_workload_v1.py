from dataclasses import replace
from types import SimpleNamespace

import pytest

from src.rq2_joint_deliverability_boundary_v1.execution_workload import (
    NormalWork, EpisodeWork, summarize_workload)
from src.rq2_joint_deliverability_boundary_v1.episode_coordinator import _requirements


def tasks(n=158, h=25):
    uids = tuple(f'g{i:03}' for i in range(n))
    hours = tuple(range(h))
    normal = NormalWork('normal', 'training', 'a'*64, uids, hours, 15)
    episode = EpisodeWork('episode', 'training', 'normal', 'a'*64, uids, hours, 1, (1, 2, 3, 4))
    return normal, episode


def test_matches_existing_episode_reservation_and_explicit_stage_enumeration():
    normal, episode = tasks()
    report = summarize_workload((normal,), (episode,))
    spec = SimpleNamespace(time_limit_seconds=episode.reference_seconds)
    arms = tuple(SimpleNamespace(solver_specification=SimpleNamespace(time_limit_seconds=s))
                 for s in episode.actual_seconds)
    calls, seconds = _requirements(158, arms, spec)
    stage_limits = [normal.seconds_per_solve]
    for _ in episode.source_hours:
        stage_limits.extend([episode.reference_seconds]*(2+len(episode.generator_uids)))
        for limit in episode.actual_seconds:
            stage_limits.extend([limit]*(1+len(episode.generator_uids)))
    assert report['solver_calls'] == calls*25+1 == len(stage_limits) == 19901
    assert report['reserved_solver_seconds'] == seconds*25+15 == sum(stage_limits)
    assert not report['formal_ready'] and not report['execution_authorized']


def test_shared_normal_counted_once_but_each_capacity_evaluation_counted():
    normal, episode = tasks(2, 3)
    report = summarize_workload((normal,), (episode, replace(episode, task_id='capacity-2')))
    assert report['normal_tasks'] == 1
    assert report['episode_tasks'] == 2
    assert report['solver_calls'] == 1+2*3*(4+4*3)
    assert 'source_and_reuse_validation' in report['unresolved']


@pytest.mark.parametrize('changes', [
    {'normal_task_id': 'absent'}, {'split': 'holdout'}, {'normal_input_identity': 'b'*64},
    {'generator_uids': ('different',)}, {'source_hours': (25,)}, {'source_hours': (0, 2)},
    {'source_hours': (True,)}, {'reference_seconds': 0}, {'reference_seconds': True},
    {'reference_seconds': 1.5}, {'actual_seconds': (1, 1, 1)},
    {'actual_seconds': (1, 1, 1, -1)}, {'task_id': 'normal'},
])
def test_rejects_missing_or_mismatched_dependencies_and_budgets(changes):
    normal, episode = tasks()
    with pytest.raises(ValueError):
        summarize_workload((normal,), (replace(episode, **changes),))


def test_no_implicit_tasks_or_deduplication():
    normal, episode = tasks()
    for normals, episodes in (((normal,), ()), ((normal,), (episode, episode)),
                              ((normal, replace(normal, task_id='unused')), (episode,))):
        with pytest.raises(ValueError):
            summarize_workload(normals, episodes)


def test_distinct_training_and_holdout_normals_both_charged():
    normal, episode = tasks(1, 1)
    other_normal = replace(normal, task_id='holdout-normal', split='holdout', input_identity='b'*64)
    other_episode = replace(episode, task_id='holdout-episode', split='holdout',
                            normal_task_id=other_normal.task_id, normal_input_identity='b'*64)
    report = summarize_workload((normal, other_normal), (episode, other_episode))
    assert report['solver_calls'] == 2*(1+3+4*2)
    assert report['normal_tasks'] == report['episode_tasks'] == 2


@pytest.mark.parametrize('changes', [
    {'generator_uids': ()}, {'generator_uids': ('a', 'a')},
    {'generator_uids': ('b', 'a')}, {'source_hours': ()},
    {'input_identity': 'A'*64}, {'seconds_per_solve': False}, {'split': 'unknown'},
])
def test_normal_declarations_are_validated(changes):
    normal, episode = tasks()
    with pytest.raises(ValueError):
        summarize_workload((replace(normal, **changes),), (episode,))


def test_contiguous_subwindow_is_counted_at_its_own_length():
    normal, episode = tasks(2, 25)
    report = summarize_workload((normal,), (replace(episode, source_hours=(10, 11)),))
    assert report['solver_calls'] == 1+2*(4+4*3)
    assert report['rows'][1]['reference_calls'] == 8


def test_report_retains_distinct_same_size_inputs_and_arm_budget_attribution():
    normal, episode = tasks(2, 2)
    first = summarize_workload((normal,), (episode,))
    other_normal = replace(normal, input_identity='b'*64, generator_uids=('x', 'y'), source_hours=(10, 11))
    other_episode = replace(episode, normal_input_identity='b'*64, generator_uids=('x', 'y'),
                            source_hours=(10, 11), actual_seconds=(4, 3, 2, 1))
    second = summarize_workload((other_normal,), (other_episode,))
    assert first['rows'] == second['rows']
    assert first != second
    replay = summarize_workload(tuple(NormalWork(**row) for row in second['normal_declarations']),
                                tuple(EpisodeWork(**row) for row in second['episode_declarations']))
    assert replay == second
    assert second['episode_declarations'][0]['actual_seconds'] == (4, 3, 2, 1)
