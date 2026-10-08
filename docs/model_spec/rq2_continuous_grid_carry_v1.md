# 连续网侧机组状态审计草案 v1

日期：2026-09-16。`DRAFT_NONAUTHORITATIVE`；零solver，全部测试为mechanism_assumption。
实现：`src/rq2_joint_deliverability_boundary_v1/grid_carry.py`。
测试：`tests/test_rq2_continuous_grid_carry_v1.py`。

## 用途与边界

旧grid v4逐24小时free-boundary SCUC不能提供跨块机组状态保证。此独立小组件检查**给定的committable机组轨迹**，
为未来continuous-grid successor提供跨chunk验收oracle；不修改或调用旧runner，不选择新实验参数，也不生成数据包。
它不求解dispatch，不检查系统功率平衡、网络、reserve、availability、机组事故恢复、动态derating、AC或N-1。
可再生/fixed/curtailable机组不能未经新合同作为committable机组套用。本审计通过不是完整grid输入通过。

`GridIdentity`绑定split、trajectory、outage seed和调用者给定的source SHA256身份。
SHA字段只作轨迹标识；本接口不读取来源文件或验证其字节。未来loader/manifest负责真正来源验证。
`GridCarry`还绑定排序且唯一的机组UID、固定参数、上小时commitment/generation与各机组完整elapsed-state小时数。
初始历史角色必须显式为mechanism_assumption或derived_dispatch_witness；这里不把调用者声明当成历史真实可达性证明。
只有具备来源见证及其独立审核后，后者才能用于正式输入。

## 一小时状态递推

时间步长固定1小时；elapsed-state history为非负整数完整小时。支持小数源minimum-up/down，但先按旧SCUC规则向上取整。
若从状态u切换，必须在切换**之前**满足
`elapsed >= ceil(minimum_up if u else minimum_down)`；切换后age=1，否则age增加1。
因此跨午夜不能重置minimum-up/down，也不能用未来停留时间修复过去提前切换。
初始age=0代表显式给定、尚无完整停留小时的边界情景，不推断其在真实数据中出现。

使用旧normal-SCUC的startup/shutdown Pmax allowance：

```text
P_next - P_prev <= ramp_per_hour + Pmax * startup
P_prev - P_next <= ramp_per_hour + Pmax * shutdown
u_next * Pmin <= P_next <= u_next * Pmax
```

上下限与ramp按`1e-6 MW`绝对容差核验，与旧网侧容差一致；不clip原始功率。
minimum dwell按整数小时精确比较，不借用MW容差。此范围只沿用具名normal机组约束，
不将startup Pmax allowance解释为更精细的物理启动曲线或事故响应许可。

source hour必须是上一小时+1，split/trajectory/seed/source身份完全相同，单位集不变。
`advance_grid_carry`接收一个小时，无未来序列；`replay_grid_chunk`顺序重复同一函数，空chunk不推进时钟。
参数存于不可变cursor，不允许在continuation调用中传入新参数。调用者重建整个cursor属于新情景，
本接口不是防篡改checkpoint或production provenance链，不证明任意重建状态继承了前史。

失败抛ValueError，输入状态不变；表示该给定轨迹不满足本局部合同，不是原问题数学不可行。
没有输出formal/security/ready gate，不生成任何production manifest或review receipt。

## 解析验收与当前验证

合成G1：Pmin=10、Pmax=100、ramp=20 MW/h、minimum-up/down=3/2小时。
从hour23 on/P=30/age=1起，hour24/25仍on且P=50/30，age=2/3；hour26关机age=1，
hour27继续off age=2，hour28以P=70启动age=1。逐小时、整段与所有分块位置的结果必须相同。
初始on age=1立即关机、off age=1立即启动、跨chunk ramp超限、缺机组/身份漂移/跳时均拒绝。
另覆盖fractional minimum ceil、down-ramp、非有限数、布尔冒充数值、初始offline非零功率及参数不可变。

针对性命令：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_grid_carry_v1.py
```

首次结果：`25 passed in 0.09s`。主线程相关回归`116 passed in 34.53s`：

```text
python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_grid_carry_v1.py tests/test_chronological_dispatch.py tests/test_rts_gmlc_scuc.py::test_multiperiod_model_has_no_pointwise_commitment_symmetry tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py
```

该命令只构建模型/检查输入或运行合成回放，不运行solver。两新增Python文件Ruff通过，`git diff --check`通过。
从既有outer复核inner SHA与成员SHA：旧科学v5 5/5、implementation v2 14/14、execution v3 22/22匹配。
独立只读`sol_reviewer`完成non-authoritative pre-seal audit：targeted `25 passed in 0.08s`；
grid-carry与boundary相关回归`75 passed in 22.31s`。另用独立枚举oracle检查8,000个短commitment/history/minimum-time
组合、20,052次分块重放及156个功率/ramp边界组合，0 mismatch；无开放局部chronology实现finding。
独立相关命令为`python -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_grid_carry_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py`。
枚举oracle由PowerShell here-string传入`python -B -`，未落盘：以独立run-length算法判定切换资格，
并单独复算bounds与startup/shutdown ramp residual、覆盖容差内外边界；不是调用被测checker作为期望值。
审查明确保留来源SHA仅标识、初始历史仅声明、机组分类/availability/derating及网络约束未校验等范围缺口。
本次未签official verdict/receipt，不宣称formal-ready。

本轮开发字节（不是seal）：

| 文件 | SHA256 |
|---|---|
| grid_carry.py | `57d3c9b3dd27d5b47299591d4b027e1e0f106ae61965ac8ea69bcff62d7f2816` |
| test_rq2_continuous_grid_carry_v1.py | `b49f1a1affa491bb0b063254e6793e0456f7e28452b84d7dab18d36f473d48e3` |

后续仍须建立continuous dispatch生成器、全部机组与网络/事故约束、来源与初态证据及规模/solver证书；
本组件不能替代这些门，也不能用来批准旧逐日结果的直接拼接。
