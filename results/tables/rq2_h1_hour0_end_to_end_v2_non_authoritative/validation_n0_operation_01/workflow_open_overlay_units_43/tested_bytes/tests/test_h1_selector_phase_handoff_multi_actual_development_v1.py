"""Two complete live Parent-alias Actuals; fabricated solver and Job seams."""
from contextlib import ExitStack
from dataclasses import replace
import json

import pytest

from experiments import h1_selector_phase_handoff_development_v1 as canonical
from tests.test_h1_selector_parent_controller_development_v1 import (
    harness,context,case,setup as base_setup,legacy_setup,sequence_factory,no_solver,load)
from tests.test_h1_selector_phase_handoff_development_v1 import options


@pytest.fixture
def setup(base_setup):
    s=base_setup;lane=s.manifest.lanes[0]
    s.manifest=replace(s.manifest,lanes=(lane,replace(lane,lane_id='second')))
    return s


def test_two_complete_actuals_share_exact_reference_and_commit_all_lanes(harness,monkeypatch):
    h=harness;p=h.module;c=h.context
    m=load(canonical.__file__,'selector_phase_handoff_multi_actual_test_alias',monkeypatch,
        dict(h1_selector_parent_controller_development_v1=p))
    with ExitStack() as stack:
        reference=stack.enter_context(p.Parent(h.root,h.raw,**h.options));ref=reference.run()
        pairs={}
        for lane in ('joint','second'):
            raw=p.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id=lane,
                reference_root=ref.scientific_root,reference_terminal_sha256=ref.scientific_terminal_sha256,
                reference_request_sha256=ref.scientific_request_sha256,reference_max_archive_bytes=ref.max_archive_bytes)
            parent=stack.enter_context(p.Parent(h.root.parent/f'{lane}_actual_parent_non_authoritative',raw,
                **h.options,reference_owner=reference,reference_completion=ref))
            pairs[lane]=(parent,parent.run())
        retained=[]
        def retain(root,before,after):
            assert reference._guard.locked() and c.case.guard.locked()
            assert all(owner._guard.locked() and owner._reference_held for owner,_ in pairs.values())
            retained.append((before,after));return after
        with m.Handoff(c.owner,(reference,ref),pairs,**options(retain)) as owner:
            result=owner.consume()
            assert len(retained)==5 and result['completed_hours']==1
            assert not any(result[k] for k in m.FLAGS)
            projection=json.loads(owner._plan.projection)
            assert [(r['lane_id'],r['status']) for r in projection['lanes']]==[
                ('joint','paired_committed'),('second','paired_committed')]
            packet=json.loads((owner.root/'takeover_packet.json').read_bytes())
            assert packet['dispositions']==[dict(lane_id=k,kind='paired_actual') for k in ('joint','second')]
            assert [r['lane_id'] for r in packet['parents']]==[None,'joint','second']
            assert owner._holder.inspect()==owner._plan.tickets
            assert owner._phase.heads==owner._plan.tickets[-1].after_heads
            assert all(not actual._guard.locked() and not actual._reference_held for actual,_ in pairs.values())
            assert not reference._guard.locked() and not c.case.guard.locked()
