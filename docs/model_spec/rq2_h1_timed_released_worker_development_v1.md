# H1 released timed worker development v1

状态：DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT；R3，根代理唯一写入。

`experiments/h1_timed_released_worker_development_v1.py` 将新 request schema
连接到既有 `OwnedWorkerHour`。它是 API，没有 CLI 或生产 controller。
真实 adapter 调用需要具体 successor 包、Job/resource 监督及新的明确 native 授权。

## 验收合同

- request 的 canonical bytes/SHA、implementation closure、parent declaration、anchor、
  pending arguments、input receipt、固定 route 和全部 false flags 必须精确匹配。
  root 必须显式 `_non_authoritative`；cwd/TEMP/TMP、环境、argv、budget/host
  由旧 `task_process_identity` 重算；development wall ceiling 为 300 秒。
- release/launch/child/initial observation 绑定真实 Windows PID/creation FILETIME。
  沿用旧 `DevelopmentNormalChild` suspended-create 的精确 process/Job handles
  `IsProcessInJob` 和不可继承句柄检查；worker 内读取的文件本身不证明 Job membership。
  此单元不新增或重做底层 Job 原语。
- exclusive `consumed.json` 写盘并稳定复读后，才通过固定 parent snapshot 重建
  source/carry packet。消费后任何失败不重试、不修补、不恢复请求。
- request、release、launch、child、initial、consumed 保留首次已验 SHA 的完整 bytes
  与文件身份 view，重建后、worker 前、发布前后复核。额外 launch 字段拒绝。
- 内部创建 owned worker；要求 exact live Completion、成功 owner 状态及本地 clock
  binding，然后重新验证全部 hour science，并重新打开 parent snapshot 核验输入。
  全部 worker metadata、lock 与 hour science/commit/timing/projection 目录及文件
  snapshot 包围最后 inspection、source 复核和结果写入，拒绝晚漂移。
- worker_result 绑定 request/consume/input receipt、实际 PID/creation、worker
  binding/terminal/implementation 及 projection SHA。返回前重新按 SHA 读取结果。
  结果文件存在不能证明成功返回或正常退出；最终确认失败后文件可能保留。
  后继 controller 必须检查实际 exit0、whole-Job quiescence、完整输出和 source，
  才能考虑 parent outcome。当前没有该 parent acceptance 路由。

## 验证范围

测试专用 isolated Python launcher 在真实短 Windows Job 中安装 synthetic loader
和 synthetic adapter，保留真实 PID/creation/QPC，完全禁止真实 solver。
三阶段成功后尝试重复消费必须失败；其余覆盖身份错误、既存 consumed、release 与
science 晚漂移、worker 成功后的 result write 失败。parent journal 保持一条 intent、
pending_unknown，没有 parent outcome。附加 canonical/size/同长度恢复 mtime 测试。

另覆盖 consumed 完整写盘后抛错：保留 consumed，source/worker 均不启动；
worker_result 完整写盘后抛错及最终按 pin 复读失败：可保留完整结果，但 execute
不返回 pin、child exit 非零、parent 保持 pending。三种情况再次消费均 FileExistsError。

这些证据只证明该测试组合。尚无实际 native Job、232-stage/192-hour 全支持覆盖、
跨进程 clock containment、完整 phase/observer/startup/exit/return-tail 计量。
2440 秒 non-solver 分项预算仍未证明。

## 存储与权限边界

consumer 新增 `consumed.json`、`worker_result.json`，各 `CAP=262144 bytes`，
合计逻辑内容上限 524288 bytes、2 files；没有额外目录。此条件界排除既有 owned
worker/hour 子树、caller 创建的 request/launch/child/initial/release/observation、
root lease、scratch/logs、外部 source、内存及文件系统分配。测试 256 MiB Job-root
及 8 MiB scratch demand 是小型合成用例预算，不是全研究资源准入。

`collector_integrated`、`independent_hour_jobs_integrated`、`worker_job_membership_verified`、
`cross_process_clock_bridge_verified`、资源/正式/授权 flags 全 false。
完整资源/DAG/manifest/common Rref/A/LB/UB、封存和新的 official 独立审查仍待完成。
