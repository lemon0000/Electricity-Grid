# C：P2机械包检查与收尾预算交接

2026-10-23，DRAFT_NONAUTHORITATIVE。目标“推进计划”保持active；接续[前次交接](continuation_handoff_20261023_p2_failure_outer.md)。起始HEAD/origin为2d6671be60890bb8791eb78b96bc664139842ce0；本次实际发布状态以提交后的remote readback/worktree核验为准。

## 本轮已完成

按[开发合同](staged_deliverability_c_p2_package_check_contract_v1.md)新增纯读取包检查器，不改原P2七输入、guard v2、旧父观察组件、codec/journal、三packet或历史工件。它持有context/SHA、原注册/55＋7＋6来源/exe、预期argv/cwd/root及parent直接process/startup记录，在完整quiet后核两遍完整库存和输入书挡。成功/数值诊断/known-rejection/失败库存/禁止读取分开；319点、138行、10接受state及query/parent/state/CAS/journal/prefix/head/events/fresh和内部Job/residual逐项核元数据。

129个不同普通测试在同一三个来源pins下通过：units_16为80项，17为真实完整包1项，18为真实late319 numeric1项，19为全入口旧编码oracle1项，20为reader/编码/P1根46项；collection_01证明互斥且无遗漏。related_02原observer＋guard72项通过。完整包wrapper41.0236306s，late319为49.4199823s；属于普通合成fixture，不能外推native或P2资源。

库存reader保留全祖先/ordinary/fstat/path/长度书挡，仅请求已观测size＋1并绑定metadata identity。摘要只在本次调用局部memo规范展开长度，8MiB内用原规范C encoder bytes/SHA，不减少digest。P1全部403个wire根/9790308B与合成319协议7582个实际digest入口/81683242B分别逐字节等于旧iterencode；两者不是科学重放或物理I/O。详见[报告](../../results/tables/staged_rts24_p2_package_check_v1_non_authoritative/validation_report.md)与[调用量/收尾预算](staged_deliverability_c_p2_package_check_cost_review_v1.md)。

早期fixture错误、120s超时、对话中断、oracle缺参数及raw/pins反例错误全部保留。units_04 Windows访问异常3221225477原因未确定，不声称修复。最终通过只统计上述五组；PRE_SEAL只读审查无剩余High/Medium，不构成official verdict/receipt/seal。标准库后核复现原P1及前轮postcheck stdout原字节，440旧发布路径与P1/B1–B3/685保持；三导航仅前置新检查点，旧正文保留。

## 下一实质步骤

先解决版本化的父端收尾记录预算及guard最终会计。原P1保存outer66、已知32个内部Job共64，两组residual为outer owner和另一个未归因identity。若P2仍有两个residual且319 point＋1 fresh各两个成员，条件历史成员642；18位FILETIME的member数组至少31459B，比固定16384B reserve多15075B，其他字段尚未计入。保留原P1外围字段、五位PID的静态例34658B；reserve不是长度上限，不表示真实P2必然超限。不要把第二residual称bootstrap/helper或据此证明父子边，不原地改guard v2。

后继应先写parent记录预算/成员上界、失败和terminal保存规则，再按agent第7–9节在新版本开发及有界验证。实际outer的启动事实/来源闭包/quiet后持久化与受控独立科学采用仍未实现；本模块没有CLI、spawn、注册或生产发布接口。新完整outer必须绑定独立新来源，不向原kernel闭合注册加键。

随后补raw→snapshot/KKT/point/合法X与journal政策/余额的fresh科学重放、昂贵失败、十小时CAS/摘要增长、父端采用成本及完整wall/RAM/storage。fresh60s＋最多5s收束对65s无进展帽仍无父端余量，不能沿用本轮普通测试wall当预算。实际argv、完整runtime、进程亲缘及科学采用/独立139/F-X/resource/formal均保持未验证或false。

原P1只覆盖五个模拟小时、31 native点和4代表行，missing_input/coveragefalse/双null保持，唯一native授权已用。无公共`p2_01`、registration或新native/长实验；新native须具体包及专项授权。RTS-24公共主比较/两母线机制与D/E原范围不变，现实输入、方案/选择/敏感性/冻结后留出及总预算OPEN，C整体未完成。

## 恢复入口

读AGENTS、agent第7–9节、本页、C计划和blocker，刷新Git/活动进程，再核`postcheck_01/ordinary_check_summary.json`、`saved_01.stdout.json`及440路径库存。root唯一writer，子代理只读不分叉。保持原失败与绑定，按精确NUL范围/原字节提交并读取远端hash；工作区不得遗漏active snapshot或无关改动。下一轮从收尾预算与实际outer开始，不重跑旧native或完整长链。
