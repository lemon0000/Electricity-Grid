"""Rebuild normal task inputs from bounded, independently pinned declarations.

Intended to run inside the future task Job; no solver or process is started here.
The saved build-only record supplies mechanism inputs, never a checkpoint.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import yaml

from experiments import audit_rq2_power_normal_binding_v1 as declaration_reader
from . import episode_store as local, source_normal, source_normal_execution as source


kernel = source.kernel
SCHEMA = 'draft_normal_task_source_preparation_v1'
BUILD_FIELDS = frozenset(('binding', 'carry', 'declaration_role', 'dependencies', 'expected_assembly_identity',
    'external_assembly_identity_verified', 'extra_implementation_sha256', 'formal_result', 'initial', 'mode',
    'model_builds', 'model_scale', 'normal_assembly_identity', 'normal_assignment_verified', 'normal_declaration_sha256',
    'normal_input_identity', 'original_dc_requested_mw', 'pair_declaration_sha256', 'pair_identity', 'request',
    'runner_sha256', 'solver_calls', 'source_time_basis', 'status'))


@dataclass(frozen=True)
class NormalTaskSourceRequest:
    normal_record_path: str
    expected_normal_record_sha256: str
    pair_declaration_path: str
    expected_pair_declaration_sha256: str
    upstream_root: str
    config_path: str
    expected_config_sha256: str
    expected_assembly_identity: str
    expected_input_identity: str
    expected_pair_identity: str
    expected_binding_identity: str
    expected_scale: kernel.Rq2ModelScale
    max_normal_record_bytes: int
    max_pair_declaration_bytes: int
    max_config_bytes: int

    def __post_init__(self):
        if (type(self.expected_scale) is not kernel.Rq2ModelScale or any(type(x) is not int or x <= 0
                for x in (self.expected_scale.variables, self.expected_scale.constraints))):
            raise ValueError('explicit expected normal model scale required')
        for name in ('normal_record_path', 'pair_declaration_path', 'upstream_root', 'config_path'):
            value = getattr(self, name)
            if type(value) is not str or '\0' in value or not Path(value).is_absolute():
                raise ValueError('absolute normal task source paths required')
        for name in ('expected_normal_record_sha256', 'expected_pair_declaration_sha256', 'expected_config_sha256',
                     'expected_assembly_identity', 'expected_input_identity', 'expected_pair_identity', 'expected_binding_identity'):
            kernel._pin(getattr(self, name))
        for name in ('max_normal_record_bytes', 'max_pair_declaration_bytes', 'max_config_bytes'):
            value = getattr(self, name)
            if type(value) is not int or not 0 < value <= 16*1024**2:
                raise ValueError('explicit declaration byte budget in (0, 16 MiB] required')


def task_source_identity(request):
    if type(request) is not NormalTaskSourceRequest:
        raise ValueError('typed normal task source request required')
    request.__post_init__()
    root = Path(__file__).resolve().parents[2]
    dependencies = tuple((name, sha256((root/name).read_bytes()).hexdigest())
        for name in source.ADAPTER_DEPENDENCIES)
    return kernel._digest(SCHEMA, request, dependencies, source.kernel.native._dependencies(),
        tuple((str(Path(module.__file__).relative_to(root)), sha256(Path(module.__file__).read_bytes()).hexdigest())
            for module in (local, source, source.kernel, declaration_reader)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def _read_pinned(path, digest, maximum):
    path = local._path(path)
    before = local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(maximum+1)
    if len(raw) > maximum or sha256(raw).hexdigest() != digest:
        raise ValueError('normal task declaration size/hash mismatch')
    if local._file_identity(path) != before:
        raise ValueError('normal task declaration replaced during read')
    return raw


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate normal declaration key')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('nonfinite normal declaration: '+value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


@dataclass(frozen=True, init=False)
class PreparedNormalTaskInputs(kernel._Owned):
    request_identity: str
    assembly: source.SourceNormalAssembly
    declaration: source.PairDeclaration
    binding_json: str
    timings: tuple[tuple[str, float], ...]
    solver_calls: int = 0
    mechanism_initial_state: bool = True
    observed_power_mapping: bool = False
    normal_assignment_verified: bool = False
    formal_result: bool = False


def prepare_task_inputs(request, *, expected_request_identity):
    started = perf_counter()
    kernel._pin(expected_request_identity)
    if task_source_identity(request) != expected_request_identity:
        raise ValueError('normal task source implementation/request drift')

    def reads():
        return tuple(_read_pinned(path, digest, limit) for path, digest, limit in (
            (request.normal_record_path, request.expected_normal_record_sha256, request.max_normal_record_bytes),
            (request.pair_declaration_path, request.expected_pair_declaration_sha256, request.max_pair_declaration_bytes),
            (request.config_path, request.expected_config_sha256, request.max_config_bytes)))

    raw, pair_raw, config_raw = reads()
    record = _json(raw)
    if (type(record) is not dict or set(record) != BUILD_FIELDS or record.get('status') != 'DRAFT_NONAUTHORITATIVE'
            or record.get('mode') != 'verify' or record.get('external_assembly_identity_verified') is not True
            or record.get('formal_result') is not False or type(record.get('solver_calls')) is not int
            or record['solver_calls'] != 0
            or record.get('normal_assignment_verified') is not False
            or type(record.get('model_builds')) is not int or record['model_builds'] != 1
            or kernel._digest(record.get('model_scale')) != kernel._digest(asdict(request.expected_scale))
            or record.get('declaration_role') != 'explicit_mechanism_input_not_executable_checkpoint'):
        raise ValueError('verified build-only mechanism declaration required')
    for name, expected in (('normal_assembly_identity', request.expected_assembly_identity),
            ('expected_assembly_identity', request.expected_assembly_identity),
            ('normal_input_identity', request.expected_input_identity), ('pair_identity', request.expected_pair_identity),
            ('pair_declaration_sha256', request.expected_pair_declaration_sha256)):
        if record.get(name) != expected:
            raise ValueError('normal task declaration external pin mismatch: '+name)
    saved_binding = record['binding']
    body = dict(saved_binding)
    binding_id = body.pop('binding_identity')
    if binding_id != request.expected_binding_identity or source.source_window._hash(body) != binding_id:
        raise ValueError('normal task binding body differs from external pin')
    declaration = source.PairDeclaration(**yaml.load(pair_raw.decode('utf-8'),
        Loader=source.source_window.audit._UniqueKeyLoader))
    declaration.__post_init__()
    if declaration.config_sha256 != request.expected_config_sha256:
        raise ValueError('normal task pair config pin mismatch')
    power = saved_binding['power_binding']
    # Reuse the existing explicit-mechanism decoder. No assignment, solver
    # result, saved terminal carry, or executable cursor is restored.
    record['source_manifest_sha256'] = power['grid_source_manifest_sha256']
    normal_request, initial, carry = declaration_reader.declared_inputs(record, dict(
        split=power['split'], outage_seed=power['outage_seed'], chain={'chain_id': power['trajectory_id']}))
    decoded = perf_counter()
    assembly = source_normal.assemble_source_normal(request.upstream_root, tuple(power['raw_source_hours']),
        normal_request, initial, carry, source_time_basis=record['source_time_basis'])
    if (assembly.assembly_identity != request.expected_assembly_identity
            or assembly.normal_identity != request.expected_input_identity
            or kernel.normal_input_identity(assembly.inputs) != request.expected_input_identity):
        raise ValueError('rebuilt normal task inputs differ from external pins')
    assembled = perf_counter()
    binding = source.binding.bind_pair_normal(assembly, request.upstream_root, declaration,
        expected_assembly_identity=request.expected_assembly_identity,
        expected_pair_identity=request.expected_pair_identity, config_path=request.config_path)
    body = dict(binding)
    binding_id = body.pop('binding_identity')
    if (binding_id != request.expected_binding_identity or source.source_window._hash(body) != binding_id
            or source._json(binding) != source._json(saved_binding)):
        raise ValueError('rebuilt normal task binding differs from saved declaration')
    bound = perf_counter()
    if reads() != (raw, pair_raw, config_raw) or task_source_identity(request) != expected_request_identity:
        raise ValueError('normal task declarations or implementation changed during preparation')
    finished = perf_counter()
    return kernel.native._make(PreparedNormalTaskInputs, request_identity=expected_request_identity,
        assembly=assembly, declaration=declaration, binding_json=source._json(binding), timings=(
        ('declaration_seconds', decoded-started), ('source_assembly_seconds', assembled-decoded),
        ('source_binding_seconds', bound-assembled), ('post_check_seconds', finished-bound),
        ('observed_total_seconds', finished-started)), solver_calls=0, mechanism_initial_state=True,
        observed_power_mapping=False, normal_assignment_verified=False, formal_result=False)
