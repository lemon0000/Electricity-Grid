"""Versioned normal/LIVE successor; frozen NFC9 reference bytes are not changed."""
import ast
import importlib.util
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('_frozen_exact14_constructor',ROOT/'experiments/staged_rts24_saved_fresh_post_return_transform_v2.py')
BASE=importlib.util.module_from_spec(spec);spec.loader.exec_module(BASE)
OUT='staged_rts24_saved_fresh_nfc_v10_non_authoritative'
REFERENCE='staged_rts24_saved_fresh_live_profile_reference_v1.py'
VALIDATOR='staged_rts24_saved_fresh_live_profile_validation_v1.py'


def replace(source,pairs):return BASE.replace(source,pairs)


def core(source):return replace(source,[('nfc_v9_non_authoritative','nfc_v10_non_authoritative',2)]).encode()
def probe(source):return replace(source,[('nfc_v9_non_authoritative','nfc_v10_non_authoritative',1)]).encode()


def parent(source):
    source=replace(source,[('nfc_v9_non_authoritative','nfc_v10_non_authoritative',1),('lease_v36.py','lease_v37.py',1),('probe_v34.py','probe_v35.py',1),
        ('staged_rts24_saved_fresh_post_return_validation_v1.py',VALIDATOR,1),
        ("    if case not in ('discovery','import_discovery'):\n        admitted=json.loads((OUT/'import_admission.json').read_bytes());assert admitted['accepted'] is True and admitted['transport_pin']==pin(code)",
         "    if case=='normal':\n        from types import SimpleNamespace\n        admitted,_=REFERENCE.admission(SimpleNamespace(**globals()),code)\n        import_profile=admitted['reference_source']['reference']\n    elif case not in ('discovery','import_discovery'):\n        admitted=json.loads((OUT/'import_admission.json').read_bytes());assert admitted['accepted'] is True and admitted['transport_pin']==pin(code)",1),
        ("    try:\n        process=subprocess.Popen(argv,", "    reference_before=reference_after=None\n    try:\n        if case=='normal':\n            from types import SimpleNamespace\n            reference_before=REFERENCE.context(SimpleNamespace(**globals()),code,plan,actual)\n        process=subprocess.Popen(argv,",1),
        ("if case=='import_discovery':assert error in", "if case in ('import_discovery','normal'):assert error in",1),
        ("if case=='import_discovery' and primary is None:","if case in ('import_discovery','normal') and primary is None:",1),
        ("    record=dict(authority='DRAFT_NONAUTHORITATIVE',case=case,accepted=", "    if case=='normal' and reference_before is not None:\n        try:\n            from types import SimpleNamespace\n            reference_after=REFERENCE.context(SimpleNamespace(**globals()),code,plan,actual)\n            assert reference_after==reference_before\n        except BaseException as error:cleanup.append('reference_bookend:'+type(error).__name__)\n    record=dict(reference_before=reference_before,reference_after=reference_after,authority='DRAFT_NONAUTHORITATIVE',case=case,accepted=",1),
        ("if case in ('discovery','import_discovery'): save(OUT/", "if case in ('discovery','import_discovery','normal'): save(OUT/",1)])
    source+="\nREFERENCE=load(ROOT/'experiments/"+REFERENCE+"','_live_frozen_profile_reference')\n"
    return source.encode()


