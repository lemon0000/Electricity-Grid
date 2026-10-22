# 实际保存 Reader 的失败窗口诊断

本包为 R3 / DRAFT_NONAUTHORITATIVE，root唯一writer；只读reviewer提供PRE_SEAL findings。复用 source v3 成功H3包2483 bindings、465文件/444owned及原 saved fixture。当前 related Python/solver进程为空。既有 source/helper/owner/config/结果字节保持。

包内DAG：fresh核旧2483绑定 → 新观察器support unit及bytes → 固定9-case矩阵/资源与review → 每case独立进程安装原synthetic/shared manifest resolver → 原v3单Reader → 注入一次故障并检查实际cleanup → 恢复hooks/alias/code/共享handle → 原件SHA和终态 → 更新接线判断。没有新N0/Job/selector/native solver、外部下载或付费调用。

五个constructor case均先取得真实三个inner objects及四个outer ReadViews，在原HistoricalSnapshot.__init__首次state=self.inspect之前注入。dependency drift case立即显式调用原独立guard，不能等到全constructor完成才拒。另四例是postconstructor、all-H后真实只读sharing denial、H2 selected=(1,)但篡改unselected0 packet，以及第三轮namespace第一个root（第7个root inventory）的_names返回值seam。仅后四例完成数值prefix，共最多5个prefix-hours；预期保存Job/stage读取上限10/50，必须由profile实际counter确认。

每case预期inner顺序journal→anchor→root_lease，再outer逆序；记录真实对象ID、closed flags、owner fields=None、capture sentinel与captured/all_packets/seen_hours三种显式清理容器。ReadView是identity observation，不是OS writer lease；不据此声称释放writer lock。不会声称其他局部容器均被清空，也不把诊断持有的引用寿命当生产内存指标。

sys.settrace仅对四个exact code对象接受line/return事件；profile按exact code/对象ID记close与Job/stage/正常_after return。callback错误单独拒收；landmark绑定AST唯一位置和line/lasti；每例要求injection_count=1及预期拒绝路径。constructor的top-level异常及context/cause链单独保存，检查原注入primary对象是否保留，不能把任意instrumentation错误当有效拒绝。finally恢复原trace/profile以及fixture/alias/code/Path，恢复后原guard应可用。

真实文件读取负例固定000.terminal.json。CreateFileW仅GENERIC_READ、share=0、OPEN_EXISTING，冲突原生码32；临时文件unit已确认Python Path.read_bytes表现为PermissionError errno13。诊断结束CloseHandle成功后再核file identity和SHA。此例覆盖临时外部只读handle造成的sharing violation，不覆盖内容漂移。H2 packet为内存反射；namespace为返回值seam，磁盘不新增文件。不能将这些机制混写成完整真实FS并发矩阵。

固定全包240秒、每例90秒、连续无case read-open activity60秒；768MiB owned-tree采样RSS、64MiB输出逻辑文件、2秒采样/30秒心跳。仅允许直接System32/conhost.exe helper。任一case不符合预期即停止余下case；不自动重跑/延长预算。超限只清理由runner持有且PID/create-time匹配的进程，完整保留request、stdout/stderr、monitor、worker/outer terminal与失败现场。

预算先验为上轮无instrumentation的H3 constructor43.386/38.454秒（各3h）；当前最多5个完成prefix-hours，另九次冷import/早拒/恢复和trace/profile开销。240秒是安全停止线，非数学wall上界；不得将本包wall当性能对照、H192预算或资源准入。输出存储上限不含case/SQLite/FS分配。RSS采样可能漏瞬态。全部formal/resource/native-authority门保持false。
