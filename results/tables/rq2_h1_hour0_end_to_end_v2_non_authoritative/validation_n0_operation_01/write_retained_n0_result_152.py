"""Record either terminal honestly; preserve external retention and candidate bytes."""
from hashlib import sha256
import json
import msvcrt
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
base=Path('D:/h1_bootstrap5_retained_152_non_authoritative');out=HERE/'bootstrap5_retained_n0_152'
plan_path=D/'bootstrap5_retained_n0_bounded_plan_152.json';plan=json.loads(plan_path.read_bytes())
terminal_path=out/'terminal.json';terminal=json.loads(terminal_path.read_bytes())
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert terminal['request_sha256']==sha256((out/'request.json').read_bytes()).hexdigest()
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['source_unchanged']
archive=D/'retained_n0_152_preserved_non_authoritative';archive.mkdir(exist_ok=False)
copies=[]
def preserve(source,relative):
    raw=source.read_bytes();target=archive/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    row=dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest(),bytes=len(raw))
    copies.append(row);return row

saved=[];saved_root=base/'nt_non_authoritative';pending=[saved_root] if saved_root.exists() else []
while pending:
    directory=pending.pop()
    for entry in os.scandir(directory):
        info=entry.stat(follow_symlinks=False)
        assert not getattr(info,'st_file_attributes',0)&0x400
        if entry.is_dir(follow_symlinks=False):
            if entry.name!='scratch_non_authoritative':pending.append(Path(entry.path))
        else:saved.append(Path(entry.path))
    assert len(saved)<=1024
assert sum(p.stat().st_size for p in saved)<128*1024**2
for source in sorted(saved):preserve(source,Path('saved_candidate')/source.relative_to(saved_root))

retention_dirs=list(base.glob('*/external_retention_non_authoritative'));assert len(retention_dirs)<=1
records=[];heads={};root_counts={};previous=None
for directory in retention_dirs:
    for path in sorted(directory.glob('[0-9][0-9][0-9][0-9].json')):
        raw=path.read_bytes();row=json.loads(raw);index=len(records)+1
        assert row['sequence']==index and path.name==f'{index:04d}.json'
        assert row['previous_retention_sha256']==previous
        root=Path(row['root']);assert root.is_relative_to(base)
        genesis=sha256((root/'header.json').read_bytes()).hexdigest()
        assert row['before']==heads.get(str(root),genesis)
        ordinal=root_counts.get(str(root),0)+1
        event_path=root/f'{ordinal:020d}.json';event=event_path.read_bytes()
        event_value=json.loads(event)
        assert event_value['sequence']==ordinal and event_value['previous']==row['before']
        assert sha256(event).hexdigest()==row['after']
        heads[str(root)]=row['after'];root_counts[str(root)]=ordinal
        assert row['retained_heads']==heads and row['formal_result'] is False and row['diagnostic_only'] is True
        previous=sha256(raw).hexdigest();records.append(dict(record=row,sha256=previous))
    for source in directory.iterdir():
        if source.is_file():preserve(source,Path('external_retention')/source.name)

suffixes=[]
for name,count in root_counts.items():
    files=list(Path(name).glob('[0-9]*.json'))
    suffixes.append(dict(root=name,externally_retained_events=count,journal_events=len(files),
                         unretained_suffix_present=len(files)>count))
post_names=('n0_invocation.json','n0_registry_execution_receipt.json','n0_retained_heads.json',
    'n0_registration_report.json','n0_phase_segments_closed.json','identity_bookends.json')
post={}
for name in post_names:
    paths=list(base.glob('*/'+name));assert len(paths)<=1
    post[name]=None if not paths else dict(artifact=preserve(paths[0],Path('post')/name),value=json.loads(paths[0].read_bytes()))
entry_path=base/'unit_code_read_lease_closed.json'
entry=None
if entry_path.exists():
    preserve(entry_path,Path('post')/entry_path.name);entry=json.loads(entry_path.read_bytes())
xml=base/'registered_development_true.xml';junit=None
if xml.exists():
    preserve(xml,Path('post')/xml.name);cases=list(ET.parse(xml).getroot().iter('testcase'))
    junit=[dict(name=c.get('name'),properties={p.get('name'):p.get('value') for p in c.findall('./properties/property')},
        errors=len(c.findall('error')),failures=len(c.findall('failure')),skips=len(c.findall('skipped'))) for c in cases]
jobs=[dict(path=str(p),observation=json.loads(p.read_bytes())) for p in saved if p.name=='observation.json' and p.parent.name=='job_000_non_authoritative']
assert len(jobs)<=1
locks=[]
for path in sorted(p for p in saved if p.name=='execution.lock'):
    before=path.read_bytes();info=path.stat(follow_symlinks=False)
    assert stat.S_ISREG(info.st_mode) and not info.st_file_attributes&0x400 and info.st_size==1
    with path.open('r+b',buffering=0) as stream:
        msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);stream.seek(0)
        msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    assert path.read_bytes()==before
    locks.append(dict(path=str(path),sha256=sha256(before).hexdigest(),reacquired_and_released=True))
returned=None
if retention_dirs:
    path=retention_dirs[0]/'public_bootstrap_return.json'
    if path.exists():
        returned=json.loads(path.read_bytes());exact=(path.parent/'returned_execution_receipt.json').read_bytes()
        assert sha256(exact).hexdigest()==returned['returned_execution_receipt_sha256']
        assert json.loads(exact)==returned['N0_validation_execution_receipt']
complete=terminal['exit_code']==0 and returned is not None and all(post[name] is not None for name in post_names)
complete=complete and entry is not None and junit is not None and len(junit)==1
if complete:
    receipt=post['n0_registry_execution_receipt.json']['value']
    assert receipt['complete'] and receipt['confirmed_builds']==4 and receipt['context_observations']==64
    assert receipt['full_numerical_hour_replays']==4 and receipt['fresh_byte_context_revalidations']==28
    assert not any(junit[0][k] for k in ('errors','failures','skips'))
    assert len(jobs)==1 and jobs[0]['observation']['exit_code']==0 and jobs[0]['observation']['whole_job_quiescent']
    assert post['n0_phase_segments_closed.json']['value']['receipt']['all_segments_closed']
    assert not any(row['unretained_suffix_present'] for row in suffixes)
value=dict(schema='h1_bootstrap5_retained_n0_bounded_result_152',
    status='VERIFIED_PUBLIC_DEVELOPMENT_N0_RETURN_AND_CLOSE' if complete else 'INCOMPLETE_DEVELOPMENT_DIAGNOSTIC',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,
    planned_pins=len(plan['files_sha256']),pin_drift=drift,archive_files=copies,saved_candidate_files=len(saved),
    externally_persisted_retention_records=records,retained_heads=heads,journal_suffix_observations=suffixes,
    post_call_artifacts=post,entry_closed=entry,junit=junit,job_observations=jobs,saved_lock_probes=locks,
    public_return_observed=returned is not None,public_development_N0_return_and_close_verified=bool(complete),
    actual_return=returned,saved_journal_suffix_adopted=False,
    internal_graceful_cleanup_proven=bool(complete),predecessor_numerical_oracle_verified=False,N0_reopen_verified=False,
    synthetic_N0_Jobs=len(jobs),real_native_calls=0,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
target=D/'bootstrap5_retained_n0_bounded_result_152.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),status=value['status'],
    pins=len(plan['files_sha256']),drift=drift,retentions=len(records),saved=len(saved),locks=len(locks),
    public_return=returned is not None,job_seconds=[v['observation']['elapsed_seconds'] for v in jobs])))
