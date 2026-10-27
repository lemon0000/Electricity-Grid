"""Pure source construction for the fixed finite diagnostic; no file IO or project imports."""
import ast
import copy

SCHEDULE=(1,64,128,192,256,320,384,448)
CHANGED=('_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once')

class Literals(ast.NodeTransformer):
    def visit_Constant(self,node):
        if type(node.value) is int and node.value==256:node.value=512
        elif type(node.value) is str:node.value=node.value.replace('before256','before512').replace('complete_256','complete_512').replace('audit_census_v2','audit_census_v3')
        return node
    def visit_Tuple(self,node):
        if all(type(n) is ast.Constant for n in node.elts) and tuple(n.value for n in node.elts)==(1,32,64,96,128,160,192,224):
            node.elts=[ast.Constant(n) for n in SCHEDULE];return node
        return self.generic_visit(node)

def replace(source,name,node):
    old=next(n for n in ast.parse(source).body if type(n) is ast.FunctionDef and n.name==name)
    lines=source.splitlines(keepends=True);return ''.join(lines[:old.lineno-1])+ast.unparse(node)+'\n'+''.join(lines[old.end_lineno:])

def helper(source,parts):
    tree=ast.parse(source);other=ast.parse(parts)
    cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    pc=next(n for n in other.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    target=next(n for n in pc.body if type(n) is ast.FunctionDef and n.name=='_check_cache')
    for i,node in enumerate(cls.body):
        if type(node) is ast.FunctionDef and node.name=='_check_cache':cls.body[i]=copy.deepcopy(target)
    for i,node in enumerate(tree.body):
        if type(node) is ast.FunctionDef and node.name in CHANGED:tree.body[i]=Literals().visit(node)
        elif type(node) is ast.FunctionDef and node.name=='_census_finish':
            branch=next(n for n in node.body if type(n) is ast.If and type(n.test) is ast.Name and n.test.id=='was_active')
            branch.body.insert(0,ast.parse("_state['stage']=_state['boundary']._observed_stage").body[0])
    return (ast.unparse(tree)+'\n').encode()

STDERR='''def validate_prefix_stderr(raw):
    parsed=parse_diagnostic_stderr(raw);frames=parsed['census_frames'];assert frames
    final=frames[-1];reason=final['reason'];assert reason in ('prefix_complete','import_return_before512')
    names=['loader_ready','before_adapter_import']+(['adapter_import_returned'] if reason=='import_return_before512' else [])+['after_adapter_import_attempt']
    assert [row[1] for row in parsed['stages']]==names
    schedule=(1,64,128,192,256,320,384,448);count=final['passed']
    assert count==512 if reason=='prefix_complete' else 0<=count<512
    assert [f['passed'] for f in frames]==[0,*[n for n in schedule if n<=count],count]
    assert not any(f['diagnostic_error_count'] or f['rejected'] or f['inflight'] or f['phase'] is not None or f['last_incomplete'] is not None for f in frames)
    begin=frames[0];assert begin['cache_new']==0
    for frame in frames:
        assert frame['start_clock']==begin['start_clock'] and frame['cache_new']==frame['cache_items']-begin['cache_items']
        assert all(row[0]==frame['passed'] for row in frame['buckets'].values())
    assert all(b['machinery_stage']>=a['machinery_stage'] for a,b in zip(frames,frames[1:]))
    assert base64.b64decode(parsed['non_stage_raw_base64'])==b'' and not parsed['unclassified_json_lines'] and not parsed['stack_present']
    graphs=parsed['graph_frames'];assert 2<=len(graphs)<=256 and len(graphs)%2==0
    assert [row[0] for row in graphs]==['enter','exit']*(len(graphs)//2)
    times=[];graph_bytes=0
    for line in raw.splitlines(keepends=True):
        row=json.loads(line);assert canonical(row)+b'\\n'==line
        times.append(row[1]['snapshot_clock'] if row[0]=='census' else row[-1])
        if row[0] in ('enter','exit'):graph_bytes+=len(line)
    assert graph_bytes<=16384 and all(b>=a for a,b in zip(times,times[1:]))
    return parsed
'''
OBSERVATION='''def validate_prefix_observation(record,raw):
    parsed=validate_prefix_stderr(raw);reason=parsed['census_frames'][-1]['reason']
    validate_prefix_record(record,reason)
    assert parsed['census_frames'][-1]['machinery_stage']==record['boundary_report']['machinery_observed_stage']
    return parsed
'''
COMPARE='''def compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors):
    if case=='discovery':return base_compare_child(case,code,stdout,stderr,child_code,identity,argv,writer_errors)
    parsed=parse_diagnostic_stderr(stderr);assert parsed['stages'] and any(row[1]=='before_adapter_import' for row in parsed['stages']) and not writer_errors
    assert parsed['census_frames'] and not any(row['diagnostic_error_count'] for row in parsed['census_frames']) and not parsed['stack_present']
    record,witness=(None,False) if not stdout else validate_diagnostic_record(case,stdout,child_code,identity,argv)
    reason=parsed['census_frames'][-1]['reason'];finite=False
    if record is not None:
        assert record['status']=='failed' and record['primary'] is not None
        if reason in ('prefix_complete','import_return_before512'):
            validate_prefix_observation(record,stderr);finite=True
        else:assert reason=='import_error_before512'
    return dict(child_record=record,diagnostic=parsed,self_close_witness_present=witness,adapter_import_attempts_upper_bound=1,
        adapter_import_return_observed=any(row[1]=='adapter_import_returned' for row in parsed['stages']),prefix_complete=reason=='prefix_complete',finite_terminal_complete=finite,
        census_terminal_reason=reason if record is not None else 'no_child_report_after_'+reason,diagnostic_only=True)
'''

def parent(source):
    for before,after,count in (('aoc_v9_non_authoritative','pfc_v1_non_authoritative',1),('lease_v24.py','lease_v27.py',1),('probe_v21.py','probe_v24.py',1),('bootstrap_import_census256_v1.py','bootstrap_import_census512_parts_v1.py',2)):
        assert source.count(before)==count,(before,source.count(before));source=source.replace(before,after,count)
    for name in ('validate_census_frame','parse_diagnostic_stderr'):
        node=next(n for n in ast.parse(source).body if type(n) is ast.FunctionDef and n.name==name)
        source=replace(source,name,Literals().visit(node))
    node=next(n for n in ast.parse(source).body if type(n) is ast.FunctionDef and n.name=='validate_prefix_record')
    node.args.args.append(ast.arg(arg='reason'));node.args.defaults.append(ast.Constant('prefix_complete'))
    old="assert record['primary']['type'] == 'AuditCensusStop' and record['primary']['message'] == 'diagnostic_prefix_complete_256'"
    text=ast.unparse(node);assert old in text
    text=text.replace(old,"assert reason in ('prefix_complete','import_return_before512')\n    expected='diagnostic_prefix_complete_512' if reason=='prefix_complete' else 'diagnostic_import_return_before512'\n    assert record['primary']['type']=='AuditCensusStop' and record['primary']['message']==expected")
    source=replace(source,'validate_prefix_record',ast.parse(text).body[0])
    for name,text in (('validate_prefix_stderr',STDERR),('validate_prefix_observation',OBSERVATION),('compare_child',COMPARE)):
        source=replace(source,name,ast.parse(text).body[0])
    node=next(n for n in ast.parse(source).body if type(n) is ast.FunctionDef and n.name=='prefix_terminal_complete')
    class Finite(ast.NodeTransformer):
        def visit_Constant(self,node):
            if node.value=='prefix_complete':node.value='finite_terminal_complete'
            return node
    source=replace(source,'prefix_terminal_complete',Finite().visit(node))
    assert source.count('prefix256_not_complete')==1
    return source.replace('prefix256_not_complete','finite_import_observation_incomplete',1).encode()
