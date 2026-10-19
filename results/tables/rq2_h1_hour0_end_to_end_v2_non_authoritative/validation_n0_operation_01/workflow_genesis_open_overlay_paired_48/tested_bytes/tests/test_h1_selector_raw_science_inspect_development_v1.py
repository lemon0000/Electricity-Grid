"""Synthetic stored captures only; the reader is forbidden from solving."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from experiments import h1_selector_raw_science_inspect_development_v1 as m
from tests import test_h1_selector_raw_science_development_v1 as producer
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture(scope='module')
def captures(tmp_path_factory):
    base=tmp_path_factory.mktemp('selector_inspect_samples');out=[]
    # Closed guard plus an explicit fabricated direct adapter; no native object
    # or Job is instantiated to prepare these test-only persistence samples.
    with m.bridge.science.prior.guard.solver_calls_forbidden():
        for lane in (producer.fixtures.R,producer.fixtures.A):
            f,d,b,args=producer.inputs(lane);records=()
            for i in range(len(m.bridge.selector.stage_labels(f,lane))):
                path=base/(lane.role+str(i))
                with pytest.MonkeyPatch.context() as patch:
                    producer.install(patch,path,lane)
                    result=m.bridge._run_stage(path,f,d,b,records,
                        expected_key=m.bridge.request_key(f,d,b,records,**args),**args)
                out.append((path,f,d,b,args,records,result['bridge_terminal_sha256']))
                records+=(result['selector_record'],)
    return out


def call(sample,path=None,pin=None,records=None):
    original,f,d,b,args,prior,sha=sample
    return m.inspect(original if path is None else path,f,d,b,prior if records is None else records,
        expected_terminal_sha256=sha if pin is None else pin,**args)


def copy_sample(tmp_path,captures,index=0):
    sample=captures[index];path=tmp_path/'copy'
    shutil.copytree(sample[0],path)
    return sample,path


def test_both_lanes_and_complete_prefixes(captures,no_solver):
    for i,sample in enumerate(captures):
        result=call(sample)
        assert result['selector_chain_complete']==(i in (2,4))
        assert result['solver_calls']==0 and result['fresh_at_return']
        assert not any(result[k] for k in m.bridge.FLAGS)
        assert not result['retry_authorized'] and not result['owner_consumption_authorized']
        assert not result['historical_native_execution_authenticated']
        assert result['selector_record']==(sample[0]/'selector_record.json').read_bytes()
        assert result['canonical_lock_hex']==json.loads((sample[0]/'terminal.json').read_bytes())['lock_hex']


@pytest.mark.parametrize('target',['terminal.json','selector_record.json','observations.json',
    'capture/complete.json','capture/native_raw/terminal.json','capture/native_raw/000/raw_receipt.json'])
def test_missing_evidence_never_repaired(tmp_path,captures,no_solver,target):
    sample,path=copy_sample(tmp_path,captures)
    # Keep the omitted bytes outside the candidate namespace, rather than erase.
    (path/target).rename(tmp_path/'retained_missing_bytes')
    before={p.relative_to(path):p.read_bytes() for p in path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='namespace'):call(sample,path)
    assert {p.relative_to(path):p.read_bytes() for p in path.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('directory',['.','capture','capture/native_raw','capture/native_raw/000'])
def test_unknown_namespace(tmp_path,captures,no_solver,directory):
    sample,path=copy_sample(tmp_path,captures);(path/directory/'extra').write_bytes(b'unknown')
    with pytest.raises(ValueError,match='namespace'):call(sample,path)


@pytest.mark.parametrize('target',['terminal.json','postsolve.json','observations.json','selector_record.json',
    'capture/binding.json','capture/specification.json','capture/export.json','capture/complete.json',
    'capture/native_raw/binding.json','capture/native_raw/terminal.json','capture/native_raw/000/intent.json',
    'capture/native_raw/000/raw.bin','capture/native_raw/000/raw_receipt.json','capture/native_raw/000/outcome.json'])
def test_each_noncanonical_file_rejected(tmp_path,captures,no_solver,target):
    sample,path=copy_sample(tmp_path,captures);p=path/target;p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='canonical'):call(sample,path)


@pytest.mark.parametrize('field',['formal_result','selector_chain_complete','lock_hex','request_key','observations_sha256'])
def test_rehashed_terminal_claims_reconstructed(tmp_path,captures,no_solver,field):
    sample,path=copy_sample(tmp_path,captures);p=path/'terminal.json';doc=json.loads(p.read_bytes())
    doc[field]=True if field in ('formal_result','selector_chain_complete') else '0'*64
    raw=m.io.encode(doc);p.write_bytes(raw)
    with pytest.raises(ValueError,match='terminal reconstruction'):call(sample,path,pin=m.io.digest(raw))


@pytest.mark.parametrize('target',['postsolve.json','observations.json','selector_record.json','capture/complete.json'])
def test_rehashed_internal_tamper(tmp_path,captures,no_solver,target):
    sample,path=copy_sample(tmp_path,captures);p=path/target;doc=json.loads(p.read_bytes())
    if target=='postsolve.json':doc['reported_values'][0][1]=(123.).hex()
    elif target=='observations.json':doc['call_basis']='caller assertion'
    elif target=='selector_record.json':doc['raw']['calls']=0
    else:doc['callback_sequence_complete']=False
    data=m.bridge.selector.native._encoded(doc) if target=='selector_record.json' else m.io.encode(doc)
    p.write_bytes(data);terminal=json.loads((path/'terminal.json').read_bytes())
    field={'postsolve.json':'postsolve_sha256','observations.json':'observations_sha256',
        'selector_record.json':'selector_record_sha256','capture/complete.json':'capture_complete_sha256'}[target]
    terminal[field]=m.io.digest(data);raw=m.io.encode(terminal);(path/'terminal.json').write_bytes(raw)
    with pytest.raises(ValueError):call(sample,path,pin=m.io.digest(raw))


@pytest.mark.parametrize('fault',['byte_change','replacement','unknown','late_read'])
def test_replay_and_final_bookend_drift(tmp_path,captures,monkeypatch,no_solver,fault):
    sample,path=copy_sample(tmp_path,captures);victim=path/'postsolve.json';original=victim.read_bytes()
    if fault=='late_read':
        reader=m.io.read_stable;reads=0
        def read(p,cap):
            nonlocal reads
            result=reader(p,cap)
            if p==path/'capture/native_raw/000/outcome.json':
                reads+=1
                if reads==4:victim.write_bytes(original+b' ')
            return result
        monkeypatch.setattr(m.io,'read_stable',read)
    else:
        audit=m.bridge._audit_stage
        def replay(*a,**kw):
            out=audit(*a,**kw)
            if fault=='byte_change':victim.write_bytes(original+b' ')
            elif fault=='replacement':
                victim.rename(tmp_path/'retained_original');victim.write_bytes(original)
            else:(path/'capture/native_raw/000/extra').write_bytes(b'extra')
            return out
        monkeypatch.setattr(m.bridge,'_audit_stage',replay)
    with pytest.raises(ValueError,match='view changed|namespace|directory changed'):call(sample,path)


def test_external_pin_and_prior_context(captures,no_solver):
    with pytest.raises(ValueError,match='external selector terminal'):call(captures[0],pin='0'*64)
    with pytest.raises(ValueError):call(captures[1],records=())


def test_exact_after_terminal_failure_is_only_saved_consistency(tmp_path,monkeypatch,no_solver):
    f,d,b,args=producer.inputs(producer.fixtures.R);path=tmp_path/'capture';producer.install(monkeypatch,path,producer.fixtures.R)
    write=m.io.write_new
    def interrupted(p,raw):
        result=write(p,raw)
        if p==path/'terminal.json':raise OSError('synthetic after-write failure')
        return result
    monkeypatch.setattr(m.io,'write_new',interrupted)
    with pytest.raises(OSError):
        m.bridge._run_stage(path,f,d,b,(),expected_key=m.bridge.request_key(f,d,b,(),**args),**args)
    # This pin is retained by the test's observer; it is not owner authority.
    pin=m.io.digest((path/'terminal.json').read_bytes())
    def denied(*a,**kw):raise AssertionError('reader entered producer')
    monkeypatch.setattr(m.bridge.capture.old.provenance.adapter,'create_solver',denied)
    result=m.inspect(path,f,d,b,(),expected_terminal_sha256=pin,**args)
    assert result['state']=='saved_numerical_consistency'
    assert not result['owner_consumption_authorized'] and not result['retry_authorized']


@pytest.mark.parametrize('fault',['duck','bool','oversize','extra_argument'])
def test_limits_rejected_before_evidence_read(tmp_path,monkeypatch,no_solver,fault):
    f,d,b,args=producer.inputs(producer.fixtures.R);args=dict(args)
    if fault=='duck':args['limits']=SimpleNamespace(max_record_bytes=10**12)
    elif fault=='extra_argument':args['unexpected']=None
    else:
        args['limits']=replace(args['limits'])
        object.__setattr__(args['limits'],'max_record_bytes',True if fault=='bool' else m.io.RAW_CAP+1)
    def denied(*a,**kw):raise AssertionError('invalid limits reached evidence read')
    monkeypatch.setattr(m.io,'read_stable',denied)
    with pytest.raises(ValueError):
        m.inspect(tmp_path/'absent',f,d,b,(),expected_terminal_sha256='0'*64,**args)


@pytest.mark.parametrize('fault',['schema','version','request'])
def test_final_evidence_scan_dependency_drift(tmp_path,captures,monkeypatch,no_solver,fault):
    sample,path=copy_sample(tmp_path,captures);directory=m._directory;calls=0
    def observe(p,names):
        nonlocal calls
        result=directory(p,names)
        if p==path/'capture/native_raw/000':
            calls+=1
            if calls==2:
                if fault=='schema':monkeypatch.setattr(m,'SCHEMA','changed')
                elif fault=='version':monkeypatch.setattr(m.bridge,'version',lambda name:'changed')
                else:monkeypatch.setattr(m.bridge,'request_key',lambda *a,**kw:'0'*64)
        return result
    monkeypatch.setattr(m,'_directory',observe)
    with pytest.raises(ValueError,match='scope|final dependency'):call(sample,path)
    assert calls==2


@pytest.mark.parametrize('raw',[b'{"x":0,"x":1}',b'{"x":NaN}'])
def test_duplicate_and_nonfinite_json(tmp_path,captures,no_solver,raw):
    sample,path=copy_sample(tmp_path,captures);(path/'terminal.json').write_bytes(raw)
    with pytest.raises(ValueError):call(sample,path,pin=m.io.digest(raw))


def test_rehashed_specification_and_export_chain_rejected(tmp_path,captures,no_solver):
    sample,path=copy_sample(tmp_path,captures)
    def alter(relative,change):
        p=path/relative;doc=json.loads(p.read_bytes());change(doc)
        data=m.io.encode(doc);p.write_bytes(data);return m.io.digest(data)
    spec=alter('capture/specification.json',lambda d:d['options'].update(Threads=2))
    export=alter('capture/export.json',lambda d:d.update(specification_sha256=spec))
    native=alter('capture/native_raw/000/raw.bin',lambda d:d.update(export_sha256=export))
    receipt=alter('capture/native_raw/000/raw_receipt.json',lambda d:d.update(raw_sha256=native,
        raw_bytes=(path/'capture/native_raw/000/raw.bin').stat().st_size))
    outcome=alter('capture/native_raw/000/outcome.json',lambda d:d.update(raw_receipt_sha256=receipt))
    raw_terminal=alter('capture/native_raw/terminal.json',lambda d:d.update(last_outcome_sha256=outcome))
    complete=alter('capture/complete.json',lambda d:d.update(raw_sha256=native,raw_terminal_sha256=raw_terminal))
    post=alter('postsolve.json',lambda d:d.update(native_sha256=native))
    observations=alter('observations.json',lambda d:d.update(capture_complete_sha256=complete))
    terminal=alter('terminal.json',lambda d:d.update(export_sha256=export,native_sha256=native,
        postsolve_sha256=post,capture_complete_sha256=complete,observations_sha256=observations))
    with pytest.raises(ValueError,match='producer request/specification/raw chain differs'):
        call(sample,path,pin=terminal)


def test_fresh_python_process_reconstructs_saved_terminal(captures,no_solver):
    sample=captures[2];path,f,d,b,args,records,pin=sample
    script=r'''
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from experiments import h1_selector_raw_science_inspect_development_v1 as m
from tests import test_h1_selector_raw_science_development_v1 as fixtures
root=Path(sys.argv[1]);pin=sys.argv[2]
def denied(*a,**kw):raise AssertionError('fresh reader entered producer')
m.bridge._run_stage=denied
m.bridge.capture.StageCapture=denied
with m.bridge.science.prior.guard.solver_calls_forbidden():
    f,d,b,args=fixtures.inputs(fixtures.fixtures.R)
    prior=tuple((root.parent/('Rref'+str(i))/'selector_record.json').read_bytes() for i in range(2))
    out=m.inspect(root,f,d,b,prior,expected_terminal_sha256=pin,**args)
    assert out['selector_chain_complete'] and out['solver_calls']==0
    assert not any(out[k] for k in m.bridge.FLAGS)
    assert not out['retry_authorized'] and not out['owner_consumption_authorized']
    assert not out['historical_native_execution_authenticated']
    print(json.dumps(dict(request_key=out['request_key'],terminal_sha256=out['terminal_sha256'],
        selector_record_sha256=out['selector_record_sha256'],canonical_lock_hex=out['canonical_lock_hex'])))
'''
    completed=subprocess.run([sys.executable,'-B','-c',script,str(path),pin],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=120)
    assert completed.returncode==0,completed.stdout+completed.stderr
    result=json.loads(completed.stdout)
    terminal=json.loads((path/'terminal.json').read_bytes())
    assert result==dict(request_key=m.bridge.request_key(f,d,b,records,**args),
        terminal_sha256=pin,selector_record_sha256=m.io.digest((path/'selector_record.json').read_bytes()),
        canonical_lock_hex=terminal['lock_hex'])
