# 共同参考网侧请求与逐臂实际状态：设计草案

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE_DESIGN。
本页为下一开发项的具体候选机制；未注册正式请求、改变四臂estimand或授权正式运行。
复用`event_disclosure`、`grid_information`、`current_grid_step`与`current_grid_short_solve`。

## 1. 请求来源与实际状态分开

建议建立四臂之外唯一的ReferenceGridCursor。相同输入、normal计划及参考初态下，四臂在小时t共享同一raw请求G_t。
reference仅接受当前已揭示网络条件、共同baseline B_t及自己的上一小时实际参考出力；
不接受arm、CFE target、业务容量、业务债务、各臂实际功率或后续故障。

reference轨迹采用“共同baseline、无CFE业务动作、无业务恢复、此前参考请求全履约”的反事实机制。
其状态不是四臂之一的实测状态；与各臂ActualStepCarry分别初始化、分别验收并保存身份。
各臂实际carry只影响该臂固定功率网络检查，不反馈下一小时共同G。
否则策略导致的actual generation差异可能改变后续请求，四臂容量差将混入不同调用序列的影响。

正式采用这一参考机制及其初态需要在新科学协议中明确；源数据没有观测到该反事实reference dispatch。

## 2. 当前参考问题

令F_t(s_ref,z_t)为当前已实现的固定normal commitment、response、actual ramp、repair、DC拓扑及节点平衡约束集。
用变量P_ref替换该模型的固定DC功率，求解：

```text
minimize G = B_t - P_ref
subject to (p, theta, flow, P_ref) in F_t(s_ref, z_t)
           0 <= P_ref <= B_t
```

保留physical/connected界，不允许按未知CFE或恢复轨迹改变参考负荷。
这一LP不是对固定功率可行性作单调二分；全部实际ramp和发电下界仍约束P_ref。
若无已验收结果，保留原生状态并停止参考链，不发布G，不用zero-DC失败推导更大减载需求。
请求采用后述数值selector得到的G及其可行见证；原生区间另存，不称数学精确最小请求。

已有解析反例：normal=20、prior actual=25、ramp=10 MW/h、外部负荷0、baseline=20 MW。
DC=20可行，DC=10违反下降ramp 5 MW。当前核验结果见`rq2_causal_grid_request_contract_v1.md`。
额外CFE减载不保证网络更可行，恢复也可能超过网侧可供上限；各臂实际功率必须独立验收。

## 3. 原加法分账与适用性

保持业务实际功率恒等式：`P_actual = B - g_served - c_served + recovery`。
物理网络读取总P_actual；由CFE动作带来的物理减载效果不转记为g_served，不抵消grid shortfall。
相同G在四臂保存为raw字段，义务投影沿用各臂定义。CFE-only的grid obligation为0，
应标`grid_service_applicable=false`及`grid_failure=null`，不能把0义务当成共同raw请求已履约。
其实际功率网络检查单列。是否把这类物理检查纳入D_C正式容量对象，属于必须明确选择的科学口径；
不能借本接口实现悄悄扩大D_C的约束集合。

MW至业务归一化单位须有显式固定映射，原G、映射前后精确值和数值表示差异需可审计。
现有接受浮点原观测的接口不能自动视为支持任意精确有理数请求；适配器必须验证守恒与原阈值，禁止静默裁剪。
归一化单位U必须显式给定且严格为正，使用G/U，禁止改为G/B。B=0时参考域只含P_ref=0；
只有该点有通过验收的见证才提供G=0，否则request unresolved；U缺失或非正是输入拒绝。
若正MW请求除以U后落入既有SERVICE_TOLERANCE、会被业务策略置0，应停止为resolution-unresolved。
唯一候选例外须显式注册：对同一参考问题独立审计P_ref=B的完整赋值，并用G>=0的代数下界，
建立目标为0的候选；随后显式canonicalize为0，原正raw数值、原求解证据及转换原因保留。
这仍受已注册数值可行性验收限制，不升级为精确实数最优证书。缺少上述证据或规则时不得转换，
也不得向上调整请求。单位与阈值的兼容性是适配验收项。

## 4. 数值dispatch选择候选

零目标solver的任意可行赋值不能直接充当已冻结策略。建议DRAFT使用预先声明的数值词典序规则：

- reference：依次最小化`(G, sum_g abs(p_g-p_plan_g), p_g按UID排序)`；
- 各臂fixed-power actual：依次最小化`(sum_g abs(p_g-p_plan_g), p_g按UID排序)`。

绝对偏差用LP辅助变量表达；所有顺序、solver/runtime、固定容差、gap门和规模预算在执行前绑定身份。
各级要求typed optimal termination、唯一native solution record及完整loaded label inventory、fresh约束审计、finite LB/UB/objective，
且满足事前固定的absolute/relative gap门。通过后把该级canonical incumbent值固定给下一模型。
这里的唯一record不代表数学唯一解。solver status/termination一致性、problem/solver记录数量、objective sense/value
和每级fresh模型中全部历史固定值的重审，均须进入实现验收，不能只检查一个optimal字符串。
这定义版本绑定的numerical_lexicographic_dispatch_selector，不证明数学精确实数词典序最优。
任一级timeout、feasible-only、缺界、gap越门或下一阶段固定值失配均使selector unresolved；
不能退回上一可行incumbent、放宽容差或临时变更变量排序。

generation各分量被逐级确定后才生成carry；flow/angle可保留非唯一，因为它们不进入当前carry递推。
未来若新增依赖flow/angle的状态，须扩充选择和绑定合同。数学精确lex证书需另行exact/rational验证。
现有短求解对timeout可行incumbent提供物理见证的能力保持；此selector采用更严格完成条件，两者不可混用。
多级求解须共享总calls/time/scale预算，不能通过每级重置预算绕过限制；全网规模与正式runtime仍待验收。

