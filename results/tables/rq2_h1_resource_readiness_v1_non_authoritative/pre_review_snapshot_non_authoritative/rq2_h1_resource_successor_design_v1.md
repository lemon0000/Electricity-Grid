# H1 完整支持资源清单与后继实现设计

状态：非执行开发设计。继承已批准 v2 科学合同；没有生成新的运行包、lease、准入回执或科研结果。2026-10-03 用户要求继续推进，根为唯一写入者。

## 当前可复核的对象

依据 `configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml` 的已批准参数，使用 19 个 theta、100 个 alpha、E168/F24/stride24，training 为 523×28=14644 pairs/cell，holdout 为 512×28=14336。保留 training 的604个、holdout 的593个缺 follow-up pair；是否需要缺失小时由实际债务和按需跟随决定，不预先删去或记为失败。

`experiments/audit_rq2_h1_resource_readiness_v1.py` 独立绑定 v2 配置、既有完整来源窗口清单、v3 exact outer、运行清单和独立 post-run 复核。由窗口逐项重算支持量，因子展开 theta 和 alpha，产生可随机索引的完整潜在证据义务目录：

| 对象 | 数量 | 含义 |
|---|---:|---|
| training cell-pair | 27,823,600 | 全部支持审计身份 |
| training 四臂对象 | 111,294,400 | 各臂结果身份，不是求解次数 |
| training 潜在网格点 LB/UB 义务 | 22,481,468,800 | 上项×101个D×2类证据，未调度；不要求逐点执行 |
| holdout 条件评价对象 | 108,953,600 | 仅在相应 training 可行 UB/具名策略冻结后评价，不乘D网格 |

目录使用完整 axes 与明确 mixed-radix 顺序，无需物化数百亿行；`obligation_at` 可访问每个身份。默认状态是 `not_scheduled_no_certificate`，未提供的 solver task、causal key、training UB 和证书为 null。这些身份只供审计，不得进入业务策略或作为共同计算复用键。

LB 仍需同合同、覆盖全部允许因果策略的下界证明；N/C/J 的 UB 仍需完整 training 因果策略和实际电网 witness；B6 UB 只属两条独立因果规划轨，B6 共享实际执行另行评价。当前目录没有证明任何 LB/UB。

## 资源差额与复用边界

v3 native 单小时实际完成232 stages，整体 Job wall2744.984s，峰值 Job commit269524992 bytes，运行逻辑文件20938085 bytes。其 fresh reopen 和完整链已复核；这是一个 training 原点的一次观测。

当前通用16MiB/stage内容上限使一条192h normal链的内容 cap为774088294400 bytes（约720.93GiB），44544个阶段槽位。这个 cap不含完整物理分配、scratch、额外archive overhead和reserve，也不包含Rref/A。审计时磁盘剩余量另以时间戳保存；若 cap 已超过该快照，当前“逐槽全量预留此cap”的方案不能据该卷通过准入。cap不是最低实际存储需求，单小时写入量也不是未来上界。

工具同时保留两个明确条件场景：每pair只生成一条公共normal前缀（须先验证复用），以及每cell-pair在一个容量探针下重复生成normal。两者都不是实际运行清单、必要求解数或耗时预测。独立hour Job的3600s声明只是条件预算算术，不为未实现的192h parent提供测量证明。完整研究的solver calls、wall、disk和可执行manifest均为null。

N/Rref独立于alpha、theta、D和arm，只允许以当前可见输入、前carry、模型/规则/solver身份形成计算键。跨pair、重叠窗口和相同timestamp均不能自动合并。实际A含各臂历史；没有逐边等价证明则不折扣资源。目录保留依赖family，但没有声称已生成实际的causal-key DAG：`verified_reuse_edges=[]`、`analytic_exclusion_proofs=[]`、`omitted_identities=0`。后续解析排除须覆盖被省略身份并绑定证明，不能将未计算项变成零成本的成功结果。

## 后继实现的验收顺序

1. **专用序列化上界。** 对H1成功与失败通道逐字段约束，绑定实际模型891变量、最多1211约束、UID长度、浮点编码、运行字段及错误记录语法。从exact serializer得到可复算的最坏字节上界，再设专用cap。1MiB只能作为开发目标，当前没有获证的cap数值。writer、readback、fresh reopen、资源算术必须使用同一版本化cap；超限拒绝，不截断原始witness，不修改旧16MiB工件。失败信息若不能给出有限上界，必须保留独立有界失败通道或继续使用原cap并报告准入失败。
2. **分段时钟。** 新版本worker以单调纳秒时钟记录source/build、native optimize、native capture/转换、独立审计、SQLite、anchor、terminal/fresh reopen等阶段。嵌套span只按叶子exclusive时间求和，父子层级不得重复计费。每个span绑定request/stage/进程/时钟域、开始/结束和状态；异常保留未闭合span并标为unknown，不能填零。worker跨度与其自身闭合，父controller/Job跨度另列，跨进程未证明的时钟关系不得相减。Gurobi Runtime保留为solver自报诊断，不能替代monotonic分类。记录本身的I/O和未分类余量也须登记。
3. **完整来源parent。** 单小时v3的 `hours==1` 与 `relative_hour=0` 保持；旧short parent保持。新parent先用小合成和保存raw验证0..191的carry连续性、384父events/385父anchor、完整44544个槽位声明、按需缺尾处理、每小时独立Job、无retry和失败poison。不能把已有原点witness复制成后续小时的有效解。
4. **Rref/A及证明任务。** 复用已有科学规则建立各自shape、阶段数、序列化、wall/commit/disk合同与合成验证，完成实际causal-key依赖图；容量LB/UB的算法任务另列。normal单链不能替代这些部分。只在task manifest和合法复用quotient确立后合计全任务资源。
5. **准入及资源pilot。** 对具体volume合计全部保留archive、scratch、overhead和reserve；串行commit取峰值另加supervisor/reserve，wall计全部任务及分类余量。未实现物理预留或hard disk quota时保持对应标志false。按agent.md第7节完成pre-seal、seal和全新official审查后，才提交具体资源pilot的运行请求。

## 冻结验收矩阵

- v2参数、完整支持和D端点0/1保持；拒绝旧46-cell计数、重复窗口、删缺尾、跨split拼接、布尔整数、网格端点不整除及OAT重复anchor。
- 因子目录首尾、跨probe/arm/cell边界可索引；holdout不乘D/LB/UB；任何身份的未生成carry/证书保持null。
- 所有复用/解析排除有逐边或覆盖证明引用；无证明不计折扣。同timestamp、隐藏ID、未来后缀或业务坐标不能偷换causal key。
- cap覆盖成功/失败channel及边界，超限、短写、readback不确定全部fail closed；仅观测最大raw大小不能替代上界证明。
- timing正常/异常/nesting/时钟回退/跨时钟域/未闭合span/重复stage均有反例测试；无闭合不得颁分项预算证据。旧2440s不能由offline2264s或Job总wall相减自动认证。
- parent验证source pin、carry、gap/duplicate/reorder、按需尾部、独立fresh owner和失败窗口；未调用solver的测试不得记native成功。
- Rref/A或完整LB/UB工作量任一缺失时，完整资源准入保持关闭。
- 保留v3的1695个封存成员和251个运行文件，以及旧v2全部工件；该工具与测试位于新增路径，不改sealed source closure。

本交付仅完成可索引义务目录、条件算术和后继验收设计。专用cap证明、分段timing接入、192h parent、实际reuse DAG、Rref/A与LB/UB实现仍须按此矩阵开发验证；不将设计完成登记为实现或准入完成。
