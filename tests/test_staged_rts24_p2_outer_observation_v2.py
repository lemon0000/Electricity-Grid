"""Temporary parent observations, generic publication faults, no P2/native run."""
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from src import staged_rts24_p2_outer_observation_v2 as d


def process():
    return dict(exit_code=0,stop_reason=None,monitor_error=None,cleanup_error=None,job_quiet_confirmed=True,
        outer_seconds=.1,sampled_tree_peak_rss_bytes=1024,rss_observation_available=True,peak_job_commit_bytes=2048,
        samples=1,terminal_bytes=100,terminal_files=1,terminal_reserved_bytes=131072,parent_reserved_bytes=131072,terminal_reserved_files=1,parent_reserved_files=1,member_handle_cap=1024,owner_pid=123,owner_creation_filetime=456,
        quiescence_witness=dict(active_processes=0,all_handles_signaled=True,complete_inventory=True,final_pids=[],
            member_identities=[dict(pid=123,creation_filetime=456)],observed_unique_member_handles=1,total_processes=1))


def claims():
    return dict(inspection_scope='caller_supplied_mechanical',completion_core_sha=None,inventory_sha=None,report_sha=None,
        point_references=319,contract_rows=138,mechanical_package_integrity=True,
        unverified_worker_claims=dict(full_139_executed=True,package_complete=True))


@pytest.fixture
def case(tmp_path):
    worker=tmp_path/'worker';parent=tmp_path/'parent';worker.mkdir();parent.mkdir()
    value=dict(schema='staged_rts24_P2_parent_observation_development_v2',authority='DRAFT_NONAUTHORITATIVE',
        worker_root=str(worker),parent_root=str(parent),limits=dict(d.CAPS),kernel_registration_sha=None,terminal_record_cap_bytes=131072,parent_record_cap_bytes=131072,terminal_reserved_files=1,parent_reserved_files=1,max_member_handles=1024,
        public_execution_enabled=False,native_authorized=False,resource_admission=False)
    raw=d.canonical_context(value)
    record=process();(worker/'payload').write_bytes(b'x'*100)
    d.codec.publish(worker/'launcher.json',d.record_image(record))
    return SimpleNamespace(worker=worker,parent=parent,context=value,raw=raw,sha=d.sha256(raw).hexdigest(),record=record)


def test_successful_mechanical_callback_is_saved_without_scientific_adoption(case):
    proposed=claims()
    result=d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:proposed)
    stored=json.loads((case.parent/'parent_observation.json').read_bytes())
    assert stored==result['observation'] and stored['ownership_status']=='quiet_verified'
    assert stored['inspection_status']=='returned' and stored['caller_supplied_mechanical_claims']==proposed
    assert all(stored[n] is False for n in ('scientific_evidence_adopted','scientific_audit_replayed','full_139_independently_verified',
        'source_freshness_independently_verified','resource_admission','formal_result'))
    assert stored['worker_terminal_status']=='not_independently_replayed' and result['parent_record_saved'] is True
    assert result['parent_record_sha']==d.sha256((case.parent/'parent_observation.json').read_bytes()).hexdigest()


@pytest.mark.parametrize('fault',['quiet','cleanup','close','active','final_pid','signaled','incomplete','member_count','owner','duplicate','exit','wall','storage','rss','missing_sample',
    'monitor','job_commit','files','reserve_zero','reserve_short','member_overflow'])
def test_unknown_failed_or_over_cap_process_never_opens_worker_results(case,fault):
    r=case.record;w=r['quiescence_witness']
    if fault=='quiet':r['job_quiet_confirmed']=False
    elif fault in ('cleanup','close'):r['cleanup_error']=fault
    elif fault=='active':w['active_processes']=1
    elif fault=='final_pid':w['final_pids']=[999]
    elif fault=='signaled':w['all_handles_signaled']=False
    elif fault=='incomplete':w['complete_inventory']=False
    elif fault=='member_count':w['total_processes']=2
    elif fault=='owner':r['owner_creation_filetime']+=1
    elif fault=='duplicate':w['member_identities']*=2;w['total_processes']=w['observed_unique_member_handles']=2
    elif fault=='exit':r['exit_code']=2
    elif fault=='wall':r['stop_reason']='wall_limit'
    elif fault=='storage':r['terminal_bytes']=d.CAPS['output_bytes']
    elif fault=='rss':r['sampled_tree_peak_rss_bytes']=d.CAPS['rss_bytes']+1
    elif fault=='monitor':r['monitor_error']='sample failed'
    elif fault=='job_commit':r['peak_job_commit_bytes']=2*1024**3+1
    elif fault=='files':r['terminal_files']=d.CAPS['files']
    elif fault in ('reserve_zero','reserve_short'):
        r['terminal_reserved_bytes']=0 if fault=='reserve_zero' else 16383
        r['terminal_bytes']=d.CAPS['output_bytes']-16383
    elif fault=='member_overflow':
        w['member_identities']=[dict(pid=123+i,creation_filetime=456) for i in range(1025)]
        w['total_processes']=w['observed_unique_member_handles']=1025
    else:r['rss_observation_available']=False;r['sampled_tree_peak_rss_bytes']=None;r['samples']=0
    def denied(root):pytest.fail('worker results inspected without complete successful quiet')
    if fault in ('reserve_zero','reserve_short','member_overflow','duplicate'):
        with pytest.raises(ValueError):d.save_observation(case.parent,case.raw,case.sha,r,denied)
        assert not list(case.parent.iterdir());return
    result=d.save_observation(case.parent,case.raw,case.sha,r,denied)
    assert result['observation']['inspection_status']=='skipped' and result['scientific_evidence_adopted'] is False


