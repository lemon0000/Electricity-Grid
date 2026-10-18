"""Exact limits on the declared logical JSON envelope, using synthetic owners."""
import json

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,make,context,case,setup,legacy_setup,no_solver,load)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


def envelope(f,preview,record_cap,archive_cap):
    m=f.m
    header=json.loads(preview._header)
    header['max_record_bytes']=record_cap
    header['declaration']['total_archive_cap']=archive_cap
    raw_header=m.phase.encode(header)
    binding=m.phase.encode(dict(declaration=header['declaration'],
        journal_root=str(preview.root/'journal_non_authoritative'),root=str(preview.root),
        root_identity=(10**40-1,)*2,file_identity=(10**40-1,)*2,packet_stamp=(10**40-1,)*5,**m.FLAGS))
    sizes=[len(raw_header),len(binding)]
    previous=m.io.digest(raw_header)
    for index,event in enumerate(preview._events,1):
        raw=m.phase.encode(dict(sequence=index,previous=previous,body=event))
        sizes.append(len(raw));previous=m.io.digest(raw)
    return max(sizes),len(preview._packet)+sum(sizes)


@pytest.mark.parametrize('bound',['record','archive'])
@pytest.mark.parametrize('delta',[-1,0])
def test_exact_full_branch_cap_rejects_one_byte_less_before_effects(fault_case,bound,delta):
    f=fault_case
    with make(f) as preview:
        preview._guard.acquire();preview._bundle.enter();f.m.common.CommonOwnerGenesis._enter(f.c.owner)
        try:preview._prepare()
        finally:
            f.m.common.CommonOwnerGenesis._leave(f.c.owner);preview._bundle.leave();preview._guard.release()
        record_cap=f.options['max_record_bytes'];archive_cap=f.options['max_archive_bytes']
        for _ in range(8):
            needed_record,needed_archive=envelope(f,preview,record_cap,archive_cap)
            candidate=needed_record if bound=='record' else needed_archive
            current=record_cap if bound=='record' else archive_cap
            if current==candidate:break
            if bound=='record':record_cap=candidate
            else:archive_cap=candidate
        else:pytest.fail('logical cap did not reach a fixed point')
        cap_name='max_record_bytes' if bound=='record' else 'max_archive_bytes'
        assert not preview.root.exists()
    with make(f,**{cap_name:candidate+delta}) as owner:
        if delta:
            with pytest.raises(ValueError,match='complete handoff archive branch'):owner.consume()
            assert not owner.root.exists() and not f.c.owner.closed and not f.retained
        else:
            assert owner.consume()['completed_hours']==1
            used=sum(p.stat().st_size for p in owner.root.rglob('*.json'))
            assert used<=owner._caps[2]
