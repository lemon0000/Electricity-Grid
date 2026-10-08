# Normal一次性开发调用日志

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`normal_store.py`拥有一次固定`source_normal_execution.run_source_normal`调用的本地日志，
复用`episode_store._Lease`、`_path`及`_file_identity`，不修改旧episode schema或源文件。
它不是通用任务执行器，不创建production lease、manifest、receipt或正式运行授权。

## 请求、所有权与事务

初始化拥有assembly、declaration和运行参数的私有副本。header绑定normal及source execution全部外部pins、
spec/budget/实际scale、配对声明、源路径、规范store路径及目录身份、源码/旧lease源码、Python/SQLite版本。
当前normal输入及执行身份必须与header一致，操作前复核；源码或请求漂移拒绝继续。
目录须为本地fixed NTFS且名称以`_non_authoritative`结尾；拒绝reparse及多hardlink journal文件。
create要求新目录；失败留下的部分文件保留，不能通过清理或覆盖冒充正常初始化。

同一目录使用non-inheritable字节锁与同进程registry；每次SQLite连接为DELETE/FULL、foreign_keys=ON，
核application/user version、精确schema、metadata及完整性。范围为同一规范目录的合作进程，
不是跨复制目录全局唯一性或对恶意目录替换的安全保证。

执行顺序为：检查unused → intent独立事务COMMIT → 新连接读取intent → 调用来源绑定内核 →
完整result独立事务COMMIT → 新连接核结果摘要。intent和result均为单行、仅一次。
事务失败、BaseException或进程退出后，已提交intent保持；只要存在intent就禁止再次execute。
进程死亡释放OS锁，但重新取得锁不代表调用没有发生。

## 可观察状态与重新打开

| 状态 | 已知内容 | 允许行为 |
|---|---|---|
| unused | 完整header，无intent/result | 在完整身份检查后调用一次 |
| unresolved_intent | intent存在，无完整result | 只核查；不重试、不猜零调用或不可行 |
| returned_record_unreplayed | 完整序列化result已提交且内容摘要一致 | 只核查；不恢复执行、不升级科学认证 |

所有者尝试写intent后即在内存中poison；即使该操作抛错，同一实例也不会再发起调用。
若进程在intent事务之前退出，重新打开时确实无intent，unused可继续一次；这与未决intent严格区分。
重新打开要求独立保留的genesis或当前head。genesis可用于核对结果提交但响应丢失的单次链，
不会解除已有intent的禁止重试门。目录/数据库复制、schema/header变化及结果摘要损坏拒绝核查。
create模式显式拒绝expected_head，避免静默忽略调用者传入的旧head。
独立保留的current head能检测result及其内部摘要的自洽改写；genesis不绑定尚未知晓的后续结果内容，
因此以genesis核对丢失返回仍只能得到未重放诊断，不能作为结果真实性认证。

`inspect`返回完整结果identity与存储摘要，不反序列化成owned solver对象或执行游标。
它核对JSON canonical bytes及完整encoded result摘要，不重审数值模型，也不认证原生调用来源：
`numerical_evidence_replayed=false`、`native_execution_authenticated=false`、`formal_result=false`。
这些flags即使内部求解成功也不改变；普通摘要不是签名，攻击者一致改写全部数据库与摘要不在认证保证范围内。

## 保存与资源边界

result使用`continuous_grid_normal._encode`完整保存SourceNormalExecutionResult及内嵌raw/witness；
另存其identity并验证wire编码与原identity对应。原source/kernel组件的flags保持原值，
不能把外层事务日志能力写回成它们自身具有持久化监督。
`max_record_bytes`显式限制完整result记录（含封装）的UTF-8字节数，超限时不写入部分result，intent保持unresolved。
该门不包含SQLite页/journal、header/intent或整个目录，也不是磁盘预留和强制进程内存上限。
代码不清理超限/失败目录。SQLite FULL是软件事务合同，进程退出测试不等于断电或硬件持久性认证。

当前execute仍是同步调用；独立进程监督和normal数值记录重放尚未接入。
该日志不能单独授权真实规模pilot、当前调度或四臂正式实验。

