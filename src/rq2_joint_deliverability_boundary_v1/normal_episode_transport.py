"""Bounded packet carrying normal evidence alongside initial episode inputs."""
from dataclasses import dataclass, fields
from hashlib import sha256
from pathlib import Path

from . import normal_episode_binding as binding
from . import normal_numerical_transport_v2 as normal_transport

legacy = binding.transport
episode, selector, LIMIT = legacy.episode, legacy.selector, legacy.LIMIT
SCHEMA = 'draft_normal_bound_episode_transport_v1'


@dataclass(frozen=True)
class BoundEpisodeInputs:
    normal_request: object
    normal_record: bytes
    episode_inputs: legacy.EpisodeInputs
    normal_sha256: str
    normal_request_identity: str
    episode_sha256: str
    binding_identity: str
    max_normal_bytes: int

    @property
    def reference_request(self): return self.episode_inputs.reference_request
    @property
    def arms(self): return self.episode_inputs.arms
    @property
    def hours(self): return self.episode_inputs.hours
    @property
    def budget(self): return self.episode_inputs.budget
    @property
    def resource_plan(self): return self.episode_inputs.resource_plan


def implementation_identity():
    return binding.normal.kernel._digest(SCHEMA, binding.implementation_identity(), legacy.implementation_identity(),
        sha256(Path(normal_transport.__file__).read_bytes()).hexdigest(),
        sha256(Path(normal_transport.legacy.__file__).read_bytes()).hexdigest(),
        tuple((cls.__module__, cls.__name__, tuple(f.name for f in fields(cls))) for cls in normal_transport.CLASSES),
        sha256(Path(__file__).read_bytes()).hexdigest())


def validate(inputs):
    if type(inputs) is not BoundEpisodeInputs:
        raise ValueError('typed normal-bound episode inputs required')
    legacy.validate(inputs.episode_inputs)
    if (type(inputs.normal_record) is not bytes or type(inputs.max_normal_bytes) is not int
            or not 0 < len(inputs.normal_record) <= inputs.max_normal_bytes <= LIMIT
            or sha256(inputs.normal_record).hexdigest() != inputs.normal_sha256
            or binding.normal.request_identity(inputs.normal_request) != inputs.normal_request_identity
            or sha256(legacy.export_inputs(inputs.episode_inputs)).hexdigest() != inputs.episode_sha256
            or binding.binding_identity(inputs.normal_request, normal_sha256=inputs.normal_sha256,
                episode_sha256=inputs.episode_sha256, max_normal_bytes=inputs.max_normal_bytes,
                max_episode_bytes=LIMIT) != inputs.binding_identity):
        raise ValueError('normal-bound episode packet identity mismatch')


def audit_inputs(inputs):
    validate(inputs)
    report, packet = binding.bind_episode(inputs.normal_record, inputs.normal_request,
        legacy.export_inputs(inputs.episode_inputs), normal_sha256=inputs.normal_sha256,
        episode_sha256=inputs.episode_sha256, max_normal_bytes=inputs.max_normal_bytes,
        max_episode_bytes=LIMIT, expected_request_identity=inputs.normal_request_identity,
        expected_binding_identity=inputs.binding_identity)
    if legacy.export_inputs(packet) != legacy.export_inputs(inputs.episode_inputs):
        raise ValueError('bound episode differs from supplied complete inputs')
    return report


def export_inputs(inputs):
    validate(inputs)
    packet = dict(schema=SCHEMA, normal_request=normal_transport.export_request(inputs.normal_request).decode('ascii'),
        normal_record_hex=inputs.normal_record.hex(), episode_inputs=legacy.export_inputs(inputs.episode_inputs).decode('ascii'),
        normal_sha256=inputs.normal_sha256, normal_request_identity=inputs.normal_request_identity,
        episode_sha256=inputs.episode_sha256, binding_identity=inputs.binding_identity,
        max_normal_bytes=inputs.max_normal_bytes)
    raw = selector.store._bytes(packet)
    if len(raw) > LIMIT: raise ValueError('complete bound episode packet exceeds transport allocation')
    return raw


def decode_inputs(raw):
    if type(raw) is not bytes or len(raw) > LIMIT:
        raise ValueError('bounded normal-bound episode packet required')
    p = selector.store._decoded(raw)
    if (type(p) is not dict or set(p) != {'schema', 'normal_request', 'normal_record_hex', 'episode_inputs',
            'normal_sha256', 'normal_request_identity', 'episode_sha256', 'binding_identity', 'max_normal_bytes'}
            or p['schema'] != SCHEMA
            or any(type(p[k]) is not str for k in ('normal_request', 'normal_record_hex', 'episode_inputs'))):
        raise ValueError('exact normal-bound episode wire inventory required')
    result = BoundEpisodeInputs(normal_transport.decode_request(p['normal_request'].encode('ascii')),
        bytes.fromhex(p['normal_record_hex']), legacy.decode_inputs(p['episode_inputs'].encode('ascii')),
        p['normal_sha256'], p['normal_request_identity'], p['episode_sha256'], p['binding_identity'], p['max_normal_bytes'])
    if export_inputs(result) != raw: raise ValueError('canonical bound episode roundtrip required')
    return result


