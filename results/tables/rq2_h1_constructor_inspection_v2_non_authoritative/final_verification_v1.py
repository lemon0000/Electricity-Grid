"""Fresh byte/process/diff verification; no production seal or review receipt."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

import psutil
import postcheck_v1 as audit

HERE, REPO = audit.HERE, audit.REPO
CORE_PIN = 'bb70408423aebbeecdb2531b801c76f41808178cce0a1d55cb68bd2876551180'


def main():
    final = HERE/'final_verification.json'
    if final.exists():
        raise ValueError('fresh final verification path required')
    core_path = HERE/'development_acceptance_v1.json'
    assert audit.pin(core_path) == CORE_PIN
    core = audit.load(core_path)
    assert all(audit.pin(path) == expected for path, expected in core['bindings'].items())
    snapshots, owned = {}, {}
    for label in ('unit_01','unit_02','unit_03','unit_04','comparison_01','oracle_01','short_comparison_01'):
        root = HERE/label
        request, terminal = audit.load(root/'request.json'), audit.load(root/'terminal.json')
        resolved = audit.resolve(request['sources_sha256'], (root/'tested_bytes',HERE/'canonical_before'))
        snapshots[label] = dict(verified_pins=len(resolved),
            live_bindings=sum(v['live'] for v in resolved.values()),
            preserved_bindings={k:v for k,v in resolved.items() if not v['live']},
            original_terminal_changed_sources=terminal['changed_sources'])
        owned.update(terminal['observed_processes'])
    remaining = []
    for pid, created in owned.items():
        try:
            process = psutil.Process(int(pid))
            if process.is_running() and process.create_time() == created:
                remaining.append(dict(pid=int(pid),create_time=created))
        except psutil.NoSuchProcess:
            pass
    assert not remaining
    active_related = []
    for process in psutil.process_iter(['pid','name','cmdline','create_time']):
        info = process.info
        if info['pid'] == os.getpid():
            continue
        name, command = (info['name'] or '').lower(), ' '.join(info['cmdline'] or []).lower()
        if (any(part in name for part in ('python','gurobi','cplex','highs','ipopt')) and
                any(part in command for part in ('h1_', 'rq2_', 'pytest'))):
            active_related.append(info)
    assert not active_related
    case = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    expected = audit.load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')['diagnostic_case_files_sha256']
    assert {str(p):audit.pin(p) for p in case.rglob('*') if p.is_file()} == expected and len(expected) == 465
    checkpoint = audit.load(case/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(checkpoint) == 444 and all(audit.pin(path) == value for path,value in checkpoint.items())
    for relative in ('experiments/h1_constructor_inspection_capture_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v2.py',
        'experiments/h1_constructor_source_batch_validation_development_v1.py',
        'tests/test_h1_constructor_inspection_capture_development_v1.py'):
        assert (REPO/relative).read_bytes() == (HERE/'unit_04/tested_bytes'/relative).read_bytes()
    preparation = audit.load(HERE/'formal_preparation_state_v3.json')
    assert all(audit.pin(path) == value for path,value in preparation['bindings'].items())
    updates = audit.load(HERE/'canonical_doc_updates.json')['updates']
    assert len(updates) == 2
    for row in updates:
        original, current = Path(row['before_snapshot']).read_bytes(), Path(row['path']).read_bytes()
        offset, size = row['insertion_offset'], row['insertion_length']
        assert current[:offset]+current[offset+size:] == original
        assert sha256(original).hexdigest() == row['before_sha256']
        assert sha256(current).hexdigest() == row['after_sha256']
    probe = audit.load(HERE/'dependency_gap_static_probe_v1.json')
    assert all(audit.pin(path) == value for path,value in probe['bindings'].items())
    assert probe['dependency_alias_restored'] and not probe['actual_reader_executed']
    review = audit.load(HERE/'preseal_review_summary.json')
    assert review['exact_development_core_sha256'] == CORE_PIN and not review['official_review']
    commands = [['git','diff','--check'],['git','status','--short','--untracked-files=normal'],
                ['git','rev-parse','HEAD'],['git','branch','--show-current']]
    git = []
    for command in commands:
        done = subprocess.run(command,cwd=REPO,capture_output=True,text=True,encoding='utf-8',check=True)
        git.append(dict(command=command,exit_code=done.returncode,stdout=done.stdout,stderr=done.stderr))
    extras = [core_path,Path(__file__),HERE/'preseal_review_summary.json',
        HERE/'dependency_gap_static_probe_v1.py',HERE/'dependency_gap_static_probe_v1.json',
        HERE/'dependency_gap_static_probe_setup_failure_source.py',HERE/'dependency_gap_static_probe_setup_failure.json']
    bindings = dict(core['bindings'])
    bindings.update({str(p):audit.pin(p) for p in extras})
    result = dict(status='DRAFT_NONAUTHORITATIVE', latest_core=str(core_path),latest_core_sha256=CORE_PIN,
        current_core_bindings_verified=len(core['bindings']), fresh_attempt_binding_resolution=snapshots,
        current_source_and_test_bytes_equal_to_unit_04=True, observed_owned_pid_creation_pairs_remaining=remaining,
        active_related_research_python_or_solver=active_related, complete_unobserved_process_tree_proof=False,
        saved_case_files=465,saved_owned_files=444,saved_case_and_owned_sha256_unchanged=True,
        canonical_byte_preservation_scope='all_preexisting_bytes_of_only_the_two_modified_canonical_documents',
        canonical_documents_verified=2, postcheck_original_all_preexisting_dirty_document_bytes_field_scope='canonical_doc_updates.updates only',
        other_dirty_worktree_files_not_in_byte_preservation_proof=True,
        concurrent_paper_changes_preserved_not_written_by_this_task=True,
        git=git, git_publication_performed=False,
        static_model_dependency_gap_observed=True, actual_reader_fault_counterexample_proved=False,
        preseal_review=str(HERE/'preseal_review_summary.json'),
        remaining_specific_development_gaps=review['remaining_specific_development_gaps'],
        source_successor_adopted=False, owner_integrated=False,
        overall_performance_review_complete=False,long_connected_launch_admitted=False,
        total_192h_wall_admission_seconds=None,resource_admission=False,
        formal_execution_ready=False,formal_result=False,native_execution_authorized=False,
        full_192_hour_execution_verified=False,real_phase_terminal_reopen_verified=False,
        complete_dynamic_closure_proved=False,unobserved_ABA_covered=False,
        sealed=False,official_review_pass=False,new_normal_jobs=0,real_native_calls=0,
        objective_complete=False, bindings=bindings)
    with final.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    assert all(audit.pin(path) == value for path,value in bindings.items())
    print(json.dumps(dict(final=str(final),sha256=audit.pin(final),bindings=len(bindings),
        remaining_owned_processes=0,saved_files=465,owned_files=444,objective_complete=False)))


if __name__ == '__main__':
    main()
