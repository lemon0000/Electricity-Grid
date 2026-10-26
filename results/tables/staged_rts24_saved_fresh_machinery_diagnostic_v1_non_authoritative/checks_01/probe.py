"""One ordinary cold-loader observation; never changes a guard or import policy."""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
admission=json.loads((OUT/'admission.json').read_bytes())
policy_raw=(ROOT/admission['policy_path']).read_bytes();assert pin(policy_raw)==admission['policy_pin']
policy=json.loads(policy_raw)
counts=dict(P1_open=0,actual_F_open=0,write_attempts=0,mutation_attempts=0,unexpected_process=0,optional_seen=0)
roots={k:os.path.normcase(os.path.abspath(v)) for k,v in policy['protected_open_roots'].items()}
def audit(event,args):
    if event in policy['process_events'] or event.startswith(tuple(policy['process_event_prefixes'])):
        if event=='subprocess.Popen' and tuple(args)==(None,'lscpu',None,None):counts['optional_seen']+=1
        else:counts['unexpected_process']+=1;raise AssertionError('unlisted diagnostic process event')
    if event in policy['mutation_events']:counts['mutation_attempts']+=1;raise AssertionError('diagnostic mutation rejected')
    if event=='open':
        path,mode,flags=args[:3]
        if isinstance(path,(str,bytes,os.PathLike)):
            target=os.path.normcase(os.path.abspath(os.fsdecode(path)))
            for key,root in roots.items():
                if target==root or target.startswith(root+os.sep):counts[key+'_open']+=1;raise AssertionError('protected diagnostic open rejected')
        if type(mode) is str and any(c in mode for c in 'wax+') or type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            counts['write_attempts']+=1;raise AssertionError('diagnostic write rejected')
sys.addaudithook(audit);sys.path.insert(0,str(ROOT))
entry=ROOT/admission['entry_path']
spec=importlib.util.spec_from_file_location('_machinery_diagnostic_entry',entry);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
before=(tuple(sys.meta_path),tuple(sys.path_hooks),tuple(sys.path),sys.path_importer_cache,sys.modules)
containers=(sys.meta_path,sys.path_hooks,sys.path)
guard=None;returned=False;error_type=None
try:
    adapter,guard=module.load_saved_successor_dependencies(admission['source_pins'],policy_raw);returned=True
except BaseException as error:
    error_type=type(error).__name__
    if type(error) is module.SavedSuccessorImportUnresolved:guard=error.boundary
after=(tuple(sys.meta_path),tuple(sys.path_hooks),tuple(sys.path),sys.path_importer_cache,sys.modules)
tokens={}
def describe(obj):
    cls=obj if isinstance(obj,type) else type(obj)
    descriptor=dict(kind='class' if isinstance(obj,type) else 'instance',type_module=cls.__module__,type_qualname=cls.__qualname__)
    if callable(obj):descriptor.update(callable_module=getattr(obj,'__module__',cls.__module__),callable_qualname=getattr(obj,'__qualname__',cls.__qualname__))
    token=tokens.setdefault(id(obj),'object_'+str(len(tokens)+1))
    return dict(identity_token=token,identity_sha=sha256(token.encode('ascii')).hexdigest(),descriptor=descriptor,descriptor_sha=sha256(raw(descriptor)).hexdigest())
def ordered(left,right,container_same):
    old_ids=tuple(map(id,left));new_ids=tuple(map(id,right));short=min(len(left),len(right))
    first=next((i for i in range(short) if old_ids[i]!=new_ids[i]),None)
    if first is None and len(left)!=len(right):first=short
    return dict(equal=old_ids==new_ids,container_identity_same=container_same,before_length=len(left),after_length=len(right),
        first_difference_index=first,before=[describe(x) for x in left],after=[describe(x) for x in right],
        added_indices=[i for i,x in enumerate(new_ids) if x not in old_ids],removed_indices=[i for i,x in enumerate(old_ids) if x not in new_ids],
        retained_relative_order_same=tuple(x for x in new_ids if x in old_ids)==tuple(x for x in old_ids if x in new_ids))
def path_item(value):
    assert type(value) is str
    norm=os.path.normcase(os.path.abspath(value));env=os.path.normcase(str(Path(policy['executable_path']).parent))
    category='repo' if norm==os.path.normcase(str(ROOT)) or norm.startswith(os.path.normcase(str(ROOT))+os.sep) else 'environment' if norm==env or norm.startswith(env+os.sep) else 'other'
    encoded=value.encode('utf8');return dict(bytes=len(encoded),sha256=sha256(encoded).hexdigest(),category=category)
left,right=before[2],after[2];short=min(len(left),len(right))
first=next((i for i in range(short) if left[i]!=right[i]),None)
if first is None and len(left)!=len(right):first=short
comparison=dict(meta_path=ordered(before[0],after[0],containers[0] is sys.meta_path),path_hooks=ordered(before[1],after[1],containers[1] is sys.path_hooks),
    path=dict(equal=left==right,container_identity_same=containers[2] is sys.path,before_length=len(left),after_length=len(right),first_difference_index=first,before=[path_item(x) for x in left],after=[path_item(x) for x in right]),
    path_importer_cache=dict(container_identity_same=before[3] is after[3]),modules=dict(container_identity_same=before[4] is after[4]))
saved=(tuple(map(id,before[0])),tuple(map(id,before[1])),before[2],id(before[3]),id(before[4]))
anchor_matches=guard is not None and saved==guard._import_machinery
report=None if guard is None else json.loads(guard.report_raw)
source_recorded=guard is not None and guard._source_raw==raw(admission['source_pins'])
different=any(not comparison[n]['equal'] for n in ('meta_path','path_hooks','path')) or any(not comparison[n]['container_identity_same'] for n in ('path_importer_cache','modules'))
complete=anchor_matches and report is not None and not report['hook_active'] and report['phase']=='FAULTED' and not returned and error_type=='SavedSuccessorImportUnresolved' and source_recorded and different and counts['optional_seen']==1 and all(counts[n]==0 for n in counts if n!='optional_seen')
value=dict(authority='DRAFT_NONAUTHORITATIVE',diagnostic_capture_accepted=bool(complete),
    loader_returned=returned,error_type=error_type,boundary=report,before_snapshot_matches_boundary=anchor_matches,comparison=comparison,counts=counts,
    source49_raw_recorded=source_recorded,scientific_API_calls_instrumented=False,
    predecessor_combined_resource_admission=False,policy_resource_admission=False,cold_acceptance=False,independent_root_verified=False,
    full_runtime_binding_verified=False,actual_F=False,run_authority=False,resource_admission=False,formal_result=False)
print(json.dumps(value,sort_keys=True),flush=True)
assert value['diagnostic_capture_accepted'] and all(counts[n]==0 for n in counts if n!='optional_seen')
raise SystemExit(0)
