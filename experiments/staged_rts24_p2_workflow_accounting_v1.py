"""Conditional P2 call accounting from saved metadata; no scientific imports."""
import ast
from collections import Counter
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
READER='experiments/staged_c_workflow_budget_v1.py'
READER_SHA='5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82'
PACKAGE='experiments/__init__.py'
PACKAGE_SHA='f67a437b3910b0400486a45167d0001163081e3b8b3f1d6166df4e3a3adf3581'
BOOTSTRAP=dict(reads=0,bytes=0)
BOOTSTRAP_PINS={}


def bootstrap_read(path):
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or getattr(info,'st_file_attributes',0)&0x400
        or info.st_size>32*1024):raise ValueError('bootstrap identity file differs')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(info.st_size+1);closed=os.fstat(stream.fileno())
    if (not os.path.samestat(info,opened) or not os.path.samestat(opened,path.stat())
        or len(raw)!=info.st_size or closed.st_size!=info.st_size):raise ValueError('bootstrap identity file changed')
    BOOTSTRAP['reads']+=1;BOOTSTRAP['bytes']+=len(raw)
    if BOOTSTRAP['reads']>4 or BOOTSTRAP['bytes']>64*1024:raise ValueError('bootstrap identity read cap')
    name=path.relative_to(ROOT).as_posix();pin=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
    if name in BOOTSTRAP_PINS and BOOTSTRAP_PINS[name]!=pin:raise ValueError('bootstrap input drift')
    BOOTSTRAP_PINS[name]=pin
    return raw


if __name__=='__main__':
    if Path.cwd().resolve()!=ROOT or any(n.split('.')[0] in ('src','experiments') for n in sys.modules):
        raise ValueError('fresh repository CLI scope required before Reader import')
    if sha256(bootstrap_read(ROOT/PACKAGE)).hexdigest()!=PACKAGE_SHA:
        raise ValueError('repository package bytes differ')
    if sha256(bootstrap_read(ROOT/READER)).hexdigest()!=READER_SHA:raise ValueError('frozen Reader bytes differ before import')
sys.path.insert(0,str(ROOT))
from experiments import staged_c_workflow_budget_v1 as retained
Reader,require=retained.Reader,retained.require

BASE=ROOT/'results/tables/staged_rts24_p2_workflow_accounting_v1_non_authoritative'
OUT=BASE/'audit_01'
PACKET='results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01/'
PINS={
    'packet.json':'9f53266cd297e3181fdf4c9f78ece30f57a217f9b8a9577e3d80f0a341eb56e6',
    'context.json':'96ab0a6b8bfca7567d91c6e5e671cece42ad7209d765342891ee5e117f38bbec',
    'observation.json':'c13d4cba911b78442c08d9997e5a204e371f2f31b5401abf4a2ec9911b99adfb'}
DIAGNOSTIC='results/tables/staged_rts24_p2_input_cost_v1_non_authoritative/'
ANCHOR_SHA='33e1614656ca456c5bb8f72f7fe0d2f6f631587b5ce6d22e18bb68c6d43072e1'
P1='results/tables/staged_rts24_native_v1_non_authoritative/p1_01/'
P1_ANCHOR='results/tables/staged_rts24_native_v1_non_authoritative/p1_execution_review_01/postcheck_03.stdout.json'
P1_ANCHOR_SHA='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
SOURCES=('experiments/staged_rts24_p2_workflow_accounting_v1.py','tests/test_staged_rts24_p2_workflow_accounting_v1.py',
    'docs/plan/staged_deliverability_c_p2_workflow_accounting_contract_v1.md')
ROLES=('reference_base_P0','reference_raw_need','recovery_min_meter','recovery_max_meter')


