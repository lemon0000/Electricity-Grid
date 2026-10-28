"""Fixed 1024-to-2048 diagnostic constructor and sampled-memory parent integration."""
import ast

SCHEDULE=(1,*range(128,2048,128))
CENSUS=('_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once')
PARENT_FUNCTIONS=('validate_census_frame','parse_diagnostic_stderr','validate_prefix_record','validate_prefix_stderr','validate_prefix_observation','compare_child')
MEMORY_PIN={'bytes': 14253, 'sha256': 'e0c54dc42657c223a81e7df8e2316289de58f95ce60457080b27fdf52931bc2d'}


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before))
        source=source.replace(before,after,count)
    return source


class Window(ast.NodeTransformer):
    def visit_Constant(self,node):
        if type(node.value) is int:
            if node.value==1024:node.value=2048
            elif node.value==1023:node.value=2047
            elif node.value==12:node.value=20
        elif type(node.value) is float and node.value==1024.0:node.value=2048.0
        elif type(node.value) is str:
            node.value=node.value.replace('before1024','before2048').replace('complete_1024','complete_2048').replace('audit_census_v4','audit_census_v5')
        return node
    def visit_Tuple(self,node):
        if all(type(n) is ast.Constant for n in node.elts) and tuple(n.value for n in node.elts)==(0,1,127,128,512,1023):
            node.elts=[ast.Constant(value=n) for n in (0,1,127,128,512,1023,1024,2047)];return node
        if all(type(n) is ast.Constant for n in node.elts) and tuple(n.value for n in node.elts)==(1,128,256,384,512,640,768,896):
            node.elts=[ast.Constant(value=n) for n in SCHEDULE];return node
        return self.generic_visit(node)
    def visit_List(self,node):
        if all(type(n) is ast.Constant for n in node.elts) and tuple(n.value for n in node.elts)==(0,1,128,256,384,512,640,768,896,1024):
            node.elts=[ast.Constant(value=n) for n in (0,*SCHEDULE,2048)];return node
        return self.generic_visit(node)


def functions(source,names):
    tree=ast.parse(source);lines=source.splitlines(keepends=True);edits=[]
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name in names:
            edits.append((node.lineno,node.end_lineno,ast.unparse(Window().visit(node))+'\n'))
    assert {n.name for n in tree.body if type(n) is ast.FunctionDef and n.name in names}==set(names)
    for start,end,text in reversed(edits):lines[start-1:end]=[text]
    return ''.join(lines)


def helper(source):return functions(source,CENSUS).encode('utf-8')

def core(source):return replace(source,[('nfc_v6_non_authoritative','nfc_v7_non_authoritative',2)]).encode('utf-8')

def probe(source):return replace(source,[('nfc_v6_non_authoritative','nfc_v7_non_authoritative',1)]).encode('utf-8')

def fixture(source):return replace(source,[('lease_v33.py','lease_v34.py',1),('probe_v31.py','probe_v32.py',1)]).encode('utf-8')


def parent(source):
    source=replace(source,[('nfc_v6_non_authoritative','nfc_v7_non_authoritative',1),('lease_v33.py','lease_v34.py',1),('probe_v31.py','probe_v32.py',1),
        ('bootstrap_import_census1024_none_v2.py','bootstrap_import_census2048_v1.py',2),
        ('results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01/run.py','experiments/staged_rts24_saved_fresh_memory_drain_v1.py',1)])
    source=functions(source,PARENT_FUNCTIONS)
    assert type(MEMORY_PIN) is dict
    source=replace(source,[("dict(bytes=12125,sha256='b504c6d5bcd31412e8f7c03f6bd84094e3895e818c830853501f58fce6c13e59')",repr(MEMORY_PIN),1),
        ("    api=process_api(); process=None;", """    checker=drain.check_bindings;held=drain.drain
    checker_proof=(checker.__code__,checker.__defaults__,checker.__kwdefaults__,checker.__closure__)
    held_proof=(held.__code__,held.__defaults__,held.__kwdefaults__,held.__closure__,tuple(c.cell_contents for c in held.__closure__ or ()))
    def check_drain():
        assert drain.check_bindings is checker and all(a is b for a,b in zip((checker.__code__,checker.__defaults__,checker.__kwdefaults__,checker.__closure__),checker_proof))
        assert drain.drain is held and all(a is b for a,b in zip((held.__code__,held.__defaults__,held.__kwdefaults__,held.__closure__),held_proof[:4]))
        assert all(c.cell_contents is expected for c,expected in zip(held.__closure__ or (),held_proof[4]))
        checker()
    check_drain()
    api=process_api(); process=None;""",1),
        ('child_code,stdout,stderr,error,observation=drain.drain(process,','child_code,stdout,stderr,error,observation=held(process,',1),
        ("        drain_reason=error", "        drain_reason=error\n        check_drain()\n        drain.validate_guard(observation['memory_guard'],healthy=error is None)",1),
        ("if case=='import_discovery':assert error is None or error=='timeout'", "if case=='import_discovery':assert error in (None,'timeout','memory_limit','memory_observation_failed','memory_sample_limit')",1),
        ('            memory=memory_observation(process)',"""            guard=None if observation is None else observation.get('memory_guard')
            memory=(dict(peak_working_set_bytes=guard['maxima']['child']['peak_working_set_bytes'],error=None)
                if guard is not None and guard['samples']>0 else dict(peak_working_set_bytes=None,error='no_live_memory_observation'))""",1),
        ('bounded_drain=observation,memory_observation=memory,','bounded_drain=observation,memory_observation=memory,memory_observation_source=\'last_live_memory_guard\',',1),
        ('child_exit=child_code,parent_kernel_identity=identity,','child_exit=child_code,parent_kernel_identity=identity,parent_controller_pid=os.getpid(),',1)])
    return source.encode('utf-8')


