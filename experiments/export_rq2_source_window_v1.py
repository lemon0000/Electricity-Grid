"""Create one independently selected marginal-window diagnostic, without solver."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from src.rq2_joint_deliverability_boundary_v1.source_window import load_source_window


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('power', 'workload'), required=True)
    parser.add_argument('--split', choices=('training', 'holdout'), required=True)
    parser.add_argument('--raw-start', type=int, required=True)
    parser.add_argument('--hours', type=int, required=True)
    parser.add_argument('--outage-seed', type=int)
    parser.add_argument('--expected-config-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.name.endswith('_non_authoritative.json') or args.output.exists():
        parser.error('new *_non_authoritative.json output required')
    result = load_source_window(args.kind, args.split, args.raw_start, args.hours,
        outage_seed=args.outage_seed, expected_config_sha256=args.expected_config_sha256)
    record = {'window': result, 'exporter_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(result['window_identity'])


if __name__ == '__main__':
    main()