def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def reader_identity():
    module=sys.modules.get('experiments.staged_c_workflow_budget_v1');path=ROOT/READER
    if (module is not retained or retained.__name__!='experiments.staged_c_workflow_budget_v1'
        or Path(retained.__file__).resolve()!=path or retained.__spec__.name!=retained.__name__
        or Path(retained.__spec__.origin).resolve()!=path or Reader is not retained.Reader or require is not retained.require):
        raise ValueError('frozen Reader module identity differs')
    package=sys.modules['experiments']
    if (Path(package.__file__).resolve()!=ROOT/'experiments/__init__.py' or package.__spec__.name!='experiments'
        or list(package.__path__)!=[str(ROOT/'experiments')]):raise ValueError('Reader package identity differs')
    raw=bootstrap_read(path)
    if sha256(raw).hexdigest()!=READER_SHA:raise ValueError('frozen Reader source differs')
    def find(code,name):
        if code.co_qualname==name:return code
        for c in code.co_consts:
            if type(c) is type(code):
                found=find(c,name)
                if found is not None:return found
    compiled=compile(raw,str(path),'exec',dont_inherit=True,optimize=sys.flags.optimize)
    if (type(Reader) is not type or Reader.__module__!=retained.__name__ or Reader.__bases__!=(object,)
        or {n for n,f in vars(Reader).items() if hasattr(f,'__code__')}!={'__init__','read','json','bookend'}):
        raise ValueError('frozen Reader class differs')
    functions=[require,*[f for f in vars(Reader).values() if hasattr(f,'__code__')]]
    for f in functions:
        if (f.__module__!=retained.__name__ or f.__globals__ is not vars(retained)
            or Path(f.__code__.co_filename).resolve()!=path or f.__code__!=find(compiled,f.__qualname__)
            or f.__defaults__!=((None,) if f.__name__ in ('read','json') else None) or f.__kwdefaults__ is not None):
            raise ValueError('frozen Reader function identity differs')


def prefix_accounting(hours):
    require(type(hours) is int and 0<=hours<=10,'bounded accepted-hour count required')
    t=hours
    scans=Counter(empty=1,fixture=2,accepted_0=7)
    for k in range(t):scans['accepted_'+str(k)]+=4  # begin twice, commit, append _check
    scans['accepted_'+str(t)]+=2  # finish and terminal append _check
    for k in range(1,t+2):
        terminal=k==t+1
        scans['accepted_'+str(k-1)]+=1
        scans['terminal_payload' if terminal else 'payload_'+str(k)]+=2
        scans['final' if terminal else 'accepted_'+str(k)]+=3
    scans['final']+=8  # two read views: store, view start, view bookend, final store
    require(sum(scans.values())==10*t+26,'CAS expansion disagreement')
    return dict(accepted_hours=t,writer_checks=4*t+2,writer_runtime=9*t+7,journal_runtime_including_two_reopens=9*t+11,
        root_inventory_calls=6*t+9,CAS_inventory_calls=10*t+26,CAS_inventory_epoch_weights=dict(scans),
        root_inventory_file_hash_reads=3*t*t+12*t+14,check_chain_entry_reads=2*t*t,
        check_genesis_and_head_reads=2*(4*t+2),reopen_sequential_entry_reads=2*(t+1),
        append_published_entry_readbacks=t+1,reopen_genesis_reads=2,
        direct_journal_root_reads_excluding_codec_publication=5*t*t+23*t+23,
        prepare_hour=6*t,propose_hour=6*t,accept_hour=3*t,execution_summary=3,
        audit_execution=9*t+7,audit_execution_context=6*t+4,audit_prefix_row_visits=9*t*(t+1)//2,
        selective_calls_three_journal_passes=3*(3*t*t+7*t)//2,
        scope='clean accepted writer plus terminal and two full terminal reopens; no failure/pending')


def inventory_object_visits(epoch_weights,sizes):
    require(set(sizes)==set(epoch_weights) and all(type(v) is int and v>=0 for v in sizes.values()),'complete nonnegative CAS sizes required')
    require(sizes['empty']==0,'empty epoch must be empty')
    return sum(epoch_weights[n]*sizes[n] for n in epoch_weights)


