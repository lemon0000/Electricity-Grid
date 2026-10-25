"""Bounded ordinary static captures. No research/native/role execution."""
import time
STARTED = time.perf_counter()
import ast
import base64
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PACKAGE = HERE.parent/'final_package_01'
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative'
PREV = ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01'
CONTRACT = 'docs/plan/staged_deliverability_c_saved_fresh_upstream_contract_scope_budget_v1.md'
NAV = ('docs/plan/科研项目执行步骤.md', 'docs/plan/staged_deliverability_c_scope_and_budget_plan_v1.md',
       'docs/model_spec/blocker_register.md', 'paper/drafts/README.md')
DOCS = (CONTRACT, 'docs/plan/continuation_handoff_20261025_saved_fresh_upstream_contract.md',
        (HERE.parent/'validation_report.md').relative_to(ROOT).as_posix())

def raw(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')

def pin(value):
    return dict(bytes=len(value), sha256=sha256(value).hexdigest())

def read(path):
    return json.loads(path.read_bytes())

def name(path):
    return path.relative_to(ROOT).as_posix()

def put(path, value):
    with path.open('xb') as stream:
        stream.write(raw(value))

def inventory(paths):
    return {name(p): pin(p.read_bytes()) for p in paths}

def helpers():
    return [HERE/n for n in ('capture_static.py', 'draft_design.py', 'design_oracle.py')] + [PACKAGE/'saved_checks.py']

def initial():
    assert not (HERE/'baseline.json').exists()
    assert sys.executable.lower() == r'D:\Miniconda3\envs\compute\python.exe'.lower()
    contracts = [PREV/n for n in ('successor_context_spec_v3.json', 'request_contract_v2.json',
                 'runtime_binding_contract_v2.json', 'deadline_contract_v2.json', 'capability_edges_v3.json')]
    source_names = read(PREV/'runtime_binding_contract_v2.json')['source_names']
    sources = inventory(ROOT/n for n in source_names)
    assert len(sources) == 49 and sources == read(PRIOR/'checks_01/group_admission_03.json')['source_pins']
    previous = dict(read(PRIOR/'checks_01/preservation_inventory.json'))
    previous.update(inventory(p for p in PRIOR.rglob('*') if p.is_file()))
    for n, expected in previous.items(): assert pin((ROOT/n).read_bytes()) == expected, n
    baseline = dict(authority='DRAFT_NONAUTHORITATIVE', base_head='f3b4717973557b04e558485267431cc32556b5b5',
                    sources=sources, preserved=previous, inputs=inventory([*contracts, ROOT/CONTRACT]),
                    helpers=inventory(helpers()), navigation_before=inventory(ROOT/n for n in NAV),
                    new_documents=list(DOCS), source_epoch=read(PRIOR/'checks_01/group_admission_03.json')['source_epoch'],
                    actual_F=False, scientific_evidence_adopted=False, resource_admission=False, formal_result=False)
    put(HERE/'baseline.json', baseline)
    for p in helpers():
        data = p.read_bytes(); ast.parse(data)
        snap = HERE/('helper_'+pin(data)['sha256']+'.snapshot')
        if not snap.exists():
            with snap.open('xb') as stream: stream.write(data)

def fixed(baseline):
    expected = {**baseline['sources'], **baseline['preserved'], **baseline['inputs'], **baseline['helpers']}
    revision_path = HERE/'draft_revision_02.json'
    if revision_path.exists():
        revision = read(revision_path)
        assert revision['baseline_pin'] == pin((HERE/'baseline.json').read_bytes())
        assert set(revision['helpers_after']) == set(baseline['helpers'])
        assert set(revision['input_overrides']) == {CONTRACT}
        archive_path = HERE/'design_attempt_01.snapshot.json'
        assert pin(archive_path.read_bytes()) == revision['archive_pin']
        for n, item in read(archive_path)['files'].items():
            assert pin(base64.b64decode(item['raw_base64'])) == {k:item[k] for k in ('bytes','sha256')}
        expected.update(revision['helpers_after']); expected.update(revision['input_overrides'])
        expected[name(revision_path)] = pin(revision_path.read_bytes())
        expected[name(archive_path)] = revision['archive_pin']
    actual = inventory(ROOT/n for n in expected)
    assert actual == expected, 'Source/history/helper drift'
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    return pin(raw(actual))

def limits():
    a = [p for p in HERE.rglob('*') if p.is_file()]
    b = [p for p in PACKAGE.rglob('*') if p.is_file()]
    assert len(a) <= 32 and sum(p.stat().st_size for p in a) <= 2*1024**2
    assert len(b) <= 16 and sum(p.stat().st_size for p in b) <= 1024**2
    return dict(execution_files=len(a), execution_bytes=sum(p.stat().st_size for p in a),
                package_files=len(b), package_bytes=sum(p.stat().st_size for p in b))

def main(action):
    actions = dict(baseline=('baseline_01', HERE, HERE/'capture_static.py', ['--baseline-target']),
                   design=('design_02', HERE, HERE/'draft_design.py', []),
                   revised_design=('design_03', HERE, HERE/'draft_design.py', []),
                   finalize=('finalizer_04', HERE, HERE/'design_oracle.py', ['--finalize']),
                   saved=('saved_05', PACKAGE, PACKAGE/'saved_checks.py', []),
                   terminal=('terminal_06', PACKAGE, PACKAGE/'saved_checks.py', []))
    assert action in actions
    label, out, script, args = actions[action]
    records = [read(p) for directory in (HERE, PACKAGE) for p in directory.glob('*.exit.json')]
    assert len(records) < 6 and all(r['returncode'] == 0 and r['accepted'] for r in records)
    spent = sum(r['charged_seconds'] for r in records)
    assert spent+12 <= 90
    if action == 'baseline': initial()
    baseline = read(HERE/'baseline.json')
    revision_path = HERE/'draft_revision_02.json'
    if action == 'revised_design':
        assert len(records) == 2
        for p in helpers():
            data = p.read_bytes(); ast.parse(data)
            snap = HERE/('helper_'+pin(data)['sha256']+'.snapshot')
            if not snap.exists():
                with snap.open('xb') as stream: stream.write(data)
    before = fixed(baseline)
    if action == 'saved':
        assert len(records) == 4 and (HERE/'document_checks.json').is_file()
        files = inventory(p for p in HERE.rglob('*') if p.is_file())
        put(PACKAGE/'execution_freeze.json', dict(files=files, count=len(files), bytes=sum(x['bytes'] for x in files.values()), root=pin(raw(files))))
        support = inventory([PACKAGE/'execution_freeze.json', PACKAGE/'saved_checks.py'])
        put(PACKAGE/'support_pins.json', support)
    elif action == 'terminal':
        assert (PACKAGE/'saved_05.exit.json').exists()
    for suffix in ('stdout.log', 'stderr.log', 'exit.json'):
        assert not (out/(label+'.'+suffix)).exists()
    script_pin = pin(script.read_bytes())
    argv = [sys.executable, '-B', str(script), *args]
    timeout = max(.01, min(11., 11.5-(time.perf_counter()-STARTED)))
    target_started = time.perf_counter()
    error, code, stdout, stderr = None, -1, b'', b''
    try:
        completed = subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=timeout, check=False)
        code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as caught:
        error, code = 'timeout', -2
        stdout, stderr = caught.stdout or b'', caught.stderr or b''
    target_seconds = time.perf_counter()-target_started
    after = fixed(baseline)
    assert before == after and pin(script.read_bytes()) == script_pin
    with (out/(label+'.stdout.log')).open('xb') as stream: stream.write(stdout)
    with (out/(label+'.stderr.log')).open('xb') as stream: stream.write(stderr)
    observed = time.perf_counter()-STARTED
    charged = observed+.25
    record = dict(authority='DRAFT_NONAUTHORITATIVE', label=label, argv=argv, returncode=code, error=error,
                  helper_epoch='draft_revision_02', revision_pin=pin(revision_path.read_bytes()),
                  design_output_pins=inventory(HERE/n for n in ('fixed_templates.json','protocol_domains.json','protocol_dag.json','verification_matrix.json')),
                  accepted=code == 0 and not stderr and len(stdout) <= 32768 and charged <= 12,
                  stdout_pin=pin(stdout), stderr_pin=pin(stderr), script_pin=script_pin,
                  baseline_pin=pin((HERE/'baseline.json').read_bytes()), fixed_before=before, fixed_after=after,
                  observed_capture_seconds=observed, target_seconds=target_seconds, tail_reserve_seconds=.25,
                  charged_seconds=charged, target_timeout_seconds=timeout, per_capture_cap_seconds=12,
                  previous_charged_seconds=spent, cumulative_cap_seconds=90, capture_python_startup_included=False,
                  whole_workflow_wall_budget_verified=False, actual_F=False, resource_admission=False,
                  scientific_evidence_adopted=False, formal_result=False,
                  prior_records=inventory(p for directory in (HERE, PACKAGE) for p in directory.glob('*.exit.json')),
                  support_pin=pin((PACKAGE/'support_pins.json').read_bytes()) if (PACKAGE/'support_pins.json').exists() else None)
    put(out/(label+'.exit.json'), record)
    size = limits()
    print(json.dumps(dict(label=label, returncode=code, accepted=record['accepted'], charged_seconds=round(charged, 6),
                          cumulative_charged_seconds=round(spent+charged, 6), **size), sort_keys=True))
    assert record['accepted'], record

if __name__ == '__main__':
    if sys.argv[1:] == ['--baseline-target']:
        baseline = read(HERE/'baseline.json')
        print(json.dumps(dict(preserved_paths=len(baseline['preserved']), source_names=len(baseline['sources']),
                              fixed=fixed(baseline), actual_F=False), sort_keys=True))
    else:
        assert len(sys.argv) == 2
        main(sys.argv[1])
