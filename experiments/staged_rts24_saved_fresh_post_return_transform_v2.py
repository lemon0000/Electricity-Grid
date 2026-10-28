"""Exact 14-source-function successor; NFC8 failure and its inputs stay frozen."""
import ast
import importlib.util
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('_frozen_post_return_constructor',ROOT/'experiments/staged_rts24_saved_fresh_post_return_transform_v1.py')
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)
OUT='staged_rts24_saved_fresh_nfc_v9_non_authoritative'
NAMESPACE=BASE.NAMESPACE
HELPER='staged_rts24_saved_fresh_bootstrap_post_return_v2.py'
VALIDATOR=BASE.VALIDATOR
NAMES=('digest','sources','stamp','caller_image','capture','hold','bookend','project_metrics','validate_metrics','replay','_replay','validate_payload','bind_payload','compare_payloads')


def replace(source,pairs):return BASE.replace(source,pairs)


def core(source):
    return replace(BASE.core(source).decode(),[('nfc_v8_non_authoritative','nfc_v9_non_authoritative',2)]).encode()


def namespace(source):return BASE.namespace(source)


def helper(source):
    source=BASE.helper(source).decode()
    old="    expected_functions = {c.co_name: c for c in unit.co_consts if type(c) is CodeType and c.co_name in {node.name for node in nodes}}\n    require(len(nodes) == len(expected_functions) == 13, 'fixed thirteen adapter function roots required')"
    new="    expected_names = "+repr(NAMES)+"\n    require(tuple(node.name for node in nodes) == expected_names, 'fixed complete adapter source names required')\n    compiled_roots = tuple(c for c in unit.co_consts if type(c) is CodeType and c.co_name in expected_names)\n    expected_functions = {c.co_name: c for c in compiled_roots}\n    require(len(compiled_roots) == len(expected_functions) == 14, 'fixed complete adapter compiled roots required')"
    return replace(source,[(old,new,1)]).encode()


def probe(source):
    return replace(BASE.probe(source).decode(),[('nfc_v8_non_authoritative','nfc_v9_non_authoritative',1)]).encode()


def parent(source):
    return replace(BASE.parent(source).decode(),[('nfc_v8_non_authoritative','nfc_v9_non_authoritative',1),
        ('lease_v35.py','lease_v36.py',1),('probe_v33.py','probe_v34.py',1),
        ('staged_rts24_saved_fresh_bootstrap_post_return_v1.py',HELPER,2)]).encode()


