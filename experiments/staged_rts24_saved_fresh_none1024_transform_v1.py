"""Pure fixed constructors for held-image audit integration and a finite window."""
import ast

SCHEDULE=(1,128,256,384,512,640,768,896)
CENSUS=('_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once')


class Finite(ast.NodeTransformer):
    def visit_Constant(self,node):
        if type(node.value) is int and node.value==512:node.value=1024
        elif type(node.value) is str:node.value=node.value.replace('before512','before1024').replace('complete_512','complete_1024').replace('audit_census_v3','audit_census_v4')
        return node
    def visit_Tuple(self,node):
        if all(type(n) is ast.Constant for n in node.elts) and tuple(n.value for n in node.elts)==(1,64,128,192,256,320,384,448):
            node.elts=[ast.Constant(n) for n in SCHEDULE];return node
        return self.generic_visit(node)


def helper(source):
    tree=ast.parse(source);cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    for i,n in enumerate(tree.body):
        if type(n) is ast.FunctionDef and n.name in CENSUS:tree.body[i]=Finite().visit(n)
    for node in cls.body:
        if type(node) is not ast.FunctionDef:continue
        if node.name=='_audit_entry':
            node.args.args.append(ast.arg(arg='_image_fn'));node.args.defaults.append(ast.Name(id='_image',ctx=ast.Load()))
        elif node.name=='_audit':
            for arg,expr in (('_image_fn','_image'),('_image_code','_image.__code__'),('_image_defs','_image.__defaults__'),('_image_id','id')):
                node.args.args.append(ast.arg(arg=arg));node.args.defaults.append(ast.parse(expr,mode='eval').body)
            outer=next(n for n in node.body if type(n) is ast.Try)
            lock=next(n for n in outer.body if type(n) is ast.With)
            index=next(i for i,n in enumerate(lock.body) if type(n) is ast.Expr and type(n.value) is ast.Call and any(type(v) is ast.Constant and v.value=='_busy' for v in n.value.args))
            check=ast.parse("""if not (_type(self) is __class__ and __class__._image is _image_fn and _image_fn.__code__ is _image_code and _image_fn.__defaults__ is _image_defs and _image_fn.__kwdefaults__ is None and _image_fn.__closure__ is None and _image_defs == (_image_id,) and id is _image_id):
    self._fault('image_metadata')
""").body[0]
            lock.body.insert(index,check)
        else:continue
        class Held(ast.NodeTransformer):
            def visit_Call(self,n):
                if type(n.func) is ast.Attribute and type(n.func.value) is ast.Name and n.func.value.id=='self' and n.func.attr=='_image':
                    assert not n.args and not n.keywords;n.func=ast.Name(id='_image_fn',ctx=ast.Load());n.args=[ast.Name(id='self',ctx=ast.Load())]
                return self.generic_visit(n)
        Held().visit(node)
    return (ast.unparse(tree)+'\n').encode()


def probe(source):
    before="if code.co_name=='_audit_entry':expected+=tuple(namespace[n] for n in ('_census_clock','_census_cut','_census_entry_end','_CENSUS'))"
    assert source.count(before)==1
    source=source.replace(before,before+"+(cls._image,)",1)
    before="elif code.co_name=='_audit':expected=(type,len,str,any,BaseException,namespace['_census_open_begin'],namespace['_census_open_end'],native['BaseExceptionGroup'])"
    assert source.count(before)==1
    source=source.replace(before,before+"+(cls._image,cls._image.__code__,cls._image.__defaults__,native['id'])",1)
    assert source.count('pfc_v1_non_authoritative')==1
    return source.replace('pfc_v1_non_authoritative','nfc_v1_non_authoritative',1).encode()


def parent(source):
    for before,after,count in (('pfc_v1_non_authoritative','nfc_v1_non_authoritative',1),('lease_v27.py','lease_v28.py',1),('probe_v24.py','probe_v26.py',1),('bootstrap_import_census512_parts_v1.py','bootstrap_import_census1024_none_v1.py',2)):
        assert source.count(before)==count,(before,source.count(before));source=source.replace(before,after,count)
    tree=ast.parse(source)
    names=('validate_census_frame','parse_diagnostic_stderr','validate_prefix_record','validate_prefix_stderr','validate_prefix_observation','compare_child')
    edits=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name in names:
            start,end=node.lineno,node.end_lineno;node=Finite().visit(node);edits.append((start,end,ast.unparse(node)+'\n'))
    lines=source.splitlines(keepends=True)
    for start,end,text in reversed(edits):lines[start-1:end]=[text]
    return ''.join(lines).encode()