def read_inputs(path, *, expected_sha256, max_request_bytes):
    binding.normal.kernel._pin(expected_sha256)
    if type(max_request_bytes) is not int or not 0 < max_request_bytes <= LIMIT:
        raise ValueError('explicit bounded episode packet size required')
    path = selector.store.local._path(path)
    before = selector.store.local._file_identity(path)
    raw = binding.normal.prepare._read_pinned(path, expected_sha256, max_request_bytes)
    if selector.store.local._file_identity(path) != before:
        raise ValueError('bound episode packet changed while reading')
    return decode_inputs(raw)


def _indirect_sources(inputs):
    audit = binding.source_pair.source_window.audit
    config = audit._load_config(Path(inputs.normal_request.source.config_path))
    roots, files = [], {}
    def add(path, digest):
        path = selector.store.local._path(path)
        binding.normal.kernel._pin(digest)
        if path in files and files[path] != digest:
            raise ValueError('conflicting indirect source pins')
        files[path] = digest
    for kind in ('power', 'workload'):
        item = config['inputs'][kind]
        root = selector.store.local._path(audit._root_path(item['package'], kind+' package'))
        roots.append(root)
        members = item['members']
        required = {'summary.json', 'training_marginal.csv.gz', 'holdout_marginal.csv.gz'}
        required |= {'n1_outage_events.csv.gz', 'power_system_blocks.csv.gz'} if kind == 'power' else {'workload_blocks.csv.gz'}
        if type(members) is not dict or not required <= set(members):
            raise ValueError('all consumed package members must have declared pins')
        add(root/'SHA256SUMS.json', item['manifest_sha256'])
        member_paths = set()
        for name, digest in members.items():
            path = selector.store.local._path(root/name)
            if not path.is_relative_to(root) or path == root or path in member_paths:
                raise ValueError('invalid or duplicate package member path')
            member_paths.add(path)
            add(path, digest)
        for key in ('builder_config', 'builder') + (('chronology',) if kind == 'power' else ()):
            add(audit._root_path(item[key+'_path'], kind+' '+key), item[key+'_sha256'])
    return tuple(roots), files


def source_snapshot(inputs):
    request = inputs.normal_request.normal
    binding.normal.legacy._declarations(request)
    paths = [Path(getattr(request.source, name)) for name in
        ('normal_record_path', 'pair_declaration_path', 'config_path')]
    root = selector.store.local._path(request.source.upstream_root)
    manifest = root/'SHA256SUMS'
    manifest_pin = episode._file_pin(manifest)
    raw = manifest.read_bytes()
    if sha256(raw).hexdigest() != manifest_pin[1]:
        raise ValueError('source manifest changed while reading')
    expected = {}
    for line in raw.decode('ascii').splitlines():
        digest, relative = line.split('  ', 1)
        binding.normal.kernel._pin(digest)
        path = selector.store.local._path(root/relative)
        if not path.is_relative_to(root) or path == root or path in expected:
            raise ValueError('invalid or duplicate source manifest path')
        expected[path] = digest
    if not expected:
        raise ValueError('nonempty source manifest required')
    pins = []
    for path in (*paths, *expected):
        pin = episode._file_pin(path)
        if path in expected and pin[1] != expected[path]:
            raise ValueError('manifest-listed source file changed')
        pins.append((str(selector.store.local._path(path)), pin))
    _, indirect = _indirect_sources(inputs)
    for path, digest in indirect.items():
        pin = episode._file_pin(path)
        if pin[1] != digest:
            raise ValueError('indirect source file changed')
        pins.append((str(path), pin))
    if episode._file_pin(manifest) != manifest_pin:
        raise ValueError('source manifest changed while sampling files')
    binding.normal.legacy._declarations(request)
    return tuple(pins)+((str(manifest), manifest_pin),)


def isolate_outputs(inputs, *outputs):
    source = inputs.normal_request.source
    upstream = selector.store.local._path(source.upstream_root)
    files = {selector.store.local._path(getattr(source, name)) for name in
        ('normal_record_path', 'pair_declaration_path', 'config_path')}
    roots, indirect = _indirect_sources(inputs)
    files.update(indirect)
    for output in outputs:
        output = selector.store.local._path(output)
        if (any(output.is_relative_to(root) or root.is_relative_to(output) for root in (upstream, *roots))
                or any(p == output or p.is_relative_to(output) for p in files)):
            raise ValueError('episode outputs must be isolated from normal source paths')
