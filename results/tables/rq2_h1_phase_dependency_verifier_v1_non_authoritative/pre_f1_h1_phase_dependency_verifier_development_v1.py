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


def read_stable(path, cap):
    """Preserve the predecessor checks; bound allocation by observed file size.

This retains the predecessor regular-file identity contract. It does not add
hardlink/ancestor-reparse protection or a guarantee against unobservable ABA.
"""
    before = io.identity(path)
    if before[2] > cap:
        raise ValueError('file byte cap exceeded')
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        opened = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if opened[:4] != before[:4]:
            raise ValueError('file replaced before open')
        raw = stream.read(before[2] + 1)
        info = os.fstat(stream.fileno())
        after = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if len(raw) > cap or len(raw) != before[2] or after != opened or io.identity(path) != before:
        raise ValueError('file changed or exceeded byte cap')
    return raw, before


def _scope():
    if (SCHEMA != 'h1_phase_dependency_verifier_development_v1'
            or MAX_FILES != 2048 or TOTAL_CAP != 256 * 1024**2
            or any(value is not False for value in FLAGS.values())):
        raise ValueError('development verifier scope changed')


def _views():
    symbolic = prior.symbolic
    baseline_path = prior.ROOT / symbolic.BASELINE
    baseline = read_stable(baseline_path, symbolic.proof.CAP)
    if io.digest(baseline[0]) != symbolic.BASELINE_PIN:
        raise ValueError('baseline pin differs')
    # Absolute external dependencies are authorized only by this exact pinned
    # baseline. Preserve its full inventory, including the two environment files.
    names = [(prior.ROOT / symbolic.PROOF, symbolic.PROOF_PIN),
        (Path(symbolic.__file__), None), (Path(symbolic.proof.__file__), None),
        (baseline_path, symbolic.BASELINE_PIN)]
    names += [(prior.ROOT / name, pin)
        for name, pin in json.loads(baseline[0])['files_sha256'].items()]
    names += [(prior.ROOT / prior.PROTOCOL, prior.PROTOCOL_PIN), (Path(prior.__file__), None)]
    if len(names) > MAX_FILES:
        raise ValueError('dependency inventory exceeds bound')
    views = {baseline_path: baseline}
    total = len(baseline[0])
    for path, pin in names:
        view = read_stable(path, symbolic.proof.exclusion.INPUT_CAP)
        if pin is not None and io.digest(view[0]) != pin:
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
    own = read_stable(Path(__file__), io.META_CAP * 128)
    views = _views()
    dependency_pins = {(path.relative_to(prior.ROOT).as_posix()
        if path.is_relative_to(prior.ROOT) else path.as_posix()): io.digest(view[0])
        for path, view in views.items()}
    predecessor_identity = io.digest(io.encode(dependency_pins))
    group = prior._project(views[prior.ROOT / prior.symbolic.PROOF][0],
        family, ordinal, predecessor_identity)
    for path, view in views.items():
        if read_stable(path, prior.symbolic.proof.exclusion.INPUT_CAP) != view:
            raise ValueError('phase dependency changed during verification')
    if read_stable(Path(__file__), io.META_CAP * 128) != own:
        raise ValueError('verifier changed during verification')
    _scope()
    return dict(schema=SCHEMA, verifier_sha256=io.digest(own[0]),
        predecessor_group=group, dependency_sha256=dependency_pins,
        observed_file_count=len(views), observed_total_bytes=sum(len(v[0]) for v in views.values()),
        fresh_at_return_only=True, detached_data=True, **FLAGS)
