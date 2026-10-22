# 保存 H3 双 Reader 的有界诊断

状态为 DRAFT_NONAUTHORITATIVE / PRE_SEAL。任务为 R3，root 是唯一 writer；现有 reviewer 只提供只读 pre-seal findings。实现沿用 karpathy-guidelines 的小范围修改和可核验出口。

本包的 DAG 为：复用旧 950 bindings → versioned historical/source/validator 修复 → targeted/相关回归 → findings 修复 → 当前预算与 hashes 核对 → 一次保存 H3/M5 prepare_many（两个独立 Reader）→ 原始 join/projection 的 saved-identity-bound reconstruction 与 21 个 detached 拒绝案例 → 终态/原件 SHA → 预算更新。不给现有 owner 或任何长链授予执行能力。

旧 case 为 D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0，共 465 文件、444 owned pins。保留旧 source v1/v2、950 包、constructor208、archive809 和 business69 原字节；不重建 N0/Job/selector，不重跑 chain_07、connected_03 body、旧 four-call 比较或 business cost01。

新路径保留一次 constructor 数值遍历，但增加全部 H 个 typed packet 的 immutable input/audit/full-nine-field digest、原 validate_current 再验、三个 parent 根的 3 轮 namespace 检查、3 次显式 model dependencies snapshot、all-H 后最终 filesystem/source/model/runtime bookend，以及独立 frozen cleanup。普通单元测试不启动 solver；unit_01 的6个 bytes 编码失败和 unit_03 的 copyreg 惰性 class cache 失败保留。unit_07 294 项通过，18 份 before/after+tested bytes，已测 required solver-forbidden 窗口。

诊断限一次完整 H3/M5 batch，即两个独立 Reader、六个 prefix-hours、两次 parent traversal、12 个保存 Job artifact replays、60 个 M5 stage replays；这些 replay 不求解。两 Reader 分别新增3个 packet validation、6个完整 packet digest、3个 model snapshots、9个根 listing。不能从这一次诊断直接外推 M232、H168/H192、真实 RTS 或完整 owner 的 wall/RSS/storage。

继承并固定原 watchdog：wall 240 秒、连续无 case read-open activity 90 秒、tree RSS 1 GiB、输出逻辑文件 128 MiB、2秒采样、30秒心跳。Case read activity 不是科学进展。只允许直接 System32/conhost.exe helper；无新正常 Job/native 子进程。超限仅停止本 runner 持有且 PID/create-time 匹配的子进程，保留 stdout/stderr、采样、异常、退出码及 cleanup 终态，不自动重跑或延长时间。操作无 solver license/paid query/network download。

每 Reader 的 packet+selected-frame 合计 cap 是128 MiB；values cap64 MiB。第二 Reader 与 first captured/values 可重叠，因此这些已声明容器的保守内容合计 cap 是320 MiB，另有 observed、普通模型、Python/第三方 allocator、guard inventory 和文件缓存，均不由它们界定。1 GiB 是本诊断的采样停止阈值，不是 H192 的峰值证明。输出 cap 亦不是 case/SQLite/FS 分配上界。

性能依据仅复用旧 H3 batch83.976秒/outer89.781秒作为取样先验，不声称是新路径上界；240秒是诊断停止线。新增 all-H loop、guards、final namespace/readback 与 cleanup 均需在本次完整路径中计时。实现、冻结 config、保存 source map、fixture、原 harness、测试终态和预算逐项SHA绑定；运行中变更即拒收。

本次 reconstruction 使用原 join/projection、shared saved manifest resolver 及显式 one-field packet projection stand-in；并非独立科学实现，也不直接读取旧 raw scientific payload。真实来源重新审计、任意动态属性/反射、未观测 ABA、真实文件并发故障矩阵、owner 接线、H168/F≤24 与 episode 终结 producer 路径仍待验。整体性能审查、resource admission、formal ready/result、native authority 全部保持 false。
