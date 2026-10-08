"""Derive or independently verify/build a draft paired dynamic normal input."""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

import yaml

from experiments import audit_rq2_power_normal_binding_v1 as declaration_reader
from src.solvers import rq2_solver_adapter as scale_implementation
from src.rq2_joint_deliverability_boundary_v1 import source_normal, source_pair, source_window, pair_normal_binding
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import build_continuous_normal_model, _dependencies


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('derive','verify'),required=True)
    parser.add_argument('--normal-declaration',type=Path,required=True)
    parser.add_argument('--expected-normal-declaration-sha256',required=True)
    parser.add_argument('--pair-declaration',type=Path,required=True)
    parser.add_argument('--expected-pair-declaration-sha256',required=True)
    parser.add_argument('--expected-pair-identity',required=True)
    parser.add_argument('--expected-assembly-identity')
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.name.endswith('_non_authoritative.json'):
        parser.error('new *_non_authoritative.json output required')
    if (args.mode=='verify')!=(args.expected_assembly_identity is not None):
        parser.error('external assembly identity is required only in verify mode')
    for digest in (args.expected_normal_declaration_sha256,args.expected_pair_declaration_sha256,args.expected_pair_identity):
        source_window._sha(digest)
    if args.expected_assembly_identity is not None:
        source_window._sha(args.expected_assembly_identity)
    normal_bytes=args.normal_declaration.read_bytes()
    pair_bytes=args.pair_declaration.read_bytes()
    if (sha256(normal_bytes).hexdigest()!=args.expected_normal_declaration_sha256
            or sha256(pair_bytes).hexdigest()!=args.expected_pair_declaration_sha256):
        raise ValueError('source declaration hash mismatch')
    d=source_pair.PairDeclaration(**yaml.load(pair_bytes.decode('utf-8'),Loader=source_window.audit._UniqueKeyLoader))
    pair=source_pair.prepare_source_pair(d)
    if pair['pair_identity']!=args.expected_pair_identity:
        raise ValueError('independent pair identity mismatch')
    if pair['status']!='staged' or pair['hours'] is None:
        raise ValueError('complete pair required before normal assembly')
    original=json.loads(normal_bytes)
    source_identity={'split':d.split,'outage_seed':d.outage_seed,
        'chain':{'chain_id':pair['hours'][0]['power_trajectory_id']}}
    request,initial,carry=declaration_reader.declared_inputs(original,source_identity)
    request=replace(request,dc_requested_mw=tuple(r['workload_projection']['dc_baseline_mw'] for r in pair['rows']))
    assembly=source_normal.assemble_source_normal(args.source_root,
        tuple(range(d.power_raw_start,d.power_raw_start+d.hours)),request,initial,carry,
        source_time_basis=original['source_time_basis'])
    binding=None
    scale=None
    if args.mode=='verify':
        binding=pair_normal_binding.bind_pair_normal(assembly,args.source_root,d,
            expected_assembly_identity=args.expected_assembly_identity,expected_pair_identity=args.expected_pair_identity)
        model=build_continuous_normal_model(assembly.inputs,expected_identity=binding['normal_input_identity'])
        scale=asdict(scale_implementation.model_scale(model))
    record={'status':'DRAFT_NONAUTHORITATIVE','mode':args.mode,
        'normal_declaration_sha256':args.expected_normal_declaration_sha256,
        'pair_declaration_sha256':args.expected_pair_declaration_sha256,
        'pair_identity':pair['pair_identity'],'normal_assembly_identity':assembly.assembly_identity,
        'normal_input_identity':assembly.normal_identity,'expected_assembly_identity':args.expected_assembly_identity,
        'external_assembly_identity_verified':args.mode=='verify',
        'request':asdict(request),'initial':asdict(initial),'carry':asdict(carry),
        'original_dc_requested_mw':original['request']['dc_requested_mw'],
        'declaration_role':'explicit_mechanism_input_not_executable_checkpoint',
        'binding':binding,'model_scale':scale,'model_builds':int(args.mode=='verify'),
        'solver_calls':0,'normal_assignment_verified':False,'formal_result':False,
        'source_time_basis':assembly.inputs.source_time_basis,'dependencies':_dependencies(),
        'extra_implementation_sha256':{name:sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in [('declaration_reader',declaration_reader),('source_normal',source_normal),
                ('source_pair',source_pair),('pair_normal_binding',pair_normal_binding),('model_scale',scale_implementation)]},
        'runner_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    def encode(obj):
        if isinstance(obj,frozenset):return sorted(obj)
        if hasattr(obj,'isoformat'):return obj.isoformat()
        raise TypeError(type(obj).__name__)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(record,stream,sort_keys=True,indent=2,default=encode,allow_nan=False)
        stream.write('\n')
    print(json.dumps({'mode':args.mode,'assembly_identity':assembly.assembly_identity,'model_scale':scale}))


if __name__=='__main__':main()
