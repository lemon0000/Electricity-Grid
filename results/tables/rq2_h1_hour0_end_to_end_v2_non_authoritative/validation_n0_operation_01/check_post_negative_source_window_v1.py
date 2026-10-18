"""Additive current-state check; does not reconstruct unobserved baseline ABA."""
from hashlib import sha256
import json
import msvcrt
import os
from pathlib import Path
import stat
import sys
import traceback

import psutil

HERE=Path(__file__).resolve().parent
pin,checker_pin=sys.argv[1:]
plan_raw=(HERE/'post_negative_source_window_plan_02.json').read_bytes()
if sha256(plan_raw).hexdigest()!=pin or sha256(Path(__file__).read_bytes()).hexdigest()!=checker_pin:
    raise ValueError('externally fixed diagnostic or postchecker bytes differ')
plan=json.loads(plan_raw)
out=HERE/'post_negative_source_window_postcheck_02_non_authoritative';out.mkdir(exist_ok=False)
result=dict(exit_code=1,plan_sha256=pin,checker_sha256=checker_pin,formal_result=False,
    resource_admission=False,full_hour0_chain_passed=False,native_execution_authorized=False,
    baseline_transient_lock_ABA_observed=False,input_preservation_scope='current canonical files and releasable locks',
    observation_contract='endpoint freshness; complete dynamic closure and transient ABA not proved',
    parent_host_and_transport_are_explicit_fakes=True,
    standalone_post_negative_validation_scope=True)



def stable(path):
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_file_attributes&0x400 or before.st_nlink!=1:
        raise ValueError('regular single-link non-reparse input required')
    with path.open('rb') as stream:
        first=os.fstat(stream.fileno());raw=stream.read(before.st_size+1);last=os.fstat(stream.fileno())
    after=path.lstat()
    fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
    view=lambda value:tuple(getattr(value,key) for key in fields)
    if (view(before)!=view(after) or view(first)!=view(last) or view(before)[:4]!=view(first)[:4]
            or len(raw)!=before.st_size):raise ValueError('input changed during postcheck')
    return raw,(before.st_dev,before.st_ino)


try:
    for key in ('source_sha256','saved_sha256','old_chain_sha256'):
        for name,digest in plan[key].items():
            if sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('fixed input differs: '+name)
    folder=Path(plan['outer_output']);terminal_raw=(folder/'terminal.json').read_bytes();terminal=json.loads(terminal_raw)
    if (terminal['exit_code']!=0 or terminal['child_exit_code']!=0 or terminal['inner_exit_code']!=0
            or not terminal['observed_owned_processes_absent'] or terminal['stop_reason'] is not None
            or terminal['errors'] or any(not terminal[k+'_unchanged'] for k in ('source','saved','old_chain'))):
        raise ValueError('complete successful observed diagnostic terminal required')
    inner_raw=(Path(plan['inner_output'])/'terminal.json').read_bytes();inner=json.loads(inner_raw)
    if sha256(inner_raw).hexdigest()!=terminal['inner_terminal_sha256']:raise ValueError('inner terminal differs')
    if (inner['exit_code']!=0 or inner['original_source_prepares']!=2 or inner['window_source_prepares']!=2
            or inner['logical_borrowed_source_returns']!=160
            or inner['complete_source_projection_sha256']!=plan['expected_complete_projection_sha256']
            or any(not inner[k] for k in ('decision_audit_bytes_equal','complete_source_fields_equal',
                'fake_transport_guards_released','actual_source_dispatch_guard_retained',
                'parent_host_and_transport_are_explicit_fakes'))):raise ValueError('real-source window evidence differs')
    if any(inner[k] for k in ('formal_result','resource_admission','native_execution_authorized',
            'full_hour0_chain_passed','live_Parent_credential_issued','full_Parent_or_Handoff_acceptance',
            'complete_dynamic_input_closure_proved','unobserved_between_bookends_ABA_covered')):
        raise ValueError('diagnostic must retain its limited scope and all formal gates false')
    for row in (*plan['completed_input_owned_processes'],*terminal['observed_owned_processes']):
        try:
            if psutil.Process(row['pid']).create_time()==row['creation_time']:raise ValueError('related owned process still active')
        except psutil.NoSuchProcess:pass
    base=Path(plan['path_roots'][1]);expected=plan['relative_input_files_sha256']
    if base!=Path('D:/h1_fresh_owned_source_cost_03_non_authoritative'):raise ValueError('completed own-root required')
    actual={p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() or p.is_symlink()}
    if actual!=set(expected) or len(actual)!=134:raise ValueError('exact134-file input inventory differs')
    identities={}
    for name,digest in expected.items():
        path=base/name
        if not path.is_relative_to(base):raise ValueError('input path escaped fixed own root')
        raw,identity=stable(path)
        if sha256(raw).hexdigest()!=digest:raise ValueError('input bytes differ: '+name)
        identities[name]=identity
    locked=[]
    for name in plan['relative_input_locks']:
        path=base/name
        with path.open('r+b',buffering=0) as stream:
            info=os.fstat(stream.fileno())
            if (info.st_dev,info.st_ino)!=identities[name]:raise ValueError('lock identity changed')
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            try:
                stream.seek(0)
                if stream.read()!=b'0':raise ValueError('canonical lock bytes differ')
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        if stable(path)[0]!=b'0':raise ValueError('lock changed after release')
        locked.append(name)
    if len(locked)!=10 or len(set(locked))!=10:raise ValueError('exact ten locks required')
    if {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() or p.is_symlink()}!=actual:
        raise ValueError('inventory changed during postcheck')
    result.update(exit_code=0,regular_input_files=134,locked_and_released=locked,
        relative_files_sha256=expected,mode_terminal_sha256=sha256(terminal_raw).hexdigest(),
        inner_terminal_sha256=sha256(inner_raw).hexdigest(),source_pins_checked=len(plan['source_sha256']),
        old_chain_pins_checked=len(plan['old_chain_sha256']),original_source_prepares=2,logical_returns=160)
except BaseException:result['error']=traceback.format_exc()
with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({key:value for key,value in result.items() if key!='relative_files_sha256'}))
raise SystemExit(result['exit_code'])
