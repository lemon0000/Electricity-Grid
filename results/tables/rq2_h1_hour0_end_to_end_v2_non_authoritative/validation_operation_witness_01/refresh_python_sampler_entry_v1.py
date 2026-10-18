"""Narrow the IO test seam after a preserved configured-smoke failure."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
P = HERE.parent/'validation_path_optimization_01'
entry = P/'entry_revision_06'
manifest_path = entry/'package_manifest_v1.json'
old = manifest_path.read_bytes()
assert sha256(old).hexdigest() == '240bec2bf100ba8e365c04f31be3d39726eecc00303c769fce8b889753d2cb8c'
assert (entry/'unit_checks_04/tested_bytes/package_manifest_v1.json').read_bytes() == old
prior = json.loads(old)['files_sha256']
assert all(sha256((entry/name).read_bytes()).hexdigest() == pin for name,pin in prior.items())
(entry/'entry06_pre_io_fixture_fix_package_manifest.json').write_bytes(old)
test_path = REPO/'tests/test_h1_gil_stack_observer_development_v1.py'
closure_path = entry/'test_closure_v1.json'
closure = json.loads(closure_path.read_bytes())
closure['files_sha256'][test_path.relative_to(REPO).as_posix()] = sha256(test_path.read_bytes()).hexdigest()
closure_path.write_text(json.dumps(closure,indent=2)+'\n',encoding='utf-8',newline='\n')
names = [*prior,'entry06_pre_io_fixture_fix_package_manifest.json']
members = {name:sha256((entry/name).read_bytes()).hexdigest() for name in names}
raw = (json.dumps(dict(schema='h1_configured_validation_package_development_v1',
    files_sha256=members,formal_result=False,formal_execution_ready=False,
    native_execution_authorized=False),indent=2)+'\n').encode()
pin = sha256(raw).hexdigest()
manifest_path.write_bytes(raw)
launcher = entry/'launch_validation.py'
text,n = re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'", "MANIFEST_SHA='"+pin+"'", launcher.read_text(encoding='utf-8'))
assert n == 1
launcher.write_text(text,encoding='utf-8',newline='\n')
monitor = (P/'run_bounded_configured_entry_v5.py').read_text(encoding='utf-8')
assert monitor.count('unit_checks_04') == monitor.count('sampler_smoke_01') == 1
monitor = monitor.replace('unit_checks_04','unit_checks_05').replace('sampler_smoke_01','sampler_smoke_02')
new_monitor = P/'run_bounded_configured_entry_v6.py'
with new_monitor.open('x',encoding='utf-8',newline='\n') as stream:
    stream.write(monitor)
plan = json.loads((HERE/'python_sampler_entry_plan_01.json').read_bytes())
plan.update(package_manifest_sha256=pin,pre_io_fixture_fix_manifest_sha256=sha256(old).hexdigest(),
    monitor_sha256=sha256(new_monitor.read_bytes()).hexdigest(),
    monitor='run_bounded_configured_entry_v6.py',
    monitor_mechanical_delta='v5 control flow unchanged; only two fresh unit/smoke attempt labels renamed',
    unit_role=['unit','parse','unit_checks_05'],
    smoke_role=['pytest','parse_path','sampler_smoke_02','tests/test_h1_gil_stack_observer_development_v1.py'],
    preserved_failed_smoke='sampler_smoke_01:5 pass/1 fail/15 errors from process-global Path.open fault injection affecting receipt generation; output-only test seam repaired',
    implementation_helper_unchanged=True)
with (HERE/'python_sampler_entry_plan_02.json').open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=pin,members=len(members),
    monitor_sha256=sha256(new_monitor.read_bytes()).hexdigest())),flush=True)
