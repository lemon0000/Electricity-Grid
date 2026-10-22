"""Read-only verification of this saved development probe; does not replay solvers."""
from pathlib import Path
import json
import subprocess
import sys
ROOT = Path(__file__).absolute().parents[4]
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_journal_diagnostic_v1 as d


def main():
    output = Path(__file__).absolute().parent
    verified = json.loads((output/'verification.json').read_text(encoding='utf-8'))
    completion = json.loads((output/'completion.json').read_text(encoding='utf-8'))
    assert verified['source_bindings'] == d.bindings()
    assert verified['preserved'] == d.preservation()
    assert all(d.stamp(output/name) == pin for name, pin in completion['files'].items())
    assert all(d.stamp(output/name) == pin for name, pin in verified['checked_roles'].items())
    report = json.loads((output/'report.json').read_text(encoding='utf-8'))
    launch = json.loads((output/'launcher.json').read_text(encoding='utf-8'))
    assert launch['exit_code'] == 0 and launch['stop_reason'] is None and not launch['child_running_after_cleanup']
    for name in ('verification.json', 'preseal_findings.json', 'validation_report.md'):
        rel = 'results/tables/staged_rts24_causal_v1_non_authoritative/development_checks_01/'+name
        assert (ROOT/rel).read_bytes() == subprocess.check_output(['git', 'show', verified['git_head_before_own_commit']+':'+rel], cwd=ROOT)
    calls = report['parent_counts']['selective_compiler_calls']
    descriptions = report['parent_counts']['selective_descriptions']
    for case in report['success_cases'].values():
        calls += case['counts']['selective_compiler_calls']
        descriptions += case['counts']['selective_descriptions']
    assert (calls, descriptions) == (500, 1324)
    print(json.dumps(dict(core_files=completion['manifest_files'], core_bytes=completion['logical_bytes'],
        source_pins=len(d.SOURCES), reference_compiler_calls=calls, reference_descriptions=descriptions,
        old_bound_bytes_unchanged=True, scope='read_only_saved_probe_postcheck'), sort_keys=True))


if __name__ == '__main__': main()
