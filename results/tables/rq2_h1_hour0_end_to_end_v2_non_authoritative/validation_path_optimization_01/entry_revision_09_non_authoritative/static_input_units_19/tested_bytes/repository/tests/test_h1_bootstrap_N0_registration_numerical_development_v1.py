"""Real synthetic N0 Job through local/global terminal registration; no native solver."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import m, example, setup, enable_post_claim, retained
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports, saved
from tests.test_h1_timed_job_controller_development_v1 import install_launcher
from experiments import h1_phase_historical_controller_development_v1 as history

owned = m.owned
CURRENT = owned.binding.source_binding.load_pinned_current
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='bounded synthetic Windows Job')


@pytest.fixture
def numerical(setup, environment, synthetic_reports, tmp_path, monkeypatch):
    s = setup
    # CreateProcessW imposes MAX_PATH on cwd, independently of Python long paths.
    root = tmp_path.parent/'nt_non_authoritative'
    s.declaration = replace(s.declaration, study_root=str(root))
    upstream, _, _, state = environment
    config = replace(s.declaration.run_configuration, upstream_root=str(upstream),
        specification=replace(spec(), time_limit_seconds=5.), limits=owned.old.replay.H1HourReplayLimits(3,100,500))
    declaration, _ = enable_post_claim(s, monkeypatch, config=config)
    monkeypatch.setattr(m.BootstrapOwner, '_continue_bootstrap', m.BootstrapOwner._continue_registered_development)
    monkeypatch.setattr(owned.binding.source_binding, 'load_pinned_current', CURRENT)
    load_network = m.BootstrapOwner._load_network
    def static_then_current(self):
        network = load_network(self)
        monkeypatch.setattr(owned.binding.source_binding.rts, 'load_rts_gmlc_chronological_data', lambda root:state['data'])
        return network
    monkeypatch.setattr(m.BootstrapOwner, '_load_network', static_then_current)
    # The module fixture verified these bytes before the one-row source seam.
    resolver = m.symbolic.proof._resolver(s.snapshot._proof_raw)
    monkeypatch.setattr(owned.binding, 'open_manifest', lambda:resolver)
    node = resolver.resolve(declaration.family, declaration.ordinal)
    enrollment = dict(test_only_synthetic_source=True)
    monkeypatch.setattr(owned.binding, 'precheck', lambda *a, **k:node)
    monkeypatch.setattr(owned.binding, 'prevalidate_enrollment', lambda *a, **k:enrollment)
    def bind(resolver, declaration, **kw):
        reader = owned.binding.snapshot.open_snapshot(declaration,
            expected_parent_identity=kw['expected_parent_identity'], expected_anchor_record=kw['expected_anchor_record'])
        try: item = reader.pending_input(**kw['pending_arguments'])
        finally: reader.close()
        item.validate(expected_receipt_sha256=kw['expected_pending_receipt_sha256'])
        request = dict(parent_declaration=declaration, pending_arguments=kw['pending_arguments'],
            input_receipt=json.loads(item.receipt), input_receipt_sha256=item.receipt_sha256, budget=asdict(kw['job_budget']))
        return owned.phase._historical_binding(item.packet, request, node, enrollment)
    monkeypatch.setattr(owned.binding, 'bind', bind)
    monkeypatch.setattr(history, '_source_paths', lambda d:(
        {Path(d['config_path']), Path(d['upstream_root'])/'SHA256SUMS'}, {Path(d['upstream_root'])}))
    captured = []
    init = owned.OwnedController.__init__
    def capture(self, *args):
        init(self, *args); captured.append(self)
    monkeypatch.setattr(owned.OwnedController, '__init__', capture)
    install_launcher(monkeypatch, tmp_path, synthetic_reports)
    continuation=m.BootstrapOwner._continue_owned_development
    def reject_noncanonical_locks(owner):
        result=continuation(owner)
        root=Path(owner.roots['controller'])/'job_000_non_authoritative'
        rows=owner._bootstrap.rows();global_rows=owner._global.rows()
        for index,lock in enumerate((root/'execution.lock',root/'worker_non_authoritative/execution.lock')):
            original=lock.read_bytes();assert original==b'0'
            lock.write_bytes(b'1')
            with pytest.raises(ValueError,match='N0 lock bytes differ'):owner._prepare_N0_terminal()
            (tmp_path/f'preserved_noncanonical_lock_{index}.bin').write_bytes(lock.read_bytes())
            lock.write_bytes(original)
            assert owner._bootstrap.rows()==rows and owner._global.rows()==global_rows
        return result
    monkeypatch.setattr(m.BootstrapOwner,'_continue_owned_development',reject_noncanonical_locks)
    return s, declaration, captured


def test_synthetic_N0_registered_reopened_and_replayed_from_other_episode(numerical):
    s,declaration,captured=numerical
    o=s.open(declaration=declaration)
    try:
        result=o.bootstrap()
        assert result['state']=='pending_post_N'
        assert all(result[k] is False for k in m.FLAGS)
        assert all(lease.stream is None for lease in captured[0]._owned_original_cleanup)
        inspected=o.inspect()
        assert inspected['N0_numerical_evidence_audited'] and inspected['state']=='pending_post_N'
        assert inspected['execution_artifacts_audited'] is inspected['retry_authorized'] is False
        assert o._remaining_global_records()==0
        assert len(o._bootstrap.rows())==5 and len(o._global.rows())==3
        body=o._bootstrap.rows()[4][1]
        assert body['parent_head']==result['parent_head']
        assert body['controller_terminal_sha256']==captured[0].last_obligation_observation.terminal_sha256
        root=Path(o.roots['controller'])
        observed=json.loads((root/'job_000_non_authoritative/observation.json').read_bytes())
        assert observed['exit_code']==0 and observed['whole_job_quiescent']
        heads=retained(o,s)
    finally:o.close()
    reopened=s.open(create=False,create_study=False,declaration=declaration,**heads)
    try:
        assert reopened.inspect()['state']=='pending_post_N'
        with pytest.raises(ValueError,match='no automatic retry'):reopened.bootstrap()
    finally:reopened.close()
    foreign=s.open(create=True,create_study=False,declaration=replace(declaration,ordinal=1),global_head=heads['global_head'])
    try:
        assert foreign.inspect()['state']=='new'
        assert foreign._remaining_global_records()==0
    finally:foreign.close()
