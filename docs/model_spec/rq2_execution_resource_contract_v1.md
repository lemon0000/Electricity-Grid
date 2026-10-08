# 完整串行任务资源声明合同

状态：DRAFT_NONAUTHORITATIVE。实现`execution_resource_contract.py`，依赖已审查的`execution_workload.py`。本合同补显式任务清单的资源算术，尚未连接selector、episode或进程监督器；不改变旧短开发budget类型及其上限。

当前接入状态（2026-09-28）：下文初始开发记录保留。`scale_selector.budget_for_hour`已从完整声明导出预算；scale episode已接单任务envelope和采样检查。完整计划与实际episode的重新绑定、外层监督及全程成本仍未闭合，见末尾验收矩阵。

## 声明与检查

每个normal和episode必须恰好有一个`TaskEnvelope`，包含wall上限、非solver时间预留、Job commit上限、归档字节、scratch字节、线程及模型变量/约束上限。字段均为显式正整数；缺项、布尔值、非整数及非正数拒绝。完整任务清单、各臂TimeLimit及所有资源声明在输出中保留，能够从返回声明重建同一报告。

每个episode的调用按完整UID阶段计入，不借用可能提前停止的臂释放预算。`non_solver_seconds`须包含来源准备、构模、加载、审计、归档、回放、终止/静默，以及solver/interface超过TimeLimit的余量。它目前是调用者声明，不是实际耗时测量。以下检查只证明声明之间的关系：

| 检查 | 声明算术 |
|---|---|
| 单任务wall | `reserved_solver_seconds + non_solver_seconds <= max_wall_seconds` |
| 总wall | 所有task的wall上限之和加controller自身预留，不超过总上限 |
| 追加commit | 最大task Job commit加supervisor追加需求及reserve，不超过总声明 |
| 追加磁盘 | 所有task的archive和scratch之和加reserve，不超过总声明 |
| 线程 | 每task声明不超过总线程上限 |

内存的max聚合依赖一次仅一个Job存活、前一Job静默后才开始下一任务。跨任务保留在supervisor内的对象也必须纳入其追加需求。不能将此合同用于重叠运行、并行四臂或未退出的worker。磁盘保留所有生成文件和scratch，不依赖自动删除；现有原始输入与旧成果也不得清理以兑现预算。真实多卷路径绑定、卷内需求汇总和可用空间检查须复用已有`normal_resources.py`能力接入后继监督器，当前总字节比较不证明任一具体卷有空间。

`controller_seconds`是各task wall以外额外预留的串行监督开销，不用于补足某个不足的task wall。`max_threads`是将来每个原生solver请求的线程数上限，不是整个进程树的线程计数或实际CPU并行度。

变量/约束和线程是待执行时核对的上限；本工具未构模或读取运行时spec，因此不认证真实模型规模、引擎线程请求或许可证容量。

## 返回与边界

结构错误抛出`ValueError`；预算短缺返回逐task或serial_plan错误，`declaration_consistent=false`。无错误只表示完整调用者声明在上述串行假设下算术一致。`whole_task_resources_verified`、`execution_authorized`和`formal_ready`始终false。

必须另外完成实际任务清单完整性、normal复用/来源、normal最优性、科学注册、资源测量、主机/卷绑定、硬进程监督及真实规模执行器接入。源码不调用solver、创建进程或生成执行许可。测试中的小字节上限和秒数是合成算术案例，不是H25运行推荐值。

## 执行接口的下一实现

真实规模selector需要独立的受审查预算类型及入口，不能把本合同对象传给旧`GridDevelopmentBudget`调用者。入口须从已核算的任务生成reference/actual阶段预算，真实构模比对变量/约束，保留完整request→L1→UID和每级锁定、赋值及残差审计。每次原生调用前持久记录intent，失败保留known/unknown调用状态，预算耗尽不得隐式重试。

episode再按明确依赖连接normal、reference及四臂actual，运行前绑定整个任务和进程/存储资源。当前normal最优性仍未满足，因此不能开始依赖其accepted计划的真实episode求解。入口实现可先用合成例及故障注入验证。

## 本轮验证

