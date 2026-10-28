"""Independent finite2048 controller package; frozen legacy checks remain intact."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import tokenize
import zlib

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v3_non_authoritative'
AOC=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v37.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v35.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v2.py'
GRAPH=ROOT/'experiments/staged_rts24_saved_fresh_import_graph_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_live_profile_v1.py'
NATIVE_TEST=ROOT/'tests/staged_rts24_saved_fresh_image_entry_fixture_v6.py'
TRANSFORM=ROOT/'experiments/staged_rts24_saved_fresh_none1024_transform_v1.py'
COMPACT=ROOT/'experiments/staged_rts24_saved_fresh_prefix_indent_transform_v1.py'
RELOCATE=ROOT/'experiments/staged_rts24_saved_fresh_none1024_relocate_v1.py'
CHECKPOINT=ROOT/'experiments/staged_rts24_saved_fresh_live_profile_checkpoint_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_post_return_admission_scope_v3.md'
CAPTURE=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/capture.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
CONSTRUCTOR=ROOT/'experiments/staged_rts24_saved_fresh_live_profile_transform_v1.py'
MEMORY=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
MEMORY_FIXTURE=ROOT/'tests/staged_rts24_saved_fresh_memory_drain_fixture_v1.py'
NFC6=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v6_non_authoritative'
NFC7=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative'
NFC8=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative'
LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative'
REFERENCE=ROOT/'experiments/staged_rts24_saved_fresh_live_profile_reference_v1.py'
REF_PROFILE=LEDGER/'import_profile.json'
REF_CHECKPOINT=LEDGER/'checkpoint.json'
PREP_LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v5_non_authoritative'
UNIT_LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v4_non_authoritative'
MEMO=ROOT/'results/tables/staged_rts24_saved_fresh_pin_memo_v1_non_authoritative'
LEDGER_SHA='5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da'
PREP_LEDGER_SHA='7177125654559df795938fd722ad46f0ddfdb6276c636a1d3063763c01c7c256'
UNIT_LEDGER_SHA='774f4978e333bb05b79f6245f86e2e4b6faf4b2d3ff566046712f2dc84be6b4d'
MEMO_SHA='e340c6ee3758175c78c2992c57586000a021ead268158e3e67571bb16243297b'
LEGACY_CHECKPOINT_SHA='dd669b1f06ce7e5e174ebd5c9cc8f0fc6b2fcebdd6fbe84ae8b69bfd15b28731'

PHASES=('unittest','pre_seal','discovery','profile_admission','live','saved')
CAPS=dict(unittest=20,pre_seal=5,discovery=6,profile_admission=5,live=30,saved=5)
STATIC_CAP=65;UNIT_CAP=20;TOTAL_CAP=85
SIZE_CAP=6;REGISTER_CAP=4;CHECKPOINT_CAP=4
SIZE_STAGES=('prerun','compile_only','predecessor_archive','migration_source_transport','import_graph','runtime_leaves',
    'first_input_pins','manifest_codec_command','registration_candidate','final_input_source_bookend','serialization')
MAX_FILES=17;MAX_BYTES=4194304
POLICY=OUT/'import_policy.json'
POLICY_PIN=dict(bytes=4745,sha256='4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c')
FILE_CAPS={'driver.py':65536,'import_policy.json':8192,'size_admission.json':262144,'registration.json':1048576,
    'unittest.exit.json':65536,'import_profile.json':1048576,'startup_profile.json':131072,'probe_discovery.plan.json':65536,'probe_normal.plan.json':65536,
    'probe_discovery.receipt.json':1048576,'probe_normal.receipt.json':1048576,'checkpoint.json':65536,
    'unit.stdout.raw':65536,'unit.stderr.raw':16384,'saved.exit.json':65536}
BASE_FILES={'driver.py','import_policy.json','size_admission.json','registration.json'}
OUTPUTS=dict(unittest=set(),pre_seal=set(),discovery={'probe_discovery.plan.json','probe_discovery.receipt.json','startup_profile.json'},
    profile_admission=set(),live={'probe_normal.plan.json','probe_normal.receipt.json'},saved=set())
_ACTIVE_EXIT=None
AUTHORITY='DRAFT_NONAUTHORITATIVE'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path,name='_packed_diagnostic'):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def helpers():return [CORE,HELPER,PROBE,PARENT,GRAPH,TEST,NATIVE_TEST,TRANSFORM,COMPACT,RELOCATE,CONSTRUCTOR,MEMORY,MEMORY_FIXTURE,ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py',ROOT/'experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py',REFERENCE,Path(__file__).absolute()]
def flags():return {k:False for k in load(PARENT,'_packed_false_fields').FALSE_FIELDS}


def embed(raw,encoding='raw'):
    assert type(raw) is bytes and encoding in ('raw','canonical_json')
    return dict(encoding=encoding,raw_base64=base64.b64encode(raw).decode('ascii'),pin=pin(raw))
def packed(objects):return {k:embed(canonical(v),'canonical_json') for k,v in objects.items()}
def exact_pin(value):
    assert type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and value['bytes']>=0
    assert type(value['sha256']) is str and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256'])
def reopen(items):
    result={}
    for name,item in items.items():
        assert set(item)=={'encoding','raw_base64','pin'} and item['encoding'] in ('raw','canonical_json')
        exact_pin(item['pin']);raw=base64.b64decode(item['raw_base64'],validate=True);assert pin(raw)==item['pin']
        if item['encoding']=='canonical_json':value=json.loads(raw);assert canonical(value)==raw
        else:value=raw
        result[name]=value
    return result


def previous():
    raw=(LEDGER/'checkpoint.json').read_bytes();assert sha256(raw).hexdigest()==LEDGER_SHA
    prior=json.loads(raw);assert prior['accepted'] is True and prior['diagnostic_accepted'] is True and prior['prior_not_accepted_count']==38
    assert prior['all_cumulative_total_seconds']==937.488786600002 and prior['package_charged_seconds']==38.77859089997946
    assert prior['acceptance_scope']=='packed_metadata_and_post_return_diagnostic_only' and prior['runtime_phase_before_close']=='OBSERVED'
    assert prior['audit_validation']['terminal_mode']=='post_return_observed_closed'
    assert {p.name for p in LEDGER.iterdir()}==set(prior['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in prior['root_map_before_checkpoint'].items():assert pin((LEDGER/name).read_bytes())==value,name
    assert len(list(LEDGER.iterdir()))==17 and sum(p.stat().st_size for p in LEDGER.iterdir())==2285992
    for path,value in read(LEDGER/'registration.json')['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    raw=(PREP_LEDGER/'checkpoint.json').read_bytes();assert sha256(raw).hexdigest()==PREP_LEDGER_SHA
    prep=json.loads(raw);assert prep['accepted'] is True and prep['diagnostic_accepted'] is False
    assert prep['acceptance_scope']=='rejection_metadata_only' and prep['prior_not_accepted_count']==37
    assert prep['all_cumulative_total_seconds']==796.826838000062 and prep['package_charged_seconds']==4.052060000001802
    assert {p.name for p in PREP_LEDGER.iterdir()}==set(prep['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in prep['root_map_before_checkpoint'].items():assert pin((PREP_LEDGER/name).read_bytes())==value,name
    assert len(list(PREP_LEDGER.iterdir()))==4 and sum(p.stat().st_size for p in PREP_LEDGER.iterdir())==194044
    assert read(PREP_LEDGER/'size_admission.json')['accepted'] is False
    for path,value in read(PREP_LEDGER/'size_admission.json')['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    raw=(UNIT_LEDGER/'checkpoint.json').read_bytes();assert sha256(raw).hexdigest()==UNIT_LEDGER_SHA
    unit_prior=json.loads(raw);assert unit_prior['accepted'] is False and unit_prior['diagnostic_accepted'] is False
    assert unit_prior['acceptance_scope']=='rejection_metadata_only' and unit_prior['prior_not_accepted_count']==36
    assert unit_prior['all_cumulative_total_seconds']==792.7747780000602
    assert unit_prior['package_charged_seconds']==12.96942539999145
    assert {p.name for p in UNIT_LEDGER.iterdir()}==set(unit_prior['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in unit_prior['root_map_before_checkpoint'].items():assert pin((UNIT_LEDGER/name).read_bytes())==value,name
    assert len(list(UNIT_LEDGER.iterdir()))==7 and sum(p.stat().st_size for p in UNIT_LEDGER.iterdir())==726621
    unit=read(UNIT_LEDGER/'unittest.exit.json');assert unit['accepted'] is True
    assert read(UNIT_LEDGER/'pre_seal.exit.json')['accepted'] is False
    for path,value in read(UNIT_LEDGER/'registration.json')['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    memo_raw=(MEMO/'checkpoint.json').read_bytes();assert sha256(memo_raw).hexdigest()==MEMO_SHA
    memo=json.loads(memo_raw);assert memo['accepted'] and memo['diagnostic_accepted'] and memo['prior_not_accepted_count']==34
    assert memo['candidate_adopted'] is False and memo['production_helper_selected'] is False
    assert {p.name for p in MEMO.iterdir()}=={Path(p).name for p in memo['artifact_pins']}|{'checkpoint.json'}
    for path,value in memo['artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
    legacy_raw=(OLD/'checkpoint.json').read_bytes();assert sha256(legacy_raw).hexdigest()==LEGACY_CHECKPOINT_SHA
    legacy=json.loads(legacy_raw);assert legacy['accepted'] and not legacy['diagnostic_accepted'] and legacy['prior_not_accepted_count']==34
    assert {p.name for p in OLD.iterdir()}==set(legacy['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in legacy['root_map_before_checkpoint'].items():assert pin((OLD/name).read_bytes())==value,name
    old=read(OLD/'registration.json')
    leaf=load(OLD/'driver.py','_frozen_nfc3_leaf');leaf.check(old)
    trace_root=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_metadata_read_v1_non_authoritative'
    ledger_inputs=read(MEMO/'registration.json')['input_pins']
    assert {p.name for p in trace_root.iterdir()}=={'driver.py','inspection.json'}
    for p in trace_root.iterdir():assert pin(p.read_bytes())==ledger_inputs[str(p)]
    roots=[ROOT/f'results/tables/staged_rts24_saved_fresh_nfc_v{i}_non_authoritative' for i in (1,2,3)]+[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,NFC7,NFC8,LEDGER]
    archive=[p for root in roots for p in root.iterdir()];assert len(archive)==105 and all(p.is_file() for p in archive)
    assert sum(p.stat().st_size for p in archive)==8636628
    return old,prior


def inherited_inputs(old):
    path=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v2_non_authoritative/registration.json'
    raw=path.read_bytes();assert pin(raw)==old['inherited_registration_pin']
    result=dict(json.loads(raw)['input_pins'])
    for path,value in old['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==old['effective_input_count']==933
    unit_reg=read(UNIT_LEDGER/'registration.json');assert unit_reg['effective_input_count']==1051
    for path,value in unit_reg['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1051
    for path,value in read(PREP_LEDGER/'size_admission.json')['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1061
    for path,value in read(NFC6/'registration.json')['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1072
    for path,value in read(NFC7/'registration.json')['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1086
    for path,value in read(NFC8/'registration.json')['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1099
    for path,value in read(LEDGER/'registration.json')['input_pins'].items():
        if path in result:assert result[path]==value,path
        else:result[path]=value
    assert len(result)==1110
    return result


def migration():
    constructor = load(CONSTRUCTOR, '_normal_live_constructor')
    rows = (('core', ROOT / 'experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py', CORE), ('probe', ROOT / 'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py', PROBE), ('parent', ROOT / 'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py', PARENT), ('validator', ROOT / 'experiments/staged_rts24_saved_fresh_post_return_validation_v1.py', ROOT / 'experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py'))
    for name, before, after in rows:
        assert getattr(constructor, name)(before.read_text(encoding='utf-8')) == after.read_bytes(), name
    old_reg = read(LEDGER / 'registration.json')
    for path in (HELPER, ROOT / 'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py', MEMORY):
        assert pin(path.read_bytes()) == old_reg['helper_pins'][str(path)]
    reference = load(REFERENCE, '_normal_live_reference').reference()
    assert reference['reference']['path'] == str(REF_PROFILE) and reference['source_checkpoint']['pin'] == pin(REF_CHECKPOINT.read_bytes())
    return dict(versioned_normal_live=True, constructor_exact=True, helper_and_graph_reader_unchanged=True, reference_source=reference, normal_single_receipt=True, legacy_parent_frozen=True, source49_unchanged=True, scientific_acceptance_threshold_change=False, diagnostic_only=True)


def space_for(additions):
    current={p.name:p.stat().st_size for p in OUT.iterdir() if p.is_file()};assert len(current)==len(list(OUT.iterdir()))
    needed=dict(additions)
    for name in ('checkpoint.json',_ACTIVE_EXIT):
        if name is not None and name not in current and name not in needed:needed[name]=FILE_CAPS.get(name,16384)
    assert not set(current)&set(additions)
    assert len(current)+len(needed)<=MAX_FILES and sum(current.values())+sum(needed.values())<=MAX_BYTES
def write_raw(path,raw):
    assert path.parent==OUT and len(raw)<=FILE_CAPS.get(path.name,16384);space_for({path.name:len(raw)})
    with path.open('xb') as stream:stream.write(raw)
def save(path,value):write_raw(path,canonical(value))
def parent_save(path,value):
    raw=canonical(value)
    if path.name.endswith('.receipt.json') and len(raw)>FILE_CAPS[path.name]:
        reduced={**value,'accepted':False,'primary':'receipt_archive_cap','archive_prior_primary':value['primary'],
            'result':None,'archive_derived_result_pin':pin(canonical(value['result'])),'archive_proposed_receipt_pin':pin(raw)}
        write_raw(path,canonical(reduced));raise ValueError('receipt archive cap; original streams retained')
    write_raw(path,raw)


def nodes():
    paths = (ROOT / 'tests/test_staged_rts24_saved_fresh_none_census2048_v1.py', NATIVE_TEST, ROOT / 'tests/test_staged_rts24_saved_fresh_post_return_v2.py', TEST)
    classes = ('None2048Tests', 'NativeImageTests', 'PostReturnTests', 'LiveProfileTests')
    names = []
    for path, name in zip(paths, classes):
        cls = next((n for n in ast.parse(path.read_bytes()).body if type(n) is ast.ClassDef and n.name == name))
        names.extend((n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_')))
    assert len(names) == len(set(names)) == 25
    return sorted(('live_profile_tests.LiveProfileTests.' + name for name in names))


def output_bounds():
    value = read(NFC7 / 'checkpoint.json')['census_frames'][-1]
    high = float.fromhex('0x1.fffffffffffffp+1023')
    value.update(seq=20, reason='import_return_before2048', active=False, inflight=False, start_clock=-high, snapshot_clock=-high, entered=2048, passed=2048, rejected=2048, observed=2048, phase='globals_attrs', last_incomplete='globals_attrs', diagnostic_error_count=4, cache_items=4096, cache_new=4096, machinery_stage=2, installation_seen=1)
    value['buckets'] = {name: [2048, high, high] for name in value['buckets']}
    line = len(canonical(['census', value])) + 1
    census = 20 * line
    parent = load(PARENT, '_post_output_bounds')
    stages = parent.POST.STAGES
    graph = 40 * sum((max((len(canonical(row)) + 1 for row in candidates)) for candidates in ([['graph', 40, kind, 'enter', -high] for kind in ('namespace', 'adapter')], [['graph', 40, kind, 'exit', -high, 50000, 50000, 4194304] for kind in ('namespace', 'adapter')])))
    stage = sum((len(canonical(['stage', name, -high])) + 1 for name in stages))
    assert line <= 2048 and census <= 24576 and (census + graph + stage <= 32768)
    memory = load(MEMORY, '_post_memory_bound')
    guard = memory.initial_guard()
    metric = dict(working_set_bytes=268435456, peak_working_set_bytes=268435456, private_bytes=268435456)
    guard.update(attempts=4096, samples=4096, maxima={name: dict(metric) for name in ('parent', 'child')}, last={name: dict(metric) for name in ('parent', 'child')}, max_sum_peak_working_set_bytes=536870912, max_sum_private_bytes=536870912, native_sampler_bound=True, binding=dict(parent_pid=4294967294, child_pid=4294967295, child_handle=18446744073709551615, struct_bytes=80), drained_child_pid=4294967295)
    memory.validate_guard(guard)
    body = dict(accepted=True, authority=AUTHORITY, metadata_only=True, diagnostic_accepted=True, audit_validation=dict(accepted=True, terminal_mode='post_return_live_closed', passed=2048, importer_return_observed=True, live_before_close=True, boundary_completed=True, graph_counts=dict(namespace=40, adapter=40), source_bookends=5, selected_open_window_only=True, all_unselected_events_verified=False, candidate_adopted=False, resource_admission=False), stages=[], graph_frames=[], census_frames=[], memory_observation=dict(peak_working_set_bytes=None, error='x' * 160), memory_guard=guard, memory_observation_source='last_live_memory_guard', drain_reason=None, runtime_phase_before_close='LIVE', import_profile_pin=dict(bytes=1048576, sha256='0' * 64), post_metrics=dict(returned=True, idle_getter_events=999999999, busy_getter_events=999999999, **{name: [40, high, high] for name in parent.POST.METRICS}), all_unselected_events_verified=False, candidate_adopted=False, **flags())
    reference = load(REFERENCE, '_live_size_reference').reference()
    expected = dict(bytes=1048576, sha256='0' * 64)
    body['audit_validation'].update(expected_import_profile_pin=expected, observed_import_profile_pin=expected, frozen_nfc9_import_profile_exact_match=True)
    body.update(expected_import_profile_pin=expected, frozen_nfc9_import_profile_exact_match=True, reference_source=reference, reference_context_pin=expected)
    body_bytes = len(canonical(body))
    assert body_bytes <= 6144
    return dict(census_frame_bytes=line, max_frames=20, normal_frames=18, census_upper_bytes=census, graph_call_cap=40, graph_upper_bytes=graph, stage_upper_bytes=stage, stderr_upper_bytes=census + graph + stage, saved_body_upper_bytes=body_bytes)


def registration_value(old,prior,inputs,code,units,origins,migrated,cost,size_pin,graph):
    snapshots={str(p):embed(p.read_bytes()) for p in helpers() if str(p) not in old['helper_pins']}
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_normal.plan.json'),'0'*64]
    artifacts={**{'helper:'+path:value for path,value in snapshots.items()},'transport':embed(code),'command':embed(canonical(command),'canonical_json')}
    inherited=inherited_inputs(old)
    return dict(accepted=True,authority=AUTHORITY,input_pins=inputs,helper_pins=pins(helpers()),embedded_artifacts=artifacts,
        inherited_registration_pin=pin((OLD/'registration.json').read_bytes()),inherited_input_pins_pin=pin(canonical(old['input_pins'])),
        inherited_embedded_sources_pin=pin(canonical(old['embedded_artifacts'])),inherited_effective_pins_pin=pin(canonical(inherited)),effective_input_count=len(set(inputs)|set(inherited)),
        previous_checkpoint_pin=pin((LEDGER/'checkpoint.json').read_bytes()),inherited_size_admission_pin=pin((PREP_LEDGER/'size_admission.json').read_bytes()),inherited_unit_registration_pin=pin((UNIT_LEDGER/'registration.json').read_bytes()),
        inherited_unit_exit_pin=pin((UNIT_LEDGER/'unittest.exit.json').read_bytes()),source_pins=old['source_pins'],source_epoch=old['source_epoch'],
        size_admission_pin=size_pin,transport_pin=pin(code),command_utf16_units=units,command_utf16_units_by_case=command_units_by_case(code),migration=migrated,conditional_runtime_origins=origins,
        static_import_graph=graph,registration_charged_seconds=cost,predecessor_charged_seconds=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=38,
        caps=dict(static=STATIC_CAP,unittest=UNIT_CAP,total=TOTAL_CAP,files=MAX_FILES,bytes=MAX_BYTES),
        memory_contract=dict(schema='staged_saved_F_sampled_memory_guard_v1',process_bytes=268435456,pair_bytes=536870912,poll_seconds=0.01,max_samples=4096,struct_bytes=80,sample_policy='last_live_poll_only',continuous_bound_verified=False,combined_retention_verified=False),
        output_bounds=output_bounds(),unit_nodes=nodes(),unit_tests_planned=25,
        all_unselected_events_verified=False,candidate_adopted=False,independent_tcb_authenticated=False,**flags())


def validate_size_timings(value):
    assert type(value['accepted']) is bool and value['authority']==AUTHORITY and value['kind']=='static'
    assert type(value['cap_seconds']) is int and value['cap_seconds']==SIZE_CAP
    charge=value['charged_seconds'];assert type(charge) is float and math.isfinite(charge) and charge>=0
    units=value['command_utf16_units'];assert type(units) is int and units>0
    cases=value['command_utf16_units_by_case'];assert type(cases) is dict and set(cases)=={'discovery','normal'}
    assert all(type(n) is int and n>0 for n in cases.values()) and max(cases.values())==units
    assert value['accepted'] is (charge<=SIZE_CAP and units<=30000)
    rows=value['phase_timings'];assert type(rows) is list and len(rows)==len(SIZE_STAGES)
    for row,stage in zip(rows,SIZE_STAGES):
        assert type(row) is dict and set(row)=={'stage','seconds'} and type(row['stage']) is str and row['stage']==stage
        seconds=row['seconds'];assert type(seconds) is float and math.isfinite(seconds) and seconds>=0
    assert sum(row['seconds'] for row in rows)<=charge


def match_registration(actual,expected):
    assert type(actual) is dict and set(actual)==set(expected),'registration exact schema differs'
    assert canonical(actual)==canonical(expected),'registration declarations differ from fixed facts'


def check(reg):
    old,prior=previous();size=read(OUT/'size_admission.json')
    validate_size_timings(size)
    assert size['accepted'] is True and pin(POLICY.read_bytes())==POLICY_PIN
    graph=load(GRAPH,'_current_graph').inspect_imports();origins,leaves=runtime_leaves()
    paths=helpers()+[CHECKPOINT,SCOPE,CAPTURE,POLICY,REF_PROFILE,REF_CHECKPOINT,*sorted(leaves)]+[ROOT/row['path'] for row in graph['modules'].values()]
    fresh=pins(paths);assert fresh==size['input_pins'],'size input set or bytes drifted'
    assert graph==size['static_import_graph'] and origins==size['conditional_runtime_origins']
    migrated=migration();assert migrated==size['migration']
    parent=load(PARENT,'_packed_check_parent');assert parent.source()==old['source_pins']
    code=parent.transport();assert pin(code)==size['transport_pin']
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_normal.plan.json'),'0'*64]
    units=max(command_units_by_case(code).values());assert units==size['command_utf16_units']<=30000 and size['command_utf16_units_by_case']==command_units_by_case(code)
    cost=reg['registration_charged_seconds'];assert type(cost) is float and 0<=cost<=REGISTER_CAP
    inputs={**fresh,str(OUT/'size_admission.json'):pin((OUT/'size_admission.json').read_bytes())}
    expected=registration_value(old,prior,inputs,code,units,origins,migrated,cost,pin((OUT/'size_admission.json').read_bytes()),graph)
    assert size['output_bounds']==expected['output_bounds']
    match_registration(reg,expected)
    embedded=reopen(reg['embedded_artifacts']);assert embedded['transport']==code and embedded['command']==command
    return old,prior


def spent(extra=0,kind='static'):
    result=dict(static=read(OUT/'size_admission.json')['charged_seconds'],unittest=0.0)
    if (OUT/'registration.json').exists():result['static']+=read(OUT/'registration.json')['registration_charged_seconds']
    for p in OUT.glob('*.exit.json'):row=read(p);result[row['kind']]+=row['charged_seconds']
    result[kind]+=extra;return result


def verify_exit(name,reg):
    row=read(OUT/(name+'.exit.json'));assert row['accepted'] and row['registration_pin']==pin((OUT/'registration.json').read_bytes())
    for path,value in row['path_artifact_pins'].items():assert pin(Path(path).read_bytes())==value,path
    data=reopen(row['embedded_artifacts'])
    if name=='unittest':
        recovered=unit_payload(row,reg);assert recovered['complete_frames']
        unit=recovered['parsed']
        assert unit=={k:data[k] for k in unit} and data['unit_report']==dict(accepted=True,tests_run=25,failures=0,errors=0,skipped=0)
    if name=='pre_seal':
        assert data['findings']['must_fix_open']==[] and data['findings']['official_review'] is False
        assert data['findings']['helper_pins']==reg['helper_pins'] and data['findings']['unit_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes())
    if name=='profile_admission':assert data['admission']['profile_pin']==pin((OUT/'startup_profile.json').read_bytes())
    for field,value in flags().items():assert row[field] is value
    return row,data


def prereq(action,reg,after=False):
    required=PHASES[:PHASES.index(action)];assert {p.name for p in OUT.glob('*.exit.json')}=={n+'.exit.json' for n in required}
    expected=set(BASE_FILES)
    for name in required:expected.update(OUTPUTS[name]|{name+'.exit.json'});verify_exit(name,reg)
    if after:expected.update(OUTPUTS[action])
    assert {p.name for p in OUT.iterdir()}==expected


def parse_unit_frames(raw,reg):
    rows=[]
    for line in raw.splitlines(keepends=True):
        row=json.loads(line);assert canonical(row)+b'\n'==line;rows.append(row)
    assert len(rows)==2*len(reg['unit_nodes'])+2
    assert rows[0][0]=='admission' and rows[-1][0]=='report'
    admission=rows[0][1];assert admission==dict(nodes=reg['unit_nodes'],before_test_calls=True)
    sequence=rows[1:-1];expected=[]
    for name in reg['unit_nodes']:expected.extend([['test_start',name],['test_end',name]])
    assert sequence==expected
    report=rows[-1][1];assert set(report)=={'accepted','tests_run','failures','errors','skipped'} and report['tests_run']==len(reg['unit_nodes'])
    assert all(type(report[k]) is int and report[k]>=0 for k in ('tests_run','failures','errors','skipped'))
    assert report['accepted'] is (report['failures']==report['errors']==report['skipped']==0)
    return dict(unit_admission=admission,unit_report=report)


def unit_payload(row,reg):
    data=reopen(row['embedded_artifacts'])
    if 'streams' not in data:
        assert row['accepted'] is False and 'unit_admission' not in data and 'unit_report' not in data
        return dict(raw_streams_observed=False,complete_frames=False,parsed=None)
    streams=data['streams'];raws={}
    assert type(streams) is dict and set(streams)=={'returncode','error','stdout_pin','stderr_pin','process_observation'}
    assert type(streams['returncode']) is int or streams['returncode'] is None and row['accepted'] is False
    assert streams['error'] is None or type(streams['error']) is str
    for name,field,cap in (('unit_stdout','stdout_pin',65536),('unit_stderr','stderr_pin',16384)):
        if name in data:raw=data[name]
        else:
            path=row['external_streams'][name];raw=Path(path).read_bytes()
            assert pin(raw)==row['path_artifact_pins'][path]
        exact_pin(streams[field]);assert type(raw) is bytes and len(raw)<=cap and pin(raw)==streams[field];raws[name]=raw
    obs=streams['process_observation'];assert type(obs) is dict and set(obs)=={'bounded_drain','handle_closed','peak_working_set_bytes','cleanup'}
    assert type(obs['handle_closed']) is bool and type(obs['cleanup']) is list and all(type(v) is str for v in obs['cleanup'])
    assert obs['peak_working_set_bytes'] is None or type(obs['peak_working_set_bytes']) is int and obs['peak_working_set_bytes']>=0
    drain=obs['bounded_drain']
    if drain is None:assert row['accepted'] is False
    else:
        assert type(drain) is dict and set(drain)==set(('child_created','chunk_bytes','cleanup','direct_child_pid','killed','pipes_closed','reader_errors','reader_threads_terminal','stderr_cap','stderr_observed_bytes','stderr_truncated','stdout_cap','stdout_observed_bytes','stdout_truncated'))
        for name,value in (('stdout_cap',65536),('stderr_cap',16384),('chunk_bytes',4096)):assert type(drain[name]) is int and drain[name]==value
        for name in ('child_created','killed','pipes_closed','reader_threads_terminal','stdout_truncated','stderr_truncated'):assert type(drain[name]) is bool
        for name in ('reader_errors','cleanup'):assert type(drain[name]) is list and all(type(v) is str for v in drain[name])
        assert type(drain['direct_child_pid']) is int and drain['direct_child_pid']>0 or drain['direct_child_pid'] is None and not drain['child_created']
        for name,raw in (('stdout',raws['unit_stdout']),('stderr',raws['unit_stderr'])):
            assert type(drain[name+'_observed_bytes']) is int and drain[name+'_observed_bytes']>=len(raw)
            if not drain[name+'_truncated']:assert drain[name+'_observed_bytes']==len(raw)
    if row['accepted']:
        assert streams['returncode']==0 and streams['error'] is None and obs['handle_closed'] and not obs['cleanup']
        assert drain['child_created'] and drain['pipes_closed'] and drain['reader_threads_terminal']
        assert not any(drain[n] for n in ('killed','stdout_truncated','stderr_truncated','reader_errors','cleanup'))
    try:parsed=parse_unit_frames(raws['unit_stdout'],reg)
    except (AssertionError,ValueError,UnicodeDecodeError):
        assert row['accepted'] is False and 'unit_admission' not in data and 'unit_report' not in data
        return dict(raw_streams_observed=True,complete_frames=False,parsed=None)
    assert all(data[name]==value for name,value in parsed.items())
    return dict(raw_streams_observed=True,complete_frames=True,parsed=parsed)


def unit_child():
    import unittest
    reg=read(OUT/'registration.json');check(reg);module=load(TEST,'live_profile_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
    def flatten(s):return [n for c in s for n in flatten(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
    actual=flatten(suite);assert actual==reg['unit_nodes']
    def emit(row):sys.stdout.buffer.write(canonical(row)+b'\n');sys.stdout.buffer.flush()
    emit(['admission',dict(nodes=actual,before_test_calls=True)])
    class Witness(unittest.TextTestResult):
        def startTest(self,test):emit(['test_start',test.id()]);super().startTest(test)
        def stopTest(self,test):super().stopTest(test);emit(['test_end',test.id()])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Witness).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==25 and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    emit(['report',report])
    if not report['accepted']:raise SystemExit(1)


def register(started=None):
    if started is None:started=time.perf_counter()
    assert {p.name for p in OUT.iterdir()}=={'driver.py','import_policy.json','size_admission.json'}
    size=read(OUT/'size_admission.json');validate_size_timings(size)
    assert size['accepted'] and size['registration_max_bytes']<=FILE_CAPS['registration.json']
    old,prior=previous();parent=load(PARENT,'_packed_register_parent');assert parent.source()==old['source_pins']
    for path,value in size['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    code=parent.transport();assert pin(code)==size['transport_pin'];migrated=migration();assert migrated==size['migration']
    graph=load(GRAPH,'_packed_register_graph').inspect_imports();assert graph==size['static_import_graph']
    origins,leaves=runtime_leaves();assert origins==size['conditional_runtime_origins'],'size-to-register runtime origin drift'
    for p in leaves:assert pin(p.read_bytes())==size['input_pins'][str(p)],str(p)
    inputs={**size['input_pins'],str(OUT/'size_admission.json'):pin((OUT/'size_admission.json').read_bytes())}
    value=registration_value(old,prior,inputs,code,size['command_utf16_units'],origins,migrated,0.0,pin((OUT/'size_admission.json').read_bytes()),graph)
    assert size['output_bounds']==value['output_bounds']
    cost=time.perf_counter()-started;assert cost<=REGISTER_CAP;value['registration_charged_seconds']=cost
    assert len(canonical(value))<=size['registration_max_bytes'];save(OUT/'registration.json',value)
    print(canonical(dict(accepted=True,charge=cost,units=value['command_utf16_units'],inputs=value['effective_input_count'],helpers=len(value['helper_pins']))).decode())


def run(action):
    global _ACTIVE_EXIT
    _ACTIVE_EXIT=action+'.exit.json';started=time.perf_counter();target=OUT/_ACTIVE_EXIT;assert not target.exists()
    reg=read(OUT/'registration.json');cap=CAPS[action];kind='unittest' if action=='unittest' else 'static'
    accepted=False;error=None;objects={};raw_artifacts={};case=None
    try:
        check(reg);prereq(action,reg);budget=spent(cap,kind);assert budget[kind]<=reg['caps'][kind] and sum(budget.values())<=TOTAL_CAP
        space_for({});parent=load(PARENT,'_packed_phase_parent')
        if action=='unittest':
            capture=load(CAPTURE,'_packed_unit_capture')
            rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],cap-(time.perf_counter()-started)-.7)
            objects['streams']=dict(returncode=rc,error=why,stdout_pin=pin(out),stderr_pin=pin(err),process_observation=obs)
            raw_artifacts=dict(unit_stdout=embed(out),unit_stderr=embed(err))
            objects.update(parse_unit_frames(out,reg))
            assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup']
            drain=obs['bounded_drain'];assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['reader_errors'] and not drain['cleanup'] and not drain['killed'] and not drain['stdout_truncated'] and not drain['stderr_truncated']
            assert objects['unit_report']['accepted']
        elif action=='pre_seal':
            raw=sys.stdin.buffer.read(16385);assert len(raw)<=16384;summary=json.loads(raw);assert canonical(summary)==raw
            objects['findings']=summary
            assert summary['must_fix_open']==[] and summary['helper_pins']==reg['helper_pins'] and summary['official_review'] is False
            assert summary['registration_pin']==pin((OUT/'registration.json').read_bytes()) and summary['unit_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes())
            assert summary['checkpoint_script_pin']==pin(CHECKPOINT.read_bytes()) and summary['verified_input_pins']==reg['effective_input_count']
            objects['admission']=dict(accepted=True,authority=AUTHORITY,diagnostic_only=True,findings_pin=pin(raw),**flags())
        elif action in ('discovery','live'):
            case_name='discovery' if action=='discovery' else 'normal'
            assert len(parent.canonical(parent.manifest(case_name,parent.transport())))<=65536
            space_for({name:FILE_CAPS[name] for name in OUTPUTS[action]});parent.save=parent_save
            case=parent.one_case(case_name,cap-(time.perf_counter()-started));assert case['accepted']
            if action=='live':objects['audit_validation']=audit_matrix(parent,case)
        elif action=='profile_admission':
            profile=read(OUT/'startup_profile.json');assert pin((OUT/'startup_profile.json').read_bytes())['bytes']<=131072 and profile['bootstrap_pin']==reg['transport_pin']
            for path,value in profile['disk_file_observations'].items():assert pin(Path(path).read_bytes())==value,path
            objects['admission']=dict(accepted=True,authority=AUTHORITY,profile_pin=pin((OUT/'startup_profile.json').read_bytes()),transport_pin=reg['transport_pin'],helper_pins=reg['helper_pins'],
                reference_source=parent.REFERENCE.reference(),environment_pin=pin(canonical(parent.environment())),registration_pin=pin((OUT/'registration.json').read_bytes()),discovery_receipt_pin=pin((OUT/'probe_discovery.receipt.json').read_bytes()),**flags())
        else:
            row=read(OUT/'probe_normal.receipt.json');objects['report']=saved_report(parent,row)
            body={**objects['report'],'stages':[],'graph_frames':[],'census_frames':[]}
            assert len(canonical(body))<=6144
            assert len(canonical(objects['report']))<=len(base64.b64decode(row['stderr_raw_base64']))+len(canonical(body))+6<=38918
        check(reg);prereq(action,reg,after=True);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:160]
    charge=time.perf_counter()-started;usage=spent(charge,kind);accepted=accepted and charge<=cap and usage[kind]<=reg['caps'][kind] and sum(usage.values())<=TOTAL_CAP
    previous=reg['predecessor_charged_seconds'];cumulative={**previous,'static':previous['static']+usage['static'],'unittest':previous['unittest']+usage['unittest']}
    record=dict(accepted=accepted,authority=AUTHORITY,label=action,kind=kind,charged_seconds=charge,cap_seconds=cap,scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=38+sum(not read(p)['accepted'] for p in OUT.glob('*.exit.json'))+(not accepted),
        registration_pin=pin((OUT/'registration.json').read_bytes()),path_artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),embedded_artifacts={**packed(objects),**raw_artifacts},
        error=error,case_accepted=None if case is None else case['accepted'],all_unselected_events_verified=False,candidate_adopted=False,**flags())
    if action=='saved' and 'report' in record['embedded_artifacts']:
        metadata={**record,'embedded_artifacts':{}}
        if len(canonical(metadata))+256>8192 or len(canonical(record))>65536:
            accepted=False;record.update(accepted=False,error='packed_saved_archive_cap',prior_not_accepted_count=record['prior_not_accepted_count']+int(record['accepted']),
                proposed_derived_report_pin=pin(canonical(objects['report'])),embedded_artifacts={})
    if len(canonical(record))>FILE_CAPS.get(target.name,16384) and raw_artifacts:
        assert action=='unittest'
        space_for({'unit.stdout.raw':len(out),'unit.stderr.raw':len(err)})
        write_raw(OUT/'unit.stdout.raw',out);write_raw(OUT/'unit.stderr.raw',err)
        accepted=False;record.update(accepted=False,error='phase_archive_cap',prior_not_accepted_count=record['prior_not_accepted_count']+int(record['accepted']),
            original_proposed_record_pin=pin(canonical(record)),external_streams=dict(unit_stdout=str(OUT/'unit.stdout.raw'),unit_stderr=str(OUT/'unit.stderr.raw')),
            embedded_artifacts=packed(objects),path_artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()))
    save(target,record);print(canonical(dict(accepted=accepted,label=action,charge=charge,error=record['error'])).decode())
    if not accepted:raise SystemExit(1)


def size_admission(started=None):
    if started is None:started=time.perf_counter()
    timings=[];last_mark=started
    def mark(stage):
        nonlocal last_mark
        now=time.perf_counter();timings.append(dict(stage=stage,seconds=now-last_mark));last_mark=now
    assert {p.name for p in OUT.iterdir()}=={'driver.py','import_policy.json'}
    mark('prerun')
    for path in helpers()+[CHECKPOINT]:compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0)
    mark('compile_only');old,prior=previous();mark('predecessor_archive')
    migrated=migration();parent=load(PARENT,'_packed_size_parent');sources=parent.source();code=parent.transport()
    mark('migration_source_transport')
    assert pin(POLICY.read_bytes())==POLICY_PIN
    graph=load(GRAPH,'_packed_size_graph').inspect_imports();mark('import_graph')
    origins,leaves=runtime_leaves();mark('runtime_leaves')
    paths=helpers()+[CHECKPOINT,SCOPE,CAPTURE,POLICY,REF_PROFILE,REF_CHECKPOINT,*sorted(leaves)]+[ROOT/row['path'] for row in graph['modules'].values()]
    inputs=pins(paths);assert sources==old['source_pins'];mark('first_input_pins')
    plan=parent.manifest('discovery',code);assert plan['import_policy']==dict(path=str(POLICY),pin=POLICY_PIN)
    marker=b'\nimport os as _bootstrap_os\n';assert code.count(marker)==1;prefix=code.partition(marker)[0]
    original=CORE.read_bytes()+b'\n'+PROBE.read_bytes();before,body=original.split(b'\nimport builtins\n',1);intended=b'import builtins\n'+body
    lines=intended.decode().splitlines(keepends=True)
    for token in tokenize.tokenize(io.BytesIO(intended).readline):
        if token.type==tokenize.COMMENT:
            row,col=token.start;lines[row-1]=lines[row-1][:col]+' '*(token.end[1]-col)+lines[row-1][token.end[1]:]
    intended=''.join(lines).encode();calls=[n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode'];assert len(calls)==1
    decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(calls[0].args[0].value),131073)
    assert payload==intended and len(payload)<=131072 and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
    tokens=lambda raw:[(t.type,t.string) for t in tokenize.tokenize(io.BytesIO(raw).readline)]
    canonical_tokens=lambda raw:[(t.type,'' if t.type==tokenize.INDENT else t.string) for t in tokenize.tokenize(io.BytesIO(raw).readline)]
    assert tokens(prefix)!=tokens(before) and canonical_tokens(prefix)==canonical_tokens(before) and len(prefix)<len(before)
    compact=load(COMPACT,'_packed_size_oracle');assert compact.code_image(compile(prefix,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0))==compact.code_image(compile(before,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0))
    assert ast.dump(ast.parse(prefix))==ast.dump(ast.parse(before)) and prefix.count(b'\n')==before.count(b'\n')
    assert ast.dump(ast.parse(payload),include_attributes=True)==ast.dump(ast.parse(b'import builtins\n'+body),include_attributes=True)
    assert compile(payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)==compile(b'import builtins\n'+body,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    command=[EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/'probe_normal.plan.json'),'0'*64]
    units=max(command_units_by_case(code).values())
    mark('manifest_codec_command')
    placeholder=dict(bytes=262144,sha256='0'*64);probe_inputs={**inputs,str(OUT/'size_admission.json'):placeholder}
    candidate=registration_value(old,prior,probe_inputs,code,units,origins,migrated,1.2345678901234567,placeholder,graph)
    registration_max_bytes=len(canonical(candidate))+1024;assert registration_max_bytes<=FILE_CAPS['registration.json']
    packed_saved_max_bytes=4*((38918+2)//3)+8192;assert packed_saved_max_bytes<=FILE_CAPS['saved.exit.json']==65536
    mark('registration_candidate')
    assert pins(paths)==inputs and parent.source()==sources
    mark('final_input_source_bookend')
    record=dict(accepted=False,authority=AUTHORITY,kind='static',charged_seconds=0.0,cap_seconds=SIZE_CAP,phase_timings=timings,
        input_pins=inputs,migration=migrated,conditional_runtime_origins=origins,static_import_graph=graph,registration_max_bytes=registration_max_bytes,packed_saved_max_bytes=packed_saved_max_bytes,
        output_bounds=output_bounds(),transport_pin=pin(code),command_utf16_units=units,command_utf16_units_by_case=command_units_by_case(code),prefix_before_pin=pin(before),prefix_after_pin=pin(prefix),payload_pin=pin(payload),dictionary_pin=pin(prefix),
        prefix_tokens_equal=False,prefix_tokens_except_indent_equal=True,prefix_runtime_code_equal=True,prefix_ast_equal=True,prefix_lines_equal=True,prefix_exact_code_unchanged_claimed=False,
        payload_byte_equal=True,payload_position_ast_equal=True,payload_code_equal=True,unit_children_launched=0,cold_children_launched=0,all_unselected_events_verified=False,candidate_adopted=False,**flags())
    canonical(record);mark('serialization')
    charge=time.perf_counter()-started;accepted=charge<=SIZE_CAP and units<=30000
    assert all(row['seconds']>=0 for row in timings) and sum(row['seconds'] for row in timings)<=charge
    record.update(accepted=accepted,charged_seconds=charge)
    validate_size_timings(record)
    save(OUT/'size_admission.json',record)
    print(canonical(dict(accepted=accepted,charge=charge,units=units,registration_max_bytes=registration_max_bytes)).decode())
    if not accepted:raise SystemExit(1)


def runtime_leaves():
    import zlib, io, tokenize, ctypes.wintypes, secrets, subprocess, encodings.utf_16_le, copy, dis, unittest, unittest.mock, pickle, dataclasses, traceback, linecache, statistics, contextlib, inspect, logging, shutil, tempfile, random, math, collections, threading, struct
    runtime = Path(EXE).parent
    origins = {}
    paths = set()
    for name, module in sorted(tuple(sys.modules.items())):
        origin = getattr(getattr(module, '__spec__', None), 'origin', None)
        if type(origin) is str and origin in ('built-in', 'frozen'):
            origins[name] = dict(kind=origin)
            continue
        if type(origin) is not str:
            continue
        path = Path(origin).absolute()
        if not path.is_relative_to(runtime):
            continue
        assert path.is_file()
        paths.add(path)
        cache = getattr(module, '__cached__', None)
        cached = Path(cache).absolute() if type(cache) is str and Path(cache).is_file() else None
        if cached is not None:
            assert cached.is_relative_to(runtime)
            paths.add(cached)
        origins[name] = dict(kind='conditional_disk_leaf', origin=str(path), pin=pin(path.read_bytes()), cached=None if cached is None else dict(path=str(cached), pin=pin(cached.read_bytes())))
    return (origins, paths)

def audit_matrix(parent, row):
    return parent.POST.audit(parent, row)

def saved_report(parent, row):
    validation = audit_matrix(parent, row)
    child = row['result']['child_record']
    comparison = row['result']['profile_comparison']
    return dict(accepted=True, authority=AUTHORITY, metadata_only=True, diagnostic_accepted=True, audit_validation=validation, stages=row['result']['diagnostic']['stages'], graph_frames=row['result']['diagnostic']['graph_frames'], census_frames=row['result']['diagnostic']['census_frames'], memory_observation=row['memory_observation'], memory_guard=row['bounded_drain']['memory_guard'], memory_observation_source=row['memory_observation_source'], drain_reason=row['drain_reason'], runtime_phase_before_close=child['runtime_phase_before_close'], post_metrics=child['post_metrics'], import_profile_pin=comparison['observed_import_profile_pin'], expected_import_profile_pin=comparison['expected_import_profile_pin'], frozen_nfc9_import_profile_exact_match=comparison['frozen_nfc9_import_profile_exact_match'], reference_source=comparison['reference_source'], reference_context_pin=pin(canonical(row['result']['reference_context'])), all_unselected_events_verified=False, candidate_adopted=False, **flags())


def early(action):
    global _ACTIVE_EXIT
    _ACTIVE_EXIT=None;started=time.perf_counter();prerun=pins(helpers()+[CHECKPOINT,SCOPE,CAPTURE,REF_PROFILE,REF_CHECKPOINT])
    try:return size_admission(started) if action=='size' else register(started)
    except BaseException as error:
        path=OUT/('size_admission.json' if action=='size' else 'registration.json')
        if not path.exists():save(path,dict(accepted=False,authority=AUTHORITY,kind='static',charged_seconds=time.perf_counter()-started,error=repr(error),input_pins=prerun,**flags()))
        raise




def command_units_by_case(code):
    return {case:len(subprocess.list2cmdline([EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/('probe_'+case+'.plan.json')),'0'*64]).encode('utf-16-le'))//2 for case in ('discovery','normal')}

if __name__=='__main__':
    if sys.argv[1:]==['size_admission']:early('size')
    elif sys.argv[1:]==['register']:early('register')
    elif sys.argv[1:]==['unit_child']:unit_child()
    elif len(sys.argv)==2 and sys.argv[1] in PHASES:run(sys.argv[1])
    else:raise SystemExit('fixed packed finite2048 diagnostic only')
