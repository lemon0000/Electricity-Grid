# 拒绝后的实际服务动作与债务递推合同 v1

日期：2026-09-13。状态：`DRAFT_NONAUTHORITATIVE`。本合同是RQ2连续服务机制的开发草案，
对应`configs/rq2_continuous_actual_action_contract_v1.DRAFT.yaml`、
`src/rq2_joint_deliverability_boundary_v1/actual_actions.py`及`tests/test_rq2_continuous_actual_action_contract_v1.py`。
它定义在已知原规划拒绝之后，如何校验一个显式声明的实际动作并延续共享物理/cohort状态。
所有实际动作均为`mechanism_assumption`，这里的“实际”指机制内执行层，未声称存在真实运行观测。

## 1. 原拒绝与后继轨迹

旧`PolicyCursor`在首次拒绝小时t仍只提交到t−1，且永久保持halted。旧结果包、协议、配置和代码字节保留。
新`ActualActionCursor`保存整个旧cursor为`origin`，以其最后已提交的共享物理状态作为起点。
首条输入必须逐字段等于origin中拒绝的`CurrentObservation`：来源小时、请求、deadline及limits均不得替换。
实际动作可以与原尝试动作不同，但必须分别保存，原规划拒绝不会因此消失。

只允许从`physical_execution`或`shared_execution`阶段的拒绝建立该后继对象。
输入身份错误、policy decision数值/调用分解异常及separate planning拒绝先走独立诊断；本草案不自动解释其实际后果。
即使属于允许的阶段，也不代表存在可继续的动作。新动作仍须通过全套原物理/cohort校验；不能从错误文本猜测可行性。

B6的旧分离planning状态和未提交`planned_step`留在origin中作为历史证据。后继只沿共享物理/cohort账推进，
不调用旧B6 planner，也不把实际恢复分配强行同步回两套虚拟账。底层共享cursor携带的旧`last_plan_cursor`只作为历史标记，
不可用于恢复旧策略；本接口不提供重新规划或恢复旧policy的入口。后继轨迹必须标为
`prescribed_actual_action_after_rejection_v1`，不能继续标为旧B6 fixed-policy execution或将两者合并比较。

## 2. 动作、观测与原约束

`DeclaredActualAction`仅包含：`recovery`、`actual_service_power`、按出生小时索引的精确`allocations`及证据类别。
调用方不能在动作里重新指定call limit、business headroom、CFE-compatible surplus或maximum recovery power。
这些约束始终取本小时原`CurrentObservation.limits`；固定envelope与period由已提交cursor携带。

各臂沿用原投影的完整请求。记g、c为本臂应履行的网络/CFE调用，b为合成baseline，r为effective恢复：

`p_actual = b - (g + c) + r`

`d_t = d_(t-1) + effective_call(g,c) - eta * effective_recovery(r)`。

时间步长保持一小时；调用与恢复沿用既有effective容差，cohort工作量仍使用精确十进制Fraction。
两条来源调用相加前的精确处理、physical/cohort一致性阈值均复用旧实现，未新增放宽。
network-only只取g；CFE-only只取c；joint及B6共享执行取g+c。
原事件duration/count/rest、调用能量、债务上限、功率平衡和恢复头寸逐小时检查，跨日不reset。
调用时不能恢复；恢复不能提前借用未来资源或偿还不存在的cohort。

只有恢复量或cohort分配的显式变化可以在本模型内表达。网络/CFE请求不能裁剪为实际完成量；
本草案没有引入非合同业务丢失、抢占损失、CFE目标违约后的服务替代或额外救援资源。
如果完整请求在原包络内无法实现，则该小时保持未评价；不得把硬约束变成罚项以使时钟继续走。
未来若需这些失效行为，必须先定义其功率、工作量、丢失/延期和风险指标合同，不能直接计入普通恢复债务。

## 3. 状态机与证据状态

| 条件 | 记录与状态 |
|---|---|
| 显式动作通过原校验 | `assumed_action_validated`；物理/cohort时钟推进一小时，保存ArmStep |
| 未提供实际动作（None） | `unassessed`、`missing_actual_action`；不推进任何状态 |
| 功率/恢复/分配/身份或数值校验失败 | `unassessed`与原错误；保存尝试动作，状态保持上一验证小时 |
| 首条观测替换或跳过拒绝小时 | 抛出接口错误；不生成新cursor |
| 前一实际小时未评价后继续输入 | 拒绝消费后续小时 |

typed数据结构本身非法时，构造/接口抛错，不承诺为任意Python对象生成科学记录。
观测的common source身份与相邻小时/split/provenance校验先于None动作判断；错误观测保留身份错误，
只有合法下一小时缺少动作才记为`missing_actual_action`，不能把跳时观测计为实际动作缺失的正常小时。
每条`ActualActionRecord`从before、原观测和显式动作重放并验证status/error/step；cursor校验相邻状态链。
该一致性校验用于开发审计，不是安全签名或production checkpoint。
缺失动作时没有实际递推；即使收到时间t的观测，也不能把t−1的余额说成t末余额。

合法零恢复会推进时钟，因此到期债务在到期小时留下`missed_at_deadline`；缺失动作不会推进时钟，因此deadline仍未评价。
迟到清偿只减少remaining，不删除历史短缺；unknown deadline始终unknown，已清偿也不补称按时完成。
首次origin拒绝及后来动作未评价不是数学不可行证明，也不是已观察的工程失效或经验服务违约。

