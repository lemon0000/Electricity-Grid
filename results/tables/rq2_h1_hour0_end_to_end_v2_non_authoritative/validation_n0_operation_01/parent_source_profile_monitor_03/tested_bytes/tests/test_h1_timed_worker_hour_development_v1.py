import json
import os

import pytest

from experiments import h1_timed_worker_hour_development_v1 as api
from tests.test_h1_stage_completion_development_v1 import SyntheticDirect
from tests.test_h1_native_raw_science_development_v1 import LIMITS
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec

pytestmark = pytest.mark.skipif(os.name != 'nt',reason='actual Windows process and NTFS lease')


class RealClockSyntheticDirect(SyntheticDirect):
    def _presolve(self, model, **kwargs):
        super()._presolve(model, **kwargs)
        self._env_options = {}; self._version_major = 12; self._suffixes = ()
        self._needs_updated = True
        self.native.setParam = lambda *args: None
        def optimize(callback):
            assert callback is None
            assert (self.path/'native_timing/intent.json').is_file()
            assert not (self.path/'native_raw/000/raw.bin').exists()
            self.apply_calls += 1
        self.native.optimize = optimize


def install(mp, root, reports):
    solvers = []
    mp.setattr(api.hour.stage.capture,'GurobiDirect',RealClockSyntheticDirect)
    mp.setattr(api.timing,'GurobiDirect',RealClockSyntheticDirect)
    def factory(specification):
        solver = RealClockSyntheticDirect(None,None,None,
            root/'hour_non_authoritative'/'stages'/f'{len(solvers):03d}',None)
        solver.report = json.loads(reports[len(solvers)])
        solvers.append(solver)
        return solver,api.hour.stage.capture.old.audit.solver_options(specification)
    mp.setattr(api.hour.stage.capture.old.provenance.adapter,'create_solver',factory)
    return solvers


def owner(root):
    pid,creation = api.job._current_process()
    return api.OwnedWorkerHour(root,packet(),spec(),LIMITS,controller_request_sha256='a'*64,
                              expected_pid=pid,expected_creation_filetime=creation)


@pytest.fixture(scope='module')
def completed(tmp_path_factory,saved):
    root = tmp_path_factory.mktemp('worker')/'worker_non_authoritative'
    with pytest.MonkeyPatch.context() as mp:
        no_solver.__wrapped__(mp)
        solvers = install(mp,root,saved[1])
        worker = owner(root)
        result = worker.run()
        assert [s.apply_calls for s in solvers] == [1,1,1]
        assert [s.close_calls for s in solvers] == [1,1,1]
        return worker,result


def replay(worker,result):
    return api.inspect(worker.root,*worker.context,expected_binding_sha=worker.binding_pin,
        expected_terminal_sha=result.terminal_sha256,expected_implementation=worker.implementation)


def test_real_clock_worker_matches_existing_scientific_oracle(completed,saved):
    worker,result = completed
    checked = replay(worker,result)
    previous = api.hour.prior.replay_stream(packet(),spec(),LIMITS,saved[1],
        expected_key=api.hour.prior.request_key(packet(),spec(),LIMITS))
    assert json.loads(result.projection_payload)['value'] == json.loads(previous.projection_payload)
    assert result.local_clock_binding_checked and result.native_total_ns > 0
    assert result.worker_window_non_native_ns > 0 and result.confirmation_tail_ns > 0
    assert checked['native_total_ns'] == result.native_total_ns
    assert checked['worker_window_non_native_ns'] == result.worker_window_non_native_ns
    assert checked['confirmation_tail_ns'] is None and not checked['clock_source_authenticated']
    assert not any(dict(result.authority_flags).values())
    assert worker._lease is None and worker.complete
    assert len([p for p in worker.root.rglob('*') if p.is_file()]) == 22*3+3+3
    with pytest.raises(TypeError): api.Completion(())


def interval_rows():
    return [dict(index=i,pid=1,thread_id=2,clock_domain=f'{i:032x}',
        apply_start_ns=5+i*30,native_start_ns=10+i*30,native_end_ns=20+i*30,
        apply_end_ns=25+i*30,binding_sha256='a'*64,terminal_sha256='b'*64) for i in range(3)]