## 监督原语复用核查与下一项

只读审查发现旧`activation_transport_v4`的`_process_creation_time_ns`及
`sample_child_private_commit_bytes`没有为OpenProcess/GetProcessTimes/GetProcessMemoryInfo/CloseHandle声明完整ABI，
且采样分两次按PID开句柄，存在64-bit HANDLE与PID重用窗口，不能直接作为新normal监督器的所有权证据。
`activation_transport_v5`采用轮询，缺少父死亡Job保护；其8/2GiB/5秒常量属于旧冻结合同。
采样最大值不能称lifetime峰值，child_exited也不证明成功结果。
这些是新normal复用审查的缺口记录；旧冻结源/结果未修改，未由此推断旧科学结果或不可行结论。

下一实现应采用显式wintypes原型与同一个保留HANDLE完成身份、采样、终止和等待；
在worker释放执行前建立Job及父死亡保护，把sampling门与硬内存门分开。
worker可持有本store，父进程验证退出与持久化结果；现阶段没有这条进程链的完成证据。

## 验证记录

独立只读pre-seal最终19项targeted通过（26.06s，exit 0），覆盖tiny单次原生调用、跨进程锁、
四个真实`os._exit`窗口、intent readback失败、丢失commit响应、完整record超限、目录复制/hardlink/schema漂移，
以及独立current head与genesis面对自洽改写的不同保证。
创建模式静默忽略expected_head的finding已修为调用前拒绝；限定范围无开放实质finding。
子进程崩溃测试使用合成返回，不运行真实网络或长solver；tiny原生调用仅1秒/1线程。

主线程最终相关回归55项通过、1项deselected（55.94s，exit 0）：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_store_v1.py tests/test_rq2_source_normal_execution_v1.py tests/test_rq2_episode_store_v1.py::test_close_releases_handle_even_when_unlock_raises tests/test_rq2_episode_store_v1.py::test_hardlinked_store_files_are_rejected tests/test_rq2_episode_store_v1.py::test_real_junction_store_path_is_rejected -k "not real_pinned_h25"
```

未重复来源层未改动的真实H25核查；该项上一轮的独立103.14s证据仍只针对来源重建，不是本store的真实规模运行证据。
源码SHA256：`a79d766c08970875e8b65e5afc30ee7288d98bcc88a5474e9b5d7f7eace754f4`。
测试SHA256：`1bf9dd14f30d5001a40c0c8ee3dc7a45e182107b784996b0f11ea86331c5df88`。
旧episode_store仍为`872f32a632c83b084139973d7aa38249dfc1099dea14e447902c23429873af8b`，
source execution仍为`56a59908c99b5da24047bdd4c93478da6576b9224ca91e2994bc60cad79d57cf`。
进程核查、diff及新文件空白检查通过；未清理仓库、未改变旧冻结源或结果。
本审查是non-authoritative pre-seal findings闭合，不是official verdict、receipt、seal或运行授权。


## 2026-09-20 Normal worker 与一次性日志连接

新增`normal_worker.py`，已把显式输入/运行pins、受限环境、挂起Job worker与原normal_store连接：父目录排他、request及launch intent持久化、worker exclusive claim、normal intent/result日志、整Job静默后parent readback。normal_process draft补同线程校验、显式环境、Job总commit与quiesce。
worker正常退出且有完整记录仅标returned_record_unreplayed；零退出无结果、超时、中断和提交后异常退出均不升级成功，也不自动重试。下层normal_store/source execution/kernel及旧冻结transport未变。
主线程process+worker+store相关回归68项通过（57.92s），含tiny 1秒/1线程HiGHS、三类intent/result崩溃窗、worker重复claim、环境漂移及未静默禁止读结果。正例来源边界为明确synthetic stub；固定worker入口另验证真实来源缺失拒绝，未执行RTS求解。
下一项为持久化normal结果的独立数值重放；系统commit储备、父进程/整个任务资源与磁盘验收、真实规模normal/current/四臂及科学注册门仍开放。详见`docs/model_spec/rq2_normal_worker_v1.md`。本轮非正式开发，不产生seal/receipt/正式运行授权。
