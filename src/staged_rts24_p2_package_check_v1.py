"""Read-only draft protocol inspection. Saved consistency is not scientific replay."""
from dataclasses import fields
from fractions import Fraction
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re

from src import staged_rts24_p2_outer_observation_v1 as parent

codec=parent.codec
require=parent.require
CAPS=dict(parent.CAPS)
POINT_LIMITS={**CAPS,'wall_seconds':10,'no_progress_seconds':10}
FRESH_LIMITS={**CAPS,'wall_seconds':60,'no_progress_seconds':60}
EXCLUDED={'completion.json','launcher.json','launcher.stdout.log','launcher.stderr.log','worker.stdout.log','worker.stderr.log'}
KERNEL_SOURCES=('src/staged_rts24_p2_controller_v1.py','src/staged_rts24_process_guard_v2.py',
    'experiments/staged_rts24_p2_native_probe_v1.py','tests/test_staged_rts24_p2_controller_v1.py',
    'tests/test_staged_rts24_p2_native_probe_v1.py','tests/test_staged_rts24_process_guard_v2.py',
    'docs/plan/staged_deliverability_c_p2_runner_development_contract_v1.md')
OUTER_SOURCES=('src/staged_rts24_p2_package_check_v1.py','tests/test_staged_rts24_p2_package_check_v1.py',
    'docs/plan/staged_deliverability_c_p2_package_check_contract_v1.md',
    'src/staged_rts24_p2_outer_observation_v1.py','tests/test_staged_rts24_p2_outer_observation_v1.py',
    'docs/plan/staged_deliverability_c_p2_failure_and_outer_contract_v1.md')
PACKET_PINS={'packet.json':dict(bytes=255146,sha256='9f53266cd297e3181fdf4c9f78ece30f57a217f9b8a9577e3d80f0a341eb56e6'),
    'context.json':dict(bytes=249557,sha256='96ab0a6b8bfca7567d91c6e5e671cece42ad7209d765342891ee5e117f38bbec'),
    'observation.json':dict(bytes=582,sha256='c13d4cba911b78442c08d9997e5a204e371f2f31b5401abf4a2ec9911b99adfb')}
ACTUAL=(4,8,12,17,21,25,29,33,37,41)
CONTEXT_KEYS=set('schema authority public_execution_enabled native_authorized resource_admission repo_root worker_root parent_root registration packet_root source_pins executable startup'.split())
STARTUP_KEYS=set('executable argv cwd worker_root limits registration_sha'.split())


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def canonical_image(value):
    """Bound expanded plain JSON before C encoding; no cross-call state cache."""
    limit=8*1024**2;memo={};active=set()
    def bound(size):require(size<=limit,'semantic image byte limit');return size
    def size(item,depth=0):
        require(depth<=512,'semantic image depth limit')
        kind=type(item)
        if item is None:return 4
        if kind is bool:return 4 if item else 5
        if kind is str:
            bound(len(item)+2);return bound(len(json.encoder.encode_basestring_ascii(item)))
        if kind is int:return bound(len(str(item)))
        if kind is float:
            require(math.isfinite(item),'nonfinite semantic value');return len(repr(item))
        require(kind in (dict,list,tuple),'unsupported semantic value')
        identity=id(item);require(identity not in active,'cyclic semantic value')
        if identity in memo:
            held,length=memo[identity];require(held is item,'semantic identity cache differs');return length
        active.add(identity);length=bound(2+max(0,len(item)-1))
        if kind is dict:
            for key,child in item.items():
                require(type(key) is str,'semantic mapping key must be an exact string')
                length=bound(length+size(key,depth+1)+1+size(child,depth+1))
        else:
            for child in item:length=bound(length+size(child,depth+1))
        active.remove(identity);memo[identity]=(item,length);return length
    expected=size(value)
    raw=json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    require(len(raw)==expected<=limit,'semantic image size differs');return raw


def digest(value):return sha256(canonical_image(value)).hexdigest()


def same(a,b):return digest(a)==digest(b)


def keys(value,names):require(type(value) is dict and set(value)==set(names.split()),'closed fields differ: '+names)


def sha(value):require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value),'invalid SHA');return value


def relative(name):
    require(type(name) is str and name and '\\' not in name and ':' not in name,'invalid relative path')
    p=PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix()==name and all(v not in ('.','..') and not v.endswith(('.', ' ')) for v in p.parts),'noncanonical relative path')
    return name


def absolute(value):
    require(type(value) is str,'absolute path scalar');p=Path(value)
    require(p.is_absolute() and '..' not in p.parts and str(p.absolute())==value,'noncanonical absolute path');return p


def checked_pin(value):
    keys(value,'bytes sha256');require(parent.integer(value['bytes']) and value['bytes']<=8*1024**2,'invalid pin size');sha(value['sha256'])


