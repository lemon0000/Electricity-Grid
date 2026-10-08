"""Pinned declaration preparation through streaming source and pair successors.

Only mechanism inputs are reconstructed; no model or solver is invoked.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import yaml

from . import normal_task_inputs as legacy, source_normal_stream as source_normal
from . import pair_normal_stream as stream_binding

kernel, source = legacy.kernel, legacy.source
_read_pinned, _json = legacy._read_pinned, legacy._json
BUILD_FIELDS, declaration_reader = legacy.BUILD_FIELDS, legacy.declaration_reader
SCHEMA = 'draft_streaming_normal_task_source_preparation_v1'


def task_source_identity(request):
    return source_normal.stream.digest(SCHEMA, legacy.task_source_identity(request),
        source_normal.implementation_identity(), stream_binding.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest(), sha256(Path(legacy.__file__).read_bytes()).hexdigest())


@dataclass(frozen=True, init=False)
class PreparedStreamingNormalTaskInputs(kernel._Owned):
    request_identity: str
    assembly: source_normal.StreamingSourceNormalAssembly
    declaration: source.PairDeclaration
    binding: stream_binding.StreamingPairBinding
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
        normal_request, initial, carry, source_time_basis=record['source_time_basis'],
        expected_implementation_identity=source_normal.implementation_identity())
    if (type(assembly) is not source_normal.StreamingSourceNormalAssembly
            or assembly.legacy_content_assembly_identity != request.expected_assembly_identity
            or assembly.normal_identity != request.expected_input_identity
            or source_normal.stream.normal_input_identity(assembly.inputs) != request.expected_input_identity):
        raise ValueError('rebuilt normal task inputs differ from external pins')
    assembled = perf_counter()
    binding_implementation = stream_binding.implementation_identity()
    binding = stream_binding.bind_pair_normal(assembly, request.upstream_root, declaration,
        expected_assembly_identity=assembly.assembly_identity,
        expected_pair_identity=request.expected_pair_identity, config_path=request.config_path,
        expected_source_implementation_identity=source_normal.implementation_identity(),
        expected_implementation_identity=binding_implementation)
    if type(binding) is not stream_binding.StreamingPairBinding:
        raise ValueError('typed streaming binding required')
    for name in ('normal_identity', 'source_assembly_identity', 'pair_identity',
                 'legacy_content_binding_identity', 'implementation_identity', 'binding_identity'):
        kernel._pin(getattr(binding, name))
    if (type(binding.legacy_content_json) is not str
            or binding.normal_identity != request.expected_input_identity
            or binding.source_assembly_identity != assembly.assembly_identity
            or binding.pair_identity != request.expected_pair_identity
            or binding.implementation_identity != binding_implementation
            or binding.legacy_content_binding_identity != request.expected_binding_identity
            or binding.binding_identity != source_normal.stream.digest(stream_binding.CONTRACT,
                request.expected_input_identity, assembly.assembly_identity, request.expected_pair_identity,
                binding.legacy_content_json, binding_implementation)):
        raise ValueError('streaming binding identity mismatch')
    legacy_binding = json.loads(binding.legacy_content_json)
    body = dict(legacy_binding)
    binding_id = body.pop('binding_identity')
    if (binding_id != request.expected_binding_identity or source.source_window._hash(body) != binding_id
            or binding.legacy_content_json != source._json(legacy_binding)
            or binding.legacy_content_json != source._json(saved_binding)):
        raise ValueError('rebuilt normal task binding differs from saved declaration')
    bound = perf_counter()
    if reads() != (raw, pair_raw, config_raw) or task_source_identity(request) != expected_request_identity:
        raise ValueError('normal task declarations or implementation changed during preparation')
    finished = perf_counter()
    return kernel.native._make(PreparedStreamingNormalTaskInputs, request_identity=expected_request_identity,
        assembly=assembly, declaration=declaration, binding=binding, timings=(
        ('declaration_seconds', decoded-started), ('source_assembly_seconds', assembled-decoded),
        ('source_binding_seconds', bound-assembled), ('post_check_seconds', finished-bound),
        ('observed_total_seconds', finished-started)), solver_calls=0, mechanism_initial_state=True,
        observed_power_mapping=False, normal_assignment_verified=False, formal_result=False)
