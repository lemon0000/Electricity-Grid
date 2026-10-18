"""Freeze one evidence-producing diagnostic, including the original dependency entry."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3];E=HERE.parent
ENTRY=E/'validation_path_optimization_01/entry_revision_07'
manifest=json.loads((ENTRY/'package_manifest_v1.json').read_bytes())['files_sha256']
code=json.loads((ENTRY/'code_allowlist_v3.json').read_bytes())['files_sha256']
vendor=json.loads((ENTRY/'vendor_code_allowlist_v1.json').read_bytes())
# The original vendor inventory is a seven-path JSON array with explicit pins;
# select its literal files through the same pinned helper, without importing Pyomo.
from types import ModuleType
import sys
helper=ModuleType('fresh_plan_vendor');helper.__file__=str(ENTRY/'vendor_code_policy.py')
sys.modules[helper.__name__]=helper
exec(compile((ENTRY/'vendor_code_policy.py').read_bytes(),helper.__file__,'exec'),vars(helper))
code.update({str(p):h for p,h in helper.vendor_files((ENTRY/'code_allowlist_v3.json').read_bytes(),
    (ENTRY/'vendor_code_allowlist_v1.json').read_bytes()).items()})
for version in ('2','3'):
    path=REPO/'experiments'/('h1_historical_n0_verifier_development_v'+version+'.py');code[str(path)]=sha256(path.read_bytes()).hexdigest()
for version in ('3','4'):
    for prefix in ('h1_bootstrap_integration_development_v','h1_owned_bootstrap_controller_development_v'):
        path=REPO/'experiments'/(prefix+version+'.py');code[str(path)]=sha256(path.read_bytes()).hexdigest()
assert len(code)==162
sources=dict(code)
sources.update({str(REPO/p):h for p,h in json.loads((ENTRY/'test_closure_v1.json').read_bytes())['files_sha256'].items()})
sources.update({str(ENTRY/p):h for p,h in manifest.items()})
members=[REPO/'tests/test_h1_successor_bootstrap_profile_development_v1.py',
    HERE/'profile_unit_01/request.json',HERE/'profile_unit_01/terminal.json',
    HERE/'fresh_n0_monitor_01/request.json',HERE/'fresh_n0_monitor_01/terminal.json',
    HERE/'saved_four_comparison_01.json',Path(__file__),HERE/'run_fresh_n0_entry_v2.py',HERE/'run_fresh_n0_bounded_v2.py',
    ENTRY/'package_manifest_v1.json',HERE/'registry_sources_02_non_authoritative/patch_manifest.json',
    HERE/'rebuild_registry_sources_v2.py',HERE/'registry_rebuild_check_02_non_authoritative/terminal.json',
    HERE/'registry_unit_04/terminal.json',HERE/'registry_unit_04/request.json',
    REPO/'tests/test_h1_registry_validation_operation_development_v1.py',
    REPO/'tests/test_h1_registry_validation_fresh_n0_development_v1.py']
sources.update({str(p):sha256(p.read_bytes()).hexdigest() for p in members})
assert all(sha256(Path(p).read_bytes()).hexdigest()==h for p,h in sources.items())
units=json.loads((HERE/'registry_unit_04/terminal.json').read_bytes());assert units['exit_code']==0 and units['source_unchanged']
old=json.loads((E/'chain_07/request.json').read_bytes())['before']
assert all(sha256(Path(p).read_bytes()).hexdigest()==h for p,h in old.items())
value=dict(status='DRAFT_NONAUTHORITATIVE',question='Does a cold genuine owned synthetic N0 reach pending_post_N through registry proof reuse, with predecessor scientific equality and released resources?',
    attempts=1,previous_attempt='01 failed before Job at profile binding; sources and locks intact',
    corrected_cause='generate independent symbolic profile against successor implementation; restore real reader before candidate definition; stable resolver callable',
    regression='profile_unit_01 passed; only implementation_sha256 differs, predecessor bytes preserved',
    entry_optimization='begin the existing metadata parse discovery window before fixtures and again before call; stock discovery unchanged',roots=1,hours=1,synthetic_jobs=1,native_calls=0,target='tests/test_h1_registry_validation_fresh_n0_development_v1.py',
    outer_output=str(HERE/'fresh_n0_monitor_02'),inner_output=str(HERE/'fresh_n0_entry_02_non_authoritative'),
    basetemp='D:/h1_registry_fresh_n0_02_non_authoritative',source_sha256=sources,code_lease_sha256=code,old_chain_sha256=old,
    limits=dict(wall_seconds=600,sampled_tree_rss_bytes=1024**3,storage_bytes=128*1024**2),
    stop='first test/oracle failure or any cap; no budget extension or unchanged retry; terminate observed diagnostic descendants only and retain terminal artifacts',
    dag=['existing explicit synthetic fixtures, original identity callables','cold verifier v3/bootstrap v4/owned v4',
        'real bootstrap journals and ownership','private scope entry plus foreign-thread rejection',
        'owned Windows Job and quiescence','four complete terminal builds','local/global retention','registry readback',
        'scope close and execution receipt','independent predecessor science oracle','owner close','lock/process/source postcheck'],
    expected=dict(full=4,fresh=28,contexts=64,build_sites=['N0_build','N0_build','registry','registry'],oracle_full_prepares=1),
    performance_basis='saved verifier four builds measured 84.8146s; fresh owner/job/identity cost unknown and explicitly capped; this is the evidence-producing diagnostic permitted by agent.md section 9',
    optimizations=['162 locked code bytes including 7 vendor files','configured eight-root interpreter; stock discovery unchanged',
        'locked selected METADATA parse values','per-root operation numerical proof; all original fresh contexts preserved'],
    unresolved='multi-root real bootstrap, common/Rref/Actual/paired/reopen, full-workflow budget and all formal gates remain open',
    full_hour0_chain_passed=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
out=HERE/'fresh_n0_plan_02.json'
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),source_files=len(sources),code_lease_files=len(code))),flush=True)
