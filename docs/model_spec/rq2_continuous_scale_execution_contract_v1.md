# 连续真实规模执行合同草案

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，设计与验收清单。
本文件不注册科学参数、不扩展现有开发预算、不授权运行，不生成生产工件。

## 当前整任务监督实施边界（2026-09-20）

最新开发已完成 normal 数值重放、host 余量观测、固定的小型声明来源准备入口
`normal_task_inputs.prepare_task_inputs`、任务进程监督原语与 `normal_archive_capture` 有界归档读取。
后两项分别通过 34/31 项独立 targeted，限定范围 pre-seal findings 闭合；后文保留历史进展记录。
`normal_task_worker` 已补 compact request 和固定 execute/replay 分支，独立 26 项 targeted 通过。
它验证 controller 预存的 intent/launch 后才 claim；completion 仍是待 controller 核验的声明。
`normal_task_controller` 已实现开发态顺序 supervisor，连接两 Job、独立双 capture 和完整报告核验；
准确合同与本轮验证记录见 `rq2_normal_task_controller_v1.md`。真实来源端到端正例与完整资源证明仍开放。
2026-09-21更新：H25首次整任务停于execute；独立零solver prepare探针在同768 MiB cap下
捕获normal_input_identity→_digest→_encode的MemoryError。独立流式来源候选现已在同768 MiB cap下
完成一次真实H25内容复现（完整8784小时数据，source8.862秒，Job commit峰值341061632 bytes，零solver），
并分别绑定旧内容reference和新implementation/assembly身份，见 `rq2_source_normal_stream_v1.md`。
后继power/pair binding及prepare整链现已接入并通过tiny/故障差分与独立审查，见
`rq2_normal_task_inputs_stream_v1.md`；真实H25完整prepare及重复重建现已在原768 MiB上限内一次完成，
prepare31.440253秒、Job commit峰值476151808 bytes，零solver。normal build/audit与同步数值执行流式后继
已通过242项相关回归，见 `rq2_normal_execution_stream_v1.md`；来源执行与pinned声明入口后继
已接通tiny合成完整prepare/source/binder/native链，见 `rq2_source_normal_execution_stream_v1.md`。
一次性声明日志后继已实现，intent先于prepare，完整nested result持久保存，见
`rq2_normal_declared_store_stream_v1.md`。嵌套证据独立replay后继已实现，见
`rq2_normal_declared_replay_stream_v1.md`；归档捕获的流式schema后继已完成，见
`rq2_normal_archive_capture_stream_v1.md`。固定流式worker已接入，保留prepare后求解前的运行态检查，
见 `rq2_normal_task_worker_stream_v1.md`。流式controller的三层报告门与两Job监督已接入，
见 `rq2_normal_task_controller_stream_v1.md`。真实H25首次流式全链已完成execute/capture/replay/
recapture，274.39秒、两Job正常退出且静默，峰值均低于768 MiB；诊断数值仍unresolved：
1秒求解无解返回，normal总耗时67.5576574秒超过既定60秒门，未取得有效assignment/witness。
完整证据见 `rq2_normal_task_stream_h25_development_v1.md`。2026-09-27零solver组件测量已完成：
完整input identity两次各约10秒，单次build10.61秒且包含内部校验；Job86.125秒正常退出且静默，
峰476012544 bytes。见 `rq2_normal_component_cost_probe_v1.md`。身份编码性能后继已完成真实零solver
对照，旧9.83/9.79秒与新6.87/6.75秒的四个摘要一致，Job98.625秒正常退出且静默；详见
`rq2_identity_stream_fast_v1.md`。独立fast normal模型/内核及来源/声明入口已接入并通过小型验证，
全部复核位置和数值/资源门保持，见`rq2_normal_execution_stream_fast_v1.md`。新类型的持久化日志、
独立replay、有界capture和固定worker后继已完成小型验证，见`rq2_normal_persistence_stream_fast_v1.md`。
当前前置工作为controller连接，然后验证真实H25和有效normal assignment；
组件改善不证明原60秒门已过，也不证明current/四臂全任务资源充分。
现有实现采用以下连接边界：

