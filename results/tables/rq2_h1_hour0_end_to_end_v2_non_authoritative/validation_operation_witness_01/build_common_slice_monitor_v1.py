"""Build a diagnostic monitor using previously tested PID/creation cleanup."""
import ast
from pathlib import Path

HERE=Path(__file__).resolve().parent
P=HERE.parent/'validation_path_optimization_01'
old=(P/'run_bounded_configured_entry_v3.py').read_text(encoding='utf-8')
saved=(HERE/'run_saved_bounded_v1.py').read_text(encoding='utf-8')
nodes={node.name:ast.get_source_segment(saved,node) for node in ast.parse(saved).body if isinstance(node,ast.FunctionDef)}
helpers='\n\n'.join(nodes[name] for name in ('live','observe','finish_children'))
old=old.replace("out = HERE / label\nout.mkdir(exist_ok=False)\n",'')
old=old.replace("if len(arguments)<5 or arguments[0]!='-I':", "if len(arguments)<5 or arguments[0]!='-I':")
anchor="child_output=entry/arguments[4]\nif child_output.exists():raise ValueError('fresh child attempt root required')\nstorage_roots=[out,child_output]"
replacement="""kind,mode,child_label,*targets=arguments[2:]
if kind=='unit':
    if mode!='parse' or targets or child_label!='unit_checks_02' or limit>120 or ram>512*1024**2 or storage_cap>64*1024**2:
        raise ValueError('exact bounded unit role required')
elif kind=='pytest':
    if (mode!='parse_path' or child_label!='common_slice_01'
            or targets!=['tests/test_h1_guarded_common_slice_development_v1.py']):
        raise ValueError('exact single bounded common-slice role required')
else:raise ValueError('unit or one common slice role required')
out=HERE/label
child_output=entry/child_label
if out.exists() or child_output.exists():raise ValueError('fresh outer and child attempt roots required')
storage_roots=[out,child_output]
out.mkdir(exist_ok=False)"""
if old.count(anchor)!=1:raise ValueError('monitor CLI validation anchor differs')
old=old.replace(anchor,replacement)
old=old.replace('proc = target = None\nresult = {}','proc = target = None\nresult = {}\nowned={};events=[];errors=[]')
anchor='try:\n    with (out / \'stdout.log\').open'
storage="""
def storage_observation():
    total=0;failures=[]
    for root in storage_roots:
        try:
            if not root.exists():continue
            for path in root.rglob('*'):
                try:
                    if path.is_file():total+=path.stat().st_size
                except OSError as error:failures.append(dict(path=str(path),error=repr(error)))
        except OSError as error:failures.append(dict(path=str(root),error=repr(error)))
    return total,failures

"""
if old.count(anchor)!=1:raise ValueError('monitor execution anchor differs')
old=old.replace(anchor,helpers+'\n\n'+storage+anchor)
old=old.replace("save('started.json', dict(pid=proc.pid, creation_time=target.create_time()))",
    "owned[proc.pid]=target.create_time()\n        save('started.json', dict(pid=proc.pid, creation_time=owned[proc.pid]))")
old=old.replace('processes = [target, *target.children(recursive=True)]','processes = observe()')
anchor="storage = sum(p.stat().st_size for root in storage_roots if root.exists()\n                    for p in root.rglob('*') if p.is_file())"
if old.count(anchor)!=1:raise ValueError('periodic storage anchor differs')
old=old.replace(anchor,"storage,storage_errors=storage_observation()\n                if storage_errors:\n                    errors.extend(storage_errors);reason='storage_read_error';finish_children();break")
start=old.index('                for child in reversed(target.children(recursive=True)):')
end=old.index('                break',start)
old=old[:start]+"                finish_children()\n"+old[end:]
start=old.index('    if proc is not None and proc.poll() is None:\n',old.index('except BaseException:\n'))
end=old.index('finally:\n',start)
old=old[:start]+"    finish_children()\n    if proc is not None:proc.wait()\n"+old[end:]
old=old.replace('finally:\n    drift =',"""finally:
    finish_children()
    storage,storage_errors=storage_observation()
    errors.extend(storage_errors)
    if storage_errors or storage>storage_cap:
        reason=reason or ('storage_read_error' if storage_errors else 'storage')
        result['exit_code']=1
    result.update(storage_read_errors=storage_errors,cleanup_errors=errors,
        final_storage_observation_complete=not storage_errors)
    if errors:result['exit_code']=1
    drift =""")
old=old.replace("sources.update(p for p in entry.iterdir() if p.is_file())", """sources.update(p for p in entry.iterdir() if p.is_file())
sources.update(Path(name) for name in json.loads((entry/'code_allowlist_v3.json').read_bytes())['files_sha256'])
sources.update(REPO/name for name in json.loads((entry/'test_closure_v1.json').read_bytes())['files_sha256'])""")
compile(old,str(P/'run_bounded_configured_entry_v4.py'),'exec')
with (P/'run_bounded_configured_entry_v4.py').open('x',encoding='utf-8') as stream:stream.write(old)
