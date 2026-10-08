"""Rebuild frozen marginal chronology and inventory proposed enrollment tails."""
from decimal import Decimal
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rq2_joint_deliverability_boundary_v1 import continuation_audit as source
from src.rq2_joint_deliverability_boundary_v1 import enrollment_support_audit as coverage

CHAIN_FILE = ROOT / 'results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative/chains.json'
CHAIN_SHA = '0f661707d4ebb6ceb6f12073e6426a03b542322324df8a4f99b6d229ced8fc48'
SUMMARY_SHA = 'faba770bf8f3d83229f840fc1074939742e847bd55ab793b63264cb2322dd45e'


def run(enrollment_hours, followup_hours, stride_hours):
    source._verify_hash(CHAIN_FILE, CHAIN_SHA, 'previous chains')
    source._verify_hash(CHAIN_FILE.parent / 'summary.json', SUMMARY_SHA, 'previous summary')
    previous_summary = source._read_json(CHAIN_FILE.parent / 'summary.json')
    source._verify_hash(source.DEFAULT_CONFIG, previous_summary['config_sha256'], 'source config')
    source._verify_hash(Path(source.__file__), previous_summary['implementation_sha256'], 'source audit')
    verified = source.audit_continuation_availability()
    if verified['chains'] != source._read_json(CHAIN_FILE):
        raise ValueError('fresh source chains differ from pinned delivery')
    report = coverage.enumerate_enrollment_support(verified['chains'], enrollment_hours=enrollment_hours,
        followup_hours=followup_hours, stride_hours=stride_hours)
    config = source._load_config(source.DEFAULT_CONFIG)
    binding = config['inputs']['workload']
    package, _ = source._verify_package(binding, 'workload')
    rows = source._read_gzip_csv(package / 'workload_blocks.csv.gz', source.WORKLOAD_FIELDS)
    above_one = {split: sorted(int(row['source_relative_hour']) for row in rows
        if row['split'] == split and Decimal(row['workload_fraction']) > 1)
        for split in ('training', 'holdout')}
    for window in report['windows']:
        if window['kind'] == 'workload':
            bad = [hour for hour in above_one[window['split']]
                   if window['source_start'] <= hour <= window['observed_end_inclusive']]
            window['raw_above_one_enrollment_hours'] = [h for h in bad if h <= window['enrollment_end_inclusive']]
            window['raw_above_one_observed_followup_hours'] = [h for h in bad if h > window['enrollment_end_inclusive']]
    for split, summary in report['summary'].items():
        windows = [w for w in report['windows'] if w['kind'] == 'workload' and w['split'] == split]
        summary['raw_above_one_workload_windows'] = {
            'enrollment': sum(bool(w['raw_above_one_enrollment_hours']) for w in windows),
            'observed_followup_only': sum(bool(w['raw_above_one_observed_followup_hours'])
                and not w['raw_above_one_enrollment_hours'] for w in windows),
            'either': sum(bool(w['raw_above_one_enrollment_hours'] or w['raw_above_one_observed_followup_hours'])
                for w in windows)}
    report.update(schema='rq2_finite_enrollment_source_coverage_v1',
        source_chains_sha256=CHAIN_SHA, source_config_sha256=previous_summary['config_sha256'],
        source_summary_sha256=SUMMARY_SHA,
        source_audit_sha256=previous_summary['implementation_sha256'],
        input_packages=config['inputs'], raw_above_one_source_hours=above_one,
        source_chains_rebuilt_from_package_rows=True, source_evidence_class='derived_published_marginals',
        power_outages_are_observed=False, workload_is_observed_power=False,
        registered_joint_coupling=False, solver_calls=0,
        implementation_sha256=source._sha256(Path(coverage.__file__)),
        runner_sha256=source._sha256(Path(__file__)))
    # Recheck source packages after use. No claim of hostile-ABA protection.
    for kind, item in config['inputs'].items():
        source._verify_package(item, kind)
    source._verify_hash(source.DEFAULT_CONFIG, previous_summary['config_sha256'], 'source config')
    source._verify_hash(CHAIN_FILE, CHAIN_SHA, 'previous chains')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--enrollment-hours', type=int, required=True)
    parser.add_argument('--followup-hours', type=int, required=True)
    parser.add_argument('--stride-hours', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.enrollment_hours, args.followup_hours, args.stride_hours)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(report['summary'], indent=2))
