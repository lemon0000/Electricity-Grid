"""Private same-append CAS batching over the unchanged typed codec.

Caller supplies the CAS snapshot just verified by journal._check and must run
full CAS/root checks before entry publication and again before adoption.
No reusable packed input, cross-operation cache, or writable replay API.
"""
from dataclasses import fields, is_dataclass
from fractions import Fraction

from src import staged_rts24_evidence_store_v1 as codec


def typed_equal(left, right):
    """Compare frozen snapshots without conflating int/float or signed zero."""
    seen, nodes = set(), [0]
    def equal(a, b, depth=0):
        nodes[0] += 1
        codec.require(depth <= codec.MAX_DEPTH and nodes[0] <= codec.MAX_NODES, "snapshot comparison limit")
        if type(a) is not type(b): return False
        if a is None or type(a) in (bool, int, str, Fraction): return a == b
        if type(a) is float: return a.hex() == b.hex()
        pair = (id(a), id(b))
        if pair in seen: return True
        seen.add(pair)
        if type(a) in (tuple, list):
            return len(a) == len(b) and all(equal(x, y, depth+1) for x, y in zip(a, b))
        if type(a) is dict:
            return (all(type(k) is str for k in (*a, *b)) and set(a) == set(b)
                    and all(equal(a[k], b[k], depth+1) for k in a))
        codec.require(is_dataclass(a) and codec.CLASSES.get(type(a).__name__) is type(a), "unregistered snapshot type")
        return all(equal(getattr(a, f.name), getattr(b, f.name), depth+1) for f in fields(a))
    return equal(left, right)


def publish_roots(store, values, verified_inventory):
    """Pack 1-2 logical roots once, then publish their exact merged closure.

    This is private to one synchronous append after a complete journal._check.
    The returned inventory is an expectation, never a new filesystem witness.
    """
    codec.require(type(values) is tuple and len(values) in (1, 2), "one append's roots required")
    codec.require(type(verified_inventory) is dict and not any(n.endswith(".pending") for n in verified_inventory),
                  "verified final CAS snapshot required")
    store._check_directories()
    old = dict(verified_inventory)
    roots, blobs = [], {}
    for value in values:
        identity, closure = codec.pack(value)
        codec.require(identity in closure, "batch root outside closure")
        roots.append(identity)
        for key, data in closure.items():
            codec.require(codec.SHA.fullmatch(key) and type(data) is bytes and codec.sha(data) == key,
                          "batch blob key differs")
            codec.require(key not in blobs or blobs[key] == data, "conflicting batch blob")
            blobs[key] = data
    codec.require(all(codec.SHA.fullmatch(key) and name == key+".json" for name, key in old.items()),
                  "invalid verified inventory")
    total = sum(codec.ordinary(store.objects/name).st_size for name in old)
    new = {key: data for key, data in blobs.items() if key+".json" not in old}
    codec.require(len(old)+len(new) <= codec.MAX_OBJECTS
                  and total+sum(map(len, new.values())) <= codec.MAX_TOTAL, "batch CAS publication budget")
    for key, data in blobs.items():
        store._check_directories()
        path = store.objects/(key+".json")
        if path.name in old:
            # A retained object disappearing mid-operation must not be healed.
            codec.require(codec.read_bytes(path) == data, "retained batch CAS differs")
        else:
            # An unexpectedly precreated key is not accepted as this writer's.
            codec.publish(path, data, store.hook)
    store._check_directories()
    return tuple(roots), {**old, **{key+".json": key for key in blobs}}
