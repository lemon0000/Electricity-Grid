# 研究目标与执行规则

更新日期：2026-10-22。当前研究范围、科学定义、工作顺序和审查规则以本文件为准；各冻结实验仍按其绑定的规格、配置与验收合同解释。

## 1. 职责

以算电协同研究的科学有效性为先：核对问题、假设、模型与证据的对应关系，发现信息泄漏、口径冲突、数据不足或不公平比较时先修正。不能为得到预设结论调整参数，也不能把模块数量或局部测试数当作研究贡献。

## 2. 当前项目目标

研究主题：**智算中心达产过程中的分阶段接入与柔性可交付性研究**。

面向固定接入点的AI智算中心，分别表示业务增长、计算设备分批投运与电网扩建进度，评价业务柔性能否支撑给定的分阶段接入计划，解释任务恢复与小时级CFE要求在哪些阶段限制履约。三条进度路径必须进入资源和运行约束；业务需求保持外生，设备余量不能始终按最终设计容量给定。

当前按几个月内可实施的毕业论文规模推进。具体交稿日期尚待用户提供，工作计划和算例时长须用实际成本核定。

## 3. 当前论文问题

1. 业务达产、设备投运与电网按期或延期投运的组合，在哪一阶段使给定接入计划遇到约束？
2. 相同即时可调MW在不同阶段，何时受当前可延期工作限制，何时受截止时间前的设备、供电或清洁恢复资源限制？
3. 瞬时MW、固定恢复余量与完整时序评价，是否改变对同一计划的判断？冻结方案在独立留出路径上表现如何？

## 4. 贡献与科学协议边界

候选贡献是可复核的阶段性瓶颈及方案判断边界。用相同外生任务和清洁资源进行匹配对照，区分即时调用增大与恢复时序冲突；根据有差异、无差异和失败结果界定贡献。任务延期、恢复、CFE匹配、联合规划和四臂名称均有既有基础，不能单独宣称新颖性，定位依据见[研究缺口](docs/literature/research_gap.md)。

历史RQ、基线编号、冻结参数与结果保持原定义。联合服务前沿的协议为`configs/rq2_joint_deliverability_preregistration_v1.yaml`及其适用后继；定义与分解见[estimands规格](docs/model_spec/rq2_joint_deliverability_estimands_v1.md)，其中`I_joint = D_J - max(D_N, D_C)`。当前阶段设计需要独立的规格、配置和验证，目标更新不修改旧协议、验收阈值、hash、receipt或运行权限。

## 5. 实施范围

- 一个固定接入点，两至三期设备、一个候选电网工程、少量给定建设与接入计划；分别给定业务、设备与电网进度。
- 连续小时的执行、延期与恢复，明确前史、任务期限及必要后续观察；设备—任务—实际用电映射包含待机、补做和配套耗能。
- 声明范围内的正常状态与关键故障网络检查、小时级CFE、共享柔性资源和固定策略留出评价。
- 核心对照是瞬时MW、固定恢复余量与完整时序评价。现有四臂作为适用合同下的运行诊断复用；阶段参数点数先经小例与预算核定。

投资开工联合优化、多阶段适应性价值、年度与小时匹配对照、多接入点及其他扩展各按独立问题设计。新增模块须说明其对应的当前问题、证据需求和计算成本；超出当前范围时先取得用户对范围变更的明确授权。

## 6. 当前工作顺序与阻塞

1. 明确服务合同、核算边界、三条阶段路径与设备—任务—取电映射，复用已核文献和现有代码。
2. 固定一个覆盖阶段变化、调用、任务恢复与期限的小型连续案例，列出依赖并做独立数值核验。
3. 按第9节测量完整计算路径并闭合预算，再确定有限的阶段计划和参数对照。
4. 完成主比较及必要敏感性；冻结给定建设计划和运行策略，在独立留出路径上执行。
5. 用可追溯结果制作图表、解释适用边界并完成论文。

遇到逻辑漏洞、失败测试、口径冲突或证据不足，先修复并验证再推进依赖工作。需要外部数据或用户决定才能解决时，在[blocker register](docs/model_spec/blocker_register.md)记录缺口、已验证内容和解除条件，停止依赖步骤，继续无依赖工作。执行状态见[科研执行步骤](docs/plan/科研项目执行步骤.md)，不在本文件重复实验流水。

## 7. 任务分级、模型路由与独立审查

