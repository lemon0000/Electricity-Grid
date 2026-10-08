# 方案 A：动作前清洁电额度与完整训练支持诊断

2026-09-29，DRAFT_NONAUTHORITATIVE。用户已明确授权实施先前审阅的方案 A 独立映射候选及完整支持诊断。
本组件采用 `y=R*w`，四臂共同使用当前小时动作前额度；保留最低双向物理容量 D、训练支持、
原始来源及缺尾窗口。此次授权不注册 E/F、deadline、预算、联合服务新定义或具体正式实验协议。

## 精确映射与来源包

`cfe_preallocation.allocate` 仅接显式 exact 字符串或 Fraction。根据已映射的 w、源 alpha=1
缺口及目标 alpha 计算 R，输出不可变 `PreallocatedCFE`：

- allowance `y=R*w`；raw request `q_C=max(w-y/alpha,0)`；surplus `s_C=max(y/alpha-w,0)`。
- raw 与 effective request 分开保存；原绝对阈值 1e-6 在缩放后应用，边界归零不等于精确比例达标。
- q 不因 f、D、grid request、策略或 arm 改变；surplus 与同一 y 绑定，禁止独立篡改。
- 额度不跨小时结转。R 是派生基准，w 来自声明的线性无闲置功率映射，均不能升格为采购或实测供电。

`source_pair_preallocated` 使用独立 `PreallocatedPairDeclaration` 和 wire schema，核验完整来源窗口
身份及逐行时钟。继续采用既有负载投影规则，raw>1 或正值投影为零均保留原行并令整包 unresolved。
新小时包同时保存 allowance、raw/effective request、surplus 及各级身份；不生成旧 ContinuationHour，
不允许旧新 declaration 混用。source-pair 完整身份是审计信息，小时额度只由当前输入计算；
未来来源改变不会改变当前 allowance。单独小时 dict 不构成可执行输入或认证。

`necessary_conditions` 保留现有 additive 请求账的四臂诊断：network/CFE 分别检查；joint 检查合计；
B6 规划两账分别检查、实际共享合计另验。单分量与合计的有效阈值分类不一致单列
`separate_shared_activity_mismatch`，不能据分量归零静默通过。

## 完整条件训练支持

`audit_rq2_preallocated_training_support_v1.py` 固定既有候选、cell清单、coverage及源包hash，
保留 conditional E168/F24/stride24 覆盖中的全部 training power/workload 窗口及缺尾信息。
对每 cell 的14,644个候选Cartesian配对逐一检查登记期CFE必要条件；按12组相同alpha/f坐标
压缩重复算术，记录每组所覆盖cell_id及完整首反例offset矩阵。其他cell参数不进入这个瞬时条件，
不能据此声称它们在完整时序上等价。仅检查CFE，未提供grid reference，不评判联合阈值分解或电网。

有反例意味着具名候选下某登记小时的effective CFE请求大于f*w；null只代表已映射登记小时中
未找到这类反例。投影未决行及窗口单独保留，不作为零负载或服务失败。恢复、期限、预算、
因果策略及后续期履约均未求解；缺尾标记保持，不换算成失败率或unresolved概率。
training全支持不要求读取holdout结果；本次不评价holdout，不重新定alpha/f来取得有限曲线。

当前报告：`results/tables/rq2_cfe_preallocation_v1_non_authoritative/training_support_verified.json`。
初版training_support.json保留；补入阈值漂移门及source-pair/boundary身份后，首反例矩阵和计数未改变。
alpha=0.5/f=0.5时14392个配对有反例、252个没有该反例；其余11组全部14644个有反例。
每个46-cell至少有一个反例，故在保留当前全支持硬履约要求时仍不能产生CFE相关规划账的有限D。
这是解析必要条件诊断，formal_result=false、solver_calls=0；不是正式frontier或经验联合概率结果。

## 验收矩阵与后续接口边界

1. exact功率平衡，w=0、R=0/1、目标边界、循环小数；q与surplus互斥且共用y。
2. 原有效阈值、分量/合计分类、不截断请求到f*w，四臂/B6分账与共享诊断。
3. 来源身份、时钟、完整行数、raw>1与正投影零，旧新类型隔离、当前额度不读取未来。
4. 小型独立算术与优化首反例搜索一致；全cell/pair inventory、来源hash和缺尾保全。
5. 既有source_pair/workload_projection及相关精确政策测试回归，旧566成员无漂移。

后续operational适配必须显式绑定pair/hour/allocation及转换记录，不能把新字典强行塞入旧封存接口。
现有部分planner/policy scalar通道仅支持built-in float；本组件不新增向上/向下舍入科学规则，
不借normal的数值容差放行。恢复12位量化仍由原策略处理，本层surplus保留exact。
完整因果容量、有限登记normal/follow-up、联合服务解释及正式运行保持各自尚未闭合的门槛。
