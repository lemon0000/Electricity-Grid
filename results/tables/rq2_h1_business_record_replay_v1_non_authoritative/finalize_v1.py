"""Fresh final bookkeeping for this non-authoritative negative diagnostic."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    destination = HERE / 'final_verification.json'
    if destination.exists():
        raise ValueError('fresh final verification output required')
    core_path = HERE / 'development_acceptance_v2.json'
    core = read(core_path)
    assert digest(core_path) == 'c1f5f466ad7693be420e6ddabd4d77e43007231d345e003a0ab106503377bfd9'
    assert all(digest(path) == expected for path, expected in core['bindings'].items())
    review = read(HERE / 'preseal_review_summary.json')
    assert review['reviewed_core_sha256'] == digest(core_path)
    assert review['remaining_specific_findings_in_detached_scope'] == []
    assert not review['official_verdict_issued'] and not review['receipt_issued']
    commands = []
    for args in (['git', 'diff', '--check'], ['git', 'diff', '--numstat'],
                 ['git', '-c', 'core.quotepath=false', 'status', '--short', '--branch']):
        result = subprocess.run(args, cwd=REPO, capture_output=True, text=True, encoding='utf-8')
        assert result.returncode == 0
        commands.append(dict(command=args, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr))
    remaining = []
    for label in ('unit_01', 'profile_01', 'profile_02'):
        for pid, created in read(HERE / label / 'terminal.json')['observed_processes'].items():
            try:
                process = psutil.Process(int(pid))
                if process.create_time() == created and process.is_running():
                    remaining.append(dict(pid=int(pid), create_time=created))
            except psutil.NoSuchProcess:
                pass
    assert not remaining
    related = []
    for process in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        info = process.info
        if info['pid'] == os.getpid() or not info['name']:
            continue
        name = info['name'].lower()
        argv = ' '.join(info['cmdline'] or []).lower()
        if (name.startswith('python') or name in ('gurobi_cl.exe', 'highs.exe', 'ipopt.exe', 'cplex.exe', 'scip.exe')):
            if 'electricity-grid' in argv or 'h1_' in argv:
                related.append(info)
    assert not related, related
    paths = set(core['bindings'])
    paths.update(str(path) for path in HERE.rglob('*') if path.is_file())
    report = dict(status='DRAFT_NONAUTHORITATIVE', latest_core=str(core_path),
        latest_core_sha256=digest(core_path), current_core_bindings_verified=len(core['bindings']),
        historical_v1_core=str(HERE / 'development_acceptance_v1.json'),
        v1_current_vs_snapshot_resolution=core['preceding_diagnostic_core_preserved'],
        preseal_review=str(HERE / 'preseal_review_summary.json'),
        remaining_specific_preseal_findings=[], commands=commands,
        observed_owned_pid_creation_pairs_remaining=remaining,
        active_related_research_python_or_solver=related,
        complete_unobserved_process_tree_proof=False,
        canonical_changes='two documents, three added lines each this increment; previous dirty bytes preserved in canonical_before',
        behavior_unit_cases=22, fixed_profile_test_cases=1,
        optimization_adopted=False, owner_integration_performed=False,
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        total_192h_wall_prediction_seconds=None, resource_admission=False,
        native_execution_authorized=False, formal_execution_ready=False, formal_result=False,
        full_192_hour_execution_verified=False, real_phase_terminal_reopen_verified=False,
        typed_followup_right_censor_terminal_verified=False,
        complete_dynamic_closure_proved=False, unobserved_ABA_covered=False,
        sealed=False, official_review_pass=False, new_normal_jobs=0, real_native_calls=0,
        bindings={path: digest(path) for path in sorted(paths)})
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(final=str(destination), sha256=digest(destination),
                         bindings=len(report['bindings']), core_bindings=len(core['bindings']),
                         optimization_adopted=False, remaining_owned_processes=remaining)))


if __name__ == '__main__':
    main()
