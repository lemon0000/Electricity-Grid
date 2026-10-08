from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from experiments import h1_parent_snapshot_development_v1 as api
from tests.test_h1_bounded_file_parent_development_v1 import owner,step
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved


def pending(p,env,hour=0):
    state,before,previous=p._restore()
    receipt=p._load(hour,source_pin(env,hour))
    packet=p._packet(receipt,hour,before,previous)
    p._append(p._intent(hour,receipt,packet),receipt.audit_payload)
    return packet,dict(expected_head=p._journal.head,expected_source_identity=receipt.identity,
        expected_request_key=api.replay.request_key(packet,p._spec,p._limits),expected_packet_audit=packet.audit_identity)


def snapshot(p,**changes):
    args=dict(expected_parent_identity=p.identity,expected_anchor_record=p._anchor.inspect().record_sha256)
    args.update(changes)
    return api.open_snapshot(p._declaration,**args)


def files(root):
    return {p.relative_to(root).as_posix():(api.io.identity(p),api.io.digest(p.read_bytes()))
            for p in root.rglob('*') if p.is_file() and p.name!='execution.lock'}


def test_live_parent_snapshot_origin_reads_without_writes(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        packet,args=pending(p,environment)
        before=files(p._root)
        q=snapshot(p)
        try:
            result=q.pending_input(**args)
            assert result.packet==packet
            result.validate(expected_receipt_sha256=result.receipt_sha256)
            record=json.loads(result.receipt)
            assert record['external_live_handoff_required'] and not record['native_execution_authorized']
            assert record['parent_identity']==p.identity and record['intent_head']==p._journal.head
            with pytest.raises(ValueError,match='read only'):q._journal.append()
            with pytest.raises(ValueError,match='read only'):q._anchor.advance()
            with pytest.raises(ValueError,match='inspection only'):step(q,environment,())
        finally:q.close()
        assert files(p._root)==before
        for lease in (p._root_lease,p._journal._lease,p._anchor._lease):lease.check()
        assert p.inspect().status=='pending_unknown'
    finally:p.close()


def test_typed_receipt_rejects_packet_and_authority_changes(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        q=snapshot(p)
        try:result=q.pending_input(**args)
        finally:q.close()
        for field,value in (('formal_result',True),('native_execution_authorized',True),
            ('writer_lock_authenticated',True),('before_identity','f'*64),('intent_head','f'*64),
            ('packet_audit_identity','f'*64),('relative_hour',1),('stage_slots',4),
            ('snapshot_implementation','f'*64),('external_live_handoff_required',False)):
            record=json.loads(result.receipt);record[field]=value
            with pytest.raises(ValueError):replace(result,receipt=api.io.encode(record))
        with pytest.raises(ValueError):result.validate(expected_receipt_sha256='f'*64)
    finally:p.close()


def test_future_carry_rebuilt_from_prior_scientific_child(tmp_path,environment,synthetic_reports):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=2,create=True)
    try:
        assert step(p,environment,synthetic_reports).completed_hours==1
        packet,args=pending(p,environment,1)
        q=snapshot(p)
        try:
            rebuilt=q.pending_input(**args).packet
            assert rebuilt==packet and rebuilt.before.completed_hours==rebuilt.relative_hour==1
        finally:q.close()
        assert not (p._root/'hour_001_non_authoritative').exists()
    finally:p.close()


@pytest.mark.parametrize('field',['expected_head','expected_source_identity','expected_request_key','expected_packet_audit'])
def test_wrong_pending_context_refused(tmp_path,environment,field):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        q=snapshot(p)
        try:
            args[field]='f'*64
            with pytest.raises(ValueError):q.pending_input(**args)
        finally:q.close()
    finally:p.close()


@pytest.mark.parametrize('when',['before','during'])
def test_existing_or_new_partial_child_cannot_be_worker_input(tmp_path,environment,monkeypatch,when):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        q=snapshot(p)
        root=p._root/'hour_000_non_authoritative'
        if when=='before':root.mkdir()
        else:
            original=q._packet
            calls=0
            def changed(*a,**k):
                nonlocal calls
                packet=original(*a,**k);calls+=1
                if calls==2:root.mkdir()
                return packet
            monkeypatch.setattr(q,'_packet',changed)
        try:
            with pytest.raises(ValueError):q.pending_input(**args)
        finally:q.close()
    finally:p.close()


def test_unanchored_journal_tail_refused(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        old=p._anchor.inspect().record_sha256
        pending(p,environment)
        with pytest.raises(ValueError):snapshot(p,expected_anchor_record=old)
    finally:p.close()


@pytest.mark.parametrize('change',['journal','anchor'])
def test_writer_changes_prefix_during_reconstruction_refused(tmp_path,environment,monkeypatch,change):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        q=snapshot(p)
        original=q._packet
        calls=0
        def changed(*a,**k):
            nonlocal calls
            packet=original(*a,**k);calls+=1
            if calls==2:
                if change=='journal':
                    p._journal.append({'fault':'unanchored'},(),expected_head=p._journal.head,
                        declared_payload_bytes=0,expected_payload_sha256=api.io.digest(b''))
                else:
                    p._anchor.advance(p._journal.head,'a'*64,expected_previous=p._journal.head)
            return packet
        monkeypatch.setattr(q,'_packet',changed)
        try:
            with pytest.raises(ValueError):q.pending_input(**args)
        finally:q.close()
    finally:p.close()


def test_closed_writer_pending_is_evidence_only(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    _,args=pending(p,environment)
    declaration=deepcopy(p._declaration)
    identity=p.identity;pin=p._anchor.inspect().record_sha256
    p.close()
    q=api.open_snapshot(declaration,expected_parent_identity=identity,expected_anchor_record=pin)
    try:
        record=json.loads(q.pending_input(**args).receipt)
        assert not record['writer_lock_authenticated'] and not record['quiescence_certified']
        assert not record['native_execution_authorized'] and record['external_live_handoff_required']
    finally:q.close()


def test_parent_declaration_pin_checked_before_loading(tmp_path,environment,monkeypatch):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        def denied(*a,**k):pytest.fail('unbound declaration reached source loader')
        monkeypatch.setattr(api.binding,'load_pinned_current',denied)
        with pytest.raises(ValueError,match='hash differs'):
            api.open_snapshot(p._declaration,expected_parent_identity='f'*64,
                              expected_anchor_record=p._anchor.inspect().record_sha256)
    finally:p.close()


@pytest.mark.parametrize('change',['workload','clock','config'])
def test_changed_source_observation_refused(tmp_path,environment,change):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        q=snapshot(p)
        if change=='workload':environment[3]['workload']='1'
        elif change=='clock':environment[3]['power_change']['timestamp']='2020-01-02T00:00:00+00:00'
        else:environment[1].write_bytes(b'{"changed":true}')
        try:
            with pytest.raises(ValueError):q.pending_input(**args)
        finally:q.close()
    finally:p.close()


def test_actual_pinned_origin_packet_in_separate_python(tmp_path):
    root=Path(__file__).resolve().parents[1]
    old=json.loads((root/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative/request.json').read_bytes())
    origin=api.binding.H1SourceDeclaration(**old['source_declaration'])
    receipt=api.binding.load_pinned_current(origin,old['upstream_root'],config_path=old['config_path'])
    p=api.bounded.SavedSourceParent(tmp_path/'actual_source_parent_non_authoritative',receipt.network,
        api.Rq2SolverSpec(**old['work']['specification']),api.replay.H1HourReplayLimits(**old['limits']),
        origin=origin,upstream_root=old['upstream_root'],config_path=old['config_path'],
        dc_bus=old['dc_bus'],hours=1,create=True)
    try:
        packet=p._packet(receipt,0,None,None)
        p._append(p._intent(0,receipt,packet),receipt.audit_payload)
        before=files(p._root)
        request=dict(declaration=p._declaration,parent_identity=p.identity,
            anchor=p._anchor.inspect().record_sha256,context=dict(expected_head=p._journal.head,
            expected_source_identity=receipt.identity,expected_request_key=api.replay.request_key(packet,p._spec,p._limits),
            expected_packet_audit=packet.audit_identity))
        script="""import sys,json
sys.path.insert(0,sys.argv[1])
from experiments import h1_parent_snapshot_development_v1 as api
r=json.loads(sys.argv[2])
with api.replay.guard.solver_calls_forbidden():
    q=api.open_snapshot(r['declaration'],expected_parent_identity=r['parent_identity'],expected_anchor_record=r['anchor'])
    try:
        p=q.pending_input(**r['context']).packet
        print(json.dumps(dict(audit=p.audit_identity,before=api.source._digest(p.before),hour=p.relative_hour,stages=len(api.replay.native.model_api.stage_order(p.inputs)))))
    finally:q.close()
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(root),json.dumps(request)],
                              capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stderr
        observed=json.loads(result.stdout)
        assert observed==dict(audit=packet.audit_identity,before=api.source._digest(packet.before),hour=0,stages=232)
        assert files(p._root)==before
        assert not (p._root/'hour_000_non_authoritative').exists()
        for lease in (p._root_lease,p._journal._lease,p._anchor._lease):lease.check()
    finally:p.close()


def test_separate_python_reads_live_locked_journal_and_anchor(tmp_path,environment):
    p=owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        _,args=pending(p,environment)
        before=files(p._root)
        payload=dict(root=str(p._root),identity=p.identity,anchor=p._anchor.inspect().record_sha256,
                     head=args['expected_head'])
        script="""import sys,json
sys.path.insert(0,sys.argv[1])
from experiments import h1_parent_snapshot_development_v1 as api
r=json.loads(sys.argv[2]);root=api.Path(r['root'])
a=api.AnchorSnapshot(root/'parent_anchor_non_authoritative',r['identity'],max_records=3,expected_record_sha256=r['anchor'])
j=api.JournalSnapshot(root/'parent_events_non_authoritative',api.chunks.ChunkContentBudget(2,524288,1048576),binding_identity=r['identity'],expected_head=r['head'])
assert a.inspect().registry_head==j.inspect().head==r['head']
assert j.inspect().events==1
j.close();a.close()
print('read_only_ok')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(Path(__file__).resolve().parents[1]),json.dumps(payload)],
                              capture_output=True,text=True,timeout=30)
        assert result.returncode==0,result.stderr
        assert result.stdout.strip()=='read_only_ok'
        assert files(p._root)==before
        for lease in (p._root_lease,p._journal._lease,p._anchor._lease):lease.check()
    finally:p.close()
