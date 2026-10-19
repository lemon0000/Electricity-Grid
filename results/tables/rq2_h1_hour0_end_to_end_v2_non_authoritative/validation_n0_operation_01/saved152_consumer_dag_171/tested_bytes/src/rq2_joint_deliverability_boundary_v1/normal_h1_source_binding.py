"""Pinned marginal/RTS correspondence for one current H1 observation.

Source audits may scan whole files. Only the selected current row is exposed to
the H1 assembler. This is content correspondence, not native execution authority.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import fsum, isfinite
from pathlib import Path

from . import normal_h1_source as h1
from . import source_normal as rts
from . import source_window as windows


SCHEMA = 'h1_pinned_current_source_correspondence_v1'
WINDOW_FIELDS = frozenset(('status','kind','split','raw_start','hours','outage_seed','config_sha256',
    'package_manifest_sha256','members','chain','rows','continuous_power_source_hours','implementation_sha256',
    'audit_implementation_sha256','python_version','pyyaml_version','solver_calls','formal_result',
    'registered_coupling','shared_observed_clock','continuous_dispatch_verified','workload_fraction_clipped',
    'executable_episode_input','window_identity'))


def _checked_window(value, kind, declaration):
    if type(value) is not dict or set(value) != WINDOW_FIELDS:
        raise ValueError('exact current source window schema required')
    value = deepcopy(value)
    pin = value.pop('window_identity')
    windows._sha(pin)
    if windows._hash(value) != pin:
        raise ValueError('current source window identity mismatch')
    value['window_identity'] = pin
    raw = declaration.power_raw_hour if kind == 'power' else declaration.workload_raw_hour
    seed = declaration.outage_seed if kind == 'power' else None
    if (value['status'] != 'DRAFT_NONAUTHORITATIVE'
            or type(value['kind']) is not str or value['kind'] != kind
            or type(value['split']) is not str or value['split'] != declaration.split
            or type(value['raw_start']) is not int or value['raw_start'] != raw
            or type(value['hours']) is not int or value['hours'] != 1
            or (type(value['outage_seed']) is not int if kind == 'power' else value['outage_seed'] is not None)
            or value['outage_seed'] != seed or value['config_sha256'] != declaration.config_sha256
            or type(value['solver_calls']) is not int or value['solver_calls'] != 0
            or any(value[name] is not False for name in ('formal_result','registered_coupling','shared_observed_clock',
                'continuous_dispatch_verified','workload_fraction_clipped','executable_episode_input'))):
        raise ValueError('current source window coordinates/authority differ from declaration')
    for name in ('config_sha256','package_manifest_sha256','implementation_sha256','audit_implementation_sha256'):
        windows._sha(value[name])
    if (value['implementation_sha256'] != sha256(Path(windows.__file__).read_bytes()).hexdigest()
            or value['audit_implementation_sha256'] != sha256(Path(windows.audit.__file__).read_bytes()).hexdigest()):
        raise ValueError('current source window implementation mismatch')
    continuous = value['continuous_power_source_hours']
    if ((kind == 'power' and (type(continuous) is not list or len(continuous) != 1
            or type(continuous[0]) is not int or continuous[0] != raw+1))
            or (kind == 'workload' and continuous is not None)
            or type(value['rows']) is not list or len(value['rows']) != 1 or type(value['rows'][0]) is not dict):
        raise ValueError('current source window row count/index mismatch')
    row = value['rows'][0]
    field = 'source_hour' if kind == 'power' else 'source_relative_hour'
    if (type(row.get(field)) is not str or row[field] != str(raw)
            or type(row.get('split')) is not str or row['split'] != declaration.split
            or (kind == 'power' and (type(row.get('outage_seed')) is not str or row['outage_seed'] != str(seed)))):
        raise ValueError('current source window canonical row coordinates required')
    return value


@dataclass(frozen=True)
class H1SourceDeclaration:
    split: str
    power_raw_hour: int
    workload_raw_hour: int
    outage_seed: int
    config_sha256: str

    def __post_init__(self):
        if self.split not in ('training', 'holdout') or type(self.split) is not str:
            raise ValueError('explicit source split required')
        for value in (self.power_raw_hour, self.workload_raw_hour, self.outage_seed):
            if type(value) is not int or value < 0:
                raise ValueError('nonnegative built-in source index/seed required')
        windows._sha(self.config_sha256)


@dataclass(frozen=True, init=False)
class H1PinnedObservation(h1._Owned):
    declaration: H1SourceDeclaration
    network: h1.H1StaticNetwork
    row: h1.RtsGmlcHourlyPoint
    raw_workload: str
    source_time_basis: str
    audit_payload: bytes
    identity: str


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def implementation_identity():
    from ..grid import rts_gmlc
    return h1._digest(SCHEMA, tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
        for m in (h1, rts, windows, windows.audit, rts_gmlc)), sha256(Path(__file__).read_bytes()).hexdigest())


def _identity(value):
    h1._network(value.network)
    return h1._digest(SCHEMA, asdict(value.declaration), value.network.identity, value.row,
        value.raw_workload, value.source_time_basis, sha256(value.audit_payload).hexdigest(), implementation_identity())


def load_pinned_current(declaration, upstream_root, *, config_path=windows.audit.DEFAULT_CONFIG):
    """Rebuild from pinned sources; never accept a supplied row as source proof."""
    if type(declaration) is not H1SourceDeclaration:
        raise ValueError('exact H1 source declaration required')
    declaration.__post_init__()
    implementation = implementation_identity()
    manifest = rts._source(upstream_root)
    power = windows.load_source_window('power', declaration.split, declaration.power_raw_hour, 1,
        outage_seed=declaration.outage_seed, config_path=config_path,
        expected_config_sha256=declaration.config_sha256)
    workload = windows.load_source_window('workload', declaration.split, declaration.workload_raw_hour, 1,
        config_path=config_path, expected_config_sha256=declaration.config_sha256)
    power = _checked_window(power, 'power', declaration)
    workload = _checked_window(workload, 'workload', declaration)
    config = windows.audit._load_config(Path(config_path))
    _, summary = windows.audit._verify_package(config['inputs']['power'], 'power')
    if summary.get('grid_source_manifest_sha256') != manifest:
        raise ValueError('marginal power package and RTS manifest differ')
    data = rts.load_rts_gmlc_chronological_data(Path(upstream_root))
    if declaration.power_raw_hour >= len(data.hourly_points):
        raise ValueError('current RTS source hour unavailable')
    row = deepcopy(data.hourly_points[declaration.power_raw_hour])
    if len(power['rows']) != 1 or len(workload['rows']) != 1:
        raise ValueError('current marginal row count/index mismatch')
    p, w = power['rows'][0], workload['rows'][0]
    if (power['continuous_power_source_hours'] != [declaration.power_raw_hour+1]
            or int(p['source_hour']) != declaration.power_raw_hour
            or int(w['source_relative_hour']) != declaration.workload_raw_hour
            or p['split'] != declaration.split or w['split'] != declaration.split
            or int(p['outage_seed']) != declaration.outage_seed):
        raise ValueError('current marginal row count/index mismatch')
    basis = 'naive_source_labelled_utc' if row.timestamp.tzinfo is None else 'aware_source'
    timestamp = row.timestamp.replace(tzinfo=timezone.utc) if basis == 'naive_source_labelled_utc' else row.timestamp
    if datetime.fromisoformat(p['timestamp']) != timestamp:
        raise ValueError('current marginal/RTS timestamp mismatch')
    load = float(p['system_load_mw'])
    residual = abs(load-fsum(row.demand_by_bus_mw.values()))
    if not isfinite(load) or load < 0 or not isfinite(residual) or residual > 1e-6:
        raise ValueError('current marginal/RTS system load mismatch')
    if type(w['workload_fraction']) is not str:
        raise ValueError('raw workload source string required')
    network = h1.static_network(data)
    audit = _bytes(dict(schema=SCHEMA, declaration=asdict(declaration), grid_manifest_sha256=manifest,
        power_window_identity=power['window_identity'], workload_window_identity=workload['window_identity'],
        power_package_manifest_sha256=power['package_manifest_sha256'],
        workload_package_manifest_sha256=workload['package_manifest_sha256'],
        power_chain_identity=windows._hash(power['chain']), workload_chain_identity=windows._hash(workload['chain']),
        power_source_row=p, workload_source_row=w, source_time_basis=basis,
        system_load_residual_mw=residual, system_load_comparison_tolerance_mw=1e-6,
        implementation_identity=implementation, source_correspondence_verified=True, source_files_verified=True,
        source_authenticated=False, selection_registered=False, shared_observed_clock=False,
        source_writer_lock_held=False, hostile_ABA_protected=False, observed_power_mapping=False,
        registered_coupling=False, formal_result=False, native_execution_authenticated=False))
    # Detect ordinary source/config drift around assembly. No source writer lock
    # or hostile ABA protection is claimed.
    if rts._source(upstream_root) != manifest:
        raise ValueError('RTS source changed during current assembly')
    for kind in ('power', 'workload'):
        windows.audit._verify_package(config['inputs'][kind], kind)
    windows.audit._verify_hash(Path(config_path), declaration.config_sha256, 'H1 source config')
    if implementation_identity() != implementation:
        raise ValueError('H1 source binding implementation drift')
    result = h1._owned(H1PinnedObservation, declaration=declaration, network=network, row=row,
        raw_workload=w['workload_fraction'], source_time_basis=basis, audit_payload=audit, identity='')
    return h1._owned(H1PinnedObservation, **{**result.__dict__, 'identity':_identity(result)})


def validate_pinned_current(value, upstream_root, *, expected_identity, config_path=windows.audit.DEFAULT_CONFIG):
    windows._sha(expected_identity)
    if type(value) is not H1PinnedObservation or value.identity != expected_identity or _identity(value) != expected_identity:
        raise ValueError('H1 pinned observation identity mismatch')
    rebuilt = load_pinned_current(value.declaration, upstream_root, config_path=config_path)
    if rebuilt.identity != expected_identity:
        raise ValueError('H1 pinned observation no longer matches current sources')
    return rebuilt


def assemble_pinned_current(value, upstream_root, *, expected_identity, relative_hour, dc_bus,
                            before=None, config_path=windows.audit.DEFAULT_CONFIG):
    """Return the ordinary H1 packet; source lineage stays in the separate receipt.

    No split/seed/raw index/window identity is supplied to the numerical model.
    Mapping may reject retained raw workload >1; a source receipt is not a plan.
    """
    checked = validate_pinned_current(value, upstream_root, expected_identity=expected_identity, config_path=config_path)
    return h1.assemble_current_normal(checked.network, checked.row, checked.raw_workload,
        relative_hour=relative_hour, dc_bus=dc_bus, source_time_basis=checked.source_time_basis, before=before)
