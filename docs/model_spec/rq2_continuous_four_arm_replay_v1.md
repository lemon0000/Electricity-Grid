# 连续四臂物理动作与债务明细账绑定 v1

状态：`DRAFT_NONAUTHORITATIVE`。本轮接续cohort账，开发显式合成动作的四臂回放适配层。
实现、配置、测试分别为`four_arm_replay.py`、`configs/rq2_continuous_four_arm_replay_v1.DRAFT.yaml`和
`tests/test_rq2_continuous_four_arm_replay_v1.py`。旧boundary、multiday、debt_cohorts及冻结协议/结果原字节保留。

## 四臂口径

所有臂消费同一个`ContinuationHour`来源容器；该容器固定使用`joint_correct_shared/shared`作为公共输入标记，
实际实验arm与mode另行绑定在`ArmCursor`。下层复用joint物理状态机，通过显式投影请求实现各臂；
下层内部arm名不能单独解释为实验臂。每个track携带物理cursor、完整cohort账，轨迹身份digest同时绑定
外层arm/mode/track、split、双侧trajectory/provenance、source-hour偏移、固定envelope和period。
双侧时钟各自递增，偏移不表示共同真实物理时钟。24小时边界不重置任何状态。

| arm/mode | 调用 | 恢复约束 | 状态 |
|---|---|---|---|
| network-only/physical_execution | grid | business headroom及maximum power | 一套共享状态 |
| CFE-only/physical_execution | CFE | business、CFE-compatible surplus及maximum power | 一套共享状态 |
| joint-correct/physical_execution | grid+CFE | 同上 | 一套共享状态 |
| B6/separate_planning | grid与CFE分别处理 | grid仅business；CFE同时受surplus限制 | 两套独立状态与cohort账 |
| B6/physical_execution | grid+CFE | 共享business/surplus/maximum power | 一套共享状态与cohort账 |

这里的separate_planning指**给定规划动作的包络回放**，不运行优化、不生成最低柔性或最优性证书。
network-only不履行CFE目标，因此不额外要求其恢复满足CFE surplus；输入字段保留，投影时明确不施加该限制。
CFE与joint恢复都必须满足同小时surplus。所有调用是完整显式请求，不先裁剪到可用柔性。

## 物理—业务绑定

每步先用既有物理回放器检查服务平衡、共享调用上限、事件/duration/rest/energy/debt和恢复功率；
再要求精确`sum(cohort allocations) == eta * effective_recovery`，每步dt固定为1小时。
effective调用与恢复沿用旧v1的float容差判断；通过判断后，grid/CFE分别以`Fraction(str(value))`转为十进制有理数再相加。
不能先float求和后转Fraction，否则`0.1+0.2`会凭空产生`4e-17`债务并误记逾期。恢复输入也按十进制有理数处理。
效率作为固定envelope参数转为Fraction，仅乘一次。cohort账不再截断微量余额。
物理float债务与精确明细账每步绝对差超过`1e-12`则拒绝；该值为新适配器一致性检查，不放宽任何旧正式容差。
进入下一步前同时核对身份、source hour、period、累计incurred与energy、余额与debt，拒绝串账。

失败时不返回更新后的cursor，原输入均不可变；该小时不被接受，不冒充观察到的完整可行轨迹。
逾期属于已观察业务状态，继续留账；物理动作不合法则抛错，不解释为数学不可行或工程安全结论。
恢复分配由调用者给出，不选择EDF/FIFO，不证明生成这些动作的策略满足非预见性。

## B6固定规划动作的共享执行

