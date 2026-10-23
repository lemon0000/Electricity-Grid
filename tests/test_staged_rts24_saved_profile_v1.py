"""Controller/path faults only; no scientific modules, child or solver execution."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

SOURCE=Path(__file__).resolve().parents[1]/'experiments/staged_rts24_saved_profile_v1.py'


@pytest.fixture
def case(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('profile_under_test',SOURCE)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    root=tmp_path/'repo';root.mkdir();tables=root/'results'/'tables';tables.mkdir(parents=True)
    p1=tables/'p1';p1.mkdir();(p1/'data').write_bytes(b'original')
    start=p1/'start.json';start.write_text(json.dumps({'pins':{'controlled_environment_sha':'env'}}))
    observed=dict(allow_native=False,counts={},inclusive_seconds={},scope='test scope',missing_process_observations='unknown_not_zero')
    (p1/'fresh_observations.json').write_text(json.dumps(observed))
    prior=tables/'prior.json';prior.write_text(json.dumps({'p1_files':{p.name:m.stamp(p) for p in p1.iterdir()}}))
    contract=root/'contract';contract.write_bytes(b'draft contract')
    monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'BASE',tables/'profile')
    monkeypatch.setattr(m,'OUTPUT',m.BASE/'profile_01');monkeypatch.setattr(m,'P1',p1)
    monkeypatch.setattr(m,'PRIOR',prior);monkeypatch.setattr(m,'PRIOR_SHA',m.stamp(prior)['sha256'])
    monkeypatch.setattr(m,'CONTRACT',contract);monkeypatch.chdir(root)
    def supervise(*a,**kw):
        expected=m.read(prior)['p1_files']
        report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
            source_sha=m.stamp(SOURCE)['sha256'],contract_sha=m.stamp(contract)['sha256'],saved_input_sha=m.PRIOR_SHA,
            saved_files_checked=len(expected),saved_bytes_checked=sum(p['bytes'] for p in expected.values()),
            science_metrics_match=True,P1_bytes_unchanged=True,solver_calls=0,new_models=0,
            instrumentation_scope='setup/import/checks outside the two profiles remain in Job wall; profiling is not a speed comparison',
            C_overall_performance_review_complete=False,full_139_executed=False,fx_temporal_backing=False,
            one_profiled_fingerprint_seconds=0.1,one_profiled_reopen_seconds=0.2)
        m.save(m.OUTPUT/'report.json',report);m.save(m.OUTPUT/'observations.json',observed)
        for name in ('worker.stdout.log','worker.stderr.log','events.jsonl','fingerprints.prof','reopen.prof'):
            (m.OUTPUT/name).write_bytes(b'test artifact')
        for label,wall in [('fingerprints',0.1),('reopen',0.2)]:
            row=dict(file='test',line=1,function='test',primitive_calls=1,calls=1,self_seconds=0.01,cumulative_seconds=0.02)
            m.save(m.OUTPUT/(label+'_stats.json'),dict(profiled_wall_seconds=wall,function_count=1,top_self=[row],top_cumulative=[row],
                scope='one profiled call; cumulative times overlap; instrumentation changes timing'))
        return dict(exit_code=0,job_quiet_confirmed=True,stop_reason=None)
    guard=SimpleNamespace(supervise=supervise,controlled_environment=lambda:{})
    core=SimpleNamespace(digest=lambda value:'env')
    import src
    monkeypatch.setitem(sys.modules,'src.staged_rts24_process_guard_v1',guard)
    monkeypatch.setitem(sys.modules,'src.staged_rts24_development_v1',core)
    monkeypatch.setattr(src,'staged_rts24_process_guard_v1',guard,raising=False)
    monkeypatch.setattr(src,'staged_rts24_development_v1',core,raising=False)
    return m,guard


def test_postquiet_validates_success_and_refuses_reuse(case):
    m,_=case
    assert m.launch()==0
    assert m.read(m.OUTPUT/'postquiet.json')['P1_bytes_rechecked_after_quiet'] is True
    with pytest.raises(FileExistsError):m.launch()


def test_P1_drift_after_worker_report_before_quiet_is_refused(case):
    m,guard=case;original=guard.supervise
    def drift(*a,**kw):
        result=original(*a,**kw);(m.P1/'data').write_bytes(b'changed after worker');return result
    guard.supervise=drift
    assert m.launch()==1
    assert m.read(m.OUTPUT/'adoption_failure.json')['accepted_success'] is False
    assert not (m.OUTPUT/'postquiet.json').exists()


@pytest.mark.parametrize('missing',['report.json','observations.json','fingerprints.prof','reopen_stats.json'])
def test_missing_terminal_output_is_not_success(case,missing):
    m,guard=case;original=guard.supervise
    def missing_output(*a,**kw):
        result=original(*a,**kw);(m.OUTPUT/missing).unlink();return result
    guard.supervise=missing_output
    assert m.launch()==1


@pytest.mark.parametrize('field,value',[
    ('formal_result',True),('resource_admission',True),('saved_files_checked',999),
    ('new_field',False),('one_profiled_reopen_seconds',float('nan')),
    ('observations/native_call_returned',1),('observations/replay/publication_returned',1),
    ('observations/unknown_counter',0)])
def test_terminal_claim_or_counter_drift_is_refused(case,field,value):
    m,guard=case;original=guard.supervise
    def drift(*a,**kw):
        result=original(*a,**kw)
        name='observations.json' if field.startswith('observations/') else 'report.json'
        path=m.OUTPUT/name;body=m.read(path)
        if name=='observations.json':body['counts'][field.removeprefix('observations/')]=value
        else:body[field]=value
        path.write_text(json.dumps(body))
        return result
    guard.supervise=drift
    assert m.launch()==1
    assert not (m.OUTPUT/'postquiet.json').exists()


@pytest.mark.parametrize('fault',['extra','reparse','stats_wall','empty_profile'])
def test_profile_output_fault_is_refused(case,monkeypatch,fault):
    m,guard=case;original=guard.supervise
    def drift(*a,**kw):
        result=original(*a,**kw)
        if fault=='extra':(m.OUTPUT/'unexpected').write_bytes(b'extra')
        elif fault=='reparse':mark_reparse(monkeypatch,m.OUTPUT/'report.json')
        else:
            path=m.OUTPUT/'reopen_stats.json';body=m.read(path)
            if fault=='stats_wall':body['profiled_wall_seconds']=10
            else:body.update(function_count=0,top_self=[],top_cumulative=[])
            path.write_text(json.dumps(body))
        return result
    guard.supervise=drift
    assert m.launch()==1
    assert not (m.OUTPUT/'postquiet.json').exists()


def test_real_cprofile_serialization_and_stats_validation(case,tmp_path,monkeypatch):
    m,_=case;output=tmp_path/'plain_profile';output.mkdir();monkeypatch.setattr(m,'OUTPUT',output)
    result,wall=m.profiled('sample',lambda:sum(range(10)))
    assert result==45
    m.validate_profile_stats('sample',wall)
    assert (output/'sample.prof').stat().st_size>0
    assert m.read(output/'sample_stats.json')['function_count']>0


def mark_reparse(monkeypatch,path):
    original=Path.lstat
    def lstat(self,*a,**kw):
        info=original(self,*a,**kw)
        if self==path:
            return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400)
        return info
    monkeypatch.setattr(Path,'lstat',lstat)


def test_existing_output_base_reparse_is_refused(case,monkeypatch):
    m,_=case;m.BASE.mkdir();mark_reparse(monkeypatch,m.BASE)
    with pytest.raises(ValueError,match='nonordinary directory'):m.launch()
    assert not m.OUTPUT.exists()


def test_input_descendant_directory_reparse_is_refused(case,monkeypatch):
    m,_=case;directory=m.P1/'junction';directory.mkdir();mark_reparse(monkeypatch,directory)
    with pytest.raises(ValueError,match='reparse input'):m.check_p1(m.read(m.PRIOR)['p1_files'])
