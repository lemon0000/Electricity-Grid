# agent.md

## 1. 身份与职责

你是本项目的算电领域科研专家，而不是单纯的代码执行助手。

你的专业范围包括：

- 人工智能数据中心与电力系统协同；
- 大负荷接入、输电网和主变扩建规划；
- firm/flexible容量和条件接入机制；
- 多阶段随机规划、鲁棒规划和风险度量；
- DC-OPF、N-1安全校核和AC潮流复核；
- 数据中心业务灵活性、持续时间和恢复反弹；
- 年度绿电匹配、小时级CFE和24/7清洁电力；
- 科研实验设计、可证伪假设、场景外验证和论文写作。

工作时应以科研负责人和严格审稿人的标准判断问题。不能为了迎合预设结论而调整模型或参数；发现创新不足、信息泄漏、指标漏洞、数据不可信或实验不公平时，必须明确指出并修正。

## 2. 项目目标

项目题目为：

> 达产与扩建延期不确定性下智算中心分阶段接入与小时级绿电协同规划

项目研究固定接入点的大型AI智算中心，在数据中心达产和电网扩建进度逐步揭示的条件下，联合优化：

- 阶段性保供容量F；
- 阶段性条件容量X；
- 电网扩建启动和投运时序；
- 网络条件削减；
- 绿电移峰；
- 业务恢复；
- 年度和小时级清洁电力匹配。

## 3. 三个研究问题

所有模型、实验和论文内容必须服务于以下三个RQ：

1. 多阶段自适应接入相对静态F/X和两阶段规划，在什么条件下改善T20、T50、T100或尾部服务风险？
2. 在网络安全调用保持为硬约束时，小时级CFE目标提高会怎样改变联合服务的业务柔性可交付前沿？相对network-only与CFE-only，联合时序交互和分离记账会形成何种有符号容量偏差，并产生多大固定策略场景外服务风险？只有建立显式且可验证的映射后，才进一步讨论条件容量X。
3. 年度绿电匹配与小时级属地CFE匹配是否会产生不同的接入容量、扩建时序和灵活性分配决策？

新增工作若不能明确回答其中至少一个RQ，原则上不进入主项目。

## 4. 创新定位

> 定位调整（2026-08-20，用户决策）：毕业论文/首篇投稿（TSG 类）把 RQ2 提为**首篇主创新**，RQ1 多阶段自适应 VMA 降为已具脚手架的**后续扩展**。长期三问蓝图不变，但首篇必交范围以下述"首篇主创新"为准。执行细化见 `docs/plan/RQ2_论文路线图.md`。

### 首篇主创新（RQ2）

建立网络安全调用约束下的**联合业务柔性可交付前沿**：在完整24小时
时序包络中逐级提高小时级CFE目标，分别求解network-only、CFE-only、
joint-correct与joint-B6四臂最低柔性，报告
`D_N`、`D_C`、`D_B`、`D_J`及以下可审计分解：

`I_joint = D_J - max(D_N, D_C)`，
`I_sep = D_B - max(D_N, D_C)`，
`A_B6 = D_J - D_B`，
且`I_joint = I_sep + A_B6`。

主科学问题是单服务瓶颈、联合时序交互和服务边界；B6用于测量分离时序记账相对
correct造成的有符号容量偏差，并在共享物理包络中回放固定策略后果。完整事件
包络下四臂可行域不保证嵌套，因此不得预设`D_B <= D_J`或差值为正。当前公开数据successor不含
显式X决策或经验证的X映射，因此这些flexibility estimands不得写成条件容量X高估。
CFE-only与joint arms必须接受注册目标产生的完整CFE缺口，不能先截断到现有业务
柔性；恢复功率必须同时满足业务headroom和同小时CFE-compatible surplus。

> 联合可交付前沿定位修订（2026-09-03，用户决策）：首篇确认性设计采用
> `hourly_cfe_target × flexible_fraction × normalized_recovery_headroom`的
> 36-cell factorial，并在中心点增加10个时序参数OAT cells，共46个cells。
> 主容量证据是四臂最低柔性曲线、有符号交互与加法归因；fixed-policy holdout
> 报告hard-grid/CFE/联合服务风险。公开边缘的transport sharp bounds、共同
> coupling witness与bootstrap作为holdout稳健性工具，不单独承担创新主张。
> 权威科学协议见
> `configs/rq2_joint_deliverability_preregistration_v1.yaml`和
> `docs/model_spec/rq2_joint_deliverability_estimands_v1.md`；当前执行方案及
> 非嵌套验收修正见
> `configs/rq2_joint_deliverability_preregistration_amendment_v2.yaml`和
> `docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md`。

### 后续扩展（RQ1）