def accounting(packet):
    rows=packet['schedule'];hours=list(range(-2,8))
    require(packet['first_hour']==-2 and packet['last_hour']==7 and packet['registration_end']==4
        and packet['observation_end']==8 and packet['selected_contingencies']==69 and packet['contract_hours']==[1,2],'fixed P2 scope differs')
    require(len(rows)==319 and [r['ordinal'] for r in rows]==list(range(1,320)) and digest(rows)==packet['schedule_sha'],'P2 slot bytes/order differs')
    role_sets=[[r['role'] for r in rows if r['section']=='actual' and r['hour']==h and r['role'] in ROLES] for h in hours]
    expected=[[ROLES[0],*ROLES[2:]] if h!=1 else list(ROLES) for h in hours]
    require(role_sets==expected and [r['hour'] for r in rows if r['role']=='actual_P']==hours,'actual role shape differs')
    counts=Counter(r['role'] for r in rows)
    require(counts==Counter(reference_base_P0=10,reference_raw_need=1,recovery_min_meter=10,recovery_max_meter=10,
        actual_P=10,normal_contract_C=2,fault_firm_F=138,fault_raw_need=138),'point roles differ')
    require(sum(r['objective']=='economic' for r in rows)==160,'QP/LP split differs')
    prefix=prefix_accounting(10)
    single_weights=[3*(10-i)+2 for i in range(10)]
    # Three journal passes, direct hour_evidence, and one worker packet validation.
    selective_weights=[3*w+2 for w in single_weights]
    selective_roles=Counter({r:0 for r in ROLES})
    for role_set,w in zip(role_sets,selective_weights):selective_roles.update({r:w for r in role_set})
    descriptions=sum(selective_roles.values())
    full_descriptions=2*sum(139+len(role_sets[hours.index(h)]) for h in (1,2))
    native=319;fingerprints=4*native+5
    return dict(basis='conditional successful internal P2 worker; not executed or resource-admitted',
        process_scopes=dict(worker=1,point_children=native,fresh=1,logical_process_roles=321,actual_Job_members=None),
        points=dict(total=native,actual=41,contract=278,QP=160,LP=159,model_builds=4*native,imports=2*native),
        input_checks=dict(light_registration=321,load_packet=960,fingerprints=fingerprints,preserve=3,
            source55_stamps=55*fingerprints,source7_stamps=7*fingerprints,
            preparation_hash_bytes=505285*(960+2*fingerprints+3),packet_JSON_bytes=255146*960,
            context_JSON_bytes=249557*fingerprints,preparation_total_logical_bytes=2345752302),
        journal=prefix,journal_and_P2_fingerprint_runtime_calls=prefix['journal_runtime_including_two_reopens']+fingerprints,
        selected_runtime_file_reads=(prefix['journal_runtime_including_two_reopens']+fingerprints)*39,
        point_CAS_inventory_calls=8*native,all_internal_CAS_inventory_calls=prefix['CAS_inventory_calls']+8*native,
        compiler_descriptions=dict(selective_calls=sum(selective_weights),selective_descriptions=descriptions,
            selective_call_sources=dict(three_journal_passes=555,hour_evidence=10,worker_packet_validation=10),
            full_call_sources=dict(worker_contract_frames=2,worker_packet_validation=2),
            selective_hour_weights=selective_weights,selective_roles=dict(selective_roles),
            full_calls=4,full_descriptions=full_descriptions,total_descriptions=descriptions+full_descriptions,
            scope='reference/full compiler output descriptions; excludes dynamic replace and nested numeric/audit construction'),
        deferred_cache=dict(fingerprint_checks_removed=0,packet_parse_candidate_saved=639,
            packet_candidate_logical_bytes_saved=639*255146,context_parse_candidate_saved=960,
            context_candidate_logical_bytes_saved=960*249557,implemented=False),
        unknown=dict(CAS_epoch_sizes=None,CAS_object_reads=None,CAS_bytes=None,nested_audit_and_codec_recursion=None,
            costly_failure_DAG=None,outer_and_registration_additions=None,wall_estimate_seconds=None,resource_estimate=None),
        overall_performance_review_complete=False,resource_admission=False,formal_result=False,native_authorized=False)


def ast_counts(raw):
    tree=ast.parse(raw)
    values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
        and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('SOURCE_PATHS','EXTERNAL_MODULES')}
    require(len(values['SOURCE_PATHS'])==28 and len(values['EXTERNAL_MODULES'])==10,'journal selected source scope differs')
    return {n:len(v) for n,v in values.items()}


