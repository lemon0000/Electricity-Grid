"""Accept raw packet evidence and separately validate layout decomposition."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
POINTS=('before_all_packet_validation','after_all_packet_validation','after_field_walks','after_source_revalidation')


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def validated_layout(point):
    if type(point) is not dict:return False
    if any(type(point.get(name)) is not int or point[name]<=0 for name in
           ('observed_recursive_bytes','layout_walk_sum','ordinary_reachable_object_bytes','instance_dict_bytes')):return False
    if point.get('original_measure_equals_layout_walk') is not True:return False
    if type(point.get('reachable_object_types_and_sizes')) is not dict or type(point.get('dataclass_instance_layouts')) is not dict:return False
    objects=point['reachable_object_types_and_sizes'];layouts=point['dataclass_instance_layouts']
    if any(type(item) is not list or len(item)!=2 or type(item[0]) is not str
           or type(item[1]) is not int or item[1]<=0 for item in objects.values()):return False
    if any(name not in objects or type(item) is not dict or item.get('type')!=objects[name][0]
           or type(item.get('instance_dict_bytes')) is not int or item['instance_dict_bytes']<=0
           for name,item in layouts.items()):return False
    return (point['observed_recursive_bytes']==point['layout_walk_sum']
        ==point['ordinary_reachable_object_bytes']+point['instance_dict_bytes']
        and sum(item[1] for item in objects.values())==point['ordinary_reachable_object_bytes']
        and sum(item['instance_dict_bytes'] for item in layouts.values())==point['instance_dict_bytes'])


def main():
    directory=HERE/'packet_02';outer=load(directory/'terminal.json');worker=load(directory/'worker_terminal.json')
    pins=load(directory/'request.json')['sources_sha256']
    assert all(pin(path)==value for path,value in pins.items())
    assert outer['accepted'] is True and outer['exit_code']==outer['process_exit_code']==0
    assert outer['reason'] is None and outer['error'] is None and outer['changed_sources']==[]
    assert outer['sources_checked_before']==outer['sources_checked_after']==len(pins)
    assert outer['observed_processes_remaining']==[] and outer['Python_optimize']==0
    assert worker==outer['worker'] and worker['error'] is None and worker['exit_code']==0
    assert worker['source_correspondence_rechecked'] and worker['solver_deny_hooks_restored']
    assert worker['stage_count']==232 and worker['relative_hour']==0
    assert worker['audit_errors']==worker['opened_input_pins_changed']==[]
    assert all(pin(path)==value for path,value in worker['opened_input_pins_before'].items())
    assert all(worker[name]==0 for name in ('Reader_invocations','model_builds','new_normal_jobs','selector_calls','real_native_solver_calls'))
    assert worker['accepted_normal_carry'] is None and worker['source_authenticated'] is False
    assert all(worker[name] is False for name in ('products_are_H192_upper_bounds','products_are_predictions_or_lower_bounds',
        'other_hours_proved_no_larger_than_origin','selected_frame_or_ChildInspection_created',
        'complete_H192_retention_or_all_source_rows_covered','after_boundary_or_future_carry_created','two_Reader_source_executed'))
    points=worker['retained_accounting_checkpoints'];assert set(points)==set(POINTS)
    assert all(type(points[name]['observed_recursive_bytes']) is int and points[name]['observed_recursive_bytes']>0 for name in POINTS)
    layouts_valid=all(validated_layout(points[name]) for name in POINTS)
    deltas=[]
    if layouts_valid:
        for before,after in zip(POINTS,POINTS[1:]):
            a,b=points[before],points[after]
            same_objects=a['reachable_object_types_and_sizes']==b['reachable_object_types_and_sizes']
            same_layout_objects=set(a['dataclass_instance_layouts'])==set(b['dataclass_instance_layouts'])
            changed=[]
            if same_layout_objects:
                for name,first in a['dataclass_instance_layouts'].items():
                    last=b['dataclass_instance_layouts'][name]
                    if first['instance_dict_bytes']!=last['instance_dict_bytes']:
                        changed.append(dict(object_id=name,type=first['type'],before=first['instance_dict_bytes'],after=last['instance_dict_bytes']))
            delta=b['observed_recursive_bytes']-a['observed_recursive_bytes']
            dict_delta=b['instance_dict_bytes']-a['instance_dict_bytes']
            deltas.append(dict(before=before,after=after,recursive_delta=delta,instance_dict_delta=dict_delta,
                ordinary_object_map_equal=same_objects,dataclass_object_sets_equal=same_layout_objects,
                changed_dataclass_instance_dicts=changed,
                delta_explained_by_observed_instance_dict_sizes=same_objects and same_layout_objects and delta==dict_delta))
    failure=load(HERE/'packet_01/terminal.json')
    assert failure['exit_code']==1 and failure['observed_processes_remaining']==[]
    assert 'AssertionError' in failure['worker']['error']
    summary={name:{key:points[name][key] for key in ('observed_recursive_bytes','ordinary_reachable_object_bytes',
        'instance_dict_bytes','layout_walk_sum','original_measure_equals_layout_walk')} for name in POINTS}
    result=dict(status='DRAFT_NONAUTHORITATIVE',raw_packet_evidence_accepted=True,
        layout_decomposition_evidence_accepted=layouts_valid,
        layout_decomposition_acceptance_is_separate_from_outer_exit=True,
        original_packet01_accepted=False,original_packet01_missing_values_reconstructed=False,
        original_packet01_full_source_freshness_proved=False,
        source_pins_verified=len(pins),opened_input_pins_verified=len(worker['opened_input_pins_before']),
        v3_packet_accounting_bytes_at_remember=worker['v3_packet_accounting_bytes_at_remember'],
        all_packets_container_recursive_bytes_after_fields_before_source_revalidation=worker['all_packets_container_recursive_bytes'],
        checkpoints=summary,checkpoint_deltas=deltas,
        conditional_equal_footprint_products=worker['conditional_equal_footprint_products'],
        products_are_bounds_or_predictions=False,
        v3_late_remeasurement_or_H192_cap_proved=False,
        stage_seconds=worker['stage_seconds'],worker_seconds=worker['elapsed_seconds'],
        runner_main_seconds=outer['outer_seconds'],peak_sampled_supervisor_and_child_RSS_bytes=outer['peak_sampled_tree_rss_bytes'],
        RSS_sampling_scope='spawn-monitor interval only; not pre/post SHA stages or instantaneous whole-main bound',
        output_logical_sample_peak_bytes=outer['peak_output_logical_bytes'],
        selected_frame_or_M232_Reader_cost_proved=False,original_source_or_128MiB_contract_changed=False,
        bindings={str(path):pin(path) for path in (Path(__file__),directory/'terminal.json',directory/'worker_terminal.json',
            directory/'request.json',HERE/'packet_01/terminal.json',HERE/'plan_v4.json',HERE/'packet_worker_v2.py',HERE/'run_packet_v2.py')},
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,real_native_solver_calls=0,formal_result=False)
    with (HERE/'postcheck_v1.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(raw_accepted=True,layout_accepted=layouts_valid,
        accounting=result['v3_packet_accounting_bytes_at_remember'],checkpoints=summary,
        runner_main_seconds=outer['outer_seconds'])))


if __name__=='__main__':main()
