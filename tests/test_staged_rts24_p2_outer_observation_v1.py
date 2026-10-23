"""Temporary parent observations, generic publication faults, no P2/native run."""
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from src import staged_rts24_p2_outer_observation_v1 as d


def process():
    return dict(exit_code=0,stop_reason=None,monitor_error=None,cleanup_error=None,job_quiet_confirmed=True,
        outer_seconds=.1,sampled_tree_peak_rss_bytes=1024,rss_observation_available=True,peak_job_commit_bytes=2048,
        samples=1,terminal_bytes=100,terminal_files=1,terminal_reserved_bytes=16384,owner_pid=123,owner_creation_filetime=456,
        quiescence_witness=dict(active_processes=0,all_handles_signaled=True,complete_inventory=True,final_pids=[],
            member_identities=[dict(pid=123,creation_filetime=456)],observed_unique_member_handles=1,total_processes=1))


def claims():
    return dict(inspection_scope='caller_supplied_mechanical',completion_core_sha=None,inventory_sha=None,report_sha=None,
        point_references=319,contract_rows=138,mechanical_package_integrity=True,
        unverified_worker_claims=dict(full_139_executed=True,package_complete=True))


@pytest.fixture
def case(tmp_path):
    worker=tmp_path/'worker';parent=tmp_path/'parent';worker.mkdir();parent.mkdir()
    value=dict(schema='staged_rts24_P2_parent_observation_development_v1',authority='DRAFT_NONAUTHORITATIVE',
        worker_root=str(worker),parent_root=str(parent),limits=dict(d.CAPS),kernel_registration_sha=None,
        public_execution_enabled=False,native_authorized=False,resource_admission=False)
    raw=d.canonical_context(value)
    return SimpleNamespace(worker=worker,parent=parent,context=value,raw=raw,sha=d.sha256(raw).hexdigest(),record=process())


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
    with pytest.raises(ValueError,match='already exists'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,lambda root:pytest.fail('existing attempt inspected'))
    assert target.read_bytes()==b'old'


def test_changed_parent_directory_is_not_used_for_publication(case):
    old=case.parent.with_name('held_old')
    def inspect(root):case.parent.rename(old);case.parent.mkdir();return claims()
    with pytest.raises(ValueError,match='parent directory changed'):
        d.save_observation(case.parent,case.raw,case.sha,case.record,inspect)
    assert not list(case.parent.iterdir()) and not list(old.iterdir())
