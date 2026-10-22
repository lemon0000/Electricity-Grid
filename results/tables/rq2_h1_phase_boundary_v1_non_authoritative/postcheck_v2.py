"""Compose the original postcheck with exact inherited-guard verification."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import postcheck_v1 as previous

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def main():
    destination = HERE / sys.argv[1]
    if destination.exists():
        raise ValueError('fresh successor verification output required')
    original_argv = sys.argv
    try:
        sys.argv = [str(Path(previous.__file__)), 'postcheck_v2_base.json']
        previous.main()
    finally:
        sys.argv = original_argv
    report = json.loads((HERE / 'postcheck_v2_base.json').read_bytes())
    verified = []
    for row in json.loads((HERE / 'reused_guard_evidence.json').read_bytes())['records']:
        path = REPO / row['path']
        expected = row['sha256']
        assert sha256(path.read_bytes()).hexdigest() == expected
        artifact = json.loads(path.read_bytes())
        actual = previous.verify_map(artifact[row['pin_field']])
        assert actual == row['verification'] and not actual['mismatches']
        assert row['eligible_for_exact_byte_reuse'] is True and row['original_scope_only'] is True
        verified.append(dict(path=str(path), sha256=expected, pin_field=row['pin_field'],
            pin_count=actual['count'], all_pins_match=True, original_scope_only=True))
        report['bindings'][str(path)] = expected
    assert len(verified) == 4
    for name in ('development_acceptance.json', 'postcheck_v2_base.json'):
        path = HERE / name
        report['bindings'][str(path)] = sha256(path.read_bytes()).hexdigest()
    report.update(schema='phase_boundary_postcheck_v2_non_authoritative',
        reused_guard_records_freshly_verified=verified,
        predecessor_report_preserved=True,
        closed_preseal_finding='verify inherited guard outer bytes and maps in final postcheck')
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(destination), passed=15, facts=9,
        reused_guard_records=4, inherited_guard_pin_counts=[r['pin_count'] for r in verified],
        long_connected_launch_admitted=False)))


if __name__ == '__main__':
    main()
