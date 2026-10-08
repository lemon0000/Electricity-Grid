import pytest
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_attempt_anchor as api


def test_durable_receipts_and_readonly_reopen(tmp_path):
    root=tmp_path/'anchor_non_authoritative'
    owner=api.DevelopmentH1AttemptAnchor(root,'1'*64,max_records=3,create=True)
    first=owner.advance('2'*64,'3'*64,expected_previous=None)
    second=owner.advance('4'*64,'5'*64,expected_previous=first.registry_head)
    owner.confirm(second)
    owner.close()
    reopened=api.DevelopmentH1AttemptAnchor(root,'1'*64,max_records=3,expected_record_sha256=second.record_sha256)
    try:
        assert reopened.inspect()==second
        with pytest.raises(ValueError,match='reopened'):reopened.advance('6'*64,'7'*64,expected_previous='4'*64)
    finally:reopened.close()


def test_anchor_fresh_failure_poison(tmp_path,monkeypatch):
    owner=api.DevelopmentH1AttemptAnchor(tmp_path/'a_non_authoritative','1'*64,max_records=2,create=True)
    original=api.files._write
    def fail(*a):original(*a);raise RuntimeError('readback lost')
    monkeypatch.setattr(api.files,'_write',fail)
    try:
        with pytest.raises(RuntimeError):owner.advance('2'*64,'3'*64,expected_previous=None)
        with pytest.raises(ValueError,match='unresolved'):owner.inspect()
    finally:owner.close()


def test_live_anchor_detects_record_replacement(tmp_path):
    owner=api.DevelopmentH1AttemptAnchor(tmp_path/'a_non_authoritative','1'*64,max_records=2,create=True)
    owner.advance('2'*64,'3'*64,expected_previous=None)
    (owner._lease.root/'000.json').write_bytes(b'{}')
    try:
        with pytest.raises(ValueError):owner.inspect()
    finally:owner.close()
