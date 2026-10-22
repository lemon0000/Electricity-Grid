"""Lossless typed CAS for local development evidence; no dynamic deserialization."""
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import types
from typing import get_args, get_origin, get_type_hints, Union

from src.grid.rts24 import Bus, Generator, Branch, Rts24Data
from src.staged_deliverability_development_v1 import Parameters
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import DebtCohort, DebtLedger
from src.staged_rts24_development_v1 import (
    Outage, PublicObservation, Fixture, PointRequest, PointWitness, EconomicEvidence, BoundQuery,
)
from src.staged_rts24_child_optimality_v1 import ChildLpEvidence
from src.staged_rts24_causal_v1 import PointEvidence, HourEvidence, ExecutionState, PreparedHour, Proposal


SCHEMA = "staged_rts24_typed_cas_v1"
CLASSES = {cls.__name__: cls for cls in (
    Bus, Generator, Branch, Rts24Data, Parameters, DebtCohort, DebtLedger, Outage, PublicObservation,
    Fixture, PointRequest, PointWitness, EconomicEvidence, BoundQuery, ChildLpEvidence,
    PointEvidence, HourEvidence, ExecutionState, PreparedHour, Proposal,
)}
REFERENCED = {Rts24Data, Fixture, PointRequest, PointWitness, EconomicEvidence, BoundQuery, ChildLpEvidence,
              PointEvidence, HourEvidence, ExecutionState, PreparedHour, Proposal}
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_BLOB = 8*1024*1024
MAX_TOTAL = 64*1024*1024
MAX_OBJECTS = 10000
MAX_DEPTH = 256
MAX_NODES = 1000000
FIELD_TYPES = {cls: get_type_hints(cls) for cls in CLASSES.values()}
FIELD_TYPES[Fixture].update(before=Rts24Data, after=Rts24Data)
FIELD_TYPES[PointRequest]["data"] = Rts24Data
FIELD_TYPES[BoundQuery]["base_query"] = BoundQuery | None
FIELD_TYPES[PointEvidence]["child_lp"] = ChildLpEvidence | None
FIELD_TYPES[ExecutionState].update(ledger=DebtLedger, records=tuple[dict, ...])


def require(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def parse(data):
    require(type(data) is bytes and len(data) <= MAX_BLOB, "JSON byte limit")
    # Bound the JSON syntax before the recursive standard-library parser runs.
    depth, nodes, quoted, escaped = 0, 0, False, False
    for byte in data:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted, nodes = True, nodes+1
        elif byte in (91, 123): depth, nodes = depth+1, nodes+1
        elif byte in (93, 125): depth -= 1
        elif byte == 44: nodes += 1
        require(0 <= depth <= MAX_DEPTH and nodes <= MAX_NODES, "JSON complexity limit")
    value = json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    require(canonical(value) == data, "noncanonical JSON")
    return value


def ordinary(path, directory=False, allow_links=False):
    info = os.lstat(path)
    require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400), "reparse path")
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and (allow_links or info.st_nlink == 1), "nonordinary path")
    return info


def directory_chain(path):
    path = Path(path).absolute()
    for parent in reversed((path, *path.parents)):
        ordinary(parent, directory=True)
    return path


def directory_identity(path):
    path = Path(path).absolute()
    result = []
    for parent in reversed((path, *path.parents)):
        info = ordinary(parent, directory=True)
        result.append((str(parent), info.st_dev, info.st_ino))
    return tuple(result)


def read_bytes(path, allow_links=False):
    path = Path(path)
    directories = directory_identity(path.parent)
    before = ordinary(path, allow_links=allow_links)
    def identity(info): return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
    require(before.st_size <= MAX_BLOB, "object byte limit")
    with path.open("rb") as stream:
        require(identity(os.fstat(stream.fileno())) == identity(before), "file changed before read")
        data = stream.read(MAX_BLOB+1)
        require(identity(os.fstat(stream.fileno())) == identity(before), "file changed during read")
    require(identity(ordinary(path, allow_links=allow_links)) == identity(before) and len(data) == before.st_size, "file changed after read")
    require(directory_identity(path.parent) == directories, "directory changed during read")
    return data


class PublicationError(OSError):
    def __init__(self, path, data, phase, may_have_published, cause):
        super().__init__(f"{phase}: {type(cause).__name__}: {cause}")
        self.target, self.expected_sha = Path(path).name, sha(data)
        self.phase, self.may_have_published = phase, may_have_published


