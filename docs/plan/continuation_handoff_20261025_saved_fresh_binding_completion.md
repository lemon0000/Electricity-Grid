# C：冻结 saved 绑定77单位节点交接

2026-10-25，DRAFT_NONAUTHORITATIVE，起始HEAD `d985f709f457022b22193c3a25839c34fe0037e0`；发布hash以远端读回为准。接续[绑定接口交接](continuation_handoff_20261025_saved_fresh_binding.md)，活动目标继续。canonical三源码未改，补齐剩余49节点，22/16/11三组各9.828/17.547/11.891s终态通过，pytest39.266s/80s、静态≤20s、批次总帽100s，未追加此前238.315s批次。

新49与旧28的三源snapshot/SF49完全一致且node union精确77，冻结ENTRY `cc384f65...`、tests `16a0d2c0...`、SRC `26b919e3...`。单位logical父目录/main/flags/preimports/tree/native注入及科学边界保持，不是实际saved文件进程或owner证据。P1全683、旧工件、原scope-budget/guard/outer保持；没有真实OUTPUT/父目录、B/C/E重放、solver或新模拟小时。

保存核验入口：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_binding_completion_v1_non_authoritative/checks_01/saved_checks.py`。它允许未来ENTRY/tests改变，仍核冻结snapshot77并显式返回canonical匹配状态；不自动把77算作未来源码通过。

接下来实现独立saved constructor/watcher，保留ordinary production-mode拒绝、原OwnedChild/完整witness及40+5+5/180s。必须使用默认无issuer的one-shot SavedChildLaunchPermit，data-only SavedOwnerInputs不能授权Native；私有注入owner恒real_owner=false。需拆分inputs的prelaunch-unbound与post-bind不可变书挡，强持partial owner/channel/原始异常和cleanup错误，relay绑exact upstream对象、deadline继承原reservation start。实际issuer/supervise/public CLI、真实saved F、最大合法编码/完整计数/昂贵失败/硬中断/整链资源仍OPEN；局部verified及整包science/resource/formal全false。
