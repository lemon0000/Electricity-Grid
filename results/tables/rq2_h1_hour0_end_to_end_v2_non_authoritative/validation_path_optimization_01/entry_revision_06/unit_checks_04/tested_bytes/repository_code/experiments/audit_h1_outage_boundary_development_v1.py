"""Read-only full-catalog boundary inventory; emits non-authoritative JSON."""
import json
from hashlib import sha256
from pathlib import Path

from src.rq2_joint_deliverability_boundary_v1 import source_window as source

CATALOG = Path('results/tables/rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit_v2_final.json')
CATALOG_SHA = '1a31bdd0d69b717525e1d281f4d53d21bf8f8cca929732b76847cfa332843ad1'
CONFIG_SHA = '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'


def audit():
    raw = CATALOG.read_bytes()
    if sha256(raw).hexdigest() != CATALOG_SHA:
        raise ValueError('catalog pin changed')
    source.audit._verify_hash(source.audit.DEFAULT_CONFIG, CONFIG_SHA, 'continuation config')
    config = source.audit._load_config(source.audit.DEFAULT_CONFIG)
    binding = config['inputs']['power']
    package, summary = source.audit._verify_package(binding, 'power')
    source.audit._verify_summary(binding, summary, 'power')
    _, chains, _ = source.audit._power_audit(package, summary, binding)
    rows = source.audit._read_gzip_csv(package/'power_system_blocks.csv.gz', source.audit.POWER_FIELDS)
    families, unresolved = {}, {}
    for family, axes in json.loads(raw)['obligation_catalog']['axes'].items():
        missing = []
        for entry in axes['power']:
            start, end = entry['source_start'], entry['observed_end_inclusive']
            # Retain every original power entry, including right-censored support.
            source._select(rows, chains, 'power', entry['split'], start, end-start+1, entry['outage_seed'])
            try:
                source._select(rows, chains, 'power', entry['split'], start-1, end-start+2, entry['outage_seed'])
            except ValueError as exc:
                key = (entry['split'], entry['outage_seed'], start)
                missing.append(dict(entry=entry, reason=str(exc)))
                unresolved[key] = dict(split=key[0], outage_seed=key[1], raw_start=key[2],
                                       missing_boundary_hour=start-1)
        families[family] = dict(power_entries=len(axes['power']), unresolved_entries=missing,
                               obligations_removed=0)
    source.audit._verify_package(binding, 'power')
    source.audit._verify_hash(source.audit.DEFAULT_CONFIG, CONFIG_SHA, 'continuation config')
    if CATALOG.read_bytes() != raw:
        raise ValueError('catalog changed during audit')
    return dict(status='DRAFT_NONAUTHORITATIVE', catalog_sha256=CATALOG_SHA,
                config_sha256=CONFIG_SHA, package_manifest_sha256=binding['manifest_sha256'],
                script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                families=families, unique_unresolved=[unresolved[k] for k in sorted(unresolved)],
                full_boundary_coverage_verified=not unresolved, obligations_removed=0,
                solver_calls=0, formal_result=False, formal_execution_ready=False,
                resource_admission=False)


if __name__ == '__main__':
    print(json.dumps(audit(), sort_keys=True, indent=2))