def publish(path, data, hook=None):
    """Windows exclusive pending -> fsync -> rename -> readback; retain failures."""
    path, phase, may = Path(path), "before_open", False
    require(os.name == "nt", "development publication requires Windows no-overwrite rename")
    require(type(data) is bytes and len(data) <= MAX_BLOB, "publication byte limit")
    directories = directory_identity(path.parent)
    require(not path.exists(), "immutable target already exists")
    pending = path.with_name(path.name+".pending")
    def stage(name):
        nonlocal phase
        phase = name
        if hook is not None: hook(name, path)
    try:
        stage("before_open")
        with pending.open("xb") as stream:
            stream.write(data)
            stage("after_write")
            stream.flush()
            os.fsync(stream.fileno())
            stage("after_fsync")
        require(read_bytes(pending) == data, "pending readback differs")
        stage("after_pending_readback")
        stage("before_rename")
        require(directory_identity(path.parent) == directories, "directory changed before rename")
        phase, may = "rename", True
        os.rename(pending, path)
        stage("after_rename")
        require(read_bytes(path) == data, "final readback differs")
        stage("after_final_readback")
        require(directory_identity(path.parent) == directories, "directory changed during publication")
        return sha(data)
    except Exception as error:
        raise PublicationError(path, data, phase, may, error) from error


class EvidenceStore:
    def __init__(self, root, hook=None):
        self.root = directory_chain(root)
        self.objects = directory_chain(self.root/"objects")
        self.directories = directory_identity(self.objects)
        self.hook = hook

    def _check_directories(self):
        require(directory_identity(self.objects) == self.directories, "CAS directory identity changed")

    def inventory(self):
        self._check_directories()
        result, total = {}, 0
        for path in self.objects.iterdir():
            require(len(result) < MAX_OBJECTS, "CAS object count limit")
            name = path.name.removesuffix(".pending").removesuffix(".json")
            require(SHA.fullmatch(name) and path.name in (name+".json", name+".json.pending"), "unknown CAS filename")
            data = read_bytes(path)
            total += len(data)
            require(total <= MAX_TOTAL, "CAS byte inventory limit")
            require(sha(data) == name, "CAS filename/hash differs")
            value = parse(data)
            require(set(value) == {"schema", "kind", "payload"} and value["schema"] == SCHEMA, "CAS envelope differs")
            result[path.name] = sha(data)
        for name in result:
            require(not name.endswith(".pending") or name.removesuffix(".pending") not in result, "CAS final and pending conflict")
        self._check_directories()
        return result

    def put(self, value):
        self._check_directories()
        identity, blobs = pack(value)
        inventory = self.inventory()
        require(not any(name.endswith(".pending") for name in inventory), "unresolved CAS pending")
        total = sum(ordinary(self.objects/name).st_size for name in inventory)
        new = {key: data for key, data in blobs.items() if key+".json" not in inventory}
        require(len(inventory)+len(new) <= MAX_OBJECTS and total+sum(map(len, new.values())) <= MAX_TOTAL, "CAS publication budget")
        for key, data in blobs.items():
            self._check_directories()
            path = self.objects/(key+".json")
            if path.exists(): require(read_bytes(path) == data, "existing CAS differs")
            else: publish(path, data, self.hook)
        self.inventory()
        return identity

    def get(self, identity):
        view = EvidenceReadView(self)
        value = view.get(identity)
        view.bookend()
        return value

    def _get(self, identity, view):
        self._check_directories()
        cache, active, used, count = view.cache, set(), view.used, [0]
        def decode(wire, depth=0):
            count[0] += 1
            require(depth <= MAX_DEPTH and count[0] <= MAX_NODES, "codec complexity limit")
            if wire is None or type(wire) in (bool, int, str): return wire
            require(type(wire) is list and wire and type(wire[0]) is str, "invalid wire type")
            tag = wire[0]
            if tag == "float":
                require(len(wire) == 2 and type(wire[1]) is str, "float shape")
                value = float.fromhex(wire[1])
                require(math.isfinite(value) and value.hex() == wire[1], "noncanonical float")
                return value
            if tag == "Q":
                require(len(wire) == 3 and type(wire[1]) is int and type(wire[2]) is int and wire[2] > 0, "fraction shape")
                value = Fraction(wire[1], wire[2])
                require((value.numerator, value.denominator) == tuple(wire[1:]), "noncanonical fraction")
                return value
            if tag in ("tuple", "list"):
                require(len(wire) == 2 and type(wire[1]) is list, "sequence shape")
                values = [decode(v, depth+1) for v in wire[1]]
                return tuple(values) if tag == "tuple" else values
            if tag == "dict":
                require(len(wire) == 2 and type(wire[1]) is list, "mapping shape")
                pairs = wire[1]
                require(all(type(p) is list and len(p) == 2 and type(p[0]) is str for p in pairs), "mapping pair shape")
                names = [p[0] for p in pairs]
                require(names == sorted(set(names)), "noncanonical mapping keys")
                return {key: decode(value, depth+1) for key, value in pairs}
            if tag == "ref":
                require(len(wire) == 2, "reference shape")
                return load(wire[1], depth+1)
            require(tag == "class" and len(wire) == 3 and type(wire[1]) is str and wire[1] in CLASSES, "unknown class")
            cls, pairs = CLASSES[wire[1]], wire[2]
            require(type(pairs) is list and all(type(p) is list and len(p) == 2 for p in pairs), "class fields shape")
            require([p[0] for p in pairs] == [field.name for field in fields(cls)], "class fields differ")
            return cls(**{key: decode(value, depth+1) for key, value in pairs})
        def load(key, depth=0):
            require(type(key) is str and SHA.fullmatch(key), "invalid CAS reference")
            require(key not in active and depth <= MAX_DEPTH, "CAS cycle/depth")
            if key in cache: return cache[key]
            require(len(used)+len(active) < MAX_OBJECTS, "decoded object count limit")
            active.add(key)
            data = read_bytes(self.objects/(key+".json"))
            require(sum(map(len, used.values()))+len(data) <= MAX_TOTAL, "decoded byte limit")
            used[key] = data
            require(sha(data) == key, "CAS bytes/hash differs")
            envelope = parse(data)
            require(type(envelope) is dict and set(envelope) == {"schema", "kind", "payload"} and envelope["schema"] == SCHEMA, "CAS envelope differs")
            value = decode(envelope["payload"], depth+1)
            require(type(value).__name__ == envelope["kind"], "CAS kind differs")
            cache[key] = value
            active.remove(key)
            require(len(used) <= MAX_OBJECTS and sum(map(len, used.values())) <= MAX_TOTAL, "decoded CAS limit")
            return value
        value = load(identity)
        if identity not in view.validated:
            require(pack(value)[0] == identity, "noncanonical typed image")
            view.validated.add(identity)
        self._check_directories()
        return value


