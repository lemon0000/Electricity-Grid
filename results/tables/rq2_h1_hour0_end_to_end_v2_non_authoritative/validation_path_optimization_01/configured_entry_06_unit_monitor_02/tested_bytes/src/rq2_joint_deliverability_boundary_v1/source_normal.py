"""Pinned RTS source assembly for a supplied continuous normal contract.

No initial state, clock basis, split or business parameters are inferred here.
This is a development input adapter, not a dispatch or a formal input package.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ..grid.rts_gmlc import (RTS_GMLC_MANIFEST_SHA256,
    load_rts_gmlc_chronological_data, verify_sha256_manifest)
from .continuous_grid_normal import ContinuousNormalInputs, normal_input_identity, _digest
from .grid_carry import GridCarry


@dataclass(frozen=True)
class SourceNormalAssembly:
    inputs: ContinuousNormalInputs
    raw_source_hours: tuple[int, ...]
    source_manifest_sha256: str
    normal_identity: str
    assembly_identity: str


def _source(root):
    root = Path(root)
    digest = sha256((root / 'SHA256SUMS').read_bytes()).hexdigest()
    if digest != RTS_GMLC_MANIFEST_SHA256 or not verify_sha256_manifest(root):
        raise ValueError('pinned RTS source manifest or source files differ')
    return digest


def assemble_source_normal(upstream_root, raw_source_hours, request, initial, carry, *, source_time_basis):
    """Bind independently supplied request/boundary to verified source indices.

    The caller supplies the entire request so timestamps and demand are checked
    against the source rather than silently corrected. The incoming carry uses
    the same numeric index as the first zero-based raw hour, but represents the
    preceding boundary. Only the raw-to-continuous index mapping is generated.
    """
    if (type(raw_source_hours) is not tuple or not raw_source_hours
            or any(type(h) is not int or h < 0 for h in raw_source_hours)
            or raw_source_hours != tuple(range(raw_source_hours[0], raw_source_hours[0]+len(raw_source_hours)))):
        raise ValueError('consecutive nonnegative zero-based raw source hours required')
    if type(carry) is not GridCarry or carry.source_hour != raw_source_hours[0]:
        raise ValueError('incoming boundary does not precede requested source window')
    manifest = _source(upstream_root)
    if type(carry.identity.source_sha256) is not str or carry.identity.source_sha256 != manifest:
        raise ValueError('carry source identity differs from verified RTS manifest')
    data = load_rts_gmlc_chronological_data(Path(upstream_root))
    # Detect ordinary source changes during loading; no concurrent writer lock
    # or hostile ABA/source authenticity guarantee is claimed.
    if _source(upstream_root) != manifest:
        raise ValueError('source changed during assembly')
    inputs = ContinuousNormalInputs(data, request, initial, carry,
        tuple(h+1 for h in raw_source_hours), source_time_basis)
    normal_id = normal_input_identity(inputs)
    adapter_hash = sha256(Path(__file__).read_bytes()).hexdigest()
    identity = _digest('draft_pinned_source_normal_assembly_v1', manifest,
        raw_source_hours, normal_id, adapter_hash)
    return SourceNormalAssembly(inputs, raw_source_hours, manifest, normal_id, identity)


def validate_source_assembly(assembly, upstream_root):
    """Reassemble against current source and compare all bound inputs."""
    if type(assembly) is not SourceNormalAssembly:
        raise ValueError('typed source assembly required')
    for name in ('source_manifest_sha256', 'normal_identity', 'assembly_identity'):
        digest = getattr(assembly, name)
        if type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('built-in lowercase SHA256 required: '+name)
    inputs = assembly.inputs
    rebuilt = assemble_source_normal(upstream_root, assembly.raw_source_hours,
        inputs.request, inputs.initial, inputs.carry, source_time_basis=inputs.source_time_basis)
    if (rebuilt.source_manifest_sha256 != assembly.source_manifest_sha256
            or rebuilt.normal_identity != assembly.normal_identity
            or rebuilt.assembly_identity != assembly.assembly_identity
            or normal_input_identity(inputs) != rebuilt.normal_identity):
        raise ValueError('source assembly drift')
    return rebuilt
