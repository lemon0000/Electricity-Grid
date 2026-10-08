"""Full marginal numerical projection audit; parameters are development declarations."""
import argparse
from collections import Counter
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import platform

import yaml

from src.rq2_joint_deliverability_boundary_v1 import continuation_audit as source
from src.rq2_joint_deliverability_boundary_v1 import workload_projection as projection


def audit(unit, places, expected_config_sha256):
    projection.project_workload_power('0',unit,decimal_places=places)
    if (type(expected_config_sha256) is not str or len(expected_config_sha256)!=64
            or any(c not in '0123456789abcdef' for c in expected_config_sha256)):
        raise ValueError('canonical config SHA256 required')
    config=source.DEFAULT_CONFIG
    source._verify_hash(config,expected_config_sha256,'projection config')
    binding=source._load_config(config)['inputs']['workload']
    package,summary=source._verify_package(binding,'workload')
    source._verify_summary(binding,summary,'workload')
    inventory,chains=source._workload_audit(package,summary,binding)
    rows=source._read_gzip_csv(package/'workload_blocks.csv.gz',source.WORKLOAD_FIELDS)
    counts={split:Counter() for split in ('training','holdout')}
    maximum_error={split:Q(0) for split in counts}
    records=[]
    for row in rows:
        result=projection.project_workload_power(row['workload_fraction'],unit,decimal_places=places)
        count=counts[row['split']]
        raw=Q(row['workload_fraction']); projected_float=Q(str(float(raw)))
        count['rows']+=1
        count['raw_above_one']+=raw>1
        count['raw_decimal_float_projection_changed']+=raw!=projected_float
        if raw<=1:
            count['within_unit_rows']+=1
            try:
                naive=Q(str(float(projected_float*Q(unit))))
                count['decimal_product_float_projection_identity_fails']+=naive!=projected_float*Q(unit)
            except (OverflowError,ValueError):
                count['decimal_product_float_projection_identity_fails']+=1
            try:
                binary_product=Q(str(float(raw)*float(Q(unit))))
                count['binary_float_multiplication_identity_fails']+=binary_product!=projected_float*Q(unit)
            except (OverflowError,ValueError):
                count['binary_float_multiplication_identity_fails']+=1
        count[result['status']]+=1
        if result['reason'] is not None:
            count[result['reason']]+=1
        if result['projection_error_exact'] is not None:
            error=abs(Q(*map(int,result['projection_error_exact'])))
            maximum_error[row['split']]=max(maximum_error[row['split']],error)
        records.append({'source_row':row,'projection':result})
    source._verify_package(binding,'workload')
    source._verify_hash(config,expected_config_sha256,'projection config')
    return {'status':'DRAFT_NONAUTHORITATIVE','normalized_unit_mw':unit,'decimal_places':places,
        'parameter_role':'mechanism_assumption','formal_parameters_registered':False,
        'config_sha256':expected_config_sha256,'package_manifest_sha256':binding['manifest_sha256'],
        'members':binding['members'],'source_inventory':inventory,'source_chains':chains,
        'counts':{k:dict(v) for k,v in counts.items()},
        'comparison_methods':{
            'decimal_product_float_projection_identity_fails':'Q(str(float(Q(str(float(raw)))*Q(unit)))) != Q(str(float(raw)))*Q(unit)',
            'binary_float_multiplication_identity_fails':'Q(str(float(raw)*float(Q(unit)))) != Q(str(float(raw)))*Q(unit)'},
        'maximum_absolute_projection_error_exact':{k:projection._ratio(v) for k,v in maximum_error.items()},
        'rows':records,'solver_calls':0,'formal_result':False,'executable_episode_input':False,
        'observed_power_mapping':False,'registered_coupling':False,
        'python_version':platform.python_version(),'pyyaml_version':yaml.__version__,
        'runner_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'projection_sha256':sha256(Path(projection.__file__).read_bytes()).hexdigest(),
        'source_audit_sha256':sha256(Path(source.__file__).read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normalized-unit-mw',required=True)
    parser.add_argument('--decimal-places',type=int,required=True)
    parser.add_argument('--expected-config-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.output.name.endswith('_non_authoritative.json'):
        parser.error('new *_non_authoritative.json output required')
    result=audit(args.normalized_unit_mw,args.decimal_places,args.expected_config_sha256)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False)
        stream.write('\n')
    print(json.dumps(result['counts'],sort_keys=True))


if __name__=='__main__':
    main()
