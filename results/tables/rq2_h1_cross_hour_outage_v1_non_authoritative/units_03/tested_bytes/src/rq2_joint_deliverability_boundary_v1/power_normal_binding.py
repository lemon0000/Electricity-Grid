"""Source correspondence between a marginal power window and normal inputs."""
from datetime import datetime
from hashlib import sha256
from math import fsum, isfinite
from pathlib import Path

from . import source_normal, source_window


def _alignment(assembly, window):
    inputs = assembly.inputs
    identity = inputs.carry.identity
    if window['kind'] != 'power':
        raise ValueError('power window required')
    if (identity.split != window['split'] or identity.outage_seed != window['outage_seed']
            or identity.trajectory_id != window['chain']['chain_id']):
        raise ValueError('normal carry and power window trajectory identity differ')
    raw = tuple(int(row['source_hour']) for row in window['rows'])
    if (raw != assembly.raw_source_hours or tuple(window['continuous_power_source_hours']) != inputs.source_hours
            or inputs.carry.source_hour != raw[0]):
        raise ValueError('normal and power window source indices differ')
    if len(window['rows']) != len(inputs.request.timestamps):
        raise ValueError('normal and power window horizons differ')
    residuals = []
    for t, row in enumerate(window['rows']):
        if datetime.fromisoformat(row['timestamp']) != inputs.request.timestamps[t]:
            raise ValueError('normal and power window timestamps differ')
        load = float(row['system_load_mw'])
        residual = abs(load-fsum(inputs.request.system_demand_by_bus_mw[t].values()))
        if not isfinite(load) or load < 0 or not isfinite(residual) or residual > 1e-6:
            raise ValueError('normal and power window system load differ')
        residuals.append(residual)
    return max(residuals)


def bind_power_normal(assembly, upstream_root, *, expected_assembly_identity,
                      expected_window_identity, expected_config_sha256,
                      config_path=source_window.audit.DEFAULT_CONFIG):
    """Rebuild both sources and return diagnostic correspondence, never a plan."""
    for digest in (expected_assembly_identity, expected_window_identity, expected_config_sha256):
        source_window._sha(digest)
    rebuilt = source_normal.validate_source_assembly(assembly, upstream_root)
    if rebuilt.assembly_identity != expected_assembly_identity:
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
    residual = _alignment(rebuilt, window)
    result = {'status': 'DRAFT_NONAUTHORITATIVE',
        'normal_assembly_identity': rebuilt.assembly_identity, 'normal_input_identity': rebuilt.normal_identity,
        'power_window_identity': window['window_identity'], 'config_sha256': expected_config_sha256,
        'grid_source_manifest_sha256': rebuilt.source_manifest_sha256,
        'power_package_manifest_sha256': window['package_manifest_sha256'],
        'split': identity.split, 'outage_seed': identity.outage_seed, 'trajectory_id': identity.trajectory_id,
        'raw_source_hours': list(rebuilt.raw_source_hours), 'continuous_source_hours': list(rebuilt.inputs.source_hours),
        'incoming_boundary_hour': rebuilt.inputs.carry.source_hour,
        'source_time_basis': rebuilt.inputs.source_time_basis,
        'maximum_system_load_residual_mw': residual,
        'system_load_comparison_tolerance_mw': 1e-6,
        'implementation_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_adapter_sha256': sha256(Path(source_normal.__file__).read_bytes()).hexdigest(),
        'window_adapter_sha256': sha256(Path(source_window.__file__).read_bytes()).hexdigest(),
        'source_correspondence_verified': True, 'initial_history_authenticated': False,
        'initial_network_feasibility_verified': False, 'normal_assignment_verified': False,
        'outage_dispatch_verified': False, 'registered_coupling': False,
        'business_power_mapping_verified': False, 'formal_result': False, 'solver_calls': 0}
    result['binding_identity'] = source_window._hash(result)
    return result
