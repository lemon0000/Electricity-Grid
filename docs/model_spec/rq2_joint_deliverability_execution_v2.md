# RQ2 联合服务可交付前沿 execution successor v2

## 1. 文档地位

本 successor 将已通过独立 R3 审查的 reference implementation v2 扩展为可在
执行机上使用的证据、持久化和恢复基础设施。科学定义仍唯一来自 sealed V5。

v2 是对 sealed execution v1 official R3 `REWORK` 的唯一聚焦 successor。v1
outer `1ec234a1279b1c5a09b2beedb66ec1dfffcda28ed4a024df44d7d47060c976d2`
及其 19 个成员保持不可变；v2 只修复 live sealed/draft validator 测试路径和
opened-gate 反例的非空洞断言，不改变科学协议、execution evidence schema 或
正式执行权限。

本候选不包含 activation wrapper，不接受正式运行参数，也不授权 46-cell、
1071-block、holdout、transport 或 bootstrap 正式执行。当前 dispatched grid
package、Windows runtime receipt、Gurobi 13.0.2 native replay 和用户正式授权均
缺失，因此 `formal_execution_ready=false`。

## 2. 权威链

successor lineage 先绑定并递归验证 sealed execution v1 outer 与 official
`REWORK` receipt。运行静态 authority 再由代码内部从 live bytes 派生：

1. V5 scientific outer 与 R4 PASS receipt；
2. implementation v2 outer 与 R3 PASS receipt；
3. `rq2_executor_v2.yml`；
4. power-system base manifest；
5. workload v3 manifest。

两个 outer 都递归验证 inner 与全部成员，不只比较 outer 文件本身。两个 review
receipt 还必须为`PASS`、绑定对应 outer，并保持 formal/result/claim/security
权限关闭。

调用者不能注入静态 trust root。v2 的四个公开 stage 入口保持硬关闭，统一抛出
`ExecutionBlocked`，不读取 authority、不构造 callback、不调用 solver，也不写
stage evidence。原因是当前`core.py`在模块加载时已经解析 implementation-v2
symbols，同进程内仅核对磁盘路径和哈希不能证明这些运行时对象未被预置
`sys.modules`替换。真正可写的公开执行面必须由后续 activation successor 使用
stdlib-first fresh process，在导入 project/science modules 前验证完整 closure，
并在导入后核对 module `__file__`与 digest。

本 v2 保留的私有 execution helpers 不接受 repository root、execution outer digest
或 dispatched-grid manifest digest；repository root只能由当前已加载的`core.py`
位置推导。authority helper还核对 live `core.py`与 sealed implementation path 是
同一普通文件，alternate-root package不能作为 execution authority。其固定路径
`configs/rq2_joint_deliverability_execution_review_pass_v2.yaml`，要求独立
`sol_reviewer`的 `PASS`、零 finding 和关闭 formal/result/claim/security 的
effect，再由 receipt 中的 digest 验证固定 execution outer、inner 和全部成员。
该 receipt 不进入被审 outer，避免自哈希循环；其路径、schema、scope、reviewer
role 和 required effect 由 sealed execution config 预先固定。当前 receipt 尚未
生成，因此所有公开 stage 均 fail closed。

后续 fresh-process activation通过 review authority 后，必须递归执行
`derive_static_authority()`，并从scientific outer 所绑定的 V5 YAML 内部加载
design；不得接受 caller-supplied design。由此 caller 不能通过提交一个与自己修改
内容一致的 digest 或 alternate root 建立 execution authority。evidence store 的
run identity 只能由
已验证的 static authority、execution outer、review receipt、正式
dispatched-grid manifest、固定路径执行机 runtime receipt和固定路径 activation
authority内部计算；调用者提供的 store identity 必须精确相等。v2将后两项登记为
`ready=false/sha256=null`，因此当前 stage 即使通过 review 也不能执行。
activation receipt还必须绑定唯一仓库相对 evidence root；后续 activation stage
还必须核对`EvidenceStore.root`与该路径，调用者不能把已授权运行重定向到任意
输出目录。

