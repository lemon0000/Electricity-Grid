# B2诊断调用次数的运行后澄清

2026-10-22，`DRAFT_NONAUTHORITATIVE`。适用于[B2执行合同v1](staged_deliverability_b2_development_contract_v1.md)及[attempt_01开发报告](../../results/tables/staged_deliverability_b2_v1_non_authoritative/attempt_01/validation_report.md)。

合同v1第1节“成功fixture中审核362个已保存唯一点”中的“唯一点”为措辞错误。正确含义是362次PYPOWER点求值和对应保存点审计：三例父连续参考分别70、70、41次，共181次；三个fresh子进程重放/后缀再做181次。父/子完整state及audit相同，重放属于重复验证；不同小时或路径也可有相同负荷/拓扑。因此这些次数不代表362个独立数值样本或362个不同运行点。

`counts.pypower_flows`和`counts.audited_pypower_points`均按调用/点审计次数解释。正常scenario引用同小时已核normal点时不另计调用；这一合法复用与跨进程重放重复不是同一概念。52个网络小时尝试、50个业务步骤、6次业务装载及3个子进程的DAG计数保持不变。

原合同v1已被attempt的起止SHA绑定，保留原字节以便重验；本澄清与运行后报告/verification共同说明其实际含义，不改运行输入、实现、预算或已保存工件，不触发补跑，也不增加任何研究权限或科学结论。
