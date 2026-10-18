"""Full scientific sequence and QPC sidecars with fabricated direct adapters."""
from copy import copy,deepcopy
from dataclasses import replace
from functools import lru_cache
import json
import pickle

import pytest

from experiments import h1_timed_selector_sequence_development_v1 as m
from tests import test_h1_selector_raw_science_development_v1 as producer
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture
def factory(tmp_path,monkeypatch,no_solver):
    # Cache only unchanged dependency identity hashing, never model/replay logic.
    physical=m.selection.physical.implementation_identity()
    monkeypatch.setattr(m.selection.physical,'implementation_identity',lambda:physical)
    monkeypatch.setattr(m.selection,'implementation_identity',lru_cache(None)(m.selection.implementation_identity))
    for module in (m.legacy.stage,m.legacy.bridge,m.legacy.configuration_api,m.timed.capture.legacy,m.legacy,m.timed,m.timed.capture):
        pin=module.implementation_identity()
        monkeypatch.setattr(module,'implementation_identity',lambda pin=pin:pin)
    real=m.timed._run_stage;calls=[]
    def build(lane=producer.fixtures.R,*,multi=False,fault=None,fault_index=1,after_stage=None):
        f,d,b,args=producer.inputs(lane)
        if multi:
            from tests.test_rq2_normal_h1_source_v1 import packet,fixture
            data=fixture(1).data
            g2=replace(data.generators[0],uid='G2',enabled=False,dispatch_mode='disabled',disabled_reason='synthetic_disabled')
            row=replace(data.hourly_points[0],generator_min_mw={'G1':10.,'G2':0.},generator_max_mw={'G1':100.,'G2':0.})
            data=replace(data,generators=(*data.generators,g2),hourly_points=(row,))
            p=packet(data,raw_workload='0.1')
            state=m.selection.physical._owned(type(p.before),network_identity=p.network.identity,completed_hours=1,
                units=(('G1',True,45.,1),('G2',False,0.,0)),evidence_role='numerical_lex_candidate')
            f=m.selection.physical._frame(p,state)
            b=m.selection.initialize_development_selection(f,b.physical_carry.disclosure,lane=lane,
                selector=args['selector'],specification=args['specification'],limits=args['limits'],chronology_origin=True)
        budget=m.legacy.configuration_api.process.TaskProcessBudget(300,.05,512*1024**2,768*1024**2,2)
        config=m.legacy.configuration_api.SelectorRunConfiguration(f.normal_network_identity,
            tuple(g.uid for g in f.info.network.units),producer.fixtures.old.REF,producer.fixtures.old.ACT,
            args['specification'],args['limits'],budget,budget,2,2)
        root=tmp_path/(str(len(calls))+'_science_non_authoritative')
        side=tmp_path/(str(len(calls))+'_timing_non_authoritative')
        def run(path,timing,*context,**kw):
            calls.append(str(path));stage_fault=fault if int(path.name)==fault_index else None
            with monkeypatch.context() as patch:
                instances=producer.install(patch,path,lane,stage_fault)
                direct=m.legacy.bridge.capture.GurobiDirect;original=direct._presolve
                def presolve(self,*a,**k):
                    original(self,*a,**k)
                    self._env_options={};self._version_major=12;self._suffixes=();self._needs_updated=True
                    self.native.setParam=lambda *a:None
                    def optimize(callback):
                        assert callback is None and (timing/'native/intent.json').exists()
                        assert (path/'capture/native_raw/000/intent.json').exists()
                        assert not (path/'capture/native_raw/000/raw.bin').exists()
                        self.apply_calls+=1
                        if stage_fault=='optimize':raise RuntimeError('synthetic optimize failure')
                    self.native.optimize=optimize
                patch.setattr(direct,'_presolve',presolve)
                patch.setattr(m.timed.capture,'GurobiDirect',direct)
                patch.setattr(m.timed.capture.timing,'GurobiDirect',direct)
                result=real(path,timing,*context,**kw)
                assert instances[0].apply_calls==instances[0].close_calls==1
            if after_stage:result=after_stage(result,path,timing)
            return result
        monkeypatch.setattr(m.timed,'_run_stage',run)
        kw=dict(max_archive_bytes=2**30,max_timing_archive_bytes=2**28,run_configuration=config,**args)
        return root,side,(f,d,b),kw,calls
    return build


def owner(c):return m.OwnedTimedSelectorSequence(c[0],c[1],*c[2],**c[3])


