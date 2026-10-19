"""Separate-process synthetic replay with the complete original fixture seams.

No producer, solver, new retention or formal result is authorized by this entry.
The saved reader remains byte-pinned by the external postcheck launcher.
"""
import hashlib
from copy import deepcopy
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from tests import h1_hour0_saved_replay_v2 as saved
from experiments import h1_group_n0_common_input_binding_development_v2 as common


def complete_fixture(original):
    def install(base):
        patch=original(base)
        try:
            binding=saved.historical.binding
            raw=(binding.ROOT/binding.MANIFEST).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=binding.MANIFEST_PIN:
                raise ValueError('synthetic fixture manifest pin differs')
            resolver=binding.manifest._resolver(raw)
            patch.setattr(binding,'open_manifest',lambda:resolver)
            patch.setattr(binding,'precheck',lambda resolver,declaration,**kw:
                resolver.resolve(kw['family'],kw['ordinal']))
            patch.setattr(binding,'prevalidate_enrollment',
                lambda *a,**kw:dict(test_only_synthetic_source=True))
            return patch
        except BaseException:
            patch.undo()
            raise
    return install


def main():
    base,packet,pin,report,report_pin,output=sys.argv[1:]
    original=saved.synthetic_source
    saved.synthetic_source=complete_fixture(original)
    try:
        print(json.dumps(dict(stage="saved_phase_holder_replay_start")),flush=True)
        result=saved.replay(Path(base),Path(packet),pin,Path(report),report_pin)
        print(json.dumps(dict(stage="saved_phase_holder_replay_done",result=result)),flush=True)
        fault_start=perf_counter()
        # Exercise the real fresh verifier on copied reference arguments. The
        # retained files, hashes and owner journals are never modified here.
        raw=Path(report).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=report_pin:raise ValueError('retained report changed')
        reference=dict(local_terminal=dict(body=json.loads(raw)['N0_records'][0]))
        patch=saved.synthetic_source(Path(base))
        try:
            print(json.dumps(dict(stage="copied_reference_positive_start")),flush=True)
            common._historical(reference)
            result['copied_reference_positive_verified']=True
            rejected=[]
            for field,value in (
                    ('historical_verifier_identity','f'*64),
                    ('historical_verifier_schema','foreign_schema'),
                    ('full_numerical_hour_replays',3),
                    ('fresh_byte_context_revalidations',3),
                    ('recomputed_on_revalidation',True)):
                changed=deepcopy(reference)
                assert changed['local_terminal']['body'][field]!=value
                changed['local_terminal']['body'][field]=value
                print(json.dumps(dict(stage="copied_reference_fault_start",field=field)),flush=True)
                try:common._historical(changed)
                except ValueError as error:
                    if str(error)!='retained historical verifier differs':raise
                    rejected.append(field)
                else:raise AssertionError('altered verifier contract accepted: '+field)
            result['copied_reference_verifier_field_rejections']=rejected
            result['retained_contract_fault_scope']='copied reference argument; persisted bytes unchanged'
        finally:patch.undo()
        result['copied_reference_fresh_verifications']=1+len(rejected)
        result['copied_reference_validation_seconds']=perf_counter()-fault_start
    finally:
        saved.synthetic_source=original
    with Path(output).open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result),flush=True)


def observed_main():
    from tests.h1_gil_stack_observer_development_v1 import observe_owner_stack
    output=Path(sys.argv[-1]).parent
    with observe_owner_stack(output/'python_stack_samples.jsonl',interval_seconds=30.,
            max_samples=64,max_frames=16,max_bytes=1024**2) as receipt:
        main()
    with (output/'python_stack_observer_closed.json').open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2)


if __name__=='__main__':observed_main()