@pytest.mark.parametrize('fault',['context_sha','context_authority','context_not_canonical','process_bool','process_extra'])
def test_bad_context_or_process_rejected_before_parent_publication(case,fault):
    raw,sha=case.raw,case.sha
    if fault=='context_sha':sha='0'*64
    elif fault=='context_authority':
        value=dict(case.context,native_authorized=True);raw=d.codec.canonical(value);sha=d.sha256(raw).hexdigest()
    elif fault=='context_not_canonical':raw=b' '+raw;sha=d.sha256(raw).hexdigest()
    elif fault=='process_bool':case.record['exit_code']=False
    else:case.record['permission']=True
    with pytest.raises(ValueError):d.save_observation(case.parent,raw,sha,case.record,lambda root:pytest.fail('bad binding inspected'))
    assert not list(case.parent.iterdir())


@pytest.mark.parametrize('fault',['exception','non_mapping','nonfinite'])
def test_inspection_failure_is_saved_as_observation_and_not_a_scientific_claim(case,fault):
    def inspect(root):
        if fault=='exception':raise OSError('ordinary inspection failure')
        return [] if fault=='non_mapping' else dict(number=float('nan'))
    result=d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert result['observation']['inspection_status']=='failed' and result['observation']['inspection_error'] is not None
    assert result['observation']['caller_supplied_mechanical_claims'] is None and result['scientific_evidence_adopted'] is False


@pytest.mark.parametrize('fault',['scientific_evidence_adopted','resource_admission','formal_result','authority','official_verdict',
    'gate','seal','receipt','extra','nested_authority','count_bool','count_float','count_over','integrity_int','worker_int','pin','scope'])
def test_claim_schema_rejects_authority_fields_extra_keys_and_noncanonical_scalars(case,fault):
    proposed=claims()
    if fault=='nested_authority':proposed['unverified_worker_claims']['scientific_evidence_adopted']=True
    elif fault=='count_bool':proposed['point_references']=True
    elif fault=='count_float':proposed['point_references']=319.0
    elif fault=='count_over':proposed['contract_rows']=139
    elif fault=='integrity_int':proposed['mechanical_package_integrity']=1
    elif fault=='worker_int':proposed['unverified_worker_claims']['full_139_executed']=1
    elif fault=='pin':proposed['report_sha']='A'*64
    elif fault=='scope':proposed['inspection_scope']='scientific'
    else:proposed[fault]=True
    saved=d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:proposed)
    assert saved['observation']['inspection_status']=='failed'
    assert saved['observation']['caller_supplied_mechanical_claims'] is None
    assert saved['observation']['scientific_evidence_adopted'] is False


def test_caller_process_mutation_does_not_rewrite_held_snapshot(case):
    def inspect(root):case.record['exit_code']=77;return claims()
    saved=d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert saved['observation']['process_snapshot']['exit_code']==0 and case.record['exit_code']==77


@pytest.mark.parametrize('phase',['before_open','after_write','after_fsync','after_pending_readback','before_rename','after_rename','after_final_readback'])
def test_publication_failure_retains_phase_pending_or_final_and_never_reports_saved(case,phase):
    def fault(stage,path):
        if stage==phase:raise OSError('ordinary '+phase)
    with pytest.raises(d.OuterObservationUnresolved) as error:
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:claims(),hook=fault)
    observed=error.value
    assert observed.phase==phase and observed.may_have_published is (phase in ('after_rename','after_final_readback'))
    assert observed.scientific_evidence_adopted is False and observed.worker_terminal_status=='not_independently_replayed'
    final=case.parent/'parent_observation.json';pending=final.with_name(final.name+'.pending')
    assert final.exists() is (phase in ('after_rename','after_final_readback'))
    assert pending.exists() is (phase not in ('before_open','after_rename','after_final_readback'))
    if final.exists():assert d.sha256(final.read_bytes()).hexdigest()==observed.expected_sha