def wire_refs(wire,depth=0):
    require(depth<=64,'wire depth limit')
    if wire is None or type(wire) in (str,int,bool):return set()
    require(type(wire) is list and wire and type(wire[0]) is str,'invalid wire node')
    tag=wire[0]
    if tag=='ref':
        require(len(wire)==2 and type(wire[1]) is str and len(wire[1])==64
            and all(c in '0123456789abcdef' for c in wire[1]),'invalid wire ref')
        return {wire[1]}
    if tag=='float':
        require(len(wire)==2 and type(wire[1]) is str,'invalid wire float')
        value=float.fromhex(wire[1]);require(math.isfinite(value) and value.hex()==wire[1],'invalid wire float')
        return set()
    if tag=='Q':
        require(len(wire)==3 and type(wire[1]) is type(wire[2]) is int and wire[2]>0
            and math.gcd(wire[1],wire[2])==1,'invalid wire rational')
        return set()
    if tag in ('tuple','list'):
        require(len(wire)==2 and type(wire[1]) is list,'invalid wire sequence');children=wire[1]
    else:
        require(tag in ('dict','class') and len(wire)==(2 if tag=='dict' else 3),'unknown wire tag')
        require(tag!='class' or type(wire[1]) is str,'invalid wire class')
        pairs=wire[-1];require(type(pairs) is list and all(type(p) is list and len(p)==2 and type(p[0]) is str for p in pairs)
            and len({p[0] for p in pairs})==len(pairs),'invalid wire pairs')
        require(tag!='dict' or [p[0] for p in pairs]==sorted(p[0] for p in pairs),'unsorted wire mapping')
        children=[p[1] for p in pairs]
    refs=set()
    for child in children:refs.update(wire_refs(child,depth+1))
    return refs


def closures(objects):
    cache={};active=set()
    def visit(key,depth=0):
        require(depth<=64 and key in objects and key not in active,'missing/cyclic/deep wire reference')
        if key in cache:return cache[key]
        envelope=objects[key]
        require(type(envelope) is dict and set(envelope)=={'schema','kind','payload'}
            and envelope['schema']=='staged_rts24_typed_cas_v1','wire envelope differs')
        active.add(key);result={key}
        for child in wire_refs(envelope['payload']):result.update(visit(child,depth+1))
        active.remove(key);cache[key]=frozenset(result);return cache[key]
    for key in objects:visit(key)
    return cache


def retained_epochs(genesis,entries,objects,sizes):
    require(len(entries)==6 and [e['kind'] for e in entries]==['hour']*5+['terminal'],'fixed P1 committed prefix differs')
    graph=closures(objects);fixture=graph[genesis['fixture_ref']];current=fixture|graph[genesis['state_ref']]
    require(objects[genesis['fixture_ref']]['kind']=='Fixture' and objects[genesis['state_ref']]['kind']=='ExecutionState','genesis root kinds differ')
    require(sorted(n+'.json' for n in current)==genesis['after_cas_keys'],'genesis closure differs')
    epochs=dict(empty=frozenset(),fixture=fixture,accepted_0=current)
    for k,entry in enumerate(entries,1):
        require(objects[entry['payload_ref']]['kind']=='dict' and objects[entry['state_ref']]['kind']=='ExecutionState','entry root kinds differ')
        payload=current|graph[entry['payload_ref']];current=payload|graph[entry['state_ref']]
        require(sorted(n+'.json' for n in current)==entry['after_cas_keys'],'entry closure differs')
        epochs['terminal_payload' if k==6 else 'payload_'+str(k)]=payload
        epochs['final' if k==6 else 'accepted_'+str(k)]=current
    require(current==set(objects) and set(objects)==set(sizes),'orphan/missing CAS inventory')
    counts={n:len(s) for n,s in epochs.items()};raw_bytes={n:sum(sizes[k] for k in s) for n,s in epochs.items()}
    weights=prefix_accounting(5)['CAS_inventory_epoch_weights']
    return dict(accepted_hours=5,CAS_files=len(objects),epoch_object_counts=counts,epoch_bytes=raw_bytes,
        inventory_calls=sum(weights.values()),inventory_object_read_instances=inventory_object_visits(weights,counts),
        inventory_logical_bytes=inventory_object_visits(weights,raw_bytes),
        scope='saved original P1 five-hour wire topology projected through writer plus two terminal reopens; not runtime observation or ten-hour forecast')


