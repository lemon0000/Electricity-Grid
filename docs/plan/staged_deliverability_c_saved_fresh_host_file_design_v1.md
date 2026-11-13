# F：Host manifest 文件层准备设计 v1

2026-10-30，DRAFT_NONAUTHORITATIVE。承接[Windows源码准备与重放交接](continuation_handoff_20261030_saved_fresh_host_windows_preparation_v2.md)。本步实现固定单文件 publication capsule 与 Host 关闭链的连接，公开构造/issuer 保持关闭。完整 context/Core/transport 验证、source-authenticated issuer、外部broker/guardian、实际Native/完整F仍为后续工作。

capsule 在 Host anchor 创建时强持，绑定 creator、原时钟、nonce、直接 parent、唯一绝对 path、manifest pin 和由完整 request/context/template/transport/payload 原字节派生的 source binding pin。Host 在发布前精确比较完整 binding；receipt 是诊断数据，不授予角色/lease/Guard/release 权限。假 capsule、复制对象或脱离原 capsule 的 receipt不能通过实际文件层的类型、root及binding检查。TCB/source issuer尚未认证，不据此声称任意调用者都受此约束。

路径限定 Windows 普通绝对 drive path，拒绝UNC/device/extended namespace、ADS、NUL/control、`.`/`..`、非法字符、重复分隔符、尾随点/空格及DOS设备名。parent与path的直接父串精确相等，不创建目录。沿drive root到parent逐级lstat普通目录、非reparse及稳定dev/ino/mode/attributes；leaf为普通、非reparse、单link文件。path lstat与held fd fstat的dev/ino/mode/nlink/size/mtime_ns/attributes必须相同。重复bookend不排除并发替换或ABA；对抗性路径包含仍待Win32 ancestor HANDLE路线，不能据此授予生产path authority。

单次发布先消费path/nonce与1file/原raw字节reservation，open前先记OPEN_ISSUED；用O_CREAT|O_EXCL|O_RDWR|O_BINARY|O_NOINHERIT，直接写入预分配fd box，exact int>=0包含fd0。open调用开始而未捕获fd时永久OPEN_UNCERTAIN，不重试，不把FileExistsError的已有文件当owned，不删除既有或partial文件。固定操作表逐leaf前后核身份与重入计数。

写入使用held fd，raw非空且<=131072B；仅接受正向且不超remaining的os.write结果，最多8次，每次最多65536B，异常不重试已发出的调用。fsync前记ISSUED；成功返回只说明本次调用返回，不证明目录或断电持久性。lseek到0后最多8次bounded os.read，含EOF确认；与原raw逐字节相等。held fd保持到Host关闭，两个Host publication bookend均从该fd重新读字节并核parent/path/identity/noninherit；不重开路径取代原fd，不依赖缓存receipt。

独立文件cleanup先记CLOSE_ISSUED，最多一次os.close，异常永久CLOSE_UNCERTAIN，禁止按已可能复用的同整数重试，也不以post-close fstat作关闭证明。正常返回作为操作完成的局部证据；Native返回到Python记录窗口仍未证明，未知保持未知。snapshot失败不压住已捕获fd的close；Job quiet失败也不阻止文件fd关闭。生产类不实现__del__、FileIO/fdopen/context wrapper或unlink。

Host v3把原capsule身份、binding和文件cleanup状态纳入held/terminal image；清理各域独立收集错误，publication cleanup位于finally路径，保留原primary和secondary。文件只有NEVER_OPENED或明确CLOSED且无OPEN_UNCERTAIN时才允许Host资源终态CLOSED；terminal重复调用返回原sticky failure，不重复I/O。对coordinated root/源码身份篡改的完整防护仍属于未完成的source issuer/TCB工作。

全部活动操作沿用原invocation_started+180秒，publication使用原prepare10秒；每次I/O和clock前后bookend，cleanup仅用原剩余failure reservation。clock失效或超时不会阻止对已知fd的单次best-effort close，但使结果UNRESOLVED。同步stdlib syscall无强制timeout，外部guardian硬停止和最终I/O阻塞仍OPEN。

普通验证分两类：专属system tmp中真实stdlib文件I/O核create-only/identity/write/fsync/readback/close；fake文件与fake DLL的完整Host私有控制流核异常/重入/Native-文件联合清理。临时目录由测试夹具在已核边界内清理，生产机制本身保留失败artifact。无ctypes Win32文件后端、Native sampler、目标/验证child、P1读取、Source49模块或NFC12重跑；实际文件测试不冒充Native校准、source/owner认证或完整F。

验证范围固定后，独立新包register→inspect→unit→非权威PRE_SEAL→saved→checkpoint，首次登记冻结，首次拒绝只checkpoint。阶段帽5/6/35/10/8/5秒，static34+unit35=69；root10files/4MiB、record1MiB、CP预留1MiB/1slot。前驱CP34577B / `ab980a79488fa414788a49aff112a359871e63632e84d562dcd12b2842f6ce2f`、累计1584.3418539999832秒/62不接受、input1688/113289494B、archive361/46354828B完整继承。新runtime闭包须覆盖实际验证新增stdlib；source/data/scientific门及原F全部预算保持。
