"""Selected inclusive observations for one saved-path diagnostic process."""
from collections import Counter
import importlib
import time


def modules():
    names = dict(v2="src.staged_rts24_journal_v2", v3="src.staged_rts24_journal_v3",
        codec="src.staged_rts24_evidence_store_v1", c="src.staged_rts24_development_v1",
        policy="src.staged_rts24_causal_v2", audit="src.staged_rts24_causal_audit_v2",
        selective="src.staged_rts24_reference_queries_v1", batch="src.staged_rts24_append_store_v1")
    return {key: importlib.import_module(name) for key, name in names.items()}


class Observation:
    """One wrapper per alias group; no nested-time summation or OS-I/O claim."""
    def __init__(self, *, readonly=False):
        self.counts, self.seconds, self.bindings = Counter(), Counter(), []
        self.closed, self.readonly = False, readonly
        try: self._install(readonly)
        except BaseException:
            self.close()
            raise

    def _install(self, readonly):
        # Patch the original factories before importing scientific modules, then
        # cover saved grid aliases already loaded in a testing interpreter too.
        self.forbid(importlib.import_module("highspy"), "Highs")
        self.forbid(importlib.import_module("pyomo.environ"), "SolverFactory")
        self.m = m = modules()
        for name in ("src.grid.dc_opf", "src.grid.network_grid_need", "src.grid.scopf", "src.grid.rts_gmlc_scuc"):
            module = importlib.import_module(name)
            for key in ("SolverFactory", "Highs"):
                if hasattr(module, key): self.forbid(module, key)
        for name in ("hour_requests", "build_point_model"):
            self.forbid(m["c"], name)
        self.observe("selective", [(m[key], "reference_requests") for key in ("selective", "policy", "audit", "v2", "v3")])
        for name in ("read_bytes", "pack", "publish"):
            targets = [(m[key], name) for key in ("codec", "v2", "v3")]
            if readonly and name == "publish":
                for owner, attr in targets: self.forbid(owner, attr)
            else: self.observe(name, targets)
        for key in ("v2", "v3"):
            self.observe("runtime_"+key, [(m[key], "runtime_identity")])
        for name in ("prepare_hour", "propose_hour", "accept_hour", "execution_summary"):
            self.observe(name, [(m["policy"], name)])
        self.observe("audit_execution", [(m[key], "audit_execution") for key in ("audit", "v2", "v3")])
        for name in ("inventory", "_get"):
            self.observe(name, [(m["codec"].EvidenceStore, name)])
        if readonly: self.forbid(m["codec"].EvidenceStore, "put")
        else: self.observe("put", [(m["codec"].EvidenceStore, "put")])
        self.observe("deepcopy", [(m["v3"], "deepcopy")])
        self.observe("typed_equal", [(m["v3"], "typed_equal"), (m["batch"], "typed_equal")])
        self.observe("batch_publish", [(m["v3"], "publish_roots"), (m["batch"], "publish_roots")])
        self.check()

    def replace(self, owner, name, replacement):
        original = getattr(owner, name)
        # A module first imported under the factory guard may copy that guard.
        # Restore the real source function rather than leaking the dead guard.
        for _, _, source, installed in reversed(self.bindings):
            if original is installed: original = source
        self.bindings.append((owner, name, original, replacement))
        setattr(owner, name, replacement)

    def forbid(self, owner, name):
        def denied(*args, **kwargs):
            self.counts["forbidden_calls"] += 1
            raise RuntimeError("saved cost diagnostic forbids "+owner.__name__+"."+name)
        self.replace(owner, name, denied)

    def observe(self, name, targets):
        original = getattr(*targets[0])
        if not all(getattr(owner, attr) is original for owner, attr in targets):
            raise ValueError("observation alias mismatch: "+name)
        def wrapped(*args, **kwargs):
            self.counts[name+".started"] += 1
            started = time.perf_counter()
            try:
                result = original(*args, **kwargs)
                self.counts[name+".returned"] += 1
                if name == "read_bytes": self.counts["read_bytes.success_bytes"] += len(result)
                if name == "publish": self.counts["publish.success_bytes"] += len(args[1])
                if name == "selective":
                    self.counts["descriptions"] += len(result["requests"])
                    self.counts.update("role."+request.role for request in result["requests"])
                return result
            except BaseException:
                self.counts[name+".raised"] += 1
                raise
            finally: self.seconds[name] += time.perf_counter()-started
        for owner, attr in targets: self.replace(owner, attr, wrapped)

    def check(self):
        if self.closed or any(getattr(owner, name) is not expected for owner, name, _, expected in self.bindings):
            raise ValueError("observation or forbidden entry binding changed")

    def snapshot(self):
        self.check()
        return dict(counts=dict(self.counts), inclusive_seconds=dict(self.seconds))

    def close(self):
        changed = any(getattr(owner, name) is not expected for owner, name, _, expected in self.bindings)
        for owner, name, original, _ in reversed(self.bindings): setattr(owner, name, original)
        self.closed = True
        if changed: raise ValueError("observation binding drift; counts are not complete")

    def __enter__(self): return self

    def __exit__(self, *error): self.close()
