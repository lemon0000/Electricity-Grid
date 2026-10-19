"""Fail-fast preparation for one non-authoritative four-Parent diagnostic.

Does not launch anything. Writes a new plan only after checking the scoped
audit, successful ordinary units, immutable package members and input closure.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ENTRY = HERE.parent/'validation_path_optimization_01'/'entry_revision_12_non_authoritative'
EVIDENCE = HERE/'whole_workflow_optimization_01_non_authoritative'
ATTEMPT = '48'


def read(path): return json.loads(path.read_bytes())
def pin(path): return sha256(path.read_bytes()).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)


def main():
    require(Path.cwd() == ROOT, 'exact repository working directory required')
    audit_path = EVIDENCE/'open_overlay_pre_seal_findings_47.json'
    audit = read(audit_path)
    require(audit['scope'] == 'named canonical Python bindings and failure paths', 'audit scope mismatch')
    require(audit['no_remaining_named_material_P1'] is True, 'scoped findings remain open')
    require(audit['official_review'] is False and audit['production_seal'] is False, 'ordinary audit required')
    for relative, expected in audit['evidence_sha256'].items():
        require(pin(ROOT/relative) == expected, 'audit evidence changed: '+relative)
    unit_path = HERE/'workflow_open_overlay_units_47'/'terminal.json'
    unit = read(unit_path)
    require(unit['exit_code'] == 0 and unit['stop_reason'] is None, 'ordinary unit terminal required')
    require(unit['source_unchanged'] and unit['observed_owned_processes_absent'] and
            not unit['cleanup_errors'] and not unit['storage_read_errors'], 'unit preservation/cleanup failure')
    manifest_path = ENTRY/'package_manifest_v1.json'
    manifest = read(manifest_path)
    require(manifest['status'] == 'DRAFT_NONAUTHORITATIVE' and not manifest['production_seal'], 'draft package required')
    for name, expected in manifest['files_sha256'].items():
        require(pin(ENTRY/name) == expected, 'package member changed: '+name)
    for name in ('bounded_stable_read_overlay_v1.py', 'test_bounded_stable_read_overlay_v1.py'):
        require((HERE/name).read_bytes() == (ENTRY/name).read_bytes(), 'helper/test copy mismatch')
    counts = {}
    for name, expected_count in (('code_allowlist_v3.json', 250), ('vendor_code_allowlist_v1.json', 7),
                                 ('test_closure_v1.json', 660), ('metadata_allowlist_v1.json', 8)):
        rows = read(ENTRY/name)['files_sha256']
        require(len(rows) == expected_count, 'closure count mismatch: '+name)
        for path, expected in rows.items():
            require(pin(Path(path)) == expected, 'closure byte mismatch: '+path)
        counts[name] = len(rows)
    science = read(ENTRY/'scientific_input_allowlist_v1.json')['files']
    require(len(science) == 2, 'exact two scientific byte inputs required')
    for path, row in science.items():
        data = Path(path).read_bytes()
        require(len(data) == row['size_bytes'] and sha256(data).hexdigest() == row['sha256'],
                'scientific input byte mismatch: '+path)
    local = read(ENTRY/'open_overlay_units_47'/'bounded_open_overlay_unit_evidence.json')['local_comparison']
    receipt = local['receipt']
    require(receipt['eligible_for_canonical_entry_clean'] and receipt['canonical_IO_dependencies'] and
            receipt['original_open_restored'] and receipt['original_read_bytes_restored'] and
            receipt['remaining_streams'] == 0 and receipt['original_read_calls'] == receipt['bounded_read_calls'] == 128,
            'genuine composed owner/read evidence required')
    old_path = EVIDENCE/'distribution_bounded_full_path_plan_41.json'
    old = read(old_path)
    prior_terminal = HERE/'workflow_genesis_distribution_paired_41'/'terminal.json'
    files = [audit_path, unit_path, old_path, prior_terminal,
             EVIDENCE/'distribution_full_parent_comparison_41.json',
             EVIDENCE/'acceptance_matrix_08.json', Path(__file__),
             HERE/'run_workflow_entry_bounded_v6.py', HERE/'build_open_overlay_entry_draft_v1.py',
             ENTRY/'launch_validation.py', manifest_path, ENTRY/'validation_entry.py',
             ENTRY/'open_overlay_units_47'/'terminal.json',
             ENTRY/'open_overlay_units_47'/'bounded_open_overlay_unit_evidence.json']
    files += [ENTRY/name for name in manifest['files_sha256']]
    files += [ROOT/old['target'].split('::')[0]]
    plan = dict(schema='h1_bounded_ordinary_four_parent_open_overlay_plan_v1', status='DRAFT_NONAUTHORITATIVE',
        observed_at_utc=datetime.now(timezone.utc).isoformat(),
        purpose='measure fresh bounded read-size mapping composed with the sole held static byte owner',
        evidence_sha256={str(p.relative_to(ROOT)): pin(p) for p in files},
        target=old['target'], instance=old['instance'], stages=old['stages'],
        dependency_order=('configure isolated interpreter policy and preload canonical raw -> install Path.open -> '
            'load static byte module -> construct/adopt sole byte owner -> byte enter -> overlay bind -> '
            'path lease -> metadata parser -> distribution resolver -> normalizer -> test DAG -> reverse exits -> '
            'overlay quiesce -> byte close or once-only cleanup retry -> restore Path.open -> detached reports'),
        invocation={'outer': 'workflow_genesis_open_overlay_paired_'+ATTEMPT,
                    'child': 'genesis_open_overlay_paired_'+ATTEMPT,
                    'entry': ENTRY.name, 'kind': 'pytest', 'mode': 'parse_path'},
        reuse=dict(previous_plan_sha256=pin(old_path), prior_terminal=read(prior_terminal),
            legacy_chain_body_restarted=False, legacy_independent_postcheck='closed artifact reused',
            static_byte_files=257, locked_METADATA_files=8, scientific_input_files=2,
            unchanged_code_and_test_closure=counts, entry11_distribution_path_reuse='unchanged',
            digest_entry10_composed=False, raw_archive_or_numerical_or_saved_record_cache=False),
        read_contract=dict(caller='exact canonical raw source/code/globals/registry/loader and creating thread',
            mapping='normal int cap+1 to observed-before size+1; otherwise original open/read fallback',
            fresh_stat_open_fstat_read_fstat_and_final_path_check=True,
            mutation_tests=['growth', 'shrink', 'replacement', 'empty/exact/excess cap'],
            scientific_thresholds_and_original_raw_body_unchanged=True,
            sole_persistent_byte_owner=True, overlay_owns_transient_streams=True,
            invalidation='sticky named binding/control/function drift; no clean receipt after recovery',
            bounded_cleanup='one byte-owner cleanup retry while original wrapper remains installed',
            audit_hook_transparency_proven=False, per_site_IO_failure_order_preserved=False,
            transient_dependency_ABA_covered=False, arbitrary_memory_security_sandbox=False),
        optimization_decisions=dict(
            read_size='local composed test establishes bytes/stamps and failure checks; full-path effect remains to measure',
            source_replay='at least81 reference inspections through capture/construction remain fresh; separate proof needed for reuse',
            cache='only existing held immutable code/static byte and metadata path reuse; no new scientific result reuse',
            parallelism='one process; reference ownership/commit callbacks serialize current DAG',
            unmeasured_tail='paired/reopen and combined cleanup must reach terminal; timeout remains incomplete'),
        representative_evidence=dict(unit47=unit, local_read_comparison=local,
            prior28_wall_seconds=600.391, prior36_wall_seconds=600.328, prior41_wall_seconds=600.312,
            prior41_prefix_seconds=[46.4102818, 200.7242331, 349.7541201, 498.5539167, 498.69194],
            source_logical_requests=2408, source_preparations=28, bundle_windows=13,
            record_bundle_windows=1, retains=5, three_paired_lanes=3,
            simulated_hours=1, whole_workflow_speedup_established=False),
        costs=dict(whole_workflow_review_complete=False, complete_runtime_estimate_seconds=None,
            basis='fixed-budget representative diagnostic under section9; no extrapolation from local speedup',
            cold_entry_and_prefix='measured by prior attempts; changed read route measured locally',
            paired_reopen_and_cleanup='not yet measured to complete optimized terminal',
            total_call_count='exact original fixture asserts 2408 source requests/28 preparations/14 bundle windows; read count observed'),
        limits=old['limits'],
        acceptance=old['acceptance']+[
            'closed overlay receipt binds helper/raw pins and canonical IO dependencies',
            'eligible read calls equal bounded reads; zero remaining transient streams; original hooks restored',
            'original sole byte owner closes with exit file/ancestor verification and no first error/history',
            'actual bounded-read counters and original/bounded byte requests saved'],
        remaining=old['remaining'],
        pre_seal_scope='named canonical Python bindings and failure paths',
        pre_seal_candidate=dict(status='scoped_findings_closed', official_review=False, production_seal=False),
        launch_prerequisites=['all recorded pins verified before this plan is written',
                              'no related active process, checked immediately before launch',
                              'new empty artifact root; fixed cap; no retry/extension of this attempt'],
        environment=dict(python=sys.version, executable=sys.executable, platform=platform.platform()),
        ordinary_unit_launch_not_formal_experiment=True, formal_result=False, formal_execution_ready=False,
        production_seal=False, resource_admission=False, native_execution_authorized=False)
    destination = EVIDENCE/('open_overlay_bounded_full_path_plan_'+ATTEMPT+'.json')
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(plan, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(plan=str(destination), sha256=pin(destination), binding_checks_completed=True,
                         starts_process=False, formal_result=False)))


if __name__ == '__main__': main()
