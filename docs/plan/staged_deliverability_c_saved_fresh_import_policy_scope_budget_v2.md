# C：固定外部hardlink读取的import policy修订

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[v1失败冻结交接](continuation_handoff_20261026_saved_fresh_import_policy_wip.md)与[v1实施范围](staged_deliverability_c_saved_fresh_import_policy_scope_budget_v1.md)。root唯一writer，独立只读PRE_SEAL，无生产seal/receipt或运行权限。

当前Conda的python.exe、Lib/subprocess.py硬链接数均为2，通用read的默认single-link规则使v1在external bookend拒绝。v2只对policy中固定pin的EXE与两个库文件使用read(...,allow_links=True)；原read本身、reparse/regular限制、目录链、lstat/open/fstat/read/fstat/lstat书挡、8MiB单文件帽与raw SHA核对保持。原P1/Source读取规则AST不变。此明确允许已pin外部hardlink文件的策略不认证FS aliases或中窗ABA；v3 proposal整体仍admissible=false，旧runtime v2保持UNDECIDED。

新profile为dependency_import_policy_v2：2881B／5eb240e21709d154b7bb17ebcee7947c6300b0108cb147dbb40669744d8e7da7。ENTRY factory、entry和external-input helper各以函数literal固定此pin；helper仅接raw并在读取任何路径前验证，未pin的dict/额外路径/外部策略均零读取拒绝。旧v1 profile及所有失败原字节冻结。其余class/loader规则保留v1：单次正常安装、closure sentinel、五连续frame＋6个内省event、sticky拒绝、trace/profile终态关闭、实际NumPy False、Source49 canonical bookend但独立Root/full runtime/角色能力false。

baseline保存三个固定文件在v2准备时的pin、regular/reparse、nlink与identity。原v1 exit只保存通用Unresolved，当前metadata与旧单链接谓词显示确定的不兼容，不把当前metadata补造为v1执行时的观测。单次正常安装由模块attempt状态管理；主动重绑模块globals、sys/import machinery的中窗ABA和任意同进程RAM改写未认证，仍需未来verified runtime lease，不能把这里称为不可绕过的生产lease。

原账续接static79.36616/120、pytest339.0513453/420，合计418.4175053/540；剩余121.5824947s。collection≤10、pytest≤30、三个cold child合计≤12、saved/terminal各≤8s；合计68s，不重置前述费用/失败。v1 38文件冻结；v2独立root为results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative，≤64files/4MiB。两个policy root组合≤128/8MiB，原wire root≤204/16MiB保持；所有4576前序路径精确保全。

单位验证锁定新版本完整集合；三cold case为normal、after-import处caught effect、已有hook阻止安装，parent总截止7.5s/child≤3s并有有界stdout/stderr、kill/wait、pipe与HANDLE关闭见证。仍不安装会造成审计内省重入的科学profiler；driver只调用依赖导入，内部任意科学/native副作用不作零计数断言。Source49名称、其他47源、原科学与wire API/guard AST保持；policy v1→v2登记增量为：helper raw pin/读取keyword、函数级pin版本化、Source49 canonical比较、测试profile路径及新增定域/Source反例。canonical比较用实际映射的canonical bytes匹配caller冻结raw，明确拒绝True==1别名和non-JSON自定义equality；不改变既有exact Source49域。

baseline/policy/proposal三个控制JSON在每次capture前后精确pin，并与首个admission的control pins相等；baseline初读raw另持到动作结束，杜绝cap/case集合读取与记录所绑版本分裂。原v1缺少的control pin不补造为历史证明。

新结果只支持import-policy原语，不能当33根runtime闭包、cold-main/self-anchor、full683/G0/H3、issuer/permit、真实saved startup或actual F。保存oracle纯stdlib，三导航前插完整旧body，Git精确发布并保留并行论文/绘图改动；宽goal保持active。

## 显式检查器修订与重新收集

首个v2 collection实际接受41节点，同一Source49 epoch，charge 6.0413367s；它仅证明集合及源固定，并未执行保存审计。其oracle尚未精确约束v1→v2 AST增量，不能用于最终验收。该collection、admission、三个控制JSON、四份原helper及snapshot全部保留原字节；新增四份`*_revision_02.py`和`revision_final.json`，修订记录绑定上述原始collection/admission/harness、weak oracle及其snapshot、三个控制文件、同一Source49和完整新旧helper集合。`collection_final`实际重新收集且必须仍为同一41节点/Source；其exit同时固定`admission_final.json`、harness和revision，后续动作只接受此final链。此为DRAFT的显式pre-seal修复，不产生生产seal。

当前static累计85.4074967/120，pytest339.0513453/420，合计424.458842/540。新增collection_final≤8s、pytest≤30s、cold≤12s、saved/terminal各下调至≤7s；static最坏119.4074967≤120，pytest最坏369.0513453≤420，合计488.458842≤540，不重置旧账、不扩大任何总帽。新旧全部helper均在每次capture前后pin；最终oracle将v1 final→v2的5个生产节点、2个既有测试路径节点及3个新测试完整AST固定，其余节点逐序相等，并验两个失败的stdout/exit/Source与三个结果root的实际文件/字节帽。64文件预算计入revision、旧collection、四helper及snapshot、final collection、pytest、三个cold、导航和saved/terminal全部工件。
