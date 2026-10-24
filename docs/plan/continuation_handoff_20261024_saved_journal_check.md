# C：raw actual 前缀连接 trusted journal 交接

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[四代表行交接](continuation_handoff_20261024_saved_contract_replay.md)。起始HEAD/origin为`9c872d000d0f9bbd066e462786376acb6748a54b`；最终发布hash以提交后远端读回为准。

按[合同](staged_deliverability_c_saved_journal_check_contract_v1.md)完成[DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)局部E的普通只读集成测试，无新src功能或原实现变化。原P1五模拟小时/21个raw点经原B/C重建，再由原journal_v2.reopen重建genesis、五hour和一个terminal、130 CAS。21个重开PointEvidence typed SHA/query SHA与原C输出相同，最终state digest/typed根相同；typed根29517379c102b40b0f0a0b77711db4d936357025e4f53283f5bdec04fcbc7a41。原missing_input/committed/known、coveragefalse/双null、accepted5/last2/余额0、resumefalse以及无pending/unaccepted/failure保持。

16新＋24原journal回归通过，共40唯一nodeid。可信绑定九字段直接反例及六个共同caller书挡反例覆盖failure/closed、外部锚、完整pins map、fixture和source期望；外部锚末次raw/文件及祖先identity与冻结image复核。45 source/runtime入口核对、完整683文件/metadata/root书挡通过。构模42/import21、audit33/历史row85、typed pack155（B105/E27/join23）、source2080/P1内容4319/外部锚末读1已计数。chain/反例wall约29.20/32.51s，24相关项按collection顺序拆互斥12＋12，wall约45.06/32.21s，仍各90s，不作资源准入。首轮漏计13次规范化pack失败与近帽相关成功日志均保留，详见[报告](../../results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/validation_report.md)和checks_01。

836旧路径、三导航旧正文、前轮stdout、P1全部683文件保持。原七输入/packet/B1–B3/guard/outer/B/C/D/journal/numeric/codec未变；1024历史identity（含owner）、两份各128KiB收尾合同仍适用。独立只读PRE_SEAL不产生official verdict/receipt/seal。没有新native/P2/长实验；真实保存重开没有writer，原相关回归的writer仅在pytest tmp。

下一步F先设计具体保存P1范围的fresh/父采用DAG、source/executable/argv/owner和完整库存书挡、成功与失败发布、总预算/安全停止，再决定最小有界实现。原fresh.json仅是历史输入，不能替代当前新增fresh process验证；本轮同一pytest进程内原B与reopen一致也不能替代F。F即使在保存P1范围接通，仍不证明未生成的P2全319/完整139/F-X、full runtime或资源准入。原P2七输入和已发布source必须保持，successor路径和原guard3/outer合同照旧。

全P2 journal_replayed、scientific_evidence_adopted、expected provenance、139/F-X、resource/formal仍false；仅saved_P1_journal_reopened=true。昂贵失败/十小时增长/full wall/RAM/storage、65s父端余量、C整体/D/E现实输入、方案比较/选择/敏感性/冻结后留出均OPEN。不得补未观测小时、改变原政策/rights/容差或从开发检查推导新native权限。

恢复读本页/合同/DAG与C计划/blocker，刷新Git/进程，并运行本证据目录checks_01/saved_checks.py。root唯一writer；R3按agent.md §7独立只读PRE_SEAL，不分叉；继续零新native/不开长实验。
