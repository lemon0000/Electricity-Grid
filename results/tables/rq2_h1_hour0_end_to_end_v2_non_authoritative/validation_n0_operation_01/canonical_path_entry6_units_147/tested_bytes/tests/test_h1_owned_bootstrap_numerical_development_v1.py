"""One synthetic three-stage N0 Windows Job; never a real solver run."""
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


@pytest.mark.parametrize('mode', ['n0', 'n1', 'long_cwd'])
def test_owned_n0_synthetic_job_and_independent_historical_replay(
        setup, environment, synthetic_reports, tmp_path, monkeypatch, mode):
    s = setup
    # CreateProcessW imposes MAX_PATH on cwd, independently of Python long paths.
    root = tmp_path.parent/(mode+'_non_authoritative') if mode != 'long_cwd' else tmp_path/'study_non_authoritative'
    s.declaration = replace(s.declaration, study_root=str(root))
    upstream, _, _, state = environment
    config = replace(s.declaration.run_configuration, upstream_root=str(upstream),
        specification=replace(spec(), time_limit_seconds=5.), limits=owned.old.replay.H1HourReplayLimits(3,100,500))
    declaration, _ = enable_post_claim(s, monkeypatch, config=config)
    monkeypatch.setattr(m.BootstrapOwner, '_continue_bootstrap', m.BootstrapOwner._continue_owned_development)
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
    attempts = []
    if mode != 'n0':
        def no_child(*a, **k):
            attempts.append(1)
            raise AssertionError('child reached invalid request/path gate')
        monkeypatch.setattr(owned.old.process, 'normal_task_child', no_child)
    if mode == 'n1':
        clock_job = owned.OwnedController._owned_clock_job
        def drop_request(self, *args):
            self._active_request = None
            return clock_job(self, *args)
        monkeypatch.setattr(owned.OwnedController, '_owned_clock_job', drop_request)
    o = s.open(declaration=declaration)
    try:
        if mode != 'n0':
            if mode == 'long_cwd':
                assert len(str(Path(o.roots['controller'])/'job_000_non_authoritative/scratch_non_authoritative')) >= 260
            with pytest.raises(ValueError, match='active request' if mode == 'n1' else 'CreateProcess limit'):
                o.bootstrap()
            assert attempts == []
            assert not list(Path(o.roots['controller']).glob('job_*'))
            assert all(x.stream is None for x in captured[0]._owned_original_cleanup)
            return
        result = o.bootstrap()
        heads = retained(o, s)
        root = Path(o.roots['controller'])
        assert result['state'] == 'pending_N_terminal_registration'
        assert all(result[k] is False for k in m.FLAGS)
        controller = captured[0]
        assert controller._lease is None and controller._owned_lease is None and controller._owned_scope is None
        observation = json.loads((root/'job_000_non_authoritative/observation.json').read_bytes())
        assert observation['exit_code'] == 0 and observation['whole_job_quiescent']
        assert observation['pid'] != os.getpid()
        args = dict(expected_binding_sha256=controller.obligation_binding_pin,
            expected_terminal_sha256=result['obligation_terminal_sha256'], completed_hours=1)
        prepared = history.prepare(root, **args)
        checked = json.loads(prepared.audit_payload)['historical_controller']
        assert checked['historical_job_clock_prefix_verified']
        assert checked['live_release_authenticated'] is False
        assert prepared.decision.relative_hour == 0
        assert o.inspect()['state'] == 'execution_indeterminate'
    finally:
        o.close()
    reopened = s.open(create=False, create_study=False, declaration=declaration, **heads)
    try:
        assert reopened.inspect()['state'] == 'execution_indeterminate'
        with pytest.raises(ValueError, match='no automatic retry'): reopened.bootstrap()
    finally:
        reopened.close()
