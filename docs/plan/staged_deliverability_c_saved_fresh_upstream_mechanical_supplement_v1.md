# C：上游合同保存包的导航兼容性机械补充

2026-10-25，DRAFT_NONAUTHORITATIVE，补充[原范围预算](staged_deliverability_c_saved_fresh_upstream_contract_scope_budget_v1.md)，在第六次动作前固定。main execution freeze为31files/1,135,236B，不修改；原saved_checks.py、support、saved_05失败原记录全部保存。源49/4058历史路径/10域/59节点/21项设计结果不改，也无科学、资源或运行权限变化。

saved_05 exit1、charge4.3197211s，stderr指向前序direct-entry oracle的首行header检查。本轮把导航状态前置于标题之前，与旧archive的header+body合同不兼容；不是前序科学数据变化。五次累计18.0073466/90s，原定terminal_06尚未执行。本补充将原第六次目标具体替换为独立terminal_checks.py，并由terminal_capture.py保存，仍最多6次、target≤11s、capture charge≤12s、累计≤90s；不增加retry或reserve。若末次失败，保留终态，不在本预算内继续运行。

四导航修复为“原header → 本轮prefix → 原body”。小型document_migration.json保存prefix/header exact编码、前后pin和body suffix pin；可从修复后字节重构frozen document_checks中的修复前pin，并复核baseline原导航pin。未来archive允许在相同header之后前置新段落，但固定body suffix保留。交接/报告只前置修复说明，原冻结全文保留。原合同字节不变。本补充是第4个新文档，仍≤4files/1MiB。

terminal_checks.py保留原保存审计逻辑，只增加可逆文档迁移、对唯一saved_05失败的typed历史验证及新terminal helper binding。失败保持exit1/accepted=false且stdout空，stderr固定pin；不能算保存成功。当前结构必须仍由design_03的21项结果支持。原archive checker继续从exact保存SHA加载，核282冻结节点/8普通探针/P1全683；新checker独立检查此次迁移后的导航。新增helper及wrapper原bytes snapshot、migration manifest和末次原stdout/stderr/exit位于原mechanical目录，总≤16files/1MiB，不写checks_01。

末次wrapper在pre/post source/history/新helper/migration pin窗口计时，0.25s未实测尾部reserve单列；最初Python启动、编辑、review及Git仍不在静态计时窗，不能声称全workflow wall/RSS准入。终态自身exit由最终Git逐blob读回承接。actual F、生产validator/bootstrap、所有科学/资源/正式门禁继续false。