def test_postrename_byte_drift_remains_unknown_with_final_retained(case):
    def changed(stage,path):
        if stage=='after_rename':path.write_bytes(b'changed')
    with pytest.raises(d.OuterObservationUnresolved) as error:
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:claims(),hook=changed)
    assert error.value.may_have_published and (case.parent/'parent_observation.json').read_bytes()==b'changed'


@pytest.mark.parametrize('leaf',['parent_observation.json','parent_observation.json.pending'])
def test_existing_parent_target_or_pending_rejected_before_inspection(case,leaf):
    target=case.parent/leaf;target.write_bytes(b'old')
    with pytest.raises(ValueError,match='empty'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:pytest.fail('existing attempt inspected'))
    assert target.read_bytes()==b'old'


def test_changed_parent_directory_is_not_used_for_publication(case):
    old=case.parent.with_name('held_old')
    def inspect(root):case.parent.rename(old);case.parent.mkdir();return claims()
    with pytest.raises(ValueError,match='parent directory changed'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert not list(case.parent.iterdir()) and not list(old.iterdir())


def replace_launcher(case):
    (case.worker/'launcher.json').write_bytes(d.record_image(case.record))


def test_1024_historical_identities_include_owner_and_allow_reused_PID(case):
    r=case.record;w=r['quiescence_witness']
    w['member_identities']=[dict(pid=123,creation_filetime=456+i) for i in range(1024)]
    w['total_processes']=w['observed_unique_member_handles']=1024
    replace_launcher(case)
    saved=d.save_observation(case.parent,case.raw,case.sha,r,lambda root:claims())
    assert saved['observation']['ownership_status']=='quiet_verified'
    assert saved['observation']['inspection_status']=='returned'
    assert saved['parent_record_bytes']>16384 and saved['parent_record_bytes']<=131072
    actual=sum(p.stat().st_size for root in (case.worker,case.parent) for p in root.iterdir())
    assert saved['final_storage_accounting']==dict(bytes=actual,files=3,within_limits=True)


@pytest.mark.parametrize('field,value',[
    ('owner_pid',2**32),('owner_creation_filetime',2**64),('outer_seconds',1),
    ('monitor_error','x'*515),('terminal_bytes',2**64),('exit_code',2**32),
    ('parent_reserved_bytes',16384),('terminal_reserved_files',True),('member_handle_cap',1025)])
def test_unbounded_process_fields_rejected_before_serialization(case,monkeypatch,field,value):
    case.record[field]=value
    original=d.codec.canonical
    def guarded(value):
        assert value is not case.record,'invalid process serialized before bounds'
        return original(value)
    monkeypatch.setattr(d.codec,'canonical',guarded)
    with pytest.raises(ValueError):d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:pytest.fail('bad record inspected'))
    assert not list(case.parent.iterdir())


@pytest.mark.parametrize('kind',['partial','no_owner','missing_history','too_many_history'])
def test_unknown_quiet_never_reads_or_scans_worker(case,monkeypatch,kind):
    r=case.record;w=r['quiescence_witness']
    if kind=='partial':
        r['quiescence_witness']={k:w[k] for k in d.PARTIAL_WITNESS}
    elif kind=='no_owner':r['owner_pid']=r['owner_creation_filetime']=None;r['quiescence_witness']=None
    elif kind=='missing_history':w['total_processes']=2
    else:w['total_processes']=1025
    monkeypatch.setattr(d,'worker_accounting',lambda *a,**kw:pytest.fail('unknown Job scanned'))
    saved=d.save_observation(case.parent,case.raw,case.sha,r,lambda root:pytest.fail('unknown Job inspected'))
    assert saved['final_storage_accounting'] is None
    assert saved['observation']['ownership_status']=='unknown' and saved['observation']['inspection_status']=='skipped'


