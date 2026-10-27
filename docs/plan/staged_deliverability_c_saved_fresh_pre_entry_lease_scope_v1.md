# C/F：独立 pre-ENTRY 本地输入 lease

2026-10-27，DRAFT_NONAUTHORITATIVE，起点 `375a07f765e1505e7f63f12421343b115ce17b04`。接续[根catalog交接](continuation_handoff_20261026_saved_fresh_root_catalog_v1.md)。root唯一writer，独立只读PRE_SEAL；Source49、ENTRY、adapter、旧profile/结果与所有失败保持。

## 范围与信任层次

新增独立stdlib bootstrap。父端在Popen前固定bootstrap/probe原bytes、Source49开发epoch、EXE、manifest raw、精确env/cwd/argv；以 `EXE -P -B -s -S -c <exact held code> ...` 启动，先持实际Popen process HANDLE并核PID/creation/image，再通过小型stdin frame释放child。stdin写入使用独立有界等待线程；timeout先kill/wait，再核写入/reader/pipe及process HANDLE终态。字节码/用户site/系统site/unsafe path均关闭，保留PYTHONHASHSEED=0和原线程变量。禁止PYTHONPATH/HOME/STARTUP/INSPECT，固定stdlib/DLL初始path；startup敏感`._pth/pyvenv.cfg`缺失须由实际外部文件观察和child书挡核对。

pre-ENTRY仅指任何Source49/ENTRY原文件读取或编译之前。解释器、exact bootstrap、builtin/frozen machinery、ctypes/_ctypes和Win32 query API已先执行，是明确条件性TCB；不称整个Python/native闭包已认证。`E`外部来源与`U`上游角色owner仍OPEN；普通parent观察`P`、manifest绑定数据`D`和本地连续持有`L`不能反推E/U。父端仅独立核HANDLE/PID/creation/image/exit；Python对象图/loaded code身份只能child本地书挡，parent独立Python图认证恒false。

条件性TCB叶明确包含整个受控compute CPython发行版的VM/compiler、stdlib、pyd、必要DLL和native loader/kernel语义；它是assumption，不是本scope的verified evidence。六个文件字段仅称selected_runtime_file_observations。先做唯一≤5s discovery，不发行L：在release后、其他stdlib import前安装有私有sentinel的早期audit，快照解释器预载模块、记录ordered import/open，再保存最终origin/loader、disk-backed file pins和native module boundaries。冻结该profile后，后续独立verification才可匹配并产生conditional L；不能同一run自产profile自证。profile字段只描述文件与加载路径观测，不认证stdlib实际函数图。profile不匹配时拒绝L，不能声称受信TCB或native内部副作用已被预防。

在early audit之后使用frozen os向本child添加唯一受控Library/bin DLL目录，使-S下的codec/_ctypes依赖可解析；强持os目录cookie至probe收尾，RemoveDllDirectory由原stdlib对象执行，另记录close返回。该cookie不是CloseHandle对象，不能用HANDLE错误6伪证。loader的finally只作已关闭cookie的幂等收尾，不能补造probe正常清理。

child必须先读有界release frame与canonical/closed manifest，核固定6571B Source49 map SHA `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`，不能从当前49文件制造expected。manifest自身pin由已持parent固定，仍只是开发绑定数据。随后以bootstrap自身query API取得当前process/thread不可继承HANDLE，保留实际PID/TID/creation/image/OS command line；两self HANDLE live后才允许Source49读取，单次source aggregate≤2MiB，EXE/native TCB单文件≤8MiB。read使用普通文件/父目录/读前后identity与hash书挡，源码raw强持为不可变tuple，不保留source文件HANDLE。

`LocalPreEntryLease`普通构造/copy/pickle/foreign creator关闭；强持manifest、原方法/helper/code/builtin、sys与关键模块容器/对象、argv/path/env/cwd、原self API签名和HANDLE。LIVE检查后向同进程`LocalPreEntryInputs`转交；以唯一resource-owner引用赋值为commit point，原source不再关闭借出资源。commit前失败由原source清理；commit后异常必须强持实际target，不丢owner或double-close。目标仍持真实self HANDLE及Source49 raw，可供未来runtime lease直接消费，不能由stdout/JSON重建。成功probe仅在同进程目标编译已持ENTRY raw（不exec）、关闭资源后输出数据；child退出后该能力消亡，下一阶段须在同一bootstrap内继续接线。

