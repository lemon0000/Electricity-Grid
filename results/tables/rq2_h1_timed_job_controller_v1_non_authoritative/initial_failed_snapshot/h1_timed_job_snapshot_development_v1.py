"""Shared pinned-input snapshot protocol with timed Job child replay."""
from copy import deepcopy
from experiments import h1_timed_job_parent_development_v1 as parent

old,io = parent.old.snapshot,parent.io


class Snapshot(old.Snapshot,parent.SourceParent):
    # Shared input receipt validates the unchanged source/carry input protocol.
    # The distinct parent declaration binds all new child replay/entry code.
    pass


def open_snapshot(declaration,*,expected_parent_identity,expected_anchor_record):
    if type(declaration) is not dict: raise ValueError('exact parent declaration required')
    declaration = deepcopy(declaration)
    if io.digest(io.encode(declaration)) != io.pin(expected_parent_identity): raise ValueError('parent declaration hash differs')
    origin = old.binding.H1SourceDeclaration(**declaration['origin'])
    receipt = old.binding.load_pinned_current(origin,declaration['upstream_root'],config_path=declaration['config_path'])
    owner = Snapshot(declaration['root'],receipt.network,old.Rq2SolverSpec(**declaration['specification']),
        old.replay.H1HourReplayLimits(**declaration['limits']),origin=origin,
        upstream_root=declaration['upstream_root'],config_path=declaration['config_path'],dc_bus=declaration['dc_bus'],
        hours=declaration['hours'],expected_anchor_record=expected_anchor_record,expected_parent_identity=expected_parent_identity)
    if not io.same(owner._declaration,declaration):
        owner.close();raise ValueError('snapshot configuration differs')
    return owner