@pytest.mark.parametrize('fault',['missing_launcher','launcher_bytes','metadata','foreign_parent'])
def test_initial_accounting_binding_never_opens_bad_worker(case,fault):
    if fault=='missing_launcher':(case.worker/'launcher.json').unlink()
    elif fault=='launcher_bytes':(case.worker/'launcher.json').write_bytes(b'changed')
    elif fault=='metadata':(case.worker/'new').touch()
    else:(case.parent/'foreign').write_bytes(b'old')
    if fault=='foreign_parent':
        with pytest.raises(ValueError,match='empty'):d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:pytest.fail('foreign parent inspected'))
        assert (case.parent/'foreign').read_bytes()==b'old';return
    saved=d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:pytest.fail('bad accounting inspected'))
    assert saved['observation']['accounting_error'] is not None and saved['final_storage_accounting'] is None


@pytest.mark.parametrize('phase',['during_inspect','after_write','after_final_readback'])
def test_worker_growth_preserves_final_as_unresolved(case,phase):
    def inspect(root):
        if phase=='during_inspect':(root/'payload').write_bytes(b'changed')
        return claims()
    def hook(stage,path):
        if stage==phase:(case.worker/'growth').touch()
    with pytest.raises(d.OuterObservationUnresolved) as error:
        d.save_observation(case.parent,case.raw,case.sha,case.record,inspect,hook=hook)
    assert error.value.may_have_published and (case.parent/'parent_observation.json').exists()


def test_final_parent_inventory_growth_is_unresolved(case):
    def hook(stage,path):
        if stage=='after_final_readback':(case.parent/'foreign').touch()
    with pytest.raises(d.OuterObservationUnresolved,match='inventory'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:claims(),hook=hook)
    assert (case.parent/'parent_observation.json').exists() and (case.parent/'foreign').exists()


def test_overshot_worker_retains_bounded_failure_and_reports_actual_excess(case):
    r=case.record;r['terminal_bytes']=case.context['limits']['output_bytes']
    (case.worker/'payload').write_bytes(b'x'*r['terminal_bytes']);replace_launcher(case)
    saved=d.save_observation(case.parent,case.raw,case.sha,r,lambda root:pytest.fail('over-cap worker inspected'))
    assert saved['parent_record_saved'] and saved['parent_record_bytes']<131072
    assert saved['observation']['inspection_status']=='skipped'
    assert saved['final_storage_accounting']['within_limits'] is False


def test_parent_actual_length_hard_boundary():
    # Canonical string: two quotes plus an ASCII payload.
    assert len(d.encode_observation('x'*(131072-2)))==131072
    with pytest.raises(ValueError,match='128 KiB'):d.encode_observation('x'*(131072-1))


def test_metadata_accountant_never_returns_monitor_early_prefix(case):
    # Monitoring may stop at the first over-budget entry. Final accounting
    # must visit every bounded entry before returning an actual total.
    limits=dict(case.context['limits'],output_bytes=1,files=1)
    (case.worker/'extra').write_bytes(b'abc')
    assert d.worker_accounting(case.worker,limits)==(sum(p.stat().st_size for p in case.worker.iterdir()),3)


def test_file_mutation_after_stat_is_rejected_by_handle_bookends(case,monkeypatch):
    original=d.codec.ordinary;changed=[]
    def ordinary(path,*a,**kw):
        result=original(path,*a,**kw)
        if Path(path)==case.worker/'payload' and not changed:
            changed.append(True);Path(path).write_bytes(b'longer than the original stat')
        return result
    monkeypatch.setattr(d.codec,'ordinary',ordinary)
    with pytest.raises(ValueError,match='file changed'):d.worker_accounting(case.worker,case.context['limits'])


def test_same_count_worker_root_replacement_is_rejected(case):
    import shutil
    old_root=case.worker.with_name('old_worker')
    def inspect(root):
        root.rename(old_root);shutil.copytree(old_root,root)
        return claims()
    with pytest.raises(d.OuterObservationUnresolved,match='held worker') as error:
        d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert not error.value.may_have_published and not list(case.parent.iterdir())
    assert (old_root/'launcher.json').exists()