def validator(source):
    source=replace(source,[("record['runtime_phase_before_close']=='OBSERVED'","record['runtime_phase_before_close']=='LIVE'",1),
        ("record['runtime_was_live'] is False","record['runtime_was_live'] is True",1),
        ("terminal_mode='post_return_observed_closed'","terminal_mode='post_return_live_closed'",1),
        ('observed_before_close=True','live_before_close=True',1),
        ("record['case']=='import_discovery'","record['case']=='normal'",1),
        ("assert case=='import_discovery' and not writer_errors","assert case=='normal' and not writer_errors",1),
        ("    return dict(accepted=True,terminal_mode='post_return_live_closed'", "    comparison=parent.REFERENCE.compare_profile(record['import_profile'])\n    assert comparison['frozen_nfc9_import_profile_exact_match'] is True\n    assert comparison['expected_import_profile_pin']==comparison['observed_import_profile_pin']\n    return dict(expected_import_profile_pin=comparison['expected_import_profile_pin'],observed_import_profile_pin=comparison['observed_import_profile_pin'],frozen_nfc9_import_profile_exact_match=True,accepted=True,terminal_mode='post_return_live_closed'",1),
        ("    parsed=parse(parent,stderr)\n    record=None;witness=False;complete=False", "    manifest_raw=(parent.OUT/'probe_normal.plan.json').read_bytes();plan=json.loads(manifest_raw)\n    assert argv[-2:]==[str(parent.OUT/'probe_normal.plan.json'),parent.pin(manifest_raw)['sha256']]\n    reference_context=parent.REFERENCE.context(parent,code,plan,manifest_raw)\n    parsed=parse(parent,stderr)\n    record=None;witness=False;complete=False",1),
        ("    return dict(child_record=record,diagnostic=parsed", "    comparison=parent.REFERENCE.compare_profile(None if record is None else record['import_profile'])\n    return dict(reference_context=reference_context,profile_comparison=comparison,child_record=record,diagnostic=parsed",1),
        ("    assert decode(parent,stdout)==record\n", "    assert decode(parent,stdout)==record\n    manifest_raw=(parent.OUT/'probe_normal.plan.json').read_bytes();plan=json.loads(manifest_raw)\n    assert parent.pin(manifest_raw)==row['plan_pin']==row['expected_manifest_pin']\n    context=parent.REFERENCE.context(parent,parent.transport(),plan,manifest_raw)\n    assert row['reference_before']==row['reference_after']==r['reference_context']==context\n    assert row['transport_pin']==context['transport_pin']\n    assert r['profile_comparison']==parent.REFERENCE.compare_profile(record['import_profile'])\n",1)])
    return source.encode()


