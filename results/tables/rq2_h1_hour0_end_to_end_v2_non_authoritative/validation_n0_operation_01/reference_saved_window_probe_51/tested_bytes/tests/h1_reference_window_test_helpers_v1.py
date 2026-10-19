"""Explicit synthetic replay/transport values for private-window unit tests.

The saved view uses real bounded filesystem observations. No numerical/native
authentication is inferred; the engine receipt says canonical_sequence=false.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace as NS

from experiments import h1_raw_ingress_development_v1 as raw
from experiments import h1_selector_parent_validation_operation_development_v2 as literal


@dataclass(frozen=True)
class Literal:
    value: str


@dataclass(frozen=True)
class Lane:
    role: str = 'Rref'
    arm: str | None = None


@dataclass(frozen=True)
class Replay:
    request: tuple
    candidate: Literal
    diagnostics: tuple


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def seed_reference(case, directory):
    parent = case.parent
    root = directory/'explicit_synthetic_saved_reference'
    root.mkdir(); (root/'terminal.bin').write_bytes(b'explicit synthetic terminal')
    terminal = 'e'*64; request = 'f'*64; cap = 1048576
    completion = case.ref._issued
    completion.scientific_root = str(root)
    completion.scientific_terminal_sha256 = terminal
    completion.scientific_request_sha256 = request
    completion.max_archive_bytes = cap
    for owner in case.parents:
        value = json.loads(owner._raw)
        value['declaration']['reference'] = None if owner is case.ref else dict(
            root=str(root), terminal_sha256=terminal, request_sha256=request, max_archive_bytes=cap)
        owner._raw = encode(value)
        owner._issued_bytes = parent._completion_bytes(owner._issued)
        inspections = parent.inspection._inspect.__globals__['inspections']
        inspections[str(owner.worker_root)] = (owner._raw, inspections[str(owner.worker_root)][1])
    counts = dict(original=0, views=0, configurations=0, snapshots=0)
    results = []; payloads = []; contexts = []
    def snapshot(root, count, limits, terminal):
        counts['views'] += 1
        names = tuple(sorted(path.name for path in root.iterdir()))
        files = {}
        for name in names:
            value, stamp = raw.read_stable(root/name, 4096)
            files[name] = sha256(value).hexdigest(), stamp, 4096
        return names, files
    def configuration(frame, disclosure, before, args, max_archive_bytes, run_configuration):
        counts['configurations'] += 1
        return dict(signature=literal._source_signature((frame, disclosure, before, args, max_archive_bytes, run_configuration)))
    def inspect(*args, **keywords):
        counts['original'] += 1
        hook = case.faults.get('reference_original')
        if hook is not None: hook(counts['original'])
        replay = Replay(('1', '1'), Literal('explicit synthetic carry'), ((0, 'label', 'accepted', 0., 0.),))
        result = dict(schema='explicit_synthetic_reference', records=(b'unit record',), replay=replay,
            terminal_sha256=terminal, request_sha256=request, fresh_at_return=True,
            owned_run_return_observed=False, formal_result=False)
        results.append(result); return result
    sequence = NS(_root=lambda value: Path(value), _snapshot=snapshot, inspect=inspect,
        _configuration=configuration, SCHEMA='explicit_synthetic_reference', FLAGS={'formal_result': False},
        io=NS(encode=encode), selection=NS(ReplayResult=Replay, stage_labels=lambda frame, lane: ('label',)))
    frame, disclosure, before = Literal('frame'), Literal('disclosure'), Literal('before')
    arguments = dict(lane=Lane(), selector=Literal('selector'), specification=Literal('specification'),
        limits=Literal('limits'), power=None)
    config = Literal('configuration')
    original_snapshot = parent.worker.snapshot
    namespace = dict(phase=original_snapshot.phase, sequence=sequence, NS=NS, Path=Path,
        frame=frame, disclosure=disclosure, before=before, arguments=arguments, config=config,
        faults=case.faults, payloads=payloads, contexts=contexts, counts=counts)
    # Source/prepare/bind/inspection use the actual predecessor method code;
    # only the numerical/source fixture is explicit synthetic data.
    exec('def _build(declaration):\n'
         ' counts["snapshots"]+=1\n'
         ' binding=NS(**declaration["source_binding"])\n'
         ' current=phase._fresh(binding,0,binding.genesis_terminal_sha256)\n'
         ' if declaration["role"]=="actual":\n'
         '  ref=declaration["reference"]\n'
         '  value=sequence.inspect(sequence._root(ref["root"]),frame,disclosure,before,\n'
         '   expected_terminal_sha256=ref["terminal_sha256"],max_archive_bytes=ref["max_archive_bytes"],\n'
         '   run_configuration=config,**arguments)\n'
         '  payloads.append(value)\n'
         '  if faults.get("borrowed_reference"):faults["borrowed_reference"](value)\n'
         ' return current\n', namespace)
    original_snapshot._build = namespace['_build']
    original_snapshot.sequence = sequence
    namespace = dict(_build=original_snapshot._build, json=json, Rebuilt=original_snapshot.RebuiltInput)
    exec('def rebuild(raw,*,expected_sha256):\n'
         ' declaration=json.loads(raw)["declaration"]\n'
         ' _build(declaration)\n _build(declaration)\n return Rebuilt()\n', namespace)
    original_snapshot.rebuild = namespace['rebuild']
    case.reference_sequence = sequence
    case.reference_counts, case.reference_results = counts, results
    case.reference_payloads, case.reference_root = payloads, root
    case.reference_arguments = arguments
