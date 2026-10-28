"""Host AST declaration oracle for the frozen Source49 binding consumer."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys

if sys.flags.optimize!=0:raise RuntimeError('unoptimized source oracle required')

ROOT=Path(__file__).absolute().parents[1]
LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def inspect():
    checkpoint=(LEDGER/'checkpoint.json').read_bytes()
    assert pin(checkpoint)['sha256']=='8abd5d04628ee39cb93dc31f4e4eb307ecf9f49f99b80063d77d903e0a24bd65'
    registration_raw=(LEDGER/'registration.json').read_bytes();cp=json.loads(checkpoint)
    assert cp['root_map_before_checkpoint']['registration.json']==pin(registration_raw)
    registration=json.loads(registration_raw);sources=registration['source_pins'];assert len(sources)==49
    raw={path:(ROOT/path).read_bytes() for path in sources}
    assert {path:pin(value) for path,value in raw.items()}==sources
    targets=[('experiments/staged_rts24_saved_fresh_adoption_v1.py','_expectation_binding_entry',('binding',),())]
    targets.extend(('src/staged_rts24_saved_fresh_adoption_v1.py',name,args,kw)
        for name,args,kw in (('hold',('expected_sources','expected_caller_image'),()),
            ('capture',('expected_sources',),()),('bookend',('held',),('inventory',)),
            ('caller_image',('held',),()),('sources',('expected',),()),('validate_metrics',('value',),())))
    targets.extend((('src/staged_rts24_development_v1.py','load_fixture',('path',),()),
        ('src/staged_rts24_p2_package_check_v1.py','inventory',('root',),()),
        ('src/staged_rts24_evidence_store_v1.py','read_bytes',('path','allow_links'),()),
        ('src/staged_rts24_saved_point_replay_v1.py','_outer',('record',),())))
    rows=[]
    for path,name,args,kw in targets:
        nodes=[node for node in ast.parse(raw[path]).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name]
        assert len(nodes)==1 and type(nodes[0]) is ast.FunctionDef and not nodes[0].decorator_list
        node=nodes[0];actual=node.args
        assert tuple(arg.arg for arg in actual.args)==args and tuple(arg.arg for arg in actual.kwonlyargs)==kw
        assert not actual.posonlyargs and actual.vararg is actual.kwarg is None
        if name=='load_fixture':
            assert len(actual.defaults)==1 and type(actual.defaults[0]) is ast.Name and actual.defaults[0].id=='CONFIG'
            assert actual.kw_defaults==[]
        elif name=='read_bytes':
            assert len(actual.defaults)==1 and type(actual.defaults[0]) is ast.Constant and actual.defaults[0].value is False
            assert actual.kw_defaults==[]
        elif name=='bookend':
            assert actual.defaults==[] and len(actual.kw_defaults)==1 and type(actual.kw_defaults[0]) is ast.Constant
            assert actual.kw_defaults[0].value is True
        else:assert actual.defaults==actual.kw_defaults==[]
        rows.append(dict(path=path,name=name,source_pin=pin(raw[path]),declaration=ast.dump(actual,include_attributes=False),
            function_ast_pin=pin(ast.dump(node,include_attributes=False).encode())))
    assert len(rows)==11
    return dict(schema='saved_F_binding_source_oracle_v1',authority='DRAFT_NONAUTHORITATIVE',accepted=True,
        source_epoch=registration['source_epoch'],source_pins=sources,source_signature_rows=rows,
        oracle_pin=pin(Path(__file__).read_bytes()),producer_capability_verified=False,run_authority=False,
        scientific_evidence_adopted=False,formal_result=False,actual_F=False)