def replay(c,pin):return m.inspect(c[0],c[1],*c[2],expected_terminal_sha256=pin,**c[3])


@pytest.mark.parametrize('lane',[producer.fixtures.R,producer.fixtures.A])
@pytest.mark.parametrize('multi',[False,True])
def test_complete_both_lanes_and_all_uids(factory,lane,multi):
    c=factory(lane,multi=multi);o=owner(c);receipt=o.run();result=o.validate_completion(receipt)
    count=len(m.selection.stage_labels(c[2][0],lane))
    assert len(c[4])==len(receipt.records)==len(result['stage_vector'])==count
    kw={k:v for k,v in c[3].items() if k!='max_timing_archive_bytes'}
    old=m.legacy.inspect(c[0],*c[2],expected_terminal_sha256=receipt.scientific_terminal_sha256,**kw)
    assert old==result['science'] and old['replay'].next_candidate is not None
    oracle=(15,15,30) if lane.role=='Rref' else (20,25)
    if multi:oracle+= (0,)
    assert old['replay'].canonical_lock_hex==tuple(float(v).hex() for v in oracle)
    assert type(receipt) is m.TimedSequenceCompletion and not isinstance(receipt,m.legacy.SequenceCompletion)
    assert all(result[k] is False for k in m.FLAGS)
    vector=result['stage_vector']
    assert result['native_interval_ns']==sum(v['native_interval_ns'] for v in vector)<=result['sequence_window_ns']
    assert all(a['stage_end_ns']<=b['stage_start_ns'] for a,b in zip(vector,vector[1:]))
    if multi:assert old['replay'].canonical_lock_hex[-1]==(0.).hex()
    with pytest.raises(TypeError):m.TimedSequenceCompletion(c[0],c[1],result)
    for operation in (copy,pickle.dumps):
        with pytest.raises(TypeError):operation(o)
    with pytest.raises(ValueError,match='consumed'):o.run()
    assert len(c[4])==count


@pytest.mark.parametrize('fault',['optimize','postsolve','negative','close'])
def test_second_stage_failure_retains_paired_prefix(factory,fault):
    c=factory(fault=fault);o=owner(c)
    with pytest.raises((ValueError,RuntimeError)):o.run()
    assert len(c[4])==2 and o.poisoned and not o.complete and o._receipt is None
    assert (c[0]/'stages/0001/capture/native_raw/000/raw.bin').exists()
    for root in c[:2]:
        assert {p.name for p in (root/'commits').iterdir()}=={'0000.json'}
        assert not (root/'terminal.json').exists()
    with pytest.raises(ValueError):o.run()
    with pytest.raises(FileExistsError):owner(c)


@pytest.mark.parametrize('target',['science_commit','timing_commit','science_terminal','timing_terminal'])
@pytest.mark.parametrize('after',[False,True])
def test_dual_journal_write_failure_no_resume(factory,monkeypatch,target,after):
    c=factory(producer.fixtures.A);o=owner(c);original=m.legacy._write
    path=(c[0] if target.startswith('science') else c[1])/('commits/0000.json' if target.endswith('commit') else 'terminal.json')
    def fail(p,value):
        if p==path:
            if after:original(p,value)
            raise OSError('synthetic sequence publication failure')
        return original(p,value)
    monkeypatch.setattr(m.legacy,'_write',fail)
    with pytest.raises(OSError):o.run()
    assert path.exists()==after and o.poisoned and not o.complete and o._receipt is None
    assert (c[0]/'stages/0000/capture/native_raw/000/raw.bin').exists()
    with pytest.raises(ValueError):o.run()
    with pytest.raises(FileExistsError):owner(c)
    assert len(c[4])==(1 if target.endswith('commit') else 2)


@pytest.mark.parametrize('kind',['timing_cap','science_cap','nested'])
def test_admission_before_mkdir(factory,kind):
    c=list(factory())
    if kind=='timing_cap':
        cfg=m._configuration(c[2],{k:v for k,v in c[3].items() if k not in ('max_archive_bytes','max_timing_archive_bytes','run_configuration')},
            c[3]['max_archive_bytes'],c[3]['max_timing_archive_bytes'],c[3]['run_configuration'])
        c[3]['max_timing_archive_bytes']=cfg['required_timing_archive_bytes']-1
    elif kind=='science_cap':c[3]['max_archive_bytes']=1
    else:c[1]=c[0]/'timing'
    with pytest.raises(ValueError):owner(c)
    assert not c[0].exists() and not c[1].exists() and not c[4]


