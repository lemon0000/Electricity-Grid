# 连续共享固定容量策略 v1

2026-09-16，`DRAFT_NONAUTHORITATIVE`。新策略由结果前给定的机制参数决定当前动作；不是正式训练容量证书或正式连续协议。

## 复用与证据边界

沿用原请求/执行响应分账和grid短缺candidate-only停止语义，新增薄`aggregate_response.py`精确分量核算，复用原cohort/物理校验；
不修改旧full-request策略、B6分离规划后继、固定24小时holdout实现或冻结结果。
参考`rq2_joint_deliverability_estimands_v4.md`§4.1/§9：grid、CFE、恢复词典序，
`q_t-q_previous <= min(ramp*dt,ramp*response_time)`作用于每个小时的向上变化，下降不受该上界限制。
旧hour23强制inactive及terminal debt评分不移植；输入结束时原样保留事件、debt与期限状态。

容量、min-event、ramp、response及最大恢复功率在第一条输入前固定。`CapacityObservation`每次只接受
一个原`CurrentObservation`及当前可用柔性；无未来数组、horizon长度或可修改policy回调。
四臂按各自请求投影执行同一共享动作集，B6这里只表示其容量来源臂，不执行两个分离物理账。
新policy身份与旧B6/组合后继不同，不将效果写回旧策略或D_B。

`committed_capacity`当前只能标为mechanism_assumption，并带显式`capacity_declaration_id`。
测试YAML中`training_capacity_certificate=null`：这已提供事前固定容量的接口绑定，但未完成真实training产物验签、
选择规则、cell/arm/input hash一致性或train/holdout loader。不能把声明标签称作训练证书。
配置`configs/rq2_continuous_capacity_policy_v1.DRAFT.yaml`只提供合成测试fixture，不是formal输入。

## 固定选择规则

小时长度沿用现有1h，账期为显式单一nonrolling period，初始化显式zero-history，chunk不reset。
活动资格按已提交事件状态、最大duration、event count与minimum rest判断。当前调用上限为：

```text
cap = max(0, min(committed_capacity, current_available_flexibility,
                 original_call_limit, baseline_power,
                 (energy_budget - exact_cumulative_incurred)/dt,
                 (debt_limit - exact_current_debt)/dt,
                 exact_previous_call + ramp * min(dt, response_time)))
```

上小时活动调用量从对应birth cohort的精确incurred取得，避免float求和误差改变ramp边界。
此处不以数值验收容差增加可调用容量；最大化定义在原参数限额内。

活动资格允许时，令`q_star=min(cap,g_req+c_req)`。若`q_star>=minimum_event_power`且
`q_star>SERVICE_TOLERANCE`，则`g_served=min(g_req,q_star)`、`c_served=q_star-g_served`；否则两项均为0。
这直接给出连续行动集上的词典序最大响应。grid/CFE分别不超过各自有效请求，不提供网络超额响应。
原始请求和effective分解歧义处理与partial合同相同；执行响应的两个分量则按精确Fraction保留，
只对总q判断活动，不能对微量served分量再次清零。例如cap=3e-6、两请求各2e-6、min-event=3e-6时，
执行grid=2e-6、CFE=1e-6，精确新增债务为3e-6。
`q==0`或`q>Q(str(SERVICE_TOLERANCE))`的活动边界与响应合同身份一起绑定policy_id。
原`partial_response.py`保持不变，新精确接口单独区分；不能用旧逐分量处理改变本策略的连续行动集。

若选择调用，r=0，实际功率=baseline-grid_served-cfe_served；否则使用既有known EDF/unknown FIFO选择恢复，
受固定最大恢复功率与当前business/CFE-compatible/max-power/debt-over-eta共同限制，沿用既有恢复精度保守量化。
`recovery_decimal_places`（0–12）只作用于恢复，不量化调用响应；转为Q(str(r))后以baseline+r重新计算精确功率。
网络单服务臂仍只需business恢复头寸；其他适用CFE的臂保留CFE-compatible约束。
未满足CFE调用不新增债务，可在实际inactive时恢复旧债务；grid短缺超过原容差则候选不提交且停止后缀。
局部业务状态的提交不等于完整履约，仍保留CFE短缺、到期miss与unknown状态。

## 身份与状态链

policy_id绑定arm、容量及声明ID、额外动作参数、恢复精度、aggregate响应合同/活动边界、规则、机制身份、原envelope、初始化与开放边界规则。
初始cursor必须等于该arm/envelope/anchor/period下规范的显式zero-history初始化。
每小时record绑定固定spec、before、原观测和current_available，重算确定性动作与aggregate record。
失败不推进，不允许其后拼接记录。不同chunk划分和未读取的未来修改不能改变之前的决定。
此为本地一致性校验，不是防篡改签名；正式composer/export仍须绑定原观测与executed投影，不能剥离外层记录。
原source保持原类型；executed投影使用Fraction并需按分子/分母编码，不可直接浮点化写成原观测。
物理浮点状态与精确cohort仍使用原1e-12对账门，未放宽长期累计误差验收。
单小时grid shortfall超过容差会停止；未来完整指标还须累计所有已评价shortfall能量，不能用逐小时布尔值代替累计短缺。

## 验收例与未闭合门

fixture D=.5、available=.4、min-event=.0625、ramp=.25/h、response=.5h，因此启动cap=.125。
h1请求g=.125/c=.25，执行(.125,0)，debt=.125；h2同请求，执行(.125,.125)，debt=.375；
h3/h4无请求，分别恢复.3125/.15625，在eta=.8下债务清零。若h1网络请求=.25，则最多声明.125的候选，
保存grid短缺后停止；不能将其改称网络安全履约。h23/h24均有CFE请求时可跨边界维持同一事件。

剩余正式准备包括：continuous科学协议、真实训练容量/源输入闭包、非零cohort carry-in与多period合同、
正式planner/证书、连续网侧dispatch、完整holdout风险/删失/权重定义、运行环境及独立official审查。
本组件的response/ramp是给定机制不等式，不认证响应前后网络安全或真实系统响应速度。

实现：`src/rq2_joint_deliverability_boundary_v1/capacity_policy.py`；
测试：`tests/test_rq2_continuous_capacity_policy_v1.py`与`tests/test_rq2_continuous_aggregate_response_v1.py`。
当前51项通过（36策略+15核算），包含1296组独立有限行动枚举oracle、微量分量及1/7精确投影反例。
该枚举校验取整输入下的连续最优；分数与微量边界另用解析断言覆盖，不把有限枚举当全实数证明。
主线程相关8文件248项通过（23.15s）。独立pre-seal审查限定范围无开放实现finding：
51项targeted、全部连续模型321项测试、39,256组独立Fraction网格枚举、四臂4例恢复集成与10个身份变体通过。
旧24h D_a不能直接作为开放连续训练容量证书；本次draft审查不生成official verdict或打开formal门。
后续诊断交付开发见`rq2_continuous_capacity_diagnostics_v1.md`。