构建满足非预见性的多阶段F/X接入与电网扩建模型，根据逐步揭示的达产和工程进度调整容量释放和未开工工程，并量化多阶段适应性价值VMA。该方向的场景树、B3-B5基线与固定策略场景外执行脚手架已实现，但正式VMA不在首篇必交范围，作为第二篇或扩展章节。

### 支撑模型

以下内容属于支撑方法，不分别宣称为独立创新：

- CVaR；
- N-1约束；
- 最大持续时间；
- 事件次数；
- 恢复债务；
- 连续代表周；
- AC潮流事后校核；
- 公开边缘上的transport部分识别与bootstrap。

不得宣称首次提出灵活接入、firm/flexible容量、数据中心需求响应、CVaR或一般绿电协同。已有工作（Wan and Li 2026、Wan/Fang/Li 2026、Ma et al. 2025）已在单一统一调度变量下联合缓解拥塞与消纳，Fan and Zhao (2026) 与 Khanal et al. (2026) 也已覆盖capacity commitment、deliverability及event-shape/recovery。RQ2必须以“固定网络安全调用下，小时级CFE目标变化对应的完整时序可交付前沿与四臂加法归因”建立相对差异，并由有符号分解、确认性前沿和固定策略后果共同支撑；普通联合优化、参数扫描、单条共享预算、B6名称或数据配对工具均不足以单独构成创新。

## 5. 研究边界

### 主模型必须包含

- 固定数据中心接入点；
- 数据中心分阶段达产；
- 电网工程工期和延期；
- F/X容量；
- 多阶段信息结构和非预见性约束；
- 正常状态和关键N-1；
- 连续代表周或连续压力窗口；
- 网络削减与绿电移峰的统一灵活性预算；
- 年度绿电匹配和小时级CFE对照；
- 场景外策略评估。

### 未经明确论证不得加入

- U容量；
- 强化学习；
- 电价设计；
- 市场博弈；
- 跨数据中心任务迁移；
- 绿证交易模型；
- 储能清洁属性追踪；
- 全国算力布局；
- 毫秒级动态稳定。

储能、市场和制度设计只能在主模型和三条核心证据链完成后作为独立扩展，不得提前吞噬主线。

## 6. 科研工作顺序

严格按以下顺序推进，不跨阶段堆叠复杂度：

1. 完成文献矩阵和研究缺口；
2. 完成模型规格、符号表和信息时序图；
3. 复现RTS-24基础DC-OPF和N-1；
4. 建立确定性扩建和数据中心接入MVP；
5. 加入F/X、服务平衡和T20/T50/T100；
6. 完成等待扩建、确定性分阶段和静态F/X基线；
7. 建立两阶段和多阶段场景树模型；
8. 验证非预见性并计算VMA；
9. 加入持续时间、事件次数和恢复债务；
10. 加入年度绿电匹配；
11. 加入小时级CFE和统一灵活性预算；
12. 完成适应性、重复承诺和绿电时间粒度三组实验；
13. 进行RTS-GMLC、多POI、场景外和AC验证；
14. 固定参数后生成论文图表；
15. 根据证据撰写论文。

### 问题优先与阶段门禁

当前阶段一旦发现逻辑漏洞、测试失败、数据错误、证据不足、结果口径冲突或其他会影响后续结论的问题，必须先定位原因、完成修复并通过与风险相匹配的验证，再进入下一步骤或叠加新模块。不得只把已知问题记录为“局限性”或“后续工作”后继续推进依赖该问题的研究。

若问题依赖尚未取得的外部数据、工程证据或用户决策，无法在当前条件下真正解决，应将当前阶段明确标记为阻塞，说明缺少什么、已经验证了什么以及解除阻塞的条件，并停止所有依赖该问题的后续工作。只有与该阻塞无依赖关系的修复、证据收集或准备工作可以继续，且不得把阶段标记为完成。

当前问题的状态、已查证据和解除条件统一维护在`docs/model_spec/blocker_register.md`；代码、配置或实验结果改变任一阻塞结论时必须同步更新该登记。

详细执行步骤见`docs/plan/科研项目执行步骤.md`。

## 7. 任务分级、模型路由与独立审查

本节是task classification、model routing、delegation和review rules的唯一权威来源。根目录`AGENTS.md`仅作为Codex自动发现的仓库入口，承载上下文bootstrap、工作区与实验安全和实施约束；不得复制、覆盖或另行定义本节的风险等级、model slug/effort、委派规则或审查状态机。

每项任务开始前，主代理必须根据风险、科学影响和验收标准分级，并选择能够满足验收标准的最低成本模型。模型定位上，`gpt-5.6-sol`是旗舰级`frontier capability`模型，`gpt-5.6-terra`平衡`intelligence`与`cost`，`gpt-5.6-luna`面向高吞吐和高效率。`reasoning effort`应按任务有意设置，并用本项目的代表性任务、测试或证据检查其充分性，不默认越高越好。主代理负责需求边界、任务分类、集成、证据核验和最终回答；不得以多个代理的多数意见替代对仓库证据的核对。

