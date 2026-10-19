"""Bind the wall-cap outcome and saved Job without adopting journal suffixes."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
out=HERE/'bootstrap5_n0_registration_137';base=Path('D:/h1_bootstrap5_n0_137_non_authoritative')
plan_path=D/'bootstrap5_n0_bounded_plan_137.json';request_path=out/'request.json';terminal_path=out/'terminal.json'
plan=json.loads(plan_path.read_bytes());request=json.loads(request_path.read_bytes());terminal=json.loads(terminal_path.read_bytes())
assert sha256(request_path.read_bytes()).hexdigest()==terminal['request_sha256']
assert terminal['exit_code']==15 and terminal['stop_reason']=='wall'
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
drift=[name for name,pin in plan['files_sha256'].items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['source_unchanged']
def item(path):
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest())
invocation_path=next(base.glob('*/n0_invocation.json'));invocation=json.loads(invocation_path.read_bytes())
assert invocation['kwargs']==plan['invocation']['kwargs']==dict(registered_development=True)
assert invocation['pytest_nodeid'] in request['command']
post_names=('n0_registry_execution_receipt.json','n0_retained_heads.json','n0_registration_report.json',
            'n0_phase_segments_closed.json','unit_code_read_lease_closed.json')
post_files={name:[item(p) for p in base.glob('**/'+name)] for name in post_names}
xml_path=base/'registered_development_true.xml'
junit=dict(present=xml_path.exists(),successful_target_testcase=False)
if xml_path.exists():
    tree=ET.parse(xml_path);cases=list(tree.getroot().iter('testcase'))
    junit.update(artifact=item(xml_path),testcases=len(cases),
        cases=[dict(name=c.get('name'),properties={p.get('name'):p.get('value') for p in c.findall('./properties/property')},
            failures=len(c.findall('failure')),errors=len(c.findall('error')),skips=len(c.findall('skipped'))) for c in cases])
jobs=[]
for path in base.glob('nt_non_authoritative/episodes/*/controller_non_authoritative/job_000_non_authoritative/observation.json'):
    observed=json.loads(path.read_bytes());jobs.append(dict(artifact=item(path),observation=observed))
assert len(jobs)==1 and jobs[0]['observation']['exit_code']==0 and jobs[0]['observation']['whole_job_quiescent']
locks=[]
for path in sorted((base/'nt_non_authoritative').rglob('execution.lock')):
    before=sha256(path.read_bytes()).hexdigest();info=path.stat(follow_symlinks=False)
    assert stat.S_ISREG(info.st_mode) and not info.st_file_attributes&0x400 and info.st_size==1
    with path.open('r+b',buffering=0) as stream:
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    assert sha256(path.read_bytes()).hexdigest()==before
    locks.append(dict(path=str(path),sha256=before,reacquired_and_released=True))
stages=[]
for line in (out/'stdout.log').read_text().splitlines():
    try:value=json.loads(line)
    except json.JSONDecodeError:continue
    if type(value) is dict and ('stage' in value or 'label' in value):stages.append(value)
assert not any(post_files.values()) and not junit['present']
value=dict(schema='h1_bootstrap5_n0_bounded_result_137',status='INCOMPLETE_WALL_CAP_NONAUTHORITATIVE',
    plan=item(plan_path),request=item(request_path),terminal_artifact=item(terminal_path),
    invocation_artifact=item(invocation_path),invocation=invocation,junit=junit,terminal=terminal,
    planned_pins=len(plan['files_sha256']),pin_drift=drift,stages=stages,job_observations=jobs,
    post_call_artifacts=post_files,saved_lock_probes=locks,
    public_registered_N0_return_observed=False,numerical_oracle_equality_observed=False,
    internal_graceful_cleanup_proven=False,externally_persisted_retained_heads_available=False,
    saved_journal_suffix_adopted=False,controller_candidate_archive_available=True,
    interpretation='One synthetic Windows Job exited0/whole Job quiet51.125s;8 retention heartbeats observed. '
        'No successful public return, registry receipt, retained heads, numerical oracle, JUnit or phase-close artifacts. '
        'Journal suffix bytes are candidates only and are not externally authenticated owner heads. '
        'OS process/lock cleanup does not prove internal cache/alias restoration.',
    next_question='Use a zero-execution or saved-candidate diagnostic to profile the remaining validation/entry cost; '
        'reuse completed Job candidate bytes for independent numerical inspection where possible. '
        'Do not extend300s or repeat the unchanged prefix; do not resume an owner without externally retained heads.',
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
target=D/'bootstrap5_n0_bounded_result_137.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),
    planned_pins=value['planned_pins'],pin_drift=drift,locks=len(locks),job_seconds=jobs[0]['observation']['elapsed_seconds'])))