@pytest.mark.parametrize('mutation',['runner','reader','legacy_reader','nonce','guard','config','prior_science','prior_timing','returned'])
def test_midstage_mutation_stops_next_commit(factory,monkeypatch,mutation):
    holder=[]
    def change(result,path,side):
        o=holder[0]
        if mutation.startswith('prior_'):
            if path.name=='0000':return result
            target=(o.root if mutation=='prior_science' else o.side)/'commits/0000.json'
            target.write_bytes(target.read_bytes()+b' ')
        elif mutation=='runner':monkeypatch.setattr(m.timed,'_run_stage',lambda *a,**k:result)
        elif mutation=='reader':monkeypatch.setattr(m.timed,'inspect',lambda *a,**k:result)
        elif mutation=='legacy_reader':monkeypatch.setattr(m.legacy,'_replay',lambda *a,**k:{})
        elif mutation=='nonce':o._nonce=object()
        elif mutation=='guard':
            from threading import Lock
            o._operation=Lock()
        elif mutation=='config':o.run_configuration=replace(o.run_configuration,actual_non_solver_seconds=3)
        else:result['native_interval_ns']+=1
        return result
    c=factory(after_stage=change);o=owner(c);holder.append(o)
    with pytest.raises(ValueError):o.run()
    assert o.poisoned and o._receipt is None and len(c[4])==(2 if mutation.startswith('prior_') else 1)
    assert not (c[1]/'terminal.json').exists()


@pytest.mark.parametrize('mutation',['copy','nonce','thread','receipt'])
def test_live_receipt_cannot_be_recreated(factory,mutation):
    c=factory(producer.fixtures.A);o=owner(c);r=o.run()
    if mutation=='copy':r=copy(r)
    elif mutation=='nonce':o._nonce=object()
    elif mutation=='thread':o._thread=-1
    else:object.__setattr__(r,'request_sha256','0'*64)
    with pytest.raises(ValueError):o.validate_completion(r)


@pytest.mark.parametrize('mutation',['timing_extra','science_extra','missing_pair','cross_pin','overlap','owner'])
def test_detached_tamper_rejected(factory,mutation):
    c=factory(producer.fixtures.A);o=owner(c);r=o.run()
    if mutation=='timing_extra':(c[1]/'extra.json').write_bytes(b'{}')
    elif mutation=='science_extra':(c[0]/'extra.json').write_bytes(b'{}')
    elif mutation=='missing_pair':(c[1]/'commits/0001.json').rename(c[1].parent/'retained_unpaired.json')
    else:
        path=c[1]/'commits/0001.json';doc=json.loads(path.read_bytes())
        key={'cross_pin':'scientific_commit_sha256','overlap':'stage_start_ns','owner':'pid'}[mutation]
        doc[key]='0'*64 if mutation=='cross_pin' else 0
        path.write_bytes(m.io.encode(doc))
    with pytest.raises((ValueError,FileNotFoundError)):replay(c,r.terminal_sha256)


def test_valid_stage_with_overlapping_window_cannot_commit(factory):
    def overlap(result,path,side):
        if path.name=='0000':return result
        doc=json.loads((side/'terminal.json').read_bytes());doc['stage_start_ns']=0
        raw=m.io.encode(doc);(side/'terminal.json').write_bytes(raw)
        c=holder[0];records=(c[0]/'stages/0000/selector_record.json').read_bytes(),
        args={k:v for k,v in c[3].items() if k not in ('max_archive_bytes','max_timing_archive_bytes','run_configuration')}
        return m.timed.inspect(path,side,*c[2],records,expected_terminal_sha256=m.io.digest(raw),**args)
    holder=[];c=factory(after_stage=overlap);holder.append(c);o=owner(c)
    with pytest.raises(ValueError,match='chronology'):o.run()
    assert len(c[4])==2 and o.poisoned and (c[0]/'commits/0001.json').exists()
    assert not (c[1]/'commits/0001.json').exists() and not (c[1]/'terminal.json').exists()


def test_science_header_same_bytes_replacement_rejected_before_release(factory):
    c=factory();o=owner(c);path=c[0]/'binding.json';raw=path.read_bytes()
    path.rename(c[0].parent/'retained_science_binding.json');path.write_bytes(raw)
    with pytest.raises(ValueError,match='identity'):o.run()
    assert not c[4] and o.poisoned