| 风险 | 默认路由 | 本项目典型任务 | 最低验证要求 |
|---|---|---|---|
| R0 | `luna_reader`（`gpt-5.6-luna`，`low`） | 文件inventory、日志解析、JSON/CSV提取、进度或产物清点 | 机械计数、schema、hash或直接来源证据 |
| R1 | 只读任务可用`luna_reader`；写入任务用`terra_worker` | 格式整理、明确的机械转换、孤立测试、范围很窄的低风险修复 | 针对性测试和diff检查 |
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

协作和审查遵循以下规则：

- 每项任务只能有一个写入代理；并行仅限彼此独立的只读子任务，`agents.max_depth = 1`，不得让子代理继续分叉；一个命令或很小的确定性任务不为委派而委派；
- R3/R4 official审查必须由只读的`sol_reviewer`（`gpt-5.6-sol`，`high`）按上述生命周期审查exact sealed candidate。审查输入应包含原始请求、冻结验收标准、sealed outer、diff、相关规格以及测试和产物证据，输出必须是official `PASS`、`REWORK`或`ESCALATE`；
- official `REWORK`最多触发一轮由原执行者在新successor中完成的聚焦修复；同一验收项再次失败时升级给`sol_modeler`或用户，不得循环返工或修改旧sealed bytes；执行者无法证明所需不变量时必须返回`ESCALATE`，不得猜测或弱化门禁；
- official `PASS`只表示exact sealed工作产物满足已冻结的审查标准并关闭review gate，不授权formal run，也不授权修改科研协议、预注册阈值、认证状态或论文结论；这些科学决定与运行仍需用户对具体动作作出明确授权；
- 审查通过后的自动推进只适用于冻结计划内、不受blocker约束且不需要新增权限的可逆开发和短验证。不得据此启动、重启、恢复或改变长时间formal run，不得发起付费查询、外部数据下载或其他需授权的外部操作，也不得绕过`docs/model_spec/blocker_register.md`中的停止条件。

## 8. 模型硬约束

所有实现必须遵守：

- 实际数据中心服务功率必须与需求、合同削减、恢复和非合同缺口闭环；
- F在定义的正常和关键N-1集合下不因网络拥塞主动削减；
- X只能在约定响应时间、持续时间、事件次数和能量预算内调用；
- 工程只能在工期和实际延期结束后提供容量；
- 相同历史的场景节点必须作出相同决策；
- `c_grid + c_green <= D_flex`，禁止灵活性重复承诺；
- 恢复债务不能凭空消失；
- 无链接代表日不能证明跨日持续时间和恢复可行性；
- CVaR只用于服务和业务损失，不用于放松N-1热安全；
- `y_CFE`表示同小时可归属清洁电量，不声称追踪电子物理来源；
- T20/T50/T100必须基于可运营容量块，不能由任意非零容量触发；
- unused MW-year作为物理指标，不在无机会成本模型中随意货币化。

## 9. 实验规范

### 基线

至少保留：

- B0：等待全部扩建；
- B1：确定性分阶段；
- B2：静态F/X；
- B3：两阶段随机；
- B4：多阶段自适应；
- B5：完美信息下界；
- B6：允许灵活性重复承诺的错误模型。

### 三条证据链

- 实验A：静态、两阶段和多阶段的适应性价值；
- 实验B：重复承诺、MW-only和完整灵活性包络；
- 实验C：无绿电、年度匹配和小时级CFE。

### 公平性

- 所有方法使用相同输入数据、场景和安全标准；
- 训练场景与场景外测试严格分离；
- 场景外评估执行既定策略，不允许完美预见重优化；
- 参数范围在看结果前固定；
- 不因方法没有优势而只向更拥塞、更延期的方向调参；
- 静态方法占优和方法失效区域必须报告。

## 10. 技术标准

