# C/F：namespace 冷启动修复后继

2026-10-27，DRAFT_NONAUTHORITATIVE，接续 namespace scope v1。原scope登记、23/23 unit、startup discovery、admission均accepted；首次normal cold失败，原16文件/394,673B整集SHA `0fa866ffc408114be70fb623cf498e2d54e49f6cfd7ab1b70bea7bd25098b24a` 固定，不改任何原helper/controller/record。原raw stderr显示 dataclasses→inspect→dis→collections.namedtuple 的合法 `__defaults__` 设置被full guard拒绝，随后部分helper缺少 NamespaceConstructionFailed 属性导致错误处理再次失败。child无stdout，parent HANDLE/reader/pipe/stdin均终态；没有child self正常清理的序列化见证，不补造。累计不接受记录由14增至15。

新 pre-entry v4 在 early audit后、full guard前明确预载dataclasses，作为条件性发行版TCB初始化的一部分进入新的独立startup画像。early audit仍拒绝项目import、self前source open、process、write/mutation；full guard安装后的函数metadata规则不放宽，不吞掉其拒绝。新core/probe/parent/tests以独立文件绑定；原namespace helper v1按同字节复用。新profile必须重新discovery并独立admission，不能复用旧transport画像。

新manifest标识为staged_saved_F_pre_entry_manifest_v2，probe report为staged_saved_F_entry_namespace_probe_v2，不重解释冻结v1闭域。probe v2在helper尚未完整执行时，只通过exact ModuleType dict和固定类型判断查找failure owner；别名报告使用固定namespace名称，不读取不存在的helper属性。增加一个helper_init_failure冷例，在helper ModuleType已创建、定义尚未执行时注入，证明主异常与self清理终态可正常报告。原四例及精确Source open预期保持 normal539/global490/alias490/partial392；新增helper_init_failure为294，namespace未初始化、exec计数0、input self close=[1,1]。所有role/科学/F/资源/正式权限仍false。

共享原 static40 / unittest20 / total60，绝不重置。原已耗static1.4964592、unittest3.6822834、总5.1787426全部续记；原probes失败0.6066815不退款。后继登记与原登记合计≤2s；重测使用原预留unittest_repair≤8s，保持26个当前逻辑节点；新discovery≤5s、admission≤2s、saved≤6s，均计共享static帽。五个cold每例≤2s；完整组≤原12s减已耗0.6066815，即11.3933185s，保留至少0.7s收尾；缺完整单例预算不启动。普通unit可用于PRE_SEAL迭代，cold前须闭合执行前finding。

为保持已执行原16文件和绝对路径pins，后继结果单独放 `results/tables/staged_rts24_saved_fresh_entry_namespace_startup_repair_v1_non_authoritative`，独立≤24文件/4MiB；原root仍在原32文件/4MiB帽内。组合文件数须如实另报，不能称组合也在原32文件内完成；不删除/搬走历史压低计数。时间账保持共同40/20/60，存储分根，不产生整体资源准入。全部raw、failure、parent终态、helper bundle、transport和registration均create-only。

后继顺序固定为原unit accepted / 原normal failed → 修订登记 → 26-node unit repair → 新startup discovery → 新profile admission → 五例cold → fresh saved metadata。saved复核原16及旧pre-entry61、Source49、当前helpers/profile/manifest/raw与费用链，不重跑bootstrap或科学逻辑。新scope只向真实ENTRY namespace持有推进，B_S导入/owner handoff、adapter及transitive runtime仍未实现；E/U、native/TCB认证、完整runtime/P1、Job/roles/permit/F、科学/资源/正式/运行门禁维持false。