本节是task classification、model routing、delegation和review rules的唯一权威来源。根目录`AGENTS.md`仅作为Codex自动发现的仓库入口，承载上下文bootstrap、工作区与实验安全和实施约束；不得复制、覆盖或另行定义本节的风险等级、model slug/effort、委派规则或审查状态机。

按科学影响判断风险；常规任务无需展示分级过程。默认由当前主代理完成，项目默认模型为`gpt-6-astra`。下表的专用代理是可选执行路由，独立审查要求仍适用。仅在独立子任务足够大、委派有明确收益或需要独立审查时使用子代理。保留Luna的低成本只读角色、Terra的普通实现角色及Sol的领域和审查角色，不为匹配模型表而转交小任务。reasoning effort沿用有效配置，遇到实际难度或验证不足再调整，不因模型升级统一提高。主代理负责集成与证据核验。

| 风险 | 可选专用路由 | 本项目典型任务 | 最低验证要求 |
|---|---|---|---|
| R0 | `luna_reader`（`gpt-5.6-luna`，`low`） | 文件inventory、日志解析、JSON/CSV提取、进度或产物清点 | 机械计数、schema、hash或直接来源证据 |
| R1 | 只读任务可用`luna_reader`；写入任务可用`terra_worker` | 格式整理、明确的机械转换、孤立测试、范围很窄的低风险修复 | diff或格式检查；行为变化采用有意义的针对性测试 |
| R2 | `terra_worker`（`gpt-5.6-terra`，`medium`） | data contract、非正式实验plumbing、不改变结果语义的复现工具和普通跨模块修复 | 针对性测试、相关回归；跨模块、持久化产物或长运行行为变化时独立审查 |
| R3 | `sol_modeler`（`gpt-5.6-sol`，`xhigh`） | 模型变量、目标和约束，AC/DC/N-1语义，非预见性，solver certificate，正式runner或冻结工件语义 | 领域不变量、解析或小型合成例、针对性测试、相关广泛回归，并由`sol_reviewer`独立审查 |
| R4 | `sol_modeler`（`gpt-5.6-sol`，`xhigh`） | preregistration、验收阈值、正式结果解释、certification状态和paper claims | 完整证据链、manifest/hash与回归证据，`sol_reviewer`独立审查及用户明确授权 |

以下事项即使文本改动很小，也不得降级：

- `src/models/`中的变量、目标、约束、索引集、概率、场景映射或词典序阶段属于R3；
- `src/grid/`中的SCUC/SCED、OPF/SCOPF、contingency选择、rating、redispatch、AC可行性、slack/Q-control或恢复语义属于R3；
- `src/scenarios/`和`src/evaluation/`中的非预见性、历史分组、训练/holdout分离或未来信息边界属于R3；
- certified bound、gap归一化、solver termination解释、warm start、constraint generation、checkpoint、resume、execution lease或atomic publication属于R3；一旦改变认证或正式结论则升级为R4；
- 冻结YAML输入、preregistration、input hash、manifest、stage certificate、formal runner、canonical result、任何`*_certified`、`*_published`、`*_ready`或gate状态，以及VMA、F/X价值、安全性、工程可行性、因果效应、经验概率或正式CFE结论，属于R3或R4，并按其是否改变科研协议、认证或结论取更高等级。

### R3/R4 frozen candidate生命周期

R3/R4 frozen candidate统一遵循以下可迭代生命周期：

`DRAFT_NONAUTHORITATIVE ↔ PRE_SEAL_AUDIT → SEALED_READY_FOR_INDEPENDENT_REVIEW → official PASS/REWORK/ESCALATE`

