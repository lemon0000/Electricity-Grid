"""Source ancestry and durable identity attacks using an explicit fake Parent."""
import json
import os

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,make,rows,context,case,setup,legacy_setup,no_solver,load)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.mark.parametrize('target',['db','lock','directory'])
def test_same_bytes_phase_replacement_between_close_and_reopen_rejected(fault_case,target):
    f=fault_case;f.faults['replace_phase']=target
    with make(f) as owner:
        with pytest.raises(ValueError):owner.consume()
        assert f.c.owner.closed and len(f.retained)==1
        assert rows(f.c.owner.owner_root/'owner.sqlite')==[]
        if owner._phase is not None:assert owner._phase._lease_object.stream is None


@pytest.mark.parametrize('target',['takeover_packet.json','binding.json'])
def test_wrong_first_readback_rejected_before_retention_or_close(fault_case,target):
    f=fault_case;f.faults.update(file=target,point='write_corrupt')
    with make(f) as owner:
        with pytest.raises(ValueError,match='readback differs'):owner.consume()
        assert not f.c.owner.closed and not f.retained
        assert (owner.root/target).read_bytes()==b'{}'
        assert owner._lease.stream is None


@pytest.mark.parametrize('kind',['phase','holder','journal'])
@pytest.mark.parametrize('point',['child_before','child_after'])
def test_partial_predecessor_child_close_failure_releases_all_old_leases(fault_case,kind,point):
    f=fault_case;old=f.c.owner
    f.faults.update(close_child=kind,point=point)
    leases=(old._original_phase._lease_object,old._original_holder._lease_object,old._original_journal._original_lease)
    with make(f) as owner:
        with pytest.raises(RuntimeError,match='injected child close'):owner.consume()
        assert old.closed and all(lease.stream is None for lease in leases)
        assert rows(old.owner_root/'owner.sqlite')==[]
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
    f.faults.clear()


def test_tampered_reentry_flag_cannot_repeat_external_retention(fault_case):
    f=fault_case;calls=[]
    def retain(root,before,after):
        calls.append(after)
        if len(calls)==1:
            owner._in_external=False
            owner._retain_journal(root,before,after)
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises(ValueError,match='callback state'):owner.consume()
        assert len(calls)==1 and not f.c.owner.closed
        assert owner._journal._original_lease.stream is None


def test_callback_cannot_use_global_state_helpers_to_reenter(fault_case):
    f=fault_case;calls=[]
    def retain(root,before,after):
        calls.append(after)
        with pytest.raises(ValueError,match='token'):f.m._LEAVE_EXTERNAL(owner,object())
        with pytest.raises(ValueError):f.m._ENTER_EXTERNAL(owner)
        with pytest.raises(ValueError):f.m._ADVANCE_COUNT(owner,'_journal_count',len(calls),object())
        with pytest.raises(ValueError):owner._retain_journal(root,before,after)
        return after
    with make(f,retain_head=retain) as owner:
        assert owner.consume()['completed_hours']==1
        assert len(calls)==5 and len(set(calls))==5


@pytest.mark.parametrize('delta',[-1,0])
def test_exact_packet_cap_preflight_boundary(fault_case,delta):
    f=fault_case
    with make(f) as preview:
        preview._guard.acquire();preview._bundle.enter();f.m.common.CommonOwnerGenesis._enter(f.c.owner)
        try:
            preview._prepare();size=len(preview._packet)
            assert not preview.root.exists()
        finally:
            f.m.common.CommonOwnerGenesis._leave(f.c.owner);preview._bundle.leave();preview._guard.release()
    with make(f,max_packet_bytes=size+delta) as owner:
        if delta:
            with pytest.raises(ValueError,match='complete handoff archive branch'):owner.consume()
            assert not owner.root.exists() and not f.c.owner.closed and not f.retained
        else:
            assert owner.consume()['completed_hours']==1
            assert len((owner.root/'takeover_packet.json').read_bytes())==size


