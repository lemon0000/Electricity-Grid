"""Stdlib-only P1 saved-set arithmetic and conditional P2 record sizing."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import stat

ROOT=Path(__file__).resolve().parents[4]
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')

def pairs(items):
    value={}
    for key,item in items:
        assert key not in value
        value[key]=item
    return value

def directory_ids(path):
    result=[]
    for item in reversed((path,*path.parents)):
        info=item.lstat();assert stat.S_ISDIR(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400
        result.append((str(item),info.st_dev,info.st_ino))
    return result

def read(path):
    def identity(info):return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns
    dirs=directory_ids(path.parent);before=path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and not getattr(before,'st_file_attributes',0)&0x400 and before.st_size<=65536
    with path.open('rb') as stream:
        assert identity(os.fstat(stream.fileno()))==identity(before)
        raw=stream.read(before.st_size+1)
        assert identity(os.fstat(stream.fileno()))==identity(before)
    assert identity(path.lstat())==identity(before) and len(raw)==before.st_size and directory_ids(path.parent)==dirs
    return raw

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def members(record):
    witness=record['quiescence_witness']
    assert set(witness)==set('active_processes all_handles_signaled complete_inventory final_pids member_identities observed_unique_member_handles total_processes'.split())
    identities=[(m['pid'],m['creation_filetime']) for m in witness['member_identities']]
    assert len(identities)==len(set(identities))==witness['observed_unique_member_handles']==witness['total_processes']
    assert (record['owner_pid'],record['owner_creation_filetime']) in identities
    assert record['job_quiet_confirmed'] is True and record['exit_code']==0 and record['stop_reason'] is record['monitor_error'] is record['cleanup_error'] is None
    assert witness['active_processes']==0 and witness['final_pids']==[] and witness['all_handles_signaled'] is witness['complete_inventory'] is True
    return set(identities)

def main():
    names=['launcher.json',*[f'points/point_{i:04d}/process.json' for i in range(1,32)],'fresh_process.json']
    raw={name:read(P1/name) for name in names}
    values={name:json.loads(data,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x))) for name,data in raw.items()}
    assert all(canonical(values[n])==b for n,b in raw.items()) and sum(map(len,raw.values()))==26301
    assert pin(raw['launcher.json'])==dict(bytes=4125,sha256='a38876323bcb10ba48ff78ac07a61414d417f4655074975c1882683aedcf4308')
    outer=members(values['launcher.json']);inner=set()
    for name in names[1:]:
        group=members(values[name]);assert len(group)==2 and group.isdisjoint(inner);inner|=group
    residual=outer-inner
    assert len(outer)==66 and len(inner)==64 and inner<=outer
    assert residual=={(23748,134371984628013733),(24064,134371984628243527)}
    # Conditional arithmetic only: keep the observed two-member residual and
    # assume each of 319 point Jobs and one fresh Job still has two members.
    count=2+(319+1)*2;reserve=16384
    one=dict(creation_filetime=134371984628013733,pid=1)
    five=dict(creation_filetime=134371984628013733,pid=23748)
    assert count==642 and len(canonical(one))==48 and len(canonical(five))==52
    lower=count*len(canonical(one))+count-1+2;assert lower==31459
    example=deepcopy(values['launcher.json']);w=example['quiescence_witness']
    example_members=[five]+[dict(creation_filetime=134371984628013733+i,pid=29999+i) for i in range(1,count)]
    w.update(member_identities=example_members,observed_unique_member_handles=count,total_processes=count)
    assert len(canonical(example_members))==34027 and len(canonical(example))==34658
    guard_name='src/staged_rts24_process_guard_v2.py';guard=read(ROOT/guard_name)
    assert b'terminal_reserved_bytes=16384' in guard and b'size+16384' in guard
    assert all(read(P1/n)==b for n,b in raw.items()) and read(ROOT/guard_name)==guard
    return dict(authority='DRAFT_NONAUTHORITATIVE',input_pins={str((P1/n).relative_to(ROOT)).replace('\\','/'):pin(b) for n,b in raw.items()},
        guard_pin={guard_name:pin(guard)},P1_saved_inputs=33,P1_saved_input_bytes=26301,read_passes=2,
        outer_members=66,known_inner_jobs=32,known_inner_members=64,
        outer_residual_members=[dict(pid=p,creation_filetime=t) for p,t in sorted(residual)],
        residual_program_attribution_proven=False,actual_parent_edges_proven=False,
        projection_assumptions=dict(residual_members=2,point_jobs=319,fresh_jobs=1,members_per_inner_job=2,creation_filetime_digits=18),
        projected_members=count,terminal_reserved_bytes=reserve,
        conditional_member_array_lower_bound_bytes=lower,conditional_member_array_shortfall_bytes=lower-reserve,
        conditional_five_digit_PID_member_array_bytes=len(canonical(example_members)),
        conditional_P1_shape_record_example_bytes=len(canonical(example)),conditional_example_reserve_shortfall_bytes=len(canonical(example))-reserve,
        boundary_reserve_guarantee_established=False,actual_P2_record_measured=False,actual_P2_overflow_inferred=False,
        resource_admission=False,formal_result=False,new_native_calls=0)

if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