1. Controller 只接收有字节上限的声明路径、外部 SHA/pins、typed budgets 和显式 environment。
   完整 RTS 数据读取、组装、深拷贝及编码都在受限任务子进程中完成。
   旧 `normal_worker.supervise_normal` 在父进程先 deepcopy/encode/创建 store，不能直接充当这一入口。
2. 已实现的固定 worker execute 分支负责来源准备、原 `DevelopmentNormalStore` 创建与单次 execution/归档。
   使用新 task-level 时间预算，保留旧 process/worker 的 60 秒限制及 numerical kernel 的 30/60 秒限制。
   不用普通可变文件作为可信 phase 心跳；首版可为准备到归档设置一个完整 phase deadline。
3. 第一 Job 全部静默后，controller 独立保留当前 head、record SHA 和 result identity，再启动独立
   replay Job。固定 worker replay 分支已能从同一小型声明重建来源，调用原 `replay_normal_store` 并持久保存诊断，
   controller 已连接固定顺序，并在 replay Job 静默后再次捕获归档、比较全部 pins。
   不构造 assembly 的受限 wire-level pin 捕获入口已接入；它只取得不透明 lineage pins，
   全部输入/数值语义由 replay 重建核验。不能把 execution child 的成功字符串当作数值验收。
   `claimed_result_identity` 仍只是外部声明，capture 不证明其与内容一致，也不证明 Job 静默或声明来源。
4. 执行与 replay 严格顺序，启动时的额外 commit 需求按并发峰值确定，不能把两阶段 Job cap 相加，
   也不能把同一 Job 的 process cap 再加一次。Controller 自身开销要有独立预算。
   启动时检查 additional+reserve；运行中采样只比较已绑定的 reserve，避免把已分配资源重复计入追加需求。
5. 固定采样、完整任务 deadline、API/身份失败均须连接同一保留 HANDLE/Job 的停止与静默确认。
   停止保留 phase intent 与 known/unknown 调用状态，不重试、不推定数学不可行。
   应同时记录 Job peak 与 process peak；非零退出不能单独证明某个具体资源限制曾触发。
6. 输出与专用 scratch 的 cwd/TEMP/TMP、归档/SQLite journal/诊断日志有明确预算和路径身份。
   余量采样及 payload 上限不是 task-scoped 物理磁盘配额；无实际配置与验证的配额设施时，
   只能声明采样式停止和写失败保留语义。写满、COMMIT/fsync 失败时连事后诊断也可能无法保存，
   必须保留先前已提交的 intent，不以“诊断缺失”推断未调用。

controller 测试已覆盖 prepare/normal intent/result/replay prepare 四个父死亡窗口、已有目录拒绝、
专用 scratch 与文件预算、伪造观测/摘要/报告、重放后归档漂移、写入和 deadline 故障。
底层 process/worker/store 的故障测试继续复用；这不代表所有整任务故障组合或真实资源已验证。
以上是 non-authoritative 开发接线，真实来源整任务、资源验收与正式运行授权仍需分别完成。

## 当前依赖与实现边界

`pair_normal_binding`已把来源配对的逐小时baseline绑定到normal输入。最新机器记录为
`results/tables/rq2_source_pairs_v1_non_authoritative/normal_dynamic_verified_non_authoritative.json`，
SHA256 `8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d`。
H=25构模为22,275变量/28,004约束，solver_calls=0。初态是显式机制声明；构模成功未证明初态或整窗可行。

现有调用链有三个独立层次，后继必须分别记账：

| 层次 | 现有入口/证据 | 尚需补齐 |
|---|---|---|
| normal全窗 | `continuous_grid_candidate._solve`、`audit_normal_assignment` | 真实规模的单次normal求解、完整赋值及原模型审计 |
| 当前小时reference/actual | 两个selector的`_stage_model`、`_audit_stage` | 对全部UID阶段的真实规模准入与执行支持 |
| 四臂整窗 | `EpisodeSession`、`episode_store` | 包含前置normal与非solver开销的整任务资源、停止及恢复合同 |