def test_exact_timing_payload_cap_and_stage_inventory(factory):
    c=factory();kw=c[3]
    args={k:v for k,v in kw.items() if k not in ('max_archive_bytes','max_timing_archive_bytes','run_configuration')}
    cfg=m._configuration(c[2],args,kw['max_archive_bytes'],kw['max_timing_archive_bytes'],kw['run_configuration'])
    count=len(m.selection.stage_labels(c[2][0],args['lane']))
    assert cfg['required_timing_archive_bytes']==2*m.META_CAP+count*(m.META_CAP+2*m.timed.capture.CAP+4*m.io.META_CAP)
    kw['max_timing_archive_bytes']=cfg['required_timing_archive_bytes']
    o=owner(c);assert o.count==count and not o.started and not c[4]


def test_actual_header_limit_rejected_before_any_directory(factory,monkeypatch):
    c=factory();kw=c[3]
    args={k:v for k,v in kw.items() if k not in ('max_archive_bytes','max_timing_archive_bytes','run_configuration')}
    config=m.legacy._configuration(*c[2],args,kw['max_archive_bytes'],kw['run_configuration'])
    monkeypatch.setattr(m,'META_CAP',len(m.legacy._header(c[0],config,'0'*32)))
    with pytest.raises(ValueError,match='timing header'):owner(c)
    assert not c[0].exists() and not c[1].exists() and not c[4]


def test_initial_snapshot_and_same_byte_replacement_cannot_move_trust(factory):
    c=factory();o=owner(c);path=c[0]/'binding.json';raw=path.read_bytes()
    path.rename(c[0].parent/'retained_original_header.json');path.write_bytes(raw)
    fresh=o._view(0)
    for old,new in ((o._initial_view[0],fresh[0]),(o._initial_view[1],fresh[1])):
        old[0].update(new[0]);old[1].update(new[1])
    assert o._view(0)==o._initial_view
    with pytest.raises(ValueError,match='identity'):o.run()
    assert not c[4] and o.poisoned


def test_final_snapshot_and_same_byte_replacement_cannot_move_trust(factory):
    c=factory(producer.fixtures.A);o=owner(c);r=o.run()
    path=c[1]/'stages/0000/native/intent.json';raw=path.read_bytes()
    path.rename(c[1].parent/'retained_original_intent.json');path.write_bytes(raw)
    o._final_view=o._view(o.count,True,True)
    with pytest.raises(ValueError,match='exact live'):o.validate_completion(r)
    assert o.poisoned


def test_snapshot_digest_binds_paths_caps_bytes_and_full_stamps(tmp_path):
    root=tmp_path/'science';side=tmp_path/'timing'
    path=side/'stages/0000/native/intent.json'
    view=(({'.':(1,2,3,4)},{'binding.json':('a'*64,(1,2,3,4,5),100)}),
        ({'.':(6,7,8,9)},{'binding.json':(b'{}',(6,7,2,9,10))},
         (({side/'stages/0000':(11,12,13,14)},{path:(100,(b'{}',(15,16,2,18,19)))}),)))
    baseline=m._snapshot_pin(view,root,side)
    variants=[]
    v=deepcopy(view);v[0][0]['.']=(1,2,30,4);variants.append(v)
    v=deepcopy(view);v[0][1]['binding.json']=('a'*64,(1,2,3,4,50),100);variants.append(v)
    v=deepcopy(view);v[1][1]['binding.json']=(b'[]',(6,7,2,9,10));variants.append(v)
    v=deepcopy(view);v[1][2][0][0][side/'stages/0000']=(11,120,13,14);variants.append(v)
    v=deepcopy(view);v[1][2][0][1][path]=(101,(b'{}',(15,16,2,18,19)));variants.append(v)
    v=deepcopy(view);v[1][2][0][1][path]=(100,(b'{}',(15,16,2,18,190)));variants.append(v)
    v=deepcopy(view);v[1][2][0][1][path.with_name('other.json')]=v[1][2][0][1].pop(path);variants.append(v)
    assert all(m._snapshot_pin(v,root,side)!=baseline for v in variants)


@pytest.mark.parametrize('identity',[(True,1),(-1,1),(m.ROOT_ID_MAX+1,1)])
def test_directory_identity_has_exact_bounded_representation(tmp_path,identity):
    with pytest.raises(ValueError,match='directory identity'):
        m._header(tmp_path/'science',tmp_path/'timing',{},'0'*64,'0'*32,1,1,0,identity)
