# C连续业务后继开发验收合同

2026-10-22，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。按照agent.md第7/8/9节，在[公共构建检查点](continuation_handoff_20261022_rts24.md)后新增[证据驱动连续规格](../model_spec/staged_rts24_causal_development_v1.md)。本合同约束实现与普通测试，不登记新实验或更改运行权限。

## 交付与验收

| 交付 | 必须核实的行为 |
|---|---|
| child LP独立审计 | 原点审计与经济父KKT不变；支持raw/min/max；正确消元、box/connection/c≤meter、shift常数和负max目标；缺证据/可行非最优/非有限/错误身份拒绝；无rigorous bound声明 |
| 连续三方法 | 独立轨迹与账本、同外生输入；当前信息固定π；完整共享资源/期限/业务和X carry；简化方法假想安排与完整回放分开 |
| actual闭环 | 准备证据与真实P分别绑定；选动作之后才审核actual；精确请求P、零额外削减、同父完整点和KKT；失败不推进full实际接受前缀 |
| 身份与终态口径 | plan/clean/method/参数/时间边界全部绑定；上下文不能拼接，summary不能缩短窗口；永久逾期与右删失不混淆 |
| 独立业务audit | 不调用writer转移，独立重建cohort、策略、余额、点证据、deadline及carry；拒绝伪造状态和摘要 |
| 保留 | B1–B3 118保存/42仓库pin/7外部与旧版本，原C审查工具/测试/DAG及build_01绑定8源/8核心/追加读回字节一致；无关paper保留 |

只运行新的两份测试及适用旧回归，使用绑定compute解释器和-B、禁用pytest cache；所选RTS24旧测试限装载/缩放。测试/静态机械检查不调用solver。R3只读sol_reviewer进行PRE_SEAL审查，修复后重跑受影响检查；不生成official结果、receipt或seal。

本包只在pytest临时目录或内存中构造解析三母线证据，不能保存伪公共结果。公共fixture没有真实normal/P0经济父点时仍拒绝。测试材料及保存的检查记录明确为开发证据，不作为D/E比较、完整F/X或工程结论。

## 完整C仍待接通

新内核每步的prefix/parent/child重审以及完整state摘要随T增长，下一journal后继须先列输入→prepare→固定策略→actual→独立audit→write/flush/fsync/publish/readback→checkpoint/close→fresh保存重放→拒绝/未决/提交未知→终态/报告的实际DAG，并计算重复前缀与回调倍数。优先设计无损frame/父证据去重及同操作合法复用，不能以跳过身份或数值核对换速度。

新有界集成或性能probe需另固定代码、规模、次数、总call cap、wall/RAM/存储、心跳和失败保留；真实native包还须专项授权。当前普通测试不关闭C整链预算；公共工程变化、真实点证据、持久化/fresh进程、昂贵失败与D/E主比较仍未获得整链验收。