def analyse(rows,**kwargs):
    return api.analyse_intervals(rows,count=3,pid=1,thread_id=2,start=0,end=100,**kwargs)


def test_contained_disjoint_arithmetic_oracle():
    assert analyse(interval_rows()) == dict(native_total_ns=30,worker_window_ns=100,worker_window_non_native_ns=70)


@pytest.mark.parametrize('fault',['missing','index','pid','thread','domain','overlap','outside','reverse','bool'])
def test_sum_less_than_wall_does_not_prove_interval_bridge(fault):
    rows = interval_rows()
    if fault == 'missing': rows.pop()
    elif fault == 'index': rows[1]['index'] = 2
    elif fault == 'pid': rows[1]['pid'] = 3
    elif fault == 'thread': rows[1]['thread_id'] = 3
    elif fault == 'domain': rows[1]['clock_domain'] = rows[0]['clock_domain']
    elif fault == 'overlap': rows[1].update(apply_start_ns=15,native_start_ns=16,native_end_ns=19,apply_end_ns=24)
    elif fault == 'outside': rows[-1]['apply_end_ns'] = 101
    elif fault == 'reverse': rows[1]['native_end_ns'] = 39
    else: rows[1]['pid'] = True
    with pytest.raises(ValueError): analyse(rows)


def test_wrong_process_or_clock_rejected_before_output(tmp_path,monkeypatch):
    root = tmp_path/'worker_non_authoritative'
    pid,creation = api.job._current_process()
    with pytest.raises(ValueError,match='process identity'):
        api.OwnedWorkerHour(root,packet(),spec(),LIMITS,controller_request_sha256='a'*64,
                           expected_pid=pid,expected_creation_filetime=creation+1)
    assert not root.exists()
    monkeypatch.setattr(api._INIT,'__kwdefaults__',{'clock':lambda:0})
    with pytest.raises(ValueError,match='default worker/native clock'): owner(root)
    assert not root.exists()


def test_binding_confirmation_does_not_adopt_drift(tmp_path,monkeypatch):
    root = tmp_path/'worker_non_authoritative'
    write = api.io.write_metadata
    def drift(path,doc):
        pin = write(path,doc)
        if path == root/'binding.json':
            changed = dict(doc,pid=doc['pid']+1)
            path.write_bytes(api.io.encode(changed))
        return pin
    monkeypatch.setattr(api.io,'write_metadata',drift)
    with pytest.raises(ValueError,match='binding confirmation'): owner(root)
    lease = api.job.bounded.chunks.base.local._Lease(root,False)
    lease.close()


