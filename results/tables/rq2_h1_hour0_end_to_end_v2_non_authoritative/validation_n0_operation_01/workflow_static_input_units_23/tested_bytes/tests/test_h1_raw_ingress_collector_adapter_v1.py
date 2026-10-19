"""Saved three-stage integration seam only; no production monkeypatch or gate."""
import importlib.util
from pathlib import Path

import pytest

from tests.test_rq2_normal_h1_hour_archive_v1 import saved, no_solver
from tests.test_rq2_normal_h1_full_collector_v3 import make
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_collector_v3 as collector

spec = importlib.util.spec_from_file_location('ingress_adapter_test', Path(__file__).resolve().parents[1]/
    'experiments/h1_raw_ingress_development_v1.py')
ingress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingress)


@pytest.mark.parametrize('audit_crash', [False, True])
def test_saved_collector_seam_persists_raw_before_first_audit(tmp_path, saved, no_solver, monkeypatch, audit_crash):
    # Only the existing synthetic development fixture gate is replaced here.
    monkeypatch.setattr(collector.DevelopmentH1FullCollector, '_require_execution_gate', lambda *a: None)
    owner = make(tmp_path, create=True)
    archive = ingress.Ingress(tmp_path/'raw_ingress_non_authoritative', 'a'*64, stages=3)
    calls = []
    original_audit = collector.base.replay._audit_stage
    def capture(*args, **kwargs):
        index = len(calls)
        calls.append(index)
        return archive.deliver(index, lambda: saved[1][index], lambda raw: raw)
    def audit(packet, specification, limits, index, locks, raw):
        assert (archive.root/f'{index:03d}'/'raw.bin').read_bytes() == raw
        assert (archive.root/f'{index:03d}'/'raw_receipt.json').is_file()
        if audit_crash:
            archive.abort()
            raise RuntimeError('scientific audit interrupted after raw persistence')
        return original_audit(packet, specification, limits, index, locks, raw)
    monkeypatch.setattr(collector.base.native.capture, 'solve_once', capture)
    monkeypatch.setattr(collector.base.replay, '_audit_stage', audit)
    try:
        head = owner.inspect().inspection.registry_head
        if audit_crash:
            with pytest.raises(RuntimeError, match='scientific audit interrupted'):
                owner._run_checkpoint_development(expected_head=head)
            assert calls == [0]
            state = ingress.inspect(archive.root, expected_request='a'*64,
                expected_binding_sha256=ingress.digest(ingress.encode(archive.binding)))
            assert state['retained_complete_raw'] == 1
            assert not state['callback_sequence_complete']
            assert archive.poisoned
            with pytest.raises(ValueError, match='poisoned'):
                archive.deliver(1, lambda: pytest.fail('must not retry'), lambda r: r)
            assert (archive.root/'000/raw.bin').read_bytes() == saved[1][0]
        else:
            result = owner._run_checkpoint_development(expected_head=head)
            assert result.status == 'accepted'
            assert owner.inspect().formal_execution_ready is False
            assert len(calls) == 3
            assert archive.finish()['retained_complete_raw'] == 3
    finally:
        owner.close()
