from hashlib import sha256
from collections import Counter
import json
import os
import pytest
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_attempt_anchor_v3 as api
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_attempt_anchor as old
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_attempt_anchor as legacy_full


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


def filled(root):
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    receipt=owner.advance('2'*64,'3'*64,expected_previous=None)
    return owner,receipt


def test_every_scan_reads_each_file_once_and_confirm_still_scans(tmp_path,monkeypatch):
    owner,receipt=filled(tmp_path/'full_non_authoritative')
    original=api._read;calls=Counter()
    def counted(path,identity=None):
        calls[path.name]+=1
        assert identity is not None
        return original(path,identity)
    monkeypatch.setattr(api,'_read',counted)
    try:
        assert owner.inspect()==receipt
        assert calls=={'header.json':1,'000.json':1}
        owner.confirm(receipt)
        assert calls=={'header.json':2,'000.json':2}
    finally:owner.close()


@pytest.mark.parametrize('fault',['same_bytes_replace','retained_bytes','header','extra','gap','missing','read','lease'])
def test_live_single_view_scan_faults_poison(tmp_path,monkeypatch,fault):
    root=tmp_path/'full_non_authoritative';owner,_=filled(root)
    record=root/'000.json'
    if fault=='same_bytes_replace':
        other=tmp_path/'replacement.json';other.write_bytes(record.read_bytes());os.replace(other,record)
    elif fault in ('retained_bytes','header'):
        path=record if fault=='retained_bytes' else root/'header.json'
        item=json.loads(path.read_bytes());item['schema']='changed';path.write_bytes(api.chunks.base._bytes(item))
    elif fault=='extra':(root/'unexpected.json').write_bytes(b'{}')
    elif fault=='gap':record.rename(root/'001.json')
    elif fault=='missing':record.rename(tmp_path/'moved_record.json')
    elif fault=='read':
        def fail(*a):raise OSError('read failed')
        monkeypatch.setattr(api,'_read',fail)
    elif fault=='lease':
        def fail():raise OSError('lease drift')
        monkeypatch.setattr(owner._lease,'check',fail)
    try:
        with pytest.raises((ValueError,OSError)):owner.inspect()
        assert owner._poisoned
        with pytest.raises(ValueError):owner.inspect()
    finally:owner.close()


@pytest.mark.parametrize('fault',['key','sequence','previous_record_sha256','previous_registry_head','registry_head','event_sha256'])
def test_reopen_single_view_validates_full_chain(tmp_path,fault):
    root=tmp_path/'full_non_authoritative';owner,_=filled(root);owner.close()
    path=root/'000.json';item=json.loads(path.read_bytes())
    if fault=='key':item['extra']=1
    elif fault=='sequence':item[fault]=True
    elif fault=='previous_record_sha256':item[fault]='9'*64
    elif fault=='previous_registry_head':item[fault]='9'*64
    else:item[fault]='invalid'
    path.write_bytes(api.chunks.base._bytes(item))
    with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)


def test_replacement_during_read_rejected(tmp_path,monkeypatch):
    root=tmp_path/'full_non_authoritative';owner,_=filled(root)
    record=root/'000.json';other=tmp_path/'replacement.json';other.write_bytes(record.read_bytes())
    original=api.files.local._file_identity;calls=[0]
    def replacing(path):
        if path==record:
            calls[0]+=1
            if calls[0]==2:os.replace(other,record)
        return original(path)
    monkeypatch.setattr(api.files.local,'_file_identity',replacing)
    try:
        with pytest.raises(ValueError):owner.inspect()
        assert owner._poisoned
    finally:owner.close()


def test_fresh_scan_after_write_failure_poison_and_retains_record(tmp_path,monkeypatch):
    root=tmp_path/'full_non_authoritative'
    owner=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    scan=owner._scan;calls=[0]
    def failed():
        calls[0]+=1
        if calls[0]==2:raise OSError('fresh scan failed')
        return scan()
    monkeypatch.setattr(owner,'_scan',failed)
    try:
        with pytest.raises(OSError):owner.advance('2'*64,'3'*64,expected_previous=None)
        assert owner._poisoned and (root/'000.json').exists()
    finally:owner.close()
    with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,expected_record_sha256='9'*64)
    restored=api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
    try:assert restored.inspect().registry_head=='2'*64
    finally:restored.close()


@pytest.mark.parametrize('fault',['missing','none','identity','pin','bootstrap','empty_bootstrap'])
def test_retained_metadata_cannot_disable_stable_view_check(tmp_path,fault):
    owner,_=filled(tmp_path/'full_non_authoritative')
    identity,digest=owner._retained['000.json']
    if fault=='missing':owner._retained.pop('000.json')
    elif fault=='none':owner._retained['000.json']=None
    elif fault=='identity':owner._retained['000.json']=(None,digest)
    elif fault=='pin':owner._retained['000.json']=(identity,'9'*64)
    else:
        owner._expected_count=None
        if fault=='bootstrap':owner._retained.pop('000.json')
        else:owner._retained.clear()
    try:
        with pytest.raises(ValueError):owner.inspect()
        assert owner._poisoned
    finally:owner.close()


def test_full_v1_and_v3_receipts_and_roots_are_isolated(tmp_path):
    root=tmp_path/'v3_non_authoritative';owner,receipt=filled(root)
    foreign=legacy_full.FullAnchorReceipt(receipt.anchor_identity,receipt.sequence,receipt.registry_head,receipt.record_sha256)
    try:
        with pytest.raises(ValueError):owner.confirm(foreign)
    finally:owner.close()
    with pytest.raises(ValueError):legacy_full.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
    root=tmp_path/'v1_non_authoritative'
    prior=legacy_full.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3,create=True)
    try:
        receipt=prior.advance('2'*64,'3'*64,expected_previous=None)
        foreign=api.FullAnchorReceipt(receipt.anchor_identity,receipt.sequence,receipt.registry_head,receipt.record_sha256)
        with pytest.raises(ValueError):prior.confirm(foreign)
    finally:prior.close()
    with pytest.raises(ValueError):api.DevelopmentH1FullAttemptAnchor(root,'1'*64,max_records=3)
