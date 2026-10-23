"""Saved development evidence and preserved bytes only; no research imports."""
from hashlib import sha256
import ast
import json
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'
CHECKS=BASE/'development_checks_01'
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
PREP=ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative'


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def stamp(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary repository file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    units=read(CHECKS/'units_03.exit.json');related=read(CHECKS/'related_01.exit.json')
    require(units['exit_code']==related['exit_code']==0 and units['timed_out'] is False,'ordinary checks not terminal')
    for label,record,count in (('units_03',units,50),('related_01',related,110)):
        require(record['source_pins_unchanged'] is True and all(stamp(ROOT/n)==v for n,v in record['source_pins'].items()),'check source drift')
        require((CHECKS/(label+'.stderr.log')).read_bytes()==b'' and re.search(rb'\b'+str(count).encode()+rb' passed in\b',
            (CHECKS/(label+'.stdout.log')).read_bytes()) is not None,'ordinary check summary differs')
    require(len(units['source_pins'])==7,'new input set differs')
    for name in units['source_pins']:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
    # Mechanical monitor successor: only the declared admission caps/message differ.
    old=(ROOT/'src/staged_rts24_process_guard_v1.py').read_text(encoding='utf-8')
    new=(ROOT/'src/staged_rts24_process_guard_v2.py').read_text(encoding='utf-8')
    expected=old[old.index('def supervise('):].replace('wall_seconds=300, no_progress_seconds=30',
        'wall_seconds=3600, no_progress_seconds=65').replace('files=5000','files=8192').replace(
        'monitor limit outside P1 cap','monitor limit outside P2 proposal cap')
    require(new[new.index('def supervise('):]==expected,'monitor behavior changed outside proposal caps')
    require('from src.staged_rts24_process_guard_v1 import OwnedChild,controlled_environment,scan_output' in new,'original ownership adapter differs')
    context=read(PREP/'packet_01/context.json');sources=context['source_pins']
    require(len(sources)==55 and all(stamp(ROOT/n)==v for n,v in sources.items()),'frozen preparation/scientific source drift')
    preserved=read(POST/'prior_preservation_inventory.json')
    require(len(preserved)==259 and all(stamp(ROOT/n)==v for n,v in preserved.items()),'prior published bytes changed')
    original=read(PRIOR)
    require({p.relative_to(P1).as_posix():stamp(p) for p in P1.rglob('*') if p.is_file()}==original['p1_files'],'P1 bytes changed')
    for name in ('P1_and_prior','P2_preparation'):
        record=read(POST/(name+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is True
            and (POST/(name+'.stderr.log')).read_bytes()==b'','prior stdlib postcheck differs')
    require(stamp(POST/'P1_and_prior.stdout.json')==stamp(PRIOR),'P1 postcheck bytes differ')
    require(not (ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/p2_01').exists()
        and not (ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/registration_v1.json').exists(),
        'public P2 output or execution registration exists')
    require(all(stamp(ROOT/n)==v for n,v in units['source_pins'].items()),'final source bookend differs')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),targeted_passed=50,related_passed=110,
        new_source_inputs_unchanged=7,preparation_source_inputs_unchanged=55,original_owner_and_science_preserved=True,
        P1_files_unchanged=683,P1_bytes_unchanged=sum(v['bytes'] for v in original['p1_files'].values()),
        B1_B3_saved_files=original['B1_B3_saved_files'],prior_checkpoint_paths=original['unique_prior_checkpoint_paths'],
        previous_published_paths_unchanged=len(preserved),P2_execution_directory_absent=True,P2_execution_registration_absent=True,
        new_public_native_calls=0,new_scientific_replays_by_postcheck=0,
        native_authorized=False,resource_admission=False,formal_result=False,C_overall_performance_review_complete=False,
        full_139_numerically_executed=False,scope='ordinary temp analytic/FakeApi/short-child checks and saved byte bindings only')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
