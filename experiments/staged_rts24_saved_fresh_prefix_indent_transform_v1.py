"""Fixed packing and nested held-commit constructors; no IO or project imports."""
import ast
import copy


def code_image(code):
    names=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags','co_code',
        'co_names','co_varnames','co_freevars','co_cellvars','co_filename','co_name','co_qualname','co_firstlineno','co_exceptiontable')
    return (tuple(getattr(code,n) for n in names),tuple(code_image(v) if type(v) is type(code) else v for v in code.co_consts),tuple(code.co_lines()))


COMPACT='''tokens_after=list(tokenize.tokenize(io.BytesIO(prefix).readline))
assert not any(t.type==tokenize.STRING and t.start[0]!=t.end[0] for t in tokens_after)
lines=prefix.decode('utf-8').splitlines(keepends=True)
for index,line in enumerate(lines):
    text=line.lstrip(' ')
    if not text.strip() or text.startswith('#'):continue
    leading=len(line)-len(text)
    assert leading%4==0 and not text.startswith('\\t')
    lines[index]=' '*(leading//4)+text
prefix=''.join(lines).encode('utf-8')
after=list(tokenize.tokenize(io.BytesIO(prefix).readline))
canonical=lambda ts:[(t.type,'' if t.type==tokenize.INDENT else t.string) for t in ts]
assert canonical(after)==canonical(tokens)
assert ast.dump(ast.parse(prefix))==ast.dump(ast.parse(before)) and prefix.count(b'\\n')==before.count(b'\\n')
assert code_image(compile(prefix,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0))==code_image(compile(before,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0))
'''


def parent(source):
    for before,after in (('nfc_v1_non_authoritative','nfc_v2_non_authoritative'),('lease_v28.py','lease_v29.py'),('probe_v26.py','probe_v27.py')):
        assert source.count(before)==1,(before,source.count(before));source=source.replace(before,after,1)
    before='bootstrap_import_census1024_none_v1.py'
    assert source.count(before)==2;source=source.replace(before,'bootstrap_import_census1024_none_v2.py',2)
    tree=ast.parse(source);node=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='minify_prefix')
    assert type(node.body[-1]) is ast.Return
    image=copy.deepcopy(ast.parse(__source_image__).body[0])
    node.body[-1:-1]=[image,*ast.parse(COMPACT).body]
    lines=source.splitlines(keepends=True)
    return (''.join(lines[:node.lineno-1])+ast.unparse(node)+'\n'+''.join(lines[node.end_lineno:])).encode()


def helper(source):
    tree=ast.parse(source);cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    for method,target,held in (('_observe_machinery','_image','_image_fn'),('_audit_entry','_observe_machinery','_observe_fn'),('_audit','_audit_entry','_entry_fn')):
        node=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name==method)
        node.args.args.append(ast.arg(arg=held));node.args.defaults.append(ast.Name(id=target,ctx=ast.Load()))
        calls=[n for n in ast.walk(node) if type(n) is ast.Call and type(n.func) is ast.Attribute and type(n.func.value) is ast.Name and n.func.value.id=='self' and n.func.attr==target]
        assert len(calls)==(2 if method=='_observe_machinery' else 1)
        for call in calls:
            assert not call.args and not call.keywords
            call.func=ast.Name(id=held,ctx=ast.Load());call.args=[ast.Name(id='self',ctx=ast.Load())]
    return (ast.unparse(tree)+'\n').encode()


def probe(source):
    assert source.count('nfc_v1_non_authoritative')==1
    source=source.replace('nfc_v1_non_authoritative','nfc_v2_non_authoritative',1)
    for before,after in (("+(cls._image,)","+(cls._image,cls._observe_machinery)"),("cls._image.__defaults__,native['id'])","cls._image.__defaults__,native['id'],cls._audit_entry)")):
        assert source.count(before)==1;source=source.replace(before,after,1)
    before="        elif code.co_name=='_image':expected="
    assert source.count(before)==1
    return source.replace(before,"        elif code.co_name=='_observe_machinery':expected=(cls._image,)\n"+before,1).encode()


__source_image__='''def code_image(code):
    names=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags','co_code','co_names','co_varnames','co_freevars','co_cellvars','co_filename','co_name','co_qualname','co_firstlineno','co_exceptiontable')
    return (tuple(getattr(code,n) for n in names),tuple(code_image(v) if type(v) is type(code) else v for v in code.co_consts),tuple(code.co_lines()))
'''
