# H1 timed Job controller and source parent development v1

状态：DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT；R3，根代理唯一写入。

本单元包括 timed_job_parent_v1、timed_job_snapshot_v1、timed_released_worker_v2、
timed_job_controller_v1（完整文件名均以 h1_ 开头、以 _development_vN.py 结尾）。
四文件共同 identity 绑定其精确字节及前序 released-worker v1 的完整依赖闭包。
旧 src、旧协议和旧开发证据不变。当前测试只允许合成 adapter；step 是 native-capable API，
真实调用仍需具体已就绪包、资源监督及新的明确授权。没有生产封存或运行许可。

## 协议和科学验收

1. SourceParent 复用 bounded parent 的 journal、anchor、逐小时 source/clock/carry 状态机；
   原 source intent/event schema 保持原语义，新的 parent declaration schema、implementation
   和 child_protocol 区分 timed Job reference。旧 Snapshot 不能解释新声明。
   新 Snapshot 的 MRO 使用旧只读 snapshot 输入算法及新 SourceParent child replay。
   PendingWorkerInput 保留共享输入协议；receipt 的 parent identity 绑定新的完整实现。
2. released worker v2 仅替换 source snapshot 与共同 implementation identity。
   所有其余函数与 v1 的 AST 等价（归一化旧 snapshot 引用后），保留原 once-consume、
   固定 bytes/identity、full science、写后失败和最后 pin-read 检查。
3. controller 在新小时 intent/anchor 后创建独立 suspended Job；绑定 request、launch、
   initial observation、child 和 release intent；复查固定视图后才 release。
   已有底层精确 process/Job handle membership、不可继承句柄和限额逻辑直接复用。
   TaskProcessBudget 的 development wall ceiling 为 300 秒，不能作为正式 H1 预算。
4. wait 后写 observation；只有实际返回的 typed observation 满足 exit0、
   whole_job_quiescent、峰值 commit/时限和无资源观察错误，才读取 consumed/worker_result。
   每份 worker result 都必须匹配请求、source receipt、PID/creation 和完整 worker pins。
5. child 的 reference.json 固定8份 Job record pins，绑定 parent identity、intent、
   source lineage 和确定的 sibling job 路径。fresh reader 检查记录、process identity、
   environment/host/budget、历史 intent anchor、完整 worker/hour science、映射和 projection。
   stored Job observation 只是条件证据，不能重建 live Job ownership 或 native authenticity。
6. controller 在 Job 退出后重新打开 source snapshot。完整 Job byte/identity view
   包围这一 source 验证、reference 创建、child replay、outcome 追加和最后返回；
   source 复核后、outcome 前和返回前均拒绝变化。reference 只包含引用，不复制 raw。
7. parent 每次 restore 都按 hour/source 顺序重放完整 Job child；只从已经完整重算的
   timed projection 中取批准转换后的 boundary，再调用 source._boundary 校验。
   不制造旧 H1HourReplayedProjection。原 generation witness、差值、映射、约束审计
   均留在原 worker/hour evidence 中；新 outcome 绑定其完整引用和 projection identity。
8. 任意失败 poison controller 的 parent，不重试、不接续。create-once root、exclusive
   consumed 和 pending child topology 保持单次执行。readonly reopen 仅解释当前完整证据。
   reference/outcome/anchor 已写成后仍可能失败；文件或 accepted event 的存在不证明
   step 成功返回，也不提供后续执行权限。无新 live 成功返回时不得按文件存在继续执行。
9. SourceParent close 先 detach 各 journal/anchor/root owner，再尝试关闭全部；
   controller/job lease 也使用 detach-before-close。关闭确认失败不能再次关闭旧 owner
   并影响后来取得 lease 的 owner。controller 禁止 copy/deepcopy/pickle。

## 验证矩阵

- 两个连续三阶段 synthetic hours：真实独立 Windows Jobs、实际 PID/creation/QPC，
  source/carry 变化、完整 outcome、只读 fresh reopen 相同。没有真实 solver 调用。
- 真实非零退出（包含 worker_result 已写成后 exit7）在父端读取 result 前拒绝。
- consumed/result 缺失与同长度恢复 mtime 漂移；worker inspect 返回后的 subtree
  晚漂移；controller 第二次 inspect 返回后的 subtree 漂移，要求 reference 前拒绝。
- observation/reference 写前与完整写后故障，outcome 写前/写后、anchor advance 后故障，
  wait 后 source/anchor 漂移、release 前 child record 漂移、Job lease 关闭后确认失败。
  observation-before/anchor-wait 使用真实 exit0 empty process 验证前置窗口；
  child-before-release 在 suspended 状态拒绝；其他下游窗口使用完整合成 worker。
  observation-after 特别要求完整 worker_result 已存在而父端未读取它。
- controller、parent root、journal、anchor 四种 owner 的固定 unlock 前/后故障、
  旧 owner 释放后新 owner 接管 registry ABA。所有异常后重复 close 不影响新 owner。
- schema 隔离、released v2 AST 等价和条件内容界检查。未改的前序科学原语不重跑。

## 资源范围和仍开放的门

每个 Job 的逻辑内容界由全部 stage 文件 caps、每 stage commit、hour header/terminal/
projection、worker两份metadata及一字节lock、8份各<=262144-byte Job records、
Job一字节lock组成。S=3 为105494530 bytes/81 files；S=232 为7977525250 bytes/
5119 files。每小时 parent child reference 另加<=262144 bytes、1 file、1 directory；
parent journal/anchor/outer leases 沿用旧类别另计。scratch/logs、FS分配、外部source、
模型及科学重放瞬时内存、完整生命周期wall均未纳入此条件界。

job_view 常驻的是8份有界record视图、worker metadata/lock及逐文件hash/identity/cap；
hour._snapshot逐文件读取后只保留hash视图，不常驻全部raw。8GB逻辑磁盘cap不能
解释为此view常驻内存，也不能证明实际 science replay/模型/序列化的峰值内存可用。
完整 host/disk/commit/time 资源准入仍未完成，新增存储分类必须纳入 successor 总预算。

当前只证明此开发组合，collector_integrated、independent_hour_jobs_integrated、
worker_job_membership_verified、cross_process_clock_bridge_verified、producer_coverage_proven、
native_export_coverage、instrumentation_coverage_verified、observer_overhead_separated、
component_budget_verified、resource_admission、formal_execution_ready、formal_result、
native_execution_authorized 均false。完整232-stage/192-hour支持、跨进程clock containment、
完整phase/observer/startup/exit/caller/return-tail、2440秒non-solver分项预算、actual reuse
DAG/manifest/common Rref/A/full LB/UB、封存及全新official独立审查仍待完成。
