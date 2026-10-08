# Normal 主机资源余量观测 v1

状态：DRAFT_NONAUTHORITATIVE。`normal_resources.py` 是只读观测与预算比较原语，尚未接入
normal worker、整任务父进程监督或正式实验准入。它不创建目录、文件、进程、配额、预留、lease 或 receipt。

## 来源与复用核查

旧 `run_rq2_public_grid_two_block_pilot_activation_transport_v4.py` 的
`available_commit_bytes` 使用 `GlobalMemoryStatusEx.ullAvailPageFile`；v5 的 `_stop_reason`
已有内存/储备并列拒绝的形式。只复用明确区分资源拒绝与数值结论的思想，旧文件及阈值保持。
新模块使用显式 WinAPI ABI，不导入旧执行授权或监控入口。

- 系统 commit：`K32GetPerformanceInfo` 读取 `PERFORMANCE_INFORMATION`，
  `(CommitLimit-CommitTotal)*PageSize` 为本次观测的系统 commit 余量。
  字段单位与软限制语义见 [Microsoft 结构定义](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information)；
  Windows 7+ 的 kernel32 导出见 [GetPerformanceInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getperformanceinfo)。
- 磁盘：`GetDiskFreeSpaceExW` 的 `lpFreeBytesAvailableToCaller` 进入预算比较；
  caller total 和 volume free 仅保留并检查内部关系。用户配额下 caller available 可以小于 volume free，
  所有输出保留 64 位，见 [Microsoft 磁盘 API](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskfreespaceexw)。
- 卷归组：使用 [GetVolumePathNameW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumepathnamew)
  和 [GetVolumeNameForVolumeMountPointW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumenameforvolumemountpointw)
  得到卷 GUID；不按目录字符串或盘符分别虚增可用空间。

## 声明与比较

`HostResourceBudget` 必须明确给出 additional commit bytes、commit reserve bytes，及 1—16 个
具名 `DirectoryDemand`。每个目录需求含 existing absolute directory、additional bytes、reserve bytes。
字节数均为 exact positive int；bool、float、零和缺失值拒绝。追加需求必须由后继任务预算推导，
本原语不根据单条结果大小推断归档、SQLite journal、临时求解文件或 Python 内存开销。

系统余量至少覆盖追加 commit 需求加储备。同卷目录的追加磁盘需求**求和**，储备取该卷所有声明
的最大值，caller available 取同卷各次观测的最小值；不同卷分别验收。这里 reserve 表示保留给
该卷其他活动的统一余量，而非每个目录各占一份。重复的 role name 拒绝；不同 role 使用同一目录
仍须相加其追加需求。等于边界允许，少一字节即不足。

`resource_identity` 绑定完整声明、规范目录路径、`(st_dev, st_ino)`、卷 GUID、当前模块与
复用的 `episode_store` 源码哈希。`observe_headroom` 要求调用方独立保存的 identity，前后重算。
沿用旧本地目录检查：仅现有 local fixed NTFS 路径，拒绝 reparse。目录替换、预算/源码漂移、
API 错误和畸形数据抛异常，不返回 sufficient 报告；余量不足则返回明确 errors，可同时包含内存和磁盘原因。

## 证据边界与剩余工作

报告包含完整采样值、每卷需求、采样起止 monotonic time、身份和错误。
`observed_headroom_sufficient` 只表示本次采样符合预算比较。
`resource_reservation_held`、`hard_resource_limits_enforced`、`whole_task_resources_verified`、
`formal_run_authorized`、`formal_result` 均为 false。

各 API 与各目录采样不是原子快照；同卷取最小值也不能排除采样之间或采样后的资源变化。
目录前后身份检查采用合作进程假设，不阻止恶意 ABA 替换、内存 monkeypatch 或 token impersonation。
磁盘观测属于当前调用线程的用户；后继执行必须维持相同权限主体，不能把报告转授给其他用户。
monotonic time 只用于本次本地采样区间，不作为跨进程/重启后的持久化凭据。
报告是可构造的诊断 dataclass；当前没有消费它的 authority 接口。后继接线必须在内部直接调用
固定 observer，不能接受调用方提供的报告、observer callable 或过去的 sufficient 标志作为准入凭据。

本模块没有进程启动、系统余量持续监控、任务峰值上限、磁盘写入硬限额或自动重试。
后继仍须把输入准备、构模、执行、审计、归档和重放放入完整任务预算及监督边界；
补专用临时目录、空间不足/写入中断保留规则，以及硬限额与观测式停止规则各自的实际保证。
不得以本次 sufficient、现有 Job commit 限制或 payload 字节门替代整体任务资源验收。
科学机制参数、真实规模求解、恢复/右删失及正式实验门保持原状态。

## 开发验证

测试涵盖边界与少一字节、双重不足、同卷合计和异卷独立、非原子采样保守取值、预算与目录漂移、
无效类型、API/结构错误、64-bit 字段，以及真实 Windows 只读调用和实际目录替换。
仅在 pytest 临时目录测试，不启动 solver、不分配压力内存、不填满磁盘；模拟配额反例不等于实际部署过 NTFS quota。

最终相关验证：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_resources_v1.py tests/test_rq2_normal_process_v1.py tests/test_rq2_normal_store_v1.py
```

主线程 **82 passed in 29.79s**，exit 0。独立 targeted：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_resources_v1.py
```

独立 **35 passed in 1.86s**，exit 0。限定范围 pre-seal 无开放实质代码 finding；
`git diff --check`、新文件 UTF-8/空白检查通过。这些验证不关闭上述集成缺口。

| 文件 | SHA256 |
|---|---|
| normal_resources.py | `6059b28f6f60d30a9905d645d6741fb01a3c6fcc12e50f096447ccb8884fa0ff` |
| test_rq2_normal_resources_v1.py | `2cfb1ea018d30f608e5bad9fa0e542a7bd98e8bcea28fd62a5ae8670a693d4fc` |
