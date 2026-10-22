# C整链预算：保存观察与公共数值执行分层

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL。接续[保存成本交接](continuation_handoff_20261023_append_cost.md)。保留具名RTS-24主比较、两母线机制回归；本页补足公共包的结构会计和证据义务，不改变任何旧注册、源、输入或运行权。

## 条件满成功路径的完整层次

下表由现有P1源码调用图与原注册31槽重算；假设所有必要祖先成功、固定策略没有提前停止。它不是已执行数量、预计wall或资源准入。注册准备是历史一次成本，不在未来命令中重做。

| 阶段/进程 | full编译 calls/描述 | selective编译 calls/描述 | numeric/Pyomo编译 | import | fingerprints / preserve |
|---|---:|---:|---:|---:|---:|
| 原注册准备 | 2 / 285 | 5 / 16 | 0 | 0 | 1 / 1 |
| launcher完整核验 | 2 / 285 | 5 / 16 | 0 | 0 | 1 / 1 |
| worker：schedule、业务、合同、writer及本地reopen | 4 / 570 | 120 / 378 | 62 | 31 | 65 / 3 |
| 31个point child合计 | 0 | 0 | 62 | 31 | 62 / 0 |
| 独立fresh：一次完整reopen | 0 | 55 / 173 | 0 | 0 | 2 / 0 |
| 包含原注册准备 | **8 / 1140** | **185 / 583** | **124** | **62** | **131 / 5** |
| 未来执行命令部分 | **6 / 855** | **180 / 567** | **124** | **62** | **130 / 4** |

依据：[P1注册/调度/业务/重开](../../experiments/staged_rts24_native_probe_v1.py)、[launcher](../../experiments/staged_rts24_native_launcher_v1.py)、[v2 journal](../../src/staged_rts24_journal_v2.py)、[策略](../../src/staged_rts24_causal_v2.py)、[独立审计](../../src/staged_rts24_causal_audit_v2.py)。31个native槽中QP16/LP15，点子进程只在获专项授权后才能进入；此表没有新增native执行。

每成功point有父显式compile、子显式compile、子import重编译、父import重编译四次，故31×4=124，不是31次构模。两个完整reopen分别位于worker本地和独立fresh；fresh不求解。33个逻辑child launch（worker、31point、fresh）不确定实际Job成员数；本机Python stub可能增加成员，quiet仍须按实际HANDLE会计核验。

设T为成功接受的前缀步数、d_i为第i小时selective请求描述数。单次writer+finish或带terminal的完整reopen均有：

```text
Q(T) = 3 T(T+1)/2 + 2T selective calls
w_i = 3(T-i)+2, i=0..T-1
descriptions = sum_i w_i d_i
```

P1的h=-2..2为d=[3,3,3,4,3]，w=[17,14,11,8,5]，每通道55/173。三个业务通道及四个额外直接遍历（原准备schedule、launcher schedule、worker schedule、worker hour_evidence）得到185/583，逐小时selective访问[55,46,37,28,19]。只计算未来命令时去掉原准备的一遍。

full compiler每次在h=1/2分别物化143/142条：139个合同节点外仍构造当期参考子集。schedule调用三次，真正代表合同另调用一次，故8 calls/1140描述；31个最终数值槽与物化描述数不能混为一谈。单hour139来自一个normal C和69×(firm F、raw)，legal-X条件审核不自动增加solve。

52次audit_execution（worker35/fresh17，含空前缀审计）处理135条历史row；逐小时访问[45,36,27,18,9]。这些row还各自摘要完整prior、检查任务/cohort、Fraction和point/KKT。62次import中的行活动、gradient、reduced cost、原点和递归父经济审计尚未逐子函数穷举；131次fingerprints还读分发记录、二进制、源码和runtime，另有journal自己的runtime检查。31个独立point CAS与journal inventory/root/链、typed pack、fsync/readback、trusted prefix、日志/events/completion及OS调度都保留为实际成本节点。上述计数不是全部Python函数调用清单，未测层不得填零。

## 已有保存观测放在哪里

[原观察](../../results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/validation_report.md)为三母线解析保存h0/h1、三方法、v2→v3固定顺序、六成功/六失败/十二fresh。准备12/34、measurement186/514，共198/548；测量外部156.945949s、owned Job130.984s、quiet后处理23.037932s。完整测量树579文件1660401B；采样worker树RSS298913792B，不含外部controller。

该观察支持相同保存形状的语义与失败裁决，以及保留核验/目录/依赖身份的成本定位。它不提供公共数值模型、dual/log、31个point transport、更多cohort或五/十小时前缀的wall。P1仍冻结使用journal_v2；新v3观察不能替换P1路由。即使两小时v2阶段来自同一源码，其输入网络、记录和依赖闭包不同，也只作为诊断参照，不作可相加的公共预算分量。