- `DRAFT_NONAUTHORITATIVE`可由同一个唯一写入代理在原路径反复修改；即使预留了`vN`文件名，版本号、内容和状态仍是provisional。draft不得拥有或生成production inner/outer manifest、production one-shot lease、review PASS receipt或user run authority；不得宣称review-ready或execution-ready，不得执行preflight、consume、spawn或formal run。临时测试工件只能位于pytest/system tmp或明确标记为non-authoritative的位置，不能冒充gate evidence。
- `PRE_SEAL_AUDIT`必须在seal前完成冻结验收矩阵、targeted与相关broad tests、与并发/失败窗口相匹配的fault injection tests、适用时独立实现的oracle，以及hash、diff、process和root检查。可由只读`sol_reviewer`进行non-authoritative adversarial audit；其输出只能称为pre-seal findings，不能使用official `PASS/REWORK/ESCALATE`，不能生成review receipt或打开任何gate。唯一writer可在同一draft中反复修复pre-seal findings；本节的“official REWORK最多一轮”不限制pre-seal development iteration。
- 只有全部pre-seal findings闭合后，才可生成canonical config/code/test、production lease、closure、inner/outer和hash并完成stable verification。authoritative outer与`SEALED_READY_FOR_INDEPENDENT_REVIEW`状态成功原子发布是唯一seal commitment point；从该时刻起，所有被outer绑定的bytes不可修改，同一路径或版本不得重封。在commitment point之前或seal机械过程中，只要authoritative outer/SEALED_READY状态尚未成功发布，candidate仍是同一个non-authoritative draft；可在核验并清理仅由本任务产生且可证明可恢复的临时工件、修复原因并重跑受影响pre-seal检查后，于同一draft/version重试。不得覆盖任何已成功发布的outer，不得把半成品当作gate evidence，也不得删除、覆盖或整理用户及其他任务工件。
- 只有到达seal commitment point后，official independent R3/R4 review才可开始。review必须由未承担该candidate写入的只读`sol_reviewer`审查exact sealed outer，并输出official `PASS`、`REWORK`或`ESCALATE`。参与过pre-seal audit的reviewer不能沿用同一实例或上下文签发final official verdict；final review必须使用新的reviewer实例和独立上下文。
- sealed official review后，任何实现字节变化都必须进入新的versioned successor，旧sealed bytes不得修改。official `REWORK`仍最多一轮，由原writer在新successor中只修复reviewer finding；同一验收项再次失败必须`ESCALATE`。official `PASS`只关闭independent review gate，不授权preflight、consume、spawn或formal run。
- draft/design、pre-seal audit、production seal、official review与formal run必须保持effect separation，但不要求机械地对应多条用户消息。一条语义清楚的用户指令可以显式同时授权draft/design、正常范围内的安全短时pre-seal audit、seal和official review；已授权开发范围内的测试与机械检查无需逐项再次确认。formal-run authority仍必须单独且明确，不得由前述开发、audit、seal或review授权推导；长运行、付费查询、外部数据下载和其他外部动作继续遵守本节及仓库既有明确授权规则。documentation-only授权不授权创建candidate、seal或运行。

协作和审查遵循以下规则（frozen candidate生命周期只适用于冻结候选，不为普通文档或R1/R2修改创建seal/receipt）：

- 每项任务只能有一个写入代理；并行仅限彼此独立的只读子任务，`agents.max_depth = 1`，不得让子代理继续分叉；一个命令或很小的确定性任务不为委派而委派；
- R3/R4 official审查必须由只读的`sol_reviewer`（`gpt-5.6-sol`，`high`）按上述生命周期审查exact sealed candidate。审查输入应包含原始请求、冻结验收标准、sealed outer、diff、相关规格以及测试和产物证据，输出必须是official `PASS`、`REWORK`或`ESCALATE`；
- 执行者无法证明所需不变量时返回`ESCALATE`，交由具备相应能力的主代理、领域代理或用户解决；不得猜测或弱化门禁。official返工次数与successor规则见上述生命周期；
- official `PASS`只表示exact sealed工作产物满足已冻结的审查标准并关闭review gate，不授权formal run，也不授权修改科研协议、预注册阈值、认证状态或论文结论；这些科学决定与运行仍需用户对具体动作作出明确授权；
- 审查通过后的自动推进只适用于冻结计划内、不受blocker约束且不需要新增权限的可逆开发和短验证。不得据此启动、重启、恢复或改变长时间formal run，不得发起付费查询、外部数据下载或其他需授权的外部操作，也不得绕过`docs/model_spec/blocker_register.md`中的停止条件。

## 8. 模型硬约束