def test_equal_length_launcher_drift_is_rejected(case):
    def inspect(root):
        path=root/'launcher.json';raw=path.read_bytes();path.write_bytes(raw.replace(b'123',b'321'))
        assert len(path.read_bytes())==len(raw)
        return claims()
    with pytest.raises(d.OuterObservationUnresolved,match='launcher'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert not list(case.parent.iterdir())


@pytest.mark.parametrize('stage',['inspect','accounting','before_open','after_rename'])
def test_unprintable_errors_keep_failed_or_unresolved_diagnostics(case,monkeypatch,stage):
    class Unprintable(OSError):
        def __str__(self):raise RuntimeError('str failed')
    def fail(*a,**kw):raise Unprintable()
    if stage=='accounting':monkeypatch.setattr(d,'worker_accounting',fail)
    if stage in ('before_open','after_rename'):
        def hook(phase,path):
            if phase==stage:raise Unprintable()
        with pytest.raises(d.OuterObservationUnresolved) as error:
            d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:claims(),hook=hook)
        assert error.value.phase==stage and error.value.may_have_published is (stage=='after_rename')
        assert '[message unavailable]' in str(error.value);return
    saved=d.save_observation(case.parent,case.raw,case.sha,case.record,fail if stage=='inspect' else lambda root:claims())
    detail=saved['observation']['inspection_error' if stage=='inspect' else 'accounting_error']
    assert '[message unavailable]' in detail['message'] and saved['scientific_evidence_adopted'] is False


def test_parent_change_during_final_worker_scan_is_not_reported_saved(case,monkeypatch):
    original=d.worker_accounting
    def accounting(*a,**kw):
        result=original(*a,**kw)
        target=case.parent/'parent_observation.json'
        if target.exists():target.write_bytes(b'changed')
        return result
    monkeypatch.setattr(d,'worker_accounting',accounting)
    with pytest.raises(d.OuterObservationUnresolved,match='final accounting bookend'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:claims())
    assert (case.parent/'parent_observation.json').read_bytes()==b'changed'


def test_short_real_guard_launcher_and_parent_are_connected(case):
    import sys
    from src import staged_rts24_process_guard_v3 as guard
    # The only spawned work is a fraction-second Python sleep. Publishing
    # this test launcher is a pytest fixture, not a production outer.
    (case.worker/'launcher.json').unlink()
    record=guard.supervise([sys.executable,'-B','-s','-c','import time; time.sleep(.3)'],cwd=case.worker,
        output=case.worker,progress=case.worker/'events',limits=dict(case.context['limits'],wall_seconds=5,no_progress_seconds=5))
    assert record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed']
    d.codec.publish(case.worker/'launcher.json',guard.record_image(record))
    saved=d.save_observation(case.parent,case.raw,case.sha,record,lambda root:claims())
    assert saved['observation']['inspection_status']=='returned' and saved['final_storage_accounting']['within_limits']
    assert saved['final_storage_accounting']['bytes']==sum(p.stat().st_size for root in (case.worker,case.parent) for p in root.iterdir())


def test_maximal_record_and_parent_encoding_fit_independent_upper_bound(case):
    r=case.record
    for key in ('samples','peak_job_commit_bytes','terminal_bytes','terminal_files','sampled_tree_peak_rss_bytes'):r[key]=2**64-1
    r['exit_code']=2**32-1;r['outer_seconds']=float.fromhex('0x1.fffffffffffffp+1023')
    r['owner_pid']=2**32-1;r['owner_creation_filetime']=2**64-1
    for key in ('monitor_error','cleanup_error','stop_reason'):r[key]='\U0001f600'*514
    w=r['quiescence_witness'];w['active_processes']=w['total_processes']=w['observed_unique_member_handles']=2**32-1
    w['member_identities']=[dict(pid=2**32-1,creation_filetime=2**64-1-i) for i in range(1024)]
    w['final_pids']=[2**32-1-i for i in range(1024)]
    saved=d.save_observation(case.parent,case.raw,case.sha,r,lambda root:pytest.fail('max failed record inspected'))
    observation=saved['observation'];observation['ownership_status']='quiet_verified'
    observation['inspection_status']='returned';observation['caller_supplied_mechanical_claims']=claims()
    for key in ('completion_core_sha','inventory_sha','report_sha'):observation['caller_supplied_mechanical_claims'][key]='f'*64
    for key in ('inspection_error','accounting_error'):observation[key]=dict(type='\U0001f600'*64,message='\U0001f600'*256)
    raw=json.dumps(observation,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    process_raw=json.dumps(d.process_snapshot(r),ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    # 32 is a conservative finite-binary64 JSON scalar bound; round both
    # remaining nullable/bool alternatives up to their longest spelling.
    parent_bound=len(raw)+32+256
    process_bound=len(process_raw)+32+256
    assert d.encode_observation(observation)==raw and d.record_image(r)==process_raw
    assert max(parent_bound,process_bound)<131072
    print(json.dumps(dict(oracle='bounded_maximal_canonical_records',members=1024,member_array_bytes=len(json.dumps(
        w['member_identities'],sort_keys=True,separators=(',',':')).encode()),process_bytes=len(process_raw),
        parent_bytes=len(raw),process_conservative_bound=process_bound,parent_conservative_bound=parent_bound)))
