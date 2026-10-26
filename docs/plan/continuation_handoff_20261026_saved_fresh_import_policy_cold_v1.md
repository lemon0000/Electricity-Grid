# C/F：import policy冷导入失败定位与commit修复WIP

2026-10-26，DRAFT_NONAUTHORITATIVE。宽goal继续active。已发布的上游HEAD为`7e091fc3b9d7dea9cc293256f4ffa12fc418de1f`：此前wire固定literal验证根/独立dependency image两项风险及剩余data API已有开发检查点。本轮新增dependency-import原语，尚未完成真实冷链，更未授予actual F。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/production seal。

## 当前证据与修复

ENTRY新原语以函数literal固定2881B/5eb240e2...的v2 policy；固定EXE/stdlib/NumPy外部读取允许已pin hardlink，保留regular/reparse/目录与读前后身份校验。实际安装用closure sentinel见证；只对固定NumPy `lscpu`栈拒绝启动并验证False fallback，其他所列process/mutation/write/P1/actualF读事件sticky拒绝。单正常creator线程、失败关闭、Source49 canonical bytes bookend、代码/绑定bookend均有逻辑实现；独立Root、任意RAM/中窗ABA、cold-main、自我锚点和transitive runtime闭包仍未建立。原runtime v2继续`UNDECIDED_BLOCKING`，v3 proposal整体admissible=false。

本轮三根均保留原字节：

| 根 | 已观察的结果 |
|---|---|
| import_policy_v1_non_authoritative | 38文件；首次pytest序列化TypeError，retry为31 passed/1 failed，external bookend与Conda硬链接规则冲突；无cold子工件 |
| import_policy_v2_non_authoritative | 39文件；原collection＋显式修订final collection都实际收41节点；41 pytest通过；cold父驱动按list比较Windows命令行string，首Popen被自身拒绝，missing9且无case启动 |
| import_policy_cold_v1_non_authoritative | 修正父驱动exact executable/list2cmdline/cwd/env后正常child确已启动；normal仍失败，管道/HANDLE关闭；caught/blocked未执行。诊断02/03仅成功捕获失败报告，component_acceptance=false。新Source修复后42项逻辑测试通过；真实cold未重跑 |

诊断03原报告明确：optional=1、blocked=1、sentinel=1、internal introspection=6、NumPy False，但classification_error/violations=1/FAULTED；P1/actualF/write/unexpected process计数均0，科学内部API未instrument。primary在loader的post-import `source_pins()->read` open，audit_primary/first_error在`_audit_entry` commit比较失败；cleanup还观察到`_entry` import-machinery书挡差异。

根因修复为loader写入`_adapter`、`_adapter_bindings`后立即`guard._set()`，再执行第二次Source49读取；原代码先改image而未commit，导致下一open审计失败。新回归`test_saved_import_policy_adapter_commit_precedes_source_open`使用无真实hook的逻辑fixture，在第二次source调用手动触发open，覆盖此边。当前Source49 epoch为`a5bd60823fc501feddd91512a9c16ddf7ad1cdfacdd2386e16bbfafd1ed4f455`。新42节点为旧41＋该回归，实际collection/call均42、无skip/fail，charge6.78688s；旧41/215/480等只属于各自冻结epoch，不称当前全回归。

## 预算、失败与封装边界

原120 static／420 pytest／540总帽继续，不重置。归档前static115.5054887、pytest353.8217016，总469.3271903。最后≤4.4s的stdlib WIP归档实际charge3.3670161s，在resource_caps_and_binding断言失败，accepted=false。终账为static118.8725048/120、pytest353.8217016/420、总472.6942064/540；静态仅余1.1274952s。下一步必须包含此失败费用，不再启动验证。未执行saved/terminal，两个预留oracle及capture路线不得被当作通过证据；原cold helper/baseline也不能用于当前新Source启动。

失败累计9条capture/准备/归档记录：原wire三条，v1两条，v2冷父驱动一条，修正驱动后的normal一条，4s诊断准备超时一条，以及最终WIP存储帽拒绝一条。准备超时未启动child且没有内部perf记录，使用工具实际wall6.4871657s＋0.5s reserve保守计6.9871657s，明确含外部启动开销、超出原4s帽；不伪造stdout/精确内部时间。诊断02/03 capture accepted不代表组件通过，分别计7.0598013s、3.0504535s。所有失败及保守费用完整保留。

资源实际失败：v1为38文件/3,001,676B，v2为39/2,448,486B，冷根为50/3,011,958B，合计127文件/8,462,120B；文件数未超128，但字节数比8MiB多73,512B。四份完整导航snapshot使冷根超出组合预算；全部原样保留，不删除/搬移来伪造过帽。单根64/4MiB和原wire 198/10,330,613B（帽204/16MiB）仍满足，组合资源门禁未通过。最终checkpoint没有生成bound_files/preserved_paths，不得声称完成保存封装。该检查在到达存储拒绝前，已核4616前序路径、Source/42回归、精确AST增量、历史ledger/诊断和初版四导航snapshot。snapshot内“8条失败”是最终归档失败前时点，导航当前入口另已更正为9条。production seal及运行、资源、科学、正式gate全false。

## 后续顺序

1. 先读本交接、WIP checkpoint、当前计划/blocker并核Git/进程；续接包含保守补账与WIP检查的原账。当前静态1.1274952s不足进一步验证，组合存储帽也失败；先明确后续独立有界admission及归档根，不重置旧账，不改写/清理失败根。
2. 静态核import machinery实际差异的来源，保持该门禁。03只证明cleanup确有差异，尚不能认定是哪个meta_path/path_hooks/path组件或归因于任一包。不要盲目删掉检查。
3. 在明确的后续有界验证admission中固定新Source，复用42逻辑测试的准确范围；重新执行normal/caught_effect/blocked_installation，并在断言前保存diagnostic。只有真实三case闭合后才能推进保存审计和runtime successor；本轮无此结果。
4. 继续实现真实producer/bootstrap与transitive runtime绑定后，才讨论角色能力、issuer/permit和F。现有ordinary observation或closed guard不能转换成真实role/运行权。

Git只同步本轮ENTRY/tests、三policy根、scope/交接与共享导航前插。并行论文/文献/绘图与共享导航旧body保留，不能报告全局worktree clean。最终commit/remote hash以实时读回为准。