def frozen_packet_json(raw,name):
    require(pin(raw)==PACKET_PINS[name],'frozen packet bytes differ')
    return json.loads(raw,object_pairs_hook=codec._pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite frozen JSON')))


def read_inputs(context):
    repo=absolute(context['repo_root']);packet=absolute(context['packet_root'])
    require({p.name for p in packet.iterdir()}==set(PACKET_PINS),'packet directory differs')
    inputs={}
    def take(path,expected):
        checked_pin(expected);raw=codec.read_bytes(path);require(pin(raw)==expected,'held input changed: '+str(path));inputs[str(path)]=raw;return raw
    packet_bytes={n:take(packet/n,v) for n,v in PACKET_PINS.items()}
    reg=codec.parse(take(absolute(context['registration']['path']),context['registration']['pin']))
    expected=frozen_packet_json(packet_bytes['context.json'],'context.json')['source_pins']
    require(len(expected)==55 and same(reg['pins']['preparation_sources'],expected)
        and set(reg['pins']['P2_sources'])==set(KERNEL_SOURCES),'registered source groups differ')
    wanted={**expected,**reg['pins']['P2_sources']}
    require(set(context['source_pins'])==set(wanted)|set(OUTER_SOURCES),'outer source set differs')
    require(all(context['source_pins'][n]==v for n,v in wanted.items()),'registered source pins differ')
    for n,v in context['source_pins'].items():take(repo/relative(n),v)
    for name,path in ((OUTER_SOURCES[0],Path(__file__)),(OUTER_SOURCES[3],Path(parent.__file__)),('src/staged_rts24_evidence_store_v1.py',Path(codec.__file__))):
        require(pin(codec.read_bytes(path))==context['source_pins'][name],'loaded checker/codec source differs')
    take(absolute(context['executable']['path']),context['executable']['pin'])
    packet_value=frozen_packet_json(packet_bytes['packet.json'],'packet.json')
    fixed=dict(schema='staged_rts24_P2_execution_registration_v1',authority='DRAFT_NONAUTHORITATIVE',native_authorized=False,
        output=context['worker_root'],limits=CAPS,point_limits=POINT_LIMITS,fresh_limits=FRESH_LIMITS,max_point_attempts=319,
        packet_pin=PACKET_PINS['packet.json'],authorization='separate_explicit_user_instruction_required_not_granted_by_this_file')
    require(set(reg)==set(fixed)|{'schedule_sha','pins','preserved'} and same({n:reg[n] for n in fixed},fixed),'kernel registration differs')
    require(reg['schedule_sha']==packet_value['schedule_sha']==digest(packet_value['schedule']),'registered schedule differs')
    legacy=reg['pins']['legacy_scientific_and_P1_runtime']
    require(legacy['executable']==context['executable']['path'] and legacy['runtime']['executable_sha256']==context['executable']['pin']['sha256'],'registered executable differs')
    require(reg['pins']['preparation_files']==PACKET_PINS,'registered packet pins differ')
    return inputs,reg,packet_value


def validate_context(value):
    require(type(value) is dict and set(value)==CONTEXT_KEYS,'closed package context required')
    fixed=dict(schema='staged_rts24_P2_package_check_development_v1',authority='DRAFT_NONAUTHORITATIVE',
        public_execution_enabled=False,native_authorized=False,resource_admission=False)
    require(same({n:value[n] for n in fixed},fixed),'package context authority differs')
    repo,worker,par=(absolute(value[n]) for n in ('repo_root','worker_root','parent_root'))
    require(not worker.is_relative_to(par) and not par.is_relative_to(worker),'parent and worker overlap')
    keys(value['registration'],'path pin');absolute(value['registration']['path']);checked_pin(value['registration']['pin'])
    require(not absolute(value['registration']['path']).is_relative_to(worker),'registration is inside worker output')
    absolute(value['packet_root']);keys(value['executable'],'path pin');absolute(value['executable']['path']);checked_pin(value['executable']['pin'])
    require(type(value['source_pins']) is dict and len(value['source_pins'])<=100,'source pin group differs')
    for n,v in value['source_pins'].items():relative(n);checked_pin(v)
    startup=value['startup'];require(type(startup) is dict and set(startup)==STARTUP_KEYS,'closed startup record required')
    expected=dict(executable=value['executable']['path'],argv=[value['executable']['path'],'-B','-s',str(repo/'experiments/staged_rts24_p2_native_probe_v1.py'),
        '--worker','--root',str(worker),'--registration-sha',value['registration']['pin']['sha256']],cwd=str(repo),worker_root=str(worker),
        limits=CAPS,registration_sha=value['registration']['pin']['sha256'])
    require(same(startup,expected),'expected startup differs')
    return codec.canonical(value)


def context_bytes(repo_root,worker_root,parent_root,registration,packet_root,executable):
    """Capture read-only development inputs; never register or launch anything."""
    repo,worker,par,reg_path,packet,exe=map(lambda p:Path(p).absolute(),(repo_root,worker_root,parent_root,registration,packet_root,executable))
    reg_raw=codec.read_bytes(reg_path);reg=codec.parse(reg_raw)
    expected=frozen_packet_json(codec.read_bytes(packet/'context.json'),'context.json')['source_pins']
    sources={**expected,**reg['pins']['P2_sources']}
    for n in OUTER_SOURCES:sources[n]=pin(codec.read_bytes(repo/n))
    value=dict(schema='staged_rts24_P2_package_check_development_v1',authority='DRAFT_NONAUTHORITATIVE',
        public_execution_enabled=False,native_authorized=False,resource_admission=False,repo_root=str(repo),worker_root=str(worker),parent_root=str(par),
        registration=dict(path=str(reg_path),pin=pin(reg_raw)),packet_root=str(packet),source_pins=sources,executable=dict(path=str(exe),pin=pin(codec.read_bytes(exe))))
    value['startup']=dict(executable=str(exe),argv=[str(exe),'-B','-s',str(repo/'experiments/staged_rts24_p2_native_probe_v1.py'),
        '--worker','--root',str(worker),'--registration-sha',pin(reg_raw)['sha256']],cwd=str(repo),worker_root=str(worker),limits=CAPS,registration_sha=pin(reg_raw)['sha256'])
    raw=validate_context(value);read_inputs(value);return raw


class InventoryLimit(ValueError):pass


def bounded_file_bytes(path,expected=None):
    """Retain codec identity bookends; request only the observed size plus one."""
    path=Path(path);directories=codec.directory_identity(path.parent);before=codec.ordinary(path)
    def identity(info):return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns
    require(expected is None or identity(before)==expected,'inventory file changed before read')
    require(before.st_size<=8*1024**2,'object byte limit')
    with path.open('rb') as stream:
        require(identity(os.fstat(stream.fileno()))==identity(before),'file changed before read')
        data=stream.read(before.st_size+1)
        require(identity(os.fstat(stream.fileno()))==identity(before),'file changed during read')
    require(identity(codec.ordinary(path))==identity(before) and len(data)==before.st_size,'file changed after read')
    require(codec.directory_identity(path.parent)==directories,'directory changed during read')
    return data


def inventory(root):
    """Metadata pass bounds the entire tree before any worker file content read."""
    root=codec.directory_chain(root);directories={};files={};total=0;entries=0;aliases=set()
    def walk(path,depth):
        nonlocal total,entries
        if depth>12:raise InventoryLimit('directory depth limit')
        info=codec.ordinary(path,directory=True);name=path.relative_to(root).as_posix();directories[name]=(info.st_dev,info.st_ino)
        with os.scandir(path) as scan:
            for entry in scan:
                entries+=1
                if entries>16384:raise InventoryLimit('directory entry limit')
                p=Path(entry.path);rel=relative(p.relative_to(root).as_posix());folded=rel.casefold()
                require(folded not in aliases,'case alias');aliases.add(folded)
                if entry.is_dir(follow_symlinks=False):walk(p,depth+1)
                else:
                    info=codec.ordinary(p);total+=info.st_size;files[rel]=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
                    if info.st_size>8*1024**2 or total>CAPS['output_bytes'] or len(files)>CAPS['files']:raise InventoryLimit('worker inventory byte/file limit')
    walk(root,0)
    raw={n:bounded_file_bytes(root/n,files[n]) for n in sorted(files)}
    for n,identity in files.items():
        i=codec.ordinary(root/n);require(identity==(i.st_dev,i.st_ino,i.st_size,i.st_mtime_ns),'inventory file replaced')
    for n,identity in directories.items():
        i=codec.ordinary(root/n,directory=True);require(identity==(i.st_dev,i.st_ino),'inventory directory replaced')
    return dict(raw=raw,pins={n:pin(v) for n,v in raw.items()},files=files,directories=directories)


class WireView:
    """Metadata projection of canonical CAS wire; no typed construction or audit."""
    def __init__(self,raw,prefix):
        self.objects={};self.cache={};self.active=set();self.nodes=0
        for n,b in raw.items():
            if n.startswith(prefix):
                name=n[len(prefix):];require(re.fullmatch('[0-9a-f]{64}\\.json',name) and sha256(b).hexdigest()==name[:-5],'CAS filename differs')
                obj=codec.parse(b);keys(obj,'schema kind payload');require(obj['schema']==codec.SCHEMA,'CAS schema differs');self.objects[name[:-5]]=obj
        require(len(self.objects)<=10000,'CAS object limit')
        for identity in self.objects:self.get(identity)

    def get(self,identity,kind=None):
        sha(identity);require(identity in self.objects,'dangling CAS reference');obj=self.objects[identity]
        require(kind is None or obj['kind']==kind,'CAS kind differs')
        if identity not in self.cache:
            require(identity not in self.active and len(self.active)<256,'cyclic or deep CAS reference');self.active.add(identity)
            self.cache[identity]=self.decode(obj['payload'],0);self.active.remove(identity)
            payload=obj['payload'];expected=payload[1] if payload[0]=='class' else payload[0]
            require(obj['kind']==expected,'CAS root kind differs')
        return self.cache[identity]

    def decode(self,value,depth):
        self.nodes+=1;require(self.nodes<=1000000 and depth<=256,'wire complexity limit')
        if value is None or type(value) in (str,int,bool):return value
        require(type(value) is list and value and type(value[0]) is str,'wire value differs');tag=value[0]
        if tag=='ref':require(len(value)==2,'ref shape');return self.get(value[1])
        if tag=='float':
            require(len(value)==2 and type(value[1]) is str,'float shape');v=float.fromhex(value[1]);require(math.isfinite(v) and v.hex()==value[1],'float canonical form');return v
        if tag=='Q':
            require(len(value)==3 and type(value[1]) is type(value[2]) is int and value[2]>0,'rational shape');v=Fraction(value[1],value[2]);require((v.numerator,v.denominator)==tuple(value[1:]),'rational canonical form');return str(v)
        if tag in ('list','tuple'):
            require(len(value)==2 and type(value[1]) is list,'sequence shape');return [self.decode(v,depth+1) for v in value[1]]
        if tag=='class':
            require(len(value)==3 and value[1] in codec.CLASSES,'class shape');pairs=value[2];names=[f.name for f in fields(codec.CLASSES[value[1]])]
        else:
            require(tag=='dict' and len(value)==2,'mapping shape');pairs=value[1];names=None
        require(type(pairs) is list and all(type(p) is list and len(p)==2 and type(p[0]) is str for p in pairs),'wire fields shape')
        found=[p[0] for p in pairs];require(found==(names if names is not None else sorted(set(found))),'wire field order/uniqueness')
        return {n:self.decode(v,depth+1) for n,v in pairs}

    def closure(self,roots):
        found=set()
        def visit(identity):
            require(identity in self.objects,'dangling closure root')
            if identity in found:return
            found.add(identity)
            def walk(value):
                if type(value) is list:
                    if len(value)==2 and value[0]=='ref':visit(value[1])
                    else:
                        for child in value:walk(child)
            walk(self.objects[identity]['payload'])
        for root in roots:visit(root)
        return {k+'.json' for k in found}


def query_identity(value):
    return digest(dict(request=digest(value['request']),base_query=None if value['base_query'] is None else digest(value['base_query']['request']),
        base_point=value['base_point'],base_economic=value['base_economic']))


def process_ok(record,limits,outer_members,numeric=False):
    checked=parent.assess_process(record,limits)
    valid=checked['inspection_permitted'] if not numeric else (checked['ownership_status']=='quiet_verified'
        and checked['proposal_caps_satisfied'] and record['exit_code']==2 and record['stop_reason']=='child_exit_nonzero'
        and record['monitor_error'] is record['cleanup_error'] is None)
    require(valid,'internal process protocol differs')
    members={(m['pid'],m['creation_filetime']) for m in record['quiescence_witness']['member_identities']}
    require(members<=outer_members,'internal process is outside outer Job history')
    return members


def completion(raw,pins):
    require(EXCLUDED<=set(raw),'completion root exclusions missing')
    value=codec.parse(raw['completion.json']);keys(value,'files manifest_files logical_bytes')
    expected={n:v for n,v in pins.items() if n not in EXCLUDED}
    require(type(value['manifest_files']) is int and type(value['logical_bytes']) is int
        and same(value['files'],expected) and value['manifest_files']==len(expected)
        and value['logical_bytes']==sum(v['bytes'] for v in expected.values()),'completion manifest differs')
    return pin(raw['completion.json'])


def journal_references(raw,schedule,report,reg,packet,terminal_rejection=False):
    view=WireView(raw,'journal/objects/');genesis=codec.parse(raw['journal/genesis.json'])
    keys(genesis,'after_cas_keys schema kind codec fixture_ref fixture_sha state_ref after_state_sha plan clean method runtime_identity authority resume_permitted')
    require(genesis['schema']=='staged_rts24_development_journal_v2' and genesis['kind']=='genesis'
        and genesis['codec']==codec.SCHEMA and genesis['resume_permitted'] is False
        and (genesis['plan'],genesis['clean'],genesis['method'])==('on_time','early','full_temporal')
        and same(genesis['runtime_identity'],reg['pins']['legacy_scientific_and_P1_runtime']['runtime']),'journal genesis differs')
    fixture=view.get(genesis['fixture_ref'],'Fixture')
    require(digest(fixture)==genesis['fixture_sha'] and fixture['source_identity']==packet['fixture_identity'],'journal fixture digest differs')
    state=view.get(genesis['state_ref'],'ExecutionState');state_sha=digest(state)
    require(state_sha==genesis['after_state_sha'],'genesis state digest differs')
    head=sha256(raw['journal/genesis.json']).hexdigest();states={};last_state_ref=genesis['state_ref'];hour_events=[]
    prefixes={n for n in raw if n.startswith('trusted_prefixes/')};committed=len(prefixes)-1
    require(0<=committed<=10 and prefixes=={f'trusted_prefixes/prefix_{i:06d}.json' for i in range(committed+1)},'trusted prefix set differs')
    cas_keys=set(genesis['after_cas_keys']);require(cas_keys==view.closure([genesis['fixture_ref'],genesis['state_ref']]),'genesis object inventory differs')
    def binding_check(value,ordinal,closed,scientific_outcome=None):
        keys(value,'genesis_sha known_head_sha known_entries known_state_sha closed scientific_outcome publication_outcome failure_sha known_cas_keys')
        require(type(value['known_entries']) is int and same(value['known_cas_keys'],sorted(cas_keys))
            and value['genesis_sha']==sha256(raw['journal/genesis.json']).hexdigest() and value['known_head_sha']==head
            and value['known_entries']==ordinal and value['known_state_sha']==state_sha
            and value['closed'] is closed and value['failure_sha'] is None and value['publication_outcome']=='committed','trusted binding differs')
        if not closed:require(value['scientific_outcome'] is None,'active prefix has closed outcome')
        if scientific_outcome is not None:require(value['scientific_outcome']==scientific_outcome,'trusted outcome differs')
    binding_check(codec.parse(raw['trusted_prefixes/prefix_000000.json']),0,False)
    entries={n for n in raw if n.startswith('journal/entry_')}
    require(entries=={f'journal/entry_{i:06d}.json' for i in range(1,committed+2)},'journal entry set differs')
    for i in range(1,committed+2):
        path=f'journal/entry_{i:06d}.json';entry=codec.parse(raw[path])
        keys(entry,'after_cas_keys schema kind ordinal previous_sha before_state_sha after_state_sha payload_ref state_ref')
        require(type(entry['ordinal']) is int and entry['ordinal']==i and entry['schema']==genesis['schema']
            and entry['previous_sha']==head and entry['before_state_sha']==state_sha,'journal chain differs')
        require(entry['kind']==('hour' if i<=committed else 'attempt' if report['failure'] and report['failure']['stage']=='actual_numeric' else 'terminal'),'journal entry kind differs')
        payload=view.get(entry['payload_ref'],'dict')
        if entry['kind']!='attempt':
            candidate=view.get(entry['state_ref'],'ExecutionState');require(digest(candidate)==entry['after_state_sha'],'entry state digest differs')
            if entry['kind']=='hour':
                keys(payload,'row independent_audit')
                rejected=terminal_rejection and i==committed
                require(len(candidate['records'])==i and candidate['records'][-1]['actual_accepted'] is (not rejected)
                    and candidate['stopped'] is rejected and same(candidate['records'][:-1],state['records']),'committed state row differs')
                row=candidate['records'][-1]
                keys(row,'prepared proposal actual actual_audit violations proposal_ledger_applied actual_accepted full_replay_conditions_satisfied ledger_scope fx_contract_status')
                require(row['proposal_ledger_applied'] is row['actual_accepted'],'row acceptance/application flags differ')
                require(row['prepared']['observation']['hour']==-3+i and row['prepared']['state_sha']==state_sha
                    and row['proposal']['state_sha']==state_sha and row['proposal']['prepared_sha']==digest(row['prepared'])
                    and same(payload['row'],row),'entry payload row/observation binding differs')
                if not rejected:states[ACTUAL[i-1]]=digest(candidate)
                event_slot=report['points_imported'] if rejected else ACTUAL[i-1]
                hour_events.append((event_slot,dict(stage='hour_adopted',next_hour=candidate['ledger']['last_hour']+candidate['first_hour'],stopped=rejected)))
            else:
                keys(payload,'checkpoint_state summary independent_audit scientific_outcome next_input resume_permitted')
                require(entry['state_ref']==last_state_ref and same(payload['checkpoint_state'],state)
                    and same(payload['summary'],report['metrics']['summary']) and same(payload['independent_audit'],report['metrics']['independent_audit'])
                    and payload['scientific_outcome']==report['metrics']['scientific_outcome']
                    and payload['resume_permitted'] is False and payload['next_input']=='not_observed','terminal state/metrics differs')
            state,state_sha,last_state_ref=candidate,digest(candidate),entry['state_ref']
        else:
            require(entry['state_ref'] is entry['after_state_sha'] is None,'attempt contains accepted state')
            keys(payload,'stage observation evidence prepared proposal actual error_type error reference_request_ids adopted mathematical_infeasibility_inferred after_state_sha')
            failed_slot=schedule[report['point_attempts_reserved']-1]
            require(payload['stage']=='actual' and payload['adopted'] is payload['mathematical_infeasibility_inferred'] is False
                and payload['after_state_sha'] is payload['actual'] is None and type(payload['error_type']) is type(payload['error']) is str
                and payload['observation']['hour']==failed_slot['hour'] and same(payload['prepared']['observation'],payload['observation'])
                and same(payload['evidence'],payload['prepared']['evidence'])
                and payload['prepared']['state_sha']==state_sha and payload['proposal']['state_sha']==state_sha
                and payload['proposal']['prepared_sha']==digest(payload['prepared'])
                and payload['reference_request_ids']==[schedule[n-1]['request_sha'] for n in failed_slot['reference_slots']],'actual attempt payload differs')
        next_keys=entry['after_cas_keys'];expected_cas=cas_keys|view.closure([entry['payload_ref']]+([] if entry['state_ref'] is None else [entry['state_ref']]))
        require(type(next_keys) is list and next_keys==sorted(expected_cas),'journal CAS inventory differs')
        cas_keys=set(next_keys);head=sha256(raw[path]).hexdigest()
        if i<=committed:binding_check(codec.parse(raw[f'trusted_prefixes/prefix_{i:06d}.json']),i,False)
    trusted=codec.parse(raw['trusted_binding.json']);binding_check(trusted,committed+1,True)
    require(cas_keys==set(k+'.json' for k in view.objects),'unaccounted journal CAS objects')
    metrics=report['metrics'];keys(metrics,'state_sha state_cas_sha summary independent_audit scientific_outcome publication_outcome terminal_entry_present state_certainty closed_entry_present unaccepted_attempt failure pending_terminal_checkpoint pending_cas_objects unreferenced_final_cas_objects genesis_sha head_sha final_entries saved_objects resume_permitted')
    require(metrics['state_sha']==state_sha and metrics['state_cas_sha']==last_state_ref and metrics['head_sha']==head
        and metrics['genesis_sha']==trusted['genesis_sha'] and type(metrics['final_entries']) is int and metrics['final_entries']==committed+1
        and type(metrics['saved_objects']) is int and metrics['saved_objects']==len(view.objects)
        and metrics['scientific_outcome']==trusted['scientific_outcome'] and metrics['publication_outcome']=='committed'
        and metrics['state_certainty']=='known' and metrics['resume_permitted'] is False
        and metrics['failure'] is metrics['pending_terminal_checkpoint'] is None and metrics['pending_cas_objects']==[]
        and metrics['closed_entry_present'] is True and metrics['unreferenced_final_cas_objects']==[]
        and same(metrics['unaccepted_attempt'],payload if entry['kind']=='attempt' else None)
        and trusted['scientific_outcome'] in (('actual_unresolved',) if entry['kind']=='attempt' else ('known_rejection',) if terminal_rejection else ('complete','missing_input','right_censored'))
        and metrics['terminal_entry_present'] is (entry['kind']=='terminal'),'saved metrics state reference differs')
    imported=report['points_imported']
    if terminal_rejection:
        require(committed>=1 and len(states)==committed-1 and imported in (ACTUAL[committed-1]-1,ACTUAL[committed-1]),'rejected hour point boundary differs')
    else:require(committed==len(states)==sum(n<=imported for n in ACTUAL),'committed/accepted hours differ from imported actual slots')
    require(report['actual_accepted_slots']==list(states),'actual accepted slot set differs')
    return states,state,hour_events,committed


def point_references(raw,pins,schedule,count,imported,reg,registration_sha,states,outer_members):
    points={};expected=set();members=set();invoked=returned=0
    point_dirs={n.split('/')[1] for n in raw if n.startswith('points/')}
    require(point_dirs=={f'point_{i:04d}' for i in range(1,count+1)},'point directory set differs')
    for slot in schedule[:count]:
        i=slot['ordinal'];prefix=f'points/point_{i:04d}/'
        names={prefix+n for n in ('request.json','result.json','native.json','native.log','process.json','point.stdout.log','point.stderr.log','point_observations.json')}
        objects={n for n in raw if n.startswith(prefix+'cas/objects/')};expected|=names|objects
        require(names<=set(raw) and objects,'point files missing')
        request=codec.parse(raw[prefix+'request.json']);keys(request,'ordinal query_ref query_sha problem_sha pins_sha role hour registration_sha execution_binding')
        result=codec.parse(raw[prefix+'result.json']);keys(result,'status error evidence_ref raw_pin request_sha query_sha problem_sha infeasibility_inferred')
        require(type(request['ordinal']) is int and request['ordinal']==i and type(request['hour']) is int
            and request['hour']==slot['hour'] and request['role']==slot['role'] and request['registration_sha']==registration_sha
            and request['pins_sha']==digest(reg['pins']),'point request frame differs')
        view=WireView(raw,prefix+'cas/objects/');query=view.get(request['query_ref'],'BoundQuery');q=query['request'];qid=query_identity(query)
        require(qid==request['query_sha'] and q['role']==slot['role'] and q['hour']==slot['hour']
            and (q['plan'],q['clean_path'],q['method'])==('on_time','early','full_temporal')
            and same(q['outages'],slot['outage']) and q['anchor_id']==slot['parent_request_sha']
            and q['objective']==slot['objective'],'point query frame differs')
        request_id=digest(q);require(slot['request_sha'] is None and slot['role']=='actual_P' or request_id==slot['request_sha'],'static request digest differs')
        predecessor=points.get(slot['parent_slot']);gate=slot['state_after_actual_slot']
        binding=dict(ordinal=i,slot_sha=digest(slot),request_sha=request_id,bound_query_sha=qid,parent_slot=slot['parent_slot'],
            parent_point_sha=None if predecessor is None else predecessor['point_sha'],parent_economic_sha=None if predecessor is None else predecessor['economic_sha'],
            state_after_actual_slot=gate,accepted_state_sha=None if gate is None else states[gate])
        require(same(request['execution_binding'],binding),'materialized slot binding differs')
        require(query['base_query'] is query['base_point'] is query['base_economic'] is None if predecessor is None else
            same(query['base_query'],predecessor['query']) and digest(query['base_point'])==predecessor['point_sha']
            and digest(query['base_economic'])==predecessor['economic_sha'],'saved parent evidence differs')
        native=codec.parse(raw[prefix+'native.json'])
        require(result['request_sha']==pins[prefix+'request.json']['sha256'] and result['query_sha']==qid
            and sha(result['problem_sha'])==request['problem_sha']==native['problem_sha']
            and result['raw_pin']==pins[prefix+'native.json'] and native['log_pin']==pins[prefix+'native.log']
            and result['infeasibility_inferred'] is False,'point returned file binding differs')
        numeric=i>imported
        current_members=process_ok(codec.parse(raw[prefix+'process.json']),POINT_LIMITS,outer_members,numeric=numeric)
        require(members.isdisjoint(current_members),'internal Job identities overlap');members|=current_members
        require(type(native['run_invoked']) is type(native['run_returned']) is bool,'native run flag scalar differs')
        invoked+=int(native['run_invoked']);returned+=int(native['run_returned'])
        obs=codec.parse(raw[prefix+'point_observations.json']);require(obs['allow_native'] is True,'point observations mode differs')
        if numeric:
            keys(result['error'],'type message')
            require(result['status']=='numeric_unresolved' and type(result['error']['type']) is type(result['error']['message']) is str
                and result['evidence_ref'] is None,'numeric failure witness differs')
            require(set(k+'.json' for k in view.objects)==view.closure([request['query_ref']]),'numeric point CAS closure differs')
            continue
        require(result['status']=='imported' and result['error'] is None and native['run_invoked'] is native['run_returned'] is True,'point import protocol differs')
        evidence=view.get(result['evidence_ref'],'PointEvidence');require(same(evidence['query'],query),'saved evidence query differs')
        require(set(k+'.json' for k in view.objects)==view.closure([request['query_ref'],result['evidence_ref']]),'point CAS closure differs')
        economic,child=evidence['economic'],evidence['child_lp'];family=slot['evidence_kind']
        require((family=='economic_kkt' and type(economic) is dict and child is None)
            or (family=='child_lp_kkt' and type(child) is dict and economic is None)
            or (family=='primal_point' and economic is child is None),'point evidence family differs')
        point=evidence['point'];point_sha=digest(point);require(point['query_sha']==qid,'point witness query differs')
        for value in (economic,child):
            if value is not None:require(value['query_sha']==qid and value['point_sha']==point_sha,'stored certificate references differ')
        points[i]=dict(query=query,query_sha=qid,point_sha=point_sha,economic_sha=None if economic is None else digest(economic),
            child_sha=None if child is None else digest(child),point=point,evidence=evidence)
    require({n for n in raw if n.startswith('points/')}==expected,'unknown point file')
    return points,members,invoked,returned


def contract_references(rows,schedule,points,imported):
    expected=[r for r in schedule if r['section']=='contract' and r['role']=='fault_raw_need' and r['ordinal']<=imported]
    require(type(rows) is list and len(rows)==len(expected),'contract row count differs')
    for row,slot in zip(rows,expected):
        keys(row,'hour outage normal_query firm_query raw_query raw_curtailment_mw normal_point_sha normal_economic_sha firm_point_sha raw_point_sha raw_optimality_sha firm_audit raw_optimality_audit legal_X')
        normal,firm,raw=(points[n] for n in (slot['parent_slot'],slot['ordinal']-1,slot['ordinal']))
        wanted=dict(hour=slot['hour'],outage=slot['outage'],normal_query=normal['query_sha'],firm_query=firm['query_sha'],raw_query=raw['query_sha'],
            raw_curtailment_mw=raw['point']['curtailment_mw'],normal_point_sha=normal['point_sha'],normal_economic_sha=normal['economic_sha'],
            firm_point_sha=firm['point_sha'],raw_point_sha=raw['point_sha'],raw_optimality_sha=raw['child_sha'])
        require(same({n:row[n] for n in wanted},wanted),'contract point references differ')
        require(row['firm_audit']['point_constraints_satisfied'] is True and row['raw_optimality_audit']['lp_optimality_conditions_satisfied'] is True,'stored contract audit protocol differs')
        require(type(row['legal_X']['point_legal_under_X']) is bool,'stored legal X scalar differs')


def events_check(raw,schedule,count,imported,accepted,rows,complete,hour_events=None):
    expected=[dict(stage='start')];contracts=0
    for slot in schedule[:count]:
        i=slot['ordinal'];expected.append(dict(stage='point_reserved',ordinal=i,role=slot['role'],hour=slot['hour']))
        if i>imported:break
        expected.append(dict(stage='point_imported',ordinal=i))
        if hour_events is None:
            if slot['role']=='actual_P' and i in ACTUAL[:accepted]:expected.append(dict(stage='hour_adopted',next_hour=slot['hour']+1,stopped=False))
        else:expected.extend(event for ordinal,event in hour_events if ordinal==i)
        if slot['section']=='contract' and slot['role']=='fault_raw_need':
            contracts+=1;expected.append(dict(stage='contract_row',hour=slot['hour'],rows=contracts))
    expected += [dict(stage='fresh_reserved'),dict(stage='fresh_returned'),dict(stage='report',package_complete=complete)]
    lines=raw.splitlines();require(len(lines)==len(expected) and contracts==rows,'event count differs');last=0
    for i,(line,wanted) in enumerate(zip(lines,expected),1):
        event=codec.parse(line);require(set(event)==set(wanted)|{'sequence','elapsed'} and type(event['sequence']) is int and event['sequence']==i,'event schema/sequence differs')
        require(type(event['elapsed']) in (int,float) and math.isfinite(event['elapsed']) and event['elapsed']>=last,'event elapsed differs');last=event['elapsed']
        require(same({n:event[n] for n in wanted},wanted),'event protocol order differs')


def protocol(snapshot,context,reg,packet,process_record,numeric,terminal_rejection=False):
    raw,pins=snapshot['raw'],snapshot['pins'];completion_pin=completion(raw,pins)
    require(not any(n.endswith('.pending') or n.rsplit('/',1)[-1].endswith('_failure.json') and not (numeric and n=='numeric_failure.json')
        or n=='journal/failure.json' for n in raw),'failure/pending cannot close protocol')
    report=codec.parse(raw['report.json']);keys(report,'authority package_complete failure point_attempts_reserved points_imported native_run_invoked_observed native_run_returned_observed fresh_launches metrics contracts full_139_executed actual_accepted_slots resource_admission overall_performance_review_complete fx_temporal_backing formal_result')
    require(report['authority']=='DRAFT_NONAUTHORITATIVE' and all(report[n] is False for n in ('resource_admission','overall_performance_review_complete','fx_temporal_backing','formal_result')),'worker report authority differs')
    count,imported=report['point_attempts_reserved'],report['points_imported']
    require(type(count) is type(imported) is int and 1<=count<=319 and imported==count-int(numeric),'point counts differ')
    complete=not (numeric or terminal_rejection)
    require(report['package_complete'] is complete and report['full_139_executed'] is complete,'worker completion claims differ')
    require(type(report['fresh_launches']) is int and report['fresh_launches']==1,'fresh launch count differs')
    if numeric:
        keys(report['failure'],'stage type message')
        require(type(report['failure']['type']) is type(report['failure']['message']) is str
            and report['failure']['stage'] in ('reference_numeric','actual_numeric','contract_numeric'),'numeric failure stage differs')
        require('numeric_failure.json' in raw,'numeric failure record missing')
        failure=codec.parse(raw['numeric_failure.json']);keys(failure,'stage type message infeasibility_inferred');require(failure['infeasibility_inferred'] is False
            and same({k:v for k,v in failure.items() if k!='infeasibility_inferred'},report['failure']),'numeric failure report differs')
        role=packet['schedule'][count-1];stage='contract_numeric' if role['section']=='contract' else 'actual_numeric' if role['role']=='actual_P' else 'reference_numeric'
        require(report['failure']['stage']==stage,'numeric failure slot differs')
    elif terminal_rejection:require(count==imported<=41 and report['failure'] is None and 'numeric_failure.json' not in raw,'terminal rejection counts differ')
    else:require(count==imported==319 and report['failure'] is None,'success point count differs')
    launcher=codec.parse(raw['launcher_start.json']);require(same(launcher,dict(limits=CAPS,package='staged_rts24_P2_v1',registration_sha=context['registration']['pin']['sha256'])),'launcher start differs')
    require(same(codec.parse(raw['launcher.json']),process_record),'saved outer supervisor record differs')
    start=codec.parse(raw['start.json']);keys(start,'authority pins preserved packet_pin max_point_attempts registration_sha native_user_authority')
    require(start['authority']=='DRAFT_NONAUTHORITATIVE' and same(start['pins'],reg['pins']) and same(start['preserved'],reg['preserved'])
        and start['packet_pin']==PACKET_PINS['packet.json'] and type(start['max_point_attempts']) is int and start['max_point_attempts']==319
        and start['registration_sha']==context['registration']['pin']['sha256']
        and start['native_user_authority']=='external_explicit_user_instruction_not_inferred_from_files','worker start differs')
    states,state,hour_events,committed=journal_references(raw,packet['schedule'],report,reg,packet,terminal_rejection)
    members={(m['pid'],m['creation_filetime']) for m in process_record['quiescence_witness']['member_identities']}
    points,inner_members,invoked,returned=point_references(raw,pins,packet['schedule'],count,imported,reg,context['registration']['pin']['sha256'],states,members)
    require(type(report['native_run_invoked_observed']) is type(report['native_run_returned_observed']) is int
        and report['native_run_invoked_observed']==invoked and report['native_run_returned_observed']==returned,'observed native run counts differ')
    prepared_rows=[row['prepared'] for row in state['records']]
    if report['failure'] and report['failure']['stage']=='actual_numeric':prepared_rows.append(report['metrics']['unaccepted_attempt']['prepared'])
    for prepared in prepared_rows:
        hour=prepared['observation']['hour'];slots=[r for r in packet['schedule'] if r['section']=='actual' and r['hour']==hour]
        actual_slot=slots[-1];by_role={r['role']:points[r['ordinal']]['evidence'] for r in slots[:-1]}
        require(same(prepared['evidence'],dict(reference=by_role['reference_base_P0'],raw=by_role.get('reference_raw_need'),
            lower=by_role['recovery_min_meter'],upper=by_role['recovery_max_meter']))
            and same(prepared['actual_outage'],actual_slot['outage']),'prepared reference point graph differs')
    for i,row in enumerate(state['records']):
        if row['actual'] is None:require(terminal_rejection and count==ACTUAL[i]-1,'missing committed actual point')
        else:require(ACTUAL[i] in points and same(row['actual'],points[ACTUAL[i]]['evidence']),'committed state actual point differs')
    rows=codec.parse(raw['contract_rows.json']);require(same(rows,report['contracts']),'saved contract/report differ');contract_references(rows,packet['schedule'],points,imported)
    require(not complete or len(states)==10 and len(rows)==138,'success state/contract counts differ')
    fresh_members=process_ok(codec.parse(raw['fresh_process.json']),FRESH_LIMITS,members)
    require(inner_members.isdisjoint(fresh_members),'fresh and point Job identities overlap');inner_members|=fresh_members
    require((process_record['owner_pid'],process_record['owner_creation_filetime']) not in inner_members,'outer owner appears in internal Job')
    residual=members-inner_members
    require((process_record['owner_pid'],process_record['owner_creation_filetime']) in residual
        and len(members)==len(inner_members)+len(residual),'outer Job history partition differs')
    fresh=codec.parse(raw['fresh.json']);keys(fresh,'metrics solver_calls');require(type(fresh['solver_calls']) is int and fresh['solver_calls']==0 and same(fresh['metrics'],report['metrics']),'fresh metrics differ')
    for name in ('worker_observations.json','fresh_observations.json'):require(codec.parse(raw[name])['allow_native'] is False,'worker/fresh observations mode differs')
    events_check(raw['events.jsonl'],packet['schedule'],count,imported,len(states),len(rows),complete,hour_events)
    root_files=EXCLUDED|{'launcher_start.json','start.json','report.json','events.jsonl','contract_rows.json','trusted_binding.json',
        'fresh.json','fresh_process.json','fresh_observations.json','fresh.stdout.log','fresh.stderr.log','worker_observations.json'}
    if numeric:root_files.add('numeric_failure.json')
    require({n for n in raw if '/' not in n}==root_files,'unknown or missing root file')
    require(all('/' not in n or n.startswith(('points/','journal/','trusted_prefixes/')) for n in raw),'unknown top-level tree')
    require({n for n in raw if n.startswith('journal/') and not n.startswith('journal/objects/')}=={'journal/genesis.json',*{f'journal/entry_{i:06d}.json' for i in range(1,committed+2)}},'unknown journal file')
    wanted_dirs={'.'}
    for n in raw:
        wanted_dirs.update(p.as_posix() for p in PurePosixPath(n).parents if p.as_posix()!='.')
    require(set(snapshot['directories'])==wanted_dirs,'unknown empty directory')
    require(len(pins)==process_record['terminal_files']+1
        and sum(v['bytes'] for v in pins.values())==process_record['terminal_bytes']+len(raw['launcher.json']),'outer terminal inventory accounting differs')
    return dict(completion_core_pin=completion_pin,report_pin=pins['report.json'],point_reference_count=count,
        points_imported=imported,contract_row_reference_count=len(rows),actual_state_reference_count=len(states),committed_hour_entries=committed,
        outer_job_history_partition_verified=True,outer_member_count=len(members),known_inner_member_count=len(inner_members),
        outer_residual_member_count=len(residual),outer_residual_member_identities=[dict(pid=p,creation_filetime=t) for p,t in sorted(residual)],
        unverified_worker_claims=dict(package_complete=report['package_complete'],full_139_executed=report['full_139_executed']))


def inspect_package(held_context,expected_context_sha,process_record,startup_record,hook=None):
    require(type(held_context) is bytes and pin(held_context)['sha256']==expected_context_sha,'held package context SHA differs')
    context=codec.parse(held_context);require(validate_context(context)==held_context,'package context differs')
    require(same(startup_record,context['startup']),'parent supplied startup record differs')
    assessment=parent.assess_process(process_record,CAPS);record=assessment['process_snapshot']
    result=dict(authority='DRAFT_NONAUTHORITATIVE',context_sha=expected_context_sha,inspection_status='inspection_prohibited',
        process_snapshot=record,parent_supplied_startup_record=json.loads(codec.canonical(startup_record)),
        mechanical_package_integrity=False,outer_process_verified=assessment['inspection_permitted'],inner_process_records_verified=False,
        completion_core_verified=False,full_inventory_verified=False,journal_reference_chain_verified=False,fresh_worker_protocol_closed=False,
        inventory=None,inventory_directories=None,inventory_sha=None,inventory_files=None,inventory_bytes=None,protocol_error=None,
        completion_core_pin=None,report_pin=None,point_reference_count=None,points_imported=None,contract_row_reference_count=None,
        actual_state_reference_count=None,committed_hour_entries=None,unverified_worker_claims=None,source_freshness_selected_only=False,
        outer_job_history_partition_verified=False,outer_member_count=None,known_inner_member_count=None,outer_residual_member_count=None,
        outer_residual_member_identities=None,process_tree_attribution_independently_verified=False,
        actual_spawn_argv_verified=False,full_runtime_closure_verified=False,typed_values_validated=False,
        scientific_audit_replayed=False,scientific_evidence_adopted=False,full_139_independently_verified=False,
        fx_temporal_backing=False,resource_admission=False,formal_result=False,official_verdict=None,receipt=None,seal=None)
    if assessment['ownership_status']!='quiet_verified':return result
    inputs,reg,packet=read_inputs(context)
    worker=codec.directory_chain(absolute(context['worker_root']));par=codec.directory_chain(absolute(context['parent_root']))
    require(not worker.resolve().is_relative_to(par.resolve()) and not par.resolve().is_relative_to(worker.resolve()),'physical parent and worker overlap')
    try:before=inventory(worker)
    except InventoryLimit as exc:result['protocol_error']=dict(type=type(exc).__name__,message=str(exc));return result
    details=None;diagnostic=(record['exit_code']==2 and record['stop_reason']=='child_exit_nonzero' and record['monitor_error'] is record['cleanup_error'] is None and assessment['proposal_caps_satisfied'])
    terminal_rejection=False
    if assessment['inspection_permitted'] or diagnostic:
        try:
            saved_report=codec.parse(before['raw']['report.json']);terminal_rejection=diagnostic and saved_report['failure'] is None
            details=protocol(before,context,reg,packet,record,diagnostic and not terminal_rejection,terminal_rejection)
        except (ValueError,KeyError,TypeError,IndexError,RecursionError) as exc:result['protocol_error']=dict(type=type(exc).__name__,message=str(exc)[:256])
    if hook is not None:hook('before_bookend',worker)
    after=inventory(worker);require(before==after,'worker inventory bookend differs')
    again,_,_=read_inputs(context);require(inputs==again,'package input bookend differs')
    result.update(full_inventory_verified=True,inventory=before['pins'],inventory_directories=before['directories'],inventory_sha=digest(before['pins']),inventory_files=len(before['pins']),
        inventory_bytes=sum(v['bytes'] for v in before['pins'].values()),source_freshness_selected_only=True,inspection_status='failure_inventory_captured')
    if details is not None:
        result.update(details,inspection_status='terminal_diagnostic_closed' if terminal_rejection else 'numeric_diagnostic_closed' if diagnostic else 'success_protocol_closed',
            mechanical_package_integrity=True,inner_process_records_verified=True,completion_core_verified=True,
            journal_reference_chain_verified=True,fresh_worker_protocol_closed=True)
    return result