`EpisodeSession._requirements`只计算逐小时reference和actual的原生调用预留，不包含前置normal，
也不包含构模、加载、源码校验、赋值重审、归档及重放。`max_reserved_solver_seconds`是各次TimeLimit之和，
不是进程wall-clock上限；`max_threads`也不是内存限额。不得把这三个字段写成完整资源保证。

## 后继执行路径

第一项实现应是独立的normal-only开发入口，接受外部绑定的完整动态normal输入，
只产生原生求解证据与`NormalAssignmentWitness`。不需要先构造reference/actual origin，
也不把旧`run_short_grid_candidate`的独立小时corrective输出当成连续实际dispatch。
求解后分别保存assignment有效性与数值最优状态；用于后继自动连接的接受条件沿用旧candidate的
`normal.optimal`且完整witness无错误，不能把仅有可行incumbent升级为已接受normal计划。
`prepare_normal_information`自身只校验赋值可行性，后继入口仍须保留这层更强的求解接受门。
该入口的规模合同需独立于旧`GridDevelopmentBudget`；旧类型、上限和调用者保持原义。
新入口须先完成无solver准入和小例故障验证，再安排明确预算的真实规模pilot；本草案没有选择或授权该pilot。

取得完整赋值后，必须由`prepare_normal_information`重审并形成独立信息声明，
再经`current_grid_information`、事故披露、共同请求、四臂小时事务连接。
前置normal的预测/发布时刻是机制声明，不能把全窗输入可访问性解释为实测预测准确性或因果认证。
normal未取得可用赋值时，后续current/selector/episode没有合法输入，应停止该依赖链。
连接还需显式`PlanInformationDeclaration`、`CurrentGridConditions`及prepared audit身份、逐小时`DisclosureStep`，
以及reference/actual各自incoming边界的generation与base availability；不能把normal末态当作首小时origin。
这些初态的物理/来源审计不能由通过normal全窗赋值检查替代。

## 资源声明与准入义务

后继声明必须外部绑定输入/源码/求解器版本及options，不接受由执行现场自算身份再自比较替代外部pin。
所有必需资源项在运行前有值；未测量或未声明保持unresolved，不能使用无限预算或默认正式准入。

| 项目 | 必需字段及检查 |
|---|---|
| 实际模型 | 原模型及每类selector最终阶段的variables/constraints、小时数、完整UID表；阶段计数来自实际构模 |
| 原生调用 | normal次数、reference阶段数、每臂actual阶段数、完整计划窗总数；重试/确认调用必须另行预留 |
| 求解时间 | 每次TimeLimit及总预留；不得在已用完后借停止臂预算重启同一未知调用 |
| 进程时间 | 独立wall-clock预算、构模/审计/归档计时、终止与未完成状态规则；原生TimeLimit不能替代 |
| 内存与存储 | 峰值RSS和证据大小的测量方法、运行上限、磁盘不足/写入中断的停止及保留规则 |
| 引擎容量 | 本次模型/当前许可的原生容量证据；已安装引擎和旧冻结模型容量记录均不能代替 |
| pilot选择 | 预先固定输入、重复次数、机械选择规则与允许读取的性能字段；不能依据目标值挑引擎/线程 |

保持全部n个UID阶段时，每小时调用为`(n+2)+sum_arm(n+1)`。
四臂n=158时为796；H=25为19,900，加一次独立normal为19,901。
这是无重试情况下完整路径的调用预留计数，不是实测调用数、耗时或成功保证。
训练容量搜索、多窗口、多参数cell、多seed及holdout还须按完整任务清单另行累计，不能把单episode预算称为全实验预算。

## 保持数学和证据语义

reference保留request→L1→UID顺序；actual保留固定实际功率、L1→UID顺序。
每一级保留旧gap、LB/UB、残差、目标锁定、assignment、来源与状态审计；数值词典序不改称精确词典序证书。
失败级之后没有selected state，合法业务候选不能在网侧未完成时单独提交。

