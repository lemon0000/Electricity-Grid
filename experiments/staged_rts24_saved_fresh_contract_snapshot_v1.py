"""Read original F constants by restricted AST interpretation, without imports."""
import ast
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
SOURCE=ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'
RUNNER=ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py'
DERIVATION=ROOT/'docs/plan/continuation_handoff_20261029_saved_fresh_full_context_role_wip_v1.md'
ERRONEOUS=ROOT/'docs/plan/continuation_handoff_20261029_saved_fresh_source_cleanup_v2.md'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def literal(node):
    if type(node) is ast.Constant and type(node.value) in (str,int):return node.value
    if type(node) is ast.Tuple:return tuple(literal(value) for value in node.elts)
    if type(node) is ast.Call and not node.args and not node.keywords and type(node.func) is ast.Attribute and node.func.attr=='split':
        value=literal(node.func.value);assert type(value) is str;return value.split()
    if type(node) is ast.Call and type(node.func) is ast.Name and node.func.id=='tuple' and len(node.args)==1 and not node.keywords:
        return tuple(literal(node.args[0]))
    if type(node) is ast.Call and type(node.func) is ast.Name and node.func.id=='dict' and not node.args:
        assert all(item.arg is not None for item in node.keywords)
        result={item.arg:literal(item.value) for item in node.keywords};assert len(result)==len(node.keywords);return result
    if type(node) is ast.BinOp and type(node.op) in (ast.Add,ast.Mult,ast.Pow):
        left,right=literal(node.left),literal(node.right);assert type(left) is type(right) is int
        if type(node.op) is ast.Add:return left+right
        if type(node.op) is ast.Mult:return left*right
        assert 0<=right<=10;return left**right
    raise ValueError('unsupported source constant expression')


def extract(path,names):
    raw=path.read_bytes();tree=ast.parse(raw);text=raw.decode('utf-8');rows={}
    for node in tree.body:
        if type(node) is ast.Assign and len(node.targets)==1 and type(node.targets[0]) is ast.Name and node.targets[0].id in names:
            name=node.targets[0].id;assert name not in rows
            rows[name]=dict(value=literal(node.value),line=node.lineno,end_line=node.end_lineno,
                            expression=ast.get_source_segment(text,node.value))
    assert set(rows)==set(names)
    return dict(path=str(path),pin=pin(raw),constants=rows)


def snapshot():
    source=extract(SOURCE,('METRIC_FIELDS',));runner=extract(RUNNER,('TARGETS','RECORDS','CAPS','STAGE_SECONDS'))
    metrics=source['constants']['METRIC_FIELDS']['value'];values={name:row['value'] for name,row in runner['constants'].items()}
    assert len(metrics)==19 and len(values['TARGETS'])==17 and len(values['RECORDS'])==4
    assert sum(values['STAGE_SECONDS'].values())==values['CAPS']['wall_seconds']==180
    derivation=DERIVATION.read_bytes();lines=derivation.decode('utf-8').splitlines()
    witnesses=[dict(line=index+1,text=line) for index,line in enumerate(lines) if '12159' in line or '12053' in line]
    assert witnesses and any('12159' in row['text'] for row in witnesses) and any('12053' in row['text'] for row in witnesses)
    return dict(schema='staged_saved_F_original_contract_snapshot_v1',authority='DRAFT_NONAUTHORITATIVE',
        original_source=source,original_runner=runner,
        original_bounds=dict(metrics=len(metrics),targets=len(values['TARGETS']),wall_seconds=180,
            success_stage_allocation_seconds=165,terminal_records=4,reserved_record_bytes=4*values['CAPS']['record_bytes']),
        conditional_P1_reads=[dict(expression='2*5055+3*683',per_side=5055,remaining_inventories=3,inventory_files=683,total=12159),
                              dict(expression='2*5002+3*683',per_side=5002,remaining_inventories=3,inventory_files=683,total=12053)],
        derivation=dict(path=str(DERIVATION),pin=pin(derivation),witnesses=witnesses,conditional=True,physical_reuse_verified=False),
        historical_erratum=dict(path=str(ERRONEOUS),pin=pin(ERRONEOUS.read_bytes()),
            replaced_claims=dict(metrics=[49,19],targets=[77,17],wall_seconds=[380,180],conditional_P1_reads=[2159,12159])),
        target_modules_executed=0,P1_reads=0,run_authority=False,actual_F=False,resource_admission=False,formal_result=False)


if __name__=='__main__':print(canonical(snapshot()).decode('ascii'))
