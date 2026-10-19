"""Fabricated direct adapter, real full selector capture and replay; no native."""
from copy import copy
from dataclasses import replace
from functools import lru_cache
import json
import pickle

import pytest

from experiments import h1_owned_selector_sequence_development_v1 as m
from tests import test_h1_selector_raw_science_development_v1 as producer
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture
def factory(tmp_path,monkeypatch,no_solver):
    # Only unchanged dependency hashing is cached. All model, capture, canonical
    # objective, physical and saved-record checks remain the production functions.
    physical=m.selection.physical.implementation_identity()
    monkeypatch.setattr(m.selection.physical,'implementation_identity',lambda:physical)
    monkeypatch.setattr(m.selection,'implementation_identity',lru_cache(None)(m.selection.implementation_identity))
    for module in (m.stage,m.bridge,m.configuration_api):
        pin=module.implementation_identity()
        monkeypatch.setattr(module,'implementation_identity',lambda pin=pin:pin)
    real=m.bridge._run_stage;calls=[]
    def build(lane=producer.fixtures.R,fault=None,return_fault=None,multi=False,fault_index=0):
        f,d,b,args=producer.inputs(lane)
        if multi:
            from tests.test_rq2_normal_h1_source_v1 import packet,fixture
            data=fixture(1).data
            g2=replace(data.generators[0],uid='G2',enabled=False,dispatch_mode='disabled',disabled_reason='synthetic_disabled')
            row=replace(data.hourly_points[0],generator_min_mw={'G1':10.,'G2':0.},
                generator_max_mw={'G1':100.,'G2':0.})
            data=replace(data,generators=(*data.generators,g2),hourly_points=(row,))
            p=packet(data,raw_workload='0.1')
            after=m.selection.physical._owned(type(p.before),network_identity=p.network.identity,completed_hours=1,
                units=(('G1',True,45.,1),('G2',False,0.,0)),
                evidence_role='numerical_lex_candidate')
            f=m.selection.physical._frame(p,after)
            b=m.selection.initialize_development_selection(f,b.physical_carry.disclosure,lane=lane,
                selector=args['selector'],specification=args['specification'],limits=args['limits'],chronology_origin=True)
        count=len(m.selection.stage_labels(f,lane))
        budget=m.configuration_api.process.TaskProcessBudget(300,.05,512*1024**2,768*1024**2,2)
        config=m.configuration_api.SelectorRunConfiguration(f.normal_network_identity,
            tuple(g.uid for g in f.info.network.units),producer.fixtures.old.REF,producer.fixtures.old.ACT,
            args['specification'],args['limits'],budget,budget,2,2)
        root=tmp_path/(str(len(calls))+'_'+lane.role+'_non_authoritative')
        def run(path,*context,**kw):
            calls.append(str(path))
            with monkeypatch.context() as patch:
                instances=producer.install(patch,path,lane,fault if int(path.name)==fault_index else None)
                result=real(path,*context,**kw)
                assert instances[0].apply_calls==instances[0].close_calls==1
            if return_fault:result=return_fault(result,path)
            return result
        monkeypatch.setattr(m.bridge,'_run_stage',run)
        kw=dict(max_archive_bytes=2**30,run_configuration=config,**args)
        return root,(f,d,b),kw,calls,count
    return build


@pytest.mark.parametrize('lane',[producer.fixtures.R,producer.fixtures.A])
def test_complete_sequence_and_live_receipt(factory,lane):
    root,context,kw,calls,count=factory(lane)
    owner=m.OwnedSelectorSequence(root,*context,**kw);receipt=owner.run()
    assert len(calls)==count and owner.complete and not owner.poisoned
    checked=owner.validate_completion(receipt)
    assert checked['replay'].next_candidate is not None and len(receipt.records)==count
    assert checked['replay'].canonical_lock_hex==tuple(float(v).hex() for v in (
        (15,15,30) if lane.role=='Rref' else (20,25)))
    assert all(checked[k] is False for k in m.FLAGS)
    assert not checked['owned_run_return_observed']
    for i in range(count):
        commit=json.loads((root/'commits'/f'{i:04d}.json').read_bytes())
        assert commit['prefix_record_sha256']==[m.io.digest(r) for r in receipt.records[:i]]
        assert commit['selector_chain_complete']==(i==count-1)
    detached=m.inspect(root,*context,expected_terminal_sha256=receipt.terminal_sha256,**kw)
    assert detached['records']==receipt.records
    with pytest.raises(TypeError):m.SequenceCompletion(root,'0'*64,'1'*64,())
    for operation in (copy,pickle.dumps):
        with pytest.raises(TypeError):operation(owner)
    with pytest.raises(ValueError,match='consumed'):owner.run()
    assert len(calls)==count


