"""Frozen-generator provenance audit; generated boundaries are not H1 inputs."""
import csv
import gzip
from hashlib import sha256
import json
from pathlib import Path

import yaml

from experiments import build_rts_gmlc_public_power_system_blocks as builder
from src.scenarios import rts_gmlc_n1_chronology as chronology

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'configs/rts_gmlc_public_power_system_blocks_v4.yaml'
CONFIG_SHA = 'cefec120fb77990a47fe7e89a77e4df8be00bde5bf7e4cd4c5ca047d52934688'
PACKAGE_SHA = '28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63'
GAPS = ROOT/'results/tables/rq2_h1_outage_source_v1_non_authoritative/boundary_coverage.json'
GAPS_SHA = 'a1d5bcafde41ed9bf9a3d3c4d46ebaf6bd0a57641837d3937e9dda18e31a3dc8'


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _read_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def _overlay(event):
    return ('', '', '') if event is None else (event.event_id, event.component_type, event.uid)


def prefix_overlay(components, seed, source_hour):
    """Reproduce only a nonnegative source prefix, never a virtual hour -1."""
    if type(source_hour) is not int or source_hour < 0:
        raise ValueError('no generated predecessor exists before chronology hour zero')
    events = chronology.simulate_n_minus_one_events(components, seed=seed, horizon_hours=source_hour+1)
    timeline = chronology.event_by_hour(events, horizon_hours=source_hour+1)
    # Event ends can be clipped by the horizon. Only component/ID is compared.
    return tuple(_overlay(event) for event in timeline)


def audit():
    if _hash(CONFIG) != CONFIG_SHA or _hash(GAPS) != GAPS_SHA:
        raise ValueError('frozen generator config or gap evidence changed')
    config = yaml.safe_load(CONFIG.read_bytes())
    package = ROOT/config['output']['directory']
    builder._verify_package(package, PACKAGE_SHA)
    summary = json.loads((package/'summary.json').read_bytes())
    pins = {CONFIG: CONFIG_SHA, GAPS: GAPS_SHA, Path(builder.__file__): summary['implementation_sha256'],
            Path(chronology.__file__): summary['n1_chronology_module_sha256'],
            Path(__file__): _hash(__file__)}
    if any(_hash(path) != digest for path, digest in pins.items()):
        raise ValueError('frozen generator implementation drift')
    source = config['source']
    builder.validate_rts_gmlc_source_identity(source)
    grid = ROOT/source['grid_root']
    if _hash(grid/'SHA256SUMS') != source['grid_manifest_sha256'] or not builder.verify_sha256_manifest(grid):
        raise ValueError('upstream grid manifest drift')
    builder._verify_package(ROOT/source['cfe_package'], source['cfe_manifest_sha256'])
    components, _, _ = builder._components(grid,
        excluded_generator_unit_types=frozenset(config['derivation']['excluded_generator_unit_types']))
    power = _read_rows(package/'power_system_blocks.csv.gz')
    frozen_events = _read_rows(package/'n1_outage_events.csv.gz')
    horizon = summary['hours']
    split_hour = summary['split_hour']
    generated_rows, full = [], {}
    for seed in config['derivation']['outage_seeds']:
        events = chronology.simulate_n_minus_one_events(components, seed=seed, horizon_hours=horizon)
        full[seed] = tuple(_overlay(e) for e in chronology.event_by_hour(events, horizon_hours=horizon))
        for event in events:
            generated_rows.append(dict(outage_seed=str(seed), event_id=event.event_id,
                component_type=event.component_type, component_uid=event.uid,
                start_hour=str(event.start_hour), end_hour_exclusive=str(event.end_hour_exclusive),
                duration_hours=str(event.duration_hours),
                crosses_split=str(event.start_hour < split_hour < event.end_hour_exclusive)))
    if generated_rows != frozen_events:
        raise ValueError('generated chronology differs from frozen event table')
    for row in power:
        if full[int(row['outage_seed'])][int(row['source_hour'])] != tuple(
                row[k] for k in ('active_event_id', 'active_component_type', 'active_component_uid')):
            raise ValueError('generated chronology differs from frozen visible power row')
    receipts = []
    for gap in json.loads(GAPS.read_bytes())['unique_unresolved']:
        seed, boundary = gap['outage_seed'], gap['missing_boundary_hour']
        if boundary < 0:
            zero = prefix_overlay(components, seed, 0)[0]
            receipts.append(dict(**gap, status='unresolved_no_negative_hour_in_generator',
                hour_zero_overlay_for_proposal_only=zero, generated_predecessor=None,
                operational_source_authorized=False))
            continue
        if gap['split'] != 'holdout' or boundary < split_hour:
            raise ValueError('supplement is not a same-split holdout boundary')
        prefix = prefix_overlay(components, seed, boundary)
        if prefix != full[seed][:boundary+1]:
            raise ValueError('horizon extension changes a past component overlay')
        visible = [row for row in power if int(row['outage_seed']) == seed
                   and int(row['source_hour']) <= boundary]
        if any(prefix[int(row['source_hour'])] != tuple(row[k] for k in
               ('active_event_id', 'active_component_type', 'active_component_uid')) for row in visible):
            raise ValueError('prefix regeneration differs from available past observations')
        eid, kind, uid = prefix[-1]
        receipts.append(dict(**gap, status='audit_only_generated_boundary',
            generated_predecessor=dict(active_event_id=eid, active_component_type=kind, active_component_uid=uid),
            generator_horizon_hours=boundary+1, existing_past_rows_compared=len(visible),
            horizon_extension_prefix_equal=True, operational_source_authorized=False))
    builder._verify_package(package, PACKAGE_SHA)
    builder._verify_package(ROOT/source['cfe_package'], source['cfe_manifest_sha256'])
    if (not builder.verify_sha256_manifest(grid)
            or any(_hash(path) != digest for path, digest in pins.items())):
        raise ValueError('source or implementation changed during origin audit')
    return dict(schema='h1_outage_origin_replay_development_v1', status='DRAFT_NONAUTHORITATIVE',
        files_sha256={path.relative_to(ROOT).as_posix(): digest for path, digest in pins.items()},
        package_manifest_sha256=PACKAGE_SHA, grid_manifest_sha256=source['grid_manifest_sha256'],
        cfe_manifest_sha256=source['cfe_manifest_sha256'], reliability_components=len(components),
        event_rows_compared=len(frozen_events), visible_power_rows_compared=len(power),
        source_horizon_hours=horizon, split_hour=split_hour, receipts=receipts,
        derivation_role='synthetic_generator_provenance_not_observed_boundary',
        full_event_table_role='offline_oracle_only_not_boundary_derivation_input',
        operational_source_authorized=False, full_boundary_coverage_verified=False,
        unique_operational_inputs_unresolved=len(receipts), obligations_removed=0,
        repair_cap_source_registered=False, resource_admission=False,
        formal_execution_ready=False, formal_result=False, native_execution_authorized=False,
        solver_calls=0, synthetic_jobs=0)


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True, indent=2))
