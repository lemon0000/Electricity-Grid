# Journal v2：保留闭包与根链检查

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。[v1保存规格](staged_rts24_journal_development_v1.md)和其一次测量保留。最终sol_reviewer发现F14：v1仅扫描现存CAS，删除genesis fixture后writer仍可能采用新hour；fresh才拒绝。v2草稿复核又发现F15：若旧root条目在append期间消失，仅核新entry不够。这两个问题由独立后继修复，不回写v1绑定源码/合同/核心工件。

[journal_v2](../../src/staged_rts24_journal_v2.py)保持全部科学类型、prepare/propose/accept、点/KKT/LP和独立业务audit不变，只改变保存schema及完整性检查。schema显式为v2，runtime pins绑定本文件。没有把v1数据自动升级为v2 journal，也不新增resume权限。

Session保留精确CAS inventory和root inventory。genesis从Fixture/initial state的纯pack闭包推导全部CAS key，逐根typed读回，绑定`after_cas_keys`；genesis发布后核精确root、CAS、目录及runtime。每次操作前要求现存CAS/root精确匹配Session，根链还逐条校previous SHA，使伪造Session旧文件表不能遮盖已改条目。

append在任何写入前纯pack payload及candidate，计算预期CAS集合为旧全集并新增完整闭包。CAS写完、entry发布前核旧root没有变化；entry metadata绑定累计`after_cas_keys`。采用前要求CAS精确等于期望全集、root精确等于旧root加新entry、目录身份仍相同，最后核runtime。删除旧对象、旧条目、genesis或加入未知root均关闭并保留旧state；entry final可能已出现时仍为unknown，交只读reopen裁决。

trusted binding增加`known_cas_keys`。fresh从外部Fixture/初始state纯pack重新得到genesis集合，再逐条按payload/after-state重算累计集合，与entry和可信已知前缀逐字段比较；必须保留全部已知key。原有source/head/count/state/关闭/failure绑定和数值重放保留。缺CAS或根链不完整时拒绝，不用保存之外的对象补齐，不由未知恢复造任务。CAS orphan仅保留诊断口径。

这些是本地文件系统的前后观察，不是并发事务、执行lease或掉电耐久性保证。完整key列表、root SHA表及逐前缀扫描增加O(T²)元数据/读取工作；先闭合保留语义，后续增量优化另立合同。v1正例测量仍有效，但不能证明v2性能；v2只按[新短探针合同](../plan/staged_deliverability_c_journal_retention_probe_v2.md)复用旧前两小时证据测量。

普通测试覆盖三方法两步科学state/closure重放、删fixture/payload/state、准备及CAS/entry发布窗口删旧对象、删旧genesis/hour、加入root、伪造Session inventory及unknown确认。公共网络数值点、完整F/X时序、长cohort/真实失败、C/D/E资源/native/formal等门仍OPEN。
