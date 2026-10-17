"""Read-only continuation of failed synthetic preflight04; never a rerun PASS."""
import ast
from base64 import b64decode, b64encode
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
import pytest
from tests import h1_group_selector_integration_helpers_v2 as helper
from tests import test_h1_hour0_three_actual_preflight_v2 as fixture
from tests import test_h1_hour0_persistence_faults_development_v2 as persistence

BASE=Path('D:/h1_three_actual_preflight_04_non_authoritative/test_actual_helper_three_lanes0')
OUT=Path(__file__).resolve().parent
RUN=OUT/sys.argv[1]
RUN.mkdir(exist_ok=False)
(RUN/'tested_script.py').write_bytes(Path(__file__).read_bytes())
phase=helper.handoff.phase
snapshot=helper.handoff.snapshot

def inventory():
    return {str(p):sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file()}

def main():
    before=inventory();start=perf_counter();steps=[]
    def trace(label):
        row=dict(label=label,elapsed_seconds=perf_counter()-start)
        steps.append(row);print(json.dumps(row),flush=True)
    result=dict(formal_result=False,scope='saved-artifact continuation of failed preflight04',
        original_preflight_exit_code=1,adapter_close_call_counts_reconstructed=False)
    try:
        failed=OUT.parent/'three_actual_preflight_04'
        terminal=json.loads((failed/'terminal.json').read_bytes())
        assert terminal['exit_code']==1 and terminal['before']==terminal['after']
        for name,pin in terminal['before'].items():
            if Path(name).as_posix()!='tests/h1_group_selector_integration_helpers_v2.py':
                assert sha256((ROOT/name).read_bytes()).hexdigest()==pin,name
        root=next(BASE.glob('study/selector_phase_handoffs_non_authoritative/*'))
        raw=(root/'takeover_packet.json').read_bytes();packet=json.loads(raw)
        assert phase.encode(packet)==raw
        declaration=json.loads((BASE/'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())['declaration']
        assert packet['common']==declaration['provenance']
        view=deepcopy(declaration['provenance'])
        view['owner_receipt']['heads']=tuple(view['owner_receipt']['heads'])
        assert packet['common']!=view
        tree=ast.parse((ROOT/'tests/h1_group_selector_integration_helpers_v2.py').read_text())
        checks=[n for n in ast.walk(tree) if isinstance(n,ast.Assert) and 'common_view' in ast.unparse(n.test)]
        assert len(checks)==1
        check=compile(ast.Expression(checks[0].test),'<actual helper assertion>','eval')
        environment=dict(consumer=helper.handoff,packet=packet,common_view=view)
        assert eval(check,environment)
        for field in ('heads','genesis','root'):
            changed=deepcopy(view);changed['owner_receipt'][field]=('0'*64,)*2 if field=='heads' else 'changed'
            assert not eval(check,dict(environment,common_view=changed))
        trace('canonical_common_equal_and_mutations_rejected')
        with pytest.MonkeyPatch.context() as patch:
            s=fixture.legacy_setup.__wrapped__(patch,BASE)
            s=persistence.setup.__wrapped__(s,patch)
            s=fixture.setup.__wrapped__(s)
            # Original case captured this identity before context updated the solver spec.
            phase_pin=phase.implementation_identity(s.manifest)
            patch.setattr(phase,'implementation_identity',lambda manifest:phase_pin)
            manifest,binding,config=snapshot._declarations(declaration['manifest'],declaration['source_binding'],declaration['run_configuration'])
            assert phase.encode(replace(s.manifest,solver_specification=manifest.solver_specification))==phase.encode(manifest)
            assert phase.encode(s.binding)==phase.encode(binding)
            fixture.no_solver.__wrapped__(patch)
            tickets=tuple(phase.AppendTicket(t['store_identity'],t['sequence'],tuple(t['before_heads']),t['kind'],b64decode(t['body'],validate=True)) for t in packet['tickets'])
            records=phase._unpack_records(manifest,json.loads(tickets[0].body)['records'])
            plan=helper.handoff.preview._planned_bootstrap(manifest,binding,s.currents[0],
                owner_genesis=packet['common']['owner_receipt']['genesis'],
                holder_genesis=packet['common']['holder_receipt']['genesis'],
                reference_records=records['reference'],actual_records=records['actual'])
            assert plan.tickets==tickets
            assert packet['holder_records']==[b64encode(r).decode('ascii') for r in plan.holder_records]
            assert phase.encode(packet['retentions'])==phase.encode(plan.retentions)
            assert phase.encode(packet['projection'])==plan.projection
            assert phase.encode(packet['after'])==plan.after
            holder=Path(packet['common']['holder_receipt']['root'])
            for i,record in enumerate(plan.holder_records,1):assert (holder/f'{i:06d}.json').read_bytes()==record
            lanes=[c.lane_id for c in manifest.lanes]
            assert packet['dispositions']==[dict(lane_id=k,kind='paired_actual') for k in lanes]
            assert all(packet[k] is False for k in helper.handoff.FLAGS)
            for parent in packet['parents']:
                c=parent['completion'];p=Path(c['root'])
                assert sha256((p/'terminal.json').read_bytes()).hexdigest()==c['terminal_sha256']
                assert sha256((p/'worker_non_authoritative/selector_snapshot.json').read_bytes()).hexdigest()==parent['snapshot_sha256']
                scientific=Path(c['scientific_root'])
                assert sha256((scientific/'terminal.json').read_bytes()).hexdigest()==c['scientific_terminal_sha256']
            journal=root/'journal_non_authoritative';head=sha256((journal/'header.json').read_bytes()).hexdigest()
            for i in range(1,6):
                event=(journal/f'{i:020d}.json').read_bytes();row=json.loads(event)
                assert row['sequence']==i and row['previous']==head
                head=sha256(event).hexdigest()
            assert row['body']['completed_hours']==1
            assert row['body']['holder_head']==plan.retentions[-1][2]
            assert row['body']['phase_heads']==list(tickets[-1].after_heads)
            trace('saved_packet_plan_journal_and_holder_verified')
            outcome=dict(replay_inputs=dict(manifest=manifest,binding=binding,
                holder_root=holder,owner_root=Path(packet['common']['owner_receipt']['root']),
                holder_head=plan.retentions[-1][2],phase_heads=tickets[-1].after_heads,
                tickets=tickets,projection=plan.projection,after=plan.after))
            result['replay']=helper.reopen_paired(outcome,trace)
        result['status']='verified_saved_continuation'
    except BaseException:
        result['status']='failed';result['error']=traceback.format_exc();raise
    finally:
        result.update(before=before,after=inventory(),steps=steps,elapsed_seconds=perf_counter()-start)
        result['saved_bytes_unchanged']=result['before']==result['after']
        with (RUN/'continuation_result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
        assert result['saved_bytes_unchanged']

if __name__=='__main__':main()