审计窗口在manifest校验后、Source49读取之前建立；self前Source49 open、P1/actual-F读、文件写/所列mutation或额外process事件sticky拒绝。资源清理不因绑定漂移被跳过；thread→process各关闭一次并以持有GetHandleInformation/error6见证，不能确认就强持UNRESOLVED。audit安装必须用私有sentinel见证；hook终态惰化但保留callback。两个通知事件process_handle_opened/transfer_prepared供独立probe故障观察，不接受production测试callback。

原import-v3依赖`-B -s ENTRY`、baseline4和旧argv grammar；本新模式预期基线3须真实观察，不能直接复用旧guard或伪装main/path。repo/site-packages接线与新的B_S import-policy、实际live-runtime/registry/角色链留在其原阻断项。所有F/native/role/science/resource/formal/run权限恒false。

## 验证与预算

本scope独立static≤50s、unittest≤30s、总≤80s，不重置或转移旧120/420/540、迁移60/45/105及catalog30/20/50账。前驱全累计static154.1855595、pytest366.4889797、unittest0.8414678，总521.516007；原12条不接受记录与超帽保留。

登记≤3s；唯一startup discovery≤5s；普通单测主组≤8s，已定位失败后仅一次显式repair≤12s；九例cold parent合计≤30s，normal/损坏manifest/flags/env/path/binding/early-source/transfer≤3s，未release timeout≤1.5s，余量用于cleanup；saved/fresh核验≤8s。并发1，流stdout≤131072/stderr≤16384、4096B块，capture包括parent准备/后置书挡，尾部保留1s。RAM只观测峰值，不宣称硬帽；constructor/kernel blocking和整个F资源仍OPEN。编辑/审查/Git及最后exit序列化不作完整workflow wall。

普通逻辑测试覆盖closed manifest/重复键/截断/源漂移、schema/flags/path/env、constructor/creator/copy/pickle、绑定与critical builtin漂移、部分Open/查询/close及secondary、transfer前/后owner归属、失败前驱拒绝。最终注册前固定九例cold：normal、manifest byteflip、flags缺-P、env不同、process HANDLE已开后observer失败、构造后helper替换、self前source open、transfer commit前observer失败、parent不release timeout。实际path/control漂移由逻辑对象测试覆盖；用process-HANDLE窗口覆盖真实部分构造清理。正常与绑定失败须证明native资源各关闭；被kill只记OS终止和parent cleanup，不声称child正常close。

结果根 `results/tables/staged_rts24_saved_fresh_pre_entry_lease_v1_non_authoritative`≤64files/8MiB，exact -c command line≤30000 UTF-16 code units；所有helper/TCB/profile/前驱/Source49/manifest pins与实际执行版本先登记。raw流/失败/费用/create-only records和code snapshots完整保存。单次self lease持有Source49 raw，不复制全历史树；保存核验只核metadata/记录/重算hash，不执行ENTRY/科学adapter/F/OwnedChild/Job/native solver。完成检查点按已授权范围提交推送，四导航只发布新prefix，保留并行内容。

为满足Windows命令行帽，exact transport原样保留core的prefix/release/early-audit，再以标准库zlib/base85携带其余core+probe原bytes。parent核prefix与解压payload重组逐字等于原文及AST相同，分别登记source/transport pins；loader限制解压≤128KiB并核EOF/无tail，child同时核实际loader frame与payload code。early audit先于codec import，codec纳入条件性发行版TCB和discovery闭集。此转换不接触Source49或源码字符串常量。startup profile比较固定code/flags/env/cwd/path和加载观测，manifest路径/SHA/nonce作为明确逐次变化的transport数据不混入加载profile。profile最多128 disk文件、每文件≤8MiB、合计≤32MiB；OS/native边界路径只作条件性root记录。缺失python312.zip与._pth/pyvenv.cfg均在parent前后及每次lease entry书挡观察，仍不证明不可见ABA或全窗无变化。
