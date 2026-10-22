"""Preserve initial v7 bytes and disambiguate historical v2 observations."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def main():
    archive=HERE/'before_metadata_reconciliation_01'
    archive.mkdir()
    names=('whole_workflow_budget_v7.json','formal_preparation_state_v7.json','acceptance_report.md')
    before={}
    for name in names:
        original=HERE/name;copy=archive/name
        copy.write_bytes(original.read_bytes())
        before[str(original)]=dict(sha256=pin(original),copy=str(copy),copy_sha256=pin(copy))
    write(archive/'snapshot_bindings.json',before)
    budget=load(HERE/names[0])
    historical=budget.pop('observed_costs')
    historical['comparison_labels']=dict(old='source_batch_v1',new='constructor_historical_v2_and_source_batch_v2')
    historical['observation_scope']='prior rejected v2 candidate; not current v3 timings'
    budget['prior_v2_candidate_observed_costs']=historical
    write(HERE/names[0],budget)
    state=load(HERE/names[1])
    scaling=state['current_episode_scaling']
    scaling['rejected_v2_candidate_historical_counts']=scaling.pop('conditional_unadopted_candidate')
    scaling['conditional_unadopted_source_v3']=budget['target_work_units']['192']['conditional_unadopted_source_v3']
    development=state['current_development_evidence']
    development['prior_v2_successor_3h_full_batch_seconds']=development.pop('successor_3h_full_batch_seconds')
    development['prior_v2_unit_tests']=development.pop('latest_unit_tests')
    development['latest_unit_tests']=294
    development['latest_unit_evidence']='source_post_validation_v3/unit_07'
    development['historical_H1_comparison_versions']=dict(old='source_batch_v1',new='source_batch_v2')
    for name in ('short_comparison_H','fixed_order','repetitions_per_implementation','short_batch_seconds'):
        development['prior_v2_'+name]=development.pop(name)
    budget_path=HERE/'whole_workflow_budget_v7.json'
    state['current_whole_workflow_budget']=dict(path=str(budget_path),sha256=pin(budget_path))
    state['bindings'][str(budget_path)]=pin(budget_path)
    write(HERE/names[1],state)
    report=(HERE/names[2]).read_text(encoding='utf-8')
    old='H168成功且无需next时为504 events；H192为576（均含额外terminal调用）'
    new='H168成功且无需next时为paired503→追加1条episode_terminal→504 events；H192为paired575→追加1条episode_terminal→576（均需额外terminal调用）'
    assert report.count(old)==1
    report=report.replace(old,new)
    (HERE/names[2]).write_text(report,encoding='utf-8',newline='\n')
    expected=budget['target_work_units']['192']['conditional_unadopted_source_v3']
    assert scaling['conditional_unadopted_source_v3']==expected
    assert expected['additional_model_dependency_snapshots_with_all_hour_validation']==154018
    assert expected['numerical_dependency_source_hash_reads']==6160720
    assert expected['numerical_distribution_version_queries']==1078126
    assert expected['numerical_platform_queries']==308036
    assert expected['named_runtime_guard_scans_by_structure']==23963
    assert development['source_v3_saved_diagnostic']['batch_seconds']==88.38515499999994
    assert all(gate['complete'] is False for gate in state['gates'])
    result=dict(status='DRAFT_NONAUTHORITATIVE',scope='metadata provenance correction after read-only PRE_SEAL findings',
        before=before,after={str(HERE/name):pin(HERE/name) for name in names},script_sha256=pin(__file__),
        corrected=['version labels on old v2 timing/test/scaling fields',
            'current v3 scaling matches v7 budget','explicit paired-prefix plus terminal-event accounting'],
        terminal_event_formula_changed=False,formal_gate_changes=[],implementation_bytes_changed=False,
        saved_Reader_rerun=False,new_normal_jobs=0,real_native_calls=0,formal_result=False)
    with (HERE/'metadata_reconciliation_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(metadata_corrected=True,archived=len(names),implementation_changed=False,Reader_rerun=False)))


if __name__=='__main__':main()
