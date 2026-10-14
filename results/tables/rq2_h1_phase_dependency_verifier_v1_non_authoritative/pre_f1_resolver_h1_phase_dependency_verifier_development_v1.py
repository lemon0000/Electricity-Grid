"""Bounded-read successor for the complete pinned phase-group projection.

The legacy projection and its identity remain explicit predecessor data. This
verifier has its own identity and performs complete entry/exit file observations.
Its returned dictionary is detached data, never a live-owner credential.
"""
import json
import os
from pathlib import Path

from experiments import h1_phase_manifest_group_development_v1 as prior

io = prior.io
SCHEMA = 'h1_phase_dependency_verifier_development_v1'
MAX_FILES = 2048
TOTAL_CAP = 256 * 1024**2
FLAGS = dict(formal_result=False, formal_execution_ready=False,
    resource_admission=False, native_execution_authorized=False,
    owner_consumption_authorized=False, source_correspondence_verified=False)


def _build():
    # Capture dispatch once. Boundary checks detect ordinary helper substitution;
    # this is not isolation from arbitrary Python reflection or unobserved ABA.
    import sys
    module = sys.modules[__name__]
    prior, io = module.prior, module.io
    identity, digest, encode, fstat = io.identity, io.digest, io.encode, os.fstat
    project = prior._project
    expected_flags = dict(FLAGS)
    symbolic, proof = prior.symbolic, prior.symbolic.proof
    root, protocol, protocol_pin = prior.ROOT, prior.PROTOCOL, prior.PROTOCOL_PIN
    proof_name, proof_pin = symbolic.PROOF, symbolic.PROOF_PIN
    baseline_name, baseline_pin = symbolic.BASELINE, symbolic.BASELINE_PIN
    baseline_cap = proof.CAP
    symbolic_path, proof_path, group_path = (Path(x.__file__) for x in (symbolic, proof, prior))
    constants = [(owner, name, getattr(owner, name)) for owner, names in (
        (prior, ('ROOT','SCHEMA','PROTOCOL','PROTOCOL_PIN','__file__')),
        (symbolic, ('PROOF','PROOF_PIN','BASELINE','BASELINE_PIN','__file__')),
        (proof, ('CAP','__file__')), (proof.exclusion, ('INPUT_CAP',)),
        (io, ('META_CAP','__file__'))) for name in names]
    predecessor_flags = dict(prior.FLAGS)
    own_path, own_cap = Path(__file__), io.META_CAP * 128
    input_cap = proof.exclusion.INPUT_CAP
    implementation_paths = tuple(Path(m.__file__) for m in
        (prior, prior.symbolic, prior.symbolic.proof, io))
    def read_stable(path, cap):
        """Preserve the predecessor checks; bound allocation by observed file size.

    This retains the predecessor regular-file identity contract. It does not add
    hardlink/ancestor-reparse protection or a guarantee against unobservable ABA.
    """
        before = identity(path)
        if before[2] > cap:
            raise ValueError('file byte cap exceeded')
        with path.open('rb') as stream:
            info = fstat(stream.fileno())
            opened = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            if opened[:4] != before[:4]:
                raise ValueError('file replaced before open')
            raw = stream.read(before[2] + 1)
            info = fstat(stream.fileno())
            after = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if len(raw) > cap or len(raw) != before[2] or after != opened or identity(path) != before:
            raise ValueError('file changed or exceeded byte cap')
        return raw, before


    def _scope():
        if (SCHEMA != 'h1_phase_dependency_verifier_development_v1'
                or MAX_FILES != 2048 or TOTAL_CAP != 256 * 1024**2
                or FLAGS != expected_flags or any(value is not False for value in FLAGS.values())):
            raise ValueError('development verifier scope changed')
        if any(getattr(owner, name, None) is not value for owner, name, value in bindings):
            raise ValueError('verifier helper identity changed')
        if (any(type(getattr(owner, name, None)) is not type(value)
                or getattr(owner, name, None) != value for owner, name, value in constants)
                or prior.FLAGS != predecessor_flags
                or any(value is not False for value in prior.FLAGS.values())):
            raise ValueError('predecessor protocol scope changed')


    def _views():
        baseline_path = root / baseline_name
        baseline = read_stable(baseline_path, baseline_cap)
        if digest(baseline[0]) != baseline_pin:
            raise ValueError('baseline pin differs')
        # Absolute external dependencies are authorized only by this exact pinned
        # baseline. Preserve its full inventory, including the two environment files.
        names = [(root / proof_name, proof_pin),
            (symbolic_path, None), (proof_path, None),
            (baseline_path, baseline_pin)]
        names += [(root / name, pin)
            for name, pin in json.loads(baseline[0])['files_sha256'].items()]
        names += [(root / protocol, protocol_pin), (group_path, None)]
        if len(names) > MAX_FILES:
            raise ValueError('dependency inventory exceeds bound')
        views = {baseline_path: baseline}
        total = len(baseline[0])
        for path, pin in names:
            view = read_stable(path, input_cap)
            if pin is not None and digest(view[0]) != pin:
                raise ValueError('pinned dependency differs')
            if path in views:
                if views[path] != view:
                    raise ValueError('repeated dependency observation differs')
            else:
                total += len(view[0])
                if total > TOTAL_CAP:
                    raise ValueError('dependency total exceeds bound')
            views[path] = view
        return views


    def prepare_group(family, ordinal):
        """Fresh complete group projection with separately named verifier evidence."""
        _scope()
        own = read_stable(own_path, own_cap)
        implementation_views = {p: read_stable(p, input_cap) for p in implementation_paths}
        views = _views()
        dependency_pins = {(path.relative_to(root).as_posix()
            if path.is_relative_to(root) else path.as_posix()): digest(view[0])
            for path, view in views.items()}
        predecessor_identity = digest(encode(dependency_pins))
        _scope()
        group = project(views[root / proof_name][0],
            family, ordinal, predecessor_identity)
        for path, view in (*views.items(), *implementation_views.items()):
            if read_stable(path, input_cap) != view:
                raise ValueError('phase dependency changed during verification')
        if read_stable(own_path, own_cap) != own:
            raise ValueError('verifier changed during verification')
        _scope()
        implementation = dict(schema=SCHEMA, verifier_sha256=digest(own[0]),
            predecessor_files_sha256={p.as_posix(): digest(v[0]) for p,v in implementation_views.items()})
        return dict(schema=SCHEMA, verifier_sha256=digest(own[0]),
            verifier_implementation=implementation,
            verifier_implementation_sha256=digest(encode(implementation)),
            predecessor_group=group, dependency_sha256=dependency_pins,
            observed_file_count=len(views), observed_total_bytes=sum(len(v[0]) for v in views.values()),
            fresh_at_return_only=True, detached_data=True, **FLAGS)

    bindings = [(module, name, value) for name, value in
        [('read_stable', read_stable), ('_views', _views), ('_scope', _scope),
         ('prepare_group', prepare_group), ('prior', prior), ('io', io)]]
    bindings += [(io, 'identity', identity), (io, 'digest', digest), (io, 'encode', encode),
        (os, 'fstat', fstat), (prior, '_project', project), (prior, 'io', io),
        (prior, 'symbolic', symbolic), (symbolic, 'proof', proof),
        (proof, 'exclusion', proof.exclusion), (proof, '_resolver', proof._resolver)]
    return read_stable, _views, _scope, prepare_group


read_stable, _views, _scope, prepare_group = _build()
del _build
