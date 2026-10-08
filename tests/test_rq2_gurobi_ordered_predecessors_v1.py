"""Nearest direct/licensed predecessor cannot cross successor boundaries."""
from dataclasses import fields, replace
import sqlite3

import pytest

from test_rq2_normal_task_controller_gurobi_ordered_v1 import (
    configured, task, supplied, prepared_source, bound_source, source_supplied)
import test_rq2_normal_declared_replay_gurobi_ordered_v1 as replay
import test_rq2_normal_declared_execution_gurobi_ordered_v1 as declared
import test_rq2_source_normal_execution_gurobi_ordered_v1 as source
import test_rq2_normal_archive_capture_gurobi_ordered_v1 as capture
import test_rq2_normal_task_controller_gurobi_ordered_reports_v1 as reports
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_execution_gurobi_direct as old_declared
from src.rq2_joint_deliverability_boundary_v1 import source_normal_execution_gurobi_direct as old_source
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_replay_gurobi_direct as old_replay
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_store_gurobi_direct as old_store
from src.rq2_joint_deliverability_boundary_v1 import normal_archive_capture_gurobi_direct as old_capture
from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_gurobi_licensed as old_worker
from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_gurobi_ordered as worker


def test_direct_source_pin(monkeypatch):
    case = source.supplied.__wrapped__(monkeypatch)
    assembly, declaration, report, _ = case
    kw = source.options(assembly, declaration, report)
    pin = old_source.source_execution_identity(kw['expected_binding_identity'],
        kw['expected_normal_execution_identity'], declaration, **{name: kw[name] for name in (
            'expected_assembly_identity', 'expected_pair_identity',
            'expected_source_implementation_identity', 'expected_binding_implementation_identity')})
    monkeypatch.setattr(source.api.kernel, 'run_normal_only', lambda *a, **k: pytest.fail('kernel entered'))
    with pytest.raises(ValueError):
        source.run(case, expected_source_execution_identity=pin)


def test_direct_declared_pin(supplied, monkeypatch):
    request, options = supplied
    pin = old_declared.declared_execution_identity(request,
        expected_request_identity=options['expected_request_identity'],
        expected_source_execution_identity=options['expected_source_execution_identity'])
    monkeypatch.setattr(declared.api.prepare, 'prepare_task_inputs', lambda *a, **k: pytest.fail('prepare entered'))
    with pytest.raises(ValueError, match='identity drift'):
        declared.run(supplied, expected_declared_execution_identity=pin)


def test_direct_replay_pin(tmp_path, supplied, monkeypatch):
    _, data, observed = replay.saved(tmp_path, supplied)
    replay.no_solver(monkeypatch)
    options = supplied[1]
    pin = old_replay.replay_identity(options['expected_declared_execution_identity'],
        replace(options['specification'], time_limit_seconds=5.),
        replace(options['budget'], max_seconds_per_solve=5.))
    with pytest.raises(ValueError):
        replay.run(data, supplied, observed, expected_replay_identity=pin)


@pytest.mark.parametrize('layer,old_type', [
    ('declared', 'DeclaredGurobiDirectNormalResult'),
    ('source', 'GurobiDirectSourceNormalExecutionResult'),
    ('kernel', 'GurobiDirectNormalExecutionResult')])
def test_direct_result_tags_with_consistent_hashes(tmp_path, supplied, monkeypatch, layer, old_type):
    replay.test_prior_result_type_rejected_with_consistent_hashes(
        tmp_path, supplied, monkeypatch, layer, old_type)


def test_direct_application_id(tmp_path, supplied):
    root = tmp_path/'direct_application_id_non_authoritative'
    with replay.open_store(root, supplied) as store:
        head = store.inspect().head
    with sqlite3.connect(root/'normal.sqlite3') as connection:
        connection.execute('PRAGMA application_id='+str(old_store.APPLICATION_ID))
    with pytest.raises(ValueError, match='metadata/schema/integrity'):
        replay.open_store(root, supplied, create=False, expected_head=head)


def test_direct_capture_rejects_ordered_schema(tmp_path, supplied):
    root, observed, _ = capture.empty(tmp_path, supplied)
    args = capture.request(root, supplied, observed)
    args['expected_capture_identity'] = old_capture.capture_identity(root,
        **{k:v for k,v in args.items() if k != 'expected_capture_identity'})
    with pytest.raises(ValueError):
        old_capture.capture_normal_archive(root, **args)


def test_licensed_worker_request_rejected(task):
    prior = old_worker.LicensedGurobiDirectNormalTaskRequest(**{
        field.name:getattr(task, field.name) for field in fields(task)})
    with pytest.raises(ValueError, match='typed compact normal task request'):
        worker.task_identity(prior)


def test_licensed_controller_report_tag_rejected(configured):
    reports.test_prior_stream_report_tag_rejected_with_updated_claim(
        configured, 'DeclaredGurobiDirectNormalRecordReplay')
