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
phase,pin=sys.argv[1:]
if phase not in ('baseline','candidate'):raise ValueError('one fixed postcheck phase required')
plan_raw=(HERE/'source_reader_input_postcheck_plan_01.json').read_bytes()
if sha256(plan_raw).hexdigest()!=pin:raise ValueError('postcheck plan differs')
plan=json.loads(plan_raw)
if sha256(Path(__file__).read_bytes()).hexdigest()!=plan['checker_sha256']:raise ValueError('checker bytes differ')
out=HERE/f'source_reader_input_postcheck_01_{phase}_non_authoritative';out.mkdir(exist_ok=False)
result=dict(exit_code=1,phase=phase,plan_sha256=pin,formal_result=False,
    resource_admission=False,full_hour0_chain_passed=False,
    baseline_transient_lock_ABA_observed=False,input_preservation_scope='current canonical files and releasable locks')


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
    for name,digest in plan['fixed_evidence_sha256'].items():
        if sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('fixed evidence differs: '+name)
    for name,digest in plan['implementation_sha256'].items():
        if sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('fixed implementation differs')
    folder=Path(plan[phase+'_monitor']);terminal_raw=(folder/'terminal.json').read_bytes()
    terminal=json.loads(terminal_raw)
    if terminal['exit_code']!=0 or not terminal['observed_owned_processes_absent']:
        raise ValueError('successful mode terminal required')
    for row in (*plan['owned_input_processes'],*terminal['observed_owned_processes']):
        try:
            if psutil.Process(row['pid']).create_time()==row['creation_time']:
                raise ValueError('related owned process still active')
        except psutil.NoSuchProcess:pass
    base=Path(plan['input_root']);expected=plan['relative_files_sha256']
    actual={p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file() or p.is_symlink()}
    if actual!=set(expected) or len(actual)!=134:raise ValueError('exact 134-file input inventory differs')
    identities={}
    for name,digest in expected.items():
        path=base/name
        if not path.is_relative_to(base):raise ValueError('input path escaped fixed own root')
        raw,identity=stable(path)
        if sha256(raw).hexdigest()!=digest:raise ValueError('input bytes differ: '+name)
        identities[name]=identity
    locked=[]
    for name in plan['relative_locks']:
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
        relative_files_sha256=expected,mode_terminal_sha256=sha256(terminal_raw).hexdigest())
except BaseException:result['error']=traceback.format_exc()
with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({key:value for key,value in result.items() if key!='relative_files_sha256'}))
raise SystemExit(result['exit_code'])
