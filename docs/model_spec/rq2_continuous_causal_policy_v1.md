# 连续服务固定因果策略与前缀审计 v1

日期：2026-09-13。状态：`DRAFT_NONAUTHORITATIVE`。本轮从四臂显式动作回放接续到一条固定的逐小时恢复策略，
形成当前观测→决策→物理/cohort校验→接受或拒绝记录的开发接口。
对应配置`configs/rq2_continuous_causal_policy_v1.DRAFT.yaml`，实现
`src/rq2_joint_deliverability_boundary_v1/causal_policy.py`，测试`tests/test_rq2_continuous_causal_policy_v1.py`。
旧协议、代码和结果保持原字节。

## 策略合同及信息边界

策略名为`full_request_edf_known_then_unknown_fifo_v1`，属于显式机制假设，不是观测到的运营策略。
每次入口只接收一个`CurrentObservation`：当前来源小时、当前业务/恢复上限与当前新增债务的deadline。
deadline在债务产生时揭示；没有已知deadline则保留unknown。接口不接收未来小时列表、forecast、horizon长度、
未来资源或任意用户callback。决策仅取固定策略、已验证状态/完整cohort账与本小时信息。
源split、双侧小时连续性及provenance在决策前校验。测试中的holdout只是合成身份标记，不新建公开数据split。

所有服务请求保留原始完整值，各臂沿用四臂投影口径，不按可用资源裁剪请求。
有effective调用时恢复为零；无调用时，在当前business headroom、maximum recovery power和`debt/eta`范围内尽量恢复，
CFE及joint轨道另受同小时CFE-compatible surplus约束。network-only不施加CFE目标。
恢复量分配先按已知deadline从早到晚，同deadline按出生小时；unknown债务排在所有known之后，按出生小时FIFO。
这包括先处理已经逾期的known债务；迟到恢复不删除到期短缺。

恢复功率向下量化到固定十进制网格，默认12位小数，再使用保守float表示，并沿用旧effective容差。
网格精度属于初始化时固定的策略参数，观察前缀中不可更改。量化或effective容差可能留下小额真实账面余额，
这些余额不补零，也可能触发合成deadline miss；不把此结果解释为经验服务违约率。
cohort分配使用精确`eta * recovery` work-energy，只分配给现有债务。

本策略不是优化器：不搜索替代可行策略，不保证最优或可持续性。full-request-or-stop是本草案的失败处理规则，
不代表真实运营系统遇到失败会停止。未来若要模拟削减服务、救援动作或连续违规过程，必须另定实际动作与状态递推合同。

## 四臂及B6

network-only、CFE-only和joint-correct在自身共享状态上运行同一条固定规则。
B6在两套分离规划状态上分别运行该规则，再按上轮`execute_b6_planned_step`合并原规划动作进行共享校验。
共享执行不重新选恢复量、不改分配以躲避失败。各轨及共享执行使用同一份当前资源输入与固定envelope。
若B6分离规划已通过、共享执行失败，失败记录保留`planned_step`，但两个提交cursor都停在上一已接受小时。
不得把planning末态当作物理状态或依据未提交planning末态继续未来小时。

48小时合成例在23/24/25小时各调用grid=0.125、CFE=0.125，共同deadline为出生小时+3。
当前共享business/CFE恢复头寸0.3125、eta=0.8。前三臂可完成给定观察窗口内的这些债务；
B6的每条分离轨道在26小时各决定恢复0.3125，合并0.625超过共享头寸，故共享执行拒绝。
该反例只是已固定机制规则的诊断，不是最低柔性前沿、数学不可行证明或经验B6效应。

## 接受、拒绝与审计字段

每个输入产生`PolicyRecord`，包含固定策略、原始当前观测、状态、阶段、错误原文、已形成的尝试动作、
可选planning成功step及可选accepted物理step。
只有整个小时通过校验，才更新物理和cohort状态。deadline miss并非物理拒绝：只要动作合法，该小时仍提交，
逾期历史留在cohort账，后续恢复仍可减少余额。

| 情形 | 处理 |
|---|---|
| 输入gap/split/provenance错误 | input_validation拒绝，无动作、无状态推进 |
| 完整请求无法形成非负功率动作 | policy_decision拒绝，原始请求保留；无完整动作时动作列表为空 |
| 包络或物理/cohort校验失败 | 记录对应replay阶段和错误，不提交该小时 |
| B6共享执行失败 | 保存独立planning结果作为诊断，提交状态均保持上一小时 |
| 合法动作但到期未清偿 | 接受小时，cohort逾期记录持续保留 |

