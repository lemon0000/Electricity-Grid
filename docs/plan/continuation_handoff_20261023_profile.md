# C保存P1性能剖析交接

2026-10-23。目标“推进计划”仍active，RTS-24公共主比较和两母线机制回归方向保持。原P1一次native授权已执行并使用；接续[P1交接](continuation_handoff_20261023_p1.md)。本次完成一次保存输入的无求解器性能诊断，未启动新native、P2、D/E或长实验。

## 当前证据

- [合同](staged_deliverability_c_saved_profile_contract_v1.md)、[源码](../../experiments/staged_rts24_saved_profile_v1.py)、[报告](../../results/tables/staged_rts24_saved_profile_v1_non_authoritative/validation_report.md)与[prelaunch](../../results/tables/staged_rts24_saved_profile_v1_non_authoritative/development_checks_01/prelaunch_01.json)固定本次执行。
- 唯一 `profile_01` exit0，命令wall27.732813s、Job27.218s，采样tree RSS155959296B。2/2历史成员HANDLE均signaled、active0、final PIDs空；worker10文件220061B，最终12文件222867B。
- 两份受仪器扰动的组件profile：一次fingerprints1.2055117s、一次完整reopen21.4340412s；另有一次指纹书挡。原683个P1文件2950863B及完整科学metrics相同；受观察的native/构模/numeric compile/科学CAS与publication计数为0。
- 最终21项不同普通检查通过，五项PRE_SEAL发现闭合。保存后核验没有新journal replay或solver；原P1只读postcheck输出与原 `postcheck_03.stdout.json` 完全相同，B1–B3及685旧路径保持。

原P1科学结果仍missing_input、coveragefalse、method/full replay双null；h1为CFE延期20MW_c且h2恢复，actual g均0。profile不补齐缺失h3..7，也不改变原冻结输入、注册或结果。

## 下一工作

实际热点已定位：fingerprints中3次Distribution.files引出4068次Path.exists，最终仅37项distribution文件入选；reopen中重复plain/asdict/digest占据较大inclusive成本，时间相互重叠。完整DAG与结构计数沿[预算对账](staged_deliverability_c_workflow_budget_reconciliation_v1.md)，不能用组件秒数线性外推P2。

RECORD先选后exists候选已被领域反例搁置：未选普通路径也可能抛PermissionError；省略该检查会改变旧失败行为。下一步仅做独立、未接线的严格域plain helper与等价普通测试：精确已注册dataclass、内置JSON类型/Fraction，未知/子类/非str键/深度或循环整根回退旧函数，证明canonical bytes/SHA与失败边界。asdict的复制与直接遍历等价依赖调用期间对象静止和标准库未被修改，不得外推并发突变。生产接线属于另一个R3后继，旧probe/journal/注册/config/P1/B1–B3字节保留。

C整体资源审查、昂贵失败、长前缀、完整139/F-X时序及D/E资源仍OPEN；业务快慢/设备与工程数值、D和排序平局/敏感性/时域、留出来源/split/seed/reveal尚未定义。不得补造数值或重复空框架。新的native仍需具体包、次数、预算和专项授权；无求解器有界开发按agent第9节固定自身范围和停止帽。

恢复时读AGENTS、agent第7–9节、本页、当前C计划与blocker，刷新Git/进程。root为唯一writer，只读审查不分叉。保持原运行数据与本次profile/source/contract精确绑定；`profile_01`不重用、不覆盖、不恢复。Git同步以远端读回和最终worktree为准。
