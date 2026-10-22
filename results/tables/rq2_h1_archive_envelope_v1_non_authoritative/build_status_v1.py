"""Combine previously bound work units with the new logical-byte audit."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n',encoding='utf-8')


def main():
    old=HERE.parent/'rq2_h1_constructor_window_fault_v1_non_authoritative'
    business=HERE.parent/'rq2_h1_target_business_cost_v1_non_authoritative'
    audit_path=HERE/'archive_audit_v2.json';audit=load(audit_path)
    assert all(pin(name)==value for name,value in audit['bindings'].items())
    component_path=business/'budget_component_observation_v1.json';component=load(component_path)
    previous=old/'whole_workflow_budget_v4.json'
    budget=deepcopy(load(previous))
    budget['prior_budget']=dict(path=str(previous),sha256=pin(previous))
    budget['current_archive_audit']=dict(path=str(audit_path),sha256=pin(audit_path))
    budget['business_component_observation']=dict(path=str(component_path),sha256=pin(component_path),value=component)
    budget['logical_archive_capacity']=dict(
        old_observation=dict(raw_body_bytes=audit['sqlite']['raw_body_bytes'],sqlite_file_bytes=audit['sqlite']['file_bytes'],
            holder_content_bytes=audit['old_holder']['all_file_content_bytes'],case_files=465,owned_files=444),
        old_declared_holder_bound=audit['old_holder']['declared_logical_bound'],
        source_audit_ascii_cap_bytes=audit['source_cap']['bytes'],
        intent_pre_owner_declared_envelope_bytes=audit['intent_declared_envelope']['intent_body_bytes_bound'],
        intent_accepted_body_cap_bytes=audit['accepted_intent_body_bytes_bound'],
        declared_envelope_is_not_numerical_report_attainability=True,
        conditional_success_scenarios=audit['scenarios'],
        terminal_counts='3H+2W after clean terminal; paired prefix 3H-1+2W',
        alternate_witness_limit_enforced=False,failure_states=audit['failure_states'],
        physical_sqlite_journal_filesystem_upper_bound_bytes=None,
        exact_target_event_cap_profile_selected=False,resource_admission=False)
    for scenario in budget['logical_archive_capacity']['conditional_success_scenarios'].values():
        scenario['terminal_admissibility_condition']='FSM assessment.needs_next_hour is false; hours alone do not permit termination'
    budget['resource_registration_missing']=[
        'select and validate target event/record/source caps; enforce a bounded alternate policy',
        'SQLite page/header/freelist/journal and filesystem allocation bounds',
        'normal 232-stage and independent Rref/Actual archives, including failures before intent acceptance',
        'holder external-head retention, scratch/checkpoint/report/reserve/concurrency',
        'representative full source/owner/producer/terminal/fresh-process replay/failure wall and RSS',
        'concrete complete-volume admission and fixed activity/stop/cleanup plan']
    for target in budget['target_work_units'].values():
        target['minimum_events_path_condition']='clean success W=0, assessment.needs_next_hour=false, extra terminal call; not a general path upper bound'
    budget['stage_coverage'].append(dict(stage='business_history_and_encoding_component',
        evidence='one synthetic training JOINT/cohort with finite-v2 business parameter overlay, h168/h192',
        component_observation_known=True,target_scale_cost_known=False))
    budget['bindings']={str(path):pin(path) for path in (previous,audit_path,component_path)}
    budget_path=HERE/'whole_workflow_budget_v5.json';save(budget_path,budget)
    previous_state=old/'formal_preparation_state_v4.json'
    state=deepcopy(load(previous_state))
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    state['prior_preparation_state']=dict(path=str(previous_state),sha256=pin(previous_state))
    state['current_archive_capacity_evidence']=dict(path=str(audit_path),sha256=pin(audit_path),
        scope='conditional logical content; physical and complete resource registration remain open')
    state['current_business_component_evidence']=dict(path=str(component_path),sha256=pin(component_path),
        scope='one synthetic parameter-overlay history; not source authentication or whole-wall upper bound')
    state['current_whole_workflow_budget']=dict(path=str(budget_path),sha256=pin(budget_path))
    state['bindings'].update({str(path):pin(path) for path in (previous_state,budget_path,audit_path,component_path)})
    save(HERE/'formal_preparation_state_v5.json',state)
    h192=audit['scenarios']['192']
    report=f'''# 整链预算：owner / holder 容量核对

整链性能审查仍未完成，正式准备的 16 项门仍全部 OPEN。本次补齐 logical archive 口径、条件事件计数和原件核对；wall/RSS/总物理存储准入继续为 null。

旧 3h 原件按只读 SQLite `mode=ro` 核验：9 条 events 的 raw body 合计 {audit['sqlite']['raw_body_bytes']}B，SQLite 文件 {audit['sqlite']['file_bytes']}B，holder JSON 合计 {audit['old_holder']['all_file_content_excluding_lock']}B，另有 1B lock。465 个 case 文件与 444 个 owned 文件的名称/SHA 均未变；最近 business 69 项、constructor 208 项绑定均匹配。重建的 owner/holder 终点 heads 与外部 preclose checkpoint 相同；这仍是旧 synthetic case 的只读字节审计，未构造新的 owner 或可写凭据。

| T（模拟小时） | clean paired 后 events | 额外 terminal 后 events | 原 source Job replay | business 历史长度下界（3 lane 始终 active） |
|---|---:|---:|---:|---:|
| 168 | 503 | 504 | 458320 | 18966864 |
| 192 | 575 | 576 | 597520 | 28311936 |

表中事件数限定 W=0 且 FSM assessment 已不再 needs_next_hour；168h 仍有 primary pending 或 follow-up debt 时，下一次调用进入 attempt 而非 terminal。source Job replay 均指 saved Job artifact replay，不是 native solves。每个 alternate intent+witness 加 2。现实现没有独立的 W hard cap，仅 archive 容量会拒绝后续追加。完成 H<192 小时后，下一小时缺源/normal 失败可保留 attempt，DB 为 3H+2W；intent 已写而 outcome 未写为 3H+1+2W。holder 在提交失败窗口可领先 DB 一票，两者各受自身 cap 约束，不能在两个已声明 cap 外再加一票。旧 toy `max_events=32` 不适于此目标。

对 holder 自身 N/B/A，令 S=min(A,N×B)，每票 raw 长度为 b_i，n≤N、Σb_i≤S。由 ceil(b_i/3)≤(b_i+2)/3，Base64 总长≤4×floor((S+2N)/3)。加上 N 个最大 wrapper（sequence=N、最长 kind）及 accepted header≤4096B、writer lock=1B，得到有条件 logical file-content 上界。Base64 ASCII 不产生 JSON escape；测试逐字节对照原 encoder。该式不包含 SQLite pages/journal、filesystem allocation、目录元数据或外部 head/checkpoint。

仅以每条 B=1MiB、N=576、A=N×B 举例，raw-body cap 为 {h192['hypothetical_raw_body_content_cap']}B，holder logical bound 为 {h192['hypothetical_holder']['logical_content_bytes_bound']}B，两层内容合计 {h192['hypothetical_raw_plus_holder_content_bytes']}B。这是未采用的参数算例，不能作为磁盘准入或实际 192h 占用预测；当前配置没有修改。

原 source producer 与消费 owner 都强制 audit≤131072B 且 canonical。source encoder 为 ensure_ascii=True/no newline，owner 为 ensure_ascii=False/outer newline；对可由 owner UTF8 编码的 plain JSON，内嵌 object 字节数不大于 source ASCII 字节数。Unicode/control/float 小例和 lone-surrogate 拒绝测试支持实现对应；普遍不等式来自编码规则，未声称测试穷尽全部 JSON。

1 个 Rref 与 3 个 Actual 分别享有 max_stages=300、max_record_bytes=1MiB、max_total_bytes=16MiB。计入 source audit 后，pre-owner 声明包络为 {audit['intent_declared_envelope']['intent_body_bytes_bound']}B；owner 实际接受的 intent 仍≤{audit['accepted_intent_body_bytes_bound']}B。原 packer 接受的 1MiB pack-only padding 在 Base64 后已超过 event cap，仅说明 producer/packing 的声明不能保证稍后的 append 被接纳；它没有通过数值报告校验，不能视为科学反例或目标报告可达性证明。producer 与转换在 append 检查前已发生，昂贵失败档案仍需预算。

复用的 business 组件观测：单 synthetic training JOINT/cohort、finite-v2 business 参数覆盖，h168/h192 原 validator 各 0.0799385/0.0913091s；full carry 为 1836367/2118971B。owner scientific state 只存 identities/flags，不能拿 full-carry 字节当 owner event 大小。该组件也不能外推整体 wall 或关闭 source/phase 门。

最新 unit_02 为 38 项通过（2.85s，outer 3.939858s），保存 8 个明确执行依赖的运行前后 SHA 及 8 份 tested snapshots；其中 wrapper 长度向量是 accepted bodies 的 superset，canonical 代表票另经原 _ticket 接受。先前 unit_01 的 33 项观察结果缺少自身运行前字节绑定，原件保留，不用它单独证明 exact-byte acceptance。最新 audit_03 退出0（outer 2.773152s，768 bindings），补核外部 checkpoint heads；audit_02 原结果与执行源码保留。audit_01 因 checker 错把 owner genesis 当 header hash 失败，原运行源码与终态也保留；按原 owner_genesis 域分离规则修复后重核。各 audit 均未实例化 owner/source Reader、写旧 DB、启动 normal Job 或调用 native solver。

下一工作仍在预算关键路径：完成适用 source file/runtime/freshness 闭包及合法 source 路径选择；验证目标 cap profile 与 alternate policy，再补 normal/selector、SQLite/holder 外部持久化、失败/terminal/reopen 的完整成本。仅当整链预算有依据后，连接真实 167→168、携 primary debt 进入 follow-up、恢复后终结、上限携债与缺必要 source 的 typed unresolved/right-censor，最后 terminal→checkpoint→close→fresh-process replay。E=168/F≤24 原合同及全部科学验收限保持。

本包为 DRAFT_NONAUTHORITATIVE / PRE_SEAL 开发证据；formal_result、resource_admission、formal_execution_ready、full_192_hour_execution_verified、seal 与 official review 均未开放。具体 native/formal 运行仍需独立权限。
'''
    (HERE/'acceptance_report.md').write_text(report,encoding='utf-8')
    handoff='''# 预算续接：archive logical envelope

最新入口为本目录 acceptance_report.md、whole_workflow_budget_v5.json、formal_preparation_state_v5.json 及 final_verification.json。保留旧 constructor 208 / business 69 绑定包；不重跑 hour0/2h/3h、业务 cost_01 或 source profile。先 fresh 查 Git/进程及适用 agent.md/plan/blocker。

本次仅 static/只读 audit；最新 unit_02 38passed2.85s/outer3.939858s，8pre/post pins与8tested snapshots不变；audit_03补核retained checkpoint heads，exit0/outer2.773152s，768bindings。旧 9 body 268799B、SQLite294912B、holder362362B含lock；465case/444owned unchanged。source audit cap131072；每 selector 独立16MiB，1+3 groups 的 pre-owner intent包络89616768B，但accepted仍≤1MiB；pack-only例不是数值报告。T192 W0 paired575→额外terminal576，alternate每次+2且无独立W cap，pending attempt/intent/prepared holder tail分别计数。holder公式仅logical内容，不能作SQLite/FS/总磁盘上界。audit_01 checker genesis错误失败、audit_02及unit_01缺自带pre-code-binding的33项观察结果均保留。latest archive_audit_v2.json；此前report/budget草稿保存于before_review_01。

所有16准备门仍false，whole wall/RSS/storage null。继续先补 source适用file/runtime/determinism/freshness闭包与路径选择、target cap profile / alternate hard policy、normal与selector档案、SQLite/holder外部head、terminal/reopen/失败资源；之后才连接真正168h/≤24h阶段和episode终结。原owner未接candidate，源597520 Job replays仍baseline；conditional candidate298760不当采用，模型snapshot成本另算。q≤f×w与q+r≤D分别保持，recovery受headroom/debt/CFE surplus，不能误加q+r≤f×w。writer重建/crash、actual0..191/232-stage、solver/licence/pilot/certificate、same-contract training/holdout、seal/fresh official/具体formal-native权限均独立OPEN。

root sole writer；phase_budget_review只做non-authoritative PRE_SEAL，不签official。并行paper工作不碰；本scope未取得新的长链/native/formal启动权限。当前工作树保持dirty，无本session commit/push。
'''
    (HERE/'continuation_handoff_20261021.md').write_text(handoff,encoding='utf-8')
    print(json.dumps(dict(budget_sha256=pin(budget_path),state_sha256=pin(HERE/'formal_preparation_state_v5.json'),open_gates=16)))


if __name__=='__main__':main()
