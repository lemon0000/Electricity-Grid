# C/F：import machinery差异的单次有界取证

2026-10-26，DRAFT_NONAUTHORITATIVE。起点HEAD `c7a930a57fecbe1b33bc9e3f055a56184128563c`，接续[失败与commit修复交接](continuation_handoff_20261026_saved_fresh_import_policy_cold_v1.md)。root唯一writer，独立只读PRE_SEAL；按agent.md §9既有开发授权内的有界性能诊断执行，无formal/native/OwnedChild/Job、solver、角色或F运行。

## 独立问题与前序边界

仅回答当前生产loader关闭时，`meta_path`、`path_hooks`、`sys.path`、`path_importer_cache`或`sys.modules`的哪项与guard保存值不相等。只运行一个普通normal fresh child，guard仍由原生产factory安装；不调用_set、不改guard或策略、不重跑三cold、不执行saved/terminal。从Unresolved.boundary读取已关闭的实际状态，与当前machinery只读比较；诊断accepted只表示取证完整，cold_acceptance及所有运行/资源/科学/正式gate继续false。

静态来源：`src/staged_rts24_saved_fresh_adoption_v1.py → saved_prefix_replay_v1 → saved_point_replay_v1 → numeric_interface_v1:5 → pyomo.environ → pyomo.common.log → deprecation/fileutils/dependencies`。环境实际源码中，deprecation.py:665在模块顶层append MovedModuleFinder，dependencies.py:544/549创建singleton并insert DeferredImportCallbackFinder。静态上证明这两处注册可达；不把它们当诊断03已观测到的完整差异。six.py:1003也有append，但matplotlib/dateutil/six链含deferred resolution，当前只能作条件路线。

前序原账及9条失败完全封存：static118.8725048/120、pytest353.8217016/420、总472.6942064/540；1.1274952s剩余不挪入本次预算，不改原帽。三个policy根原127文件/8,462,120B超8MiB 73,512B，仍为失败。本scope是对该失败的新问题取证，不改变原scope验收、不让原cold/封装变成通过。报告必须列predecessor、successor和全累计；后续修复/验证需另行明确范围，不现场retry或续时。

## 路径、成本与停止

登记≤2s；一次capture≤12s，含准备/实际child/后置pins及0.5s尾保留，目标timeout为余量扣除2.5s收尾；小型只读归档≤4s。新static合计≤18s、pytest0。首次Python启动、编辑/独立审查/Git不计capture账，因此不能声称完整workflow wall。已观察正常child耗时约2至6.25s，12s capture容纳已知上界及前后成本；不把该取证预算视为完整F成本。任何失败、超流或超时保存终态且不重跑。

诊断capture父端只允许一次精确EXE、list2cmdline argv、ROOT cwd和env=None的Popen；登记阶段另有一次精确只读Git对象查询，费用包含在2s登记帽内，不在cold child内执行。子端在ENTRY import前安装独立P1/actualF读、写、mutation和额外process拒绝观察，唯一固定lscpu事件由生产guard拒绝。原bounded drain限制stdout262144B/stderr32768B、4096B块，超限kill/wait；记录reader/pipe与Windows HANDLE关闭，并读取终态peak working set（不宣称RAM硬帽/整链资源准入）。未覆盖native aliases和内部科学API，不安装会引起审计重入的profiler。

## 保存与核对

新根`results/tables/staged_rts24_saved_fresh_machinery_diagnostic_v1_non_authoritative`，≤16文件/512KiB。只存登记/探针/capture/archive四个小helper、admission、一次stdout/stderr/exit、结果与小checkpoint；无完整Source副本、导航snapshot或历史root复制。用当前42项regression admission的Source49 epoch、现有content-addressed snapshots、Git parent commit和旧manifest精确pin作引用。每次capture前后核49 raw pin、helpers、admission、固定policy、EXE/Python、NumPy utils/subprocess及两Pyomo文件；不在capture重复遍历4616历史路径。历史保全不重新宣称独立全扫，已有失败/原字节由Git引用继续保留。

五类machinery只记相等布尔、长度、逐项identity/descriptor SHA、首差索引和finder/hook type/module/qualname；路径只记UTF-8长度/SHA/类别，不输出完整sys.path、env或模块表。cache/modules只记容器identity是否相同。before对象引用必须与boundary保存的原身份列表相等，避免比较位置失配。取证不认可任意漂移，更不通过重commit来接受导入期间变化。

新根局部合规仅是诊断工件检查；`predecessor_combined_resource_admission=false`及`policy_resource_admission=false`固定保留。PRE_SEAL发现、Source/辅助代码bookend、记录费用和实际资源后发布可续接交接；共享导航仅保存短prefix/Git引用，不复制全文。
