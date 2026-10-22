"""Prove shared bound inputs separately from additional attempt registration."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    first_path=HERE/'suite_01/request.json';last_path=HERE/'remaining_01/request.json'
    first=load(first_path)['sources_sha256'];last=load(last_path)['sources_sha256']
    common=set(first)&set(last);extra=set(last)-set(first)
    assert len(first)==2492 and len(last)==2584 and len(common)==2492 and not set(first)-set(last)
    mismatches=[name for name in common if first[name]!=last[name]]
    assert mismatches==[] and all(pin(path)==value for path,value in last.items())
    kinds={name:('original_suite_archive' if Path(name).is_relative_to(HERE/'suite_01')
        else 'support_archive' if Path(name).is_relative_to(HERE/'support_04')
        else 'completion_execution_or_registration') for name in sorted(extra)}
    counts=Counter(kinds.values())
    assert counts==dict(original_suite_archive=77,support_archive=8,completion_execution_or_registration=7)
    known={'attempt01_postcheck.json','plan_remaining_v1.json','postcheck_attempt01_v1.py',
        'preseal_findings_attempt01.json','register_remaining_v1.py','remaining_design_v1.md','run_remaining_v1.py'}
    assert {Path(name).name for name,kind in kinds.items() if kind=='completion_execution_or_registration'}==known
    fixture=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    fixture_pins={name:first[name] for name in common if Path(name).is_relative_to(fixture)}
    assert len(fixture_pins)==465
    worker=HERE/'fault_worker_v1.py'
    assert first[str(worker)]==last[str(worker)]==pin(worker)
    value=dict(status='DRAFT_NONAUTHORITATIVE',suite_source_pins_verified=len(first),
        completion_source_pins_verified=len(last),common_source_pins=len(common),
        common_hash_mismatches=0,common_hash_mismatch_paths=[],
        original_only_pins=0,added_registration_or_archival_pins=len(extra),
        added_pin_classification=counts,added_pin_paths_and_classes=kinds,
        common_saved_fixture_file_pins=465,worker_sha256=pin(worker),
        source_and_fixture_same_exact_bound_core=True,
        complete_dynamic_dependency_closure_proved=False,
        explanatory_field_scope='combination_postcheck.source_pins_verified=2584 is completion attempt only, not a sum or a suite01 count',
        new_runner_and_registration_bytes_are_additional_inputs=True,
        bindings={str(path):pin(path) for path in (Path(__file__),first_path,last_path,worker)},
        formal_result=False,resource_admission=False,formal_execution_ready=False)
    with (HERE/'source_contract_reconciliation_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value[key] for key in ('suite_source_pins_verified','completion_source_pins_verified',
        'common_source_pins','common_hash_mismatches','added_pin_classification')}))


if __name__=='__main__':main()
