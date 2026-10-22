# C公共数值接口与保存成本交接

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。接续[journal_v2交接](continuation_handoff_20261023_journal.md)，公共RTS-24方向和B1–B3绑定不变。本检查点没有运行solver/native、长实验或新的科学轨迹，目标“推进计划”继续active。

## 已完成

- [纯数值接口](../../src/staged_rts24_numeric_interface_v1.py)使用原Pyomo构模、固定变量/退出flow消元、规范化平衡方向、min目标与对角Hessian数组；导入完整snapshot后核问题canonical SHA、活动/目标echo、全free列reduced cost，再经原经济/child/primal独立audit产生既有PointEvidence类型。[验收合同](staged_deliverability_c_numeric_interface_contract_v1.md)固定schema、HiGHS dual约定、目标echo独立门及primal-only payload。
- 独立PRE_SEAL发现自由angle raw rc遗漏和actual dual-valid/payload不一致，均已修复。全列rc检查又暴露Pyomo在无机组母线可能反向表示constant==expression：现按原始代数规范化G-Pd-Pnet-out+in并保存±1 map，不按解翻转符号。已有独立解析点、shift/tap、固定/退出机组和max端点验证。没有official verdict、receipt或seal。
- 新66项普通检查及158项相关旧检查合计224 passed/30.91s。过程曾有7个正例在增加rc检查后失败，原因是上述row方向；修复后最终范围通过，未放宽容差。旧v1/v2只读postcheck均exit0，531/138核心与源、B1–B3原字节保持。
- [静态保存核算](staged_deliverability_c_retained_cost_review_v1.md)只读677输入、成功逻辑读取1354次，验证旧531/558007B与新138/286322B；见[机器报告](../../results/tables/staged_rts24_saved_cost_v1_non_authoritative/audit_01/report.json)。无模型/策略/replay或数值点生成。

## 成本补正

成功v2保存的CAS keys为3→27→56→57，CAS bytes为4989→23789→47671→49467；root最终17504B。两个hour的state根2350/3662B。两hour+terminal的特定CAS inventory分量879514B，root inventory/_check额外读取分量273966B；不含create/fresh、publish/get/readback、runtime、其他case与报告，不能与旧总read counter当成同一口径。

累计key列表和历史state物化字节可能二次，writer反复全量inventory的累计读/解析可能三次。科学audit逐row摘要prior，在外层反复前缀重放时也可能三次；单次digest只是当前S_t。新成本页明确补正旧O(T²)笼统措辞，旧绑定规格未改。下一保存优化应在独立successor合并同append重复pack/inventory，再考虑增量key/持久record前缀，必须保持删除检测、完整闭包、unknown及fresh等价。

## 下一可执行开发

[公共数值包计划](staged_deliverability_c_public_numeric_package_plan_v1.md)固定了完整DAG和分层调用上限：P1为五小时实际前缀加工程前后支路/机组代表，31；P2为十小时实际轨迹加两帧139完整合同，319；单方法十小时完整1431、三方法4273。都是事前上限，无一次native执行；P1仅代表校准，不能替代公共主比较。

接下来实现highspy数组/状态/完整dual适配及受控native runner/watchdog，先做无solver fake-backend/失败路径普通测试、固定真实输入/版本/资源/失败保留并独立审查。当前没有这个可启动包，也没有专项native授权；不启动、不用兼容性假设代替校准。可并行推进保存成本后继。公共数值/g、完整139、F/X反事实时序、C整链及D/E资源仍OPEN。

新对话读本页、AGENTS.md、agent.md第7–9节、C计划和blocker，刷新Git/进程；复用旧probe，不重跑attempt。当前新增source/合同及核算输出按本检查点保存；后续字节修改先核所绑定证据并使用后继。最终提交号以远端读回为准。
