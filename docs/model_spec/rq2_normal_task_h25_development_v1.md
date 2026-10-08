# 真实来源 H25 normal 整任务短验证

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

本项核验已有真实来源与开发 controller 的端到端连接。沿用已核验的 H25 build-only 声明、RTS-GMLC 来源、训练配对及全部初始状态；初态、工作负荷到功率映射和配对仍属于 mechanism_assumption，不升级为实际历史观测。此次不执行四臂、current/episode、容量前沿或正式实验。

固定声明为 `configs/rq2_normal_task_h25_development_v1.DRAFT.yaml`，SHA256 `9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6`。该文件保存绝对输入路径、全部来源/执行/replay pins、目标、预算及显式环境。原 build-only 声明 SHA256 为 `8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d`；规模为 22275 variables / 28004 constraints。

顶层角色为 `declaration_role: development_execution_declaration`，用来区分执行资源设置与被引用的科学参数角色。原 pair/source 仍为 mechanism_assumption。

入口 `experiments/audit_rq2_normal_task_v1.py` 默认只做声明/身份与实时资源只读检查。只有显式 `--execute-development` 才调用原 controller；既有 target 不可重试、覆盖或恢复。入口必须提供外部 YAML SHA 与脚本 SHA，无 solver/科学参数 CLI 覆盖。caller metadata 打印实际声明、脚本及 controller/source-request pins，不构成生产 manifest 或权限凭证。

固定开发预算：HiGHS 1.15.1，最多一次调用、1线程、1秒；normal 内核 observed wall 60秒。execute/replay Job 各240秒、静默各3秒，两次 capture 各10秒、parent tail 20秒，总600秒。Job/process commit各768 MiB、父额外32 MiB、系统reserve64 MiB；父 lifetime peak working set上限512 MiB。archive272 MiB、两份scratch各16 MiB、diskreserve64 MiB；record16 MiB，report1 MiB。内存初始准入要求864 MiB可用commit，磁盘要求368 MiB。预算仅为此次开发验证，不是正式资源标定。

若准入、时间、内存、字节门或写入失败，保留当前状态，不放宽预算或换目录自动重跑。链路 completed 与数值 accepted 分开报告：unresolved record 不代表数学不可行；inconsistent record 表示工件/重放一致性问题。即使 accepted 被重放复现，native_execution_authenticated、whole_task_resources_verified 和 formal_result 仍为 false。

运行证据需同时检查两个 Job 的身份/退出/静默、两次 capture 完整 pins、报告 SHA 与三态语义。未完成阶段只能报告实际保留证据；不能由缺 result 或子进程退出推断原生调用次数。

## 准备验证

初稿 `D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_audit_rq2_normal_task_v1.py`：7 passed in 5.75s。测试仅检查 compact 声明、重复键/权限/额外字段/hash/controller identity/solver范围拒绝，不启动 Job 或 solver。

首次只读资源检查：target_exists=false，commit available=(10350985−9844463)×4096=2074714112 bytes，caller disk available=110233677824 bytes，observed_headroom_sufficient=true。该瞬时读数不预留资源，实际启动会重新检查。

角色元数据修正后的最终只读测试：7 passed in 4.78s。最终脚本 SHA256 为 `2fa8f84dc1dbe1d95e84c1d83f25c2fa0ec852384fd2279aecd212cc1d3480da`，controller identity 仍为 `934925d184803268737d5d04473e3dfc6005b4e20fe53c7977d3eedf6e020b86`。此入口允许外部 pin 声明，并非内置唯一科学协议；本次实际开发调用只对应上述 exact YAML/script bytes。

## Attempt 1 实际终态

独立入口测试：7 passed in 4.74s，限定 pre-seal finding 闭合。随后仅执行一次：

```powershell
D:/Miniconda3/envs/compute/python.exe -B experiments/audit_rq2_normal_task_v1.py --declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6 --expected-script-sha256 2fa8f84dc1dbe1d95e84c1d83f25c2fa0ec852384fd2279aecd212cc1d3480da --execute-development
```

日志：`results/logs/rq2_normal_task_h25_attempt1_non_authoritative.log`。实际 attempt：`results/tables/rq2_normal_task_h25_attempt1_non_authoritative/`。入口进程退出0表示返回了诊断；科学和任务状态必须读取实际 observation。

Controller 状态为 `unresolved_task_attempt`，stopped_phase=`execute`，error_type=`ValueError`，耗时25.562秒。执行子进程 PID44576，creation FILETIME134343826559101101，exit_code=1，reason=`child_exited`；整 Job 静默确认 true。87次 runtime samples，没有 host reserve/API observation error；最低可用commit1745952768 bytes，最低caller disk110233268224 bytes。

process peak commit805146624 bytes，Job peak total commit806359040 bytes，声明cap805306368 bytes。峰值接近声明上限只提示资源相关调查方向，不能从这个观测或exit1认证 MemoryError、特定限制触发或数学不可行。原进程原语不继承 stdout/stderr，日志中没有 child traceback，具体异常尚未识别。

已保留 controller request/intent/observation、execute request/intent/supervision/launch/claim/observation；没有 normal store、execute completion、capture pins 或 replay intent。solver_calls=null、call_count_complete=false；不由缺少store推断零调用。没有同root重试、换root重跑或预算变更。