P1 child argv为-B，保存诊断为-B -s；两者的受控child都由guard设置PYTHONNOUSERSITE=1。无-s不能解释为P1 child启用user-site；外部controller的真实env、argv和导入闭包仍需分别核。历史wall与当前源字节核验分开，新的静态读取不会重新验证原应用二进制/完整环境性能。

优化顺序保持：保留科学/保存核验；先定位实际昂贵路径，再在独立successor中证明operation内复用、增量结构和失败窗口。不得为了性能跨数值等待盲目缓存，或省略full point/KKT、完整旧CAS/root删除检测。P1的300s、单点10s/solver5s等仍是停止帽；31×10>300不保证全包完成。这里不给P1/P2或D/E新的ETA。

## 论文主张与四层义务

| 输出/主张 | 必要证据 | 目前含义 |
|---|---|---|
| 预固定外生路径上三方法的阶段、期限与CFE判断 | 当期P0、实际事故raw、恢复端点、策略后actual P，连续独立账本、完整journal/fresh和未知终结 | 可作为条件轨迹比较；仍需公共数值、完整时域与资源/运行门 |
| 所声明69态的完整静态DC F/X网络条件成立 | 对应小时/建成frame的normal C及所有firm F/raw，共139节点；完整残差和legal-X审核 | P1只有代表子集；不能称完整69态通过 |
| 一小时业务必要条件 | 同一设备/功耗口径下完整C与合法调用、D及可延期工作；独立精确算术 | 不生成真实债务，不等于跨时恢复充分条件；旧两母线失败保持 |
| 完整F/X跨小时合同可交付、aggregate release | 声明的反事实任务/事件序列、次数/持续/能量/休息、恢复资源、期限、必要观察与相应网络覆盖 | 仍未建立，不能由实际低负荷轨迹或139单小时节点替代 |

来源：[最小规格第4–7节](../model_spec/staged_deliverability_minimum_spec_v1.md)、[网络规格四层语义](../model_spec/staged_deliverability_network_development_v1.md)、[当前C范围](staged_deliverability_c_scope_and_budget_plan_v1.md)。论文须报告四层状态；失败与未决均为合法结局，不要求计划必定通过。条件实际轨迹的运行不以aggregate_contract_release=true为前置，但其自身数值/预算/授权仍必需；旧false不变。正面全状态网络主张要求完整覆盖，一条合格反例可否定全称命题而不描述其余状态。139和小时级完整时序都不足以授予AC、真实响应或工程认证。

有限D/E仍保留既定业务快慢达产×电网按期/延期×三方法以及必要敏感性，不能将现单一业务进度形状重命名为完整D。主/留出事件身份、开始/持续、工程揭示、任务/设备、清洁路径与共享服务规则须先固定；E在给定计划、容量、策略冻结后才揭示独立输入，不用留出选参。点数与总资源待公共代表成本确定，当前不登记D/E运行。

后续三方法十小时actual代表单元的103请求上限（21+41+41）与P2的319、全范围4273继续按[原公共包计划](staged_deliverability_c_public_numeric_package_plan_v1.md)解释为分开的设计层，不因此删改原P1/P2或扩大权限。完整反事实合同若要正面声明须独立后继，不能成为用来回避已知必要条件失败的调参步骤。

## 本次机械核算的执行合同

[纯stdlib工具](../../experiments/staged_c_workflow_budget_v1.py)只解析原P1 registration、已保存network_frames、append_cost checkpoint及其source/result pins。预先固定三入口SHA；不导入科学模块，不调用request_schedule、reference/hour compiler、model、solver/native、writer/reopen、指纹函数或下载，不创建P1目录。核13注册源、registration绑定的28个runtime source entries、五个cost源及626个已存结果文件，首尾逐字节hash，并区分静态预测与历史观测。

一次CLI机械核算，独占`results/tables/staged_deliverability_c_budget_v1_non_authoritative/audit_01`，输出audit.json≤512KiB；输入单文件≤2MiB、逻辑读取≤1800次/12MiB、合作式读取20s，阻塞OS IO不承诺硬实时。读取前限额、文件身份/类型与有限read、末端全量bookend；任何漂移/预算/解析错误即非零，不续算，不重跑旧记录。普通测试限tmp/保存元数据读取，验证前缀展开、角色/事故范围和错误pin/路径/size拒绝。根唯一writer，独立只读审查；无production seal/verdict/receipt，所有resource/formal字段保持false。

audit输出绑定本页、工具及测试；一旦保存，三源保持，修复走独立successor。它是机械证据对账，计时仅标本次metadata audit，不是新的代表性能实测；旧环境的应用二进制没有在本轮重校验。结果用于下一整链审查，C整体性能、D/E资源与P1专项授权仍OPEN。