class EvidenceReadView:
    """A single synchronous read operation; caller must complete bookend()."""
    def __init__(self, store):
        self.store, self.cache, self.used, self.validated = store, {}, {}, set()
        self.closed = False
        self.before = store.inventory()

    def get(self, identity):
        require(not self.closed, "closed read operation")
        return self.store._get(identity, self)

    def bookend(self):
        require(not self.closed, "closed read operation")
        for key, data in self.used.items():
            require(read_bytes(self.store.objects/(key+".json")) == data, "CAS changed during decode")
        require(self.store.inventory() == self.before, "CAS inventory changed during read operation")
        self.store._check_directories()
        self.closed = True


def _matches(value, annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType): return any(_matches(value, item) for item in args)
    if origin is tuple:
        if type(value) is not tuple: return False
        if len(args) == 2 and args[1] is Ellipsis: return all(_matches(item, args[0]) for item in value)
        return len(value) == len(args) and all(_matches(item, typ) for item, typ in zip(value, args))
    return type(value) is annotation


def pack(value):
    """Pure canonical encoding and full closure budget before any writes."""
    memo, active, blobs, count, total = {}, set(), {}, [0], [0]
    def encode(item, depth=0, top=False):
        count[0] += 1
        require(depth <= MAX_DEPTH and count[0] <= MAX_NODES, "codec complexity limit")
        if item is None or type(item) in (bool, int, str): return item
        if type(item) is float:
            require(math.isfinite(item), "nonfinite float")
            return ["float", item.hex()]
        if type(item) is Fraction: return ["Q", item.numerator, item.denominator]
        require(id(item) not in active, "cyclic evidence")
        if type(item) in (tuple, list, dict):
            active.add(id(item))
            if type(item) is dict:
                require(all(type(key) is str for key in item), "nonstring mapping key")
                wire = ["dict", [[key, encode(item[key], depth+1)] for key in sorted(item)]]
            else: wire = ["tuple" if type(item) is tuple else "list", [encode(v, depth+1) for v in item]]
            active.remove(id(item))
            return wire
        require(is_dataclass(item) and CLASSES.get(type(item).__name__) is type(item), "unregistered evidence type")
        require(all(_matches(getattr(item, name), annotation) for name, annotation in FIELD_TYPES[type(item)].items()), "dataclass field type differs")
        if not top and type(item) in REFERENCED:
            key = id(item)
            if key not in memo: memo[key] = (item, write(item, depth+1))
            require(memo[key][0] is item, "identity memo collision")
            return ["ref", memo[key][1]]
        active.add(id(item))
        wire = ["class", type(item).__name__, [[field.name, encode(getattr(item, field.name), depth+1)] for field in fields(item)]]
        active.remove(id(item))
        return wire
    def write(item, depth=0):
        data = canonical(dict(schema=SCHEMA, kind=type(item).__name__, payload=encode(item, depth, top=True)))
        require(len(data) <= MAX_BLOB, "encoded object byte limit")
        identity = sha(data)
        if identity not in blobs:
            require(len(blobs) < MAX_OBJECTS and total[0]+len(data) <= MAX_TOTAL, "encoded closure budget")
            blobs[identity], total[0] = data, total[0]+len(data)
        return identity
    return write(value), blobs