def saved_P1_projection(reader):
    anchor=reader.json(P1_ANCHOR,P1_ANCHOR_SHA);pins=anchor['p1_files']
    names={n for n in pins if n.startswith('journal/')}
    require(len(names)==137 and len(pins)==683,'P1 journal/anchor shape differs')
    require(all((reader.root/(P1+n)).lstat().st_nlink==1 for n in names),'linked retained journal file')
    values={n:reader.json(P1+n,pins[n]) for n in sorted(names)}
    genesis=values['journal/genesis.json'];entries=[values['journal/entry_'+str(i).zfill(6)+'.json'] for i in range(1,7)]
    previous=pins['journal/genesis.json']['sha256'];state=genesis['after_state_sha']
    for i,e in enumerate(entries,1):
        require(e['ordinal']==i and e['previous_sha']==previous and e['before_state_sha']==state,'saved P1 entry chain differs')
        previous=pins['journal/entry_'+str(i).zfill(6)+'.json']['sha256'];state=e['after_state_sha']
    binding=reader.json(P1+'trusted_binding.json',pins['trusted_binding.json'])
    require(binding['known_head_sha']==previous and binding['known_state_sha']==state and binding['known_entries']==6
        and binding['closed'] is True,'P1 trusted terminal binding differs')
    objects={n.removeprefix('journal/objects/').removesuffix('.json'):v for n,v in values.items() if n.startswith('journal/objects/')}
    sizes={key:pins['journal/objects/'+key+'.json']['bytes'] for key in objects}
    require(all(pins['journal/objects/'+key+'.json']['sha256']==key for key in objects),'CAS filename/hash differs')
    result=retained_epochs(genesis,entries,objects,sizes)
    require(sorted(n+'.json' for n in objects)==binding['known_cas_keys'],'P1 trusted CAS set differs')
    observation_names=[n for n in pins if n in ('worker_observations.json','fresh_observations.json') or n.endswith('/point_observations.json')]
    require(len(observation_names)==33,'P1 saved process observations differ')
    counts=Counter()
    for n in observation_names:counts.update(reader.json(P1+n,pins[n])['counts'])
    observed={n:counts[n] for n in ('selective_compile_attempts','selective_descriptions','full_compile_attempts','full_descriptions',
        'fingerprints_attempts','journal_runtime_identity_attempts','audit_execution_attempts','prepare_hour_attempts',
        'propose_hour_attempts','accept_hour_attempts','execution_summary_attempts','journal_begin_step_attempts',
        'journal_commit_step_attempts','journal_finish_attempts','journal_create_session_attempts','journal_reopen_attempts',
        'numeric_compile_attempts','pyomo_build_attempts','numeric_import_attempts')}
    require(observed==dict(selective_compile_attempts=175,selective_descriptions=551,full_compile_attempts=4,full_descriptions=570,
        fingerprints_attempts=129,journal_runtime_identity_attempts=185,audit_execution_attempts=52,prepare_hour_attempts=30,
        propose_hour_attempts=30,accept_hour_attempts=15,execution_summary_attempts=3,journal_begin_step_attempts=5,
        journal_commit_step_attempts=5,journal_finish_attempts=1,journal_create_session_attempts=1,journal_reopen_attempts=2,
        numeric_compile_attempts=124,pyomo_build_attempts=124,numeric_import_attempts=62),'P1 structural formula disagrees with retained observations')
    model=prefix_accounting(5)
    require(model['journal_runtime_including_two_reopens']+observed['fingerprints_attempts']==185,'P1 runtime split differs')
    require(all(model[n]==observed[n+'_attempts'] for n in ('prepare_hour','propose_hour','accept_hour','execution_summary','audit_execution')),'P1 scientific operation split differs')
    result['saved_process_observer_crosscheck']=observed
    return result


