"""Actual Reader MRO teardown and predecessor namespace grammar, no solver."""
from threading import RLock,get_ident
import os

import pytest

from experiments import h1_constructor_rejection_support_development_v1 as support
from experiments import h1_phase_historical_batch_development_v2 as candidate
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def reader_with_owners(failure=None):
    calls=[]
    class Owner:
        def __init__(self,name):self.name,self.closed=name,False
        def close(self):
            calls.append(self.name);self.closed=True
            if self.name==failure:raise RuntimeError('named owner close failure')
    class Reader(candidate.ConstructorInspectionCapture,candidate.HistoricalTimedSnapshot):pass
    reader=object.__new__(Reader)
    reader._guard,reader._closed=RLock(),False
    reader._cic_creator=(os.getpid(),get_ident());reader._cic_value=object()
    owners=[Owner(name) for name in ('_journal','_anchor','_root_lease')]
    for name,value in zip(('_journal','_anchor','_root_lease'),owners):setattr(reader,name,value)
    return reader,owners,calls,Owner


@pytest.mark.parametrize('drift',['alias','code'])
def test_current_v2_rejects_parent_close_drift_but_dynamic_cleanup_leaves_owners(monkeypatch,drift):
    reader,owners,calls,Owner=reader_with_owners()
    outer=Owner('outer');frames={0:object()};primary=ValueError('primary fault')
    parent=candidate.binding.snapshot.parent.SourceParent
    with monkeypatch.context() as patch:
        if drift=='alias':patch.setattr(parent,'close',lambda self:None)
        else:patch.setattr(parent.close,'__code__',(lambda self:None).__code__)
        with pytest.raises(ValueError,match='successor'):candidate._check_dependencies()
        candidate._close_replay(reader,[outer],frames,False,primary)
        assert calls==['outer'] and not any(owner.closed for owner in owners)
        assert not reader._closed and all(getattr(reader,field) is owner
            for field,owner in zip(('_journal','_anchor','_root_lease'),owners))
    # The detached successor closes the original retained owners after restore.
    support.close_replay(reader,[],{},False,primary)
    assert all(owner.closed for owner in owners)


@pytest.mark.parametrize('drift',['alias','code'])
@pytest.mark.parametrize('failure',[None,'_journal','_anchor','_root_lease','outer_b'])
def test_frozen_real_parent_program_closes_all_owners_after_descriptor_or_code_fault(monkeypatch,drift,failure):
    reader,owners,calls,Owner=reader_with_owners(failure)
    outer_a,outer_b=Owner('outer_a'),Owner('outer_b')
    primary=ValueError('primary validation failure');frames={0:object()}
    parent=candidate.binding.snapshot.parent.SourceParent
    with monkeypatch.context() as patch:
        if drift=='alias':patch.setattr(parent,'close',lambda self:None)
        else:patch.setattr(parent.close,'__code__',(lambda self:None).__code__)
        with pytest.raises(ValueError,match='successor'):candidate._check_dependencies()
        support.close_replay(reader,[outer_a,outer_b],frames,False,primary)
    assert calls==['_journal','_anchor','_root_lease','outer_b','outer_a']
    assert all(owner.closed for owner in (*owners,outer_a,outer_b))
    assert reader._closed and all(getattr(reader,name) is None for name in ('_journal','_anchor','_root_lease'))
    assert reader._cic_value is candidate.capture._EMPTY and frames=={}
    if failure is not None:assert 'batch historical cleanup also failed' in primary.__notes__


def test_frozen_teardown_preserves_original_first_cleanup_error_without_primary():
    reader,owners,calls,Owner=reader_with_owners('_journal');outer=Owner('outer')
    frames={0:object()}
    with pytest.raises(RuntimeError,match='named owner close failure'):
        support.close_replay(reader,[outer],frames,True,None)
    assert calls==['_journal','_anchor','_root_lease','outer'] and frames=={}
    assert all(owner.closed for owner in (*owners,outer))


def test_frozen_teardown_does_not_clear_success_frames_and_is_safe_to_repeat():
    reader,owners,calls,Owner=reader_with_owners();frames={0:object()}
    support.close_replay(reader,[],frames,True,None)
    assert 0 in frames and calls==['_journal','_anchor','_root_lease']
    support.close_replay(reader,[],frames,True,None)
    assert calls==['_journal','_anchor','_root_lease']


