"""Original resource declaration binding; short synthetic input preparation."""
from dataclasses import replace

import pytest

from test_rq2_scale_episode_v1 import inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_episode as ep, scale_episode_replay as replay


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    return inputs(tmp_path_factory.mktemp('episode_plan'))


def test_original_declaration_recomputes(prepared):
    req, arms, hours, settings = prepared
    ep.resources.bind_plan(settings['resource_plan'], settings['budget'], req, arms, hours)


@pytest.mark.parametrize('fault', ['missing', 'extra_window', 'split', 'normal_pin', 'envelope',
                                  'serial_wall', 'role_seconds', 'parent_commit'])
def test_plan_mismatch_refused_before_owner_or_audit_root(prepared, tmp_path, fault):
    req, arms, hours, settings = prepared
    settings = dict(settings)
    plan = settings['resource_plan']
    normal, task = plan.normals[0], plan.episodes[0]
    if fault == 'missing': plan = replace(plan, episodes=())
    elif fault == 'extra_window':
        plan = replace(plan, normals=(replace(normal, source_hours=(1, 2)),),
                       episodes=(replace(task, source_hours=(1, 2)),))
    elif fault == 'split':
        plan = replace(plan, normals=(replace(normal, split='holdout'),),
                       episodes=(replace(task, split='holdout'),))
    elif fault == 'normal_pin':
        plan = replace(plan, normals=(replace(normal, input_identity='b'*64),),
                       episodes=(replace(task, normal_input_identity='b'*64),))
    elif fault == 'envelope':
        plan = replace(plan, envelopes=(plan.envelopes[0], replace(plan.envelopes[1], archive_bytes=600*1024**2)))
    elif fault == 'serial_wall':
        plan = replace(plan, serial_budget=replace(plan.serial_budget, max_total_wall_seconds=1))
    elif fault == 'role_seconds':
        plan = replace(plan, episodes=(replace(task, actual_seconds=(1, 1, 2, 1)),))
    else:
        envelope = replace(settings['budget'].envelope, max_job_commit_bytes=768*1024**2)
        settings['budget'] = replace(settings['budget'], envelope=envelope)
        plan = replace(plan, envelopes=(plan.envelopes[0], envelope))
    settings['resource_plan'] = plan
    root = tmp_path/'never_created'
    with pytest.raises(ValueError): ep.DevelopmentScaleEpisode(root, req, arms, hours, **settings)
    assert not root.exists()
    with pytest.raises(ValueError):
        replay.audit_episode(root, req, arms, hours, **settings, expected_header_sha256='0'*64,
            expected_intent_sha256s=(), expected_result_sha256s=(), expected_audit_identity=replay.implementation_identity())
    assert not root.exists()


def test_agreeing_fabricated_selector_hashes_are_rejected(prepared):
    req, arms, hours, settings = prepared
    req = replace(req, budget=replace(req.budget, resource_contract_identity='f'*64))
    arms = tuple(replace(a, budget=replace(a.budget, resource_contract_identity='f'*64)) for a in arms)
    with pytest.raises(ValueError, match='recomputed original'):
        ep.resources.bind_plan(settings['resource_plan'], settings['budget'], req, arms, hours)


@pytest.mark.parametrize('field', ['max_solver_calls', 'max_solver_seconds'])
def test_larger_ad_hoc_total_is_not_the_declared_task(prepared, field):
    req, arms, hours, settings = prepared
    budget = replace(settings['budget'], **{field: getattr(settings['budget'], field)+1})
    with pytest.raises(ValueError, match='episode total'):
        ep.resources.bind_plan(settings['resource_plan'], budget, req, arms, hours)


@pytest.mark.parametrize('field', ['commit_reserve_bytes', 'disk_reserve_bytes'])
def test_global_reserve_cannot_understate_runtime_requirement(prepared, tmp_path, field):
    req, arms, hours, settings = prepared
    plan = settings['resource_plan']
    plan = replace(plan, serial_budget=replace(plan.serial_budget,
        **{field: getattr(settings['budget'], field)-1}))
    settings = dict(settings, resource_plan=plan)
    root = tmp_path/'never_created'
    with pytest.raises(ValueError, match='serial reserves'):
        ep.DevelopmentScaleEpisode(root, req, arms, hours, **settings)
    with pytest.raises(ValueError, match='serial reserves'):
        replay.audit_episode(root, req, arms, hours, **settings, expected_header_sha256='0'*64,
            expected_intent_sha256s=(), expected_result_sha256s=(), expected_audit_identity=replay.implementation_identity())
    assert not root.exists()
