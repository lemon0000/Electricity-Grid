# C：saved supervisor 事前调用与容量审查

2026-10-25，DRAFT_NONAUTHORITATIVE。按[设计/只读合同](../../../docs/plan/staged_deliverability_c_saved_fresh_supervisor_scope_budget_v1.md)完成静态依赖census、条件调用/截止账本和独立字节oracle；canonical三源码/SF49、原scope-budget/guard/outer及P1均未改。原161普通节点仍归属同一source epoch，没有新pytest、科学replay、solver或saved actor。

关键发现：有独立host expected image和broker make_context时，hold内部capture也计入，成功full inventory共10次，P1条件读12736；host末次full bookend后13419，超原12500。当前helper展开33个full context checks并至少计adapter自身loaded复读，source/exe/anchor条件下界6513，超原6500；其他loaded/catalog/fixture/新supervisor费用未计，完整调用量尚未闭合。原E base直接可追溯到保存chain_04的io，未复跑科学链。

时间向量至少185s，大于180s；R_b2/R_h3的earlier-deadline proposal已传播到fresh，parent active110、fresh close90/active80。original caps只是局部fail-stop上限，不保证同时可用；fresh同一50s episode含后续inner records，当前实现尚缺该handoff。host尾部I/O硬中断与失败可交付性仍OPEN，原failure15s不能额外续期。

wire oracle证明旧cap不能仅靠“component≤128KiB”合成：单component raw131435、两component263034超过旧131072。新10-slot proposal共2,392,504B，区分value/packet/physical并取消broker重复复制controller return；compacterror3864、primary+4cleanup19956符合proposal。证据限于component-cap与字符计数：BMP逐点65536、astral4代表，不是未来完整schema最大编码、四个合法科学record、OS allocation/RSS或真实运行证据。新guards未实现，所有admission仍false。

oracle_03因误把_role_compare的parse记为_role_context而被AST断言拒绝，oracle_04因独立计数器漏DEL127 escape失败；两次原script/source snapshot、stdout/stderr和exit保留。修正后oracle_05终态通过；只读PRE_SEAL指出fresh截止与failure transport/进程边界，v2 ledger/matrix经oracle_07终态通过。旧v1 JSON原样保存，未用部分输出冒充整轮通过。累计静态检查帽90s、单次≤15s，实际累计以exit.json的capture_seconds（含source书挡/snapshot/子检查）核算；所有attempt均计入。

P1全683和前序研究/失败包逐字保持，实际OUTPUT及父目录不存在。当前只关闭本设计/算术scope的pre-seal findings，不生成manifest/lease/official verdict/seal或运行授权。下一步是validation reuse的依赖与失效证明及whole-path计数，随后saved wire/issuer/driver实现；不是直接启动F。完整319/139/F-X、C/D/E现实输入、65s余量、资源/正式与科学采用仍OPEN/false，没有新增模拟小时。

入口：[saved_checks.py](checks_01/saved_checks.py)，[条件调用账本](checks_01/workflow_ledger.json)、[deadline v2](checks_01/deadline_ledger_v2.json)、[failure v2](checks_01/failure_availability_v2.json)、[wire oracle](checks_01/wire_capacity_oracle.json)及[当前交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_supervisor_budget.md)。