outer、inner、JSON/YAML authority、CAS object 和输入包成员只解析已经通过稳定
descriptor读取并完成SHA-256校验的同一份bytes；输入包在一次 snapshot 内验证
exact inventory、manifest和全部成员后，CSV/YAML/JSON解析与block构造均消费该
snapshot，不允许先按路径校验后再次读取。后续 activation successor 接通planning
helper时，必须先完成execution outer、递归上游authority、V5 design和registered
inputs全部门禁，之后才允许构造内部callback或触发solver调用。
所有外部JSON解析统一拒绝duplicate object key与非有限数值，包括
`NaN`/`Infinity`常量和`1e999`类指数溢出，不能接受标准producer无法生成、但
普通`json.loads()`会折叠或放行的表示。

## 3. 输入闭合

`audit_registered_inputs()`对两个现有输入包执行：

1. manifest SHA-256 与全部成员 SHA-256；
2. package 文件集合与 manifest 精确一致；
3. 每个 block 恰有 24 个唯一 hour offsets；
4. hourly 与 marginal block ID 集合一致；
5. `541/530/34/34`精确计数；
6. training/holdout block ID 不相交；
7. `source_hour`或`source_relative_hour`不相交；
8. 两侧 marginal 概率和在`1e-9`内等于1。

通过审计的完整 input audit 以固定 key `input_audit/registered`提交为不可变
content-addressed object。planning index 与 holdout summary 必须同时保存该
object SHA-256；bootstrap 从 evidence store 重新加载 audit，并要求调用参数、
summary 引用和持久化 object 三者逐字节一致。仅在调用栈中传递 audit 或单独保存
其内容哈希不足以通过该门。

私有 stage helpers不接受调用者提供的 input audit、block objects、execution outer
digest 或 grid manifest digest。后续 activation必须从固定 execution review
receipt取得已审 outer，再从 sealed config 读取唯一 registered grid manifest，
重跑`audit_registered_inputs()`并自行加载`541/530/34/34`四组blocks。接受
caller 构造的自洽 audit 只保留为下划线前缀的 synthetic unit-test helper，不属于
执行 API。

当前 power base 与 workload package 通过；sealed execution config 的
`dispatched_grid.manifest_sha256`仍为`null`，即使调用者知道或提供某个 package
digest也不能绑定输入。V5 指定的
`rts_gmlc_public_grid_need_dispatch_v4_gurobi`目录不存在，因此只报告
`blocked_missing_dispatched_grid_package`。缺失输入不是 E0、solver failure 或
数学不可行。

未来激活 dispatched-grid package 时，必须再通过八成员精确清单、producer
`config.yaml`、完整 CSV header、`(block_id, split, hour_offset)`逐行映射、
base/marginal 一致性、E0/finite 状态、block-status 计数、checkpoint inventory、
provenance contract、producer source hashes、stage-base 和 summary 交叉哈希。
`checkpoint_inventory.json`不作为自证摘要：审计还必须从已绑定 producer config
读取唯一 checkpoint directory，要求恰有1,071个普通JSON文件、逐文件SHA-256与
package inventory一致，并以单block工作集解析完整`outcomes`和`rows`。每个
checkpoint row必须与最终CSV逐字段一致；目录清单和全部文件哈希在语义解析后再次
复核，缺失、多余、别名、内容漂移或TOCTOU均fail closed。
包内`config.yaml`还必须等于已通过既有 activation chain 生成的
`results/execution_configs/rq2_public_successor_v2/grid.yaml`
（SHA-256 `b8f7a71f...`），而不是尚未打开执行门的 template
（SHA-256 `84db8e7a...`）。candidate 同时绑定 template、activated config 与
activation record，避免登记一个合法 producer 永远无法产生的 package。
`grid_need_fraction`必须用包内且注册为
`250 MW`的`dc_reference_demand_mw`重算，不能依赖执行代码中的隐式常数。
每一行还必须重放非负 incumbent、LB/UB、absolute/relative gap、gap tolerance、
termination/status、maximum residual 和 model scale；finite、no-outage 与 E0
分别使用各自的精确状态合同，不能只依赖`dispatch_resolved`布尔值。
active finite与baseline共享sealed minimization interval/gap predicate：
incumbent只能在`[LB, UB]`内，absolute gap和relative gap必须分别不超过其记录
tolerance与冻结`mip_relative_gap`，边界只允许`rel_tol=abs_tol=1e-12`。
Gurobi active finite与baseline仅接受注册的`termination=optimal,status=ok`，
不接受未登记的`globallyOptimal`。no-outage除not-applicable状态与零model scale
外，还要求grid need、fraction、incumbent、全部bounds/gaps/tolerance和residual
逐项为零。
任何 bound certificate 的 lower/upper/absolute-gap 必须全有或全无。对当前注册的
Gurobi package，E0 的 primary 与 zero-DC confirmation 均只能是
`termination=infeasible, solver_status=warning`，两侧所有 incumbent/bound/gap/
residual 字段必须为空，且两侧`(model_variables, model_constraints)`必须完全相同
并严格为正。该规则逐字段对齐 sealed semantic successor，不接受`ok`作为 Gurobi
infeasible status。CSV未投影的zero-DC
`resolved/proven_infeasible/grid_need/residual/source/event/component`及
certificate incumbent/relative-gap/gap-tolerance必须从内容绑定的原始checkpoint
重放，不能从CSV缺失值推断。
每个checkpoint的`baseline_audit`也按producer的event/no-event分支完整重放。
no-event只能包含`accepted=true`和注册的not-applicable termination；event
baseline必须闭合termination/status/message、objective与LB/UB、absolute/relative
gap、gap tolerance、constraint/integrality residual、threads、configured gap、
solver name/options及正model scale。incumbent必须位于`[LB, UB]`内，gap不得超过
自身absolute tolerance或配置的relative gap；interval方向、边界与派生量仅允许
sealed semantic successor注册的`rel_tol=abs_tol=1e-12`序列化误差，不能借用
solver gap tolerance扩大证书区间，也不能额外增加`1e-9`裕量。验证后的baseline
model scale集合必须精确重建summary中的`normal_scuc_model_scales`，summary不能
自证。

