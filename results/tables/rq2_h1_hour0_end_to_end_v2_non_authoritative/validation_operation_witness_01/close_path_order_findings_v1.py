"""Verify existing evidence and bind the path-order decision; run no experiment."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_04'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def main():
    checker = HERE / 'postcheck_path_order_v2.py'
    before = digest(checker)
    command = [sys.executable, '-I', '-B', str(checker)]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, timeout=45)
    for name, data in (('path_order_postcheck_v2.stdout', completed.stdout),
                       ('path_order_postcheck_v2.stderr', completed.stderr)):
        with (HERE / name).open('xb') as stream:
            stream.write(data)
    terminal = dict(command=command, exit_code=completed.returncode,
        elapsed_seconds=time.perf_counter() - started,
        script_sha256_before=before, script_sha256_after=digest(checker),
        observed_at_utc=datetime.now(timezone.utc).isoformat(),
        measurements_rerun=False, formal_result=False)
    if completed.returncode == 0:
        terminal['output_sha256'] = digest(HERE / 'path_order_comparison_02.json')
    write('path_order_postcheck_v2_terminal_01.json', terminal)
    assert completed.returncode == 0 and before == terminal['script_sha256_after']
    old = read(HERE / 'path_order_comparison_01.json')
    new = read(HERE / 'path_order_comparison_02.json')
    assert new.pop('postcheck_script_sha256') == before and new == old
    for name, pin in old['evidence_sha256'].items():
        assert digest(REPO / name) == pin
    assert digest(ENTRY / 'package_manifest_v1.json') == 'd13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43'
    for name, pin in read(ENTRY / 'package_manifest_v1.json')['files_sha256'].items():
        assert digest(ENTRY / name) == pin
    launcher = (ENTRY / 'launch_validation.py').read_text(encoding='utf-8')
    assert re.search("MANIFEST_SHA='([0-9a-f]{64})'", launcher)[1] == digest(ENTRY / 'package_manifest_v1.json')
    files = [Path(__file__), checker, HERE / 'postcheck_path_order_v1.py',
        HERE / 'path_order_comparison_01.json', HERE / 'path_order_comparison_02.json',
        HERE / 'path_order_postcheck_v2_terminal_01.json',
        HERE / 'path_order_postcheck_v2.stdout', HERE / 'path_order_postcheck_v2.stderr',
        HERE / 'measure_metadata_path_order_v1.py', HERE / 'measure_path_order_raw_audits_v3.py',
        HERE / 'metadata_order_plan_01.json', HERE / 'path_order_raw_plan_01.json',
        HERE / 'entry04_plan_01.json', HERE / 'postcheck_entry04_v1.py',
        ENTRY.parent / 'configured_entry_04_checks_01.json',
        ENTRY / 'package_manifest_v1.json', ENTRY / 'launch_validation.py']
    for label in ('metadata_c_first_01', 'metadata_d_first_01',
                  'path_order_c_first_01', 'path_order_d_first_01'):
        for root in (HERE / label, HERE / label / 'attempt_non_authoritative'):
            files.extend(root / name for name in ('request.json', 'terminal.json'))
    pins = {p.relative_to(REPO).as_posix(): digest(p) for p in files}
    for mode in ('c_first', 'd_first'):
        root = HERE / ('path_order_' + mode + '_01/attempt_non_authoritative')
        assert read(root / 'request.json')['metadata_discovery_fresh'] is True
        assert read(root / 'terminal.json')['stock_distribution_discovery_fresh'] is True
    erratum = dict(schema='h1_metadata_discovery_field_erratum_development_v1',
        applies_to=['raw v3 request metadata_discovery_fresh=True',
                    'raw v3 terminal stock_distribution_discovery_fresh=True',
                    'raw plan question no-cache wording'],
        field_meaning='stock version/distribution callables execute each lookup; no added selected-distribution/result cache',
        parsed_locked_version_cache_present=True, stdlib_internal_path_caches_not_cleared=True,
        cold_full_filesystem_discovery_proved=False,
        historical_bytes_preserved=True, measurements_rerun=False,
        evidence_sha256=pins, official_verdict=None, formal_result=False)
    write('path_order_evidence_erratum_01.json', erratum)
    pins['results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_operation_witness_01/path_order_evidence_erratum_01.json'] = digest(HERE / 'path_order_evidence_erratum_01.json')
    baseline = read(ENTRY / 'interpreter_path_policy_v1.json')['baseline_evidence']
    closure = dict(schema='h1_entry04_path_order_external_closure_development_v1',
        status='DRAFT_NONAUTHORITATIVE', observed_at_utc=datetime.now(timezone.utc).isoformat(),
        package_manifest_sha256=digest(ENTRY / 'package_manifest_v1.json'),
        inherited_policy_baseline_evidence=baseline,
        inherited_baseline_role='predecessor C-first baseline only',
        d_first_decision_evidence='path_order_comparison_02.json',
        actual_postcheck_exit_record='path_order_postcheck_v2_terminal_01.json',
        original_comparison_reverified_exact=True, measurements_rerun=False,
        tested_entry_bytes_unchanged=True, evidence_sha256=pins,
        official_verdict=None, full_chain_passed=False,
        whole_workflow_performance_review_complete=False, long_chain_launch_admitted=False,
        formal_execution_ready=False, resource_admission=False, native_execution_authorized=False)
    write('entry04_path_order_evidence_closure_01.json', closure)
    print(json.dumps(dict(postcheck_exit_code=completed.returncode,
        comparison_exact=True, evidence_files=len(pins), package_members=21)))


if __name__ == '__main__':
    main()
