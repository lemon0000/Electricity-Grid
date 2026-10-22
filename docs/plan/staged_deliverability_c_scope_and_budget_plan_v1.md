# C：阶段评价范围与整链成本审查计划

2026-10-23最新开发检查点：以[保存证据交接](continuation_handoff_20261023_journal.md)的journal_v2继续。v1三方法五小时/3 fresh的一次测量保留（500/1324、outer75.1158s、531核心）；最终领域审查F14及v2草稿F15由完整CAS/root集合、链与最终依赖核验修复。新后继仅复用旧前两小时+1 fresh+3失败分支，37/121、outer27.9132s、采样tree RSS418926592B、138核心286322B，0旧full compiler/solver/native；见[新报告](../../results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/validation_report.md)。共382项不同普通检查通过；旧B1–B3/C/build/causal及v1绑定字节一致。公共RTS-24方向保留，公共数值点/g、139节点完整合同层、反事实F/X时序、长cohort/真实失败与IO/前缀增长仍待测，C整体性能和D/E点数/资源仍OPEN；native包须先登记并另获授权。以下段落保留各自时点含义。

2026-10-22，`DRAFT_NONAUTHORITATIVE`。接续[B3/C顺序](staged_deliverability_b3_c_next_steps_v1.md)、[B3规格](../model_spec/staged_termination_development_v1.md)及[有界诊断合同](staged_deliverability_b3_development_contract_v1.md)。本页安排C的交付，不登记或启动主实验，不改变旧实验权限。

同日新增[连续业务后继](continuation_handoff_20261022_causal.md)：child raw/min/max的数值最优性消费、三方法独立连续账本、actual零额外削减闭环和独立策略/余额审计已通过269项开发检查。证据限解析测试，公共normal/P0数值点与g仍未知；journal/关闭/fresh保存重放未实现。当前prefix重审和state摘要按Σt增长，需先做无损去重及完整新路径有界实测；C整链和D/E预算仍OPEN，不以测试wall准入。

同日C续作已形成[网络方向、完整DAG与结构预算审查](staged_deliverability_c_dag_and_cost_review_v1.md)。用户随后确认保留公共网络方向，RTS-24作为最小公共网络后继，两母线保持机制回归。B1–B3保存核验见[C交接](continuation_handoff_20261022_c.md)；新增输入表、请求/构模与独立点/KKT组件的一次有界检查见[RTS-24交接](continuation_handoff_20261022_rts24.md)。12离散模板生成1699请求描述、12actual预留槽，8模型构建，0求解器请求；公共连续策略、完整点、journal/reopen与整链实测仍未接通。已绑定DAG页保留原字节，当前选择与状态以本页及新交接为准。下面四步的整体完成条件不变，不能用构建时间关闭C。

## 四步交付

1. **固定D/E采用的范围。** 先确定最终采用合成两母线机制还是具名公共主网络，以及声明的正常/故障集合、已知计划退出与实际事件路径。当前小例保留为机制回归；若论文保留公共网络来源，应在选定的公共网络后继上测量，不能用两母线成本替代。网络推广与完整F/X任务时序背书分别审查。
2. **形成一张完整DAG及计数表。** 覆盖输入、正常完整C、各故障F及合法X、实际点、三种评价、任务批次访问、独立审计、journal、关闭/重开重放、终态与报告；包括固定成功路径和代表性失败路径。小时数、批次数、故障数、计划/资源组合数及重开长度均进入总调用量。
3. **形成可复用成本表。** 只有网络、记录形状、策略、环境和规模在原证据内才引用B2/B3实测；区分结构调用数、事前预计和实际wall/RSS/bytes。完整state摘要的O(T²)编码、ledger增长、每次L小时前缀重放单列，不由10小时线性外推。复用的源、输入、依赖及环境指纹必须一致。
4. **仅对缺口登记一次代表性测量，再形成准入页。** 固定代码/输入、点数、并发、wall/RAM/存储上限、心跳及失败保留；完成后才给D/E有限点数、总预算与未知项。超出测量范围则重审；准入页不授予正式运行权限。

## 结果仍按四层保存

| 层 | 当前证据与后续要求 |
|---|---|
| 给定实际轨迹 | B2/B3可表示固定策略在已接受小时内的响应、实际P、CFE、任务恢复和期限；拒绝、未决、右删失及未接受输入单列 |
| 完整F/X网络条件 | 正常完整C及声明事故F/X按网络合同核验；不同工程状态重新计算，安全枚举不当成实际同时发生的事故 |
| 一小时业务必要条件 | 当前post故障调用0.4 MW与登记X0.5 MW均超过aD0.25 MW，失败反例原样保留；未被排除不等于完整背书 |
| 完整时序合同背书 | 若D/E要主张完整合同交付，须新增反事实任务/事件序列、恢复资源与期限的定义及验证；仅实际轨迹成功时，合同结论仍保持相应failed/unresolved |

## B3可复用与待测成本

B3的三例parent/fresh-child及四个same-process reopen探针，只支持同一2-bus、最多10小时、同一持久化结构的组件诊断。实际完成状态、计数、阶段wall、采样RSS、文件bytes和source pins，以保存的report/completion及运行后说明为准。599点计算、重复重放和745点审核不作为独立样本数。

一般网状网络的矩阵/多源/故障枚举、SCED/AC/native、长时域与更多cohort、完整F/X时序新增路径均需后继测量。close/readback注入覆盖真实write/flush/fsync后的声明异常；真实阻塞I/O、坏盘/掉电、kill及失败报告写入失败不能由其代表。当前C整体性能审查与D/E主实验规模仍OPEN。

实现与写作继续同步：B3证据可进入方法章的连续账本与终结说明；D/E结论形成后再写容量、方案差异和贡献。来源缺口见[blocker register](../model_spec/blocker_register.md)，不能由机制例升级为场址容量、工程认证或经验概率。
