"""Fresh PRE_SEAL input for owner identity and bounded implementation reuse."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
bootstrap=ROOT/'experiments/h1_bootstrap_integration_development_v5.py'
prior=HERE/'public_implementation_identity_cost_125/tested_bytes/experiments'/bootstrap.name
def body(path,name):
    node=next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.dump(ast.Module(body=node.body,type_ignores=[]),include_attributes=False)
assert body(prior,'implementation_identity')==body(bootstrap,'_raw_implementation_identity')
paths=[bootstrap,ROOT/'agent.md',ROOT/'AGENTS.md',Path(__file__)]
paths.extend(ROOT/'experiments'/name for name in (
    'h1_owned_bootstrap_controller_development_v5.py','h1_group_execution_roster_development_v4.py',
    'h1_historical_n0_verifier_development_v4.py','h1_phase_manifest_binding_development_v3.py',
    'h1_phase_manifest_validation_operation_development_v1.py','h1_phase_dependency_validation_operation_development_v1.py',
    'h1_validation_runtime_closure_development_v2.py'))
paths.extend(ROOT/'tests'/name for name in (
    'test_h1_bootstrap_phase_segments_development_v5.py','test_h1_phase_owner_identity_faults_development_v1.py',
    'test_h1_phase_implementation_observation_development_v5.py',
    'test_h1_phase_manifest_segment_faults_development_v1.py','test_h1_phase_dependency_window_faults_development_v1.py'))
for label in ('phase_owner_identity_faults_126','phase_owner_identity_faults_127',
              'phase_owner_identity_faults_128','phase_implementation_observation_129'):
    paths.extend(HERE/label/name for name in ('request.json','started.json','stdout.log','terminal.json'))
paths.extend(D/name for name in ('public_phase_pre_seal_input_118.json',
    'roster4_header_probe_result_119.json','public_implementation_identity_cost_result_125.json'))
terminals={label:json.loads((HERE/label/'terminal.json').read_text()) for label in
    ('phase_owner_identity_faults_128','phase_implementation_observation_129')}
assert all(t['exit_code']==0 and t['source_unchanged'] and t['observed_owned_processes_absent']
           and not t['cleanup_errors'] for t in terminals.values())
value=dict(schema='h1_public_phase_pre_seal_input_130',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    root_sole_writer=True,raw_formula_ast_identical_to_tested_125=True,
    files_sha256={p.relative_to(ROOT).as_posix():sha256(p.read_bytes()).hexdigest() for p in paths},
    terminals=terminals,unit_bodies={'128':'99 passed in20.50s','129':'110 passed in23.11s'},
    changes=['Three private id-keyed weak identity registries with ref/token guarded removal; class lookup and actual MRO hash/eq pins.',
        'Bootstrap root implementation digest only: raw entry/resume/exit against private baseline; creator-thread LIFO memo inside one synchronous segment.',
        'Original complete raw formula preserved; callback/Job gaps, foreign thread and outside scope use raw. Roster own formula remains unchanged.',
        'Runtime checks remain per call; exit failure clears memo and uses original cleanup. Diagnostic receipt separates implementation bookends and ABA limitation.'],
    regressions=['alias pre-handle refusal; fake cannot inspect/close genuine actual handles; changed real hash does not strand cleanup',
        '100 memo hits with runtime checks; foreign raw; callback gap/child/resume; two owner LIFO; exit drift/raw exception/body primary/CloseHandle pending retry; callback persistent write followed by resume refusal'],
    failed_iterations_preserved={'126':'Four-tuple cleanup regression, fixed by separate registry tuple and original three-item capsule record.',
        '127':'Test incorrectly expected a trusted receipt after sticky runtime drift. Genuine handles were closed; updated test requires receipt refusal and independent cleanup counters.'},
    scope='AST original coordinator + controlled unit identity oracle + real tiny Windows data handles and actual Bootstrap5 pre-handle class-drift refusal. No genuine header or N0 in128/129.',
    remaining=['independent audit of current bytes','genuine Bootstrap5/Roster4 header create/inspect/close/reopen',
        'new N0 numerical oracle/three arms/typed paired Post close/reopen','whole-workflow budget and formal gates'],
    production_seal=False,official_review=False,formal_result=False,formal_execution_ready=False,
    full_optimized_workflow_accepted=False,resource_admission=False,native_execution_authorized=False)
out=D/'public_phase_pre_seal_input_130.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
