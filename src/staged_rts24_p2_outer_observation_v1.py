"""Draft parent-observation publication only; no launcher or scientific adoption."""
from hashlib import sha256
import json
import math
import os
from pathlib import Path

from src import staged_rts24_evidence_store_v1 as codec

CAPS=dict(wall_seconds=3600,no_progress_seconds=65,rss_bytes=1024**3,output_bytes=64*1024**2,files=8192)
CONTEXT_KEYS={'schema','authority','worker_root','parent_root','limits','kernel_registration_sha',
    'public_execution_enabled','native_authorized','resource_admission'}
PROCESS_KEYS={'exit_code','stop_reason','monitor_error','cleanup_error','job_quiet_confirmed','outer_seconds',
    'sampled_tree_peak_rss_bytes','rss_observation_available','peak_job_commit_bytes','samples',
    'terminal_bytes','terminal_files','terminal_reserved_bytes','owner_pid','owner_creation_filetime','quiescence_witness'}
CLAIM_KEYS={'inspection_scope','completion_core_sha','inventory_sha','report_sha','point_references',
    'contract_rows','mechanical_package_integrity','unverified_worker_claims'}


def require(value,message):
    if not value:raise ValueError(message)


def integer(value,minimum=0):return type(value) is int and value>=minimum


def nullable_sha(value):
    return value is None or type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def mechanical_claims(value):
    require(type(value) is dict and set(value)==CLAIM_KEYS,'closed mechanical claim fields required')
    require(value['inspection_scope']=='caller_supplied_mechanical','mechanical inspection scope differs')
    require(all(nullable_sha(value[n]) for n in ('completion_core_sha','inventory_sha','report_sha')),'mechanical pin differs')
    require(integer(value['point_references']) and value['point_references']<=319
        and integer(value['contract_rows']) and value['contract_rows']<=138,'mechanical count differs')
    require(type(value['mechanical_package_integrity']) is bool,'mechanical integrity scalar differs')
    worker=value['unverified_worker_claims']
    require(type(worker) is dict and set(worker)=={'full_139_executed','package_complete'}
        and all(v is None or type(v) is bool for v in worker.values()),'unverified worker claim fields differ')
    return json.loads(codec.canonical(value))


def canonical_context(value):
    require(type(value) is dict and set(value)==CONTEXT_KEYS,'closed development context required')
    fixed=dict(schema='staged_rts24_P2_parent_observation_development_v1',authority='DRAFT_NONAUTHORITATIVE',
        public_execution_enabled=False,native_authorized=False,resource_admission=False)
    require(codec.canonical({k:value[k] for k in fixed})==codec.canonical(fixed),'context authority differs')
    require(nullable_sha(value['kernel_registration_sha']),'context registration identity differs')
    require(type(value['limits']) is dict and set(value['limits'])==set(CAPS),'context limit fields differ')
    for key,cap in CAPS.items():
        v=value['limits'][key]
        require(type(v) in (int,float) and math.isfinite(v) and 0<v<=cap,'context proposal cap')
        if key in ('rss_bytes','output_bytes','files'):require(type(v) is int,'integer cap required')
    paths=[]
    for name in ('worker_root','parent_root'):
        raw=value[name];require(type(raw) is str,'context path type')
        path=Path(raw);require(path.is_absolute() and '..' not in path.parts and str(path.absolute())==raw,'canonical absolute context path required')
        paths.append(path)
    require(not paths[0].is_relative_to(paths[1]) and not paths[1].is_relative_to(paths[0]),'parent and worker roots overlap')
    return codec.canonical(value)


