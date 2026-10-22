"""Versioned source observations and complete known work units, never admission."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from experiments.h1_phase_boundary_budget_development_v1 import schedule


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def main():
    post=load(HERE/'postcheck_v1.json')
    assert all(pin(path)==value for path,value in post['bindings'].items())
    previous=HERE.parent/'rq2_h1_source_callable_gap_v1_non_authoritative'
    budget_path=previous/'whole_workflow_budget_v6.json'
    state_path=previous/'formal_preparation_state_v6.json'
    budget=deepcopy(load(budget_path));state=deepcopy(load(state_path))
    assert len(state['gates'])==16 and all(gate['complete'] is False for gate in state['gates'])
    observations=post['observations']
    decision=dict(status='DRAFT_NONAUTHORITATIVE',scope='one_saved_H3_source_successor_development_evidence',
        successor='historical_v3 + source_batch_v3 + detached_validator_v2',
        old_v1_v2_and_current_owner_bytes_changed=False,old_v2_known_defects_remain_in_old_version=True,
        known_repairs_wired_into_new_Reader=True,all_hour_packet_validation_wired=True,
        fixed_saved_H3_double_Reader_diagnostic_completed=True,
        science_scope='saved audit identity-bound internal consistency with original join/projection and new normal decision',
        independently_implemented_scientific_oracle=False,direct_old_raw_scientific_bytes_read=False,
        shared_saved_manifest_resolver=True,one_field_packet_projection_standin=True,
        normal_path_unit_and_fault_cases=294,detached_saved_data_rejection_cases=21,
        constructor_failure_evidence='actual AST programs + exact-MRO stand-in owners',
        complete_real_saved_Reader_file_fault_matrix_verified=False,
        arbitrary_private_checker_reflection_covered=False,unobserved_between_bookends_ABA_covered=False,
        complete_dynamic_input_closure_proved=False,
        production_speedup_established=False,source_successor_adopted=False,
        existing_owner_remains_baseline=True,owner_rejects_new_batch_type=True,
        source_or_owner_resource_discount_admitted=False,
        next_work=['complete source applicability/failure-window evidence and integration decision',
            'versioned owner route only after its full-DAG net cost and failure/terminal/reopen scope are fixed',
            'actual H168/F<=24 phase-boundary and episode-terminal connection remains open'],
        resource_admission=False,formal_execution_ready=False,formal_result=False,native_execution_authorized=False,
        evidence=dict(postcheck_path=str(HERE/'postcheck_v1.json'),postcheck_sha256=pin(HERE/'postcheck_v1.json')))
    save('source_adoption_decision_v3.json',decision)
    targets={}
    for key,row in budget['target_work_units'].items():
        expected=schedule(row['hours'],terminal=True,public_inspect=True)
        for name in ('batch_calls','reader_observations','reader_prefix_hour_weight','materialized_currents'):
            assert row[name]==expected[name]
        R,P,B=row['reader_observations'],row['reader_prefix_hour_weight'],row['batch_calls']
        # Preserve the original cost data as explicitly historical/rejected.
        row['rejected_v2_candidate_historical_counts']=row.pop('conditional_unadopted_candidate')
        row['superseded_v6_namespace_two_bookend_proposal']=row.pop('conditional_not_integrated_parent_namespace_support')
        extra_deps=3*R+P
        candidate=dict(Reader_integration_development_only=True,owner_integrated=False,
            observations=R,parent_traversals=R,parent_prefix_hour_weight=P,
            saved_job_artifact_replays_by_structure=2*P,M5_stage_replays_by_structure=10*P,
            conditional_M232_stage_replays_by_structure=464*P,
            all_hour_packet_validations=P,full_packet_nine_field_digests=2*P,
            packet_retained_size_traversals=P,selected_frame_retained_size_traversals=2*row['materialized_currents'],
            explicit_model_bookend_snapshots=3*R,additional_model_dependency_snapshots_with_all_hour_validation=extra_deps,
            numerical_dependency_source_hash_reads=40*extra_deps,
            packet_audit_source_hash_reads=P,
            numerical_distribution_version_queries=7*extra_deps,
            numerical_platform_queries=2*extra_deps,
            named_runtime_guard_scans_by_structure=13*R+5*B,
            guard_scan_basis=dict(direct_checks_per_Reader=7,model_snapshots_per_Reader=3,
                checks_per_model_snapshot=2,source_entry_checks_per_batch=5),
            namespaced_root_listings=9*R,
            namespace_explicit_entry_stat_visits_if_only_current_prefix_present=3*(5*P+R),
            namespace_explicit_entry_stat_visits_with_full_192h_suffix_upper=3*961*R,
            prefix_known_content_observation_calls=3*R,additional_final_prefix_observation_calls_vs_v2=R,
            source_observation_calls_inside_Readers=3*R,additional_final_source_observation_calls_vs_v2=R,
            additional_final_view_unchanged_calls_vs_v2=R,
            total_numerical_model_or_implementation_internal_hash_calls_exhaustively_counted=False,
            implicit_path_resolution_stat_calls_exhaustively_counted=False,
            work_units_are_static_not_runtime_counters=True,
            historical_content_cap_per_Reader_bytes=128*1024**2,
            currents_content_cap_bytes=64*1024**2,
            overlapping_declared_containers_content_cap_bytes=320*1024**2,
            container_content_cap_does_not_bound_observed_model_allocator_or_RSS=True,
            observed_H3_named_runtime_inventory=observations[0]['named_runtime_inventory'],
            named_inventory_is_fixture_context_specific=True,
            dynamic_dependency_closure_complete=False,unobserved_ABA_covered=False,
            applicable_H192_packet_retention_and_M232_coverage_proved=False,
            usable_for_resource_discount=False,total_wall_admission_seconds=None,
            peak_rss_admission_bytes=None,total_storage_admission_bytes=None)
        row['conditional_unadopted_source_v3']=candidate
        targets[key]=candidate
    budget['prior_budget']=dict(path=str(budget_path),sha256=pin(budget_path))
    budget['source_adoption_decision']=dict(path=str(HERE/'source_adoption_decision_v3.json'),
        sha256=pin(HERE/'source_adoption_decision_v3.json'))
    budget['current_saved_H3_source_observation']=dict(
        postcheck_path=str(HERE/'postcheck_v1.json'),postcheck_sha256=pin(HERE/'postcheck_v1.json'),
        hours=3,stage_slots=5,repetitions=1,batch_seconds=post['batch_seconds'],
        worker_seconds=post['worker_seconds'],outer_seconds=post['runner_seconds'],
        peak_sampled_tree_rss_bytes=post['peak_sampled_tree_rss_bytes'],
        peak_output_logical_bytes=post['peak_output_logical_bytes'],observations=observations,
        current_owner_net_cost_or_H192_bound_established=False)
    budget['remaining_source_work']=[
        'applicable dependency/failure-window evidence beyond the finite named endpoint guard',
        'actual saved Reader file/owner failures rather than actual-AST stand-in owners alone',
        'M232/all-hour retention and target namespace/source scale resource evidence',
        'versioned owner integration and complete failure/terminal/reopen net-cost evidence']
    budget['remaining_whole_workflow_unknowns']=[
        'complete native N/selector/Rref/Actual producer costs and valid executable DAG',
        'complete owner business-history/cache/serialization and failure/terminal/reopen costs',
        'selected full-horizon archive event/callback/witness profile and physical SQLite/FS storage',
        'aggregate wall/RSS/storage admission; all three stay null',
        'H168/F<=24 source-connected boundary and episode termination with honest unresolved states']
    bound_paths=(budget_path,state_path,HERE/'source_adoption_decision_v3.json',HERE/'postcheck_v1.json',
        HERE/'probe_budget_v1.json',HERE/'preseal_findings_v1.json')
    budget['bindings'].update({str(path):pin(path) for path in bound_paths})
    save('whole_workflow_budget_v7.json',budget)
    state['prior_preparation_state']=dict(path=str(state_path),sha256=pin(state_path))
    state['current_whole_workflow_budget']=dict(path=str(HERE/'whole_workflow_budget_v7.json'),sha256=pin(HERE/'whole_workflow_budget_v7.json'))
    state['current_source_adoption_decision']=dict(path=str(HERE/'source_adoption_decision_v3.json'),sha256=pin(HERE/'source_adoption_decision_v3.json'))
    state['current_development_evidence']['source_v3_saved_diagnostic']=dict(
        batch_seconds=post['batch_seconds'],worker_seconds=post['worker_seconds'],outer_seconds=post['runner_seconds'],
        independently_implemented_scientific_oracle=False,raw_old_science_directly_read=False,
        internal_saved_identity_bound_reconstruction=True,tests=294,detached_rejection_cases=21,
        real_Reader_failure_matrix_complete=False,owner_integrated=False,source_successor_adopted=False)
    for gate in state['gates']:
        if gate['id']=='source_path_performance_and_freshness':
            gate['remaining_work']='Versioned v3 wired finite repairs and passed one saved H3 dual Reader. Complete applicable dependency/failure-window and target/M232 retention scope, then versioned owner integration/full net cost; existing owner remains baseline, no discount.'
        if gate['id']=='episode_workflow_budget':
            gate['remaining_work']='v7 enumerates baseline and conditional v3 added all-H/digest/model/namespace/guard work. Actual full-owner/native producer, failure/terminal/reopen and physical resources remain unbounded; aggregate wall/RSS/storage are null.'
    state['bindings'].update({str(path):pin(path) for path in (*bound_paths,HERE/'whole_workflow_budget_v7.json')})
    # Do not change live canonical documents currently pinned by the 950 bundle.
    state['canonical_plan_and_blocker_bytes_retained']=True
    state['formal_gate_changes']=[]
    save('formal_preparation_state_v7.json',state)
    T=targets['192']
    report=f'''# Source v3 保存诊断与整链预算 v7

historical v3/source batch v3/validator v2 已接入全部已处理小时的 packet 再验证、三轮 parent namespace 检查、最终 bookend 和独立 cleanup。已有 owner 保持原路径，并实际拒绝新 batch 类型。全部16个正式准备门保持 OPEN；总 wall/RSS/storage 准入上界继续为 null。

一次保存 H3/M5 双 Reader 已终态 exit0：batch {post['batch_seconds']:.6f}s、worker {post['worker_seconds']:.6f}s、outer {post['runner_seconds']:.6f}s。294 项 unit/fault/回归通过；18份unit snapshots和24份probe snapshots与对应源字节一致。21个detached拒绝项包括old owner拒新类型。旧950 bindings、465 case/444 owned和1322启动pins fresh核验；未新建Job/selector，native为0。

每个 Reader 只有一次 constructor traversal、各重新验证3个packet、各做3轮namespace、token独立。临时packet+selected-frame内容估算为122826/120546B。2秒采样tree RSS峰值197238784B；输出目录循环内logical峰值537988B，均非完整资源上界。case read-open累计23102；滞后heartbeat为18987，读取活动不等于科学进展。

科学核对是 saved audit identity-bound 的内部一致性重构，复用原join/projection、shared manifest resolver、显式one-field stand-in，还借用新current的normal decision；未直接读取旧raw science，也不是独立oracle。执行worker的输出字段重命名未列入其三项源码替换列表，已在postcheck.provenance_correction明确补记；它不改变科学路径。

| Reader | constructor s | all-H再验 s | final bookend s | 含cleanup总s |
|---|---:|---:|---:|---:|
| 1 | {observations[0]['stage_seconds']['constructor']:.6f} | {observations[0]['stage_seconds']['all_hour_packet_revalidation']:.6f} | {observations[0]['stage_seconds']['final_bookends']:.6f} | {observations[0]['seconds_including_cleanup']:.6f} |
| 2 | {observations[1]['stage_seconds']['constructor']:.6f} | {observations[1]['stage_seconds']['all_hour_packet_revalidation']:.6f} | {observations[1]['stage_seconds']['final_bookends']:.6f} | {observations[1]['seconds_including_cleanup']:.6f} |

这些时间嵌套于batch，不重复相加。与旧H3 83.976s并非同次交替对照，不作提速或H192预测。

T192、W=0且assessment.needs_next_hour=false的条件调度仍有773 source batches /1546 Readers /149380 prefix-hours。当前owner基线597520保存Job replay（M5 2987600 stage；M232仅结构条件值138624640），不扣减。若未来合法采用v3，条件Job replay为298760；还需{T['all_hour_packet_validations']}次validate_current、{T['full_packet_nine_field_digests']}次full packet digest、{T['additional_model_dependency_snapshots_with_all_hour_validation']}次新增model dependency snapshot、{T['namespaced_root_listings']}个根listing及{T['named_runtime_guard_scans_by_structure']}次named guard扫描。这些是代码结构推导，不是运行时计数。隐式Path stat、normal内部hash/数值模型及完整owner的成本没有穷尽。

E168/F≤24、recover_then_check、primary births只取enrollment、followup债务保留、缺必要source为U的合同和旧边界/target-business证据继续复用。q=g+c≤f*w 与 q+r≤D 分开。H168成功且无需next时为504 events；H192为576（均含额外terminal调用）；alternate witness每个加2且尚无独立W上限。旧32-event toy cap不足，archive/physical资源仍需具体profile。小时数本身不允许终结，有pending primary时保持attempt。

失败unit_01的bytes编码6fail、unit_03的copyreg懒cache1fail及所有当时bytes保留。当前guard先预热标准dataclass cache再exact pin；runtime记录由独立seal检查，公开checker漂移由独立程序拒绝，半构造Reader提前保留，finally直接cleanup并清私有引用。constructor-failure证据是actual AST + exact-MRO stand-in owners；真实保存文件/owner故障矩阵、private backup任意反射和bookend间ABA未闭合。

单Reader128MiB加values64MiB的重叠内容cap合计320MiB，不包含observed、model、allocator或RSS。全部16门、owner adoption、真实H168/≤24 producer连接、episode终结、writer/crash、M232、合法reuse DAG、same-contract bounds、seal/fresh official与具体formal/native authority仍需完成。本scope只读pre-seal findings没有official verdict。当前canonical plan/blocker已在旧950包pin中，字节保持；没有formal gate变化。
'''
    with (HERE/'acceptance_report.md').open('x',encoding='utf-8',newline='\n') as stream:stream.write(report)
    handoff='''# Source v3 交接

最新入口：本目录 acceptance_report.md、postcheck_v1.json、source_adoption_decision_v3.json、whole_workflow_budget_v7.json、formal_preparation_state_v7.json、final_verification.json。先fresh Git/进程/适用agent规则；root为R3唯一writer，现reviewer仅PRE_SEAL。当前goal继续active，16门全false。

新historical v3/source v3/validator v2/runtime guard已实际跑保存H3双Reader一次，batch88.385155/worker90.296220/outer94.0秒、2秒采样RSS197238784B；每Reader1遍历/allH3/namespace3；294units/21detached拒绝；465case/444owned/1322launch pins不变。postcheck另有2261 fresh bindings。旧950/809/208/69证据继续原样复用；未创建N0/Job/selector/native，owner仍旧版且拒新batch。

修复全部小时packet的input/audit/九字段digest与原validate_current、合计128MiB retained cap、三轮parent名字与inode、all-H后最终FS/source/model/runtime、独立copy关闭图、half-constructed Reader提前保留、private容器finally清理、runtime结构seal及公开checker独立预验。unit01 6fail和unit03 1fail保留。新代码和已完成probe保持字节，下一实质修改用versioned successor。

科学reconstruction借用新normal decision及原join/projection/shared resolver/one-field stand-in；不是独立oracle/旧raw science直接读取。worker额外输出字段rename已补记postcheck，不改worker或重跑。Job/stage及T192成本是结构推导；不作为runtimecounter或ETA。任意private-checker反射、未观测ABA、完整真实文件/owner失败矩阵未证。320MiB是重叠容器内容上限，RSS/observed/model另计。

继续顺序：先完成v3适用依赖/失败窗口与目标M232/retention覆盖的接线判断；若有合法owner后继，先完整DAG及本身资源预算，再验证failure/terminal/reopen净成本，随后才是source-connected hour167→168/≤24与episode终结。禁止重跑旧chain07、connected03 body、四batch比较或business cost01；canonicalplan/blocker被旧950 pin，当前不改。只读事实可直接复用，不能给v3候选298760 Job replay折扣；当前owner597520基线。native/长链/formal未授权，不启动。
'''
    with (HERE/'continuation_handoff_20261021.md').open('x',encoding='utf-8',newline='\n') as stream:stream.write(handoff)
    print(json.dumps(dict(budget_version=7,remaining_open_gates=16,baseline_192_job_replays=597520,
        conditional_v3_packet_validations=T['all_hour_packet_validations'],
        conditional_v3_full_packet_digests=T['full_packet_nine_field_digests'],
        conditional_v3_additional_dependency_snapshots=T['additional_model_dependency_snapshots_with_all_hour_validation'],
        source_adopted=False,whole_wall_admission_seconds=None)))


if __name__=='__main__':main()
