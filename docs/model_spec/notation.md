# 符号表

## 1. 索引约定

除非特别说明，功率单位为MW，能量和恢复债务单位为MWh，时间单位为h，季度时点用整数编号。成本币种由实验配置指定，所有成本必须使用同一基准年。

常用完整索引顺序为 $(n,s,w,t,c)$：长期场景树节点、节点内短期场景、连续时间窗口、窗口内小时、网络状态。公式中会省略不影响含义的索引，但实现中的变量命名和结果表必须保留对应列。

## 2. 集合与映射

| 符号 | 含义 | 单位 | 备注 |
|---|---|---|---|
| $\mathcal K$ | 规划季度集合，$k=0,\ldots,K-1$ | - | 长期阶段 |
| $\mathcal Y$ | 规划期内的日历年集合 | - | 年度CFE核算 |
| $\mathcal K_y$ | 属于日历年 $y$ 的季度 | - | $\mathcal K_y\subseteq\mathcal K$ |
| $\mathcal N$ | 季度场景树节点集合 | - | 规划信息节点 |
| $\mathcal N_k$ | 位于季度 $k$ 的节点 | - | $\mathcal N_k\subseteq\mathcal N$ |
| $root$ | 根节点 | - | 唯一初始信息集 |
| $pa(n)$ | 节点 $n$ 的父节点 | - | 根节点除外 |
| $anc(n)$ | 从根到 $n$（含 $n$）的祖先节点 | - | 工程启动和路径约束 |
| $desc(n)$ | 节点 $n$ 的后代节点 | - | 策略分析 |
| $k(n)$ | 节点 $n$ 所在季度 | quarter | 映射 |
| $\Omega$ | 场景树叶节点/长期路径集合 | - | 风险和外样本指标 |
| $n_k(\omega)$ | 叶路径 $\omega$ 在季度 $k$ 经过的节点 | - | 叶场景表达 |
| $\mathcal I^b_k$ | 基线 $b$ 在季度 $k$ 的规划决策等价组集合 | - | 只分组可控长期决策，不等同于自然节点 |
| $i^b_k(n),i^b_k(\omega)$ | 自然节点或叶在基线 $b$ 下所属的规划决策组 | - | 非预见性映射；B5可有意使用不可实施的单叶组 |
| $\mathcal S_n$ | 节点 $n$ 内短期运行场景 | - | 负荷和新能源轨迹 |
| $\mathcal W_n$ | 节点 $n$ 使用的连续代表周或压力窗口 | - | 不使用无链接代表日 |
| $\mathcal T_w$ | 窗口 $w$ 中按时间排序的小时 | - | 通常为168 h或连续多日 |
| $first(w),last(w)$ | 窗口首、末小时 | - | 状态边界 |
| $\mathcal C$ | 网络状态集合 | - | $0$为正常状态 |
| $\mathcal C^{crit}$ | 关键N-1状态集合 | - | $\mathcal C=\{0\}\cup\mathcal C^{crit}$ |
| $\mathcal B$ | 电网节点集合 | - | bus |
| $b^{dc}$ | 数据中心固定POI节点 | - | 配置输入，不是决策 |
| $\mathcal L^E$ | 现有线路/变压器支路集合 | - | branch |
| $\mathcal L^C$ | 候选新增回路集合 | - | 可选；与工程映射 |
| $o(\ell),r(\ell)$ | 支路 $\ell$ 的起点和终点 | - | orientation仅用于符号 |
| $\delta^+(b),\delta^-(b)$ | 从节点 $b$ 流出/流入的支路 | - | 节点平衡 |
| $\mathcal G$ | 发电机集合 | - | 含清洁和非清洁机组 |
| $\mathcal G_b$ | 位于节点 $b$ 的发电机 | - | 子集 |
| $\mathcal G^{CFE}$ | 可用于CFE归属的清洁机组 | - | 由地域和属性规则确定 |
| $\mathcal A$ | 候选扩建工程集合 | - | 局部增容和永久工程 |
| $\mathcal A_\ell$ | 影响支路 $\ell$ 的工程 | - | 热限额或新增回路 |
| $\mathcal P$ | 里程碑比例集合 $\{0.2,0.5,1.0\}$ | - | T20/T50/T100 |
| $\mathcal B^{det}$ | M4确定性基线集合 $\{B0,B1,B2\}$ | - | 统一约束下的策略变体，不是场景集合 |