def driver(source):
    source=replace(source,[('lease_v36.py','lease_v37.py',1),('probe_v34.py','probe_v35.py',1),('parent_v33.py','parent_v34.py',1),
        ('test_staged_rts24_saved_fresh_post_return_v2.py','test_staged_rts24_saved_fresh_live_profile_v1.py',1),
        ('staged_rts24_saved_fresh_post_return_checkpoint_v2.py','staged_rts24_saved_fresh_live_profile_checkpoint_v1.py',1),
        ('staged_rts24_saved_fresh_post_return_transform_v2.py','staged_rts24_saved_fresh_live_profile_transform_v1.py',1),
        ('staged_deliverability_c_saved_fresh_post_return_admission_scope_v2.md','staged_deliverability_c_saved_fresh_post_return_admission_scope_v3.md',1),
        ('staged_rts24_saved_fresh_post_return_validation_v1.py',VALIDATOR,1),
        ("LEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative'", "NFC8=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v8_non_authoritative'\nLEDGER=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative'\nREFERENCE=ROOT/'experiments/"+REFERENCE+"'\nREF_PROFILE=LEDGER/'import_profile.json'\nREF_CHECKPOINT=LEDGER/'checkpoint.json'",1),
        ("LEDGER_SHA='39a8b3ac3e5ff68a5810b2d2809d3c16ca292b0ef0f76951a10d957206cd686e'", "LEDGER_SHA='5fb9c83a6ec9e7933e684a7f4ca2491fa52d9d7e1a6a8b7cc3740d9eb30428da'",1),
        ("prior['accepted'] is True and prior['diagnostic_accepted'] is False", "prior['accepted'] is True and prior['diagnostic_accepted'] is True",1),
        ("prior['all_cumulative_total_seconds']==898.7101957000225 and prior['package_charged_seconds']==32.24230059997353", "prior['all_cumulative_total_seconds']==937.488786600002 and prior['package_charged_seconds']==38.77859089997946",1),
        ("    assert prior['acceptance_scope']=='rejection_metadata_only' and not (LEDGER/'saved.exit.json').exists()\n    failed=read(LEDGER/'probe_import_discovery.receipt.json')['result']['child_record']\n    assert failed['primary']['message']=='fixed thirteen adapter function roots required' and failed['boundary_report']['machinery_authenticated_stage']==2", "    assert prior['acceptance_scope']=='packed_metadata_and_post_return_diagnostic_only' and prior['runtime_phase_before_close']=='OBSERVED'\n    assert prior['audit_validation']['terminal_mode']=='post_return_observed_closed'",1),
        ('len(list(LEDGER.iterdir()))==15 and sum(p.stat().st_size for p in LEDGER.iterdir())==1191896','len(list(LEDGER.iterdir()))==17 and sum(p.stat().st_size for p in LEDGER.iterdir())==2285992',1),
        ('[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,NFC7,LEDGER]','[trace_root,MEMO,UNIT_LEDGER,PREP_LEDGER,NFC6,NFC7,NFC8,LEDGER]',1),
        ('len(archive)==88','len(archive)==105',1),('==6350636','==8636628',1),
        ("    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1099", "    for path,value in read(NFC8/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1099\n    for path,value in read(LEDGER/'registration.json')['input_pins'].items():\n        if path in result:assert result[path]==value,path\n        else:result[path]=value\n    assert len(result)==1110",1),
        ('CAPS=dict(unittest=16','CAPS=dict(unittest=20',1),('UNIT_CAP=16;TOTAL_CAP=81','UNIT_CAP=20;TOTAL_CAP=85',1),
        ("'registration.json':786432","'registration.json':1048576",1),("'unittest.exit.json':32768","'unittest.exit.json':65536",1),
        ('unit_tests_planned=21','unit_tests_planned=25',1),('tests_run=21,failures=0','tests_run=25,failures=0',1),('result.testsRun==21','result.testsRun==25',1),
        ("load(TEST,'post_return_tests')","load(TEST,'live_profile_tests')",1),
        ("ROOT/'experiments/"+VALIDATOR+"',Path(__file__).absolute()]","ROOT/'experiments/"+VALIDATOR+"',REFERENCE,Path(__file__).absolute()]",1),
        ('[CHECKPOINT,SCOPE,CAPTURE,POLICY,','[CHECKPOINT,SCOPE,CAPTURE,POLICY,REF_PROFILE,REF_CHECKPOINT,',2),
        ('helpers()+[CHECKPOINT,SCOPE,CAPTURE])','helpers()+[CHECKPOINT,SCOPE,CAPTURE,REF_PROFILE,REF_CHECKPOINT])',1),
        ("'probe_import_discovery.plan.json'","'probe_normal.plan.json'",5),
        ("'probe_import_discovery.receipt.json'","'probe_normal.receipt.json'",3),
        ("audit_prefix={'probe_normal.plan.json','probe_normal.receipt.json','import_profile.json'}","audit_prefix={'probe_normal.plan.json','probe_normal.receipt.json'}",1),
        ("else 'import_discovery'","else 'normal'",1),
        ('<=4096','<=6144',1),('<= 4096','<= 6144',1),('6<=36870','6<=38918',1),('((36870+2)//3)','((38918+2)//3)',1)])
    source=source.replace("'audit_prefix'","'live'").replace('audit_prefix=30','live=30').replace('audit_prefix={','live={')
    source=replace(source,[("                environment_pin=pin(canonical(parent.environment()))", "                reference_source=parent.REFERENCE.reference(),environment_pin=pin(canonical(parent.environment()))",1)])
    source=replace(source,[("units=len(subprocess.list2cmdline(command).encode('utf-16-le'))//2",'units=max(command_units_by_case(code).values())',2),
        ('command_utf16_units=units,','command_utf16_units=units,command_utf16_units_by_case=command_units_by_case(code),',2),
        ("assert units==size['command_utf16_units']<=30000", "assert units==size['command_utf16_units']<=30000 and size['command_utf16_units_by_case']==command_units_by_case(code)",1),
        ("    units=value['command_utf16_units'];assert type(units) is int and units>0", "    units=value['command_utf16_units'];assert type(units) is int and units>0\n    cases=value['command_utf16_units_by_case'];assert type(cases) is dict and set(cases)=={'discovery','normal'}\n    assert all(type(n) is int and n>0 for n in cases.values()) and max(cases.values())==units",1)])
    source+='''\n\ndef command_units_by_case(code):
    return {case:len(subprocess.list2cmdline([EXE,'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(OUT/('probe_'+case+'.plan.json')),'0'*64]).encode('utf-16-le'))//2 for case in ('discovery','normal')}
'''
    # Define helpers before the controller CLI dispatch executes.
    tail=source.index('\n\ndef command_units_by_case(code):');helper_tail=source[tail:];source=source[:tail]
    cli=source.index("if __name__=='__main__':");source=source[:cli]+helper_tail+'\n'+source[cli:]
    raw_nodes='''def nodes():
    paths=(ROOT/'tests/test_staged_rts24_saved_fresh_none_census2048_v1.py',NATIVE_TEST,ROOT/'tests/test_staged_rts24_saved_fresh_post_return_v2.py',TEST)
    classes=('None2048Tests','NativeImageTests','PostReturnTests','LiveProfileTests');names=[]
    for path,name in zip(paths,classes):
        cls=next(n for n in ast.parse(path.read_bytes()).body if type(n) is ast.ClassDef and n.name==name)
        names.extend(n.name for n in cls.body if type(n) is ast.FunctionDef and n.name.startswith('test_'))
    assert len(names)==len(set(names))==25
    return sorted('live_profile_tests.LiveProfileTests.'+name for name in names)
'''
    raw_migration='''def migration():
    constructor=load(CONSTRUCTOR,'_normal_live_constructor')
    rows=(('core',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py',CORE),
        ('probe',ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py',PROBE),
        ('parent',ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py',PARENT),
        ('validator',ROOT/'experiments/staged_rts24_saved_fresh_post_return_validation_v1.py',ROOT/'experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py'))
    for name,before,after in rows:assert getattr(constructor,name)(before.read_text(encoding='utf-8'))==after.read_bytes(),name
    old_reg=read(LEDGER/'registration.json')
    for path in (HELPER,ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py',MEMORY):assert pin(path.read_bytes())==old_reg['helper_pins'][str(path)]
    reference=load(REFERENCE,'_normal_live_reference').reference()
    assert reference['reference']['path']==str(REF_PROFILE) and reference['source_checkpoint']['pin']==pin(REF_CHECKPOINT.read_bytes())
    return dict(versioned_normal_live=True,constructor_exact=True,helper_and_graph_reader_unchanged=True,
        reference_source=reference,normal_single_receipt=True,legacy_parent_frozen=True,source49_unchanged=True,
        scientific_acceptance_threshold_change=False,diagnostic_only=True)
'''
    raw_matrix='''def audit_matrix(parent,row):
    return parent.POST.audit(parent,row)
'''
    raw_saved='''def saved_report(parent,row):
    validation=audit_matrix(parent,row);child=row['result']['child_record'];comparison=row['result']['profile_comparison']
    return dict(accepted=True,authority=AUTHORITY,metadata_only=True,diagnostic_accepted=True,audit_validation=validation,
        stages=row['result']['diagnostic']['stages'],graph_frames=row['result']['diagnostic']['graph_frames'],census_frames=row['result']['diagnostic']['census_frames'],
        memory_observation=row['memory_observation'],memory_guard=row['bounded_drain']['memory_guard'],memory_observation_source=row['memory_observation_source'],drain_reason=row['drain_reason'],
        runtime_phase_before_close=child['runtime_phase_before_close'],post_metrics=child['post_metrics'],import_profile_pin=comparison['observed_import_profile_pin'],
        expected_import_profile_pin=comparison['expected_import_profile_pin'],frozen_nfc9_import_profile_exact_match=comparison['frozen_nfc9_import_profile_exact_match'],
        reference_source=comparison['reference_source'],reference_context_pin=pin(canonical(row['result']['reference_context'])),
        all_unselected_events_verified=False,candidate_adopted=False,**flags())
'''
    def bounds(node):
        raw=ast.unparse(node)
        raw=raw.replace("terminal_mode='post_return_observed_closed'","terminal_mode='post_return_live_closed'")
        raw=raw.replace('observed_before_close=True','live_before_close=True').replace("runtime_phase_before_close='OBSERVED'","runtime_phase_before_close='LIVE'")
        marker='body_bytes = len(canonical(body))'
        assert raw.count(marker)==1
        extra="reference = load(REFERENCE, '_live_size_reference').reference()\n    expected = dict(bytes=1048576, sha256='0' * 64)\n    body['audit_validation'].update(expected_import_profile_pin=expected, observed_import_profile_pin=expected, frozen_nfc9_import_profile_exact_match=True)\n    body.update(expected_import_profile_pin=expected, frozen_nfc9_import_profile_exact_match=True, reference_source=reference, reference_context_pin=expected)\n    "+marker
        raw=raw.replace(marker,extra)
        return ast.parse(raw).body[0]
    updates={name:(lambda n,raw=raw:ast.parse(raw).body[0]) for name,raw in (('nodes',raw_nodes),('migration',raw_migration),('audit_matrix',raw_matrix),('saved_report',raw_saved))}
    updates['output_bounds']=bounds
    return BASE.BASE.edit_functions(source,updates).encode()