@pytest.mark.parametrize('fault',['negative','postsolve','close'])
def test_failed_stage_preserved_and_no_retry(factory,fault):
    root,context,kw,calls,_=factory(fault=fault);owner=m.OwnedSelectorSequence(root,*context,**kw)
    with pytest.raises((ValueError,RuntimeError)):owner.run()
    assert owner.poisoned and not owner.complete and len(calls)==1
    assert (root/'stages/0000/capture/native_raw/000/raw.bin').exists()
    assert not (root/'terminal.json').exists() and not list((root/'commits').iterdir())
    with pytest.raises(ValueError):owner.run()
    with pytest.raises(FileExistsError):m.OwnedSelectorSequence(root,*context,**kw)
    assert len(calls)==1


@pytest.mark.parametrize('field',['lock_hex','selector_record','selector_chain_complete','native_sha256'])
def test_return_body_never_substitutes_fresh_inspection(factory,field):
    def change(result,path):
        result[field]={'lock_hex':(999.).hex(),'selector_record':b'{}','selector_chain_complete':True,
                      'native_sha256':'e'*64}[field]
        return result
    root,context,kw,calls,_=factory(return_fault=change);owner=m.OwnedSelectorSequence(root,*context,**kw)
    with pytest.raises(ValueError,match='return differs'):owner.run()
    assert (root/'stages/0000/terminal.json').exists() and not (root/'terminal.json').exists()
    assert owner.poisoned and len(calls)==1


@pytest.mark.parametrize('change',['archive','network','uid','power'])
def test_admission_before_directory(factory,change):
    root,context,kw,calls,_=factory(producer.fixtures.A)
    if change=='archive':kw['max_archive_bytes']=1
    elif change=='network':kw['run_configuration']=replace(kw['run_configuration'],network_sha256='a'*64)
    elif change=='uid':kw['run_configuration']=replace(kw['run_configuration'],generation_uids=('G2',))
    else:kw['power']=None
    with pytest.raises(ValueError):m.OwnedSelectorSequence(root,*context,**kw)
    assert not root.exists() and calls==[]


@pytest.mark.parametrize('lane',[producer.fixtures.R,producer.fixtures.A])
def test_complete_sorted_inventory_includes_disabled_generator(factory,lane):
    root,context,kw,calls,count=factory(lane,multi=True)
    owner=m.OwnedSelectorSequence(root,*context,**kw);receipt=owner.run()
    report=owner.validate_completion(receipt)
    assert count==(4 if lane.role=='Rref' else 3) and len(calls)==count
    assert dict(report['replay'].next_candidate.physical_carry.generation_mw)['G2']==0.
    assert json.loads((root/'commits'/f'{count-1:04d}.json').read_bytes())['label']=='generation:G2'
    assert report['replay'].canonical_lock_hex[-1]==(0.).hex()


