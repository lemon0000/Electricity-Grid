"""Source-held post-spawn parent. Launch and P1 grants remain external and closed."""
import ast
import builtins
import base64
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import subprocess
from threading import get_ident
import tokenize
from types import CodeType,FunctionType,ModuleType,SimpleNamespace

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_complete_bootstrap_native_v2_non_authoritative'
RUNTIME=Path('D:/Miniconda3/envs/compute');EXE=RUNTIME/'python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v42.py'
DRAIN=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v2.py'
SOURCE_CONTROL=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
SOURCE_SHA='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
FLAGS=('external_permission_verified','parent_independent_P1_verified','resource_admission','formal_result','run_authority','actual_F')
_PARENTS={}

def require(value,message):
    if not value:raise ValueError(message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def creator():return os.getpid(),get_ident()
def flags():return {name:False for name in FLAGS}

def data_image(value,depth=0):
    typ=type(value)
    if value is None or typ in (bool,int,float,str,bytes):return typ,value
    if depth>=32:return typ,id(value)
    if typ in (tuple,list):return typ,tuple(data_image(v,depth+1) for v in value)
    if typ in (set,frozenset):return typ,tuple(sorted(data_image(v,depth+1) for v in value))
    if typ is dict:return typ,tuple((k,data_image(v,depth+1)) for k,v in sorted(value.items()))
    return typ,id(value)

def verify_program(held):
    bindings,functions,proof=held
    namespace,original,rows,classes,data,builtin_ns,builtin_rows,attributes,private_modules=proof
    if set(namespace)!=set(name for name,_ in original) or any(namespace[name] is not value for name,value in original):
        raise ValueError('held parent namespace binding changed')
    current=namespace['__builtins__']
    if type(current) is not dict:current=vars(current)
    if current is not builtin_ns or len(current)!=len(builtin_rows) or any(current.get(name) is not value for name,value in builtin_rows):
        raise ValueError('held parent native builtins changed')
    for fn,code,defaults,kw,kw_image,closure,cells,annotations,attrs in rows:
        if fn.__code__ is not code or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kw \
                or data_image(kw)!=kw_image or fn.__closure__ is not closure \
                or any(cell.cell_contents is not item for cell,item in zip(closure or (),cells)) \
                or data_image(fn.__annotations__)!=annotations or data_image(fn.__dict__)!=attrs:
            raise ValueError('held parent source function metadata changed')
    for cls,items,bases in classes:
        values=vars(cls)
        if cls.__bases__!=bases or set(values)!=set(name for name,_ in items) or any(values[name] is not value for name,value in items):
            raise ValueError('held parent class binding changed')
    for value,expected in data:
        if data_image(value)!=expected:raise ValueError('held parent constant image changed')
    for module,items,module_functions in private_modules:
        current=vars(module)
        if set(current)!=set(name for name,_ in items) or any(current[name] is not value for name,value in items):
            raise ValueError('held private module namespace changed')
        for name,function,code,defaults,kw,kw_image,closure,owns_globals in module_functions:
            if current.get(name) is not function or function.__code__ is not code or function.__defaults__ is not defaults \
                    or function.__kwdefaults__ is not kw or data_image(kw)!=kw_image or function.__closure__ is not closure:
                raise ValueError('held private imported function metadata changed')

    for root,path,expected,metadata in attributes:
        value=root
        for name in path:value=vars(value)[name]
        if value is not expected:raise ValueError('held imported direct attribute changed')
        if metadata is not None:
            code,defaults,kw,kw_image,closure=metadata
            if value.__code__ is not code or value.__defaults__ is not defaults or value.__kwdefaults__ is not kw \
                    or data_image(kw)!=kw_image or value.__closure__ is not closure:
                raise ValueError('held imported direct function metadata changed')


def program(namespace):
    bindings=[];functions=[];rows=[];classes=[];data=[]
    def capture_fn(function):
        closure=function.__closure__
        rows.append((function,function.__code__,function.__defaults__,function.__kwdefaults__,data_image(function.__kwdefaults__),
            closure,tuple(cell.cell_contents for cell in closure or ()),data_image(function.__annotations__),data_image(function.__dict__)))
    for name,value in namespace.items():
        if type(value) is FunctionType and value.__globals__ is namespace:
            require(value.__closure__ is None,'closed held parent program required')
            functions.append((name,value.__code__,value.__defaults__,None if value.__kwdefaults__ is None else tuple(value.__kwdefaults__.items())))
            capture_fn(value)
        else:bindings.append((name,value))
        if type(value) is type and value.__module__==namespace.get('__name__'):
            classes.append((value,tuple(vars(value).items()),value.__bases__))
            for member in vars(value).values():
                if type(member) in (staticmethod,classmethod):member=member.__func__
                if type(member) is property:member=member.fget
                if type(member) is FunctionType:capture_fn(member)
        if name not in ('__builtins__','_ACTORS','_PARENTS') and type(value) in (dict,list,set,tuple,frozenset):
            data.append((value,data_image(value)))
    builtin_ns=namespace['__builtins__'];builtin_ns=builtin_ns if type(builtin_ns) is dict else vars(builtin_ns)
    attributes=[]
    syntax=ast.parse(namespace['_SOURCE_RAW'] if '_SOURCE_RAW' in namespace else Path(namespace['__file__']).read_bytes())
    for node in ast.walk(syntax):
        if type(node) is not ast.Attribute:continue
        path=[];base=node
        while type(base) is ast.Attribute:path.append(base.attr);base=base.value
        if type(base) is not ast.Name or base.id not in namespace:continue
        root=namespace[base.id]
        if type(root) not in (ModuleType,type):continue
        value=root
        try:
            for name in reversed(path):value=vars(value)[name]
        except (KeyError,TypeError):continue
        metadata=None
        if type(value) is FunctionType:
            metadata=(value.__code__,value.__defaults__,value.__kwdefaults__,data_image(value.__kwdefaults__),value.__closure__)
        attributes.append((root,tuple(reversed(path)),value,metadata))
    # Recovery never follows a replaced attribute in an observed module namespace.
    private_bindings=[]
    for name,value in bindings:
        if type(value) is ModuleType:
            copied=ModuleType(value.__name__);vars(copied).update(vars(value))
            for key,fn in tuple(vars(copied).items()):
                if type(fn) is FunctionType and fn.__globals__ is vars(value):
                    clone=FunctionType(fn.__code__,vars(copied),fn.__name__,fn.__defaults__,fn.__closure__)
                    clone.__kwdefaults__=None if fn.__kwdefaults__ is None else dict(fn.__kwdefaults__);vars(copied)[key]=clone
            value=copied
        private_bindings.append((name,value))
    private_modules=[]
    for name,value in private_bindings:
        if type(value) is not ModuleType:continue
        module_functions=tuple((key,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,data_image(fn.__kwdefaults__),fn.__closure__,
            fn.__globals__ is vars(value)) for key,fn in vars(value).items() if type(fn) is FunctionType)
        private_modules.append((value,tuple(vars(value).items()),module_functions))
        for root,path,expected,metadata in tuple(attributes):
            if root is not namespace.get(name):continue
            actual=value
            try:
                for key in path:actual=vars(actual)[key]
            except (KeyError,TypeError):continue
            copied_metadata=None
            if type(actual) is FunctionType:
                copied_metadata=(actual.__code__,actual.__defaults__,actual.__kwdefaults__,data_image(actual.__kwdefaults__),actual.__closure__)
            attributes.append((value,path,actual,copied_metadata))
    # Explicit owners cover local Path/Popen/stream methods omitted by global-Name AST edges.
    owners=[Path,type(Path()),subprocess.Popen,io.BufferedReader,io.BufferedWriter,io.FileIO]
    if type(namespace.get('Thread')) is type:owners.append(namespace['Thread'])
    seen={id(cls) for cls,_,_ in classes}
    for owner in owners:
        for cls in owner.__mro__:
            if cls is object or id(cls) in seen:continue
            seen.add(id(cls));classes.append((cls,tuple(vars(cls).items()),cls.__bases__))
            for member in vars(cls).values():
                if type(member) in (staticmethod,classmethod):member=member.__func__
                if type(member) is property:member=member.fget
                if type(member) is FunctionType:capture_fn(member)
    proof=(namespace,tuple(namespace.items()),tuple(rows),tuple(classes),tuple(data),builtin_ns,tuple(builtin_ns.items()),
        tuple(attributes),tuple(private_modules))
    return tuple(private_bindings),tuple(functions),proof

def call(held,name,*args,_verify=verify_program.__code__,_image=data_image.__code__,
        _factory=FunctionType,_native=tuple(vars(builtins).items()),**kwargs):
    # Check the observed namespace from isolated original primitives.
    check=dict(__builtins__=dict(_native));check['data_image']=_factory(_image,check,'held_data_image', (0,))
    _factory(_verify,check,'held_program_verifier')(held)
    context=dict(held[0])
    for key,code,defaults,kw in held[1]:
        function=_factory(code,context,key,defaults);function.__kwdefaults__=None if kw is None else dict(kw);context[key]=function
    return context[name](*args,**kwargs)

def get_program(held,name):
    require(type(held) is tuple and all(type(row) is tuple and len(row)==2 for row in held),'immutable exact held program set required')
    matches=[value for key,value in held if key==name]
    require(len(matches)==1 and tuple(key for key,_ in held)==('core','quiet','validation','replay','transport'),'closed held program names required')
    return matches[0]


def source_module(key):
    name,size,digest=SOURCE_REFS[key];path=ROOT/name;raw=path.read_bytes()
    require(pin(raw)==dict(bytes=size,sha256=digest),'fixed parent source differs: '+key)
    module=ModuleType('_saved_complete_parent_'+key);module.__file__=str(path);vars(module)['_SOURCE_RAW']=raw
    exec(compile(raw,str(path),'exec',dont_inherit=True,optimize=0),vars(module),vars(module))
    return module

def load(path,name):
    path=Path(path)
    key=next((key for key,row in SOURCE_REFS.items() if ROOT/row[0]==path),None)
    require(key is not None,'closed source-held parent library required')
    return source_module(key)

def dependencies():
    return tuple((name,program(vars(source_module(name)))) for name in ('core','quiet','validation','replay','transport'))

def environment():
    result={name:os.environ[name] for name in ('SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE') if name in os.environ}
    system=Path(result['SYSTEMROOT'])
    result['PATH']=';'.join(str(path) for path in (RUNTIME,RUNTIME/'DLLs',RUNTIME/'Library/bin',system/'System32',system))
    result.update(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    return result

def source():
    raw=SOURCE_CONTROL.read_bytes()
    require(pin(raw)==dict(bytes=21981,sha256='f147def983e56f538dc3252d270ad335b83f5a381853c8a42deb281d2ead7244'),'fixed Source49 control required')
    sources=json.loads(raw)['source_pins'];require(pin(canonical(sources))['sha256']==SOURCE_SHA,'fixed Source49 epoch required')
    for name,expected in sources.items():require(pin((ROOT/name).read_bytes())==expected,'Source49 bytes differ: '+name)
    return sources

SOURCE_REFS={'core': ('experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py', 69895, '43f0b2c9add534a4a4fb74413c29fe4649d9a696475a73e80572a7eef15603cc'), 'probe': ('tests/staged_rts24_saved_fresh_runtime_handoff_probe_v42.py', 32006, '1a71ac951f95d02dbc987bc5db39a449be69fa2b5fc7dc2393dc5a6c8b308c4d'), 'quiet': ('experiments/staged_rts24_saved_fresh_parent_quiet_actor_v2.py', 22359, 'c6c647b5a9237a63ded591e24674755e3b141343594ae234360d23f22b82fa3b'), 'validation': ('experiments/staged_rts24_saved_fresh_complete_bootstrap_validation_v1.py', 73927, '762224af9656c5dfaa75fa4594bf9d14aea1c1bf37af637aabfb1ad79879f33a'), 'replay': ('experiments/staged_rts24_saved_fresh_producer_parent_reopen_v2.py', 6025, '76fd313beb7a4db8ce5f6ada89d6619ccd64c98ae7720c18c894786c261c24ed'), 'transport': ('experiments/staged_rts24_saved_fresh_utf16_transport_v1.py', 4984, '0d78987de9f64aa9700556f683f797d8f015f6c0b77953d1e84dd1d441f67666')}

def minify_prefix(prefix):
    before = prefix
    tokens = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    lines = prefix.decode('utf-8').splitlines(keepends=True)
    edits = []
    skip = {tokenize.ENCODING, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
    words = {tokenize.NAME, tokenize.NUMBER, tokenize.STRING}
    for left, right in zip(tokens, tokens[1:]):
        if left.type in skip or right.type in skip or left.end[0] != right.start[0]:
            continue
        row, a = left.end
        b = right.start[1]
        gap = lines[row - 1][a:b]
        if not gap or not gap.isspace():
            continue
        separate = left.type in words and right.type in words or (left.type == tokenize.NUMBER and right.string == '.')
        separate = separate or (left.type == right.type == tokenize.OP and (left.string + right.string in tokenize.EXACT_TOKEN_TYPES or left.string.endswith('.') or right.string.startswith('.')))
        edits.append((row - 1, a, b, ' ' if separate else ''))
    for row, a, b, value in reversed(edits):
        lines[row] = lines[row][:a] + value + lines[row][b:]
    prefix = ''.join(lines).encode('utf-8')
    assert [(t.type, t.string) for t in tokenize.tokenize(io.BytesIO(prefix).readline)] == [(t.type, t.string) for t in tokens]
    assert ast.dump(ast.parse(prefix)) == ast.dump(ast.parse(before)) and prefix.count(b'\n') == before.count(b'\n')

    def code_image(code):
        names = ('co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals', 'co_stacksize', 'co_flags', 'co_code', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars', 'co_filename', 'co_name', 'co_qualname', 'co_firstlineno', 'co_exceptiontable')
        return (tuple((getattr(code, n) for n in names)), tuple((code_image(v) if type(v) is type(code) else v for v in code.co_consts)), tuple(code.co_lines()))
    tokens_after = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    assert not any((t.type == tokenize.STRING and t.start[0] != t.end[0] for t in tokens_after))
    lines = prefix.decode('utf-8').splitlines(keepends=True)
    for index, line in enumerate(lines):
        text = line.lstrip(' ')
        if not text.strip() or text.startswith('#'):
            continue
        leading = len(line) - len(text)
        assert leading % 4 == 0 and (not text.startswith('\t'))
        lines[index] = ' ' * (leading // 4) + text
    prefix = ''.join(lines).encode('utf-8')
    after = list(tokenize.tokenize(io.BytesIO(prefix).readline))
    canonical = lambda ts: [(t.type, '' if t.type == tokenize.INDENT else t.string) for t in ts]
    assert canonical(after) == canonical(tokens)
    assert ast.dump(ast.parse(prefix)) == ast.dump(ast.parse(before)) and prefix.count(b'\n') == before.count(b'\n')
    assert code_image(compile(prefix, '<pre_entry_prefix>', 'exec', dont_inherit=True, optimize=0)) == code_image(compile(before, '<pre_entry_prefix>', 'exec', dont_inherit=True, optimize=0))
    return prefix


def transport():
    return source_module('transport').build(CORE,PROBE,minify_prefix)

def parent_view(held):
    view=dict(ROOT=ROOT,OUT=OUT,CORE=CORE,EXE=EXE,RUNTIME=RUNTIME,SOURCE_SHA=SOURCE_SHA,load=load,controller_pid=os.getpid())
    view['quiet_actor_type']=dict(get_program(held,'quiet')[0])['ParentQuietActor']
    view['quiet_actor_registry']=dict(get_program(held,'quiet')[0])['_ACTORS']
    view['quiet_finish']=lambda actor:call(get_program(held,'quiet'),'finish',actor)
    view['producer_data_replay']=lambda raw,quiet,sources:call(get_program(held,'replay'),'audit_producer_data',raw,quiet,sources)
    view['validate_memory_guard']=lambda value:call(get_program(held,'quiet'),'program_memory_guard',value)
    view['input_context']=lambda raw,code,argv,profile_dependency=None:input_context(raw,code,argv,
        held=held,profile_dependency=profile_dependency)
    return SimpleNamespace(**view)

def read_data(held,path,cap=1048576):
    path=Path(path);info=path.lstat()
    require(0<=info.st_size<=cap,'bounded fixed diagnostic data file required')
    raw=path.read_bytes()
    return call(get_program(held,'core'),'read_file',path,pin(raw))

def profile_dependency(held,kind):
    require(kind in ('startup','import'),'closed independent profile kind required')
    case='discovery' if kind=='startup' else 'import_discovery'
    names=dict(profile_raw=kind+'_profile.json',receipt_raw='probe_'+case+'.receipt.json',
        manifest_raw='probe_'+case+'.plan.json',admission_raw=kind+'_admission.json',registration_raw='registration.json')
    return {key:read_data(held,OUT/name) for key,name in names.items()}

def input_context(plan_raw,code,argv,held=None,profile_dependency=None):
    require(type(plan_raw) is type(code) is bytes and type(argv) is list,'held canonical parent input bytes required')
    if held is None:held=dependencies()
    plan=call(get_program(held,'core'),'check_plan',plan_raw)
    require(code==transport() and plan['bootstrap_pin']==pin(code),'same exact Core44/Probe42 transport required')
    path=OUT/('probe_'+plan['case']+'.plan.json')
    expected=[str(EXE),'-P','-B','-s','-S','-c',code.decode('utf8'),'--pre-entry-lease',str(path),pin(plan_raw)['sha256']]
    require(argv==expected and len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2<=30000,'same bounded complete child command required')
    require(plan['environment']==environment() and plan['source_pins']==source(),'same controlled environment and Source49 bytes required')
    require(read_data(held,path,131072)==plan_raw,'same pre-existing manifest file required')
    require(call(get_program(held,'core'),'read_file',EXE,plan['executable_pin']) is not None,'same selected executable required')
    for path,pinned in plan['selected_runtime_file_observations'].items():call(get_program(held,'core'),'read_file',path,pinned,links=True)
    require(all(not os.path.lexists(path) for path in plan['startup_absent']),'startup absent paths changed')
    for field in ('namespace_helper','import_helper','import_policy'):
        ref=plan[field];call(get_program(held,'core'),'read_file',ref['path'],ref['pin'])
    require(plan['producer_helpers']=={key:dict(path=path,pin=pin(Path(path).read_bytes()))
        for key,path in call(get_program(held,'core'),'producer_helper_paths').items()},'same complete helper closed set required')
    for ref in plan['producer_helpers'].values():call(get_program(held,'core'),'read_file',ref['path'],ref['pin'])
    refs={}
    if plan['case']!='discovery':
        startup=profile_dependency_for(held,'startup')
        call(get_program(held,'validation'),'startup_relation',parent_view(held),plan_raw,code,startup)
        require(call(get_program(held,'core'),'read_file',plan['startup_profile']['path'],plan['startup_profile']['pin'])==startup['profile_raw'],
            'same independently accepted startup bytes required')
        refs['startup']={key:pin(raw) for key,raw in startup.items()}
    if plan['case']=='producer':
        imported=profile_dependency if profile_dependency is not None else profile_dependency_for(held,'import')
        call(get_program(held,'validation'),'profile_relation',parent_view(held),plan_raw,code,imported)
        require(call(get_program(held,'core'),'read_file',plan['import_profile']['path'],plan['import_profile']['pin'])==imported['profile_raw'],
            'same independently accepted import profile bytes required')
        refs['import']={key:pin(raw) for key,raw in imported.items()}
    return dict(schema='staged_saved_F_complete_parent_input_context_v1',authority='DRAFT_NONAUTHORITATIVE',
        manifest_pin=pin(plan_raw),transport_pin=pin(code),argv_pin=pin(canonical(argv)),environment_pin=pin(canonical(plan['environment'])),
        source_pins_pin=pin(canonical(plan['source_pins'])),helper_pins_pin=pin(canonical(plan['producer_helpers'])),
        profile_dependencies=refs,**flags())

def profile_dependency_for(held,kind):return profile_dependency(held,kind)

class ParentActor:
    __slots__=('_creator','_program','_held','_process','_quiet','_plan','_code','_argv','_context','_profile','_phase',
        '_failure','_secondary','_raws','_quiet_snapshot','_result','_retirement_raw')
    def __new__(cls,*args,**kwargs):raise TypeError('capture the creating parent')
    def __setattr__(self,name,value):raise AttributeError('parent is frozen')
    def __delattr__(self,name):raise AttributeError('parent is frozen')
    def __reduce__(self):raise TypeError('creating parent cannot be serialized')

def parent_entry(actor):
    require(type(actor) is ParentActor and actor._creator==creator() and _PARENTS.get(id(actor)) is actor,
        'exact creating parent actor required')
    return actor

def error_image(error):
    remaining=[48]
    def visit(value,depth=0):
        if value is None:return None
        remaining[0]-=1
        if remaining[0]<0:return None
        try:message=str(value)[:180]
        except BaseException:message='<exception message unavailable>'
        if depth>=6:return dict(type=type(value).__name__[:80],message=message,primary=None,secondary=[],cause=None,group=[],truncated=True)
        secondary=[]
        attached=getattr(value,'secondary',getattr(value,'cleanup',()))
        attached=attached if type(attached) in (tuple,list) else (attached,)
        for item in attached[:8]:
            layer,child=item if type(item) is tuple and len(item)==2 else ('cleanup',item)
            secondary.append(dict(layer=str(layer)[:80],error=visit(child,depth+1)))
        groups=[visit(child,depth+1) for child in value.exceptions[:8]] if isinstance(value,BaseExceptionGroup) else []
        return dict(type=type(value).__name__[:80],message=message,primary=visit(getattr(value,'primary',None),depth+1),
            secondary=secondary,cause=visit(getattr(value,'__cause__',None),depth+1),group=groups,truncated=remaining[0]<=0)
    return visit(error)


def fallback(process):
    """Only used for a child already transferred into this creating parent."""
    errors=[]
    if process.poll() is None:
        try:process.kill();process.wait(timeout=1.)
        except BaseException as error:errors.append('kill_wait:'+type(error).__name__+':'+str(error)[:160])
    for name in ('stdin','stdout','stderr'):
        try:
            stream=getattr(process,name)
            if stream is not None and not stream.closed:stream.close()
        except BaseException as error:errors.append(name+':'+type(error).__name__+':'+str(error)[:160])
    try:
        if not process._handle.closed:process._handle.Close()
        require(process._handle.closed,'fallback process HANDLE unresolved')
    except BaseException as error:errors.append('process_handle:'+type(error).__name__+':'+str(error)[:160])
    return errors

def commit_terminal(actor,raw,phase):
    require(type(raw) is bytes and len(raw)<=1048576,'bounded preformed terminal bytes required')
    if phase=='RETIRED':
        require(_PARENTS.get(id(actor)) is actor,'exact parent registry row changed')
        for name,item in dict(_phase=phase,_result=raw,_process=None,_quiet=None,_held=None,_plan=None,_code=None,
                _argv=None,_context=None,_profile=None,_failure=None,_secondary=(),_raws=None,_quiet_snapshot=None,
                _retirement_raw=None,_program=None).items():object.__setattr__(actor,name,item)
        del _PARENTS[id(actor)]
    else:
        object.__setattr__(actor,'_phase','UNRESOLVED');object.__setattr__(actor,'_result',raw)

def failure_terminal(actor,primary,secondary,stage):
    # Preserve a canonical failure image before any irreversible registry retirement.
    errors=list(secondary);held=actor._held;q=actor._quiet;snapshot=None;retired=None;evidence=None;prior_pin=None
    object.__setattr__(actor,'_failure',primary)
    if q is not None and q._phase=='RETIRED':
        evidence=q._retired_evidence
        snapshot=json.loads(q._result)
        prior_pin=json.loads(evidence)['parent_result_pin']
        retired=call(get_program(held,'quiet'),'retired_observation',q,evidence)
    elif q is not None:
        try:
            errors.extend(call(get_program(held,'quiet'),'abort',q,primary))
            snapshot=call(get_program(held,'quiet'),'terminal_snapshot',q)
        except BaseException as error:
            errors.append(error)
            if actor._process is not None:
                try:errors.extend(fallback(actor._process))
                except BaseException as physical:errors.append(physical)
            if actor._quiet_snapshot is not None:snapshot=json.loads(actor._quiet_snapshot)
    else:errors.extend(fallback(actor._process))
    out,err=(b'',b'') if actor._raws is None else actor._raws
    if q is not None and actor._raws is None and q._raws is not None:out,err=q._raws
    core=dict(schema='staged_saved_F_complete_parent_failure_core_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
        stage=stage,primary=error_image(primary),secondary=[error_image(error) if isinstance(error,BaseException)
            else error_image(RuntimeError(error)) for error in errors],
        manifest_raw_base64=base64.b64encode(actor._plan).decode('ascii'),transport_pin=pin(actor._code),argv_pin=pin(actor._argv),
        stdout_raw_base64=base64.b64encode(out).decode('ascii'),stderr_raw_base64=base64.b64encode(err).decode('ascii'),
        stdout_pin=pin(out),stderr_pin=pin(err),quiet_snapshot=snapshot,prior_retirement_parent_result_pin=prior_pin,**flags())
    core_raw=canonical(core)
    require(len(core_raw)+65536<=1048576,'bounded failure core and retirement reserve required')
    expected=retired
    if snapshot is not None and retired is None:evidence,expected=retirement_candidate(actor,core_raw,snapshot)
    value=dict(schema='staged_saved_F_complete_parent_failure_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
        failure=core,failure_pin=pin(core_raw),retirement=expected,
        retirement_evidence_base64=None if evidence is None else base64.b64encode(evidence).decode('ascii'),
        retirement_errors=[],terminal_parent_phase='RETIRED' if expected is not None or q is None and not errors else 'UNRESOLVED',**flags())
    raw=canonical(value);require(len(raw)<=1048576,'bounded canonical parent failure required')
    if expected is not None and retired is None:
        object.__setattr__(actor,'_retirement_raw',evidence)
        try:
            retired=call(get_program(held,'quiet'),'retire',q,evidence)
            require(canonical(retired)==canonical(expected),'same failed terminal retirement required')
        except BaseException as error:
            value['retirement_errors'].append(error_image(error))
            try:retired=call(get_program(held,'quiet'),'retired_observation',q,evidence)
            except BaseException as observed:value['retirement_errors'].append(error_image(observed));retired=None
            value['retirement']=retired
            value['terminal_parent_phase']='RETIRED' if retired is not None else 'UNRESOLVED'
    if _PARENTS.get(id(actor)) is not actor:
        value['terminal_parent_phase']='UNRESOLVED'
        value['retirement_errors'].append(error_image(ValueError('exact parent registry row changed')))
    raw=canonical(value);require(len(raw)<=1048576,'bounded final canonical parent failure required')
    commit_terminal(actor,raw,value['terminal_parent_phase'])
    return json.loads(raw)

def primitive_failure(actor,primary,secondary,stage,_dump_code=json.dumps.__code__,_dump_defaults=json.dumps.__defaults__,
        _dump_kw=tuple(json.dumps.__kwdefaults__.items()),_dump_bindings=tuple(json.dumps.__globals__.items()),
        _b64=base64.b64encode,_put=object.__setattr__,_image=error_image.__code__,_factory=FunctionType,_native=tuple(vars(builtins).items())):
    context={'__builtins__':dict(_native)}
    image=_factory(_image,context,'held_emergency_exception_image')
    rows=[image(error) if isinstance(error,BaseException) else image(RuntimeError(str(error))) for error in secondary[:8]]
    value=dict(schema='staged_saved_F_parent_emergency_failure_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
        stage=stage,terminal_parent_phase='UNRESOLVED',primary=image(primary),secondary=rows,
        manifest_raw_base64=_b64(actor._plan).decode('ascii'),transport_pin=pin(actor._code),argv_pin=pin(actor._argv),
        parent_independent_P1_verified=False,external_permission_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)
    dumps=_factory(_dump_code,dict(_dump_bindings),'held_emergency_json',_dump_defaults);dumps.__kwdefaults__=dict(_dump_kw)
    raw=dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(raw)>1048576:raise RuntimeError('emergency parent record cap')
    for name,item in dict(_phase='UNRESOLVED',_result=raw,_failure=primary,_secondary=tuple(secondary)).items():_put(actor,name,item)
    return value

def capture(process,plan_raw,code,argv):
    """Adopt an existing direct child from a separately authorized outer."""
    require(type(process) is subprocess.Popen and process.args==argv and process.returncode is None
        and type(process.pid) is int and process.pid>0,'exact live transferred Popen required')
    require(type(plan_raw) is type(code) is bytes and len(plan_raw)<=131072 and len(code)<=131072
        and type(argv) is list and len(argv)==10 and all(type(v) is str for v in argv),'original bounded parent input bytes required')
    actor=object.__new__(ParentActor)
    values=dict(_creator=creator(),_program=program(globals()),_held=None,_process=process,_quiet=None,
        _plan=plan_raw,_code=code,_argv=canonical(argv),_context=None,_profile=None,_phase='CAPTURING',
        _failure=None,_secondary=(),_raws=None,_quiet_snapshot=None,
        _result=canonical(dict(schema='staged_saved_F_parent_publication_pending_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=False,
            manifest_pin=pin(plan_raw),transport_pin=pin(code),argv_pin=pin(canonical(argv)),**flags())),_retirement_raw=None)
    for name,value in values.items():object.__setattr__(actor,name,value)
    _PARENTS[id(actor)]=actor
    try:
        held=dependencies();object.__setattr__(actor,'_held',held)
        context=input_context(plan_raw,code,argv,held=held)
        plan=call(get_program(held,'validation'),'unique_json',plan_raw)
        imported=profile_dependency_for(held,'import') if plan['case']=='producer' else None
        identity=call(get_program(held,'quiet'),'kernel_identity',process)
        q=call(get_program(held,'quiet'),'capture',process,identity,argv,pin(plan_raw),pin(code),DRAIN.read_bytes())
        for name,value in dict(_quiet=q,_context=canonical(context),_profile=None if imported is None else tuple(sorted(imported.items())),_phase='CAPTURED').items():
            object.__setattr__(actor,name,value)
        return actor
    except BaseException as primary:
        object.__setattr__(actor,'_failure',primary)
        try:failure_terminal(actor,primary,(),stage='CAPTURE')
        except BaseException as publication:primitive_failure(actor,primary,(publication,),stage='CAPTURE')
        error=RuntimeError('complete parent capture failed');error.owner=actor;error.primary=primary;error.secondary=()
        raise error from primary

def retirement_candidate(actor,row_raw,snapshot):
    evidence=canonical(dict(schema='staged_saved_F_parent_retirement_record_v1',authority='DRAFT_NONAUTHORITATIVE',
        quiet_snapshot_pin=pin(canonical(snapshot)),parent_result_pin=pin(row_raw),
        accepted=json.loads(row_raw)['accepted'],**flags()))
    require(len(evidence)<=1048576,'bounded held parent retirement evidence required')
    expected=dict(schema='staged_saved_F_parent_actor_retirement_v1',authority='DRAFT_NONAUTHORITATIVE',
        exact_registry_row_retired=True,terminal_snapshot_pin=pin(canonical(snapshot)),evidence_pin=pin(evidence),**flags())
    return evidence,expected


def run_owned(actor,seconds):
    parent_entry(actor)
    require(actor._phase=='CAPTURED' and type(seconds) in (int,float) and math.isfinite(seconds) and 0<seconds<=180.,
        'single bounded source-held parent execution required')
    object.__setattr__(actor,'_phase','DRAINING')
    held=actor._held;q=actor._quiet;quiet=None;result=None;primary=None;secondary=[];out=err=b'';after=None
    try:
        require(canonical(input_context(actor._plan,actor._code,json.loads(actor._argv),held=held,
            profile_dependency=None if actor._profile is None else dict(actor._profile)))==actor._context,'parent input changed before release')
        call(get_program(held,'quiet'),'release',q)
        rc,out,err,reason,_=call(get_program(held,'quiet'),'drain_child',q,seconds)
        object.__setattr__(actor,'_raws',(out,err))
        call(get_program(held,'quiet'),'close_handle',q)
        quiet=call(get_program(held,'quiet'),'finish',q);object.__setattr__(actor,'_quiet_snapshot',canonical(quiet))
        # Parent obtains all candidate facts from this exact actor and its drain.
        result=call(get_program(held,'validation'),'replay_retained',parent_view(held),q,actor._plan,actor._code,json.loads(actor._argv),out,err,
            profile_dependency=None if actor._profile is None else dict(actor._profile))
        require(result['accepted'] is True,'exact_complete_graph_contract_unresolved')
        after=canonical(input_context(actor._plan,actor._code,json.loads(actor._argv),held=held,
            profile_dependency=None if actor._profile is None else dict(actor._profile)))
        require(after==actor._context,'parent input changed after quiet replay')
    except BaseException as error:
        primary=error
        try:secondary.extend(call(get_program(held,'quiet'),'abort',q,primary))
        except BaseException as error:secondary.append('actor_abort:'+type(error).__name__+':'+str(error)[:160])
        try:quiet=call(get_program(held,'quiet'),'terminal_snapshot',q);object.__setattr__(actor,'_quiet_snapshot',canonical(quiet))
        except BaseException as error:secondary.append('terminal_snapshot:'+type(error).__name__+':'+str(error)[:160])
        if actor._raws is None:
            # Failure drains are retained privately by the exact source actor.
            if q._raws is not None:out,err=q._raws;object.__setattr__(actor,'_raws',(out,err))
    object.__setattr__(actor,'_failure',primary);object.__setattr__(actor,'_secondary',tuple(secondary))
    row=dict(schema='staged_saved_F_complete_parent_receipt_v1',authority='DRAFT_NONAUTHORITATIVE',
        case=json.loads(actor._plan)['case'],accepted=primary is None and not secondary,
        manifest_raw_base64=base64.b64encode(actor._plan).decode('ascii'),argv=json.loads(actor._argv),
        stdout_raw_base64=base64.b64encode(out).decode('ascii'),stderr_raw_base64=base64.b64encode(err).decode('ascii'),
        quiet_receipt=quiet,result=result,primary=error_image(primary),secondary=list(secondary),
        context_before=None if actor._context is None else json.loads(actor._context),
        context_after=None if after is None else json.loads(after),parent_controller_pid=os.getpid(),**flags())
    row_raw=canonical(row);require(len(row_raw)<=1048576,'bounded complete parent receipt required')
    object.__setattr__(actor,'_failure',primary);object.__setattr__(actor,'_secondary',tuple(secondary))
    evidence=None;expected=None
    if quiet is not None:evidence,expected=retirement_candidate(actor,row_raw,quiet)
    candidate=dict(schema='staged_saved_F_complete_parent_terminal_v1',authority='DRAFT_NONAUTHORITATIVE',
        accepted=row['accepted'] and expected is not None,receipt=row,receipt_pin=pin(row_raw),retirement=expected,
        retirement_evidence_base64=None if evidence is None else base64.b64encode(evidence).decode('ascii'),
        terminal_parent_phase='RETIRED' if expected is not None else 'UNRESOLVED',**flags())
    candidate_raw=canonical(candidate)
    require(len(candidate_raw)+1024<=1048576,'bounded complete parent terminal and failure reserve required')
    require(_PARENTS.get(id(actor)) is actor,'exact parent registry row changed before retirement')
    require(expected is not None,'retained terminal snapshot unresolved')
    object.__setattr__(actor,'_retirement_raw',evidence)
    retired=call(get_program(held,'quiet'),'retire',q,evidence)
    require(canonical(retired)==canonical(expected),'held exact retirement result differs')
    require(_PARENTS.get(id(actor)) is actor,'exact parent registry row changed after retirement')
    commit_terminal(actor,candidate_raw,'RETIRED')
    return json.loads(candidate_raw)


def recovery_context(held,_factory=FunctionType,_module_type=ModuleType):
    # Recovery reconstructs source CodeTypes even after an entry witness rejects drift.
    context=dict(held[0])
    for module,items,functions in held[2][8]:
        copied=_module_type(module.__name__);vars(copied).update(items)
        for name,original,code,defaults,kw,kw_image,closure,owns_globals in functions:
            if owns_globals:
                clone=_factory(code,vars(copied),name,defaults,closure)
                clone.__kwdefaults__=None if kw is None else dict(kw);vars(copied)[name]=clone
        for name,value in tuple(context.items()):
            if value is module:context[name]=copied
    for name,code,defaults,kw in held[1]:
        function=_factory(code,context,name,defaults);function.__kwdefaults__=None if kw is None else dict(kw);context[name]=function
    return context

def dispatch(actor,operation,args=(),_class=ParentActor,_pid=os.getpid,_tid=get_ident,_typ=type,_error=ValueError,
        _factory=FunctionType,_call_code=call.__code__,_call_defaults=call.__defaults__,_call_kw=tuple(call.__kwdefaults__.items()),
        _recover_code=recovery_context.__code__,_recover_defaults=recovery_context.__defaults__,_loads=json.loads,_native=tuple(vars(builtins).items())):
    if _typ(actor) is not _class or actor._creator!=(_pid(),_tid()):raise _error('exact creating parent required')
    if operation=='observation':
        if args!=() or actor._result is None:raise _error('held final parent bytes required')
        return _loads(actor._result)
    if operation!='run' or _typ(args) is not tuple or len(args)!=1 or actor._program is None:
        raise _error('closed parent run operation required')
    held=actor._program
    isolated={'__builtins__':dict(_native)}
    original_call=_factory(_call_code,isolated,'held_parent_call',_call_defaults);original_call.__kwdefaults__=dict(_call_kw)
    try:return original_call(held,'run_owned',actor,args[0])
    except BaseException as late:
        primary=actor._failure if actor._failure is not None else late
        secondary=actor._secondary+(() if primary is late else (late,))
        context=_factory(_recover_code,isolated,'held_parent_recovery',_recover_defaults)(held)
        try:return context['failure_terminal'](actor,primary,secondary,stage='PARENT_TERMINAL')
        except BaseException as publication:
            return context['primitive_failure'](actor,primary,secondary+(publication,),stage='PARENT_TERMINAL')


def one_case(process,plan_raw,code,argv,seconds):
    actor=capture(process,plan_raw,code,argv)
    return dispatch(actor,'run',(seconds,))

def current():
    for name,row in SOURCE_REFS.items():
        path=ROOT/row[0];raw=path.read_bytes()
        require(pin(raw)==dict(bytes=row[1],sha256=row[2]),'fixed complete parent source differs: '+name)
        compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
    return None,dict(schema='staged_saved_F_complete_parent_contract_v1',authority='DRAFT_NONAUTHORITATIVE',
        mode='post_spawn_source_held_owner',source_refs={key:dict(path=row[0],bytes=row[1],sha256=row[2]) for key,row in SOURCE_REFS.items()},
        launcher_present=False,parent_P1_reader_present=False,exact_actor_retirement=True,
        profile_admission_requires_saved_parent_replay=True,exact_complete_graph_contract=None,
        external_permission_verified=False,parent_independent_P1_verified=False,resource_admission=False,
        formal_result=False,run_authority=False,actual_F=False)


def source_dispatch(raw,expected_pin):
    """The approved outer must independently bind both bytes and expected pin.

    This factory is not a launcher, grant issuer, or self-authentication root.
    Public module convenience methods are not the trusted execution entry.
    """
    require(type(raw) is bytes and len(raw)<=131072 and pin(raw)==expected_pin,
        'outer-bound exact Parent40 source bytes required')
    namespace=dict(__file__=__file__,__name__='_source_held_complete_parent',__builtins__=dict(vars(builtins)),_SOURCE_RAW=raw)
    exec(compile(raw,__file__,'exec',dont_inherit=True,optimize=0),namespace,namespace)
    held=namespace['program'](namespace)
    return namespace['held_parent_dispatch'].__code__,dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType),(held,)


def held_parent_dispatch(state,operation,args):
    held,=state
    context=dict(held[0])
    for name,code,defaults,kw in held[1]:
        function=FunctionType(code,context,name,defaults);function.__kwdefaults__=None if kw is None else dict(kw);context[name]=function
    if operation=='capture':
        if type(args) is not tuple or len(args)!=4:raise ValueError('four original parent capture arguments required')
        return context['call'](held,'capture',*args)
    if operation=='run':
        if type(args) is not tuple or len(args)!=2:raise ValueError('exact parent and bounded run required')
        return context['dispatch'](args[0],'run',(args[1],))
    if operation=='observation':
        if type(args) is not tuple or len(args)!=1:raise ValueError('exact parent observation required')
        return context['dispatch'](args[0],'observation',())
    raise ValueError('closed source-held parent operation required')
