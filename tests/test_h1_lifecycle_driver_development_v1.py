from dataclasses import replace
import json
import os

import pytest

from experiments import h1_lifecycle_driver_development_v1 as api
from tests.test_h1_timed_job_controller_development_v1 import install_launcher
from tests.test_h1_saved_source_parent_development_v1 import environment, source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports, saved

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='owned Windows driver/Job/QPC integration')


def arguments(env):
    upstream, config, origin, state = env
    return dict(network=api.base.parent.source.static_network(state['data']),
        specification=replace(spec(), time_limit_seconds=5.), limits=api.base.old.replay.H1HourReplayLimits(3,100,500),
        source_identities=(source_pin(env, 0),), origin=origin, upstream_root=upstream, config_path=config,
        dc_bus=1, budget=api.base.old.process.TaskProcessBudget(300.,.05,512*api.base.old.MIB,768*api.base.old.MIB,2.))


def test_declared_storage_and_exact_summary():
    assert api.content_bound(192)['logical_bytes'] == 387*api.CAP+1
    assert api.content_bound(192)['files'] == 388
    for h in (0,193,True,1.0):
        with pytest.raises(ValueError): api.content_bound(h)
    reports = [dict(arithmetic=dict(native_total_ns=6, stagewise_overshoot_ns_ratio=[1,1])),
               dict(arithmetic=dict(native_total_ns=4, stagewise_overshoot_ns_ratio=[1,2]))]
    result = api._summary(20, reports)
    assert result == dict(wall_ns=20,native_total_ns=10,outside_native_ns=10,
        stagewise_overshoot_ns_ratio=[3,2],stagewise_charge_contract_candidate_ns_ratio=[23,2])
    with pytest.raises(ValueError): api._summary(9,reports)
    with pytest.raises(TypeError): api.Completion(())


@pytest.mark.parametrize('fault', ['binding','constructor','manifest','headroom'])
def test_before_job_failure_retains_create_once_root(tmp_path, environment, monkeypatch, fault):
    root = tmp_path/'driver_non_authoritative'; args = arguments(environment)
    original = api._save
    def save(path, value):
        result = original(path,value)
        if fault == 'binding' and path.name == 'binding.json': raise OSError('injected binding')
        return result
    monkeypatch.setattr(api,'_save',save)
    if fault == 'constructor':
        def fail(*a,**k): raise OSError('injected constructor')
        monkeypatch.setattr(api.bridge,'Controller',fail)
    if fault == 'manifest': args['source_identities'] = ('a'*64,)
    if fault == 'headroom':
        def fail(*a,**k): raise OSError('injected headroom')
        monkeypatch.setattr(api,'_headroom',fail)
    with pytest.raises((OSError,ValueError)): api.run(root,**args)
    assert (root/'binding.json').exists() and not (root/'terminal.json').exists()
    assert not (root/'controller_non_authoritative/job_000_non_authoritative').exists()
    with pytest.raises((FileExistsError,ValueError)): api.run(root,**args)