第一次拒绝后cursor标记halted，再输入未来小时会被拒绝。失败记录只表示这个固定规则的尝试未被接口接受，
不表示该小时现实系统未服务，也不表示不存在其他可行策略。replay阶段错误还可能是合同或实现不一致，
不能把所有ValueError自动归类为业务违约。
不可变对象与记录校验用于开发一致性；手工重建完整对象是新初始化，不提供防恶意篡改或production checkpoint证书。

`summarize_policy_prefix`区分submitted小时数、accepted小时数、最后提交小时与rejected小时，
只汇总最后已提交物理轨道的债务与cohort状态。它不会把失败小时之前的状态说成失败小时末状态。
被拒绝小时及其后的实际动作、末债务和deadline结果保持未评价；已收到的失败观测不扩大accepted暴露分母。
right-censoring统计仅指在最后提交小时仍未观察到deadline的已接受cohorts。完整horizon的风险率、
服务完成率或completion claim均不由此前缀接口产生，`completion_claim_allowed=false`。

## 科学范围与后续

初始化沿用显式零历史合成假设；非零carry-in、异质逐服务deadline、正式split/coupling与真实业务参数仍未注册。
本轮不运行电网dispatch/AC/N-1或solver，不触及旧冻结threshold/协议/结果，不清理仓库。
正式科学协议、full-input、formal/result/claim/security各门继续关闭。
下一步可在固定机制情景下建立可复核的前缀结果包和失败类别汇总；完整连续失败轨迹与正式holdout风险统计
必须先补齐失败后的实际服务动作及状态合同，不能从本轮fail-stop前缀直接外推。

## 开发验收

审查补充合同：B6分离轨道与共享轨道的effective调用合计必须相等；容差分解不一致时在policy_decision阶段拒绝，
保留原始观测及其deadline。有限输入引起的数值OverflowError按当前阶段记录为未提交拒绝。
PolicyRecord绑定动作前的执行/规划状态，并从固定策略和当前观测重算状态、阶段、错误、动作及两个step；
PolicyCursor逐项检查相邻记录的状态链和末次提交状态。此校验提供开发重放一致性，不是密码学防篡改证明。

验收包括：48小时跨日状态与债务、相同历史前缀下动作一致、未来输入变化不影响既有前缀、
单小时输入限制、known EDF/unknown FIFO、当前headroom/CFE限制、无未来借债、B6失败原子性、
first-rejection停止、输入错误与物理拒绝分开、迟到恢复保留违规、量化余额与策略冻结。
独立pre-seal审查已完成；不生成official verdict或运行授权。

验证解释器：`D:/Miniconda3/envs/compute/python.exe -B`。编辑前核对git状态、计划/blocker和相关模块；
python/gurobi/highs进程检查未发现相关活跃正式运行。新增4个文件，另向plan/blocker追加开发状态，
不触及此前模块或结果目录。

针对性命令`python -B -m pytest -q tests/test_rq2_continuous_causal_policy_v1.py`最终得到`26 passed in 0.23s`。
完整相关回归命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

修复审查问题后的完整开发回归为`182 passed in 31.33s`。
独立只读`sol_reviewer`复核同一代码/测试字节：针对性`26 passed in 0.22s`，六文件回归`182 passed in 29.25s`，
`git diff --check`及12项新旧字节绑定均通过。B6容差分解、审计字段绑定和数值溢出三项问题已修复并有回归覆盖，
当前未发现开放实现问题。审查结论仅适用于本DRAFT开发范围；真实deadline、非零carry-in和完整失败轨迹仍待解决。
旧multiday/cohort/four-arm共9个config/code/tests绑定均与原记录匹配，sealed v5 outer绑定inner及其5个成员均匹配。
`git diff --check`通过。旧v5 symlink环境限制本轮未重跑，未视为关闭；本轮没有formal运行、solver、下载或付费查询。

本次开发字节标识（SHA256；不是seal）：

| 文件 | SHA256 |
|---|---|
| configs/rq2_continuous_causal_policy_v1.DRAFT.yaml | `03d2fe940088bd4d8a067d70c1e2604362535c45b332da98630523fbe275ace7` |
| src/rq2_joint_deliverability_boundary_v1/causal_policy.py | `ecad25be817437bbfa28bce782afa1a26da163bfe29e08151bb2d5e2799bd1c2` |
| tests/test_rq2_continuous_causal_policy_v1.py | `b4b5ac9b69f83c11a389a35d33711d8cf5da5e23b2da3b92802874c19f9bf092` |
