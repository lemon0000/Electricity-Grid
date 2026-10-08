# 固定实际功率的数值调度选择

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal限定范围无开放实质finding。
实现`actual_dispatch_selector.py`，测试`test_rq2_actual_dispatch_selector_v1.py`。
对应共同参考设计§4的各臂fixed-power分支，复用原current_grid_step约束与owned native pipeline。
本组件中的actual指机制下候选执行状态；不是电网实际观测，也未连接四臂业务事务。

## 输入与策略身份

输入为隔离当前信息、当前outage disclosure、受控ActualDispatchOrigin/State及PrescribedDcPower。
exact MW分子/分母、source hour和机制角色由原功率类型验证；result显式保存完整功率对象，selection摘要也包含它。
模型始终固定该功率，不选择业务响应、改变恢复功率或生成共同请求。

origin从显式初态经initialize_actual_carry核验后创建；不接受raw carry、ReferenceGridOrigin/State替代actual wrapper。
origin即绑定selector、solver、预算、runtime和源码闭包生成的policy identity；同一origin首小时失败后换参数也拒绝。
后继绑定origin、previous wrapper、policy、selection证据及最终物理carry；不能将普通可行赋值转成已选择状态。
接口无法阻止调用者另建新的origin/实验，正式防结果调参仍须外部预注册及attempt记录。
网侧状态暂不带arm/business policy身份，后续四臂事务须同时绑定臂、业务cursor和网侧state，不能仅凭同值物理状态推断同一业务历史。

## 选择与数值验收

每小时最小化`(sum(abs(p_g-p_plan_g)), p_g按唯一排序UID)`；fixed/disabled UID仍计入。
L1由双侧非负辅助量表达；每级fresh建模，把此前canonical float目标原值固定为等式，记录float.hex。
另以Q(str)重算真实L1和全部generation目标，并检查本级目标、所有此前目标以及辅助量总和。
显式lock_tolerance_mw满足`0 <= lock <= absolute_gap_mw <= 1e-6`；零lock代表严格相等，不round。
物理和辅助不等式保持继承的1e-6 MW门；gap和目标lock分开记录，不声明最终累计误差或精确lex证书。

每级要求owned optimal、唯一完整native赋值、fresh物理验收、finite非负LB/UB/objective、
`LB <= objective ≈ UB`及显式absolute/relative gap，relative分母为`max(abs(UB),1e-12)`。
最终generation逐UID必须等于最后赋值审计生成的carry，全部n+1级通过才提供next_dispatch_state。
flow/angle可能非唯一，它们不进入现有跨小时carry；若以后参与状态，须扩展选择合同。

首次求解前检查完整n+1次调用、每级solver limit之和、线程，以及最后一级最大模型规模。
时间预算是native limit之和，不是整个Python执行的wall-clock watchdog。
GridDevelopmentBudget硬上限20 calls，因此当前最多19个generator UID；正式RTS规模不在该接口能力内。

## 拒绝与实际动作语义

| 情形 | 本接口输出/动作 | 后续业务事务必须保持 |
|---|---|---|
| 来源/时钟/identity错误、非法功率、策略变更或预算不合格 | 首次native求解前抛出输入拒绝 | 不提交业务或网侧状态；不是服务失败观测 |
| timeout、feasible-only、missing bounds/assignment、原生矛盾 | result unresolved，保存已运行级，无next state | 不降级提交早期或单级可行见证，不消费后缀 |
| 物理残差或目标/锁定残差越门 | 保留赋值、残差和错误，无next state | 不调整业务功率、请求、阈值或债务以强行继续 |
| 全级通过 | 提供owned候选网侧后继及exact功率证据 | 仍需业务candidate通过并与功率/来源/臂身份一致才共同提交 |

停止不证明数学不可行；物理见证不等于完整grid/CFE履约。给定合法零功率也必须通过同一网络选择流程。
原始请求、CFE短缺、债务和失败风险分母均不由本模块创建或修改。
额外CFE削减可触发down-ramp违约，恢复可增加网络需求；两者都按实际固定功率验收，不能假定更低负荷更可行。

## 验证与后续

初批38项中36项通过，两个失败来自测试helper误用`hour`而非`t`参数；已修复。
随后增加首小时policy绑定、末级UID失败、exact功率记录、确定性重放和依赖闭包测试，46项针对性通过（36.65s）。
五文件220项相关回归通过（140.85s），独立pre-seal当前46项通过（38.99s），限定范围无开放实质finding。
相关回归使用同一pytest命令，文件为本测试及reference_selector、reference_grid、current_grid_step、
current_grid_short_solve的`test_rq2_*_v1.py`。`git diff --check`通过；旧四个模块源码哈希保持。
手算两机例：plan/prior各10 MW、总实际功率100 MW、每台下界10，上界及ramp100；
L1最小80，按UID先选G1=10，继而G2=90。输入数组逆序应得到同一结果。
非单调例：prior25、ramp10、external0，固定20可行，固定10在当前约束下无已验收后继；不输出不可行证书。
fault injection包含物理门内5e-7的L1/UID漂移，严格lock应拒绝，最后级失败不能发布部分选择。

测试命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_actual_dispatch_selector_v1.py`。
真实微型LP使用1秒/1线程；未执行正式计算、发布seal/receipt或修改旧冻结产物。
当前开发SHA256（非production seal）：

- source：`57953126a88f7516b328f23f6e3e72e4660a771fc2fac9d5e170a0a3a2071957`
- test：`34edc5def0ef87d7a7ad0e63d2e12005a7834e6060535e20e8b12543bf0187bc`

下一项为共同请求exact MW单位适配和业务/网络双提交；该模块不替代来源发布、训练容量绑定、
完整恢复/right-censoring、正式科学协议、正式规模或执行门验收。


## 2026-09-20 四臂连续小时协调开发

`episode_coordinator.py`已连接单对象内存中的四臂共同请求链、固定策略、公平物理/业务初态、整窗最坏预算预检和逐小时预留。
保留各臂独立停止；末小时保留恢复债务，窗口消费完不代表完整履约。完整小时输入、候选、外层提交、已开始/未完成/未开始臂分别记录。
`hourly_transaction.py`同步区分dispatch执行异常与求解前网络输入拒绝，缺失执行结果不猜零调用。
独立pre-seal 31项episode（44.69s）及23项hourly（32.10s）通过，findings闭合；九文件323项相关回归通过（170.08s，exit 0）。
完整合同、开发hash和命令见`docs/model_spec/rq2_episode_coordinator_v1.md`；旧22/291项记录保留为此前版本证据。
下一项为完整episode证据的持久化及无solver重放，再处理跨进程唯一性/恢复；现有业务prefix不能替代reference→mapping→business→actual全链。
本组件仍为DRAFT_NONAUTHORITATIVE。完整连续输入、训练容量与四臂策略绑定、正式规模、恢复/right-censoring及科学/正式运行门未关闭。
所有初态与未识别业务参数保持机制声明；没有新增真实运行观测、正式结果、容量/安全认证或formal-run authority。
