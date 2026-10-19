"""Fresh bounded reads of the predecessor registry declaration projection.

The returned compatibility bytes retain the predecessor schema and identity.
A separate mandatory receipt names this verifier. No source observation is
cached across calls and no execution or reuse credential is issued.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import types

from experiments import h1_registry_declaration_development_v1 as predecessor
from experiments import h1_phase_dependency_verifier_development_v1 as bounded

SCHEMA = 'h1_registry_declaration_development_v2'
PREDECESSOR_SHA256 = '6c6162c4819a45b7b759e174cb44c18aef0a24f8ec24cc73f3d269e9746abf8a'
DECLARATION_CAP = predecessor.DECLARATION_CAP
_TOKEN = object()


@dataclass(frozen=True, init=False)
class VerifiedRegistryDeclaration:
    compatibility_raw: bytes
    verification_receipt: bytes

def _bind():
    prior, reader_module = predecessor, bounded
    io, registry = prior.io, prior.registry
    read, encode, digest, pin = reader_module.read_stable, io.encode, io.digest, io.pin
    json_module, path_type = json, Path
    decode, ftype = json.loads, types.FunctionType
    root, baseline, baseline_pin, cap = prior.ROOT, prior.BASELINE, prior.BASELINE_PIN, prior.CAP
    declaration_cap = DECLARATION_CAP
    prior_path, own_path = Path(prior.__file__), Path(__file__)
    reader_path = Path(reader_module.__file__)
    own_pin = digest(read(own_path, cap)[0])
    reader_pin = digest(read(reader_path, cap)[0])
    token, result_type = _TOKEN, VerifiedRegistryDeclaration
    module_namespace = globals()
    prior_schema, registry_schema = prior.SCHEMA, registry.SCHEMA
    authority_path, authority_pin = registry.AUTHORITY, registry.AUTHORITY_SHA
    archive_path, archive_pin = registry.ARCHIVE, registry.ARCHIVE_SHA
    frozen, catalog, old = registry.frozen, registry.catalog, registry.old
    old_source = old.source
    package_pin, catalog_pin = frozen.PACKAGE_SHA, catalog.CATALOG_SHA
    source_hash = old_source._hash
    verification_identity = digest(encode([SCHEMA, own_pin, PREDECESSOR_SHA256, reader_pin]))
    constants = tuple((owner, name, getattr(owner, name)) for owner, names in (
        (prior, ('SCHEMA',)), (registry, ('SCHEMA', 'AUTHORITY', 'AUTHORITY_SHA', 'ARCHIVE', 'ARCHIVE_SHA')),
        (frozen, ('PACKAGE_SHA',)), (catalog, ('CATALOG_SHA',))) for name in names)
    expected = ()

    def state(value):
        if type(value) is ftype:
            return (id(value), id(value.__code__), repr(value.__defaults__), repr(value.__kwdefaults__))
        return (id(value),)

    def check():
        for target, name, value, identity in expected:
            live = target.get(name) if type(target) is dict else vars(target).get(name)
            if live is not value or state(live) != identity:
                raise ValueError('registry declaration verifier dispatch changed: ' + name)
        if (prior.ROOT != root or prior.BASELINE != baseline or prior.BASELINE_PIN != baseline_pin
                or prior.CAP != cap or DECLARATION_CAP != declaration_cap
                or SCHEMA != 'h1_registry_declaration_development_v2'
                or PREDECESSOR_SHA256 != '6c6162c4819a45b7b759e174cb44c18aef0a24f8ec24cc73f3d269e9746abf8a'):
            raise ValueError('registry declaration verifier constants changed')
        if any(type(getattr(owner, name)) is not type(value) or getattr(owner, name) != value
                for owner, name, value in constants):
            raise ValueError('registry declaration predecessor constants changed')

    def source_views(observations=None):
        own = read(own_path, cap)
        reader = read(reader_path, cap)
        if observations is not None:
            observations.extend((str(path), len(view[0]), digest(view[0]), view[1])
                for path, view in ((own_path, own), (reader_path, reader)))
        if digest(own[0]) != own_pin or digest(reader[0]) != reader_pin:
            raise ValueError('registry declaration verifier source changed')
        return own, reader

    def views(observe):
        baseline_view = observe(baseline, cap)
        if digest(baseline_view[0]) != baseline_pin:
            raise ValueError('pinned declaration predecessor differs')
        result = {baseline: baseline_view}
        for name, expected_pin in decode(baseline_view[0])['files_sha256'].items():
            path = root / name
            view = observe(path, cap)
            if digest(view[0]) != expected_pin:
                raise ValueError('pinned declaration dependency differs')
            result[path] = view
        # This is the explicitly named predecessor projection source, never the
        # successor source masquerading as a predecessor implementation.
        result[prior_path] = observe(prior_path, cap)
        if digest(result[prior_path][0]) != PREDECESSOR_SHA256:
            raise ValueError('registry declaration predecessor source differs')
        return result

    def identity():
        check()
        own, reader = source_views()
        value = digest(encode([SCHEMA, digest(own[0]), PREDECESSOR_SHA256, digest(reader[0])]))
        check()
        return value

    def validate_values(raw, receipt):
        if type(raw) is not bytes or type(receipt) is not bytes:
            raise TypeError('canonical registry declaration bytes required')
        body, proof = decode(raw), decode(receipt)
        if (encode(body) != raw or encode(proof) != receipt or len(raw) > declaration_cap
                or body.get('schema') != prior_schema or proof.get('schema') != SCHEMA
                or proof.get('verifier_identity') != verification_identity
                or proof.get('compatibility_raw_sha256') != digest(raw)
                or proof.get('split') != body.get('split')
                or proof.get('predecessor_implementation_sha256') != PREDECESSOR_SHA256
                or any(proof.get(name) is not False for name in ('cross_call_reuse', 'formal_result',
                    'formal_execution_ready', 'resource_admission', 'native_execution_authorized'))):
            raise ValueError('registry declaration projection/verification binding differs')

    def initialize(self, raw, receipt, *, _token=None):
        check()
        if _token is not token:
            raise TypeError('internally verified registry declaration required')
        validate_values(raw, receipt)
        object.__setattr__(self, 'compatibility_raw', raw)
        object.__setattr__(self, 'verification_receipt', receipt)
        check()

    def value(self):
        check()
        validate_values(self.compatibility_raw, self.verification_receipt)
        result = decode(self.compatibility_raw)
        check()
        return result

    def build(split):
        if type(split) is not str or split not in ('training', 'holdout'):
            raise ValueError('explicit source split required')
        check()
        auxiliary = []
        source = source_views(auxiliary)
        observations = []

        def observe(path, maximum):
            view = read(path, maximum)
            observations.append((str(path), maximum, len(view[0]), digest(view[0]), view[1]))
            return view

        entry = views(observe)

        def pinned(path, expected_pin):
            view = entry[path_type(path)]
            if digest(view[0]) != expected_pin:
                raise ValueError('registry declaration input differs')
            return decode(view[0])

        authority = pinned(authority_path, authority_pin)
        archive = pinned(archive_path / 'manifest.json', archive_pin)
        member = archive['members'][split]
        if digest(entry[archive_path / member['path']][0]) != member['sha256']:
            raise ValueError('selected archive member differs')
        implementation = registry.implementation_identity()
        basis = dict(schema=registry_schema, authority=authority_pin,
            archive=archive_pin, source_package=package_pin,
            cap_table=authority['cap_table_sha256'], catalog=catalog_pin,
            implementation=implementation)
        body = dict(schema=prior_schema, status='DRAFT_NONAUTHORITATIVE', split=split,
            expected_registry_identity=source_hash(basis), registry_identity_basis=basis,
            selected_archive_member=member, predecessor_checks_sha256=baseline_pin,
            declaration_implementation_sha256=digest(entry[prior_path][0]),
            source_window_validated=False, normal_source_correspondence_verified=False,
            synthetic_mechanism_not_empirical=True, detached_consumer_authenticated=False,
            resource_admission=False, formal_execution_ready=False, formal_result=False,
            native_execution_authorized=False)
        raw = encode(body)
        if len(raw) > declaration_cap:
            raise ValueError('declaration exceeds byte cap')
        if registry.implementation_identity() != implementation:
            raise ValueError('registry implementation changed')
        entry_count = len(observations)
        for path, view in entry.items():
            if observe(path, cap) != view:
                raise ValueError('declaration dependency changed during build')
        if source_views(auxiliary) != source:
            raise ValueError('registry declaration verifier source changed during build')
        check()
        receipt = encode(dict(schema=SCHEMA, verifier_identity=verification_identity,
            predecessor_schema=prior_schema, predecessor_implementation_sha256=PREDECESSOR_SHA256,
            split=split, compatibility_raw_sha256=digest(raw),
            reader_contract='fresh_observed_size_plus_one__predecessor_regular_file_checks',
            ordered_observation_sha256=digest(encode(observations)),
            dependency_unique_files=len(entry), entry_observations=entry_count,
            exit_observations=len(observations)-entry_count,
            dependency_requested_read_bytes=sum(size+1 for _, _, size, _, _ in observations),
            legacy_dependency_requested_read_bytes=sum(maximum+1 for _, maximum, _, _, _ in observations),
            auxiliary_source_observations=len(auxiliary),
            auxiliary_source_requested_read_bytes=sum(size+1 for _, size, _, _ in auxiliary),
            cross_call_reuse=False, formal_result=False, formal_execution_ready=False,
            resource_admission=False, native_execution_authorized=False))
        result = result_type(raw, receipt, _token=token)
        check()
        return result

    def inspect(path, *, expected_sha256, split):
        check()
        pin(expected_sha256)
        path = path_type(path)
        before = read(path, declaration_cap)
        if digest(before[0]) != expected_sha256:
            raise ValueError('external declaration pin differs')
        result = build(split)
        if before[0] != result.compatibility_raw:
            raise ValueError('declaration reconstruction differs')
        if read(path, declaration_cap) != before:
            raise ValueError('declaration changed during inspect')
        check()
        return result

    result_type.__init__, result_type.value = initialize, value
    bindings = [(module_namespace, name, value) for name, value in (
        ('predecessor', prior), ('bounded', reader_module), ('_TOKEN', token),
        ('json', json_module), ('Path', path_type),
        ('VerifiedRegistryDeclaration', result_type), ('build', build),
        ('inspect', inspect), ('implementation_identity', identity))]
    bindings += [(owner, name, getattr(owner, name)) for owner, names in (
        (prior, ('io', 'registry', 'group')),
        (reader_module, ('read_stable',)), (io, ('identity', 'digest', 'encode', 'pin')),
        (registry, ('implementation_identity', 'frozen', 'catalog', 'old')), (old, ('source',)),
        (old_source, ('_hash',)),
        (json, ('loads',)), (result_type, ('__init__', 'value'))) for name in names]
    expected = tuple((owner, name, value, state(value)) for owner, name, value in bindings)
    return build, inspect, identity


build, inspect, implementation_identity = _bind()
del _bind