- 服务与功率闭环：外生需求、实际执行、合同削减、补做和非合同缺口保持可审计余额。K为计算资源，P为计量点用电；功率等效约束`w-q+r≤K`须有明确映射，不能代替实际取电平衡。
- F/X保留网络与合同语义：正常状态检查完整F+X，声明的故障状态检查F，并按合同条件调用X；F不因拥塞主动削减，X受响应、持续时间、次数和能量预算限制。D为业务柔性容量，不能未经验证映射为新增X。
- 未完工设备或电网工程不提供能力；按工期与实际延期投运。不同建成网络重新计算调用及恢复供电条件，不能对所有计划沿用一条固定调用曲线。
- 当前业务模型共享`q+r≤D`；既有具名模型的`c_grid + c_green <= D_flex`按原合同执行。必须在比较前固定同一次削减能否同时计入两类服务的合同与计量规则，不同计划或arm之间不得切换，并防止共享物理资源重复承诺。
- 按任务批次、效率和期限核减恢复债务；逾期后补做不消除已发生的逾期。债务与预算沿连续物理时间延续，分离窗口须有明确前史和后续观察；缺少结局信息时诚实右删失，已观察违规仍保留。
- 同一观测历史采用相同动作；训练与留出严格分离。留出评价不重新优化给定建设计划，因果执行冻结运行策略。
- `y_CFE`为同小时适用范围内可归属电量，不追踪物理电子。外部清洁资源与归属规则保持可比、守恒且不重复分配，恢复与待机纳入实际用电；不得先截断完整服务缺口以迎合柔性上限。
- 不放宽电压、热限、响应、gap、残差或最大接受阈值获取有利结果；CVaR仅用于服务与业务损失，不放松网络安全。适用时，T20/T50/T100按可运营容量块计算，unused MW-year只作物理量或在有依据的成本模型内使用。

## 9. 实验规范

### 实验启动前的整体性能审查

2026-10-17 用户要求：之后所有实验启动前，必须先确认完整执行流程的优化空间和资源成本。
适用于合成集成、机制实验、校准、正式实验，以及新 attempt、重启、恢复或扩大规模。
按具体实验包及其任务 DAG 审查，包内已覆盖的子任务复用同一份证据；普通单元测试和静态检查按实现合同执行。
为形成审查证据的有界性能诊断，可在已有授权范围内先行开展：先核对自身执行路径，固定问题、规模、次数、资源上限与安全停止条件；无需递归完成其要产生的整体实测审查。
诊断结果仅支持目标实验的完整审查，不授予目标实验运行权限。

启动前必须完成并保存以下检查：

1. **完整路径与调用量**：列出输入装载、生成/求解、数值审计、持久化、失败分支、外部回调、提交、清理、关闭重开、保存重放和报告等实际阶段及依赖；计算循环、递归和回调叠加后的调用量，明确历史重放随任务规模的增长。
2. **整体优化空间**：定位重复计算、重复校验、I/O、依赖身份计算和调度瓶颈；检查缓存、增量校验、合法结果复用 DAG、批处理及独立任务并行的条件。优先完成可证明安全且对总预算有实质收益的优化；暂不采用的方案必须给出成本收益、证据或合同约束理由。
3. **有界代表性实测**：使用小规模完整路径或保存记录覆盖关键成功路径、昂贵失败路径和回调/收尾，记录分阶段 wall time、调用次数、内存及存储观测。探针自身先固定问题、规模、次数和资源上限。单模块、单 arm、求解器时间或局部提速比例不能代替整链证据；未覆盖阶段必须列为未知并补齐关键证据。
4. **科学与校验等价**：优化保持模型、输入口径、验收阈值、非预见性和状态延续；核对科学输出、保存工件和适用的 hashes、残差、gap、LB/UB。跨观察窗口复用或减少校验需要证明依赖闭包、输入 freshness、失效条件与失败窗口覆盖；涉及校验合同或冻结实现变化时按第 7 节采用 versioned successor 和独立审查。
5. **预算与停止条件**：按完整任务数、真实调用倍数及合法复用关系列出阶段和总时长估计、依据、不确定性、并发、RAM/存储上限；同时固定心跳、无进展判据、超限处置、安全停止、清理及终态保存方式。运行偏离预算时按事先约定诊断或停止，不能靠反复顺延预计时间替代处置；不得因性能放宽科学验收限。
6. **绑定与结论**：审查记录绑定实际代码/config/input/dependency 版本或 hashes、环境、任务规模、DAG、优化决策和实测证据，并明确整体性能审查是否完成。后续代码、配置、环境、规模或执行路径超出原证据覆盖范围时重新审查；覆盖范围不变且 hashes 匹配时复用已有闭合证据。