资源合同和任务核算组合42项通过（1.59秒），包括逐资源少1单位拒绝、单任务wall不足不能被总预算掩盖、Job内存取max与归档/scratch全部相加、缺失/重复task envelope、非法资源值、split错配及完整声明重建。独立组合复跑42项通过（1.58秒）；最终资源文件16项通过（0.10秒），源码及规格审查闭合，限定范围无剩余实质finding。git diff --check通过。未修改冻结代码/配置/结果，未启动solver或正式任务。

## 2026-09-28 完整执行资源验收矩阵

本表核对实际调用路径，不把已有合成模块重复列为待开发。证据来自`execution_workload.py`、`scale_selector.py::budget_for_hour`、`scale_episode.py`、`scale_episode_resources.py`、`scale_episode_replay.py`和`normal_task_process.py`。

| 对象 | 已有证据 | 尚缺的必要连接与验收 |
|---|---|---|
| 完整声明与实际窗口 | workload逐任务计数；selector工厂重算完整资源合同摘要；episode与offline现强制原始EpisodeResourcePlan，核对完整窗口、UID、split、normal输入身份、五role预算、envelope、累计调用/秒数及reserve | 当前关闭的是调用者声明与实际episode的内部绑定；完整研究清单、normal原始输入与声明范围的重新核验及normal复用/最优性仍缺 |
| 单phase进程 | selector controller有固定worker、启动记录、Job内存上限、停止后静默 | 复用这些组件；不重写selector或底层Windows Job实现 |
| episode父进程与所有子任务 | 父侧采样、嵌套Job、固定worker及持久execute/audit控制器已具短小例证据；预算投影覆盖父进程加inner Job | 真实规模预算、长任务接口适用性与最外层controller资源仍待验收，不能从短例提升完整资源认证 |
| 完整wall | 每phase以及episode采样计时；已有轮询deadline终止原语 | `TaskProcessBudget`仍拒绝wall>3600秒；H25/158 UID的19900次调用即使每级预留1秒也超过该上限。完整窗口需要显式全任务预算接口，不得静默提高旧cap或拆小时改变事务/未知中断语义。轮询停止不等于OS硬wall quota |
| 独立离线audit | 已有完整输入/phase/跨小时纯回放，独立audit worker在外层Job内验证且归档hash不变；两phase父事务及独立预算分解已接入 | 真实规模加载、重算、输出和关闭成本仍须验证；不得由“零solver”推导无需wall/commit/disk预算 |
| archive/scratch与宿主 | 每phase及父metadata预留、保留scratch累加、volume headroom工具、写前检查 | 完整清单须纳入normal、episode、audit及父启动/结果元数据，绑定实际卷；发布前采样不覆盖最后写入/关闭，磁盘仍无硬quota |
| 来源和科学条件 | 公开来源及normal/四臂开发证据存在 | 声明算术不认证normal复用、真实normal最优性、参数身份、风险分母或右删失；这些保持独立科学/数据门 |

原始资源声明绑定已接入episode及离线核验，细节见`rq2_scale_episode_resources_v1.md`；固定worker已具短合成证据，见`rq2_scale_episode_worker_v1.md`。下一项在同一声明下复用既有Job组件接入持久父控制器，覆盖启动意图、父进程、最终发布/关闭及独立核验成本。总预算须覆盖父进程与子任务同时存在的资源，而任务间仅在静默确认后使用max聚合。开发时先以明确的小例证明连接及失败语义，再决定真实规模预算；这里没有批准长运行或调整gap/残差阈值。

上述持久父控制器现已实现并完成限定pre-seal，见`rq2_scale_episode_controller_v1.md`。下一项集中核对真实规模声明与3600秒开发接口的适用冲突及运行性证据，保留已经验证的两phase事务；完整资源、科学/数据及正式运行门继续开放。

嵌套验证仅使用pytest临时目录和短Python子进程，无solver。首轮合成父进程256 MiB上限在导入依赖时触发MemoryError；改为测试专用768 MiB process/1 GiB outer Job并固定数值库线程后，两个嵌套案例通过。该观察说明父侧加载成本不可漏算，不提供真实episode内存容量认证。
