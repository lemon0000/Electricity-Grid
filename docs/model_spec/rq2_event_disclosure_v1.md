# 当前小时事故揭示机制

日期：2026-09-16。状态：DRAFT_NONAUTHORITATIVE。
实现`event_disclosure.py`；测试`test_rq2_event_disclosure_v1.py`。本组件不调用solver。

## 来源核对与必要性

`src/scenarios/rts_gmlc_n1_chronology.py::simulate_n_minus_one_events`生成derived benchmark事故。
其`event_id`包含seed，且普通事件和stationary-down事件的`end_hour_exclusive`均使用
`min(..., horizon_hours)`。因此event对象包含未来信息，截断末端也不能当作已观察修复。
`outage_trajectory._validate`通过`event_by_hour`展开完整事件表，适用于原offline合同，保持原实现。
normal candidate还含全时段source、seed及身份；本组件不接受该对象，也不因此宣称整条调度链已满足因果性。

## 显式机制合同

调用方必须提供完整且排序唯一的组件清单，以及三个无默认声明：

- `current_n1_outage_overlay_revealed_before_current_action`：当前N-1 outage overlay在当前动作前揭示；
- `complete_current_n1_outage_overlay__no_hidden_same_hour_replacement`：每小时完整报告最多一个N-1 down组件；
  同UID连续down表示同一事件，小时内隐藏repair/retrip不在这个机制范围；
- `mechanism_assumption`：当前报告、入站状态和repair cap都是机制输入，不是由本接口认证的真实观测。

组件标识只含kind/UID；当前报告只含source hour、当前N-1 down组件或明确无N-1故障，以及当小时返回发电机的限额。
无N-1故障不表示所有机组都物理可用：静态停用、计划commitment及其他边界仍由网络模型处理。
报告对象缺失与明确无N-1故障不同。来源小时必须严格连续；不消费future表、horizon、raw event ID或随机seed。
组件UID是静态网络标识，不能由调用方编码未来事件；本接口不是对恶意调用方任意字符串的保密沙箱。

## 状态递推

初始化显式给定incoming source hour和当时down组件。初态down只得到local ordinal=1和first_seen_hour，
`observed_start_hour=None`，不伪造trip或实际已停时间。其后新down状态首次出现时才记observed start。
ordinal仅随已揭示的新事件递增；不采用原seed/event序号或整段轨迹摘要作为策略可见身份。

同组件持续down：保留事件，禁止提前提供repair cap。
原generator从down变up：当前完整报告必须显式提供有限非负repair cap；原branch返回不接受generator cap。
当前可切换到另一个down组件：同边界结束旧事件、揭示新事件，离散采样时仍满足N-1；
这不证明小时内部的多事故时序或瞬时安全。该cap属于刚返回的旧generator，不属于新故障组件。
cap上界、发电/功率平衡与响应限额仍须由后续网络模型核验，本组件不提供调度可行性。

观察停止时active原样保留，不生成repair、零尾部或额外小时。
source gap、非法组件、缺repair信息或非法类型均抛错，输入不可变，状态不推进。
`DisclosureStep`保留before/current report/after以及started/ended，便于后续连接并核对。
状态及步骤记录禁止普通构造和dataclasses.replace，只由初始化/当前转换函数内部生成，避免调用方伪造可继续的历史。
这是同进程的确定性机制转换，不是签名或对Python反射/私有API调用的安全沙箱，也不是持久化验证器或真实报告来源证明；
未来跨进程/产物导入仍需完整前缀重放和来源审计。当前不提供state反序列化入口。

## 验收与下一项

验证实际转换的未来后缀扰动不影响已揭示前缀、改变当前报告会改变当前状态、分块和整段推进相等，
并覆盖stationary-down、末端不修复、同小时不同组件切换、缺报告/来源gap/非法repair限额与未来事件对象拒绝。
这些只证明揭示组件自身，不能替代未来request generator的前缀不变性测试。

36项新测试随63项相关回归通过（1.54s）；独立pre-seal的公开state伪造历史finding已修复并复核闭合。
独立复跑36项通过（1.50s），限定范围无开放实质finding；本记录不是official verdict或正式启动证据。
源码SHA256：`861da4ece3ef25a412ae5dbaefa56847333b0dcfd17bbb776c9c74669b49ea4b`；
测试SHA256：`3f7160fca326ec0c331e9177d49531c0e979613c21bed06d0428592d5f84170f`。
实际命令：

```text
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_event_disclosure_v1.py tests/test_rq2_continuous_grid_carry_v1.py tests/test_rts_gmlc_public_power_system_blocks.py::test_n1_competing_risk_chronology_is_reproducible_and_nonoverlapping tests/test_rts_gmlc_public_power_system_blocks.py::test_event_expansion_rejects_overlap
```

下一项继续核对正常计划的信息集及单步网络输入合同，显式规定请求含义、CFE credit、调度选择和失败处理；
尚未生成request、dispatch、训练容量证书或正式连续输入包。
未来若接offline事件表适配器，须在审计侧检查隐藏同UID边界替换并拒绝无法满足本信息合同的输入；
当前没有该适配器，不接受以截断end_hour推断repair。