def test_unsupported_reader_still_closes_outer_leases_and_preserves_primary():
    reader,owners,calls,Owner=reader_with_owners();outer=Owner('outer')
    primary=ValueError('primary failure');frames={0:object()}
    support.close_replay(object(),[outer],frames,False,primary)
    assert outer.closed and calls==['outer'] and frames=={}
    assert 'batch historical cleanup also failed' in primary.__notes__
    support.close_replay(reader,[],{},False,primary)


def parent_namespace(tmp_path):
    root=tmp_path/'controller';parent=root/'source_parent_non_authoritative'
    events=parent/'parent_events_non_authoritative';anchors=parent/'parent_anchor_non_authoritative'
    for directory in (parent,events,anchors,parent/'hour_000_non_authoritative',
                      events/'001',events/'002',root/'clock_bridge_non_authoritative',
                      root/'clock_bridge_non_authoritative/000',root/'job_000_non_authoritative'):
        directory.mkdir(parents=True,exist_ok=True)
    for directory in (parent,events,anchors):
        (directory/'execution.lock').write_bytes(b'0')
    for directory in (events,anchors):(directory/'header.json').write_bytes(b'{}\n')
    for i in range(3):(anchors/f'{i:03d}.json').write_bytes(b'{}\n')
    for i in (1,2):
        for name in ('metadata.bin','payload.bin','commit.json'):(events/f'{i:03d}'/name).write_bytes(b'{}\n')
    (parent/'hour_000_non_authoritative/reference.json').write_bytes(b'{}\n')
    (root/'clock_bridge_non_authoritative/binding.json').write_bytes(b'{}\n')
    for name in ('intent.json','job.json','terminal.json'):
        (root/'clock_bridge_non_authoritative/000'/name).write_bytes(b'{}\n')
    return root,parent,events,anchors


@pytest.mark.parametrize('target',['parent','events','anchors'])
def test_current_known_file_post_observer_misses_extra_name_new_grammar_rejects(tmp_path,monkeypatch,target):
    root,parent,events,anchors=parent_namespace(tmp_path)
    # Only the lease and Job view are stand-ins. Real namespace, stable reads,
    # known-file hashes and original _inventory execute against temporary files.
    class View:
        directory_identity=(1,2);lock_identity=(1,3)
        def __init__(self,path):pass
        def close(self):pass
    monkeypatch.setattr(candidate.history.prior,'ReadView',View)
    monkeypatch.setattr(candidate.base.parent,'job_view',lambda *args:('explicit_job_view_standin',))
    observations={};topology={}
    candidate.prior._observe_prefix(observations,root,1,1)
    support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=topology)
    {'parent':parent,'events':events,'anchors':anchors}[target].joinpath('unexpected.bin').write_bytes(b'fault')
    candidate.prior._observe_prefix(observations,root,1,1)
    with pytest.raises(ValueError,match='unexpected or unbounded historical suffix'):
        support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=topology)


def test_parent_namespace_retains_valid_interrupted_future_suffix(tmp_path):
    root,parent,events,anchors=parent_namespace(tmp_path);seen={}
    support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=seen)
    (parent/'hour_001_non_authoritative').mkdir();(events/'003').mkdir()
    (anchors/'003.json').write_bytes(b'{}\n')
    support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=seen)


@pytest.mark.parametrize('target',['parent','events','anchors'])
def test_parent_namespace_rejects_observed_entry_replacement(tmp_path,target):
    root,parent,events,anchors=parent_namespace(tmp_path);seen={}
    support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=seen)
    path={'parent':parent/'hour_000_non_authoritative','events':events/'001','anchors':anchors/'001.json'}[target]
    path.rename(tmp_path/'preserved_old_entry')
    if target=='anchors':path.write_bytes(b'{}\n')
    else:path.mkdir()
    with pytest.raises(ValueError,match='removed or replaced'):
        support.observe_parent_names(parent,completed_hours=1,declared_hours=192,retained=seen)
