"""Offline full-source scalar representability audit; never a policy input."""
from collections import Counter
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
import json

import yaml
from experiments import audit_rq2_workload_projection_v1 as source
from experiments import h1_exact_business_development_v1 as business

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL='configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
PROTOCOL_SHA='95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430'
CONFIG_SHA='0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'


def audit():
    protocol_bytes=(ROOT/PROTOCOL).read_bytes()
    if sha256(protocol_bytes).hexdigest()!=PROTOCOL_SHA:raise ValueError('frozen protocol drift')
    protocol=yaml.safe_load(protocol_bytes)
    fs=protocol['design']['primary_factorial']['flexible_fraction']
    if fs!=['0.05','0.20','0.50'] or protocol['business_anchor']['flexible_fraction'] not in fs:
        raise ValueError('registered flexible fraction inventory differs')
    mapping=protocol['source_mapping']
    if (mapping['normalized_power_unit_mw'],mapping['workload_projection_decimal_places'])!=('250',12):
        raise ValueError('mapping declaration differs')
    implementation=business.implementation_identity()
    original=source.audit('250',12,CONFIG_SHA)
    rows=[];counts=Counter()
    for row in original['rows']:
        projection=row['projection'];split=row['source_row']['split'];checks=[]
        for fraction in fs:
            if projection['status']!='projected':
                checks.append(dict(f=fraction,status='source_mapping_unresolved',
                    reason=projection['reason'],available_exact=None,builtin=None))
                counts[split+':source_mapping_unresolved']+=1
                continue
            w=Q(*map(int,projection['projected_fraction_exact']))
            if Q(str(projection['workload_occupancy']))!=w:raise ValueError('source projection identity differs')
            q=Q(fraction)*w
            try:
                value=business.lossless_builtin(q)
                if Q(str(value))!=q:raise AssertionError('adapter changed exact scalar')
                checks.append(dict(f=fraction,status='lossless',available_exact=str(q),builtin=value))
                counts[split+':lossless']+=1
            except ValueError as error:
                checks.append(dict(f=fraction,status='interface_unresolved',available_exact=str(q),reason=str(error)))
                counts[split+':interface_unresolved']+=1
        rows.append(dict(source_row=row['source_row'],projection=projection,checks=checks))
    if (source.audit('250',12,CONFIG_SHA)!=original or business.implementation_identity()!=implementation
            or (ROOT/PROTOCOL).read_bytes()!=protocol_bytes):
        raise ValueError('source/protocol/implementation changed during audit')
    return dict(schema='h1_exact_business_interface_development_audit_v1',status='DRAFT_NONAUTHORITATIVE',
        protocol_sha256=PROTOCOL_SHA,implementation_identity=implementation,
        source_audit={k:v for k,v in original.items() if k!='rows'},rows=rows,counts=dict(sorted(counts.items())),
        source_rows_retained=len(rows),checks_retained=sum(len(r['checks']) for r in rows),
        source_rows_removed=0,policy_input=False,operational_source_binding_verified=False,
        full_business_feasibility_verified=False,formal_result=False,real_native_calls=0,synthetic_jobs=0,
        runner_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    path=Path(args.output)
    if not any(p.endswith('_non_authoritative') for p in path.parts):
        raise ValueError('non_authoritative output required')
    result=audit()
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(counts=result['counts'],source_rows_retained=result['source_rows_retained'],
        checks_retained=result['checks_retained'],sha256=sha256(path.read_bytes()).hexdigest())))