@pytest.mark.parametrize('mutation',['runner','reader','nonce','config','guard'])
def test_live_callback_mutation_rejected_before_commit(factory,monkeypatch,mutation):
    holder=[]
    def change(result,path):
        owner=holder[0]
        if mutation=='runner':
            owner._runner=lambda *a,**k:result
            monkeypatch.setattr(m.bridge,'_run_stage',owner._runner)
        elif mutation=='reader':
            owner._reader=lambda *a,**k:{}
            monkeypatch.setattr(m.stage,'inspect',owner._reader)
        elif mutation=='nonce':owner._nonce=object()
        elif mutation=='config':
            owner.run_configuration=replace(owner.run_configuration,actual_non_solver_seconds=3)
        else:
            from threading import Lock
            owner._operation=Lock()
        return result
    root,context,kw,calls,_=factory(return_fault=change)
    owner=m.OwnedSelectorSequence(root,*context,**kw);holder.append(owner)
    with pytest.raises(ValueError):owner.run()
    assert owner.poisoned and len(calls)==1 and not list((root/'commits').iterdir())


def test_stage_terminal_then_exception_is_not_a_completion(factory):
    def fail(result,path):raise RuntimeError('after stage terminal')
    root,context,kw,calls,_=factory(return_fault=fail);owner=m.OwnedSelectorSequence(root,*context,**kw)
    with pytest.raises(RuntimeError,match='after stage'):owner.run()
    assert (root/'stages/0000/terminal.json').exists() and not (root/'terminal.json').exists()
    assert owner._receipt is None and owner.poisoned


@pytest.mark.parametrize('mutation',['receipt','nonce','copied_receipt','thread'])
def test_completion_requires_exact_live_return(factory,mutation):
    root,context,kw,calls,_=factory(producer.fixtures.A)
    owner=m.OwnedSelectorSequence(root,*context,**kw);receipt=owner.run()
    if mutation=='receipt':object.__setattr__(receipt,'request_sha256','e'*64)
    elif mutation=='nonce':owner._nonce=object()
    elif mutation=='copied_receipt':receipt=copy(receipt)
    else:owner._thread=-1
    with pytest.raises(ValueError):owner.validate_completion(receipt)


@pytest.mark.parametrize('mutation',['commit','gap','stage_suffix','root_suffix','terminal','raw','commit_suffix'])
def test_detached_replay_rejects_incomplete_or_changed_archive(factory,mutation):
    root,context,kw,calls,_=factory(producer.fixtures.A)
    owner=m.OwnedSelectorSequence(root,*context,**kw);receipt=owner.run();pin=receipt.terminal_sha256
    if mutation=='commit':
        path=root/'commits/0000.json';value=json.loads(path.read_bytes());value['canonical_lock_hex']=(999.).hex()
        path.write_bytes(m.io.encode(value))
    elif mutation=='gap':(root/'commits/0000.json').rename(root.parent/'retained_commit.json')
    elif mutation=='stage_suffix':(root/'stages/0002').mkdir()
    elif mutation=='root_suffix':(root/'unexpected').write_bytes(b'retained')
    elif mutation=='commit_suffix':(root/'commits/0002.json').write_bytes((root/'commits/0001.json').read_bytes())
    elif mutation=='raw':
        path=root/'stages/0000/capture/native_raw/000/raw.bin';path.write_bytes(path.read_bytes()+b' ')
    else:
        path=root/'terminal.json';value=json.loads(path.read_bytes());value['candidate_identity']='e'*64
        raw=m.io.encode(value);path.write_bytes(raw);pin=m.io.digest(raw)
    with pytest.raises((ValueError,FileNotFoundError)):
        m.inspect(root,*context,expected_terminal_sha256=pin,**kw)
    assert len(calls)==2


def test_reentrant_run_cannot_release_another_stage(factory):
    holder=[]
    def reenter(result,path):
        with pytest.raises(ValueError,match='active'):holder[0].run()
        return result
    root,context,kw,calls,count=factory(return_fault=reenter)
    owner=m.OwnedSelectorSequence(root,*context,**kw);holder.append(owner)
    receipt=owner.run();assert len(calls)==count and owner.validate_completion(receipt)


@pytest.mark.parametrize('change',['shortened','reordered'])
def test_configured_stage_inventory_cannot_be_shortened(factory,monkeypatch,change):
    root,context,kw,calls,_=factory()
    labels=m.selection.stage_labels(context[0],kw['lane'])
    altered=labels[:-1] if change=='shortened' else tuple(reversed(labels))
    monkeypatch.setattr(m.selection,'stage_labels',lambda *a:altered)
    with pytest.raises(ValueError,match='configured selector stage order'):
        m.OwnedSelectorSequence(root,*context,**kw)
    assert not root.exists() and calls==[]


