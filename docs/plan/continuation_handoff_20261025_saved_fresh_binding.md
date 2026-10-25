# C：F saved 子角色绑定接口交接

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[ordinary文件入口交接](continuation_handoff_20261025_saved_fresh_entry.md)，起始HEAD `bdeebb784575824742f89b76be7e11ad5a730a1c`；发布hash以远端读回为准。活动目标“持续推进计划”继续。未执行真实saved F、B/C/E重放、solver或正式运行，新增模拟小时0。

本轮将实际SCHEMA的parent/fresh绑定接口写入原ENTRY：`argv_for`唯一saved grammar，固定`--saved-entry`与context/tree/channel/nonce；input/output从context推导，descriptor从role推导，supervise builder继续拒绝。独立SavedFileBootstrap持有raw context、main/argv/orig_argv/path、ENTRY bytes/file identity/父链、EXE identity和完整受控环境。RoleStore及execution_context要求同一role/context/tree/Open-only writer；ordinary/saved不能跨域。`_open_saved_role_inputs`仅返回store/held/channel，不运行科学角色。

`saved_owner_inputs`是creating-process构造数据，无launch/factory或run authority。它从同一held store和原reservation派生输入并消费一次，保留原start；consume最后一次store检查后重做source/EXE/env/deadline书挡，随后仅内存提交。生成后跨deadline、source/EXE/env/endpoint漂移均拒绝check；raw字典或任意tree不能替代能力。controller→parent仍依赖未实现的saved supervise，当前parent→fresh仅有单位接口正例。原ordinary constructor/watch及公共main仍拒绝production/saved模式，实际saved文件入口与owner尚未接通。

最终源码 **59唯一节点终态通过**：28 saved binding units、12 critical role units、4 changed interface checks、15 ordinary角色矩阵。15项角色矩阵分两组全终态，旧45s失败/超时不回写。全部pytest attempt **238.315s＜240s**，静态另60s、总帽300s；不得在该批次追加pytest。完整77新单位节点只跑了最终28项，其余49未计通过；早epoch的通过组也未计当前59。完整26旧role units只选12项，normal external invocation计划未跑。

保留binding_units_01的4pass/56setup errors（实际OUTPUT父目录不存在）及binding_owner_07的30s组超时。单位夹具显式模拟输出父目录identity、main/flags/preimports、tree和native endpoint，仅从当前P1/SF49做只读capture；未创建实际OUTPUT及其父目录，不是实际saved context物理身份、OS命令行或真实owner证据。terminal image冲突单位分支早epoch已测，未计当前；真实root-exit残留helper完整成功窗口仍OPEN，saved不沿用ordinary cache例外。

14角色图/197 archive entries由原stdout精确派生；原context只存pin及省略environment的projection。2,382旧路径、三导航全部旧正文、P1全683文件和原科学adapter/guard/outer/scope-budget/SF49/17 targets保持。保存核验入口为`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_binding_v1_non_authoritative/checks_01/saved_checks.py`。旧full saved checker在canonical改动前通过；现在应核冻结snapshot/原输入，不用新canonical替代旧epoch。独立只读PRE_SEAL的静态必修findings已闭合，无official verdict/receipt/seal。

恢复先核Git/进程，读[本轮合同](staged_deliverability_c_saved_fresh_binding_development_contract_v1.md)、[原F范围预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)、[报告](../../results/tables/staged_rts24_saved_fresh_binding_v1_non_authoritative/validation_report.md)。优先在冻结源码上给其余49新单位节点固定新有限预算；然后实现独立saved constructor/watcher和trusted supervise。保持一次parent/fresh、零solver/重试、40+5+5/180s，关闭完整调用量、最大合法context/四record、昂贵失败/发布、arming与host最终同步I/O硬中断、整链资源后才判断安全与具体授权条件。本轮不授予真实F启动权；局部saved verified、整包science/resource/formal/public P2全false，完整319/139/F-X、C整体和D/E有限比较/敏感性/留出仍OPEN。
