"""Mechanical NFC5 successor relocation and the separately allocated budget fixture."""
import ast


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before))
        source=source.replace(before,after,count)
    return source.encode('utf-8')


def core(source):return replace(source,[('nfc_v5_non_authoritative','nfc_v6_non_authoritative',2)])

def probe(source):return replace(source,[('nfc_v5_non_authoritative','nfc_v6_non_authoritative',1)])

def parent(source):
    return replace(source,[('nfc_v5_non_authoritative','nfc_v6_non_authoritative',1),('lease_v32.py','lease_v33.py',1),('probe_v30.py','probe_v31.py',1)])

def fixture(source):
    return replace(source,[('lease_v32.py','lease_v33.py',1),('probe_v30.py','probe_v31.py',1)])


def tests(source):
    tree=ast.parse(source)
    pairs=(('lease_v32.py','lease_v33.py'),('parent_v29.py','parent_v30.py'),('probe_v30.py','probe_v31.py'),
        ('image_entry_fixture_v4.py','image_entry_fixture_v5.py'),('nfc_v5_non_authoritative/driver.py','nfc_v6_non_authoritative/driver.py'))
    class Paths(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is str:
                for before,after in pairs:node.value=node.value.replace(before,after)
            return node
    Paths().visit(tree)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='None1024Tests')
    test=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_01_exact_source_constructor_and_original_audit_statements')
    test.body.insert(0,ast.parse("continuation=load(ROOT/'experiments/staged_rts24_saved_fresh_census1024_controller_relocate_v3.py','_controller_successor')").body[0])
    changed=[]
    for node in ast.walk(test):
        if type(node) is not ast.Call or type(node.func) is not ast.Attribute or node.func.attr!='assertEqual':continue
        first=node.args[0]
        if type(first) is ast.Call and type(first.func) is ast.Attribute and type(first.func.value) is ast.Name and first.func.value.id=='successor' and first.func.attr in ('probe','parent'):
            name=first.func.attr;changed.append(name)
            text=ast.Call(func=ast.Attribute(value=first,attr='decode',ctx=ast.Load()),args=[ast.Constant(value='utf-8')],keywords=[])
            node.args[0]=ast.Call(func=ast.Attribute(value=ast.Name(id='continuation',ctx=ast.Load()),attr=name,ctx=ast.Load()),args=[text],keywords=[])
    assert sorted(changed)==['parent','probe']
    completion=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_07_both_modes_record_authority_and_parent_completion')
    changed=0
    for node in ast.walk(completion):
        if type(node) is not ast.Call or type(node.func) is not ast.Name or node.func.id!='dict':continue
        keywords={k.arg:k for k in node.keywords}
        if set(keywords)=={'static','unittest','total','files','bytes'}:
            assert {k:v.value.value for k,v in keywords.items()}==dict(static=36,unittest=10,total=46,files=16,bytes=4194304)
            for name,value in dict(static=39,unittest=10,total=49).items():keywords[name].value=ast.Constant(value=value)
            changed+=1
    assert changed==1
    target=ast.parse("changed['caps']['total']=0").body[0].targets[0]
    assignments=[n for n in ast.walk(completion) if type(n) is ast.Assign and len(n.targets)==1 and ast.dump(n.targets[0])==ast.dump(target)]
    assert len(assignments)==1 and assignments[0].value.value==47
    assignments[0].value=ast.Constant(value=50)
    completion.body.extend(ast.parse('''
timed=dict(accepted=True,authority=driver.AUTHORITY,kind='static',cap_seconds=6,charged_seconds=1.0,
    command_utf16_units=29706,phase_timings=[dict(stage=name,seconds=0.01) for name in driver.SIZE_STAGES])
self.assertIsNone(driver.validate_size_timings(timed))
for kind in ('missing','order','extra','nan','inf','bool','oversum','negative','int','row_keys','stage_type','charge_bool','charge_cap','accepted_type','units_type'):
    changed=copy.deepcopy(timed);rows=changed['phase_timings']
    if kind=='missing':rows.pop()
    elif kind=='order':rows[0],rows[1]=rows[1],rows[0]
    elif kind=='extra':rows.append(dict(rows[-1]))
    elif kind=='nan':rows[0]['seconds']=float('nan')
    elif kind=='inf':rows[0]['seconds']=float('inf')
    elif kind=='bool':rows[0]['seconds']=True
    elif kind=='oversum':rows[0]['seconds']=2.0
    elif kind=='negative':rows[0]['seconds']=-0.01
    elif kind=='int':rows[0]['seconds']=0
    elif kind=='row_keys':rows[0]['extra']=False
    elif kind=='stage_type':rows[0]['stage']=0
    elif kind=='charge_bool':changed['charged_seconds']=True
    elif kind=='charge_cap':changed['charged_seconds']=7.0
    elif kind=='accepted_type':changed['accepted']=1
    else:changed['command_utf16_units']=True
    with self.assertRaises(AssertionError):driver.validate_size_timings(changed)
rejected=copy.deepcopy(timed);rejected.update(accepted=False,charged_seconds=7.0)
self.assertIsNone(driver.validate_size_timings(rejected))
''').body)
    return (ast.unparse(ast.fix_missing_locations(tree))+'\n').encode('utf-8')
