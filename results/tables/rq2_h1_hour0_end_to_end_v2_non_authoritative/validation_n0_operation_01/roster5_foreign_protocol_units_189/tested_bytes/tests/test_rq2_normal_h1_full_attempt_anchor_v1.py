from hashlib import sha256
import pytest
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_attempt_anchor as api
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_attempt_anchor as old


def pin(i):return sha256(str(i).encode()).hexdigest()


def test_full_192_hour_anchor_inventory_and_inspection_only_reopen(tmp_path):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=385,create=True)
    before=None
    try:
        for i in range(385):
            receipt=owner.advance(pin(i),pin(i+1000),expected_previous=before)
            before=receipt.registry_head
            if i==235:owner.confirm(receipt) # full single-hour inventory boundary
        assert receipt.sequence==384
        owner.confirm(receipt)
        with pytest.raises(ValueError,match='budget'):owner.advance(pin(999),pin(998),expected_previous=before)
    finally:owner.close()
    reopened=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=385,expected_record_sha256=receipt.record_sha256)
    try:
        assert reopened.inspect()==receipt
        with pytest.raises(ValueError,match='reopened'):
            reopened.advance(pin(999),pin(998),expected_previous=before)
    finally:reopened.close()


@pytest.mark.parametrize('bad',[True,0,386,1.0])
def test_exact_capacity_rejection_precedes_files(tmp_path,bad):
    root=tmp_path/'full_non_authoritative'
    with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=bad,create=True)
    assert not root.exists()


@pytest.mark.parametrize('persisted',[False,True])
def test_uncertain_write_poison_and_reopen_retains_observed_prefix(tmp_path,monkeypatch,persisted):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=236,create=True)
    write=api._write
    def fail(*a):
        if persisted:write(*a)
        raise RuntimeError('receipt unknown')
    with monkeypatch.context() as patch:
        patch.setattr(api,'_write',fail)
        try:
            with pytest.raises(RuntimeError):owner.advance('2'*64,'3'*64,expected_previous=None)
            with pytest.raises(ValueError):owner.inspect()
        finally:owner.close()
    reopened=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=236)
    try:
        receipt=reopened.inspect()
        assert (receipt is not None)==persisted
        if persisted:assert receipt.registry_head=='2'*64
    finally:reopened.close()


def test_legacy_type_and_namespace_isolation(tmp_path):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    try:
        receipt=owner.advance('2'*64,'3'*64,expected_previous=None)
        foreign=old.AnchorReceipt(receipt.anchor_identity,receipt.sequence,receipt.registry_head,receipt.record_sha256)
        with pytest.raises(ValueError,match='exact'):owner.confirm(foreign)
    finally:owner.close()
    with pytest.raises(ValueError):old.DevelopmentH1AttemptAnchor(root,'1'*64,max_records=3)
    root2=tmp_path/'old_non_authoritative'
    owner=old.DevelopmentH1AttemptAnchor(root2,'1'*64,max_records=3,create=True)
    owner.close()
    with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root2,'1'*64,max_records=3)
    with pytest.raises(ValueError):old.DevelopmentH1AttemptAnchor(tmp_path/'old_cap_non_authoritative','1'*64,max_records=236,create=True)


def test_record_limit_and_live_corruption(tmp_path):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    owner.advance('2'*64,'3'*64,expected_previous=None)
    (root/'000.json').write_bytes(b' '*(api.MAX_RECORD_BYTES+1))
    try:
        with pytest.raises(ValueError,match='limit'):owner.inspect()
        with pytest.raises(ValueError,match='unresolved'):owner.inspect()
    finally:owner.close()
    with pytest.raises(ValueError,match='limit'):api._write(tmp_path/'oversize.json',{'data':'x'*api.MAX_RECORD_BYTES})
    assert not (tmp_path/'oversize.json').exists()


def test_direct_dependency_drift_rejects_existing_root(tmp_path,monkeypatch):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    owner.advance('2'*64,'3'*64,expected_previous=None)
    owner.close()
    changed=tmp_path/'dependency.py'
    changed.write_bytes(b'changed dependency bytes')
    original=api.implementation_identity()
    for module in (api.files,api.chunks,api.chunks.base,api.chunks.base.replay.native,
                   api.files.local,api.files.worker.store):
        owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(module,'__file__',str(changed))
                assert api.implementation_identity()!=original
                with pytest.raises(ValueError,match='implementation'):owner.inspect()
        finally:owner.close()
        with monkeypatch.context() as patch:
            patch.setattr(module,'__file__',str(changed))
            with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
    restored=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
    restored.close()