checkpoint `rows`到最终CSV的映射使用字段类型规范和`csv.DictWriter`实际
`str(value)`结果逐字段零容差比较。source/string字段必须保持JSON string，
model-scale字段必须保持JSON integer，数值字段必须保持有限JSON float；空值只在
producer写出空字符串或outcome的`null`投影时接受。字符串转数值及小于`1e-12`
的数值漂移均fail closed。`primary.resolved`与
`primary.proven_infeasible`在文本投影前必须是JSON boolean，不能由同字面值
string冒充；source/event/component metadata同样执行类型敏感的canonical比较。
统一CSV loader还要求header非空且无重复字段，并拒绝超宽行产生的`None` key及
缺列产生的`None` value；因此正确header后追加未注册尾列也不能被忽略。

## 4. Solver 证据

`capture_primal_evidence()`保存：

1. 全部 active scalar variable 的`float.hex()`值；
2. active constraint 名称集合；
3. objective 与独立 residual；
4. solver certificate SHA-256；
5. native solver log SHA-256 与字节数。

`replay_primal_evidence()`必须重新构造空白模型，检查 variable/constraint inventory，
重新赋值 primal，并独立重算 objective、变量边界、整数性和全部 constraint
residual。开发机只运行 synthetic replay；Gurobi 13.0.2 的 native probe 必须由
Windows 执行机完成并生成 runtime receipt。