## 4. 信息边界与指标合同

本入口每次仅接收当前观测和一个声明动作，没有选择动作的算法。动作序列可能由外部生成，
因此逐小时接口和确定性重放本身不能证明外部动作选择具有因果性。
本轮不提供自动fallback controller，不将结果用于固定策略holdout风险率。
后续若实现controller，必须在运行前固定规则，只依赖当前观测与已提交共享状态，并对未来后缀扰动做非预见性测试；
B6策略加补救规则必须有独立完整policy身份。

未来结果包必须分列：原policy接受前缀、原拒绝小时/原因、机制后继已验证小时、首个未评价小时及未提交后缀。
同一小时的旧规划拒绝和新实际动作是两种不同状态，不能作为两小时曝光或两个独立样本。
在本例中旧接受小时1–25与后继小时26–48合计覆盖48个机制小时，原拒绝记录额外保留但不增加时间分母。
origin的right-censoring保持原样；后继按自己的最后验证小时另行评估cohort，不回填旧结果。
`formal_result`、`paper_claim`、`security_certified`及科学协议/输入门保持false。

## 5. 解析例与验收矩阵

测试从旧causal fixture逐小时重建B6拒绝：小时23/24/25各产生总债务1/4，小时25余额3/4，
小时26原分离恢复各0.3125、共享0.625超限。下面两个声明后缀在新YAML中预先列出，均为合成动作示例：

| 声明后缀 | 小时26/27/28的恢复 | 小时26/27/28后债务 | 到期记录 |
|---|---|---|---|
| bounded_recovery | 每小时0.3125，按出生小时23/24/25各分配1/4 | 1/2、1/4、0 | 三笔到期短缺均0 |
| zero_recovery | 每小时0 | 3/4、3/4、3/4 | 三笔短缺分别在26/27/28写入1/4 |

两者延续到小时48，原事件数和累计调用能量仍为1与0.75，休息时间为23小时；旧halted cursor仍停在25。
两例说明原拒绝不能唯一确定实际债务结局，不是根据结果选择更优策略，也不构成已注册的补救政策比较。

| 验收项 | 检查 |
|---|---|
| 状态与债务守恒 | 48小时解析例及新调用债务累积 |
| 原拒绝不可改写 | origin仍halted、首次观测逐字段绑定、原policy拒绝继续 |
| 原边界不可放宽 | 超headroom、功率不平衡、调用时恢复、裁剪请求对应的功率均不能提交 |
| cohort语义 | 分配金额匹配、禁止未来cohort、到期短缺与迟到/unknown分开 |
| 缺失与失败 | None、无效动作、split/gap均不推进；不填后缀 |
| 审计 | 记录重放校验、禁止把mechanism_assumption改称observed |

下一项应先固定因果补救动作生成规则及B6后继policy身份，再开发完整后继结果包；
真实业务参数、丢失/抢占模型、非零carry-in及正式数据split仍是独立科学输入缺口。

## 6. 本轮验证记录

使用`D:/Miniconda3/envs/compute/python.exe -B`。编辑前核对git状态、仓库指令、计划/blocker、前缀合同及依赖模块；
相关进程检查未发现活跃正式运行。本轮新增4个文件，另向计划/blocker追加开发状态，未修改旧模型、冻结协议或结果。

针对性命令：`python -B -m pytest -q tests/test_rq2_continuous_actual_action_contract_v1.py`。
独立审查发现缺失动作分支曾绕过观测身份校验；现已改为先验证观测，补齐None与gap/split/provenance/错误arm组合。
修复后主线程针对性结果为`22 passed in 1.25s`。相关八文件命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_actual_action_contract_v1.py tests/test_rq2_continuous_prefix_diagnostics_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

修复后主线程最终八文件回归为`216 passed in 67.31s`。
独立只读`sol_reviewer`最终复核为`22 passed in 1.35s`及`216 passed in 65.59s`；唯一身份检查finding已闭合，
当前无开放实现finding。独立核对config/code/test哈希与下表一致，diff检查通过。
此结论仅为non-authoritative pre-seal findings，不是official verdict、receipt或运行授权。

旧前缀交付`--verify-existing`返回24组合/1038记录/replay匹配；此前16项文档SHA256绑定及本地公开数据交付7项成员哈希匹配。
`git diff --check`通过。旧v5 symlink环境项本轮未重跑，仍保留未验证状态。
本轮没有正式实验、solver、下载、付费查询、结果包重写或仓库清理。

本轮SHA256开发绑定（不是seal）：

| 文件 | SHA256 |
|---|---|
| configs/rq2_continuous_actual_action_contract_v1.DRAFT.yaml | `f7a29715385bbdb0c498a740d72219fa5d4011633ea70912d4c3f9de9beff54d` |
| src/rq2_joint_deliverability_boundary_v1/actual_actions.py | `370b544bd293b18431436ed2ed1d669d0f3cc29001ea63b3279a68ee6dc149a9` |
| tests/test_rq2_continuous_actual_action_contract_v1.py | `79c03a71024d2646d8f88425a3b2bbeb7aded839461cdcceb5abb0d05e38a5d2` |
