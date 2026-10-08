"""Create one source-bound diagnostic for an explicit draft pairing declaration."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import yaml

from src.rq2_joint_deliverability_boundary_v1 import source_pair, source_window


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration',type=Path,required=True)
    parser.add_argument('--expected-declaration-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.name.endswith('_non_authoritative.json'):
        parser.error('new *_non_authoritative.json output required')
    source_window._sha(args.expected_declaration_sha256)
    raw=args.declaration.read_bytes()
    if sha256(raw).hexdigest()!=args.expected_declaration_sha256:
        raise ValueError('pair declaration hash mismatch')
    fields=yaml.load(raw.decode('utf-8'),Loader=source_window.audit._UniqueKeyLoader)
    if type(fields) is not dict:
        raise ValueError('pair declaration mapping required')
    declaration=source_pair.PairDeclaration(**fields)
    result=source_pair.prepare_source_pair(declaration)
    record={'declaration_sha256':args.expected_declaration_sha256,
        'exporter_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'pair':result}
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(record,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status':result['status'],'rows':len(result['rows']),'pair_identity':result['pair_identity']}))


if __name__=='__main__':
    main()
