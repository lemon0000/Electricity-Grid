"""Explicit successor source assembly using streaming content identities.

Legacy content references are comparisons, not claims of legacy execution.
This distinct type is intentionally not accepted by the legacy execution chain.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from . import identity_stream as stream, source_normal as legacy


CONTRACT = 'draft_streaming_source_normal_assembly_v1'


def _pin(value):
    if (type(value) is not str or len(value) != 64
            or any(c not in '0123456789abcdef' for c in value)):
        raise ValueError('built-in lowercase SHA256 required')


def implementation_identity():
    """Bind this adapter, encoder, legacy source helpers and normal dependencies."""
    root = Path(__file__).resolve().parents[2]
    paths = (Path(__file__), Path(stream.__file__), Path(legacy.__file__))
    sources = tuple((path.relative_to(root).as_posix(), sha256(path.read_bytes()).hexdigest())
        for path in paths)
    return stream.digest(CONTRACT, sources, stream.legacy._dependencies())


@dataclass(frozen=True)
class StreamingSourceNormalAssembly:
    inputs: legacy.ContinuousNormalInputs
    raw_source_hours: tuple[int, ...]
    source_manifest_sha256: str
    normal_identity: str
    legacy_content_assembly_identity: str
    implementation_identity: str
    assembly_identity: str


def assemble_source_normal(upstream_root, raw_source_hours, request, initial, carry, *,
                           source_time_basis, expected_implementation_identity):
    """Rebuild verified source inputs; require the separately retained new pin."""
    _pin(expected_implementation_identity)
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('streaming source implementation drift')
    if (type(raw_source_hours) is not tuple or not raw_source_hours
            or any(type(h) is not int or h < 0 for h in raw_source_hours)
            or raw_source_hours != tuple(range(raw_source_hours[0], raw_source_hours[0]+len(raw_source_hours)))):
        raise ValueError('consecutive nonnegative zero-based raw source hours required')
    if type(carry) is not legacy.GridCarry or carry.source_hour != raw_source_hours[0]:
        raise ValueError('incoming boundary does not precede requested source window')
    manifest = legacy._source(upstream_root)
    if type(carry.identity.source_sha256) is not str or carry.identity.source_sha256 != manifest:
        raise ValueError('carry source identity differs from verified RTS manifest')
    data = legacy.load_rts_gmlc_chronological_data(Path(upstream_root))
    if legacy._source(upstream_root) != manifest:
        raise ValueError('source changed during assembly')
    inputs = legacy.ContinuousNormalInputs(data, request, initial, carry,
        tuple(h+1 for h in raw_source_hours), source_time_basis)
    # Inputs owns its deepcopy; release the loader object before hashing it.
    del data
    normal_id = stream.normal_input_identity(inputs)
    legacy_reference = stream.digest('draft_pinned_source_normal_assembly_v1', manifest,
        raw_source_hours, normal_id, sha256(Path(legacy.__file__).read_bytes()).hexdigest())
    identity = stream.digest(CONTRACT, manifest, raw_source_hours, normal_id,
        legacy_reference, expected_implementation_identity)
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('streaming source implementation drift')
    return StreamingSourceNormalAssembly(inputs, raw_source_hours, manifest, normal_id,
        legacy_reference, expected_implementation_identity, identity)


def validate_source_assembly(assembly, upstream_root, *, expected_implementation_identity):
    """Reassemble source and detect content, reference and implementation drift."""
    if type(assembly) is not StreamingSourceNormalAssembly:
        raise ValueError('typed streaming source assembly required')
    _pin(expected_implementation_identity)
    for name in ('source_manifest_sha256', 'normal_identity', 'legacy_content_assembly_identity',
                 'implementation_identity', 'assembly_identity'):
        _pin(getattr(assembly, name))
    if assembly.implementation_identity != expected_implementation_identity:
        raise ValueError('streaming source implementation drift')
    inputs = assembly.inputs
    if type(inputs) is not legacy.ContinuousNormalInputs:
        raise ValueError('typed continuous normal inputs required')
    rebuilt = assemble_source_normal(upstream_root, assembly.raw_source_hours,
        inputs.request, inputs.initial, inputs.carry, source_time_basis=inputs.source_time_basis,
        expected_implementation_identity=expected_implementation_identity)
    if (any(getattr(assembly, name) != getattr(rebuilt, name) for name in (
            'source_manifest_sha256', 'normal_identity', 'legacy_content_assembly_identity',
            'implementation_identity', 'assembly_identity'))
            or stream.normal_input_identity(inputs) != rebuilt.normal_identity):
        raise ValueError('streaming source assembly drift')
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('streaming source implementation drift')
    return rebuilt
