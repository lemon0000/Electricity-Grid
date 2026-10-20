"""Streaming source/pair correspondence with separate content and implementation pins.

The legacy-format report is a content reference, never an execution claim.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

from . import source_normal_stream as source, source_window, source_pair
from . import power_normal_binding as old_power, pair_normal_binding as old_pair

CONTRACT = 'draft_streaming_pair_normal_binding_v1'


def implementation_identity():
    modules = (source, source_window, source_pair, source_pair.workload_projection,
        source_window.audit, old_power, old_pair)
    root = Path(__file__).resolve().parents[2]
    paths = (Path(__file__), *(Path(module.__file__) for module in modules))
    return source.stream.digest(CONTRACT, source.implementation_identity(),
        tuple((path.relative_to(root).as_posix(), sha256(path.read_bytes()).hexdigest()) for path in paths))


@dataclass(frozen=True)
class StreamingPairBinding:
    normal_identity: str
    source_assembly_identity: str
    pair_identity: str
    legacy_content_json: str
    legacy_content_binding_identity: str
    implementation_identity: str
    binding_identity: str


def _legacy_power_content(rebuilt, *, expected_assembly_identity,
                      expected_window_identity, expected_config_sha256,
                      config_path=source_window.audit.DEFAULT_CONFIG):
    """Legacy-format content reference only; this is not execution provenance."""
    for digest in (expected_assembly_identity, expected_window_identity, expected_config_sha256):
        source_window._sha(digest)
    if rebuilt.legacy_content_assembly_identity != expected_assembly_identity:
        raise ValueError('independent normal assembly identity mismatch')
    identity = rebuilt.inputs.carry.identity
    window = source_window.load_source_window('power', identity.split,
        rebuilt.raw_source_hours[0], len(rebuilt.raw_source_hours), outage_seed=identity.outage_seed,
        config_path=config_path, expected_config_sha256=expected_config_sha256)
    if window['window_identity'] != expected_window_identity:
        raise ValueError('independent power window identity mismatch')
    config = source_window.audit._load_config(Path(config_path))
    _, summary = source_window.audit._verify_package(config['inputs']['power'], 'power')
    source_window.audit._verify_hash(Path(config_path), expected_config_sha256, 'binding config')
    if summary.get('grid_source_manifest_sha256') != rebuilt.source_manifest_sha256:
        raise ValueError('power package and normal grid source manifest differ')
    residual = old_power._alignment(rebuilt, window)
    result = {'status': 'DRAFT_NONAUTHORITATIVE',
        'normal_assembly_identity': rebuilt.legacy_content_assembly_identity, 'normal_input_identity': rebuilt.normal_identity,
        'power_window_identity': window['window_identity'], 'config_sha256': expected_config_sha256,
        'grid_source_manifest_sha256': rebuilt.source_manifest_sha256,
        'power_package_manifest_sha256': window['package_manifest_sha256'],
        'split': identity.split, 'outage_seed': identity.outage_seed, 'trajectory_id': identity.trajectory_id,
        'raw_source_hours': list(rebuilt.raw_source_hours), 'continuous_source_hours': list(rebuilt.inputs.source_hours),
        'incoming_boundary_hour': rebuilt.inputs.carry.source_hour,
        'source_time_basis': rebuilt.inputs.source_time_basis,
        'maximum_system_load_residual_mw': residual,
        'system_load_comparison_tolerance_mw': 1e-6,
        'implementation_sha256': sha256(Path(old_power.__file__).read_bytes()).hexdigest(),
        'source_adapter_sha256': sha256(Path(source.legacy.__file__).read_bytes()).hexdigest(),
        'window_adapter_sha256': sha256(Path(source_window.__file__).read_bytes()).hexdigest(),
        'source_correspondence_verified': True, 'initial_history_authenticated': False,
        'initial_network_feasibility_verified': False, 'normal_assignment_verified': False,
        'outage_dispatch_verified': False, 'registered_coupling': False,
        'business_power_mapping_verified': False, 'formal_result': False, 'solver_calls': 0}
    result['binding_identity'] = source_window._hash(result)
    return result


def bind_pair_normal(assembly, upstream_root, declaration, *, expected_assembly_identity,
                     expected_pair_identity, expected_source_implementation_identity,
                     expected_implementation_identity, config_path=source_window.audit.DEFAULT_CONFIG):
    for pin in (expected_assembly_identity, expected_pair_identity,
                expected_source_implementation_identity, expected_implementation_identity):
        source._pin(pin)
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('streaming binding implementation drift')
    if type(assembly) is not source.StreamingSourceNormalAssembly:
        raise ValueError('typed streaming source assembly required')
    if assembly.assembly_identity != expected_assembly_identity:
        raise ValueError('independent streaming assembly identity mismatch')
    pair = source_pair.prepare_source_pair(declaration, config_path=config_path)
    if pair['pair_identity'] != expected_pair_identity:
        raise ValueError('independent pair identity mismatch')
    if pair['status'] != 'staged' or pair['hours'] is None:
        raise ValueError('complete staged pair required; unresolved hours cannot be skipped')
    # Reassembly owns the verified input snapshot. Do not make another annual
    # data copy solely to hold the baseline while checking correspondence.
    rebuilt = source.validate_source_assembly(assembly, upstream_root,
        expected_implementation_identity=expected_source_implementation_identity)
    if rebuilt.assembly_identity != expected_assembly_identity:
        raise ValueError('independent streaming assembly identity mismatch')
    power = _legacy_power_content(rebuilt,
        expected_assembly_identity=rebuilt.legacy_content_assembly_identity,
        expected_window_identity=declaration.power_window_identity,
        expected_config_sha256=declaration.config_sha256, config_path=config_path)
    inputs = rebuilt.inputs
    if len(inputs.request.dc_requested_mw) != len(pair['hours']):
        raise ValueError('normal/pair baseline horizon differs')
    projected = tuple(row['workload_projection']['dc_baseline_mw'] for row in pair['rows'])
    for i, (baseline, hour, planned) in enumerate(zip(inputs.request.dc_requested_mw, pair['hours'], projected, strict=True)):
        if (inputs.source_hours[i] != hour['power_source_hour']
                or Q(str(baseline)) != Q(str(planned))
                or Q(str(hour['workload_occupancy']))*Q(declaration.normalized_unit_mw) != Q(str(baseline))):
            raise ValueError('normal baseline differs from exact paired business power')
    content = {'status':'DRAFT_NONAUTHORITATIVE','pair_identity':pair['pair_identity'],
        'normal_assembly_identity':power['normal_assembly_identity'],
        'normal_input_identity':power['normal_input_identity'],'power_binding':power,
        'mapping':pair['mapping'],'dc_baseline_mw':list(projected),
        'power_source_hours':[h['power_source_hour'] for h in pair['hours']],
        'workload_source_hours':[h['workload_source_hour'] for h in pair['hours']],
        'implementation_sha256':sha256(Path(old_pair.__file__).read_bytes()).hexdigest(),
        'pair_implementation_sha256':sha256(Path(source_pair.__file__).read_bytes()).hexdigest(),
        'power_binding_implementation_sha256':sha256(Path(old_power.__file__).read_bytes()).hexdigest(),
        'dynamic_baseline_correspondence_verified':True,
        'normal_assignment_verified':False,'initial_network_feasibility_verified':False,
        'registered_coupling':False,'observed_power_mapping':False,'causal_certificate':None,
        'formal_result':False,'solver_calls':0}
    content['binding_identity'] = source_window._hash(content)
    wire = json.dumps(content, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    identity = source.stream.digest(CONTRACT, rebuilt.normal_identity, expected_assembly_identity,
        expected_pair_identity, wire, expected_implementation_identity)
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('streaming binding implementation drift')
    return StreamingPairBinding(rebuilt.normal_identity, expected_assembly_identity,
        expected_pair_identity, wire, content['binding_identity'], expected_implementation_identity, identity)
