"""Record CPU attribution and plan reuse of the existing metadata resolver."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative';BASE=HERE.parent/'validation_path_optimization_01'
plan_path=D/'public_phase_runtime_cost_plan_120.json';plan=json.loads(plan_path.read_text())
profile_path=next(Path('D:/h1_public_phase_runtime_120_non_authoritative').glob('*/public_phase_runtime_profile.json'))
profile=json.loads(profile_path.read_text());terminal_path=HERE/'public_phase_runtime_cost_120/terminal.json'
terminal=json.loads(terminal_path.read_text());assert terminal['exit_code']==0 and terminal['source_unchanged']
drift=[name for name,pin in plan['files_sha256'].items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
result=dict(schema='h1_public_phase_runtime_cost_result_120',plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
    terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),profile_sha256=sha256(profile_path.read_bytes()).hexdigest(),
    components=profile['components'],terminal=terminal,planned_pins=len(plan['files_sha256']),pin_drift=drift,
    observation='Runtime checker batches32 calls each took0.009-0.024s; configuration.binding32 took0.503s. Its package metadata version192 calls accounted0.400s cumulative. Shared check8 took0.131s, of which binding0.120s.',
    inference='Repeated configuration identity/package metadata is material. The direct runtime checkers are not dominant in this0-owner probe. Full public nested call counts are still not profiled.',
    profiler_enabled=True,matched_unprofiled_runtime_comparison=False,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,formal_result=False,resource_admission=False)
out=D/'public_phase_runtime_cost_result_120.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
assert not drift
old=BASE/'entry_revision_07';reused=BASE/'entry_revision_14_non_authoritative'
for name in ('code_read_lease.py','metadata_parse_lease.py'):
    assert (old/name).read_bytes()==(reused/name).read_bytes()
assert (HERE/'pinned_distribution_resolver_v1.py').read_bytes()==(reused/'pinned_distribution_resolver_v1.py').read_bytes()
paths={Path(p) for p in plan['files_sha256']}
paths.update([Path(__file__),HERE/'run_unit_entry_v4.py',HERE/'run_unit_bounded_v17.py',
    reused/'pinned_distribution_resolver_v1.py',old/'code_read_lease.py',old/'metadata_parse_lease.py',old/'metadata_allowlist_v1.json'])
command=list(plan['command']);command[2]=str(HERE/'run_unit_bounded_v17.py');command[3]='metadata_entry_composition_121'
command[command.index('--')+1]=str(HERE/'run_unit_entry_v4.py')
command[command.index('--basetemp')+1]='D:/h1_metadata_entry_121_non_authoritative'
assert not Path(command[command.index('--basetemp')+1]).exists()
value=dict(plan);value.update(at_utc=datetime.now(timezone.utc).isoformat(),command=command,
    question='Does the existing pinned metadata resolver compose cleanly with the new graph and remove the package-discovery/parse cost in the0-owner component probe?',
    dag=['Acquire original code+metadata leases; load the exact reused entry14 resolver with two native discovery oracles.',
        'Before each pytest body, begin the held parser discovery window after fixtures. Run the identical fixed profile test120 with0 owners and2 static-data windows.',
        'Close resolver/parser/code leases; require alias restoration, all handles closed, empty resolver cache, honest fast/fallback/fresh-object counters.',
        'Save the profiled component observations and new entry closed receipt; check process/source/storage terminal.'],
    optimization=dict(reuse='Reuse byte-identical CodeReadLease/MetadataParseLease and entry14 pinned_distribution_resolver; do not reimplement or alter project runtime/science checks.',
        evidence='120 identified metadata.version as0.400/0.503s inside32 configuration bindings. Entry3 does not reset parser windows after pytest fixture setup and has no distribution resolver. Prior entry14 helper tests/evidence are reused by source hash.',
        limitations='Discovery paths reused only for eight held unique packages; fresh PathDistribution instances remain. Unknown names and changed discovery graph fall back. No transient ABA or per-call discovery claim.',
        comparison='Identical cProfile program and counts. Profiled attribution only, not an unprofiled or whole-workflow speed claim.'),
    entry_composition='New diagnostic entry4 and monitor17 (monitor16 behavior unchanged, only exact unit-entry path updated).',
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
out=D/'metadata_entry_composition_plan_121.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(result120_sha256=sha256((D/'public_phase_runtime_cost_result_120.json').read_bytes()).hexdigest(),
    plan121_sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