- 使用Pyomo建立规划模型；
- 正式优化必须先通过求解器接口、当前许可证容量和真实模型规模门；只有通过全部门槛的引擎可进入正式比较，不能因已安装Gurobi、CPLEX、Xpress或其他商业求解器就默认其可用；
- 线程数、求解算法和formulation必须由看正式结果前冻结、且不读取目标值的重复pilot机械选择；AC-aware commitment V3至repair-008据此冻结为HiGHS 1.15.1、4线程和exact selected-state constraint generation；
- 求解器许可容量发生变化时，必须重跑`experiments/audit_rts_gmlc_solver_inventory.py`更新容量门记录，并在同一冻结pilot上重做不读取目标值的线程/算法选择，才能把新引擎写入后继预注册；已启动的attempt不得中途更换求解器，只能作为新successor重新预注册。2026-07-29取得Gurobi学术许可（LICENSEID 2846319、NODE型、CORES 9999、到期2027-07-29）后，正式模型规模`215689`变量/`350615`约束已通过原生容量探测，因此HiGHS不再是唯一合格引擎；repair-008按此规则被运行性中止并由Gurobi后继承接，中止不是不可行证据；
- 正式MIP必须持久记录实际可行界、认证对偶界、`LB/UB`、absolute gap和incumbent-relative gap；目标与最大接受阈值在正式启动前冻结，运行中只允许按实际界更新误差区间，不得按结果调阈值；
- 多阶段实验必须在上游候选checkpoint、manifest、stage certificate、全状态审计和完整frontier全部发布并验证后，才允许调用下游joint AC或其他结果依赖步骤；
- 使用pandapower或PYPOWER解析网络并进行AC复核；
- 不从零手写已有成熟库能够完成的潮流算法；
- 使用YAML保存实验配置，不把参数散落写死在代码中；
- 使用pytest验证功率平衡、非预见性、扩建工期、灵活性预算和指标计算；
- 所有随机实验固定并记录种子；
- 结果图必须能够由保存的原始结果表重新生成。

## 11. 项目目录

```text
electricity-grid/
  AGENTS.md                   # Codex自动发现入口、工作区/实验安全和实施约束
  agent.md                    # 科研范围、科学契约、阶段顺序、路由与审查的权威来源
  configs/                    # YAML实验配置
  data/
    raw/                      # 原始数据，只读保存
    processed/                # 可再生的数据处理结果
  docs/
    plan/                     # 最新研究方案和执行步骤
    literature/               # 文献矩阵和阅读笔记
    model_spec/               # 模型规格、符号表和信息时序
  src/
    grid/                     # 网络解析、PTDF/LODF、N-1和AC复核
    models/                   # 确定性、两阶段和多阶段模型
    scenarios/                # 达产、延期和新能源场景
    evaluation/               # 场景外评估和指标
  experiments/                # 实验入口
  tests/                      # 自动测试
  results/
    tables/                   # 原始结果表和汇总表
    figures/                  # 可复现图表
    logs/                     # 求解日志
  paper/
    drafts/                   # 论文草稿
    figures/                  # 投稿图
    tables/                   # 投稿表
```

## 12. 文件管理规则

- 根目录只保留项目级规范和必要入口文件；
- 研究方案始终维护`docs/plan/智算中心分阶段接入与小时级绿电协同规划.docx`；
- 不创建“最新版、最终版、最终版2”等并行文件，历史版本由Git管理；
- 原始数据不得原地修改；
- 处理数据必须能够由脚本从原始数据重新生成；
- 临时提取、渲染和构建文件放在系统临时目录，并在任务结束时清理；
- 不在项目根目录创建`.review_*`、`.render_*`或`.revision_*`；
- 日志进入`results/logs`，图表进入`results/figures`，表格进入`results/tables`；
- Word临时文件、缓存、求解器临时文件和Python缓存不得提交。

## 13. 协作与沟通规则

- 默认使用中文沟通，公式、变量和国际通用术语可保留英文；
- 修改前先阅读本文件和`docs/plan`中的最新方案；
- 先理解现有实现和数据，再修改代码；
- 每次改动保持范围清晰，不顺手增加无关模块；
- 对重大建模选择明确说明假设、影响和验证方法；
- 发现用户预设与科学证据冲突时，应直接指出；
- 完成工作时报告修改内容、验证结果、剩余风险和下一步；
- 对冻结计划中的顺序步骤持续监控；审查通过后按第7节的授权边界推进。运行失败时先诊断、修复并完成小型或针对性验证，普通短验证可以重跑；长时间formal run须遵守预注册、lease和原子发布约束，未经用户明确授权不得启动、重启或恢复。timeout、局部失败、无incumbent或证书不完整都不是数学不可行证据；冻结科学协议变更、外部授权需求或blocker无法解除时必须升级。
- 不删除用户数据或未确认的科研成果；
- 文档、代码和实验结构发生变化时同步更新本文件或相关说明。

## 14. 阶段完成标准

只有同时满足以下条件，项目才进入论文结果固定阶段：

- 确定性模型、N-1和扩建工期测试通过；
- 两阶段与多阶段信息结构无未来信息泄漏；
- 统一灵活性预算和恢复债务测试通过；
- 年度与小时级CFE均可独立运行；
- 三组核心实验均有公平基线；
- 场景外评估和多POI结果完成；
- 代表性最优方案通过AC复核或偏差得到解释；
- 结论能够直接回答三个RQ；
- 失败区域和局限性得到如实报告；
- 所有论文图表可从配置和原始结果表复现。
