"""Fresh-process replay of a saved synthetic hour-0 packet; no producer calls.

The tiny source/registry seams are the same declared synthetic fixture as the
integration. All manifest, binding, tickets and expected state come from files.
"""
from base64 import b64decode
import json
from pathlib import Path
import sys
from time import perf_counter

from experiments import h1_selector_input_snapshot_development_v2 as snapshot
from experiments import h1_phase_historical_controller_development_v1 as historical
from tests.test_h1_saved_job_development_v1 import install_child_source
from tests.test_h1_hour0_end_to_end_development_v2 import complete_source_rows
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def synthetic_source(base):
    patch=install_child_source(base)
    no_solver.__wrapped__(patch)
    complete_source_rows(patch)
    source=snapshot.phase.source.source
    registry=snapshot.phase.source.registry
    declaration=json.loads((base/'synthetic_registry.json').read_bytes())
    identity=declaration['expected_registry_identity']
    config_pin=snapshot.common.bootstrap.phase.binding.SOURCE_CONFIG_PIN
    manifest=source.windows.load_source_window('power','training',0,1,outage_seed=20260822,
        expected_config_sha256=config_pin)['package_manifest_sha256']
    patch.setattr(registry.frozen,'PACKAGE_SHA',manifest)
    protocol=registry.events.DisclosureProtocol((registry.events.OutageComponent('generator','G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    from src.scenarios.rts_gmlc_n1_chronology import N1ReliabilityComponent
    components=(N1ReliabilityComponent('generator','G1',0.1,4.0),)
    def context(split):
        seed=20260822
        row=source.windows.load_source_window('power',split,0,1,outage_seed=seed,
            expected_config_sha256=config_pin)['rows'][0]
        return dict(split=split,protocol=protocol,caps={'G1':registry.Q(20)},components=components,
            rows={seed:{0:row}},catalog_entries=[dict(source_start=0,observed_end_inclusive=0,
                outage_seed=seed,chain_id=f'power:{split}:outage_seed={seed}')],
            gaps=[dict(split=split,outage_seed=seed,raw_start=0)],identity=identity,
            split_hour=99,archive_member_sha256='d'*64,cap_table_sha256='e'*64)
    patch.setattr(registry,'_load',context)
    patch.setattr(registry.frozen,'prefix_overlay',lambda *a:(('','',''),))
    patch.setattr(historical,'_source_paths',lambda d:(
        {Path(d['config_path']),Path(d['upstream_root'])/'SHA256SUMS'},{Path(d['upstream_root'])}))
    return patch


def replay(base,packet_path,packet_sha256,report_path,report_sha256):
    start=perf_counter();phase=snapshot.phase
    raw=snapshot.io.read_stable(packet_path,64*1024**2)[0]
    if snapshot.io.digest(raw)!=packet_sha256:raise ValueError('saved packet hash differs')
    packet=json.loads(raw)
    report_raw=snapshot.io.read_stable(report_path,64*1024**2)[0]
    if snapshot.io.digest(report_raw)!=report_sha256:raise ValueError('retained report hash differs')
    retained=json.loads(report_raw)['paired_replay']
    audit=packet['group_audit']['phase_manifest_candidate']['audit']
    manifest,binding,configuration=snapshot._declarations(audit['manifest'],
        packet['group_audit']['canonical_source_binding'],audit['selector_configuration']['configuration'])
    tickets=tuple(phase.AppendTicket(t['store_identity'],t['sequence'],tuple(t['before_heads']),
        t['kind'],b64decode(t['body'],validate=True)) for t in packet['tickets'])
    holder_root=Path(packet['common']['holder_receipt']['root'])
    owner_root=Path(packet['common']['owner_receipt']['root'])
    expected_heads=tuple(retained['phase_heads'])
    def denied(*args):raise AssertionError('saved replay attempted new retention')
    patch=synthetic_source(base)
    try:
        with phase.tickets.TicketHolder(holder_root,owner_root=owner_root,max_tickets=manifest.max_events,
                max_ticket_bytes=manifest.max_event_bytes,max_total_ticket_bytes=manifest.max_archive_bytes,
                create=False,expected_head=retained['holder_head'],retain_head=denied) as holder:
            assert holder.inspect()==tickets
            with phase.DevelopmentOwner(owner_root,manifest,binding,holder=holder,
                    create=False,expected_heads=expected_heads) as owner:
                observation=owner.inspect(expected_heads=expected_heads)
                with phase.closing(owner._connect()) as db:rows=owner._rows(db)
                checked,state,states=owner._restore(rows)
                assert observation==checked and checked.completed_hours==1
                assert not (checked.pending_intent or checked.pending_attempt or checked.recovery_required or checked.conflicted_keys)
                assert rows==[t.event for t in tickets]
                assert state.scientific==packet['after']==retained['state']
                assert json.loads(rows[-1][3])['projection']==packet['projection']
                assert phase.digest(state.scientific)==retained['carry_sha256']
                assert phase.digest(packet['projection'])==retained['projection_sha256']
                assert holder.head==retained['holder_head'] and owner.heads==expected_heads
        assert snapshot.io.read_stable(packet_path,64*1024**2)[0]==raw
        assert snapshot.io.read_stable(report_path,64*1024**2)[0]==report_raw
        return dict(scope='fresh_process_saved_synthetic_hour0_replay',packet_sha256=packet_sha256,
            report_sha256=report_sha256,phase_heads=expected_heads,holder_head=retained['holder_head'],
            carry_sha256=retained['carry_sha256'],projection_sha256=retained['projection_sha256'],
            completed_hours=1,paired_lanes=3,elapsed_seconds=perf_counter()-start,
            real_native_calls=0,Jobs=0,formal_result=False)
    finally:patch.undo()


if __name__=='__main__':
    base,packet,pin,report,report_pin,output=sys.argv[1:]
    result=replay(Path(base),Path(packet),pin,Path(report),report_pin)
    with Path(output).open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result),flush=True)
