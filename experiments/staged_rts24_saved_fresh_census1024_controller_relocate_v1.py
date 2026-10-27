"""Fixed controller-output relocation; the held image helper remains unchanged."""
import ast


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before))
        source=source.replace(before,after,count)
    return source.encode('utf-8')


def core(source):return replace(source,[('nfc_v3_non_authoritative','nfc_v4_non_authoritative',2)])
def probe(source):return replace(source,[('nfc_v3_non_authoritative','nfc_v4_non_authoritative',1)])
def parent(source):
    return replace(source,[('nfc_v3_non_authoritative','nfc_v4_non_authoritative',1),('lease_v30.py','lease_v31.py',1),('probe_v28.py','probe_v29.py',1)])
def fixture(source):
    return replace(source,[('lease_v29.py','lease_v31.py',1),('probe_v27.py','probe_v29.py',1)])


def tests(source):
    tree=ast.parse(source)
    pairs=(('lease_v30.py','lease_v31.py'),('parent_v27.py','parent_v28.py'),('probe_v28.py','probe_v29.py'),
        ('image_entry_fixture_v2.py','image_entry_fixture_v3.py'),('nfc_v3_non_authoritative/driver.py','nfc_v4_non_authoritative/driver.py'))
    class Paths(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is str:
                for before,after in pairs:node.value=node.value.replace(before,after)
            return node
    Paths().visit(tree)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='None1024Tests')
    test=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_01_exact_source_constructor_and_original_audit_statements')
    assignment=ast.parse("controller=load(ROOT/'experiments/staged_rts24_saved_fresh_census1024_controller_relocate_v1.py','_controller_relocate')").body[0]
    test.body.insert(0,assignment)
    changed=[]
    for node in ast.walk(test):
        if type(node) is not ast.Call or type(node.func) is not ast.Attribute or node.func.attr!='assertEqual':continue
        first=node.args[0]
        if type(first) is ast.Call and type(first.func) is ast.Attribute and type(first.func.value) is ast.Name and first.func.value.id=='relocate' and first.func.attr in ('probe','parent'):
            name=first.func.attr;changed.append(name)
            text=ast.Call(func=ast.Attribute(value=first,attr='decode',ctx=ast.Load()),args=[ast.Constant(value='utf-8')],keywords=[])
            node.args[0]=ast.Call(func=ast.Attribute(value=ast.Name(id='controller',ctx=ast.Load()),attr=name,ctx=ast.Load()),args=[text],keywords=[])
    assert sorted(changed)==['parent','probe']
    completion=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_07_both_modes_record_authority_and_parent_completion')
    completion.body.extend(ast.parse('''
expected=dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',
    input_pins={'input':dict(bytes=1,sha256='0'*64)},helper_pins={'helper':dict(bytes=1,sha256='1'*64)},
    embedded_artifacts={'helper:helper':{'encoding':'raw','raw_base64':'eA==','pin':dict(bytes=1,sha256='2'*64)}},
    caps=dict(static=22,unittest=8,total=30,files=16,bytes=4194304),unit_nodes=reg['unit_nodes'],unit_tests_planned=14)
self.assertIsNone(driver.match_registration(expected,expected))
for kind in ('input','helper','embedded','budget','nodes','count','authority','bool','extra'):
    changed=json.loads(driver.canonical(expected))
    if kind=='input':changed['input_pins'].clear()
    elif kind=='helper':changed['helper_pins'].clear()
    elif kind=='embedded':changed['embedded_artifacts'].clear()
    elif kind=='budget':changed['caps']['total']=31
    elif kind=='nodes':changed['unit_nodes']=changed['unit_nodes'][:-1]
    elif kind=='count':changed['unit_tests_planned']=13
    elif kind=='authority':changed['authority']='SEALED_READY_FOR_INDEPENDENT_REVIEW'
    elif kind=='bool':changed['accepted']=1
    else:changed['extra']=False
    with self.assertRaises(AssertionError):driver.match_registration(changed,expected)
''').body)
    return (ast.unparse(ast.fix_missing_locations(tree))+'\n').encode('utf-8')