独立证据索引：`results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/summary.json`，绑定22个实际工件/代码/配置文件，SHA256 `208c26d1dd57fc280eb83552b8492b4474a65b2815860bfa393695fdd69557d8`。保留源角色与所有 false authority flags。下一必要工作是受限零solver来源准备诊断，定位异常及内存峰值来源；实际 normal/replay/current/四臂成功门继续开放。

## 独立来源准备诊断（2026-09-21）

`experiments/diagnose_rq2_normal_prepare_v1.py` 使用同一已绑定 source request，只调用 `prepare_task_inputs`。在子进程内禁止 create_solver、run_normal_only、run_source_normal；不调用 normal controller/store 或恢复原 attempt。root 必须是原 attempt 的不同同级目录，已有root拒绝。768 MiB process/Job cap与原reserve保持；phase117秒、静默3秒。初态/源数据/参数/源码均沿用旧pins。

parent 预存 request/intent/launch；child核PID、creation FILETIME、argv、环境、root及请求身份。来源组装、绑定内部重新组装及返回共有8个固定成功阶段；失败只保留已提交前缀。每个诊断文件最多16 KiB，最多16个阶段文件，保存异常type与最多8帧位置，不保存message或locals。phase失败与失败记录保存失败分开，原异常继续传播。

Job静默后parent复核观测、阶段、source/assembly/input/binding pins及5项精确float计时，生成与observation SHA绑定的summary。零退出而缺prepared、阶段缺失/乱序、超时、身份/权限错配均unresolved_probe。stage只是最近成功落盘边界；本次probe异常不追认attempt1异常或内存限制因果。

开发测试从6项异常/solver guard扩大到parent/child和阶段/计时/旧attempt目录保护。最终probe+薄调用入口相关回归32 passed in3.33s。probe source SHA256 `dbb9b50580afc07cbad8ce98c51ca68b2ac3a274dbeb434c803f1e6041ce5b42`；test SHA256 `981ad0bd2b141b04b2378bc2f36eddab4ba09488994e26344f5c6e33e66cd7cc`。实际probe结果后续按终态记录，不能由测试推断真实来源成功。

独立受影响路径14 passed, 11 deselected in3.41s，此前全targeted24 passed in2.88s；限定finding闭合。随后执行一次真实来源probe，root为 `results/tables/rq2_normal_prepare_probe1_non_authoritative`，日志为 `results/logs/rq2_normal_prepare_probe1_non_authoritative.log`。命令使用上述probe SHA、原YAML SHA、原audit脚本 SHA，`--diagnostic-root` 指向该同级目录，显式 `--execute-development`。

实际结果为unresolved_probe：PID5056/creation FILETIME134344408684897783，11.016秒后exit1，整Job静默true。52次runtime samples无reserve/API error，最低host commit余量16577224704 bytes。process/Job峰值分别805158912/806350848 bytes。已提交阶段仅before_prepare、source_assembly_enter；没有prepared。failure捕获本次probe的MemoryError，8帧均位于continuous_grid_normal.py，路径为normal_input_identity（98行）→_digest（68行）→_encode（56/50/54行）。

这是来源身份编码期间内存不足的直接诊断证据；全树_encode临时对象是下一优化对象。它不证明原attempt1具有相同异常，也不认证Job cap是唯一原因，不构成数学不可行或资源认证。probe工件、日志和代码等13项绑定在 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/prepare_probe1_evidence.json`，SHA256 `6ca5753bd474f017bfc52ec70f601f450469ce3f610859fe1a8689c52bf45bdf`；原22项证据哈希仍保持。

后继先差分验证独立流式编码原语，保留旧normal源码及输入/依赖身份。旧normal_input_identity还绑定自身源码hash，不能用原地修改旧_digest的方式静默更新现有pins。流式原语尚未接入执行链，也未证明H25在同资源预算下完成。


## 2026-09-21 真实 H25 流式来源组装验证完成

独立流式来源候选已取得真实数据证据：probe2保留完整8784小时RTS数据，25小时请求对应raw0..24/source1..25；normal内容摘要d9959966…与旧assembly内容reference626f7dbe…均复现，新assembly身份689ac1bc…独立记录。source阶段8.862秒，进程10.89秒exit0、Job静默true，51次采样；process/Job commit峰值339828736/341061632 bytes，低于原768 MiB cap，working-set峰值362663936 bytes，无reserve/API error，solver_calls=0。机制初值与workload-power映射标签保持，不转为真实观测。

先前probe1在来源开始前exit1；只读复算定位到环境dict插入序导致父子进程身份不同。保留v1/probe1全部字节，v2只修复环境指纹重建并验证实际键值，独立55项通过。完整证据与边界见docs/model_spec/rq2_source_normal_stream_v1.md；probe2 root为results/tables/rq2_stream_source_probe2_non_authoritative，13工件hash索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_source_probe2_evidence.json。

下一必要工作已从“验证来源流式编码”推进到后继power/pair binding与prepare整链接入，须保留独立实现pins并核验重复重建/快照的资源。此次只证明一次来源候选内容复现与受限进程观察，未证明完整prepare、normal执行/replay、current/四臂资源、完整恢复或右删失口径；科学注册与正式启动门继续开放。原22+13+11项历史工件及新13项bytes/hash均核验一致，未清理仓库。
