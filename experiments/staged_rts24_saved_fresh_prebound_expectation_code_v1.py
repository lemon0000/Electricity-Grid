"""Source-bound expectation code derivation; never executes project/P1 operations."""
import ast
import copy
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import CodeType

if sys.flags.optimize!=0:raise RuntimeError('unoptimized producer derivation required')
ROOT=Path(__file__).absolute().parents[1]
ENTRY='experiments/staged_rts24_saved_fresh_adoption_v1.py'
LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def require(value,message):
    if not value:raise ValueError(message)


def source_contract():
    raw=(LEDGER/'checkpoint.json').read_bytes()
    require(pin(raw)['sha256']=='bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de','fixed connected predecessor required')
    cp=json.loads(raw);require(cp['accepted'] is cp['diagnostic_accepted'] is True,'accepted connection required')
    reg_raw=(LEDGER/'registration.json').read_bytes();require(pin(reg_raw)==cp['root_map_before_checkpoint']['registration.json'],'predecessor registration differs')
    reg=json.loads(reg_raw);sources=reg['source_pins']
    require(len(sources)==49 and pin(canonical(sources))['sha256']==reg['source_epoch']=='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875','fixed Source49 required')
    for path,expected in sources.items():require(pin((ROOT/path).read_bytes())==expected,'producer source differs: '+path)
    return dict(checkpoint_pin=pin(raw),registration_pin=pin(reg_raw),source_pins=sources,source_epoch=reg['source_epoch'])


def transform(node):
    require(type(node) is ast.FunctionDef and node.name=='capture_saved_expectation' and not node.decorator_list,'fixed expectation function required')
    args=node.args
    require(not args.posonlyargs and len(args.args)==1 and args.args[0].arg=='expected_sources'
        and not args.defaults and not args.kwonlyargs and not args.kw_defaults and args.vararg is args.kwarg is None,'fixed expectation signature required')
    for item in ast.walk(node):
        require(not isinstance(item,(ast.Global,ast.Nonlocal)),'producer scope rebinding forbidden')
    matches=[]
    for index,item in enumerate(node.body):
        if type(item) is ast.Assign and len(item.targets)==1 and type(item.targets[0]) is ast.Name and item.targets[0].id=='binding':matches.append(index)
    require(len(matches)==1,'unique preparation assignment required');index=matches[0];removed=node.body[index]
    call=removed.value
    require(type(call) is ast.Call and type(call.func) is ast.Name and call.func.id=='_expectation_adapter'
        and len(call.args)==1 and type(call.args[0]) is ast.Name and call.args[0].id=='source' and not call.keywords,'fixed preparation call required')
    expected_source=ast.parse('source = parse(canonical(expected_sources))').body[0]
    require(index>=1 and ast.dump(node.body[index-1])==ast.dump(expected_source),'fixed source producer required before binding')
    result=copy.deepcopy(node);result.name='capture_saved_expectation_prebound'
    result.args.args.append(ast.copy_location(ast.arg(arg='binding',annotation=None,type_comment=None),args.args[0]))
    del result.body[index];ast.fix_missing_locations(result)
    require(all(not (type(item) is ast.Name and item.id=='binding' and not isinstance(item.ctx,ast.Load))
        for item in ast.walk(result)),'extra binding Store/Del forbidden')
    inverse=copy.deepcopy(result);inverse.name=node.name;inverse.args.args.pop();inverse.body.insert(index,copy.deepcopy(removed))
    require(ast.dump(inverse,include_attributes=True)==ast.dump(node,include_attributes=True),'prebound derivation is not reversible')
    return result,inverse,index


def function_code(node,filename):
    unit=compile(ast.Module(body=[node],type_ignores=[]),filename,'exec',dont_inherit=True,optimize=0)
    codes=[value for value in unit.co_consts if type(value) is CodeType and value.co_name==node.name]
    require(len(codes)==1 and not codes[0].co_freevars,'closed function code required');return codes[0]


