from dataclasses import asdict

import pytest

from test_rq2_normal_task_controller_gurobi_licensed_v1 import configured
from test_rq2_normal_task_worker_gurobi_licensed_v1 import task, supplied, prepared_source, bound_source, source_supplied
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_gurobi_licensed as api
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_gurobi_direct as old


def test_license_path_changes_outer_identity_and_preserves_inner_request(tmp_path, configured):
    request, budget, env = configured
    root = tmp_path/'task_non_authoritative'
    changed = dict(env)
    alternative = tmp_path/'synthetic.lic'
    alternative.write_text('synthetic path only', encoding='ascii')
    changed['GRB_LICENSE_FILE'] = str(alternative)
    assert api.controller_identity(root, request, budget, env) != api.controller_identity(root, request, budget, changed)
    assert asdict(request) == asdict(old.worker.decode_request(asdict(request)))


def test_old_request_and_old_worker_route_cannot_authorize_successor(tmp_path, configured):
    request, budget, env = configured
    root = tmp_path/'task_non_authoritative'
    predecessor = old.worker.decode_request(asdict(request))
    with pytest.raises(ValueError): api.controller_identity(root, predecessor, budget, env)
    assert api.worker.task_identity(request) != old.worker.task_identity(predecessor)
    argv = api.worker.worker_argv(tmp_path/'packet.json', '0'*64)
    old_argv = old.worker.worker_argv(tmp_path/'packet.json', '0'*64)
    assert argv != old_argv
    assert 'normal_task_worker_gurobi_licensed' in argv[4]