def driver(source):
    source=replace(source,[('lease_v35.py','lease_v36.py',1),('probe_v33.py','probe_v34.py',1),('parent_v32.py','parent_v33.py',1),
        ('staged_rts24_saved_fresh_bootstrap_post_return_v1.py',HELPER,1),
        ('test_staged_rts24_saved_fresh_post_return_v1.py','test_staged_rts24_saved_fresh_post_return_v2.py',1),
        ('staged_rts24_saved_fresh_post_return_checkpoint_v1.py','staged_rts24_saved_fresh_post_return_checkpoint_v2.py',1),
        ('staged_rts24_saved_fresh_post_return_transform_v1.py','staged_rts24_saved_fresh_post_return_transform_v2.py',1),
        ('staged_deliverability_c_saved_fresh_post_return_admission_scope_v1.md','staged_deliverability_c_saved_fresh_post_return_admission_scope_v2.md',1),
        ("LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative'", "NFC7=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative'\nLEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative'",1),
        ("LEDGER_SHA='b56159068165115b54866169be5fb228cbaad6079081b79b85291443a8d58ce4'", "LEDGER_SHA='39a8b3ac3e5ff68a5810b2d2809d3c16ca292b0ef0f76951a10d957206cd686e'",1),
        ("prior['accepted'] is True and prior['diagnostic_accepted'] is True and prior['prior_not_accepted_count']==37", "prior['accepted'] is True and prior['diagnostic_accepted'] is False and prior['prior_not_accepted_count']==38",1),
        ("prior['all_cumulative_total_seconds']==866.467895100049 and prior['package_charged_seconds']==36.34044319999521", "prior['all_cumulative_total_seconds']==898.7101957000225 and prior['package_charged_seconds']==32.24230059997353",1),
        ("    assert prior['prefix_complete'] is False and prior['adapter_import_return_observed'] is True", "    assert prior['acceptance_scope']=='rejection_metadata_only' and not (LEDGER/'saved.exit.json').exists()\n    failed=read(LEDGER/'probe_import_discovery.receipt.json')['result']['child_record']\n    assert failed['primary']['message']=='fixed thirteen adapter function roots required' and failed['boundary_report']['machinery_authenticated_stage']==2",1),
        ("len(list(LEDGER.iterdir()))==16 and sum(p.stat().st_size for p in LEDGER.iterdir())==1138658", "len(list(LEDGER.iterdir()))==15 and sum(p.stat().st_size for p in LEDGER.iterdir())==1191896",1),
        ('[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,LEDGER]','[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,NFC7,LEDGER]',1),
        ('len(archive)==73','len(archive)==88',1),('==5158740','==6350636',1),
        ("    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1086",
         "    for path,value in read(NFC7/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1086\n    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1099",1),
        ('unit_tests_planned=20','unit_tests_planned=21',1),('tests_run=20,failures=0','tests_run=21,failures=0',1),('result.testsRun==20','result.testsRun==21',1),
        ('prior_not_accepted_count=37','prior_not_accepted_count=38',2),('len(names) == len(set(names)) == 20','len(names) == len(set(names)) == 21',1)])
    # The actual census template still comes from the last completed diagnostic, not the failed metadata checkpoint.
    source=replace(source,[("read(LEDGER / 'checkpoint.json')['census_frames'][-1]", "read(NFC7 / 'checkpoint.json')['census_frames'][-1]",1)])
    def migration(node):
        raw='''def migration():
    constructor=load(CONSTRUCTOR,'_post_return_exact14_constructor')
    rows=(('core',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v34.py',CORE),
        ('probe',ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v32.py',PROBE),
        ('parent',ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v31.py',PARENT),
        ('helper',ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py',HELPER),
        ('namespace',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py'))
    for name,before,after in rows:assert getattr(constructor,name)(before.read_text(encoding='utf-8'))==after.read_bytes(),name
    adapter=ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py';tree=ast.parse(adapter.read_bytes())
    names=tuple(n.name for n in tree.body if type(n) is ast.FunctionDef);assert names==constructor.NAMES and len(names)==len(set(names))==14
    raw=HELPER.read_bytes();unit=ast.parse(raw);loader=next(n for n in unit.body if type(n) is ast.FunctionDef and n.name=='load_bootstrap_adapter')
    fixed=next(n for n in loader.body if type(n) is ast.Assign and type(n.targets[0]) is ast.Name and n.targets[0].id=='expected_names')
    assert ast.literal_eval(fixed.value)==names
    before=ast.parse(rows[-1][1].read_bytes());after=ast.parse(rows[-1][2].read_bytes())
    reader=lambda t:next(n for n in t.body if type(n) is ast.FunctionDef and n.name=='freeze_namespace_graph')
    assert ast.dump(reader(before))==ast.dump(reader(after))
    return dict(versioned_post_return=True,constructor_exact=True,original_graph_reader_unchanged=True,
        exact14_source_function_literal=True,each_compiled_root_once=True,source49_unchanged=True,all_fresh_checks_retained=True,
        memory_stop_policy_unchanged=True,scientific_acceptance_threshold_change=False,diagnostic_only=True)
'''
        return ast.parse(raw).body[0]
    return BASE.edit_functions(source,{'migration':migration}).encode()


def checkpoint(source):
    return replace(source,[('nfc_v8_non_authoritative','nfc_v9_non_authoritative',1),('unit_tests=20','unit_tests=21',1),
        ('prior_not_accepted_count=37+','prior_not_accepted_count=38+',1),('prior_archive_files=73,prior_archive_bytes=5158740','prior_archive_files=88,prior_archive_bytes=6350636',1)]).encode()


def create():
    pairs=(('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v34.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py'),
        ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v32.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py'),
        ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v31.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py'),
        ('helper','experiments/staged_rts24_saved_fresh_bootstrap_import_census2048_v1.py','experiments/'+HELPER),
        ('driver','results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative/driver.py','results/tables/'+OUT+'/driver.py'),
        ('checkpoint','experiments/staged_rts24_saved_fresh_post_return_checkpoint_v1.py','experiments/staged_rts24_saved_fresh_post_return_checkpoint_v2.py'))
    out=ROOT/'results/tables'/OUT;out.mkdir(exist_ok=True)
    for name,before,after in pairs:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf-8'));compile(raw,after,'exec',dont_inherit=True,optimize=0)
        p=ROOT/after
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
    policy=out/'import_policy.json'
    if not policy.exists():policy.write_bytes((ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative/import_policy.json').read_bytes())
    print('Created independent exact14 post-return draft')


if __name__=='__main__':create()
