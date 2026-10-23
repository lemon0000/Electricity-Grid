"""Input-cost plumbing with tiny functions/temp outputs, never public target runs."""
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType,SimpleNamespace

import pytest

from experiments import staged_rts24_p2_input_cost_v1 as d


@pytest.fixture
def case(tmp_path,monkeypatch):
    output=tmp_path/'measure';output.mkdir()
    monkeypatch.setattr(d,'OUTPUT',output)
    expected={n:{'ordinary':n} for n in d.LABELS};sources={'ordinary':dict(bytes=1,sha256='a'*64)}
    monkeypatch.setattr(d,'warm_imports',lambda:None)
    monkeypatch.setattr(d,'input_check',lambda:None)
    monkeypatch.setattr(d,'source_pins',lambda:sources)
    monkeypatch.setattr(d,'expected_values',lambda:expected)
    monkeypatch.setattr(d,'runtime_snapshot',lambda:({'ordinary_runtime':'fixed','loaded_module_names':sorted(sys.modules)},{}))
    monkeypatch.setattr(d,'runtime_unchanged',lambda before,refs,modules:before)
    monkeypatch.setattr(d,'forbidden_labels',lambda:['ordinary_solver'])
    counts={n:0 for n in d.LABELS};restored=[]
    def fingerprints():counts['fingerprints']+=1;return expected['fingerprints']
    def packet(*,validate):assert validate is False;counts['packet']+=1;return expected['packet']
    def preserve():counts['preserve']+=1;return expected['preserve']
    monkeypatch.setattr(d.p2,'fingerprints',fingerprints);monkeypatch.setattr(d.p2,'load_packet',packet)
    monkeypatch.setattr(d.p2,'preserve',preserve)
    class FakeDeny:
        def __init__(self):self.calls={'ordinary_solver':0}
        def install(self):pass
        def check(self):pass
        def restore(self):restored.append(True)
    monkeypatch.setattr(d,'Deny',FakeDeny)
    start=dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,limits=d.LIMITS,
        fixed_target_calls={n:1 for n in d.LABELS},forbidden_labels=['ordinary_solver'],native_authorized=False)
    d.save(output/'start.json',start)
    for n in ('worker.stdout.log','worker.stderr.log'):(output/n).write_bytes(b'')
    return SimpleNamespace(output=output,start=start,start_sha=d.stamp(output/'start.json')['sha256'],counts=counts,restored=restored)


def test_three_tiny_calls_profile_separately_and_adopt_only_exact_outputs(case):
    assert d.worker(case.start_sha)==0 and case.counts=={n:1 for n in d.LABELS} and case.restored==[True]
    adopted=d.adopt(case.start,case.start_sha)
    assert set(adopted['output_pins'])==d.REQUIRED
    for n in d.LABELS:
        stats=d.read(case.output/(n+'_stats.json'))
        assert stats['target_calls']==stats['target_primitive_calls']==1 and stats['function_count']>0


@pytest.mark.parametrize('fault',['result','target_exception','source','runtime','install'])
def test_worker_fault_restores_guards_and_never_publishes_report(case,monkeypatch,fault):
    if fault=='result':monkeypatch.setattr(d.p2,'fingerprints',lambda:{'wrong':'result'})
    elif fault=='target_exception':
        def failed():raise OSError('ordinary target failure')
        monkeypatch.setattr(d.p2,'fingerprints',failed)
    elif fault=='source':
        def sources():return case.start['source_pins'] if not case.restored else {'changed':True}
        monkeypatch.setattr(d,'source_pins',sources)
    elif fault=='runtime':monkeypatch.setattr(d,'runtime_unchanged',lambda *a:(_ for _ in ()).throw(ValueError('runtime drift')))
    else:monkeypatch.setattr(d.Deny,'install',lambda self:(_ for _ in ()).throw(ValueError('install failed')))
    with pytest.raises((ValueError,OSError)):d.worker(case.start_sha)
    assert case.restored==[True] and not (case.output/'report.json').exists()


@pytest.mark.parametrize('fault',['extra','report_flag','result','profile','stats','runtime','source','missing_guard'])
def test_postquiet_adoption_rejects_saved_drift(case,monkeypatch,fault):
    d.worker(case.start_sha)
    if fault=='extra':(case.output/'extra').write_bytes(b'x')
    elif fault=='source':monkeypatch.setattr(d,'source_pins',lambda:{'changed':True})
    elif fault=='profile':(case.output/'packet.prof').write_bytes(b'not a profile')
    else:
        filename={'stats':'packet_stats.json','runtime':'runtime_after.json','missing_guard':'observations.json'}.get(fault,'report.json')
        value=d.read(case.output/filename)
        if fault=='report_flag':value['native_authorized']=0
        elif fault=='result':value['result_shas']['packet']='0'*64
        elif fault=='stats':value['target_calls']=2
        elif fault=='runtime':value['ordinary_runtime']='changed'
        else:value['forbidden_calls']={}
        (case.output/filename).write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises((ValueError,EOFError,TypeError)):d.adopt(case.start,case.start_sha)


def test_guard_blocks_direct_and_imported_aliases_and_restores(monkeypatch):
    module=ModuleType('ordinary_cost_guard');alias=ModuleType('ordinary_cost_alias')
    def construct():return 'original'
    module.construct=construct;alias.imported=construct
    monkeypatch.setitem(sys.modules,module.__name__,module);monkeypatch.setitem(sys.modules,alias.__name__,alias)
    monkeypatch.setattr(d,'deny_targets',lambda:[(module,'construct')])
    guard=d.Deny();guard.install()
    try:
        for fn in (module.construct,alias.imported):
            with pytest.raises(RuntimeError,match='forbidden'):fn()
        with pytest.raises(ValueError):guard.check()
    finally:guard.restore()
    assert module.construct is alias.imported is construct and sum(guard.calls.values())==2