def code_image(code):
    def constant(value):
        if type(value) is CodeType:return ('code',code_image(value))
        if type(value) is bytes:return ('bytes',value.hex())
        if type(value) is tuple:return ('tuple',[constant(item) for item in value])
        if type(value) is frozenset:return ('frozenset',sorted((constant(item) for item in value),key=canonical))
        if value is Ellipsis:return ('ellipsis',)
        require(value is None or type(value) in (str,int,bool,float,complex),'unsupported producer code constant')
        return ('complex',value.real,value.imag) if type(value) is complex else (type(value).__name__,value)
    names=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags',
        'co_names','co_varnames','co_freevars','co_cellvars','co_filename','co_name','co_qualname','co_firstlineno')
    return dict(attributes=[(name,getattr(code,name)) for name in names],bytecode=code.co_code.hex(),
        linetable=code.co_linetable.hex(),exceptiontable=code.co_exceptiontable.hex(),constants=[constant(item) for item in code.co_consts])


def normalize_derived_metadata(code,filename):
    consts=tuple(normalize_derived_metadata(item,filename) if type(item) is CodeType else item for item in code.co_consts)
    return code.replace(co_filename=filename,co_qualname=code.co_qualname.replace('capture_saved_expectation_prebound','capture_saved_expectation',1),co_consts=consts)


def derive(raw):
    contract=source_contract();require(type(raw) is bytes and pin(raw)==contract['source_pins'][ENTRY],'frozen ENTRY bytes required')
    tree=ast.parse(raw);nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=='capture_saved_expectation']
    require(len(nodes)==1,'unique original expectation root required');node=nodes[0]
    successor,inverse,index=transform(node);filename=str(ROOT/ENTRY)
    original=function_code(node,filename);restored=function_code(inverse,filename)
    require(original==restored,'restored complete CodeType differs')
    full_module=compile(raw,filename,'exec',dont_inherit=True,optimize=0)
    roots=[item for item in full_module.co_consts if type(item) is CodeType and item.co_name==node.name]
    require(len(roots)==1 and roots[0]==original,'full-module original CodeType differs')
    code=function_code(successor,filename+'::prebound_v1')
    def walk(value):
        yield value
        for item in value.co_consts:
            if type(item) is CodeType:yield from walk(item)
    require(all('_expectation_adapter' not in item.co_names for item in walk(code)),'second preparation dependency remains')
    require('_expectation_binding_entry' in code.co_names and code.co_argcount==2,'original held binding entry required')
    require(original.co_cellvars.count('binding')==1 and code.co_cellvars==('binding',)+tuple(name for name in original.co_cellvars if name!='binding'),
        'binding must become the only reordered cell argument')
    before=[item for item in original.co_consts if type(item) is CodeType and item.co_name=='bookends']
    after=[item for item in code.co_consts if type(item) is CodeType and item.co_name=='bookends']
    require(len(before)==len(after)==1 and before[0].co_freevars==after[0].co_freevars
        and before[0]==normalize_derived_metadata(after[0],filename),'bookend closure code or freevars changed')
    report=dict(schema='staged_saved_F_prebound_expectation_code_v1',authority='DRAFT_NONAUTHORITATIVE',
        source_contract=contract,source_path=ENTRY,source_pin=pin(raw),original_name=node.name,derived_name=successor.name,
        original_args=['expected_sources'],derived_args=['expected_sources','binding'],removed_statement_index=index,
        original_ast_pin=pin(ast.dump(node,include_attributes=True).encode()),derived_ast_pin=pin(ast.dump(successor,include_attributes=True).encode()),
        full_module_code_pin=pin(canonical(code_image(roots[0]))),derived_code_pin=pin(canonical(code_image(code))),
        original_cellvars=list(original.co_cellvars),derived_cellvars=list(code.co_cellvars),bookend_freevars=list(before[0].co_freevars),
        inverse_position_ast_equal=True,inverse_complete_code_equal=True,full_module_root_code_equal=True,
        binding_cell_argument_verified=True,bookend_code_metadata_only_renamed=True,second_preparation_dependency_removed=True,
        requires_original_entry_globals=True,requires_same_live_prepared_binding=True,
        removed_preparation_obligations=['Source49_map_and_raw_freshness','canonical_adapter_source_code_defaults_and_module_identity',
            'fixed_executable_and_adapter_P1_SCOPE','final_source_bookend'],
        P1_reads=0,source49_target_modules_executed=0,producer_capability_verified=False,full_runtime_binding_verified=False,
        full_P1_content_verified=False,run_authority=False,resource_admission=False,scientific_evidence_adopted=False,
        formal_result=False,actual_F=False)
    return code,report


def current():return derive((ROOT/ENTRY).read_bytes())