execution 层逐字节复刻 implementation v2 的`planning_input_sha256`。每次调用均
发布 immutable native-solve record；capacity stage 完成后，还必须将每条 record
通过 immutable invocation ordinal、solve-order pointer 和 planning hash 闭合到具体
representative `cell/arm` output 或 full-support fallback certificate。index builder
必须使用原 training blocks、workload blocks 和 solver specification 对 frozen
implementation v2 capacity stage 做一次零-solver replay，由 callback 的实际
`JointDeliverabilityPlanningInputs`重新计算每次调用的 planning hash，并要求完整
frontier byte-equivalent；不能从 certificate 或调用顺序自证 fallback hash。
每个带incumbent的representative或fallback record还必须使用该次callback实际收到
的inputs重新构造fresh model，重放持久化primal并与既有replay object逐字节等价；
预先伪造一组自洽primal/replay对象不能通过index提交。
重放入口还要求`541`个 power training blocks 与`34`个 workload training blocks
的完整 canonical inventory hash 等于 registered input audit，调用者不能传入另一组
自洽 training support。planning index 同时保存两侧 training inventory SHA-256
与共同 input-audit object SHA-256。
capacity frontier 本身也以固定 key `capacity_frontier/registered`进入 CAS；
downstream 从该对象重建 representative/fallback solver-call inventory，并逐条
核对 solve-order、solve object、native log、primal 和 replay 指针。只提交一个
metadata 自洽但`records=[]`的 planning index 不构成证据。
每次 downstream 消费 planning evidence 时还必须使用 sealed design、真实
`541×34` training blocks 和 sealed solver contract 完整重跑 implementation v2
capacity stage；callback 按真实`JointDeliverabilityPlanningInputs`重算 planning
hash，带 incumbent 的调用在 fresh model 上重放 primal，最终 frontier 必须
canonical-byte equivalent。
私有`_execute_planning_stage_with_evidence_from_audit()`固定执行：
空pre-state验证、registered training support重建、sealed solver contract解析、
`_EvidenceSolvingCallback`构造、reference capacity stage、planning index提交、
完整CAS inventory和`_registered_planning_evidence()`全量重放。它固定使用注册
model factory和solver adapter，不接受caller注入`solve_driver`、
`model_factory`或`solver_specification`；相应注入仅存在于下划线前缀的synthetic
test helper。v2公开planning入口保持硬关闭，后续fresh-process activation
successor负责在完成runtime closure后接通该helper。
planning不声明隐式resume：pre-state必须是空 evidence store，任何同阶段或跨阶段
既有对象都在callback构造和solver前拒绝。post-state必须通过完整
`_registered_planning_evidence()`，精确闭合input audit、solve/order、
primal/replay、frontier和index keyset；不能仅依赖namespace allowlist。
非 optimal termination 若携带可行 incumbent，仍保存 capacity、LB/UB、gap、
residual、native log、primal 和 fresh-model replay，但 certificate 状态保持
`unresolved`，不得进入 estimand。

## 5. Holdout Streaming

完整 holdout 不构造跨 46-cell 的内存大表。最小持久化单位为
`cell_id × power_block_id`，每个 chunk 包含该 power block 与34个 workload blocks
的四臂24小时轨迹。

正式入口先强制46个按注册顺序的 cells、184个具名 arm outputs、530个 holdout
power blocks、34个 holdout workload blocks、唯一ID及两侧概率质量。缩小维度的
synthetic helper 不属于正式入口。两侧 block objects 的完整 canonical inventory
hash（包括来源时序、概率、状态和24小时值）必须与 input audit 一致，不能只比较
`530/34`计数。
holdout stage 另提交 content-addressed summary，逐 cell 保存`resolved`、
`not_evaluable_capacity_unresolved`或
`finite_service_identification_unresolved`；bootstrap 必须传播后两类状态，不得
把缺少 trajectory chunk 解释为可评估或全局 resolved。summary 必须引用与
planning index 相同的不可变 input-audit object，并保存 planning-index object
SHA-256；planning index 缺失、多余或与 capacity frontier 不一致时，holdout
不得开始。

resume采用两遍式流程：第一遍`commit=False`按注册顺序重建并验证全部已有chunk，
要求已有key形成连续前缀；任何后序坏checkpoint必须在新文件写入前被发现。只有
第一遍全部通过后，第二遍才允许补写缺失chunk。existing summary只有在完整chunk
集合与exact payload均匹配时才可接受。

每个 chunk 还保存冻结容量、raw service requests、available flexibility、
connected demand、recovery headroom 和完整 policy parameters。写入前，执行层用
这些输入重新执行 current-state policy，逐字节比较整条 trajectory，并从轨迹重算：

- grid/CFE/total shortfall；
- hard-grid、CFE、recovery-completion 与 joint failure；
- peak/terminal recovery debt。

指标重算不调用implementation-v2返回的`metrics`字段，而是仅从24小时trajectory
逐项以`math.fsum()`独立计算；该结果再与claimed metrics比较。重算值与 claimed
metrics 不一致时拒绝。chunk 先写入 SHA-256 内容寻址 object，
再写不可变 checkpoint pointer。相同 key 与相同 bytes 幂等；相同 key 的不同
bytes 视为 drift。全量上限为24,380个 trajectory chunks，但工作集仅为一个
power block 的34个 pairs、136条 arm trajectories。

后续 metric-matrix replay 再次从持久化的 raw requests、capacity、headroom 和
policy parameters 调用完整`execute_holdout_policy()`，同时比较 trajectory 和
metrics。只重算已存 trajectory 的汇总指标不足以通过该门。

