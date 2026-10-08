import ast
import inspect
import json
import textwrap

import pytest

from experiments import h1_timed_hour_development_v1 as api
from experiments import h1_owned_hour_development_v1 as old_hour
from experiments import h1_native_raw_science_development_v1 as old_science
from tests.test_h1_stage_completion_development_v1 import SyntheticDirect
from tests.test_h1_native_raw_science_development_v1 import LIMITS
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec

timing = api.stage.capture.timing


class Clock:
    now = 100
    def __call__(self): return self.now


class TimedSyntheticDirect(SyntheticDirect):
    def _presolve(self, model, **kwargs):
        super()._presolve(model, **kwargs)
        self._env_options = {}; self._version_major = 12; self._suffixes = ()
        self._needs_updated = True
        def set_param(name, value): self.clock.now += 11
        def optimize(callback):
            assert callback is None
            assert (self.path/'native_raw/000/intent.json').exists()
            assert (self.path/'native_timing/intent.json').exists()
            assert not (self.path/'native_raw/000/raw.bin').exists()
            self.apply_calls += 1; self.clock.now += 73
            if self.fault == 'optimize': raise RuntimeError('synthetic optimize failed')
        self.native.setParam = set_param; self.native.optimize = optimize


def install(mp, root, saved, fault=None):
    solvers, clock = [], Clock()
    mp.setattr(api.stage.capture, 'GurobiDirect', TimedSyntheticDirect)
    mp.setattr(timing, 'GurobiDirect', TimedSyntheticDirect)
    init = timing.Measurement.__init__
    def measured(self, path, request, index, **kwargs): return init(self, path, request, index, clock=clock)
    mp.setattr(timing.Measurement, '__init__', measured)
    def factory(specification):
        index = len(solvers)
        solver = TimedSyntheticDirect(None, None, None, root/'stages'/f'{index:03d}', fault)
        solver.clock = clock; solver.report = json.loads(saved[1][index]); solvers.append(solver)
        return solver, api.stage.capture.old.audit.solver_options(specification)
    mp.setattr(api.stage.capture.old.provenance.adapter, 'create_solver', factory)
    return solvers


@pytest.fixture(scope='module')
def completed(tmp_path_factory, saved):
    root = tmp_path_factory.mktemp('timed_hour')/'hour'
    with pytest.MonkeyPatch.context() as mp:
        no_solver.__wrapped__(mp)
        solvers = install(mp, root, saved)
        owner = api.OwnedHour(root, packet(), spec(), LIMITS)
        receipt = owner.run()
        assert [s.apply_calls for s in solvers] == [1,1,1]
        assert [s.close_calls for s in solvers] == [1,1,1]
        return owner, receipt


def replay(owner, receipt):
    return api.inspect(owner.root, *owner.context, expected_terminal_sha=receipt.terminal_sha256,
                       expected_implementation=receipt.implementation)


def test_science_core_ast_is_unchanged():
    names = ['_keys','_hex','_atom','_channel','decode_native','request_key',
             'capture_postsolve','_postsolve','_numerical','audit_stage','_outputs']
    for name in names:
        before = ast.parse(textwrap.dedent(inspect.getsource(getattr(old_science,name))))
        after = ast.parse(textwrap.dedent(inspect.getsource(getattr(api.science,name))))
        assert ast.dump(before) == ast.dump(after), name


def test_three_stage_timed_hour_matches_science_oracle(completed, saved):
    owner, receipt = completed
    result = replay(owner, receipt)
    assert result['canonical_locks'] == (20.,1.,20.)
    assert result['native_intervals_complete'] and result['native_total_ns'] == 219
    assert receipt.native_total_ns == 219
    assert not result['instrumentation_coverage_verified'] and not result['component_budget_verified']
    prior = api.prior.replay_stream(packet(),spec(),LIMITS,saved[1],expected_key=api.prior.request_key(packet(),spec(),LIMITS))
    assert json.loads(receipt.projection_payload)['value'] == json.loads(prior.projection_payload)
    locks = ()
    for index in range(3):
        root = owner.root/'stages'/f'{index:03d}'
        commit = json.loads((owner.root/'commits'/f'{index:03d}.json').read_bytes())
        checked = api.stage.inspect(root,*owner.context,index,locks,
            expected_producer_complete_sha=commit['producer_complete_sha256'],
            expected_science_terminal_sha=commit['science_terminal_sha256'],expected_implementation=api.stage.implementation_identity())['result']
        old = api.prior._audit_stage(packet(),spec(),LIMITS,index,locks,saved[1][index])
        assert checked['assignment'] == old['assignment']
        assert checked['generation_mapping'] == old['generation_mapping']
        assert checked['timing']['native_interval_ns'] == 73
        locks = (*locks,checked['lock'])
    assert len([p for p in owner.root.rglob('*') if p.is_file()]) == 22*3+3
    with pytest.raises(ValueError): old_hour.inspect(owner.root,*owner.context,
        expected_terminal_sha=receipt.terminal_sha256,expected_implementation=old_hour.implementation_identity())