## 5. 小时事务与拒绝语义

1. 验证共同当前来源、normal信息和disclosure与reference前态相邻。
2. 参考LP及selector全部通过后生成当前共同请求及reference后继；该链与任一臂成败分开。
3. 对每个仍活动的臂，从最后已提交业务cursor生成immutable business candidate，保留原请求与短缺。
4. grid义务不足时仅归档candidate，业务与该臂网侧carry均不提交，后缀未评价。
5. 业务candidate合法时将exact P_actual送入该臂当前网络selector。两边同时通过才发布
   `(next_business_cursor, next_actual_grid_carry)`；先前对象保持不变。
6. 网络selector unresolved时保留赋值/原生状态及业务candidate，两个实际状态均不推进。

输入来源错误、业务义务拒绝、数值selector未完成和已审计物理残差分列。
未找到合法赋值不是已证明物理不可行；停止后无实际观测的小时不能进入经验失败或成功分母。
同小时reference/request/business/network子步骤共用source hour，不重复计暴露。

## 6. 开发顺序与验收

1. 将当前fixed-power模型扩展为独立reference问题，保留旧模型字节；解析例检验功率区间及上述非单调反例。
2. 开发总预算约束下的数值selector与逐级native/loaded/canonical证据；真实微型LP与fault injection检验每一级失败。
3. 定义ReferenceGridCursor、共同请求及exact MW适配，验证同前缀不同未来得到同请求/状态，且arm/alpha/D不能进入reference身份。
4. 连接immutable业务candidate与actual网侧事务，验证网侧失败不提交业务债务、四臂raw请求相同、分块与整段推进一致。
5. 再做训练容量绑定、正式共同输入包与完整服务closure，维持holdout隔离。

不可缺的反例包括：参考无已验解、timeout、非唯一generation、实际臂状态分叉、CFE额外削减导致down-ramp失败、
恢复负荷超网侧界、CFE-only适用性、来源gap、业务成功但网络未完成、selector后期失败和跨chunk不重置。
科学授权项为reference反事实定义、请求含义与co-benefit分账、normal信息集、数值selector及容差、
四臂容量与风险中的物理适用性；本草案不替代这些正式选择。
是否每小时都生成参考请求（包括无事故小时）与实时reserve范围也须显式注册；本页不将旧事故小时调用范围自动扩大。

## 7. 设计核查

只读领域代理核对现有接口并提出上述候选；独立sol_reviewer对设计与非单调反例复核，
未发现阻止下一DRAFT实现的实质问题。复核提出的单位分辨率/零baseline、唯一record含义和数值证据要求已补清。
本页没有执行selector、生成reference包、选定正式数值或关闭科学门。该核查不是official verdict或运行授权。

第一步LP与赋值投影审计后续已实现为`reference_grid.py`，见`rq2_reference_grid_v1.md`：44项新测试及193项相关回归通过，
限定pre-seal identity finding修复闭合。该原始赋值审计不产生selected request/next reference state。
后续`reference_selector.py`已实现总预算内逐级数值选择与受控ReferenceGridState，详见`rq2_reference_selector_v1.md`。
前级目标锁定采用不超过absolute gap的显式lock_tolerance_mw，L1按实际绝对偏差复算；正式参数仍待注册。
各臂fixed-power actual selector、共同请求精确单位适配和小时事务仍未连接，不据reference子模块完成而关闭完整链门。

后续actual selector已开发为`actual_dispatch_selector.py`，46项新测试及220项相关回归通过，
独立46项pre-seal验证通过，限定范围无开放实质finding，见`rq2_actual_dispatch_selector_v1.md`。
从origin起绑定数值policy，result显式保留exact prescribed power；仍待共同请求适配及业务/网络小时事务连接。

后续共同请求适配已开发为`common_request_adapter.py`，以Fraction直接连接已有精确业务路径；
U绑定normalization，审计侧normal/prepared/current来源强制business split/seed/hour一致。
38项targeted/223项相关回归及独立38项验证通过，来源finding闭合，见`rq2_common_request_adapter_v1.md`。
下一项为跨小时固定mapping及reference、业务、网侧状态的小时事务，不把单独prefix当作reference来源证据。


## 2026-09-20 四臂连续小时协调开发

`episode_coordinator.py`已连接单对象内存中的四臂共同请求链、固定策略、公平物理/业务初态、整窗最坏预算预检和逐小时预留。
保留各臂独立停止；末小时保留恢复债务，窗口消费完不代表完整履约。完整小时输入、候选、外层提交、已开始/未完成/未开始臂分别记录。
`hourly_transaction.py`同步区分dispatch执行异常与求解前网络输入拒绝，缺失执行结果不猜零调用。
独立pre-seal 31项episode（44.69s）及23项hourly（32.10s）通过，findings闭合；九文件323项相关回归通过（170.08s，exit 0）。
完整合同、开发hash和命令见`docs/model_spec/rq2_episode_coordinator_v1.md`；旧22/291项记录保留为此前版本证据。
下一项为完整episode证据的持久化及无solver重放，再处理跨进程唯一性/恢复；现有业务prefix不能替代reference→mapping→business→actual全链。
本组件仍为DRAFT_NONAUTHORITATIVE。完整连续输入、训练容量与四臂策略绑定、正式规模、恢复/right-censoring及科学/正式运行门未关闭。
所有初态与未识别业务参数保持机制声明；没有新增真实运行观测、正式结果、容量/安全认证或formal-run authority。
