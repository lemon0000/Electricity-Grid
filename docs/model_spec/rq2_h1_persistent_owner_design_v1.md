# H1 current-only persistent owner 开发设计

DRAFT_NONAUTHORITATIVE。本文是后继实现的验收设计；持久 owner、实际执行与正式门禁均未完成。
已完成入口见 `rq2_h1_origin_current_information_development_v1.md`。根代理唯一写入，R3 独立只读审查。

## 目标与依赖

一个 enrollment root 持有共同 Rref 与 canonical lane roster。每小时从外部 retained N binding/head
调用 fresh current join；内部推导 outage origin/current action、物理 frame 与 cap。
不得接受 caller-built PreparedCurrent/Prefix/carry 作为认证凭据。
Rref、各 A lane 拥有独立 generation/disclosure carry；完整 business cursor 保留 cohort、debt、
event count、累计预算、due 与 None 语义。enrollment genesis 才初始化 zero-history。

第一版可仅消费已保存的 pinned selector records，零 solver replay。
input_mode=saved_record_replay，raw_ingress_owned=false、native_execution_authenticated=false、
whole_job_quiescence_verified=false、resource_admission=false、formal_execution_ready=false、formal_result=false。
真实 raw ingress/Job 尚未接通时不得把它称为真实执行 owner。

旧 episode_store 的整个类绑定完整 planned hours，不能原样复用。
可借鉴 `_Lease`、文件身份检查、SQLite DELETE/FULL、外部 retained head、intent-first 协议。
旧 normal_h1_projection_store 的 same-key sticky conflict 算法可借鉴，但它不推进 episode state，
64条 record 上限也不能用作完整研究容量声明。新实现放 experiments/tests/docs，旧 src 保持原字节。

## 单小时次序

1. 外部 retained owner head 与完整已提交 prefix 对应；重放恢复全部科学状态。
2. fresh N/current source/registry admission；核对 relative progress 与前序 normal boundary。
3. 持久 hour intent，绑定当前 inputs、N audit head、前序科学/audit heads、全部 lane 与 saved-record pins。
4. 重放 Rref 的完整 selector prefix，产生唯一共同 request projection；不立即发布。
5. 将该共同 request 与当前 CFE allocation、业务限制映射为各 lane 的 business candidate。
6. 对每个 candidate 计算 exact actual service power，再重放该 lane actual selector。
7. 复核 source/N/implementation；一个 SQLite transaction 发布 outer outcome、key witness/claim 和新 head。
8. 同一 hour outcome 重放后才返回可保留的新 head。candidate、raw 与失败证据均保留。

业务→actual exact balance：P_actual=(workload-grid_served-cfe_served+recovery)*normalized_unit_mw。
仅 actual accepted 后 business 与 actual carry 同时推进。任何异常发生在完整 outer outcome 之前，
共同 Rref 与所有 lane 都不发布。确定性 unresolved 可进入完整 outcome，但对应 lane 两状态均保持
before 并 halted；服务统计仅计 paired committed 记录。CFE-only 的 grid service 指标保持 None。

## 科学 identity 与 audit identity

小时科学 key 包括：enrollment 科学合同、relative hour、N 当前 scientific projection、规范化 outage
projection、Rref 前序 scientific carry、各 lane 完整业务状态及 actual carry、当前业务输入/mapping、
固定 selector/business policy 与 cap semantic identity。
不得纳入未来输入、完整 source window hash、split/seed/source labels、真实 clock offset、raw report SHA、
Job/inode/process identity 或 N audit head。来源标签变化不得改变同一科学 projection 的计算 key。

audit chain 单独保留以上来源与执行信息、实施 closure、真实 source clock、registry receipt、N binding/head、
selector saved raw hashes、全部 failure/conflict。相同 scientific key 不能据此越过 audit 对应检查。
相同 key 的不同 witness 若 scientific projection 相同则可保留；若不同则永久 unresolved_conflict，
保留首 witness，不覆盖，也不再暴露任一 projection 或其下游 continuation。

