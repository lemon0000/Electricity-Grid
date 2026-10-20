"""Bind staged pair power to a supplied normal counterfactual; no solve."""
from copy import deepcopy
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from . import power_normal_binding, source_pair, source_window


def bind_pair_normal(assembly, upstream_root, declaration, *, expected_assembly_identity,
                     expected_pair_identity, config_path=source_window.audit.DEFAULT_CONFIG):
    source_window._sha(expected_assembly_identity)
    source_window._sha(expected_pair_identity)
    pair=source_pair.prepare_source_pair(declaration,config_path=config_path)
    if pair['pair_identity']!=expected_pair_identity:
        raise ValueError('independent pair identity mismatch')
    if pair['status']!='staged' or pair['hours'] is None:
        raise ValueError('complete staged pair required; unresolved hours cannot be skipped')
    # Hold a private snapshot while source/baseline correspondence is checked.
    snapshot=deepcopy(assembly)
    power=power_normal_binding.bind_power_normal(snapshot,upstream_root,
        expected_assembly_identity=expected_assembly_identity,
        expected_window_identity=declaration.power_window_identity,
        expected_config_sha256=declaration.config_sha256,config_path=config_path)
    inputs=snapshot.inputs
    if len(inputs.request.dc_requested_mw)!=len(pair['hours']):
        raise ValueError('normal/pair baseline horizon differs')
    projected=tuple(row['workload_projection']['dc_baseline_mw'] for row in pair['rows'])
    for i,(baseline,hour,planned) in enumerate(zip(inputs.request.dc_requested_mw,pair['hours'],projected,strict=True)):
        if (inputs.source_hours[i]!=hour['power_source_hour']
                or Q(str(baseline))!=Q(str(planned))
                or Q(str(hour['workload_occupancy']))*Q(declaration.normalized_unit_mw)!=Q(str(baseline))):
            raise ValueError('normal baseline differs from exact paired business power')
    result={'status':'DRAFT_NONAUTHORITATIVE','pair_identity':pair['pair_identity'],
        'normal_assembly_identity':power['normal_assembly_identity'],
        'normal_input_identity':power['normal_input_identity'],'power_binding':power,
        'mapping':pair['mapping'],'dc_baseline_mw':list(projected),
        'power_source_hours':[h['power_source_hour'] for h in pair['hours']],
        'workload_source_hours':[h['workload_source_hour'] for h in pair['hours']],
        'implementation_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'pair_implementation_sha256':sha256(Path(source_pair.__file__).read_bytes()).hexdigest(),
        'power_binding_implementation_sha256':sha256(Path(power_normal_binding.__file__).read_bytes()).hexdigest(),
        'dynamic_baseline_correspondence_verified':True,
        'normal_assignment_verified':False,'initial_network_feasibility_verified':False,
        'registered_coupling':False,'observed_power_mapping':False,'causal_certificate':None,
        'formal_result':False,'solver_calls':0}
    result['binding_identity']=source_window._hash(result)
    return result