`execute_b6_planned_step`接受成功的分离规划step，合并其两轨恢复与同出生小时的allocations，
在共享物理限制下重新校验。调用者必须提供与规划恢复量及导出的物理功率完全一致的共享action；
两轨effective恢复先按十进制有理数相加再转共享float动作，不把各轨已忽略的微量恢复重新放大为物理恢复。
不能趁执行时更换恢复量。完整envelope要求与planning一致；逐时共享call/headroom上限显式给定。
首次执行必须与零历史规划起点一致，后续step的planning前态必须等于已消费planning末态，不能拼接别的规划历史。
执行入口还会从planning前态、来源小时、deadline和动作重新回放并逐项比较完整step，
不能篡改actions后继续使用另一组动作的成功末态。arm/mode/track inventory固定且唯一，空轨道不能跳过服务检查。
分离轨道可以各自成功而共享调用、恢复头寸或事件包络失败；不预设B6与correct可行域嵌套或偏差符号。

同出生小时的grid/CFE在本草案共用一个deadline，才能合并为一个cohort。
异质deadline的逐服务cohort未实现；真实deadline仍unknown，给定deadline只标记为mechanism_assumption。
near-tolerance情况下分离/共享effective转换可能不同，一致性不成立会拒绝，不自动改allocations以获得成功。

## 初始状态、范围与证据

本适配器仅支持明确传入`zero_carry_in_assumption=True`的合成零历史初始化；
非零真实carry-in尚未适配，拒绝静默清零。初始化后所有事件与债务跨chunk完整携带。
手工重建开发对象不属于受验证的continuation，不提供production防篡改、checkpoint、lease或solver能力。
48小时fixture沿用公开标为机制假设的小数参数，23/24/25调用，26/27/28恢复；
单服务每小时调用0.125，共享联合每小时0.25。deadline取调用小时+3仅用于手算验证。

此处的physical检查仅指数据中心归一化服务功率与业务包络；没有求解电网dispatch、DC/AC或N-1。
没有注册正式split/coupling、真实deadline/业务参数和raw>1映射，不连接公开数据为正式模型输入。
全部formal/result/claim/security门保持false；未清理仓库、下载或启动正式实验。

下一步是固定因果策略的逐小时决策与违规记录接口；四臂优化、正式机制参数注册及正式执行仍需各自的数据和验收门。

## 开发验证记录

使用`D:/Miniconda3/envs/compute/python.exe -B`。编辑前核对git状态、执行计划/blocker及既有模块与协议，
python/gurobi/highs进程筛选未发现相关活跃正式运行。新增4个文件（本说明、YAML、实现、测试），另向plan/blocker追加开发状态。
没有新solver调用、下载、查询、正式实验或仓库清理。

相关回归命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

中间相关回归`149 passed in 28.43s`。后续补充十进制舍入、B6规划记录重放、cursor inventory与history类型测试，
修正后的完整相关回归为**`156 passed in 32.97s`**，对应字节如下。
已核上轮multiday/cohort的config/code/test共6个绑定及sealed v5 inner/5个成员均保持原字节；`git diff --check`通过。
旧v5 symlink环境限制本轮未重跑，未记为通过。

只读独立pre-seal审查发现B6伪造planning动作仍可沿用旧末态，以及空轨道可以跳过服务检查；
已分别通过完整规划step重放对照和规范cursor结构检查修复，并增加对应回归。
该审查只适用于DRAFT开发，不是official review verdict或运行授权。
最终只读复核确认两项finding均闭合，无新增开放finding；reviewer使用指定解释器独立运行同一5文件矩阵，
得到`156 passed in 27.44s`，并核验下列hash及旧multiday/cohort六文件绑定均匹配。

| 文件 | SHA-256（开发标识，非seal） |
|---|---|
| configs/rq2_continuous_four_arm_replay_v1.DRAFT.yaml | `0ddd3ff9f2c75c37dee7513e96c6001bff210091f9684a1aca7e6c504a7ddb28` |
| src/rq2_joint_deliverability_boundary_v1/four_arm_replay.py | `39613c017ac1b6a96d12b9f5b760d1b457b3100e1355a6590b7702a85741ae4d` |
| tests/test_rq2_continuous_four_arm_replay_v1.py | `43ddd422c3179eac813bcf60333ee4cc8df2b3625a3486110f78d0401add6824` |