def tests(source):
    tree=ast.parse(source)
    pairs=(('lease_v33.py','lease_v34.py'),('parent_v30.py','parent_v31.py'),('probe_v31.py','probe_v32.py'),
        ('image_entry_fixture_v5.py','image_entry_fixture_v6.py'),('nfc_v6_non_authoritative/driver.py','nfc_v7_non_authoritative/driver.py'),
        ('bootstrap_import_census1024_none_v2.py','bootstrap_import_census2048_v1.py'))
    class Paths(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is str:
                for before,after in pairs:node.value=node.value.replace(before,after)
            return node
    Paths().visit(tree);Window().visit(tree)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='None1024Tests');cls.name='None2048Tests'
    method=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_03_exact1024_and1023_physical');method.name='test_03_exact2048_and2047_physical'
    test=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_01_exact_source_constructor_and_original_audit_statements')
    test.body.insert(0,ast.parse("window=load(ROOT/'experiments/staged_rts24_saved_fresh_census2048_transform_v1.py','_window2048_oracle')").body[0])
    changed=[]
    for node in ast.walk(test):
        if type(node) is not ast.Call or type(node.func) is not ast.Attribute or node.func.attr!='assertEqual':continue
        first=node.args[0]
        if type(first) is not ast.Call or type(first.func) is not ast.Attribute or type(first.func.value) is not ast.Name:continue
        owner,name=first.func.value.id,first.func.attr
        if (owner=='compact' and name=='helper') or (owner=='continuation' and name in ('probe','parent')):
            changed.append(name);text=ast.Call(func=ast.Attribute(value=first,attr='decode',ctx=ast.Load()),args=[ast.Constant(value='utf-8')],keywords=[])
            node.args[0]=ast.Call(func=ast.Attribute(value=ast.Name(id='window',ctx=ast.Load()),attr=name,ctx=ast.Load()),args=[text],keywords=[])
    assert sorted(changed)==['helper','parent','probe']
    tree.body.insert(next(i for i,n in enumerate(tree.body) if type(n) is ast.ClassDef),ast.parse("memory_fixture=load(ROOT/'tests/staged_rts24_saved_fresh_memory_drain_fixture_v1.py','_memory_drain_fixture')").body[0])
    completion=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_07_both_modes_record_authority_and_parent_completion')
    receipt_loop=next(n for n in completion.body if type(n) is ast.For)
    update=next(i for i,n in enumerate(receipt_loop.body) if type(n) is ast.Expr and type(n.value) is ast.Call and type(n.value.func) is ast.Attribute and n.value.func.attr=='update' and type(n.value.func.value) is ast.Name and n.value.func.value.id=='receipt')
    receipt_loop.body[update+1:update+1]=ast.parse("""child_pid=observed['child_record']['kernel_identity']['pid']
receipt['parent_kernel_identity']={**receipt['parent_kernel_identity'],'pid':child_pid}
receipt['parent_controller_pid']=1000
receipt['bounded_drain']={**receipt['bounded_drain'],'direct_child_pid':child_pid,'memory_guard':memory_fixture.accepted_guard(native=True,child_pid=child_pid)}
receipt['memory_observation']=dict(peak_working_set_bytes=6,error=None)
receipt['memory_observation_source']='last_live_memory_guard'
""").body
    receipt_loop.body.extend(ast.parse('''
for kind in ('parent_pid','child_pid','test_mode','memory_source','memory_projection'):
    changed=copy.deepcopy(receipt);guard=changed['bounded_drain']['memory_guard']
    if kind=='parent_pid':guard['binding']['parent_pid']+=1
    elif kind=='child_pid':
        guard['binding']['child_pid']+=1;guard['drained_child_pid']+=1
    elif kind=='test_mode':changed['bounded_drain']['memory_guard']=memory_fixture.accepted_guard()
    elif kind=='memory_source':changed['memory_observation_source']='after_exit'
    else:changed['memory_observation']['peak_working_set_bytes']+=1
    with self.assertRaises(AssertionError):driver.audit_matrix(parent,changed)
''').body)
    changed=0
    for node in ast.walk(completion):
        if type(node) is ast.Call and type(node.func) is ast.Name and node.func.id=='dict':
            keywords={k.arg:k for k in node.keywords}
            if set(keywords)=={'static','unittest','total','files','bytes'}:
                assert {k:v.value.value for k,v in keywords.items()}==dict(static=39,unittest=10,total=49,files=16,bytes=4194304)
                for name,value in dict(static=49,unittest=14,total=63).items():keywords[name].value=ast.Constant(value=value)
                changed+=1
    assert changed==1
    target=ast.parse("changed['caps']['total']=0").body[0].targets[0]
    assignments=[n for n in ast.walk(completion) if type(n) is ast.Assign and len(n.targets)==1 and ast.dump(n.targets[0])==ast.dump(target)]
    assert len(assignments)==1 and assignments[0].value.value==50;assignments[0].value=ast.Constant(value=64)
    bounded=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='test_08_finite_output_duplicate_and_original_guard_rejection')
    bounded.body.extend(ast.parse("memory_fixture.exercise(self,load(ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py','_memory_drain_contract'))").body)
    return (ast.unparse(ast.fix_missing_locations(tree))+'\n').encode('utf-8')