## 3. 信息、时间与概率参数

| 符号 | 含义 | 单位 | 索引 | 类型 |
|---|---|---|---|---|
| $\pi_n$ | 到达节点 $n$ 的无条件概率 | p.u. | $n$ | 输入 |
| $\rho_{n,s}$ | 节点内短期场景条件概率 | p.u. | $n,s$ | 输入 |
| $\omega_w$ | 连续窗口在对应季度/年度聚合中的出现权重 | occurrences/accounting period | $n,w$ | 只用于能量、成本和事件总数聚合 |
| $\Delta t$ | 运行时间步长 | h | - | 主实验默认1 h |
| $\Delta y_k$ | 季度长度 | year | $k$ | 通常0.25 |
| $H_k$ | M2季度静态运行点代表的运行小时数 | h | $k$ | 只乘正常态运行和接入缺口成本 |
| $H^{val}_k$ | 有显式连续轨迹支持的验证时长 | h | $k$ | 静态M3取0；不得由重复快照声明生成 |
| $d_n$ | 节点成本折现因子 | p.u. | $n$ | 根节点基准为1 |
| $\Gamma_{a,m,n}$ | 工程在节点 $m$ 启动后是否应在节点 $n$ 前实际投运 | binary | $a,m,n$ | 按路径预计算 |
| $H_{n,n'}$ | 两节点历史是否相同 | binary | $n,n'$ | 仅叶场景/测试表达 |

概率必须满足同一父节点下条件概率和为1；$\pi_n$等于路径条件概率乘积。$\omega_w$不进入恢复债务递推或最大连续时间约束，但进入季度/年度能量、成本和事件总数聚合。

## 4. 电网参数

| 符号 | 含义 | 单位 | 索引 | 场景性 |
|---|---|---|---|---|
| $D^{sys}_{b,n,s,w,t}$ | 数据中心以外的系统有功负荷 | MW | $b,n,s,w,t$ | 是 |
| $\underline P_g,\overline P_g$ | 机组最小/最大有功出力 | MW | $g$ | 否 |
| $A^G_{g,n,s,w,t}$ | 可再生或机组可用率 | p.u. | $g,n,s,w,t$ | 是 |
| $O^G_{g,c}$ | 网络状态 $c$ 下机组是否可用 | binary | $g,c$ | 事故参数 |
| $c^E_g$ | 线性发电边际成本 | currency/MWh | $g$ | 否 |
| $c^{NL}_g,c^{SU}_g$ | 空载和启动成本（启用SCUC时） | currency/h, currency/start | $g$ | 否 |
| $R^{up}_g,R^{dn}_g$ | 正常时序爬坡能力 | MW/h | $g$ | 否 |
| $R^{corr,+}_g,R^{corr,-}_g$ | 事故后允许的纠正再调度 | MW | $g,c$ | 否 |
| $B_\ell$ | 现有支路DC潮流电纳 | MW/rad | $\ell\in\mathcal L^E$ | 否 |
| $\overline f^N_\ell$ | 正常连续热限额 | MW | $\ell$ | 否 |
| $\overline f^{ST}_{\ell,c}$ | 响应前短时应急热限额 | MW | $\ell,c$ | 否/可缺失 |
| $\overline f^{LT}_{\ell,c}$ | 响应后持续应急热限额 | MW | $\ell,c$ | 否 |
| $\overline\theta_b$ | 节点相角绝对值上界 | rad | $b$ | 为候选回路大M提供有限边界 |
| $O_{\ell,c}$ | 状态 $c$ 下支路是否可用 | binary | $\ell,c$ | 事故参数 |
| $B^C_\ell,\overline f^C_\ell$ | 候选回路电纳和热限额 | MW/rad, MW | $\ell\in\mathcal L^C$ | 否 |
| $\overline C^{0}_{POI}$ | POI初始合同/主变容量上限 | MW | - | 否 |
| $\Delta C^{POI}_a$ | 工程对POI容量的增量 | MW | $a$ | 否 |
| $\Delta f_{\ell,a}$ | 工程对现有支路热限额的增量 | MW | $\ell,a$ | 否 |
| $C^{inv}_a$ | 工程在启动时点计取的投资成本 | currency | $a$ | 目标中再乘启动节点折现因子 |
| $L^0_a$ | 工程额定工期 | quarter | $a$ | 否 |
| $M^{flow}_\ell$ | 候选回路DC方程的有效大M | MW | $\ell$ | 经边界推导 |
| $S^{base}$ | 网络标幺基准功率 | MVA | - | 数据记录 |

若RTS数据中短时和持续应急额定值不可得，必须在配置中声明X采用预防性调用或给出透明的应急额定值构造规则。

M2允许一个工程映射到多条既有支路，但该映射表示具有共同启动、工期和总成本的捆绑走廊项目，不表示多项独立工程共享一份成本。冻结M2成本采用`synthetic_objective_units_not_calibrated_currency_year`，不能解释为具有统一基准年的真实美元。

## 5. 数据中心需求参数

| 符号 | 含义 | 单位 | 索引 | 场景性 |
|---|---|---|---|---|
| $N^{rack}_n$ | 已建可用机柜数量 | rack | $n$ | 是 |
| $a^{act}_n$ | 机柜激活比例 | p.u. | $n$ | 是 |
| $\varrho^{IT}_{n,s,w,t}$ | 激活机柜平均IT利用率 | p.u. | $n,s,w,t$ | 是 |
| $p^{rack}_n$ | 额定IT功率密度 | kW/rack | $n$ | 是/设备代际 |
| $P^{IT,max}_n$ | 已建IT设备功率上限 | MW | $n$ | 是 |
| $PUE_{n,s,w,t}$ | Power Usage Effectiveness | p.u. | $n,s,w,t$ | 是 |
| $P^{fixed}_n$ | 不随IT利用率变化的设施负荷 | MW | $n$ | 是 |
| $P^{IT}_{n,s,w,t}$ | 基线IT功率（预处理值） | MW | $n,s,w,t$ | 是 |
| $D^{req}_{n,s,w,t}$ | 数据中心基线电网侧需求 | MW | $n,s,w,t$ | 是 |
| $D^{flex}_{n,s,w,t}$ | 业务上可暂停/延期/降频的电网侧需求上限 | MW | $n,s,w,t$ | 是 |
| $D^{flex,cert}_n$ | 满负荷运行时经业务侧认证的条件调用包络 | MW | $n$ | 容量可交付性校核 |
| $D^{phys,max}_{n,s,w,t}$ | 已激活设施在该小时可承载的最大电网侧功率 | MW | $n,s,w,t$ | 是；限制恢复负荷 |
| $P^{app}$ | 最终申请接入容量 | MW | - | 否 |
| $B_{min}$ | 首个可运营容量模块 | MW | - | 否 |
| $H_{min}$ | 容量块需连续可服务的验证时长 | h | - | 否 |

$a^{act}$、$\varrho^{IT}$、$p^{rack}$和$PUE$必须分别保存，不得把多个缩放因素重复乘入需求。

## 6. F/X与业务灵活性参数

| 符号 | 含义 | 单位 | 索引 | 备注 |
|---|---|---|---|---|
| $\overline X_n$ | 节点允许释放的最大条件容量 | MW | $n$ | 合同/策略上限 |
| $\tau^{resp}$ | X从触发到达到要求削减量的最大响应时间 | h | - | 配置参数 |
| $H^{max}$ | 单次连续灵活性调用上限 | h | - | aggregate envelope |
| $N^{event,max}_k$ | 每季度允许事件数 | count | $k$ | aggregate envelope |
| $H^{rest}$ | 两次事件之间最小恢复/停用时间 | h | - | aggregate envelope |
| $E^{curt,max}_k$ | 每季度可恢复削减累计能量上限 | MWh | $k$ | 不含永久业务损失 |
| $Q^{max}$ | 恢复债务上限 | MWh | - | 业务积压容量 |
| $R^{rec,max}$ | 最大额外恢复功率 | MW | - | 受POI限制 |
| $R^{curt,max}$ | 数据中心增加条件削减的最大速度 | MW/h | - | 响应能力 |
| $\eta^{defer}$ | 可恢复削减形成债务的比例 | p.u. | - | 主模型固定1；非恢复部分必须改记 $\ell^{drop}$ |
| $\eta^{rec}$ | 恢复效率 | p.u. | - | 不得大于1 |
| $\overline L^{drop}_k$ | 允许永久放弃的业务能量上限 | MWh | $k$ | 与恢复债务分开 |
| $P^{evt,min}$ | 被计为一次灵活性事件的最小调用功率 | MW | - | 按可执行业务块设定 |

## 7. CFE和风险参数

| 符号 | 含义 | 单位 | 索引 | 备注 |
|---|---|---|---|---|
| $\alpha^{ann}$ | 年度清洁电力匹配目标 | p.u. | experiment | G1 |
| $\alpha^{hr}$ | 小时级CFE目标 | p.u. | experiment | G2/G3 |
| $A^{CFE}_g$ | 机组是否满足清洁属性和地域规则 | binary | $g$ | 定义 $\mathcal G^{CFE}$ |
| $\overline G^{attr}_{g,n,s,w,t}$ | 可归属给本数据中心的清洁出力上限 | MW | $g,n,s,w,t$ | 防止超额归属 |
| $\beta$ | CVaR置信水平 | p.u. | - | 如0.95 |
| $\lambda^{risk}$ | CVaR项权重 | dimensionless | experiment | 仅服务/业务损失 |
| $\epsilon^{MW}$ | 判断数值违约或冲突的功率容差 | MW | - | 与求解容差一致并预注册 |
| $\kappa^{access}$ | 未接入需求损失系数 | currency/MWh | - | 不等于unused MW-year价格 |
| $\kappa^{grid}$ | 合同允许网络削减成本 | currency/MWh | - | X调用成本 |
| $\kappa^{green}$ | 绿电移峰业务成本 | currency/MWh | - | 与网络削减分开 |
| $\kappa^{drop}$ | 永久业务损失成本 | currency/MWh | - | 高于可恢复移峰 |
| $\kappa^{breach,F},\kappa^{breach,X}$ | 非合同firm/conditional服务违约成本 | currency/MWh | - | 仅诊断/外样本使用 |
| $\kappa^{CFEgap}$ | CFE目标缺口成本 | currency/MWh | - | 压力实验可用 |

## 8. 规划变量

| 符号 | 含义 | 单位 | 索引 | 决策时点 |
|---|---|---|---|---|
| $F_{b,i}$ | 已释放firm容量 | MW | $b,i\in\mathcal I^b_k$ | 规划决策组 |
| $X_{b,i}$ | 已释放条件容量 | MW | $b,i\in\mathcal I^b_k$ | 规划决策组 |
| $C_{b,i}$ | 总接入权，$C_{b,i}=F_{b,i}+X_{b,i}$ | MW | $b,i$ | 派生 |
| $C^{M2}_k$ | M2已接入且正在运行的firm需求，受 $D^{req}_k$ 上限约束 | MW | $k$ | M2季度决策；不是可闲置合同权 |
| $z^{start}_{a,b,i}$ | 工程是否按规划决策组 $i$ 的计划启动 | binary | $a,b,i$ | 可控规划决策 |
| $v_{a,n}$ | 工程在自然节点 $n$ 是否实际可用 | binary | $a,n$ | 由历史启动与路径Gamma派生，不做跨叶决策等值 |
| $y_{p,n}$ | 里程碑比例 $p$ 是否已形成可运营容量块 | binary | $p,n$ | 指标辅助 |

M3机制门中的 $F_k,X_k$ 与工程开工季度是固定策略输入而非优化变量；仍使用同一符号，是为了让服务和安全约束可直接迁移到后续B0-B2规划模型。固定策略必须单独保存`parameter_status`，不能把可行性评估结果写成最优容量路径。

M4中的 $F_k,X_k,C_k,u^{access}_k,z^{start}_k,v_k$ 是确定性季度/root规划变量，统一标记为`quarter_root_only_no_state_or_scenario`。B0-B2的附加约束分别为：B0令 $X=0$ 且工程投运前 $C=0$；B1令 $X=0$ 但允许立即使用既有POI容量；B2允许静态F/X拆分。任何事故态索引只属于运行见证，不能加到这些规划变量上。

M5的B3/B4/B5共享同一自然场景树，但使用不同的 $\mathcal I^b_k$。只有 $F/X/z^{start}$ 按这些组共享；$v_{a,n}$、需求和运行补救仍按自然历史派生。为简化通用公式，后文写成 $F_n/X_n/z^{start}_{a,n}$ 时，M5实现应理解为通过 $i^b_k(n)$ 读取对应规划决策组变量，不能据此把B3的 $v$ 跨延期叶锁定。

## 9. 运行变量

| 符号 | 含义 | 单位 | 索引 | 类型 |
|---|---|---|---|---|
| $p_{g,n,s,w,t,c}$ | 机组有功出力 | MW | $g,n,s,w,t,c$ | 运行补救 |
| $u^{snap}_g$ | 单负荷快照中有功机组是否选中 | binary | $g$ | 电网安全诊断；跨该快照全部事故状态共享，不跨小时 |
| $\theta_{b,n,s,w,t,c}$ | 节点电压相角 | rad | $b,n,s,w,t,c$ | 运行补救 |
| $f_{\ell,n,s,w,t,c}$ | 支路有功潮流 | MW | $\ell,n,s,w,t,c$ | 运行补救 |
| $\nu_{\ell,n,c}$ | 候选回路在节点和事故状态下是否可用 | binary | $\ell,n,c$ | $v_{a(\ell),n}O_{\ell,c}$ |
| $D^{conn}_{n,s,w,t}$ | 已取得接入权的需求，$\min(D^{req},F+X)$ | MW | $n,s,w,t$ | 辅助变量 |
| $D^F_{n,s,w,t}$ | 当前需求中的firm层，$\min(D^{req},F)$ | MW | $n,s,w,t$ | 辅助变量 |
| $D^X_{n,s,w,t}$ | 当前需求中的conditional层 | MW | $n,s,w,t$ | $D^{conn}-D^F$ |
| $\delta^C_{n,s,w,t},\delta^F_{n,s,w,t}$ | 两个 `min` 关系的区间选择变量 | binary | $n,s,w,t$ | 精确线性化辅助 |
| $u^{access}_{n,s,w,t}$ | 因尚未取得接入权而无法上线的需求 | MW | $n,s,w,t$ | 规划损失，不是容量产品 |
| $c^{grid}_{n,s,w,t,c}$ | 网络按合同调用的条件削减 | MW | $n,s,w,t,c$ | 运行补救 |
| $c^{green}_{n,s,w,t}$ | 为CFE目标延期的业务功率 | MW | $n,s,w,t$ | 正常运行补救 |
| $\ell^{drop}_{n,s,w,t,c}$ | 永久放弃且不恢复的业务 | MW | $n,s,w,t,c$ | 业务损失 |
| $r^{rec}_{n,s,w,t,c}$ | 业务恢复产生的额外功率 | MW | $n,s,w,t,c$ | 运行补救 |
| $q_{n,s,w,t,c}$ | 恢复债务/未完成业务能量 | MWh | $n,s,w,t,c$ | 状态变量 |
| $u^F_{n,s,w,t,c}$ | firm层非合同服务缺口 | MW | $n,s,w,t,c$ | 主模型固定为0 |
| $u^X_{n,s,w,t,c}$ | conditional层超过合同调用后的服务缺口 | MW | $n,s,w,t,c$ | 主训练固定为0；外样本诊断 |
| $P^{DC}_{n,s,w,t,c}$ | 实际数据中心电网侧功率 | MW | $n,s,w,t,c$ | 进入节点平衡 |
| $on_{n,s,w,t,c}$ | 聚合可恢复灵活性是否正在调用 | binary | $n,s,w,t,c$ | 持续时间辅助 |
| $start^{evt}_{n,s,w,t,c}$ | 灵活性事件是否在本小时开始 | binary | $n,s,w,t,c$ | 事件计数 |
| $stop^{evt}_{n,s,w,t,c}$ | 灵活性事件是否在本小时结束 | binary | $n,s,w,t,c$ | 最小恢复时间 |
| $\widehat p,\widehat\theta,\widehat f$ | 合同容量可交付性校核的发电、相角和潮流副本 | MW, rad, MW | $n,s,w,t,c$ | 安全认证辅助 |
| $\widehat c^{grid}_{n,s,w,t,c}$ | 合同容量校核中允许调用的X | MW | $n,s,w,t,c$ | 不超过 $X_n$ |
| $\widehat P^{DC}_{n,s,w,t,c}$ | 合同容量校核的POI负荷 | MW | $n,s,w,t,c$ | 正常为 $F+X$，N-1不低于F |
| $c^{M4}_{k,c}$ | M4规划模型中的事故态X调用见证 | MW | $k,c$ | base/immediate为0；sustained不超过 $X_k$ |
| $p^{QP}_{g,k,0}$ | M3经审计OSQP点的actual正常态基准出力 | MW | $g,k$ | L1线性可行性投影的数值目标点，不是外生参数 |
| $\delta^{proj,+}_{g,k},\delta^{proj,-}_{g,k}$ | M3线性可行投影相对 $p^{QP}$ 的正/负移动 | MW | $g,k$ | 临时非负辅助变量 |

当前M3的带帽变量构成相同外生条件下的独立合同反事实调度，其纠正出力相对自身带帽正常基态计算；它不是actual调度的即时转移路径。M3中的 $u^F/u^X$ 固定为0，零值只表示硬约束，诊断模式尚未启用。

`u_access`、`c_grid`、`ell_drop`、`u^F/u^X`含义不同，结果表不得合并为一个“unserved load”。

M2中 $u^{access}_k=D^{req}_k-C^{M2}_k$；因 $C^{M2}$ 直接进入POI节点平衡，当前实现不另建 $D^{conn}$。该约化只用于确定性firm-only机制验收，M3必须恢复完整合同权、实际需求和带帽可交付性三种口径。

## 10. CFE和风险变量

| 符号 | 含义 | 单位 | 索引 | 类型 |
|---|---|---|---|---|
| $a^{CFE}_{g,n,s,w,t}$ | 清洁机组出力中归属给数据中心的份额 | MW | $g,n,s,w,t$ | 运行补救 |
| $y^{CFE}_{n,s,w,t}$ | 同小时可归属清洁功率 | MW | $n,s,w,t$ | 派生/运行变量 |
| $g^{CFE}_{n,s,w,t}$ | 小时级CFE目标缺口 | MW | $n,s,w,t$ | 压力/软目标变量 |
| $L_\omega$ | 叶路径总服务和业务损失 | currency或统一损失单位 | $\omega$ | 风险聚合 |
| $p_\omega$ | 完整叶路径概率，等于对应叶节点 $\pi_n$ | p.u. | $\omega$ | 风险权重 |
| $\eta^{VaR}$ | CVaR线性化阈值 | 与 $L$ 相同 | - | 风险变量 |
| $\zeta_\omega$ | 超过VaR阈值的正偏差 | 与 $L$ 相同 | $\omega$ | 风险变量 |

## 11. 后处理指标符号

| 符号 | 含义 | 单位 |
|---|---|---|
| $T20,T50,T100$ | 首次形成对应申请容量比例的可运营季度 | quarter |
| $T_{module}$ | 首个 $B_{min}$ 可运营模块季度 | quarter |
| $VMA$ | 两阶段与多阶段场景外目标差 | currency或统一目标单位 |
| $E^{unused}$ | 已释放但未使用容量的时间积分 | MW-year |
| $\Delta X^{over}$ | 错误重复承诺模型相对正确模型的X高估 | MW或% |
| $p^{fail}_{out}$ | 场景外履约失败概率 | p.u. |
| $Q^{peak}$ | 最大恢复债务 | MWh |
| $Score^{CFE}$ | 可归属CFE电量占数据中心总用电量比例 | p.u. |
| $R^{conflict}$ | 网络与绿电服务请求超过共享包络的比例 | p.u. |
| $U$ | 物理接入缺口暴露；M4为$\sum_kH_ku^{access}_k$，M5为$\sum_{\omega,k}p_\omega H_ku^{access}_{k,\omega}$ | MWh |
| $E^C$ | M5概率加权总合同容量暴露，$\sum_{\omega,k}p_\omega H_kC_{k,\omega}$ | MWh |
| $E^X$ | 条件容量暴露；M4为$\sum_kH_kX_k$，M5为$\sum_{\omega,k}p_\omega H_kX_{k,\omega}$ | MWh |
| $[E^{C,min},E^{C,max}]$ | M5在 $U=U^*$ 面上的总合同容量暴露集合值区间 | MWh |
| $[E^{X,min},E^{X,max}]$ | M4在 $U=U^*$ 面、M5在 $U=U^*,E^C=E^{C,min}$ 面上的X暴露集合值区间 | MWh |
| $N_z$ | M4端点规范化中的工程启动数，$\sum_kz^{start}_k$ | count |
| $A_v$ | M4端点规范化中的投运暴露，$\sum_kH_kv_k$ | h |
| $r^{QP}$ | M3 OSQP原约束违约与边界投影的最大值 | 原约束对应单位 |
| $\Delta p^{max}$ | M3 L1线性可行性投影的最大单坐标发电移动 | MW |
| $J^{QP},J^{proj}$ | M3投影前/后的原始凸主目标值 | synthetic objective units |

$y^{CFE}$按功率建模，单个时间步的可归属电量为 $y^{CFE}\Delta t$ MWh。若实现直接保存电量变量，必须改名为 $e^{CFE}$，不能在年度约束中再次乘 $\Delta t$。

M4先以等式锁定 $U=U^*$，再分别求 $E^{X,min}$ 和 $E^{X,max}$；端点规范化继续以等式锁定 $E^X$ 和 $N_z$。相应容差只用于后验审计，不是优化松弛。显示端点采用minimum-X规范化，但该选择和maximum-X端点都不是经济最优结论。

M5合成场景门先锁定 $U=U^*$ 并报告 $E^C$ 的最小/最大端点；默认展示固定 $E^C=E^{C,min}$，再在该面报告 $E^X$ 的最小/最大端点。工程规范化只能发生在所选物理端点等式锁定后。该顺序处理未定价的空闲合同权，仍不构成经济最优结论。

M3的 $\Delta p^{max}$ 移动包络与 $|J^{proj}-J^{QP}|$ 目标偏差包络统一解释为`numerical_feasibility_projection_envelopes_not_optimality_gap_or_error_certificate`，不得报告为最优间隙、误差证书或全局最优证明。
