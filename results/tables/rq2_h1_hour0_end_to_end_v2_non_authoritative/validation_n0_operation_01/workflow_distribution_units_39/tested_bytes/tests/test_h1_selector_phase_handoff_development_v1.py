"""Live alias parents and real persistent handoff; fabricated native/Job seams."""
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from experiments import h1_selector_phase_handoff_development_v1 as canonical
from tests.test_h1_selector_parent_controller_development_v1 import (
    harness,context,case,setup as base_setup,legacy_setup,sequence_factory,no_solver,load)


@pytest.fixture
def setup(base_setup,request):
    s=base_setup
    if request.node.name=='test_live_complete_pair_commits_exact_phase_and_retains_each_head':
        lane=s.manifest.lanes[0]
        unresolved=replace(lane,lane_id='unresolved',mechanism=replace(lane.mechanism,flexible_fraction=Fraction(1,2)))
        s.manifest=replace(s.manifest,lanes=(lane,unresolved))
    return s


@pytest.fixture
def handoff(harness,monkeypatch):
    h=harness
    module=load(canonical.__file__,'selector_phase_handoff_test_alias',monkeypatch,
        dict(h1_selector_parent_controller_development_v1=h.module))
    return h,module


def options(retain):
    return dict(retain_head=retain,max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2)


def test_missing_actual_keeps_genesis_and_releases_all_guards(handoff):
    h,m=handoff;p=h.module;c=h.context
    with p.Parent(h.root,h.raw,**h.options) as ref:
        receipt=ref.run();before=c.owner.inspect()
        with m.Handoff(c.owner,(ref,receipt),{'joint':None},**options(lambda *a:a[-1])) as consumer:
            with pytest.raises(ValueError,match='Actual execution missing or failed'):consumer.consume()
            assert not consumer.root.exists() and consumer._state=='failed'
            assert c.owner.inspect()==before
            ref.validate_completion(receipt)
            assert not ref._guard.locked() and not c.case.guard.locked()
            with pytest.raises(ValueError):consumer.consume()


def test_live_complete_pair_commits_exact_phase_and_retains_each_head(handoff):
    h,m=handoff;p=h.module;c=h.context;retained=[]
    with p.Parent(h.root,h.raw,**h.options) as ref:
        receipt=ref.run()
        raw=p.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
            reference_root=receipt.scientific_root,reference_terminal_sha256=receipt.scientific_terminal_sha256,
            reference_request_sha256=receipt.scientific_request_sha256,reference_max_archive_bytes=receipt.max_archive_bytes)
        with p.Parent(h.root.parent/'actual_parent_non_authoritative',raw,**h.options,
                reference_owner=ref,reference_completion=receipt) as actual:
            completed=actual.run()
            c.case.global_.head='d'*64
            c.case.global_.history.append(('d'*64,{'other_group':True}))
            def retain(root,before,after):
                assert ref._guard.locked() and actual._guard.locked() and c.case.guard.locked()
                with pytest.raises(ValueError):ref.close()
                with pytest.raises(ValueError):actual.close()
                n=len(retained)+1;body=json.loads((root/f'{n:020d}.json').read_bytes())
                assert body['previous']==before
                if n in (3,4):
                    # Prospective retention really precedes the corresponding holder file.
                    assert not (c.owner.holder_root/f'{n-2:06d}.json').exists()
                retained.append((before,after,body['body']['kind']))
                return after
            with m.Handoff(c.owner,(ref,receipt),{'joint':(actual,completed),'unresolved':None},**options(retain)) as consumer:
                report=consumer.consume()
                assert [r[2] for r in retained]==['takeover_intent','handoff_opened','holder_head_prepared_1',
                    'holder_head_prepared_2','bootstrap_consumed_terminal']
                assert report['journal_head']==retained[-1][1] and report['completed_hours']==1
                assert not any(report[k] for k in m.FLAGS)
                assert consumer._holder.inspect()==consumer._plan.tickets
                assert consumer._phase.heads==consumer._plan.tickets[-1].after_heads
                lanes={v['lane_id']:v for v in json.loads(consumer._plan.projection)['lanes']}
                assert lanes['joint']['status']=='paired_committed'
                assert lanes['unresolved']['status'] in ('business_input_unresolved','business_unresolved')
                assert lanes['unresolved']['before_business']==lanes['unresolved']['after_business']
                assert lanes['unresolved']['before_actual']==lanes['unresolved']['after_actual']
                assert c.owner.closed and not c.case.guard.locked()
                assert actual._reference_held is False and not actual._guard.locked() and not ref._guard.locked()
                with pytest.raises(ValueError,match='single-attempt'):consumer.consume()
                assert consumer._state=='complete'
            assert (consumer.root/'execution.lock').read_bytes()==b'0'
            assert len(retained)==5
