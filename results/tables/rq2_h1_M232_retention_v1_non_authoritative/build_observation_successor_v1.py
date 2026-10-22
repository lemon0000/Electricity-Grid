"""Retain the failed probe; version time-dependent accounting observations."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def replace_once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after)


def main():
    old=HERE/'packet_worker_v1.py';text=old.read_text(encoding='utf-8')
    text=replace_once(text,'from dataclasses import fields','from dataclasses import fields,is_dataclass\nfrom fractions import Fraction')
    helper='''def observe_accounting(source_v3,value):
    measured=source_v3.retained_size(value)
    seen=set();objects={};layouts={}
    def visit(item):
        if id(item) in seen:return
        seen.add(id(item))
        key=str(id(item));objects[key]=(type(item).__module__+'.'+type(item).__qualname__,sys.getsizeof(item))
        if is_dataclass(item) and not isinstance(item,type):
            if hasattr(item,'__dict__'):
                layouts[key]=dict(type=objects[key][0],instance_dict_bytes=sys.getsizeof(vars(item)))
            for field in fields(item):visit(getattr(item,field.name))
        elif type(item) is dict:
            for key,value in item.items():visit(key);visit(value)
        elif type(item) in (tuple,list,set,frozenset):
            for value in item:visit(value)
        elif type(item) is Fraction:visit(item.numerator);visit(item.denominator)
    visit(value)
    ordinary=sum(item[1] for item in objects.values())
    dictionaries=sum(item['instance_dict_bytes'] for item in layouts.values())
    return dict(observed_recursive_bytes=measured,ordinary_reachable_object_bytes=ordinary,
        instance_dict_bytes=dictionaries,layout_walk_sum=ordinary+dictionaries,
        original_measure_equals_layout_walk=measured==ordinary+dictionaries,
        reachable_object_types_and_sizes=objects,dataclass_instance_layouts=layouts)


'''
    text=replace_once(text,'def main():\n',helper+'def main():\n')
    text=replace_once(text,'started=time.perf_counter();times={};report={};error=None',
        'started=time.perf_counter();times={};report={};error=None\n    observations={};slots=None;original_slots=None')
    text=replace_once(text,"times['remember_one_actual_packet']=time.perf_counter()-tick\n            tick=time.perf_counter();source_v3._validate_all_packets(packets,1)",
        "times['remember_one_actual_packet']=time.perf_counter()-tick\n            report['v3_packet_accounting_bytes_at_remember']=size\n            observations['before_all_packet_validation']=observe_accounting(source_v3,packets[0])\n            tick=time.perf_counter();source_v3._validate_all_packets(packets,1)")
    text=replace_once(text,"times['validate_one_actual_packet']=time.perf_counter()-tick\n            component={}",
        "times['validate_one_actual_packet']=time.perf_counter()-tick\n            observations['after_all_packet_validation']=observe_accounting(source_v3,packets[0])\n            component={}")
    text=replace_once(text,'assert size==source_v3.retained_size(packets[0])',
        "observations['after_field_walks']=observe_accounting(source_v3,packets[0])")
    text=replace_once(text,'            assert container_size>=size\n','')
    text=replace_once(text,'assert rebuilt.identity==receipt.identity and denied==[]',
        "assert rebuilt.identity==receipt.identity and denied==[]\n            observations['after_source_revalidation']=observe_accounting(source_v3,packets[0])\n            assert source_v3._packet_digest(packet)==stored_pin[2]")
    text=replace_once(text,"source_declaration=request['declaration'],v3_packet_accounting_bytes=size,",
        "source_declaration=request['declaration'],v3_packet_accounting_bytes_at_remember=size,")
    before="""        report['solver_deny_hooks_restored']=all(getattr(owner,name) is value for (owner,name),value in zip(slots,original_slots,strict=True))
        assert report['solver_deny_hooks_restored']
    except BaseException:error=traceback.format_exc()[-16000:]
"""
    after="""    except BaseException:error=traceback.format_exc()[-16000:]
    finally:
        try:
            report['solver_deny_hooks_restored']=(slots is not None and original_slots is not None
                and all(getattr(owner,name) is value for (owner,name),value in zip(slots,original_slots,strict=True)))
        except BaseException:
            report['solver_deny_hooks_restored']=False
            error=error or traceback.format_exc()[-16000:]
"""
    text=replace_once(text,before,after)
    text=replace_once(text,'accepted=error is None and changes==[] and audit_errors==[]',
        "accepted=error is None and changes==[] and audit_errors==[] and report.get('solver_deny_hooks_restored') is True")
    text=replace_once(text,'stage_seconds=times,elapsed_seconds=time.perf_counter()-started,',
        "stage_seconds=times,elapsed_seconds=time.perf_counter()-started,\n        retained_accounting_checkpoints=observations,\n        accounting_stability_across_checkpoints_required=False,\n        packet_fields_or_domain_validation_relaxed=False,")
    text=replace_once(text,"'v3_packet_accounting_bytes','conditional_equal_footprint_products','error'",
        "'v3_packet_accounting_bytes_at_remember','conditional_equal_footprint_products','error'")
    worker=HERE/'packet_worker_v2.py'
    with worker.open('x',encoding='utf-8') as stream:stream.write(text)
    old_runner=HERE/'run_packet_v1.py';runner_text=old_runner.read_text(encoding='utf-8')
    assert runner_text.count('packet_worker_v1.py')==2 and runner_text.count('plan_v3.json')==2
    runner_text=runner_text.replace('packet_worker_v1.py','packet_worker_v2.py').replace('plan_v3.json','plan_v4.json')
    assert runner_text.count("'run_packet_v1.py'")==1
    runner_text=runner_text.replace("'run_packet_v1.py'","'run_packet_v2.py'")
    assert runner_text.count('v3_packet_accounting_bytes')==3
    runner_text=runner_text.replace('v3_packet_accounting_bytes','v3_packet_accounting_bytes_at_remember')
    runner_text=replace_once(runner_text,"worker['all_packets_container_recursive_bytes']>=worker['v3_packet_accounting_bytes_at_remember']",
        "worker['all_packets_container_recursive_bytes']>0\n        and set(worker.get('retained_accounting_checkpoints',{}))=={'before_all_packet_validation',\n            'after_all_packet_validation','after_field_walks','after_source_revalidation'}")
    runner=HERE/'run_packet_v2.py'
    with runner.open('x',encoding='utf-8') as stream:stream.write(runner_text)
    result=dict(status='DRAFT_NONAUTHORITATIVE',old_worker=str(old),old_worker_sha256=pin(old),
        new_worker=str(worker),new_worker_sha256=pin(worker),old_runner_sha256=pin(old_runner),
        new_runner=str(runner),new_runner_sha256=pin(runner),
        original_failed_attempt_retained=True,scientific_source_or_128MiB_gate_changed=False,
        reason='diagnostic incorrectly assumed recursive sys.getsizeof accounting was stable across later operations',
        formal_result=False)
    with (HERE/'successor_generation_v1.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(worker_v2=pin(worker),runner_v2=pin(runner),domain_changed=False)))


if __name__=='__main__':main()