@pytest.mark.parametrize('mutation',['runner','reader','guard'])
def test_prefix_reader_mutation_stops_before_next_stage(factory,monkeypatch,mutation):
    root,context,kw,calls,_=factory();original=m.stage.inspect;holder=[];reads=[];unexpected=[]
    def reader(*args,**kwargs):
        result=original(*args,**kwargs);reads.append(True)
        if len(reads)==2:
            owner=holder[0]
            def forbidden(*a,**k):unexpected.append(True);raise AssertionError('next stage released after drift')
            if mutation=='runner':
                owner._runner=forbidden;monkeypatch.setattr(m.bridge,'_run_stage',forbidden)
            elif mutation=='reader':
                owner._reader=forbidden;monkeypatch.setattr(m.stage,'inspect',forbidden)
            else:
                from threading import Lock
                owner._operation=Lock()
        return result
    monkeypatch.setattr(m.stage,'inspect',reader)
    owner=m.OwnedSelectorSequence(root,*context,**kw);holder.append(owner)
    with pytest.raises(ValueError):owner.run()
    assert owner.poisoned and len(calls)==1 and not unexpected
    assert not (root/'stages/0001').exists() and (root/'commits/0000.json').exists()


@pytest.mark.parametrize('fault',['postsolve','after_terminal'])
def test_second_stage_failure_preserves_first_commit(factory,fault):
    snapshots=[]
    def returned(result,path):
        if path.name=='0000':snapshots.append((path/'terminal.json').read_bytes())
        if path.name=='0001' and fault=='after_terminal':raise RuntimeError('second stage after terminal')
        return result
    root,context,kw,calls,_=factory(fault=None if fault=='after_terminal' else fault,
        return_fault=returned,fault_index=1)
    owner=m.OwnedSelectorSequence(root,*context,**kw)
    with pytest.raises((ValueError,RuntimeError)):owner.run()
    assert owner.poisoned and len(calls)==2
    assert (root/'stages/0000/terminal.json').read_bytes()==snapshots[0]
    assert (root/'commits/0000.json').exists() and not (root/'commits/0001.json').exists()
    assert not (root/'terminal.json').exists()
    with pytest.raises(ValueError):owner.run()
    assert len(calls)==2


@pytest.mark.parametrize('target',['raw','commit'])
def test_later_stage_cannot_change_retained_prefix(factory,target):
    def tamper(result,path):
        if path.name=='0001':
            p=path.parent/'0000/capture/native_raw/000/raw.bin' if target=='raw' else path.parent.parent/'commits/0000.json'
            p.write_bytes(p.read_bytes()+b' ')
        return result
    root,context,kw,calls,_=factory(return_fault=tamper);owner=m.OwnedSelectorSequence(root,*context,**kw)
    with pytest.raises(ValueError,match='prior selector evidence changed'):owner.run()
    assert len(calls)==2 and owner.poisoned and not (root/'commits/0001.json').exists()


def test_exact_logical_archive_envelope_boundary(factory):
    root,context,kw,calls,count=factory()
    caps=m._stage_caps(kw['limits']);assert len(caps)==14
    expected=2*1024**2+count*(1024**2+3*m.io.RAW_CAP+kw['limits'].max_record_bytes+
        m.bridge.science.POST_CAP+9*m.io.META_CAP)
    assert sum(caps.values())==3*m.io.RAW_CAP+kw['limits'].max_record_bytes+m.bridge.science.POST_CAP+9*m.io.META_CAP
    with pytest.raises(ValueError,match='archive envelope'):
        m.OwnedSelectorSequence(root,*context,**(kw|dict(max_archive_bytes=expected-1)))
    assert not root.exists() and calls==[]
    owner=m.OwnedSelectorSequence(root,*context,**(kw|dict(max_archive_bytes=expected)))
    assert root.exists() and not owner.started and calls==[]
