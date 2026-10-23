# P2机械包检查开发证据

2026-10-23，DRAFT_NONAUTHORITATIVE。承接[前次检查点](../../../docs/plan/continuation_handoff_20261023_p2_failure_outer.md)，遵循[开发合同](../../../docs/plan/staged_deliverability_c_p2_package_check_contract_v1.md)。原P2七输入、guard、codec/journal、prepared packet、P1/B1–B3及历史失败字节保持；没有公共P2注册、native或长实验。

## 实现与证据边界

新`staged_rts24_p2_package_check_v1`只读检查已持有context/SHA、parent直接process/startup记录、原注册/packet及55＋7＋6来源与exe、完整quiet之后的两遍worker库存及输入书挡。completion仅精确排除根目录六项，六项仍在父完整库存。完整协议核319点/138行/10个accepted-state引用、query/经济父点/accepted-state/prepared证据、wire CAS闭包与journal/head/prefix、ordered events、fresh/report、全部内部Job和outer residual集合。

五类机械状态分开：success、numeric、known-rejection terminal、failure inventory及禁止读取。unknown quiet不读worker；已知quiet的失败可保存稳定库存，不要求失败文件或report已写出。numeric根`numeric_failure.json`按闭合schema核验，嵌套同名和非numeric包不能借此豁免；actual numeric的未接受attempt及known rejection的committed/accepted计数分别处理。worker完整性声明单列为未验证；实际argv、进程亲缘、完整runtime、typed重建、科学重审/采用、独立139、F/X时序、resource/formal始终不由本层升级。

合成完整包使用真实类型结构及原codec保存占位点/KKT和`legal_X=false`，它不是有效网络数值见证。普通测试禁止Popen、科学构模/compiler、native、snapshot导入、独立audit及journal.reopen。完整规模检查保留真实文件系统两遍inventory和输入书挡；另一个全入口摘要oracle直接使用fixture snapshot，两条证据分开。

## 验证记录

普通测试按五个互斥组安排129项：80项剩余分支/反例、1项真实完整包、1项late319 numeric、1项全入口摘要oracle、46项reader/规范编码与P1 wire根核验。最终三个来源pins、终态与互斥收集核验见`postcheck_01`；尚未形成终态的记录不计通过。

P1全部403个保存wire根的新旧规范bytes相等，合计9790308B。合成319协议7582个实际digest入口/81683242B规范字节全部与独立旧iterencode一致，根类型NoneType/dict/list；没有减少digest调用。长度memo仅在单次调用内，不跨状态缓存。reader保留原ordinary/全祖先/两次fstat/关闭后path/精确长度条件，另与枚举identity绑定；0B、8MiB边界、短读、增长/截断、替换、目录漂移及link/reparse故障均有反例。

保留的早期记录：units_01为3 failed/11 passed/44 errors；units_02/03/05/06/08触及120s wrapper上限；units_05虽出现局部1 failed/1 passed文本，仍无wrapper终态通过。units_04栈诊断以Windows访问异常3221225477退出，原因未确定，不声称已修复该异常。stack_01/03分别50s/55s结束，stack_02路径别名断言失败。units_11在对话中断后失去handle，复查无活动Python、无终态pass；units_12的oracle调用缺numeric实参，units_15的log反例混用新raw/旧pins，均保留并修正测试。早期通过的窄组与中间完整组不重复累加。

全部读写身份书挡和CAS身份保留，仅本层的有界size＋1读取及已界定JSON的C encoder替换逐token编码。旧失败与后续成功运行条件不同，不作提速比或P2预算结论。普通测试的wrapper耗时、pytest耗时和未来P2资源时间分开。

## 成本与下一依赖

[调用量及预算审查](../../../docs/plan/staged_deliverability_c_p2_package_check_cost_review_v1.md)明确每次输入76次read、首尾152次，context准备另85次；两遍库存为2N内容读取/4N fstat，全部祖先核验保留。普通完整fixture的5837文件观测不能替代未来公共P2存储/收尾预算。

独立保存P1复算为outer66、32内部Job共64、两个residual；第二成员不归因。条件投影642成员时，18位FILETIME的member数组至少31459B，超过原16KiB reserve 15075B；同P1外围字段、五位PID的静态记录例34658B。reserve不是终态长度上限，故这只反证边界余量尚无保证，不推断实际P2超限，不修改guard v2。

后继先版本化解决parent收尾记录预算并开发真正outer启动绑定，再接受控独立科学采用及失败持久化。十小时真实raw/KKT/合法X/journal重放、昂贵失败、quiet后采用成本、65s无进展余量与完整wall/RAM/storage仍OPEN。C整体、139/F-X与D/E现实输入/有限方案/选择/敏感性/冻结后留出和总预算未完成；RTS-24公共方向与两母线机制保持。原P1一次native授权已使用，新native另需具体包和专项授权。