@pytest.mark.parametrize('fault',['delete','add','reorder','repeat'])
def test_adoption_rejects_module_inventory_corruption(case,fault):
    d.worker(case.start_sha);path=case.output/'observations.json';value=d.read(path);names=value['loaded_module_names']
    if fault=='delete':names.pop()
    elif fault=='add':names.append('foreign_cost_module');names.sort()
    elif fault=='reorder':names.reverse()
    else:names.append(names[-1])
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='module inventory'):d.adopt(case.start,case.start_sha)


@pytest.mark.parametrize('fault',['empty','prefix','missing','order','label','field'])
def test_adoption_rejects_event_corruption(case,fault):
    d.worker(case.start_sha);path=case.output/'events.jsonl';events=[json.loads(v) for v in path.read_bytes().splitlines()]
    if fault=='empty':events=[]
    elif fault=='prefix':events.insert(0,dict(stage='foreign'))
    elif fault=='missing':events.pop(2)
    elif fault=='order':events[1],events[2]=events[2],events[1]
    elif fault=='label':events[1]['label']='preserve'
    else:events[-1]['extra']=True
    path.write_text(''.join(json.dumps(v)+'\n' for v in events),encoding='utf-8')
    with pytest.raises(ValueError,match='event sequence'):d.adopt(case.start,case.start_sha)


def test_worker_rejects_foreign_event_prefix(case):
    (case.output/'events.jsonl').write_bytes(b'foreign\n')
    with pytest.raises(FileExistsError):d.worker(case.start_sha)
    assert not any(case.counts.values()) and not (case.output/'report.json').exists()


def test_target_exception_survives_cleanup_exception(case,monkeypatch):
    def failed():raise OSError('primary failure')
    def cleanup(self):raise RuntimeError('cleanup failure')
    monkeypatch.setattr(d.p2,'fingerprints',failed);monkeypatch.setattr(d.Deny,'restore',cleanup)
    with pytest.raises(OSError,match='primary'):d.worker(case.start_sha)
    assert d.read(case.output/'guard_cleanup_failure.json')['message']=='cleanup failure'
    assert not (case.output/'report.json').exists()


def test_adoption_binds_original_profile_target(case):
    d.worker(case.start_sha);path=case.output/'packet_stats.json';stats=d.read(path)
    stats['target']['name']='another_target';path.write_text(json.dumps(stats),encoding='utf-8')
    with pytest.raises(ValueError,match='target identity'):d.adopt(case.start,case.start_sha)


def test_real_fresh_setup_and_guard_bookends_without_target_calls():
    code="from experiments import staged_rts24_p2_input_cost_v1 as d; d.warm_imports(); d.forbidden_labels(); before,refs=d.runtime_snapshot(); modules=dict(d.sys.modules); d.importlib.import_module('pypower.case24_ieee_rts'); guard=d.Deny(); guard.install(); guard.check(); guard.restore(); d.runtime_unchanged(before,refs,modules); print('setup_and_guard_bookends_only')"
    result=subprocess.run([sys.executable,'-B','-s','-c',code],cwd=d.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    assert result.stdout.strip()==b'setup_and_guard_bookends_only' and not d.OUTPUT.exists()


def test_guard_detach_is_rejected_but_original_alias_still_restored(monkeypatch):
    module=ModuleType('ordinary_detach_guard');original=lambda:None;module.call=original
    monkeypatch.setitem(sys.modules,module.__name__,module);monkeypatch.setattr(d,'deny_targets',lambda:[(module,'call')])
    guard=d.Deny();guard.install();module.call=lambda:None
    with pytest.raises(ValueError,match='detached'):guard.check()
    with pytest.raises(ValueError,match='restoration'):guard.restore()
    assert module.call is original


@pytest.mark.parametrize('quiet',[False,True])
def test_launcher_does_not_adopt_unknown_or_failed_worker(tmp_path,monkeypatch,quiet):
    output=tmp_path/'measure';monkeypatch.setattr(d,'BASE',tmp_path);monkeypatch.setattr(d,'OUTPUT',output)
    monkeypatch.setattr(d.p2.p1,'require_compute',lambda:None)
    monkeypatch.setattr(d,'warm_imports',lambda:None);monkeypatch.setattr(d,'input_check',lambda:None)
    monkeypatch.setattr(d,'source_pins',lambda:{})
    monkeypatch.setattr(d,'forbidden_labels',lambda:['ordinary'])
    monkeypatch.setattr(d,'controlled_environment',lambda:{})
    read=d.read
    monkeypatch.setattr(d,'read',lambda p:{'pins':{'controlled_environment_sha':d.digest({})}} if p==d.p2.saved.P1/'start.json' else read(p))
    monkeypatch.setattr(d,'supervise',lambda *a,**k:dict(exit_code=2 if quiet else None,stop_reason='ordinary failure',job_quiet_confirmed=quiet))
    monkeypatch.setattr(d,'adopt',lambda *a:pytest.fail('adoption after failed/unknown worker'))
    assert d.launch()==1 and (output/'adoption_failure.json').exists()
    with pytest.raises(FileExistsError):d.launch()


def test_default_cli_never_creates_measurement():
    script=Path(d.__file__)
    result=subprocess.run([sys.executable,'-B','-s',str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    assert result.returncode==2 and not d.OUTPUT.exists()
