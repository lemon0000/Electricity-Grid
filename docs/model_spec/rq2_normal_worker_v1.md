# Normal worker 与一次性日志连接 v1

状态：DRAFT_NONAUTHORITATIVE。本层是连续 normal 后继的短时开发监督链，
没有生产 lease、正式 manifest、seal、receipt 或正式运行授权。

## 本轮完成范围

`normal_worker.supervise_normal` 把已给定的 `SourceNormalAssembly`、`PairDeclaration`、
全部来源/数值 execution pins、两个独立预算及显式环境交给固定的 worker 入口。
调用方先独立保留 `supervision_identity`；该身份绑定 source execution、worker/process/store/lease 源码、
Python executable 路径及字节、worker 预算与环境。下层 source execution 继续绑定数值模型与运行时依赖。
完整 request 的独立 SHA256 另绑定实际输入、路径与 normal genesis。

旧 `normal_store`、source execution、normal kernel 与冻结 transport 不变。
上一轮 `normal_process` 仍属同一个未封存 draft，本轮新增显式 Unicode 环境、
Job 总 commit 限制、thread-id 所有权，以及整 Job 静默核查；历史原语测试记录保留。

## 执行顺序与失效窗口

1. 私有输入快照、外部 supervision pin 及输入编码往返检查。
2. 排他创建新的 `*_non_authoritative` attempt 目录，父进程保持外层 NTFS byte lock。
3. 在子目录 `normal_non_authoritative` 创建原 normal 日志并保留 genesis，释放内层日志锁。
4. 完整 canonical JSON request 写入、fsync、readback；提交独立 launch intent。
5. 原子创建入 Job 的挂起 worker；写入 PID、creation FILETIME、实际 argv 与其摘要、request hash 及 supervision identity。
6. 释放 worker，worker 核对请求、源码/运行身份、环境、自身 PID 及 `sys.orig_argv`，排他写入绑定 launch 摘要的一次性 worker claim。
7. worker 按父进程 genesis 打开内层日志，调用原 `execute()`：normal intent 提交且读回后才允许数值调用。
8. 父进程等待直接子进程；随后终止 Job 剩余成员，查询 `ActiveProcesses == 0`。
9. 只有整 Job 已静默才核对 request/launch/claim 与当前实现，再按 genesis 重开 normal 日志核对结果摘要。
10. 排他写入 `observation.json`。数值接受门不在本层；所有记录保留，不清理失败 attempt。

所有创建使用 exclusive create。现有 attempt 目录不能重新执行；即使 normal 日志尚无 intent，
本层也不自动重启 worker。已有 normal intent 保持原来的不可重试规则。
worker claim 拒绝同一请求的第二次 worker 调用；目录锁与身份保证针对单一 canonical 本地 NTFS root，
不声称复制目录之间的全局 exactly-once 或恶意同权限修改防护。

父进程异常退出时 Job 关闭保护仍适用。若无法证明整 Job 静默，父进程抛错并保留证据，
不读取或发布结果观察。正常路径的 exit code 为零也只说明入口返回；缺结果、超时、
非零退出或 child elapsed 超限都得到 `unresolved_worker_attempt`。
结果已提交但 worker 随即异常退出时，保留完整记录且监督状态仍为 unresolved。
缺失 observation、launch 或 claim 不能反推零 native 调用。
`worker_error.json` 只记录已提交 claim 后的日志打开/执行异常；更早的 request、解码、环境、
launch 或 claim 检查异常仅由非零退出及缺失记录表征。测试中的 `bootstrap_error.txt` 是测试包装器的诊断，
不属于固定 worker 入口的归档能力。

## 编码与环境合同

request 使用 canonical JSON 与现有 `_encode` 类型表示。解码器仅允许输入 dataclass、
datetime、有限 float、tuple/list/frozenset 和无重复键 mapping，并要求再编码完全相同。
它不使用 pickle、eval、任意 import，也不接受 `SourceNormalExecutionResult`、assignment witness
等 owned 结果类型。解码后的输入仍由原来源绑定和数值内核核验，传输哈希不替代来源核验。

worker 使用 Python `-I -B`，显式加入仓库 import 路径。环境清单只包含 SYSTEMROOT、WINDIR、
TEMP/TMP、显式 runtime PATH、四个数值库线程变量与 KMP_DUPLICATE_LIB_OK。
本地已验证 threadpoolctl.py:48 和 sklearn/__init__.py:56 导入时会 setdefault
`KMP_DUPLICATE_LIB_OK=True`，因此当前开发环境显式登记该既有值；不接受导入后未声明的环境漂移。
该环境不是容器或安全沙箱，PATH/环境身份也不证明所有动态库文件内容。
TEMP/TMP 当前为显式绑定的系统临时路径，尚未提供每次 attempt 独立 scratch 隔离。
声明的数值库线程值为 1，solver 自身仍严格使用已绑定的 Rq2SolverSpec；并未声称 OS 级线程总数限额。

## 资源与结果边界

