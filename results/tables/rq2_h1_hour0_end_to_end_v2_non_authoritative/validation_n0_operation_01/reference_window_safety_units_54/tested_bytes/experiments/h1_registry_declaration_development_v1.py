"""Pre-execution registry identity declaration; detached development metadata.

No row decoder, source window, owner or execution capability is opened here.
Consumers must separately validate the selected window using registry.prepare.
"""
import json
from pathlib import Path

from experiments import h1_phase_manifest_group_development_v1 as group
from experiments import h1_outage_registry_development_v1 as registry

io, ROOT = group.io, group.ROOT
SCHEMA = 'h1_registry_declaration_development_v1'
BASELINE = ROOT/'results/tables/rq2_h1_phase_manifest_group_v1_non_authoritative/development_checks.json'
BASELINE_PIN = '2097c351a76d3880b404558373519b75d81d123d1090de1972b7e0a0e952bc99'
CAP = group.symbolic.proof.exclusion.INPUT_CAP
DECLARATION_CAP = 16384


def _views():
    baseline = io.read_stable(BASELINE,CAP)
    if io.digest(baseline[0]) != BASELINE_PIN:
        raise ValueError('pinned declaration predecessor differs')
    views = {BASELINE:baseline}
    for name,pin in json.loads(baseline[0])['files_sha256'].items():
        path = ROOT/name
        view = io.read_stable(path,CAP)
        if io.digest(view[0]) != pin:
            raise ValueError('pinned declaration dependency differs')
        views[path] = view
    views[Path(__file__)] = io.read_stable(Path(__file__),CAP)
    return views


def build(split):
    """Build canonical bytes offline; the caller must retain an external hash."""
    if type(split) is not str or split not in ('training','holdout'):
        raise ValueError('explicit source split required')
    views = _views()
    def pinned(path,pin):
        view = views[Path(path)]
        if io.digest(view[0]) != pin: raise ValueError('registry declaration input differs')
        return json.loads(view[0])
    authority = pinned(registry.AUTHORITY,registry.AUTHORITY_SHA)
    archive = pinned(registry.ARCHIVE/'manifest.json',registry.ARCHIVE_SHA)
    member = archive['members'][split]
    if io.digest(views[registry.ARCHIVE/member['path']][0]) != member['sha256']:
        raise ValueError('selected archive member differs')
    implementation = registry.implementation_identity()
    basis = dict(schema=registry.SCHEMA,authority=registry.AUTHORITY_SHA,
        archive=registry.ARCHIVE_SHA,source_package=registry.frozen.PACKAGE_SHA,
        cap_table=authority['cap_table_sha256'],catalog=registry.catalog.CATALOG_SHA,
        implementation=implementation)
    body = dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',split=split,
        expected_registry_identity=registry.old.source._hash(basis),registry_identity_basis=basis,
        selected_archive_member=member,predecessor_checks_sha256=BASELINE_PIN,
        declaration_implementation_sha256=io.digest(views[Path(__file__)][0]),
        source_window_validated=False,normal_source_correspondence_verified=False,
        synthetic_mechanism_not_empirical=True,detached_consumer_authenticated=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False,
        native_execution_authorized=False)
    raw = io.encode(body)
    if len(raw)>DECLARATION_CAP: raise ValueError('declaration exceeds byte cap')
    if registry.implementation_identity()!=implementation:
        raise ValueError('registry implementation changed')
    for path,view in views.items():
        if io.read_stable(path,CAP)!=view:
            raise ValueError('declaration dependency changed during build')
    return raw


def inspect(path, *, expected_sha256, split):
    """Rebuild a previously retained declaration; no identity discovery fallback."""
    io.pin(expected_sha256)
    path = Path(path)
    before = io.read_stable(path,DECLARATION_CAP)
    if io.digest(before[0]) != expected_sha256:
        raise ValueError('external declaration pin differs')
    rebuilt = build(split)
    if before[0] != rebuilt:
        raise ValueError('declaration reconstruction differs')
    if io.read_stable(path,DECLARATION_CAP)!=before:
        raise ValueError('declaration changed during inspect')
    return json.loads(rebuilt)