def test_owned_driver_includes_startup_replay_close_and_tail(tmp_path, environment, synthetic_reports, monkeypatch):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    root = tmp_path/'driver_non_authoritative'; args = arguments(environment)
    receipt = api.run(root,**args)
    assert type(receipt) is api.Completion and receipt.declared_driver_call_window_complete
    assert receipt.final_accounting_persistence_tail_ns > 0
    value = api.inspect(root,binding_pin=receipt.binding_sha256,terminal_pin=receipt.terminal_sha256)
    assert not value['live_return_observed'] and value['final_accounting_persistence_tail_ns'] is None
    assert not any(value[k] for k in api.FLAGS)
    binding = json.loads((root/'binding.json').read_bytes())
    terminal = json.loads((root/'terminal.json').read_bytes())
    hour = json.loads((root/'000.result.json').read_bytes())
    assert binding['start_ns'] <= hour['preparation_interval_ns'][0]
    assert hour['clock_interval_ns'][1] <= terminal['final_replay_interval_ns'][0]
    assert terminal['close_interval_ns'][1] <= terminal['end_ns']
    assert value['arithmetic']['wall_ns'] == terminal['end_ns']-binding['start_ns']
    assert value['arithmetic']['outside_native_ns'] >= hour['report']['arithmetic']['outside_native_ns']
    files = [p for p in root.iterdir() if p.is_file()]
    assert len(files) == api.content_bound(1)['files']
    assert sum(p.stat().st_size for p in files) <= api.content_bound(1)['logical_bytes']
    job = root/'controller_non_authoritative/job_000_non_authoritative'
    observed = json.loads((job/'observation.json').read_bytes())
    assert observed['exit_code'] == 0 and observed['whole_job_quiescent']
    assert observed['pid'] != os.getpid()
    # Same-length, restored-mtime metadata corruption must fail under retained pins.
    path = root/'000.result.json'; raw = path.read_bytes(); stamp = path.stat()
    path.write_bytes(b'['+raw[1:]); os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    try:
        with pytest.raises(ValueError): api.inspect(root,binding_pin=receipt.binding_sha256,terminal_pin=receipt.terminal_sha256)
    finally: path.write_bytes(raw)
    terminal_path = root/'terminal.json'; terminal_raw = terminal_path.read_bytes()
    # Re-sign only the fixture's outer metadata: inner report grammar and
    # stage-vector arithmetic must still reject an internally inconsistent claim.
    for change in ('authority','arithmetic','extra_request'):
        row = json.loads(raw); doc = json.loads(terminal_raw)
        if change == 'authority': row['report']['formal_result'] = True
        if change == 'arithmetic':
            row['report']['arithmetic']['native_total_ns'] += 1
            doc['arithmetic'] = api._summary(doc['end_ns']-binding['start_ns'],[row['report']])
        if change == 'extra_request': row['report']['extra_claim'] = False
        changed = api.io.encode(row); path.write_bytes(changed)
        doc['result_sha256'][0] = api.io.digest(changed)
        changed_terminal = api.io.encode(doc); terminal_path.write_bytes(changed_terminal)
        try:
            with pytest.raises(ValueError): api.inspect(root,binding_pin=receipt.binding_sha256,
                terminal_pin=api.io.digest(changed_terminal))
        finally: path.write_bytes(raw); terminal_path.write_bytes(terminal_raw)
    # Preserve all original file identities while exchanging their directory.
    directory = root/'controller_non_authoritative/clock_bridge_non_authoritative/000'
    stash = tmp_path/'old_clock_directory'; replacement = tmp_path/'replacement_clock_directory'
    original_unchanged = api.base.entry.unchanged; swapped = []
    def swap(views):
        original_unchanged(views)
        if not swapped:
            directory.rename(stash); directory.mkdir()
            for p in stash.iterdir(): p.rename(directory/p.name)
            swapped.append(True)
    try:
        with monkeypatch.context() as mp:
            mp.setattr(api.base.entry,'unchanged',swap)
            with pytest.raises(ValueError,match='root/implementation changed'):
                api.inspect(root,binding_pin=receipt.binding_sha256,terminal_pin=receipt.terminal_sha256)
        assert swapped == [True]
    finally:
        if swapped:
            for p in directory.iterdir(): p.rename(stash/p.name)
            directory.rename(replacement); stash.rename(directory)
    with pytest.raises((FileExistsError,ValueError)): api.run(root,**args)
    # Driver lease has been released before the private successful return.
    lease = api.base.old.bounded.chunks.base.local._Lease(root,False)
    lease.check(); lease.close()


@pytest.mark.parametrize('fault', ['terminal_before','terminal_after','fresh_read','lease_close','final_tick','late_job','late_parent'])
def test_after_parent_outcome_failure_has_no_driver_return(tmp_path, environment, synthetic_reports, monkeypatch, fault):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    root = tmp_path/'driver_non_authoritative'; args = arguments(environment)
    original_save, original_inspect = api._save, api.inspect
    reached = []
    def save(path,value):
        if path == root/'terminal.json' and fault == 'terminal_before':
            reached.append(fault); raise OSError(fault)
        result = original_save(path,value)
        if path == root/'terminal.json' and fault == 'terminal_after':
            reached.append(fault); raise OSError(fault)
        return result
    monkeypatch.setattr(api,'_save',save)
    def inspect(*a,**k):
        result = original_inspect(*a,**k)
        if fault == 'fresh_read': reached.append(fault); raise OSError(fault)
        return result
    monkeypatch.setattr(api,'inspect',inspect)
    Lease = api.base.old.bounded.chunks.base.local._Lease
    original_close = Lease.close
    def close(self):
        original_close(self)
        if self.root == root and (root/'terminal.json').exists():
            if fault == 'lease_close': reached.append(fault); raise OSError(fault)
            if fault == 'final_tick':
                def tick(previous): reached.append(fault); raise OSError(fault)
                monkeypatch.setattr(api.bridge,'tick',tick)
    monkeypatch.setattr(Lease,'close',close)
    original_controller_close = api.bridge.Controller.close
    def controller_close(self):
        original_controller_close(self)
        if fault in ('late_job','late_parent') and not reached:
            target = (root/'controller_non_authoritative/job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative/commits/000.json'
                if fault == 'late_job' else root/'controller_non_authoritative/source_parent_non_authoritative/parent_events_non_authoritative/002/metadata.bin')
            raw = target.read_bytes(); stamp = target.stat()
            target.write_bytes(b'['+raw[1:]); os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            reached.append(fault)
    monkeypatch.setattr(api.bridge.Controller,'close',controller_close)
    with pytest.raises((OSError,ValueError),match='complete driver evidence changed' if fault.startswith('late_') else fault): api.run(root,**args)
    assert reached == [fault]
    assert (root/'000.result.json').exists()
    assert json.loads((root/'000.result.json').read_bytes())['outcome_head']
    assert (root/'terminal.json').exists() is (fault not in ('terminal_before','late_job','late_parent'))
    # The saved parent result is retained even though no driver Completion exists.
    job = root/'controller_non_authoritative/job_000_non_authoritative'
    assert json.loads((job/'observation.json').read_bytes())['exit_code'] == 0
    assert not (root/'controller_non_authoritative/job_001_non_authoritative').exists()