## 最小持久结构

- metadata：schema、canonical roster、policy/cap semantic identities、implementation、明确 record/byte bounds。
- hour_intents：seq、predecessor owner head、relative hour、当前 scientific key 与独立 audit payload。
- hour_outcomes：共同 Rref、各 lane before/candidate/paired after、完整 witness pins、status、新 outer head。
- key_claims/key_witnesses：首 projection、全部 unique raw witnesses、对应 audit 与 sticky conflict。

heads 从完整 append-only outcome prefix 重建。缓存不是事实来源。禁止反序列化任意可执行对象；
只有 canonical bounded records 的重新验证结果可恢复状态。reopen 必须提供独立保留的 exact head。
bare intent 不自动 retry。commit/return 模糊时当前 owner poisoned；恢复不得再次执行 effectful work。

## 需先闭合的业务适配边界

真实 raw0 没有 raw-1，而旧 BoundaryAnchor 要求非负编号。内部业务相对时钟与真实 source 时钟必须
明确分开；cohort birth、due、last_hour 同步平移，且训练/留出 audit 对应不得因规范化被绕过。
这属于待验证映射，不能假造一条真实前驱来源行。

CFE preallocation 保留 exact Fraction。显式绑定 pair/hour/allocation、单位与转换记录；禁止静默
float 化或引入新舍入门限。需要证明现有业务接口的合法输入域、exact balance、阈值邻域和恢复12位量化
兼容性；部分 Python 接口偶然接受 Fraction 不构成注册证明。
探针见 `results/tables/rq2_h1_operational_business_v1_non_authoritative/exact_boundary_probe.json`。
探针暴露表示/阈值差异，不证明这些差异在完整合法前置条件下可达。

## 168→192 follow-up

E=168 内登记评分义务。F≤24 按需继续判断 enrollment-born debt/due/outcome，不重置预算。
依据冻结 v2 合同第“登记评分与按需后续”节，follow-up 的新请求仍按共同固定规则执行，
其新 birth 和全部债务必须保留，但不递归扩大登记评分集，也不递归延长 primary observation window。
follow-up producer 从已接受的168小时 N/head/anchor继续，不能重新初始化 N 或 business。
每小时先验证 continuation need，再准备 source/N/Rref/business/actual；判断仍需且缺来源时保持 unresolved/right-censored。
全部登记 cohort 结局可判定或最后 due 后产生 stop certificate；末债不必为零，已知失败不能由晚恢复改写。
不填充虚假成功小时。旧168小时 controller/reader字节保持不变。

## 验收矩阵

- 当前 admission 拒绝：没有 intent，状态不变；原证据不删。
- intent 后缺 raw、record漂移、Rref失败或 late lane异常：保留 bare intent，全部 heads 不推进，无 suffix。
- business有效而 actual unresolved：两边都不推进，lane halted；candidate loss 不冒充已履约指标。
- actual成功但 outer commit 前崩溃：无已发布 pair。
- outer commit 成功但返回丢失：外部预计 next head reopen、零 solver 重放，不重复执行。
- same key/same raw：幂等；same key/不同 raw/相同 projection：保留多个 witness；不同 projection：sticky conflict。
- N/source/implementation 在 prepare 与 commit 之间变化：拒绝 outcome。
- roster缺失/重复/换序、公用Rref不一致、仅业务或仅actual有after：整个 outcome 无效。
- source标签/时钟改变但科学历史相同：科学key相同，audit不同；禁止跨audit拼接saved record。
- 两小时及跨168边界：完整 debt/event/budget/cohort连续，不能reset、不能伪造 recovery或忽略due。
- 非法copy/pickle、并发owner、文件替换、retained-head旧值、malformed/oversize journal与部分写入均拒绝。

完整 manifest、合法复用 DAG、同合同 LB/UB、资源准入、successor seal 和全新 official reviewer仍为后继门。
本文不提供 native 运行授权；具体新包及门禁齐备后另获明确授权。
