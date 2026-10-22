"""Record the integration decision and conditional successor costs, never admission."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'rq2_h1_archive_envelope_v1_non_authoritative'


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def main():
    prior_path=PREVIOUS/'final_verification.json';prior=load(prior_path)
    assert pin(prior_path)=='2d3abb3493b8b6ac3c43c9e71014206ba24b47d38e22fa23c98d29d7f73aec2f'
    assert len(prior['bindings'])==809 and all(pin(p)==v for p,v in prior['bindings'].items())
    unit=load(HERE/'unit_06/terminal.json')
    assert unit['exit_code']==0 and unit['changed_code']==[]
    assert unit['junit']==dict(tests=200,failures=0,errors=0,skipped=0)
    assert len(unit['code_bindings_before'])==18
    assert unit['code_bindings_before']==unit['code_bindings_after']
    assert all(pin(p)==v for p,v in unit['code_bindings_before'].items())
    inventory=load(HERE/'global_inventory_v1.json')
    assert all(pin(p)==v for p,v in inventory['bindings'].items())
    decision=dict(status='DRAFT_NONAUTHORITATIVE',scope='preseal_integration_decision_not_official_verdict',
        current_candidate='h1_phase_historical_batch_development_v2 + h1_phase_exact_source_batch_development_v2',
        candidate_bytes_changed=False,current_constructor_candidate_admissible=False,
        source_successor_adopted=False,existing_owner_remains_baseline=True,
        blockers=[
            dict(id='timed_parent_cleanup_dispatch',old_v2='parent close alias/code drift is rejected but dynamic cleanup leaves owners',
                detached_component='original timed-parent and cleanup-driver programs cloned with required builtins; tested actual Reader MRO fake owners',
                integrated=False),
            dict(id='three_parent_namespaces',old_v2='known-file observer ignores extra parent/events-root/anchor-root names',
                detached_component='original _inventory grammar, bounded suffix and retained entry identities for all three roots',
                integrated=False),
            dict(id='scientific_identity_reachable_globals',old_v2='model.json shim changes same typed packet input identity while guard and dependency snapshot pass',
                old_numeric_entry='validate_current rejects at borrowed model digest static-network check',
                closed=False),
            dict(id='path_descriptor_sweep',old_v2='read_bytes first post sweep is unchanged but subsequent same-input identity changes',
                old_numeric_entry='validate_current rejects H1 current input drift',closed=False)],
        proof_scope='unit control/data paths; no full historical Reader or two-Reader batch executed',
        detached_teardown_scope='original Reader MRO unchanged; original creator PID/thread required; parent close alias/code drift and owner/outer-lease errors',
        foreign_thread_rejection_verified=True,foreign_process_test='stored creator PID mismatch seam only, no actual fork/reopen',
        attempts_all_owners_when_close_raises=True,failed_owner_resource_release_proved=False,
        namespace_helper_entry_exit_dynamic_guard_integrated=False,
        unsupported_teardown_cases=['changed Reader bases/MRO inner ownership','owner.close program drift','arbitrary reflection'],
        old_known_file_observer_standins=['ReadView lease','Job view'],
        actual_temporary_namespace_and_read_checks=True,
        planned_H1_diagnostic_launched=False,
        H1_diagnostic_deferred_reason='repair and wire versioned successor before spending another saved-reader diagnostic on known gaps',
        current_launch_status=load(HERE/'launch_status_v1.json'),
        global_inventory_functions=inventory['visited_functions'],global_inventory_references=inventory['global_references'],
        global_inventory_not_a_complete_dynamic_closure=True,
        full_source_or_scientific_output_drift_proved=False,formal_result=False)
    decision_path=HERE/'source_adoption_decision_v1.json';save(decision_path,decision)
    budget_path=PREVIOUS/'whole_workflow_budget_v5.json'
    budget=deepcopy(load(budget_path))
    budget['prior_budget']=dict(path=str(budget_path),sha256=pin(budget_path))
    budget['source_adoption_decision']=dict(path=str(decision_path),sha256=pin(decision_path))
    for target in budget['target_work_units'].values():
        hypothetical=target['conditional_unadopted_candidate']
        hypothetical['current_v2_blocked_by_concrete_faults']=True
        hypothetical['usable_for_resource_discount']=False
        readers=target['reader_observations'];weight=target['reader_prefix_hour_weight']
        target['conditional_not_integrated_parent_namespace_support']=dict(
            proposed_bookends_per_reader=2,namespaces_per_bookend=3,
            directory_listings=6*readers,
            explicit_entry_stat_visits_if_only_current_prefix_present=2*(5*weight+readers),
            explicit_entry_stat_visits_with_full_allowed_192h_suffix_upper=2*961*readers,
            implicit_path_resolution_or_other_os_stat_calls_counted=False,
            full_suffix_count_basis='192 child directories + 384 event directories + 385 anchor files',
            extra_content_reads_by_this_helper=0,wall_or_rss_upper_bound_established=False,
            integrated=False,admission=False)
    budget['remaining_source_work']=[
        'versioned Reader/source/validator wire-up of tested teardown and three namespace observations',
        'all-hour packet scientific identity revalidation or complete applicable reachable dependency closure',
        'Path concrete descriptor/callable-state and method-global coverage plus nondeterminism windows',
        'saved Reader and two-Reader batch numerical/fault/cleanup equivalence under exact successor',
        'net source/owner cost including added guards, all-hour checks and failure/terminal/reopen']
    budget['bindings'].update({str(p):pin(p) for p in (budget_path,decision_path,HERE/'global_inventory_v1.json',HERE/'unit_06/terminal.json',HERE/'launch_status_v1.json')})
    output_budget=HERE/'whole_workflow_budget_v6.json';save(output_budget,budget)
    state_path=PREVIOUS/'formal_preparation_state_v5.json';state=deepcopy(load(state_path))
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    state['prior_preparation_state']=dict(path=str(state_path),sha256=pin(state_path))
    state['current_whole_workflow_budget']=dict(path=str(output_budget),sha256=pin(output_budget))
    state['current_development_evidence']['source_callable_gap']=dict(path=str(decision_path),sha256=pin(decision_path),
        scope='current candidate integration declined; detached cleanup/namespace support only',tests=200)
    for gate in state['gates']:
        if gate['id']=='source_path_performance_and_freshness':
            gate['remaining_work']='Current v2 has concrete parent-cleanup/namespace/scientific-global/Path-sweep gaps and is not admitted for integration. Wire a versioned successor with named repairs, applicable identity/freshness closure, all-hour coverage and full saved-reader/batch success/failure/cleanup equivalence; then select an admissible source path.'
    state['bindings'].update({str(p):pin(p) for p in (state_path,output_budget,decision_path)})
    save(HERE/'formal_preparation_state_v6.json',state)
    report='''# Source 候选接线判断与独立修复组件

当前 constructor v2 不可接入 owner。已从笼统“闭包未证”推进到可复现的 cleanup、namespace、科学 identity 和 Path sweep 缺口；旧 candidate / owner 字节未改。本包只增加独立 helper 和 unit，不能把组件测试解释成 source 已修好。

| 发现 | 实际验证 | 当前处置 |
|---|---|---|
| timed parent close descriptor/code 漂移 | 实际 Reader bases/MRO + fake owners：v2 guard 拒绝，但动态 super cleanup 遗留3 owners | 独立 helper 克隆原 timed-parent 与 outer-driver 程序，保留creator PID/thread检查；覆盖同故障、尝试各 owner/outer close、保留primary与首错、重复close；失败owner释放状态未证，尚未接线 |
| parent / events / anchor 根多出名字 | 原 known-file post observer 两次调用均返回；新 helper 的原 _inventory 拒绝 | lease/Job view为明确stand-in，其余临时目录、stable reads、hash与inventory真实执行；合法 interrupted suffix和observed entry replacement另验 |
| 模型间接 global | model.json shim 保持列明函数及 source/runtime tuple，same typed packet input identity 改变，原 validate_current 在借用model digest的static-network检查拒绝 | source identity closure仍OPEN；未运行完整Reader，不声称完整batch接纳或科学输出漂移 |
| Path 延迟 sweep | 新read_bytes第一次post sweep仍相同，下一次normal_input_identity改变，validate_current拒绝current input drift | concrete method descriptors/callable/global closure仍OPEN |

另外 isfinite 与 imported _validate_request._finite 漂移可绕过当前guard/bookends。LOAD_GLOBAL静态清单含nested code及可直接解析项目函数，共12函数/123条引用；25条来自函数globals的引用没有explicit alias slot guard。module attribute、instance dispatch、class descriptor、mutable values未展开，清单不是完整动态闭包。

最新 unit_06：200 passed /4.78s，outer5.756522s，18项before/after SHA map与18份tested snapshots保存且相同；其中171项旧constructor unit按原bytes纳入，新增29项。普通单元无normal Job/selector/native，也无完整保存Reader。unit_02 14fail来自新helper私有builtin namespace漏list，已补并增加LOAD_GLOBAL注册预检；unit_04 1fail来自错误预期较晚的input错误，实际先触发static-network drift，已按确切调用路线更正。所有失败stdout/JUnit/tested bytes及unit_01/03/05均保留。unit_05只有before map、tested snapshots和runner-derived changed_code=[]，不称其终态自行保存after map。

helper只承诺原Reader MRO未改变、creator PID/thread相符时的指定parent close alias/code窗口。foreign thread实际验证不消费capture/不关reader owners；PID检查仅stored-creator mismatch seam，未启动新进程。owner在实际释放前抛错的用例证明其余owners仍被尝试、primary带note、首错保留，失败owner释放不宣称成立。changed MRO的内部owners、owner.close程序自身漂移、任意反射仍未证；unsupported reader仍由原driver尝试全部外层leases并保留primary。namespace helper自身/原_inventory/Path entry-exit guard仍属后继接线工作。helper没有writer/solver/live capability。

预算v6仍使用原owner baseline：T192 597520次saved Job artifact replay；旧候选298760仅为历史条件算术，已明确不能作资源折扣。若后继在每Reader前后各增加三个namespace检查，T192会新增9276次目录list；仅当前prefix时explicit entry stat visits为1496892，允许完整192h suffix时上界2971412。这些是拟议调用路径的计数，不包括隐式_path解析stat、不建立wall/RSS上界，尚未执行或接线。

本次暂缓原计划的一次H1差分探针：launch_status_v1.json明确后发preseal_repair_plan覆盖design_and_budget中的conditional H1 launch，历史120s额度不是当前准入。已知不安全候选再跑同类Reader不能解除接线条件。下一步应把cleanup、三root namespace及all-hour scientific identity/Path闭包接入独立versioned Reader/source/validator，再固定具体保存Reader/batch的等价与净成本诊断。双独立Reader、paired前fresh以及完整post/失败检查继续保留。

完整整链预算、真正167→168/携债followup/诚实右删失/episode terminal→checkpoint→close→fresh-process replay仍未闭合；16准备门全部false，wall/RSS/物理总存储准入null。所有formal/native/resource/full192/seal/official标志保持false。本包不是official review或运行权限。
'''
    (HERE/'acceptance_report.md').write_text(report,encoding='utf-8')
    (HERE/'continuation_handoff_20261021.md').write_text('''# Source 接线关键缺口与独立支撑组件

最新入口：本目录 acceptance_report.md、source_adoption_decision_v1.json、whole_workflow_budget_v6.json、formal_preparation_state_v6.json、final_verification.json。先fresh查Git/进程及适用agent.md/plan/blocker，不动paper并行任务。上一archive809、constructor208、business69包/465case/444owned继续复用，既有candidate/owner字节不动。

本次unit06 200passed4.78s/outer5.756522s，18before/after SHA maps+18tested snapshots；只unit/static，未跑H1Reader、新N0/hour0/2h/3h、新Job/selector/native。原v2在timed parent close alias/code漂移时guard拒绝但cleanup留3owners；known-file后置observer漏source-parent/events/anchor根额外名字；model.json改变同typed packet的normal_input_identity而guard和modeldeps不变（validate_current先拒static-network drift）；Path first-post-sweep相同，后续inputidentity变、validate_current拒。故当前v2明确不准接线，不给298760条件Job replay折扣。

新 experiments/h1_constructor_rejection_support_development_v1.py 冻结原timed parent close与outer cleanup driver程序，保留原creator PID/thread约束；原MRO下指定parent descriptor/code漂移时尝试各owners并保留primary，失败owner释放未证。foreign-thread真实检查、stored-PID mismatch seam通过，未做实际fork/reopen。三个namespace以原_inventory语法核名字/entry identities，保留合法interrupted suffix。仅独立组件，未接Reader/source/owner；MRO改变的inner owners、owner.close自身漂移/任意反射未证，helper/_inventory/Path entry-exit guard待接线。namespace对照lease/Job view为standin，其余tmp目录/read/inventory真实。

需要下一独立versioned source/Reader/validator：接入cleanup与三个root namespace，并补all-H packet identity再验或适用reachable globals/descriptor闭包，明确Path concrete methods/callable state与非确定窗口。静态LOAD_GLOBAL仅12函数123引用（25函数globals slot未显式guard），不构成动态闭包。然后才值得登记保存H1/完整双Readerbatch的正/负例、cleanup及净成本；本次原H1探针未启动，旧120s额度不转授新路径。v6列拟议namespace2bookend计数：T192新增9276lists /1496892 current-only或2971412full-allowed-suffix explicit entry stat visits，隐式_path stat与wall/RSS未知。

保留unit02漏list的14fails及unit04错误message预期的1fail及所有tested bytes；unit05为历史before+changed_code记录，当前验收是unit06。launch_status_v1明确后发repair plan覆盖原design conditional H1 launch，当前无H1诊断准入。16准备门全false；整链预算、真实168h/≤24h/episode终结、writer/crash、actual0..191/232stage、solver/license/pilot/certificate、same-contract training/holdout、seal/fresh official/具体formal-native权限继续OPEN。原E168/F≤24、q≤f×w与q+r≤D分开、recovery headroom/debt/CFE surplus以及source缺口不补未来规则不变。
''',encoding='utf-8')
    print(json.dumps(dict(decision_sha256=pin(decision_path),budget_sha256=pin(output_budget),
        state_sha256=pin(HERE/'formal_preparation_state_v6.json'),open_gates=16)))


if __name__=='__main__':main()