@pytest.mark.parametrize('filename',['intent.json','completion.json','terminal.json'])
@pytest.mark.parametrize('after_write',[False,True])
def test_timing_failure_retains_raw_before_propagation(tmp_path,saved,monkeypatch,filename,after_write):
    root=tmp_path/'hour'; solvers=install(monkeypatch,root,saved)
    owner=api.OwnedHour(root,packet(),spec(),LIMITS)
    original=api.io.write_metadata
    def fail(path,doc):
        if path.parent.name=='native_timing' and path.name==filename:
            if after_write: original(path,doc)
            raise OSError('timing confirmation failed')
        return original(path,doc)
    monkeypatch.setattr(api.io,'write_metadata',fail)
    with pytest.raises(OSError): owner.run()
    child=root/'stages/000'; raw=json.loads((child/'native_raw/000/raw.bin').read_bytes())
    assert raw['apply_error']=='OSError' and (child/'native_raw/000/raw_receipt.json').exists()
    assert (child/'native_raw/000/outcome.json').exists()
    assert solvers[0].apply_calls==(0 if filename=='intent.json' else 1)
    assert not (child/'science').exists() and not (child/'complete.json').exists()
    assert owner.poisoned and not owner.complete and not (root/'terminal.json').exists()
    with pytest.raises(ValueError): owner.run()


def test_optimize_exception_keeps_original_channels(tmp_path,saved,monkeypatch):
    root=tmp_path/'hour'; solvers=install(monkeypatch,root,saved,'optimize')
    owner=api.OwnedHour(root,packet(),spec(),LIMITS)
    with pytest.raises(RuntimeError): owner.run()
    child=root/'stages/000'; doc=json.loads((child/'native_raw/000/raw.bin').read_bytes())
    assert doc['apply_error']=='RuntimeError' and doc['variables']
    assert solvers[0].apply_calls==solvers[0].close_calls==1
    assert not (child/'native_timing/terminal.json').exists() and not (child/'science').exists()


@pytest.mark.parametrize('fault',['capture','raw_write','receipt','outcome','science_drift','close'])
def test_timing_success_is_insufficient_for_stage_completion(tmp_path,saved,monkeypatch,fault):
    root=tmp_path/'hour'; solvers=install(monkeypatch,root,saved,'close' if fault=='close' else None)
    owner=api.OwnedHour(root,packet(),spec(),LIMITS)
    child=root/'stages/000'
    if fault=='capture':
        monkeypatch.setattr(api.stage.capture,'_capture',lambda *a,**k: (_ for _ in ()).throw(OSError('capture interrupted')))
    elif fault=='raw_write':
        original=api.io.write_new
        def fail(path,raw):
            if path.name=='raw.bin': raise OSError('raw write failed')
            return original(path,raw)
        monkeypatch.setattr(api.io,'write_new',fail)
    elif fault in ('receipt','outcome'):
        original=api.io.write_metadata
        def fail(path,doc):
            if path.name==('raw_receipt.json' if fault=='receipt' else 'outcome.json'): raise OSError('raw metadata failed')
            return original(path,doc)
        monkeypatch.setattr(api.io,'write_metadata',fail)
    elif fault=='science_drift':
        original=api.science.audit_stage
        def mutate(*args,**kwargs):
            result=original(*args,**kwargs)
            (child/'native_timing/completion.json').write_bytes(b'{}')
            return result
        monkeypatch.setattr(api.science,'audit_stage',mutate)
    with pytest.raises((OSError,ValueError,RuntimeError)): owner.run()
    assert (child/'native_timing/terminal.json').exists()
    assert not (child/'complete.json').exists() and not (root/'projection.bin').exists()
    assert solvers[0].apply_calls==1 and owner.poisoned
    if fault=='capture': assert not (child/'native_raw/000/raw.bin').exists()


@pytest.mark.parametrize('name',['commits/000.json','terminal.json'])
@pytest.mark.parametrize('after_write',[False,True])
def test_hour_commit_and_terminal_confirmation_failures(tmp_path,saved,monkeypatch,name,after_write):
    root=tmp_path/'hour'; solvers=install(monkeypatch,root,saved)
    owner=api.OwnedHour(root,packet(),spec(),LIMITS); original=api.io.write_new
    def fail(path,raw):
        if path==root/name:
            if after_write: original(path,raw)
            raise OSError('hour confirmation failed')
        return original(path,raw)
    monkeypatch.setattr(api.io,'write_new',fail)
    with pytest.raises(OSError): owner.run()
    assert owner.poisoned and not owner.complete and (root/name).exists()==after_write
    assert len(solvers)==(1 if name.startswith('commits') else 3)


@pytest.mark.parametrize('target',['complete.json','science/intent.json','native_timing/binding.json','native_timing/terminal.json'])
def test_mismatched_timing_evidence_rejected(completed,target):
    owner,receipt=completed; path=owner.root/'stages/001'/target; before=path.read_bytes()
    try:
        doc=json.loads(before)
        if target=='native_timing/binding.json': doc['stage']=0
        elif target=='native_timing/terminal.json':
            doc=json.loads((owner.root/'stages/000'/target).read_bytes())
        else: doc['timing_terminal_sha256']='a'*64
        path.write_bytes(api.io.encode(doc))
        with pytest.raises(ValueError): replay(owner,receipt)
    finally: path.write_bytes(before)
