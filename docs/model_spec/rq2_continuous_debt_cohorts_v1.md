# 连续多日恢复债务明细账 v1

状态：`DRAFT_NONAUTHORITATIVE`。这是连续服务草案的下一项开发前置组件，服务于RQ2的恢复时序与deadline语义。
它消费显式动作，尚非planner、物理校验器或正式协议。配置为`configs/rq2_continuous_debt_cohorts_v1.DRAFT.yaml`，
实现为`src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py`。旧草案、冻结协议和结果保持原字节。

## 明细账合同

每个产生正effective调用能量的小时建立一个cohort，记录`created_hour`、`due_hour`、deadline证据类别、
原始债务`incurred`、当前余额`remaining`及到期时未恢复量`missed_at_deadline`。
本版本假定一个小时内的新增债务共用一个deadline；异质逐job deadline需要后继细分，不能由本账推断。
每步必须是上一小时+1；轨迹身份和单一nonrolling accounting period随不可变账本携带，不能切换或reset。
完整已有cohort历史必须携带，不能只传入总债务后猜测其年龄。
构造空账本表示显式零carry-in机制情景；非零carry-in须提供全部cohorts及已观察到期snapshot。
手动重建对象视为重新初始化，不是受审计的延续；此开发对象没有持久化或防恶意篡改证书。

操作顺序为新增债务、按显式cohort分配恢复量、在小时末检查到期。
deadline=26表示在第26小时结束前清偿；第26小时内的恢复可计入准时偿还。
恢复分配是调用者显式给定的机制动作，本轮不选择EDF/FIFO策略或宣称分配最优。
未知deadline与已知deadline可以同时存在，不为unknown设默认到期日。

单位是同一功率基准下的work-energy；新增量为effective `q * dt`，恢复分配为`eta * r * dt`。
只接收非负`Fraction`精确有理数。效率仅在物理功率转换成恢复work时作用一次，不能再在账内乘一次。
每步满足`sum(remaining_next) = sum(remaining) + incurred - sum(allocations)`。
禁止超额恢复、从未来债务借用恢复、重复cohort分配和同小时新增调用与恢复并存。
所有正输入均入账，不在明细账内再次截断微量债务。

上游v1回放器的effective容差仍按其原合同执行；本模块不改变它。
只有上游已经校验call limit、服务功率平衡及business/CFE恢复头寸后，才能把对应effective能量送入本账。
本轮通过合成例逐时对照既有aggregate状态机，不提供两者的正式联合controller；任意手填allocations不证明有可用恢复功率。

## 逾期与观察结束

| 条件 | cohort状态 | 债务处理 |
|---|---|---|
| deadline未知 | deadline_unidentified | 即使已还清，也不声称准时 |
| 未来deadline尚未观察且仍欠债 | right_censored_before_deadline | 保留全部余额 |
| 已知deadline前/当时清偿 | recovered_by_deadline | 仅对该已观察cohort成立 |
| 到期小时末仍欠债 | deadline_missed | 固定记录当时短缺；迟到恢复不能抹去 |

到期短缺只在due-hour记录一次，不按后续每小时重复累计为新增逾期能量。迟到恢复继续减少余额，逾期历史永久保留。
账本校验要求到期已被观察时必须有完整snapshot，且当前余额不能大于到期短缺。
当`last_hour == due_hour`时，snapshot必须与当前余额严格相等；只有后续小时的迟到恢复才允许余额变小。
全部已知cohort清偿也不能推出整个连续服务horizon完成：未来小时可能产生新义务，unknown deadline仍未定义。
不会在observation end补零请求尾部或强制清债。

## 参数证据与开发情景

真实`service_deadline`、`recovery_deadline`仍为数据交付中的null。当前known deadline只允许
`mechanism_assumption`类别；无值只允许`unidentified`，拒绝伪装成observed。
synthetic fixture在23/24/25小时各新增0.25债务，假设due-hours分别为26/27/28；
26/27/28各恢复0.25 work，对应eta=0.8下0.3125恢复功率。due-hours是手算测试输入，未作正式参数注册。
与总账对照的债务轨迹为`0.25, 0.5, 0.75, 0.5, 0.25, 0`，24→25连续携带。
两笔债务即使总余额相同，不同恢复分配也可产生不同逾期结果；因此聚合债务不足以识别准时恢复。

## 验收与后续

验收覆盖跨日守恒、合成例与aggregate逐时一致、任意chunk携带、due-hour边界、迟到恢复保留违规、
unknown与right-censoring区分、相同总债务不同逾期、gap/身份/period漂移、无未来借债、重复分配与精确微量能量。
独立审查与实际运行记录追加于本文件末尾，结论仅限DRAFT开发。

下一步需要把选定的业务deadline机制和cohort分配与物理动作共同绑定到四臂回放接口，
并决定正式机制情景、会计期、split/coupling及raw>1映射。正式注册与数据科学门继续关闭。

## 开发验证记录

解释器：`D:/Miniconda3/envs/compute/python.exe`，调用均加`-B`。编辑前检查git状态及python/gurobi/highs进程，
未发现相关活跃正式运行。新增文件仅为本DRAFT文档、YAML、cohort实现和测试；另向执行计划/blocker追加开发状态。
本轮未启动solver、外部查询、下载或正式实验，未清理仓库。

针对性命令：`python -B -m pytest -q tests/test_rq2_continuous_debt_cohorts_v1.py`，首轮修正测试helper后为`21 passed in 0.28s`。
相关回归命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

开发中间回归为`122 passed in 40.82s`；审查finding修正后的最终相关回归为**`123 passed in 42.36s`**。
额外核验：上轮multiday config/code/tests三个hash、sealed v5 outer绑定inner及五个inner成员均匹配。
`git diff --check`通过。旧v5 symlink环境限制没有在本轮重跑或改写为通过。

独立只读pre-seal审查发现到期当小时构造账本缺少snapshot与remaining等值校验；
该项已修复并增加“due-hour拒绝不一致、后一小时允许迟到恢复”的回归测试。
审查性质为DRAFT开发复核，不是official verdict或review gate证书。
最终只读复核确认该finding闭合，无开放finding；reviewer独立focused为`22 passed in 0.22s`，
并逐项核对本节config/code/test hash匹配。该复核不关闭正式注册、数据输入或运行门。

最终测试字节（开发复核标识，非seal）：

| 文件 | SHA-256 |
|---|---|
| configs/rq2_continuous_debt_cohorts_v1.DRAFT.yaml | `1600625ff247a9da5610ff88c717c5ad327ab320608abfcc5348de56a100a01e` |
| src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py | `d10497c1e6ab5ff573dec8d938b5407a7e28277551b37a1e0d7f79b4241adaab` |
| tests/test_rq2_continuous_debt_cohorts_v1.py | `e5262911bece30cb5cb0033ef593970f49656349a9d09dbd69e90f9a7cc70c5e` |
