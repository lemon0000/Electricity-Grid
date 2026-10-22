"""Bounded static LOAD_GLOBAL inventory, not a complete dynamic dependency proof."""
from collections import deque
import dis
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import CodeType,FunctionType

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from experiments import h1_phase_historical_batch_development_v2 as candidate

ROOTS=('_number','_encode','_digest','_validate','_dependencies','normal_input_identity','_validate_request')
MAX_FUNCTIONS,MAX_EDGES=128,4096


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def global_names(code):
    names={op.argval for op in dis.get_instructions(code) if op.opname=='LOAD_GLOBAL'}
    for item in code.co_consts:
        if type(item) is CodeType:names.update(global_names(item))
    return sorted(names)


def main():
    pending=deque(getattr(candidate.model,name) for name in ROOTS)
    seen=set();rows=[];edges=0;truncated=False;bindings={str(Path(__file__)):pin(__file__)}
    guards=candidate._DEPENDENCIES
    while pending:
        function=pending.popleft()
        if id(function) in seen:continue
        if len(seen)>=MAX_FUNCTIONS:truncated=True;break
        seen.add(id(function));namespace=function.__globals__;references=[]
        source=Path(function.__code__.co_filename)
        if source.is_file():bindings[str(source)]=pin(source)
        for name in global_names(function.__code__):
            if edges>=MAX_EDGES:truncated=True;break
            edges+=1
            present=name in namespace;value=namespace.get(name)
            slot=any(vars(obj) is namespace and key==name for obj,key,_,_ in guards if hasattr(obj,'__dict__'))
            state=any(value is v and before is not None for _,_,v,before in guards) if present else False
            references.append(dict(name=name,from_function_globals=present,
                otherwise_builtin_resolution=not present,
                value_type=type(value).__name__ if present else None,
                explicit_alias_slot_guard=slot,explicit_callable_state_guard=state))
            if type(value) is FunctionType and value.__module__.startswith(('src.','experiments.')):
                pending.append(value)
        rows.append(dict(function=function.__module__+'.'+function.__qualname__,file=str(source),
            line=function.__code__.co_firstlineno,references=references))
        if edges>=MAX_EDGES:break
    for path in (Path(candidate.__file__),HERE/'design_and_budget.md',HERE/'preseal_repair_plan.md'):
        bindings[str(path)]=pin(path)
    result=dict(status='DRAFT_NONAUTHORITATIVE',root_functions=list(ROOTS),
        function_limit=MAX_FUNCTIONS,edge_limit=MAX_EDGES,visited_functions=len(rows),
        global_references=edges,enumeration_truncated=truncated,
        includes_nested_code_global_loads=True,
        recursively_resolves_only_plain_project_function_globals=True,
        module_attribute_and_instance_dispatch_expanded=False,
        class_descriptor_and_mutable_value_closure_proved=False,
        full_dynamic_dependency_closure_proved=False,rows=rows,bindings=bindings,
        source_successor_adopted=False,new_normal_jobs=0,real_native_calls=0,
        resource_admission=False,formal_execution_ready=False,formal_result=False)
    target=HERE/'global_inventory_v1.json'
    raw=(json.dumps(result,indent=2)+'\n').encode('utf-8')
    if target.exists():assert target.read_bytes()==raw
    else:target.write_bytes(raw)
    print(json.dumps(dict(functions=len(rows),references=edges,truncated=truncated,
        bindings=len(bindings),sha256=pin(target))))


if __name__=='__main__':main()
