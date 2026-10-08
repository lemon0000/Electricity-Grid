# Normal 归档有界身份捕获 v1

状态：DRAFT_NONAUTHORITATIVE。仅提供 controller 在任务 Job 静默后使用的不透明归档读取入口；尚未与 phase controller 连接，不验证 Job 静默，不产生正式运行授权。

## 请求与证据边界

`capture_normal_archive` 接收 root、typed ArchiveCaptureBudget、外部 store/source-execution pins、claimed_result_identity 和 capture identity。identity 绑定请求、SQLite 版本与实际实现路径/字节。调用者负责固定这些请求与任务来源；capture 不将子进程自报成功当作权威证据。

`NormalArchivePins` 返回 store identity、genesis、当前 head、record SHA/字节数及外部 result identity claim。成功记录状态仅为 `opaque_record_captured`。它只说明这次读取的字节与归档 digest 一致，不能说明 encoded_result 合法、赋值可行或 claim 与内容相符。即使 payload 与 digest 被一起改写，也只能取得另一组不透明 pins。

后继必须将捕获到的 head、record SHA 与 claim 交给原 `replay_normal_store`，从同一固定来源重新准备输入，核对完整 record、身份与数值。此模块不构造 assembly，不反序列化 encoded_result，不恢复 owner/执行游标。没有 result 时只返回 unused 或 unresolved_intent；不推断原生调用次数，不允许自动重试。result 存在须有合法 claim；不存在须为 None。

## 读取与预算

复用原 local NTFS 合作式 `_Lease(create=False)`，会以 r+b 打开已有 execution.lock。数据库连接使用 mode=ro、query_only、显式同一读取事务；不执行恢复写入。任何 journal/wal/shm sidecar 均拒绝并保留原文件，等待后续受控 reconciliation，不把缺少捕获诊断当作未执行。

在读取 payload 前检查数据库大小、类型和 length。预算显式限制数据库文件（开发上限 1 GiB）、record（上限 256 MiB，且不超过数据库预算）与 elapsed（上限 60 秒）。这些是读取入口的操作上限，不修改旧 solver/process/worker 限制。metadata 门 1 MiB；intent 要求精确派生长度；BLOB 每块至多 64 KiB，metadata/intent 有界拼接，record 仅流式 SHA。SQLite cache 配置 1 MiB、mmap 关闭；这不是整个 controller 的硬内存上限，SQLite/native/导入开销仍须纳入后继任务预算。

精确检查 sqlite_master 的 type/name/tbl_name/sql 三表 inventory，核 application/user version、DELETE 模式、foreign_keys、integrity_check(1) 与外键结果。header 要求 canonical JSON、外部 store SHA、root 路径/dev+ino、false flags 和 record 门。intent 必须逐字节等于原 schema/store/genesis/source-execution 派生值。head 沿用原 normal_store 公式。

SQLite progress handler 对扫描检查 deadline；每块读前后及最终返回前检查 elapsed。同步 OS/SQLite I/O 不可抢占，因此只是合作式 deadline，不是硬实时保证。异常不返回 pins，关闭连接并释放 lease。前后核 root/lock/数据库 identity、数据库 size/mtime 和实现字节；不防同权限恶意绕锁、伪造元数据或 ABA 修改。

## 验证要求与后继

测试复用 tiny 合成来源 normal 记录：捕获后禁止 solver，再调用原独立重放；错误 claim 在 capture 保持未验证，replay 拒绝。大 BLOB 测试确认分块且不解析内容；非法归档只可得到 opaque pins，不能通过数值重放。其他反例覆盖空/未决 intent、digest/header/intent 改写、超限、额外表/index/trigger、sidecar、hardlink/root copy、lease 冲突、中断、扫描/分块 deadline、读取期间文件与源码漂移。数据库字节及 mtime 不变另有检查。

这些测试不验证真实 RTS 求解、claim 来源、整 Job 静默或完整任务资源；这些由后继 phase controller 与 execution/replay 集成故障测试补齐。


## 当前验证记录（2026-09-20）

旧 Lease 的完整锁文件读取之前，新增 single-link/1-byte 检查，取得 lease 后再核 file identity。sidecar 先经过 local._path，拒绝 broken reparse path；测试以路径层故障注入验证该调用，未声称实测 Windows symlink 权限。SQL deadline 测试必须实际收到 OperationalError: interrupted；只因 integrity 结果不匹配而 ValueError 不算通过。

初步 capture/store/replay 相关回归：94 passed in 235.45s。之后仅补上述 lock/sidecar 边界与反例，最终 targeted：31 passed in 30.07s。相关命令为 `D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_archive_capture_v1.py tests/test_rq2_normal_store_v1.py tests/test_rq2_normal_replay_v1.py`；最终 targeted 使用其中第一个文件。

最终 source SHA256 `31c2415a3765631b20fe3b494bd8a13005152e8e0943c33753f8e803f976214b`；test SHA256 `9d77d768d4e0960679d49770db560cb38f02e1586fea38532cdb5292b0e349ec`。独立最终复核结果另记。


独立最终 targeted：31 passed in 31.66s，source/test hashes 与上列一致。lock 读取门、sidecar 路径与 SQL interrupted 反例均已复核，限定 capture 原语范围无开放实质 finding；不形成 official verdict、seal 或正式运行授权。旧 normal_store/normal_replay/episode_store/normal_process 四个依赖源哈希保持；diff 与新文件 UTF-8/whitespace 检查通过。计划、blocker register、正式准备与规模执行合同已同步。