def checkpoint(source):
    source=replace(source,[('nfc_v9_non_authoritative','nfc_v10_non_authoritative',1),('unit_tests=21','unit_tests=25',1),
        ('probe_import_discovery.receipt.json','probe_normal.receipt.json',2),
        ("saved=driver.reopen(rows['saved']['embedded_artifacts'])['report'];assert saved['diagnostic_accepted'] and saved['audit_validation']==validation", "replay=verified_saved_replay(driver,parent,receipt,rows['saved']);saved=replay\n        assert saved['diagnostic_accepted'] and saved['audit_validation']==validation",1),
        ("import_profile_pin=pin((OUT/'import_profile.json').read_bytes())", "import_profile_pin=replay['import_profile_pin'],expected_import_profile_pin=replay['expected_import_profile_pin'],frozen_nfc9_import_profile_exact_match=replay['frozen_nfc9_import_profile_exact_match'],reference_source=replay['reference_source'],reference_context_pin=replay['reference_context_pin']",1),
        ('prior_archive_files=88,prior_archive_bytes=6350636','prior_archive_files=105,prior_archive_bytes=8636628',1),
        ('packed_metadata_and_post_return_diagnostic_only','packed_metadata_and_profile_matched_live_diagnostic_only',1)])
    source=replace(source,[("def main():", "def verified_saved_replay(driver,parent,receipt,row):\n    saved=driver.reopen(row['embedded_artifacts'])['report'];replay=driver.saved_report(parent,receipt)\n    assert canonical(saved)==canonical(replay),'complete saved replay differs'\n    return replay\n\n\ndef main():",1)])
    return source.encode()


def create():
    pairs=(('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v37.py'),
        ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v35.py'),
        ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py'),
        ('validator','experiments/staged_rts24_saved_fresh_post_return_validation_v1.py','experiments/'+VALIDATOR),
        ('driver','results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative/driver.py','results/tables/'+OUT+'/driver.py'),
        ('checkpoint','experiments/staged_rts24_saved_fresh_post_return_checkpoint_v2.py','experiments/staged_rts24_saved_fresh_live_profile_checkpoint_v1.py'))
    out=ROOT/'results/tables'/OUT;out.mkdir(exist_ok=True)
    for name,before,after in pairs:
        raw=globals()[name]((ROOT/before).read_text(encoding='utf-8'));compile(raw,after,'exec',dont_inherit=True,optimize=0)
        p=ROOT/after
        if p.exists():assert p.read_bytes()==raw
        else:p.write_bytes(raw)
    policy=out/'import_policy.json'
    if not policy.exists():policy.write_bytes((ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative/import_policy.json').read_bytes())
    print('Created normal/LIVE draft successors')


if __name__=='__main__':create()