@pytest.mark.parametrize('stage',[1,3,5])
def test_wrong_retention_acknowledgement_rejects_exact_stage(fault_case,stage):
    f=fault_case;count=[]
    def retain(root,before,after):
        count.append(after);return '0'*64 if len(count)==stage else after
    with make(f,retain_head=retain) as owner:
        with pytest.raises(ValueError,match='exact external journal head acknowledgement'):owner.consume()
        assert len(count)==stage and owner._state=='failed'
        assert rows(f.c.owner.owner_root/'owner.sqlite')==([('intent',),('outcome',)] if stage==5 else [])


@pytest.mark.parametrize('field',['_journal_count','_retained'])
def test_callback_counter_mutation_rejected(fault_case,field):
    f=fault_case
    def retain(root,before,after):setattr(owner,field,99);return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises(ValueError,match='callback state or counters'):owner.consume()
        assert not f.c.owner.closed and rows(f.c.owner.owner_root/'owner.sqlite')==[]


def test_captured_global_ancestor_remains_valid(fault_case):
    f=fault_case
    f.c.case.global_.head='d'*64
    f.c.case.global_.history.append(('d'*64,{'other_group':True}))
    with make(f) as owner:
        assert owner.consume()['completed_hours']==1


def test_unknown_captured_global_head_rejects_before_effects(fault_case):
    f=fault_case;doc=json.loads(f.ref._raw)
    doc['declaration']['provenance']['global_head']='f'*64
    f.ref._raw=f.m.phase.encode(doc)
    before=f.c.owner.inspect()
    with make(f) as owner:
        with pytest.raises(ValueError,match='not a retained ancestor'):owner.consume()
        assert not owner.root.exists() and not f.retained
    assert f.c.owner.inspect()==before


@pytest.mark.parametrize('target',['packet','binding','journal_header','binder'])
@pytest.mark.parametrize('attack',['replace','hardlink'])
def test_durable_identity_change_rejected_after_external_callback(fault_case,tmp_path,target,attack):
    f=fault_case;calls=[]
    def retain(root,before,after):
        calls.append(after)
        paths={'packet':owner.root/'takeover_packet.json','binding':owner.root/'binding.json',
               'journal_header':root/'header.json','binder':f.c.owner.root/'header.json'}
        path=paths[target]
        assert path.is_file()
        if attack=='replace':
            replacement=tmp_path/'same_bytes.tmp';replacement.write_bytes(path.read_bytes());replacement.replace(path)
        else:os.link(path,tmp_path/'outside_namespace_hardlink.json')
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises(ValueError):owner.consume()
        assert len(calls)==1 and owner._state=='failed' and not f.c.owner.closed
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
        assert owner._lease.stream is None and owner._journal._original_lease.stream is None


def test_callback_reentry_rejects_without_poisoning_original_transaction(fault_case):
    f=fault_case;count=[]
    def retain(root,before,after):
        with pytest.raises(ValueError):owner.consume()
        with pytest.raises(ValueError):owner.close()
        count.append(after);return after
    with make(f,retain_head=retain) as owner:
        assert owner.consume()['completed_hours']==1
        assert len(count)==5 and owner._state=='complete'


@pytest.mark.parametrize('target',['journal','holder','db'])
def test_unknown_suffix_is_preserved_and_prevents_phase_commit(fault_case,target):
    f=fault_case;count=[];suffix=[]
    def retain(root,before,after):
        count.append(after)
        if len(count)==2:
            if target=='db':
                import sqlite3
                with sqlite3.connect(f.c.owner.owner_root/'owner.sqlite') as db:
                    db.execute('INSERT INTO events(seq,predecessor,kind,body,head) VALUES (?,?,?,?,?)',
                        (1,owner._phase.genesis,'intent',b'{}','e'*64))
                return after
            path=(root/'00000000000000000006.json' if target=='journal'
                  else f.c.owner.holder_root/'000003.json')
            path.write_bytes(b'{}');suffix.append(path)
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises(ValueError):owner.consume()
        assert len(count)==2 and f.c.owner.closed
        if target=='db':assert rows(f.c.owner.owner_root/'owner.sqlite')==[('intent',)]
        else:
            assert suffix[0].read_bytes()==b'{}'
            assert rows(f.c.owner.owner_root/'owner.sqlite')==[]
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
