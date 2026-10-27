"""Mechanical NFC4 successor relocation and the separately allocated budget fixture."""
import ast


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before))
        source=source.replace(before,after,count)
    return source.encode('utf-8')


def core(source):return replace(source,[('nfc_v4_non_authoritative','nfc_v5_non_authoritative',2)])

def probe(source):return replace(source,[('nfc_v4_non_authoritative','nfc_v5_non_authoritative',1)])

def parent(source):
    return replace(source,[('nfc_v4_non_authoritative','nfc_v5_non_authoritative',1),('lease_v31.py','lease_v32.py',1),('probe_v29.py','probe_v30.py',1)])

def fixture(source):
    return replace(source,[('lease_v31.py','lease_v32.py',1),('probe_v29.py','probe_v30.py',1)])


def tests(source):
    tree=ast.parse(source)
    pairs=(('lease_v31.py','lease_v32.py'),('parent_v28.py','parent_v29.py'),('probe_v29.py','probe_v30.py'),
        ('image_entry_fixture_v3.py','image_entry_fixture_v4.py'),('nfc_v4_non_authoritative/driver.py','nfc_v5_non_authoritative/driver.py'))
    class Paths(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is str:
                for before,after in pairs:node.value=node.value.replace(before,after)
            return node
    Paths().visit(tree)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='None1024Tests')
    test=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_01_exact_source_constructor_and_original_audit_statements')
    test.body.insert(0,ast.parse("successor=load(ROOT/'experiments/staged_rts24_saved_fresh_census1024_controller_relocate_v2.py','_controller_successor')").body[0])
    changed=[]
    for node in ast.walk(test):
        if type(node) is not ast.Call or type(node.func) is not ast.Attribute or node.func.attr!='assertEqual':continue
        first=node.args[0]
        if type(first) is ast.Call and type(first.func) is ast.Attribute and type(first.func.value) is ast.Name and first.func.value.id=='controller' and first.func.attr in ('probe','parent'):
            name=first.func.attr;changed.append(name)
            text=ast.Call(func=ast.Attribute(value=first,attr='decode',ctx=ast.Load()),args=[ast.Constant(value='utf-8')],keywords=[])
            node.args[0]=ast.Call(func=ast.Attribute(value=ast.Name(id='successor',ctx=ast.Load()),attr=name,ctx=ast.Load()),args=[text],keywords=[])
    assert sorted(changed)==['parent','probe']
    completion=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_07_both_modes_record_authority_and_parent_completion')
    changed=0
    for node in ast.walk(completion):
        if type(node) is not ast.Call or type(node.func) is not ast.Name or node.func.id!='dict':continue
        keywords={k.arg:k for k in node.keywords}
        if set(keywords)=={'static','unittest','total','files','bytes'}:
            assert {k:v.value.value for k,v in keywords.items()}==dict(static=22,unittest=8,total=30,files=16,bytes=4194304)
            for name,value in dict(static=36,unittest=10,total=46).items():keywords[name].value=ast.Constant(value=value)
            changed+=1
    assert changed==1
    target=ast.parse("changed['caps']['total']=0").body[0].targets[0]
    assignments=[n for n in ast.walk(completion) if type(n) is ast.Assign and len(n.targets)==1 and ast.dump(n.targets[0])==ast.dump(target)]
    assert len(assignments)==1 and assignments[0].value.value==31
    assignments[0].value=ast.Constant(value=47)
    return (ast.unparse(ast.fix_missing_locations(tree))+'\n').encode('utf-8')