def assess_process(record,limits):
    require(type(record) is dict and set(record)==PROCESS_KEYS,'closed supervisor record required')
    snapshot=json.loads(codec.canonical(record))
    require(snapshot['exit_code'] is None or type(snapshot['exit_code']) is int,'invalid exit code')
    require(type(snapshot['job_quiet_confirmed']) is bool,'invalid quiet observation')
    for name in ('stop_reason','monitor_error','cleanup_error'):
        require(snapshot[name] is None or type(snapshot[name]) is str,'invalid process error observation')
    require(type(snapshot['outer_seconds']) in (int,float) and math.isfinite(snapshot['outer_seconds'])
        and snapshot['outer_seconds']>=0,'invalid process wall observation')
    require(all(integer(snapshot[n]) for n in ('samples','peak_job_commit_bytes','terminal_bytes','terminal_files','terminal_reserved_bytes')),'invalid process counts')
    require(type(snapshot['rss_observation_available']) is bool and (snapshot['sampled_tree_peak_rss_bytes'] is None
        or integer(snapshot['sampled_tree_peak_rss_bytes'])),'invalid RSS observation')
    witness=snapshot['quiescence_witness'];quiet=False
    if type(witness) is dict and set(witness)=={'active_processes','all_handles_signaled','complete_inventory','final_pids',
            'member_identities','observed_unique_member_handles','total_processes'}:
        members=witness['member_identities']
        valid=type(members) is list and all(type(m) is dict and set(m)=={'pid','creation_filetime'}
            and integer(m['pid'],1) and integer(m['creation_filetime'],1) for m in members)
        if valid:
            identities={(m['pid'],m['creation_filetime']) for m in members}
            quiet=(snapshot['job_quiet_confirmed'] is True and snapshot['cleanup_error'] is None
                and integer(witness['active_processes']) and witness['active_processes']==0 and witness['final_pids']==[]
                and witness['all_handles_signaled'] is True and witness['complete_inventory'] is True
                and integer(witness['total_processes'],1) and witness['total_processes']<=1024
                and integer(witness['observed_unique_member_handles'],1)
                and witness['total_processes']==witness['observed_unique_member_handles']==len(members)==len(identities)
                and integer(snapshot['owner_pid'],1) and integer(snapshot['owner_creation_filetime'],1)
                and (snapshot['owner_pid'],snapshot['owner_creation_filetime']) in identities)
    exit_ok=snapshot['exit_code']==0 and type(snapshot['exit_code']) is int and all(snapshot[n] is None for n in ('stop_reason','monitor_error','cleanup_error'))
    caps_ok=(snapshot['outer_seconds']<=limits['wall_seconds'] and snapshot['terminal_files']+1<=limits['files']
        and snapshot['terminal_reserved_bytes']==16384
        and snapshot['terminal_bytes']+snapshot['terminal_reserved_bytes']<=limits['output_bytes']
        and snapshot['peak_job_commit_bytes']<=2*1024**3 and snapshot['rss_observation_available'] is True
        and snapshot['samples']>0 and integer(snapshot['sampled_tree_peak_rss_bytes'])
        and snapshot['sampled_tree_peak_rss_bytes']<=limits['rss_bytes'])
    return dict(execution_status='successful_exit' if exit_ok else 'failed_or_unknown',
        ownership_status='quiet_verified' if quiet else 'unknown',proposal_caps_satisfied=bool(caps_ok),
        inspection_permitted=bool(quiet and exit_ok and caps_ok),process_snapshot=snapshot)


class OuterObservationUnresolved(OSError):
    def __init__(self,phase,expected_sha,may_have_published,cause):
        super().__init__(f'{phase}: {type(cause).__name__}: {cause}')
        self.phase,self.expected_sha,self.may_have_published=phase,expected_sha,may_have_published
        self.publication_outcome='unknown' if may_have_published else 'not_published'
        self.scientific_evidence_adopted=False
        self.worker_terminal_status='not_independently_replayed'


def save_observation(parent_root,context_bytes,expected_context_sha,process_record,inspect_after_quiet,hook=None):
    require(type(context_bytes) is bytes and sha256(context_bytes).hexdigest()==expected_context_sha,'held context SHA differs')
    context=json.loads(context_bytes)
    require(canonical_context(context)==context_bytes,'held context is not canonical')
    parent=Path(parent_root).absolute()
    require(str(parent)==context['parent_root'],'parent path differs from held context')
    assessment=assess_process(process_record,context['limits'])
    directories=codec.directory_identity(parent)
    target=parent/'parent_observation.json'
    require(not os.path.lexists(target) and not os.path.lexists(target.with_name(target.name+'.pending')),'parent observation already exists')
    claims=None;error=None;inspection='skipped'
    if assessment['inspection_permitted']:
        try:
            worker=codec.directory_chain(Path(context['worker_root']))
            require(not worker.resolve().is_relative_to(parent.resolve()) and not parent.resolve().is_relative_to(worker.resolve()),'physical worker and parent roots overlap')
            claims=mechanical_claims(inspect_after_quiet(worker));inspection='returned'
        except Exception as exc:
            claims=None;inspection='failed';error=dict(type=type(exc).__name__,message=str(exc)[:256])
    require(codec.directory_identity(parent)==directories,'parent directory changed during inspection')
    observation=dict(authority='DRAFT_NONAUTHORITATIVE',scope='parent process and caller-supplied mechanical observation only',
        context_sha=expected_context_sha,**assessment,inspection_status=inspection,inspection_error=error,
        caller_supplied_mechanical_claims=claims,worker_terminal_status='not_independently_replayed',
        source_freshness_independently_verified=False,scientific_audit_replayed=False,scientific_evidence_adopted=False,
        full_139_independently_verified=False,fx_temporal_backing=False,resource_admission=False,formal_result=False)
    raw=codec.canonical(observation);expected=sha256(raw).hexdigest()
    try:
        actual=codec.publish(target,raw,hook)
        require(actual==expected and codec.read_bytes(target)==raw and codec.directory_identity(parent)==directories,'parent record post-publication readback differs')
    except codec.PublicationError as exc:
        raise OuterObservationUnresolved(exc.phase,expected,exc.may_have_published,exc) from exc
    except Exception as exc:
        raise OuterObservationUnresolved('parent_record_bookend',expected,target.exists(),exc) from exc
    return dict(parent_record_sha=expected,parent_record_saved=True,observation=observation,
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