关键调用量未界定、昂贵阶段未获得代表性证据、存在尚未处理的实质性能瓶颈或整体预算无依据时，不得启动新的长实验；先做有界诊断与优化。
完成本审查仅解除这一启动前条件，不替代科学门禁、资源准入、seal、official review 或具体运行授权。
需要新的真实 native 校准时，先登记具体包、次数、预算和验收问题，并按既有规则取得专项授权。
已启动 attempt 保持原配置和字节绑定；本要求在后续启动时落实，优化在独立后继中验证。

### 比较与公平性

当前阶段比较按第5节确定；历史B0–B6、VMA、四臂与其他实验的比较义务仍由各自冻结合同约束。

- 比较计划使用相同外生业务、期限、清洁资源、核算规则和安全标准；建设状态的不同作为计划差异显式保留。
- 参数范围与选择规则在看目标结果前固定，报告无改善、简化方法占优和失败区域。
- 留出场景不参与选择，冻结容量与策略后因果执行；固定计划与完美信息分析分别标识。
- 仅在界限与完整履约证据充分时报告最低容量点值，其余保留区间、未决或右删失。

## 10. 技术标准

- 复用现有Pyomo模型和网络库，参数放入YAML；网络解析与AC检查使用现有pandapower/PYPOWER等成熟实现。
- 正式求解前验证接口、当前许可证容量和实际模型规模。引擎、线程、算法及formulation按预先冻结、不读取目标值的重复pilot机械选择，具体版本与旧attempt历史在对应配置及记录中维护。
- 许可证或引擎变化时，重做`experiments/audit_rts_gmlc_solver_inventory.py`容量门及同一冻结pilot的选择，写入新的后继；已启动attempt不更换求解器。
- 正式MIP持久记录可行界、认证对偶界、LB/UB、absolute gap及incumbent-relative gap，目标与接受阈值运行前冻结。依赖上游结果的步骤须在对应checkpoint、manifest、certificate、全状态审计和完整frontier按合同发布并验证后执行。
- pytest与独立算术/oracle验证适用的不变量；随机实验固定并记录种子，图表由保存的结果表生成。

## 11. 文件入口与证据

当前介绍入口为[paper/drafts/README.md](paper/drafts/README.md)，中英文MD各一份并生成对应PDF；[交接](docs/plan/continuation_handoff_20261022.md)说明本轮材料与下一步。具体模型用`docs/model_spec/`、`configs/`、代码与测试核对，结果用机器可读工件确认，不能仅据README或介绍推断科学结论。进度与阻塞分别只在执行步骤和blocker登记中维护，文献与来源边界在`docs/literature/`维护。

## 12. 文件管理

- 维护既有正文与必要入口，历史版本由Git保存。Word等材料按具体交付需求同步，未同步的材料不作为当前范围依据。
- 原始数据只读，处理数据须可重建；保留失败、冻结与历史科研工件，不清理无关用户工作。
- 临时提取、渲染和构建文件使用系统临时目录并在任务结束时清理，不在仓库根目录创建临时任务目录。
- 日志进入`results/logs`，实验图表进入`results/figures`和`results/tables`，介绍与论文图表维护于`paper/`；缓存、Word临时文件和求解器临时文件不提交。

## 13. 结果与沟通

报告实际完成内容、验证、证据边界和下一步。区分模拟跨度与墙钟时间、开发验证与正式结果、局部必要条件与完整运行结论；跨源配对与合成权重不解释为同址观测或经验概率。timeout、局部失败、缺incumbent和未决不等于数学不可行；选定故障DC结果不等于工程认证。发现不支持的预设结论应据实修正，不以增加复杂度替代证据。

## 14. 当前论文完成标准

1. 阶段路径、给定计划、服务定义、设备—任务—取电映射及信息边界有明确规格与来源。
2. 功率与服务平衡、投运时序、共享预算、恢复债务和截止时间通过适用的独立检查与回归。
3. 以可比输入完成声明网络范围内的阶段比较与必要敏感性，解释瞬时限制、恢复限制、无差异和未知区域。
4. 给定建设计划与运行策略冻结后完成独立留出评价，保留缺口和右删失，不以事后重优化替代执行。
5. 输入、配置、计算状态与图表可追溯，论文按证据回答第3节问题并说明适用范围；工程性声明具有相应的完整安全证据。

本节约束当前论文交付，不替代既有冻结实验的验收与门禁，也不授予任何运行或正式发布权限。