bootstrap 读取 holdout 时，不信任 summary 与 chunks 的内部自洽。它从 sealed
capacity frontier、46个 registered cells、530个 live finite/E0 power blocks 和
34个 live workload blocks 重建每个预期 chunk，要求 exact key set、canonical
payload、cell status、chunk count和全局 ordered stream digest全部一致。

## 6. Bootstrap Resume

私有bootstrap helper不接受调用者提供的draws、metric loader或endpoint solver。
后续 activation必须先验证sealed V5 bootstrap contract的完整digest，复算固定
PCG64DXSM deterministic probe，再由注册边缘概率内部生成200个draws；raw draw
stream按完整canonical payload计算SHA-256。
helper只接受与 input audit 内容哈希一致的完整`530×34`支持；任一 replicate
在 E0 conditioning 后没有 finite support 时返回`unresolved`，不得生成 resolved
区间。每个 cell 的完整 metric tensor 必须
由 content-addressed holdout chunks 重放，按固定 metric/power/workload 次序编码为
little-endian float64 blob，并提交独立 matrix object；matrix object 同时绑定该
cell 全部 holdout chunk object 的有序摘要。每个 bootstrap checkpoint 绑定该
matrix object SHA-256；每次 resume 与 CI aggregate 都先从 holdout chunks
重新执行 policy/metric replay，再用 immutable commit 验证既有 matrix 未被预置
替换，随后才加载 checkpoint。bootstrap 在生成 draws 前还必须验证 holdout
summary 的 input-audit 与 planning-index object SHA-256 均与实际加载对象一致。
checkpoint 单位为
`replicate × cell_id`，包含该 cell 的23个注册指标及 lower/upper endpoint。
每个 checkpoint 和最终 aggregate 还绑定同一 input-audit 与 planning-index
object SHA-256。正式规模最多9,200个 checkpoint。

endpoint调用的全局顺序固定为
`replicate → ascending cell_id unsigned UTF-8 → registered metric order → lower → upper`。
checkpoint schema为`rq2_joint_deliverability_bootstrap_cell_v2`，保存该
replicate-cell对应的全局`endpoint_invocation_start_ordinal`、固定46次
endpoint调用数量及exclusive end ordinal。resume先逐一重放全部已有checkpoint，
再要求其key恰为上述全局顺序的连续前缀；ordinal、顺序或前缀任一漂移均在新
endpoint solve或写入前拒绝。
若全部 power support 为 E0，resume 与 aggregate 都返回注册的
`finite_service_identification_unresolved`语义和空 interval；即使cell statuses
同时含其他non-evaluable状态，该原因码也由空finite support优先确定。不把空finite
support抛成evidence drift，也不生成resolved CI。

恢复时必须满足：

1. run identity 相同；
2. draw-stream SHA-256 相同；
3. `replicate × cell` inventory 完整且无额外项；
4. 每个 checkpoint 的23指标顺序和上下界合法。

resume在任何metric-matrix commit、endpoint solve或新checkpoint写入前，先拒绝
全部额外key，并对所有已存在 metric-matrix objects 执行只读 replay，即使该 cell
尚无 bootstrap checkpoint；随后再验证所有已有checkpoint。后序checkpoint或孤立
matrix损坏时不得先补写更早缺失的checkpoint。只有现存集合全部通过后才进入新计算。
该顺序也适用于首个bootstrap replicate为全E0，以及总体支持含finite block但某个
replicate恰好只抽到E0的情况；empty-finite early return不能绕过matrix语义复核。
aggregate在无resolved cell时要求matrix与bootstrap集合均为空；在mixed-support
empty replicate时只允许并完整验证该replicate之前的checkpoint前缀。

每个 metric checkpoint 同时保存完整 transport primal/dual certificate。恢复时
根据当次 draw marginal 与内容寻址 metric matrix 复算 primal objective、dual
objective、marginal residual、dual feasibility 和 gap；不重新调用 LP，但也不
信任 checkpoint 自报 endpoint。

confidence interval 只能从验证后的 checkpoint bytes 使用
`numpy.quantile(..., method="linear")`重建，不能信任单独汇总文件。
CI aggregate 自身也必须重新生成 draws，并针对 state、metric matrix 逐证书复算；
不能直接汇总 checkpoint 中自报的 lower/upper。