def test_reentry_and_foreign_cleanup_leave_owner_available(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    worker = owner(tmp_path/'worker_non_authoritative')
    try:
        worker.guard.acquire()
        try:
            with pytest.raises(ValueError,match='active'): worker.run()
            assert not worker.poisoned and not worker.started
        finally: worker.guard.release()
        with ThreadPoolExecutor(1) as pool:
            with pytest.raises(ValueError,match='owner'): pool.submit(worker.close).result()
        assert not worker.poisoned and worker._lease is not None
    finally: worker.close()


@pytest.mark.parametrize('target,after',[('binding',False),('binding',True),('terminal',False),('terminal',True)])
def test_worker_publication_failures_no_receipt_or_retry(tmp_path,saved,monkeypatch,target,after):
    root = tmp_path/'worker_non_authoritative'
    solvers = install(monkeypatch,root,saved[1])
    write = api.io.write_metadata
    def fail(path,doc):
        if path == root/(target+'.json'):
            if after: write(path,doc)
            raise OSError('worker publication')
        return write(path,doc)
    monkeypatch.setattr(api.io,'write_metadata',fail)
    if target == 'binding':
        with pytest.raises(OSError): owner(root)
        assert not solvers
    else:
        worker = owner(root)
        with pytest.raises(OSError): worker.run()
        assert worker.poisoned and not worker.complete and worker._lease is None
        assert (root/'hour_non_authoritative'/'terminal.json').is_file()
        before = len(solvers)
        with pytest.raises(ValueError): worker.run()
        assert len(solvers) == before
    lease = api.job.bounded.chunks.base.local._Lease(root,False)
    lease.close()


@pytest.mark.parametrize('fault',['foreign_pid','overlap','fresh_failure','clock_drift','after_inspect_science','after_inspect_commit'])
def test_hour_success_does_not_imply_worker_completion(tmp_path,saved,monkeypatch,fault):
    root = tmp_path/'worker_non_authoritative'
    install(monkeypatch,root,saved[1])
    worker = owner(root)
    if fault in ('foreign_pid','overlap'):
        original = api._intervals
        def altered(*args):
            rows,views = original(*args)
            if fault == 'foreign_pid': rows[0]['pid'] += 1
            else:
                rows[1]['apply_start_ns'] = rows[0]['apply_start_ns']
            return rows,views
        monkeypatch.setattr(api,'_intervals',altered)
    elif fault == 'fresh_failure':
        def fail(*args,**kwargs): raise ValueError('worker fresh failure')
        monkeypatch.setattr(api,'inspect',fail)
    elif fault == 'clock_drift':
        original = api.hour.OwnedHour.run
        def changed(hour_owner):
            result = original(hour_owner)
            monkeypatch.setattr(api._INIT,'__kwdefaults__',{'clock':lambda:0})
            return result
        monkeypatch.setattr(api.hour.OwnedHour,'run',changed)
    else:
        original = api.inspect
        def drift(*args,**kwargs):
            result = original(*args,**kwargs)
            relative = ('stages/000/science/result.bin' if fault == 'after_inspect_science' else 'commits/000.json')
            path = root/'hour_non_authoritative'/relative
            stat = path.stat(); data = path.read_bytes()
            path.write_bytes(data[:-1]+bytes([data[-1]^1]))
            os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            return result
        monkeypatch.setattr(api,'inspect',drift)
    with pytest.raises(ValueError): worker.run()
    assert worker.poisoned and not worker.complete and worker._lease is None


@pytest.mark.parametrize('window',['unlock_before','unlock_after','new_owner_after_release'])
def test_worker_release_failure_never_returns_completion(tmp_path,saved,monkeypatch,window):
    import msvcrt
    root = tmp_path/'worker_non_authoritative'
    install(monkeypatch,root,saved[1])
    worker = owner(root)
    Lease = api.job.bounded.chunks.base.local._Lease
    new_owners = []
    if window == 'new_owner_after_release':
        release = worker._lease.close
        def fail():
            release()
            new_owners.append(Lease(root,False))
            raise OSError('worker lease confirmation')
        monkeypatch.setattr(worker._lease,'close',fail)
    else:
        locking = msvcrt.locking; target = worker._lease.stream.fileno()
        def fail(fd,mode,count):
            if fd == target and mode == msvcrt.LK_UNLCK:
                if window == 'unlock_after': locking(fd,mode,count)
                raise OSError('worker lease unlock')
            return locking(fd,mode,count)
        monkeypatch.setattr(msvcrt,'locking',fail)
    try:
        with pytest.raises(OSError): worker.run()
        assert worker.poisoned and not worker.complete and worker._lease is None
        assert (root/'terminal.json').is_file() and (root/'hour_non_authoritative'/'terminal.json').is_file()
        if new_owners:
            new_owners[0].check()
            with pytest.raises(ValueError,match='already held'): Lease(root,False)
        else:
            monkeypatch.setattr(msvcrt,'locking',locking)
            reopened = Lease(root,False); reopened.close()
    finally:
        for new in new_owners: new.close()


def test_disk_reader_rejects_pin_and_topology_mismatch(completed,tmp_path):
    import shutil
    worker,result = completed
    root = tmp_path/'copy_non_authoritative'
    shutil.copytree(worker.root,root)
    (root/'unexpected').write_bytes(b'x')
    with pytest.raises(ValueError,match='entry cap'):
        api.inspect(root,*worker.context,expected_binding_sha=worker.binding_pin,
            expected_terminal_sha=result.terminal_sha256,expected_implementation=worker.implementation)
    with pytest.raises(ValueError,match='external worker pin'):
        api.inspect(worker.root,*worker.context,expected_binding_sha='f'*64,
            expected_terminal_sha=result.terminal_sha256,expected_implementation=worker.implementation)