`NormalWorkerBudget` 独立于 normal 数值预算：child wall deadline 最多 60 秒，
quiescence wait 最多 5 秒，显式 per-process/job commit 上限，以及完整 request/normal result record 字节门。
请求上限不超过 256 MiB。Job commit 超限可表现为 allocation failure；不能自动解释为 solver 不可行。
父进程编码、创建日志、身份核查和最终归档的时间/内存未纳入 child deadline；
SQLite 页、journal、错误记录、环境依赖及整个目录没有磁盘配额或预留。
系统可用 commit 储备采样、完整任务资源验收与真实规模预算仍待补齐。

成功传输的状态仅为 `returned_record_unreplayed`，表示子进程正常返回且存在经摘要核对的完整记录。
它不等于内层 normal_accepted；真实模型接受还需查看并数值重放保存的证据。
`numerical_evidence_replayed=false`、`native_execution_authenticated=false`、`formal_result=false` 始终保持。
摘要、PID 和环境核对不是原生执行真实性签名。基于 genesis 的重开仍不认证事先未知的结果内容。
supervision identity 绑定源码合同，不认证 Python 内存未被 monkeypatch。
实际 argv 另外完整登记在 launch，worker 对照 `sys.orig_argv`，parent 对照自己保存的 argv；
Observation 绑定 launch 摘要。测试注入的 stub script 因此可见，但仍不是 canonical worker 的原生来源认证。

整组静默使用 Windows [Job accounting ActiveProcesses](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)
观测；显式环境按 [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
的 Unicode environment block 接口传入。直接子进程 HANDLE 保留至核查结束，操作强制同进程同线程。

## 验证范围和下一项

真实短子进程测试包括：tiny 单次 HiGHS 1 秒/1 线程执行、parent readback、三个 normal intent/result
崩溃窗口、零退出无结果、超时、完整记录超限、worker 重复 claim、环境漂移、请求字节/身份门，
以及 quiescence 失败禁止父进程读取结果。正例的公开来源边界明确使用合成 stub，
不能写成公开数据上的 normal 求解成功。固定原始 worker 入口另验证真实来源缺失时拒绝并保留 intent。
process 测试增加显式环境、Job limit readback、后代静默、非 owner 线程拒绝及静默超时。
补充真实 Job 总 commit 行为的成对控制：每进程上限同为 128 MiB，两个成员各申请 80 MiB，
Job 总上限 160 MiB 时第二次申请被拒绝，256 MiB 时允许，排除仅由 per-process 门造成的解释。
另补集成父死亡：worker 提交 normal intent 后等待，测试终止 supervisor 父进程，
确认 worker 随 Job 终止；重开原日志仍为 unresolved_intent，内层 execute 与外层同 root 再执行均拒绝。
该实验只覆盖已提交 intent 这一集成窗口，未宣称所有父死亡位置已有端到端穷举证据。

下一项为持久化 normal 结果的独立数值重放，再按规模合同补齐整体资源和真实规模验证。
H25 的现有来源/build-only 证据没有由本层升级为真实 H25 赋值、当前调度或四臂正式实验。

## 最终开发验证记录

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_worker_v1.py tests/test_rq2_normal_process_v1.py tests/test_rq2_normal_store_v1.py
```

主线程最终相关回归 **69 passed in 62.41s**，exit 0。独立最新 worker targeted
**24 passed in 34.95s**，exit 0。argv 漂移在 claim 前拒绝；正常测试保存的 launch 清楚展示来源 stub script。
之后源码保持不变，新增上述两组共 3 个 fault/control cases，主线程 targeted **3 passed in 6.57s**。

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_process_v1.py::test_real_aggregate_job_limit_rejects_two_member_allocation tests/test_rq2_normal_worker_v1.py::test_parent_death_after_worker_intent_preserves_unresolved_store
```

上述主线程证据来自 69 项相关回归和 3 项新增 targeted 两次运行。
新增 3 项另经独立 **3 passed in 6.54s**；两项实测证据缺口已闭合，限定范围无开放实质 finding。
独立预审的旧规格现时/历史混淆 finding 已修复；实际命令记录、早期异常归档及共享 TEMP 的边界已明确。
以上仅为 non-authoritative pre-seal；不是 official verdict、seal 或运行授权。

最终 SHA256：

| 文件 | SHA256 |
|---|---|
| normal_worker.py | `8d9d1e77d209a49bd0d00e01cb303b2e56156c633a51245a9f467bbac0ffd3dd` |
| normal_process.py | `ffc487c05c72d00a7c2e8d7515a29f16a3d0c8ac3f0efa6cdba36bbcea34d44f` |
| test_rq2_normal_worker_v1.py | `6fb8c2903814551842e647959deb0b2182112af5b2686a4b190317feae87e87e` |
| test_rq2_normal_process_v1.py | `604810155b6e9159d3fc5d8593d9ec61d43a27c3bf503c3c4a8f9bbbb2bc6778` |

normal_store 与 source execution 分别保持
`a79d766c08970875e8b65e5afc30ee7288d98bcc88a5474e9b5d7f7eace754f4`、
`56a59908c99b5da24047bdd4c93478da6576b9224ca91e2994bc60cad79d57cf`。
最终进程扫描无 Python/solver 遗留，`git diff --check` 通过；未清理仓库。