def audit(root=ROOT):
    reader_identity()
    reader=Reader(root)
    reader.read(READER,READER_SHA)
    reader.read(PACKAGE,PACKAGE_SHA)
    for name in SOURCES:reader.read(name)
    files={n:reader.json(PACKET+n,pin) for n,pin in PINS.items()}
    anchor=reader.json(DIAGNOSTIC+'postcheck_01/saved_01.stdout.json',ANCHOR_SHA)
    start=reader.json(DIAGNOSTIC+'measure_01/start.json');source_pins=start['source_pins']
    require(len(source_pins)==66 and anchor['source_files_unchanged']==66 and anchor['new_native_calls']==0,'diagnostic scope differs')
    for name,pin in source_pins.items():reader.read(name,pin)
    require(all(source_pins[n]==pin for n,pin in files['context.json']['source_pins'].items()),'preparation source identity differs')
    selected=ast_counts(reader.read('src/staged_rts24_journal_v2.py',source_pins['src/staged_rts24_journal_v2.py']))
    observations={n:reader.json(DIAGNOSTIC+n) for n in ('measure_01/report.json','measure_01/launcher.json','execution_observations_01/command_01.exit.json')}
    report=observations['measure_01/report.json'];launcher=observations['measure_01/launcher.json'];command=observations['execution_observations_01/command_01.exit.json']
    require(launcher['exit_code']==command['exit_code']==0 and launcher['job_quiet_confirmed'] is True
        and report['solver_calls']==report['new_models']==report['new_replays']==0,'saved diagnostic terminal differs')
    attempt=reader.json(DIAGNOSTIC+'postcheck_01/measurement_inventory.json')
    require(len(attempt)==16,'diagnostic inventory differs')
    for name,pin in attempt.items():reader.read(DIAGNOSTIC+'measure_01/'+name,pin)
    result=accounting(files['packet.json']);projection=saved_P1_projection(reader);reader.bookend()
    require(reader.operations+BOOTSTRAP['reads']<=1800 and reader.bytes+BOOTSTRAP['bytes']<=12*1024**2,'total metadata byte/read cap')
    native=reader.root/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    require(not (native/'p2_01').exists() and not (native/'registration_v1.json').exists(),'P2 execution appeared')
    return dict(authority='DRAFT_NONAUTHORITATIVE',accounting=result,saved_P1_CAS_projection=projection,input_pins=reader.pins,
        input_reads=reader.operations+BOOTSTRAP['reads'],input_bytes=reader.bytes+BOOTSTRAP['bytes'],
        bounded_reader_input_reads=reader.operations,bounded_reader_input_bytes=reader.bytes,
        bootstrap_identity_reads=BOOTSTRAP['reads'],bootstrap_identity_bytes=BOOTSTRAP['bytes'],
        bootstrap_identity_pins=dict(BOOTSTRAP_PINS),
        bounded_reader_wall_seconds=time.perf_counter()-reader.started,
        selected_journal_source_counts=selected,saved_diagnostic_observations=observations,
        new_scientific_calls=0,new_native_calls=0,new_scientific_replays=0,source_and_artifact_bookends=True,
        environment_revalidated=False,resource_admission=False,formal_result=False,official_verdict=None,seal=None,receipt=None)


def publish_audit(path,raw):
    require(type(raw) is bytes and 0<len(raw)<=512*1024,'audit output size')
    with path.open('xb') as stream:
        opened=os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1,'nonordinary new audit')
        require(stream.write(raw)==len(raw),'short audit write')
        stream.flush();closed=os.fstat(stream.fileno())
        require(os.path.samestat(opened,closed) and closed.st_size==len(raw),'audit write size differs')
    after=path.lstat()
    require(stat.S_ISREG(after.st_mode) and after.st_nlink==1 and not getattr(after,'st_file_attributes',0)&0x400
        and os.path.samestat(closed,after),'audit path changed after close')
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());saved=stream.read(len(raw)+1);end=os.fstat(stream.fileno())
    require(os.path.samestat(after,before) and os.path.samestat(before,end) and os.path.samestat(end,path.lstat())
        and end.st_size==len(raw) and saved==raw,'audit readback differs')
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    require(Path.cwd().resolve()==ROOT and sys.flags.no_user_site and sys.dont_write_bytecode,'root -B -s metadata CLI required')
    require(not any(n=='src' or n.startswith('src.') for n in sys.modules),'scientific modules already loaded')
    require(not OUT.exists(),'metadata output exists')
    value=audit();raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    require(len(raw)<=512*1024,'audit output cap')
    for path in reversed((BASE.parent,*BASE.parent.parents)):
        info=path.lstat();require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
            and not getattr(info,'st_file_attributes',0)&0x400,'linked output parent')
    require(BASE.parent.resolve(strict=True).is_relative_to(ROOT),'output parent differs')
    BASE.mkdir(exist_ok=True);info=BASE.lstat()
    require(stat.S_ISDIR(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400 and BASE.resolve()==BASE,'linked output base')
    OUT.mkdir()
    output_pin=publish_audit(OUT/'audit.json',raw)
    print(json.dumps(dict(input_files=len(value['input_pins']),input_reads=value['input_reads'],input_bytes=value['input_bytes'],
        output_pin=output_pin,output_readback_reads=1,output_readback_bytes=len(raw),
        new_scientific_calls=0,new_native_calls=0,resource_admission=False)))


if __name__=='__main__':main()