当前每一级重新构模，`_solve`加载后再独立构建canonical模型，selector还进行物理与锁定重审。
复用模型、warm start或缓存都必须验证结构、数值、独立审计和来源漂移检测等价，不能只凭目标值接近验收。
减少fixed/disabled UID阶段也需要对当前模型约束和每个事故状态证明目标恒定，
并明确其审计记录、锁定、最终assignment与重放身份；dispatch_mode标签本身不是省略证据。
有限容差下数学冗余不自动意味着旧数值执行轨迹或记录等价。
若更改选择机制，则需要新的策略身份与四臂公平性论证，不能覆盖旧selector与旧结果。

## 中断与状态验收

调用前持久化intent；返回与外层发布分别记账。intent已存在但返回缺失仍为unknown，
不能由timeout、进程退出或空结果推定零调用、数学不可行或允许自动重试。
保留已有known/unknown、未开始/未完成/已停止臂，以及reference、业务候选和actual的独立证据。
任何后继规模入口必须显式说明与`episode_store`本地合作进程排他及重放的连接，不能声称跨复制目录全局唯一性。

## 验收矩阵与推进顺序

| 顺序 | 交付与反例 | 通过后仅能说明 |
|---|---|---|
| 1 | normal-only输入/规模/资源外部pin准入；缺项、非有限预算、源码变化、超规模在native前拒绝 | 后继入口的准入合同已实现 |
| 2 | tiny normal原生正例；错误assignment、缺界、gap、来源漂移、create/solve/load异常；原规范审计与独立review | 小例执行与证据路径可靠 |
| 3 | 预先声明的真实规模pilot；记录容量、构模/solve/审计wall time、RSS、产物大小及失败状态 | 指定输入/配置的实际执行证据 |
| 4 | 完整normal见证→prepared/current来源绑定；不同初态、错小时、错baseline反例 | 当前网络输入合法，不等于全服务履约 |
| 5 | 全UID选择链及episode规模后继；外层回滚、unknown invocation、磁盘/超时故障、无solver重放 | 指定连续执行链及恢复合同成立 |
| 6 | 训练容量/固定策略绑定、完整恢复与风险分母、科学参数登记、seal与独立official review | 分别关闭对应门；formal run仍需明确授权 |

本轮只完成该设计合同。步骤1—6仍需各自代码/实验或注册证据。
既有公开数据中的归一化观测、benchmark派生值和功率/初态/配对机制保持分列；
缺失deadline、末端恢复、raw workload>1与耦合参数不能由资源合同补成观测事实。

## 本轮核验

独立只读sol_reviewer进行了non-authoritative设计核查，限定范围未发现实质设计矛盾。
核对normal接受门、current/origin依赖、全UID及19901计数边界、预算未覆盖项；未运行solver或测试。
主线程核对动态normal产物hash、旧candidate/episode源码hash及调用算术，文档空白检查与`git diff --check`通过。
本反馈只针对合同草案，不构成实现通过、official review、seal或运行授权。

## 后续实现进展（2026-09-20）

上述“步骤1—6待实现”是设计交付时的记录。后续已新增`normal_execution.py`独立normal短内核，
见`rq2_normal_execution_v1.md`：外部input/execution/实际scale pins、原生证据与完整witness接受门、
同步资源观测和unknown中断记账已有tiny/fault验证。
这只完成步骤1—2的数值内核部分；未完成来源绑定调用入口、独立进程与持久化监督、完整归档资源门，
也没有真实H25求解、容量pilot或current连接。旧预算及正式门保持不变。

后续`source_normal_execution.py`已完成公开来源与内核的前后绑定连接，见`rq2_source_normal_execution_v1.md`。
独立32项连接层验证及124项相关回归通过；真实H25验证止于kernel边界。
现在下一项为normal专用进程监督/持久化与完整资源验收，再取得真实规模normal赋值；上述历史“来源连接待实现”已由本项部分闭合。

`normal_store.py`后续已补同步normal的一次性intent/result日志、完整结果记录字节门和合作进程排他，
见`rq2_normal_store_v1.md`。记录状态仍为returned_record_unreplayed；独立进程监督、数值重放与真实规模验证未完成。
旧transport监控经复用核查存在HANDLE ABI、PID二次打开及父死亡保护缺口，新监督不能直接继承这些原语。


