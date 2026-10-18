"""Build a fresh diagnostic successor; preserve failed entry05 bytes."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P = HERE.parent/'validation_path_optimization_01'
prior, target = P/'entry_revision_05', P/'entry_revision_06'
raw = (prior/'package_manifest_v1.json').read_bytes()
assert sha256(raw).hexdigest() == 'a6eba4f2921b51dcf105cf9dbf4373464b5acef94097a62593f906c3f83cb1cc'
members = json.loads(raw)['files_sha256']
assert all(sha256((prior/name).read_bytes()).hexdigest() == pin for name,pin in members.items())
old_test = REPO/'tests/test_h1_guarded_common_slice_development_v1.py'
assert sha256(old_test.read_bytes()).hexdigest() == '9215b1e97e750abe730c02c07450467ef1149d1cad214d4df10fd0b4417b5f39'


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


old_observer = '''@pytest.fixture(scope='session',autouse=True)
def diagnostic_stack_observer(tmp_path_factory):
    assert_initial_imports()
    # No profiler or frame callback changes any numerical/identity dispatch.
    with (tmp_path_factory.getbasetemp()/'stack_samples.log').open('x',encoding='utf-8') as stream:
        faulthandler.dump_traceback_later(60,repeat=True,file=stream)
        try:yield
        finally:faulthandler.cancel_dump_traceback_later()
'''
new_observer = '''@pytest.fixture(scope='session',autouse=True)
def diagnostic_stack_observer(tmp_path_factory,request):
    assert_initial_imports()
    assert not request.config.pluginmanager.has_plugin('faulthandler')
    assert not faulthandler.is_enabled()
    root=tmp_path_factory.getbasetemp()
    with observe_owner_stack(root/'stack_samples.jsonl') as receipt:
        yield
    receipt.update(pytest_faulthandler_plugin_loaded=False,
        fatal_handler_enabled_at_setup=False)
    with (root/'stack_observer_receipt.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)
'''
test = replace_once(old_test.read_text(encoding='utf-8'), old_observer, new_observer)
test = replace_once(test, 'import pytest\n',
    'import pytest\nfrom tests.h1_gil_stack_observer_development_v1 import observe_owner_stack\n')
new_test = REPO/'tests/test_h1_guarded_common_slice_development_v2.py'
with new_test.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(test)

monitor = (P/'run_bounded_configured_entry_v4.py').read_text(encoding='utf-8')
assert sha256((P/'run_bounded_configured_entry_v4.py').read_bytes()).hexdigest() == \
    'f35732e7e1fade7e3053fc6be02b6b69a6984f6209b5bfd4ea36fce33bf4b65e'
for old,new in (('entry_revision_05','entry_revision_06'), ('unit_checks_03','unit_checks_04'),
    ('h1_cs01_non_authoritative','h1_cs02_non_authoritative'),
    ('common_slice_01','common_slice_02'),
    ('test_h1_guarded_common_slice_development_v1.py','test_h1_guarded_common_slice_development_v2.py')):
    monitor = monitor.replace(old,new)
old_role = '''    if (mode!='parse_path' or child_label!='common_slice_02'
            or targets!=['tests/test_h1_guarded_common_slice_development_v2.py']):
        raise ValueError('exact single bounded common-slice role required')
    if SLICE_BASE.exists():raise ValueError('fresh short diagnostic root required; preserve old inputs')'''
new_role = '''    slice_role=(mode=='parse_path' and child_label=='common_slice_02'
        and targets==['tests/test_h1_guarded_common_slice_development_v2.py'])
    smoke_role=(mode=='parse_path' and child_label=='sampler_smoke_01'
        and targets==['tests/test_h1_gil_stack_observer_development_v1.py'])
    if not slice_role and not smoke_role:
        raise ValueError('exact single bounded common-slice or sampler-smoke role required')
    if smoke_role and (limit>60 or ram>512*1024**2 or storage_cap>64*1024**2):
        raise ValueError('bounded sampler-smoke limits exceeded')
    if slice_role and SLICE_BASE.exists():
        raise ValueError('fresh short diagnostic root required; preserve old inputs')'''
monitor = replace_once(monitor, old_role, new_role)
monitor = replace_once(monitor, "([SLICE_BASE] if kind=='pytest' else [])",
    "([SLICE_BASE] if kind=='pytest' and slice_role else [])")
new_monitor = P/'run_bounded_configured_entry_v5.py'
with new_monitor.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(monitor)
monitor_pin = sha256(new_monitor.read_bytes()).hexdigest()

unit = (REPO/'tests/test_h1_common_slice_monitor_development_v1.py').read_text(encoding='utf-8')
unit = unit.replace('run_bounded_configured_entry_v4.py','run_bounded_configured_entry_v5.py')
unit = unit.replace('entry_revision_05','entry_revision_06').replace('unit_checks_03','unit_checks_04')
unit = unit.replace('common_slice_01','common_slice_02').replace('h1_cs01_non_authoritative','h1_cs02_non_authoritative')
unit = unit.replace('test_h1_guarded_common_slice_development_v1.py','test_h1_guarded_common_slice_development_v2.py')
unit,n = re.subn(r"EXPECTED_SHA='[0-9a-f]{64}'", "EXPECTED_SHA='"+monitor_pin+"'", unit)
assert n == 1
unit += '''

def test_explicit_sampler_smoke_role_has_only_two_owned_storage_roots(tmp_path):
    here,entry,monitor,launcher=fixture_entry(tmp_path,'pass\\n')
    done=run(here,monitor,launcher,child='sampler_smoke_01',
        targets=['tests/test_h1_gil_stack_observer_development_v1.py'])
    assert done.returncode==0,done.stdout+done.stderr
    request=json.loads((here/'owned_unit_outer/request.json').read_bytes())
    assert len(request['storage_roots'])==2
'''
new_unit = REPO/'tests/test_h1_common_slice_monitor_development_v2.py'
with new_unit.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(unit)

target.mkdir(exist_ok=False)
for name in (*members,'launch_validation.py'):
    (target/name).write_bytes((prior/name).read_bytes())
(target/'entry05_predecessor_package_manifest.json').write_bytes(raw)
entry_path = target/'validation_entry.py'
entry = entry_path.read_text(encoding='utf-8').replace(
    'test_h1_guarded_common_slice_development_v1.py','test_h1_guarded_common_slice_development_v2.py')
entry = entry.replace('h1_cs01_non_authoritative','h1_cs02_non_authoritative')
entry = replace_once(entry, '    allowed={\n',
    "    allowed={\n        'tests/test_h1_gil_stack_observer_development_v1.py',\n")
old_call = """                    status=int(pytest.main(['-q','-s','-p','no:cacheprovider','--import-mode=importlib','--basetemp',str(basetemp),*targets],
                        plugins=[Plugin(window,receipts,result),Admission(interpreter_policy)]))"""
new_call = """                    diagnostic=targets in (
                        ['tests/test_h1_guarded_common_slice_development_v2.py'],
                        ['tests/test_h1_gil_stack_observer_development_v1.py'])
                    selected_plugins=[Plugin(window,receipts,result),Admission(interpreter_policy)]
                    if diagnostic:
                        class DiagnosticFlags:
                            def pytest_configure(self,config):
                                import faulthandler
                                if config.pluginmanager.has_plugin('faulthandler') or faulthandler.is_enabled():
                                    raise ValueError('diagnostic faulthandler plugin/fatal handler must be disabled')
                                result['diagnostic_faulthandler_plugin_absent']=True
                                result['diagnostic_fatal_handler_enabled_at_configure']=False
                        selected_plugins.append(DiagnosticFlags())
                    diagnostic_flags=['-p','no:faulthandler'] if diagnostic else []
                    result['diagnostic_pytest_flags']=diagnostic_flags
                    status=int(pytest.main(['-q','-s','-p','no:cacheprovider',*diagnostic_flags,
                        '--import-mode=importlib','--basetemp',str(basetemp),*targets],plugins=selected_plugins))"""
entry = replace_once(entry, old_call, new_call)
entry_path.write_text(entry, encoding='utf-8', newline='\n')
closure_path = target/'test_closure_v1.json'
closure = json.loads(closure_path.read_bytes())
for path in (new_test, new_unit, REPO/'tests/h1_gil_stack_observer_development_v1.py',
        REPO/'tests/test_h1_gil_stack_observer_development_v1.py'):
    closure['files_sha256'][path.relative_to(REPO).as_posix()] = sha256(path.read_bytes()).hexdigest()
closure_path.write_text(json.dumps(closure, indent=2)+'\n', encoding='utf-8', newline='\n')
new_members = {name:sha256((target/name).read_bytes()).hexdigest()
    for name in (*members,'entry05_predecessor_package_manifest.json')}
manifest = dict(schema='h1_configured_validation_package_development_v1',files_sha256=new_members,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False)
manifest_raw = (json.dumps(manifest,indent=2)+'\n').encode()
manifest_pin = sha256(manifest_raw).hexdigest()
(target/'package_manifest_v1.json').write_bytes(manifest_raw)
launcher = target/'launch_validation.py'
launch,n = re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+manifest_pin+"'",
    launcher.read_text(encoding='utf-8'))
assert n == 1
launcher.write_text(launch,encoding='utf-8',newline='\n')
plan = dict(status='DRAFT_NONAUTHORITATIVE', package_manifest_sha256=manifest_pin,
    code_files=149,test_files=len(closure['files_sha256']),
    purpose='Integrate Python sampler and target-specific disabled C fatal plugin; check helpers, exact monitor roles and tiny configured sampler routing before any next slice',
    predecessor_failed_package_sha256=sha256(raw).hexdigest(),
    failed_attempt_preserved='configured_entry_05_common_slice_monitor_01 and D:/h1_cs01_non_authoritative',
    changes=['versioned test uses Python sampler','target-specific no:faulthandler plus configure/setup assertions',
        'fresh short root D:/h1_cs02_non_authoritative','bounded explicit sampler-smoke role'],
    monitor_sha256=monitor_pin, unit_role=['unit','parse','unit_checks_04'],
    unit_limits=dict(count=1,wall_seconds=120,sampled_rss_mib=512,storage_mib=64),
    smoke_role=['pytest','parse_path','sampler_smoke_01','tests/test_h1_gil_stack_observer_development_v1.py'],
    smoke_limits=dict(count=1,wall_seconds=60,sampled_rss_mib=512,storage_mib=64),
    fresh_slice_started=False, fresh_slice_launch_admitted=False,
    next_condition='Review stable-read cost candidate before deciding the next bounded numerical diagnostic; no new long chain',
    full_hour0_chain_passed=False,official_review_verdict=None,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'python_sampler_entry_plan_01.json').open('x',encoding='utf-8') as stream:
    json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=manifest_pin,monitor_sha256=monitor_pin,
    members=len(new_members),test_files=len(closure['files_sha256']))),flush=True)