## 7. 原子性与路径

所有 objects 与 pointers 都是 immutable。写入流程为同目录 temporary file、
file fsync、atomic replace、parent-directory fsync。existing identical bytes
幂等；existing different bytes、遗留 lock、symlink 或 Windows reparse component
均 fail closed。

首次创建 evidence 目录树时逐级检查既有组件，再创建单层目录并 fsync 新目录及其
父目录；不得先穿过内部 symlink/reparse 创建外部子目录后再报错。由此 object、
blob 和 checkpoint 的祖先目录项也属于崩溃恢复证据，而不只刷新最深层目录。
若检查与`mkdir`之间发生并发创建，`FileExistsError`分支仍重新检查类型并 fsync
该目录与父目录。sealed inventory 还拒绝任何未由注册文件路径解释的空目录。

此实现不自动清理 commit-indeterminate 或锁状态。恢复必须由后续 activation
规范根据 evidence 明确处理。

sealed inventory只允许规范的 object、blob 和 checkpoint pointer 路径，逐文件
校验内容寻址名称，并要求 pointer→object、primal/solve→native-log blob 以及
metric-matrix object→float64 blob 全闭合。因object/blob先于pointer提交，崩溃可
留下内容哈希与路径均正确但尚未被pointer引用的inert orphan；inventory将其显式
列出，后续相同digest commit可安全采用。任何已被pointer或已引用object引用但缺失
的object/blob仍fail closed。Windows parent-directory flush 使用
write-capable directory handle；其 native NTFS probe 只能在执行机完成，macOS
开发机不得替代该证据。

私有holdout、bootstrap和aggregate helper在阶段执行前后均调用完整
`EvidenceStore.inventory()`；planning分别使用空pre-state和完整post-state
validator。namespace检查负责拒绝空目录、无关stage、额外blob和遗留lock，并报告
inert CAS orphan；同一stage的exact keyset由各阶段状态机另外验证。holdout按live
cells/blocks验证可恢复前缀与最终完整summary/chunk closure；
bootstrap/aggregate验证matrix与replicate-cell checkpoint的合法前缀或完整集合。
v2公开stage仍保持硬关闭。

## 8. 规模与剩余门禁

| 项目 | 正式上限 |
|---|---:|
| dispatched-grid source checkpoints | 1,071 |
| holdout trajectory chunks | 24,380 |
| holdout policy executions | 3,315,680 |
| hourly state transitions | 79,576,320 |
| bootstrap replicate-cell checkpoints | 9,200 |
| bootstrap endpoint solves | 423,200 |

静态内存投影同时计入一个 trajectory chunk、单 cell 的23张`530×34` metric
matrices、单 cell 在200-replicate下23个指标的 lower/upper endpoint samples、
46个cell的最终置信区间输出，以及完整 bootstrap draw indices。aggregate按cell
依次重放、计算quantile并释放该cell的samples，不同时保留46个cell的完整sample
数组。该数值只是不含 Python object overhead 的 numeric lower bound；正式
peak-memory gate 必须用`tracemalloc`覆盖 dict/tuple/float 对象和 canonical JSON
serialization buffer，静态投影不能作为验收证据。

进入 formal activation 前仍需：

1. 绑定并验证完整 dispatched-grid manifest；
2. package inventory绑定的完整1,071-file grid checkpoint directory；
3. Windows x86-64 全新环境 runtime receipt；
4. Gurobi 13.0.2、license、4-thread 与 native primal probe；
5. 注册维度 peak-memory 实测；
6. transport runtime 实测投影及资源批准；
7. exact sealed execution outer 的独立 R3 审查，并生成固定路径 PASS receipt；
8. 固定路径Windows runtime receipt与activation authority在后继版本中绑定并通过；
9. 单独用户 formal-run authorization；
10. versioned activation wrapper、canonical fresh output root、exclusive run lease，
   stdlib-first fresh-process import closure，以及中断后单独审查的 resume
   authority。

## 9. 结论边界

successor 通过测试只说明工程机制可复核，不说明正式输入已齐备、正式计算可执行、
模型可行、结果存在或研究结论成立。不得把 synthetic replay、缺失 package 或
执行机 preflight failure 解释为网络安全或联合服务不可行。