Normal进程原语独立pre-seal限定范围无开放实质代码finding；规格中崩溃窗口措辞已按实际注入位置修正。最终22项独立targeted通过（1.04s），源码与测试hash见`docs/model_spec/rq2_normal_process_v1.md`。后继worker仍须补请求/环境身份绑定、同线程或并发合同、整Job静默后读取工件以及资源/日志/数值重放验收；不能把进程原语测试升级为完整监督或正式运行通过。


## 2026-09-20 Normal worker 与一次性日志连接

新增`normal_worker.py`，已把显式输入/运行pins、受限环境、挂起Job worker与原normal_store连接：父目录排他、request及launch intent持久化、worker exclusive claim、normal intent/result日志、整Job静默后parent readback。normal_process draft补同线程校验、显式环境、Job总commit与quiesce。
worker正常退出且有完整记录仅标returned_record_unreplayed；零退出无结果、超时、中断和提交后异常退出均不升级成功，也不自动重试。下层normal_store/source execution/kernel及旧冻结transport未变。
主线程process+worker+store相关回归68项通过（57.92s），含tiny 1秒/1线程HiGHS、三类intent/result崩溃窗、worker重复claim、环境漂移及未静默禁止读结果。正例来源边界为明确synthetic stub；固定worker入口另验证真实来源缺失拒绝，未执行RTS求解。
下一项为持久化normal结果的独立数值重放；系统commit储备、父进程/整个任务资源与磁盘验收、真实规模normal/current/四臂及科学注册门仍开放。详见`docs/model_spec/rq2_normal_worker_v1.md`。本轮非正式开发，不产生seal/receipt/正式运行授权。


## 2026-09-20 Normal 数值重放最终开发验证

normal_replay 已补齐资源拒绝的精确计数、保存计时的 float 类型与偏序、lifetime peak 单调性、spec/budget/scale 编码类型，以及 admission/native/canonical 构模计时数量检查。保持成功标志并重算哈希的篡改反例也被拒绝；来源后检失败在来源恢复后仍保持 unresolved。
最终四文件相关回归 177 passed in 148.23s；独立 targeted 46 passed in 82.15s。限定范围 pre-seal findings 已闭合，完整命令和最终 source/test hashes 见 `docs/model_spec/rq2_normal_replay_v1.md`。旧 normal/source/store/worker/native replay 文件哈希保持。
以上支持 tiny 合成网络及显式来源 stub 的记录一致性，不认证 native 执行历史、资源测量或真实 RTS 求解，不生成 seal、receipt 或正式授权。
下一必要工作为整个 normal 任务的资源验收：父进程输入准备/归档/重放预算、系统 commit 储备、临时文件与归档磁盘边界及故障停止规则。已有 worker 的子进程 Job 限制和单条 payload 字节门不能替代这些项目；真实规模 normal/current/四臂、恢复/右删失及科学参数注册门继续开放。


## 2026-09-20 Normal 主机资源余量观测原语

新增 normal_resources.py 和 docs/model_spec/rq2_normal_resources_v1.md：固定 Windows ABI 观测系统 commit 与 caller-available 磁盘余量；明确追加需求/储备，同卷需求合计、储备取最大、采样可用空间取最小。外部 identity 绑定目录 dev/ino/volume GUID、预算与源码，前后检查；失败不返回 sufficient 报告。
相关 resources/process/store 回归 82 passed in 29.79s；独立 targeted 35 passed in 1.86s，限定范围无开放实质代码 finding。测试包括真实只读 Windows 调用和目录替换，以及模拟边界、配额可用量不足与 API 故障；没有 solver 或磁盘/内存压力运行。
本项仅补只读观测及声明比较，未接入 worker，未创建资源预留或硬配额。下一项是完整 normal 任务监督连接：内部固定调用 observer，覆盖输入准备、执行、审计、归档及重放，明确父进程与子进程预算、专用临时目录、持续观测/停止及写入失败保留规则；不能信任 caller-supplied observation。真实规模、科学注册与正式运行门保持开放，旧冻结代码、结果及未提交文件保留。
