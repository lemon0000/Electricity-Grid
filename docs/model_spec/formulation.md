# 数学模型规格

## 1. 模型范围与索引省略

本文件先给出确定性季度路径上的RTS-24模型，再说明多阶段、完整灵活性、CFE和CVaR扩展。所有扩展复用同一服务平衡和网络约束，禁止为不同实验复制口径不一致的模型。

为便于阅读，公式常省略 $(n,s,w,t,c)$。实现必须按 `notation.md` 恢复完整索引。正常状态记为 $c=0$，关键N-1状态记为 $c\in\mathcal C^{crit}$。

### 1.1 已实现的M2约化边界

当前确定性M2使用单一路径季度 $k$，只保留一个固定POI、一个具有共同启动决策/工期/总成本的捆绑既有走廊热增容工程，以及firm-only接入。数据中心季度需求要求非下降。为避免在F/X服务闭环完成前制造空闲合同权，M2定义

$$
0\le C^{M2}_k\le D^{req}_k,
\qquad
u^{access}_k=D^{req}_k-C^{M2}_k,
$$

$$
C^{M2}_k\le P^{app},
\qquad
C^{M2}_k\le \overline C^0_{POI}+\Delta C^{POI}v_k,
$$

$$
C^{M2}_k\ge C^{M2}_{k-1}.
$$

$C^{M2}$直接作为全部正常/N-1状态的POI firm负荷，因此表示“已接入且正在运行的firm需求”，不是第3节可独立闲置的完整合同权 $C=F+X$。M2结果不能用于unused MW-year，也不能替代M3的 $D^{conn}=\min(D^{req},C)$ 和带帽合同容量校核。

工程在季度 $m$ 启动、经过 $L$ 个完整季度后，从 $k=m+L$ 起投运：

$$
v_k=\sum_{m:m+L\le k}z^{start}_m,
\qquad
\sum_m z^{start}_m\le1.
$$

无法在规划期内投运的启动季度仍保留在 $K+1$ 个审计候选中，其投运向量全为0且仍按启动季度计入投资成本。这样可以显式检查全部固定策略；在非负投资成本下它被“不启动”弱支配，零成本并列时按规范顺序保留“不启动”。M2工程只增加映射中既有支路的A/C热限额，不改变拓扑、电纳或相移：

$$
\overline f_{\ell,k,c}
=\overline f^c_\ell+\Delta f^c_\ell v_k.
$$

故障支路仍强制 $f=0$，因此该热增容不需要候选新回路的大M。映射中的多条支路是同一个捆绑走廊工程，必须共享一个工期和总成本；不能把一个成本误解为购买多个独立工程。

M2目标只给正常态运行计能量成本，事故枚举是互斥的硬安全检查：

$$
\min\;
\sum_k d_k C^{inv}z^{start}_k
+\sum_k d_kH_k
\left(C^{op}_k+\kappa^{access}u^{access}_k\right).
$$

其中 $H_k$ 为季度运行小时数。M2完整枚举“不启动”和每个固定启动季度，共 $K+1$ 个候选；每个候选固定启动/投运状态后，由OSQP直接数值求解原始凸二次目标，审计原单位约束，再由HiGHS在线性可行域内修复。只有全部候选均解析后才选择修复目标最小者。有限枚举已消除PWL选择和MIQP求解器依赖，但没有显式最优间隙证书时只能称为完整候选枚举中的最佳数值QP结果，不能称数学精确全局最优。投资成本按启动季度 $d_k$ 折现；M2不把107个事故状态重复乘以季度小时数。

二次候选的线性修复必须同时满足原模型约束违约不超过 $10^{-6}$，且修复前后目标差不超过三项数值门槛的最大值：绝对门槛 $10^{-6}$、相对门槛 $10^{-8}\max\{|J^{QP}|,|J^{repair}|,1\}$，以及 $2s_J\tau_{QP}$。其中 $s_J$ 是送入OSQP前采用的目标缩放，$\tau_{QP}$ 是QP预审可行容差；最后一项保守计入一次约束修复和一次边界投影的目标尺度影响。该最大值只称`numerical repair acceptance envelope`，不是最优间隙、误差上界或全局最优证书。原目标为线性时，HiGHS修复本身求解完整原LP，该目标差门槛不适用，但原约束审计仍适用。

### 1.2 已实现的M3固定策略机制门

M3先评估预先给定的季度 $(F_k,X_k)$ 与工程开工计划，不在缺少firm/X相对价值、容量持有成本和事故频率证据时任意优化拆分。输入计划必须满足

$$
F_k\ge F_{k-1},\qquad F_k+X_k\ge F_{k-1}+X_{k-1},
$$

但允许 $X_k<X_{k-1}$，以表示工程投运后把X转成F。M3按常数精确计算

$$
C_k=F_k+X_k,
\quad D^{conn}_k=\min(D^{req}_k,C_k),
\quad D^F_k=\min(D^{req}_k,F_k),
$$

$$
D^X_k=D^{conn}_k-D^F_k,
\quad u^{access}_k=D^{req}_k-D^{conn}_k.
$$

实际运行层和完整合同层具有独立的发电、相角与潮流变量。实际层满足

$$
P^{DC,act}_{k,c}=D^{conn}_k-c^{grid,act}_{k,c},
$$

合同反事实层满足

$$
P^{DC,hat}_{k,c}=C_k-\widehat c^{grid}_{k,c}.
$$

正常态及支路响应前短时态强制两类调用均为0；持续支路/机组事故态满足

$$
0\le c^{grid,act}_{k,c}\le D^X_k,
\qquad
0\le\widehat c^{grid}_{k,c}\le X_k,
$$

从而实际层不削减活跃firm需求，合同层不低于完整F。两层分别相对各自正常基态执行相同纠正再调度边界。合同层是相同外生系统负荷、工程状态和事故集合下的独立反事实调度，不表示actual调度可瞬时迁移到该点。

训练机制门把 $u^F,u^X$ 固定为0；输出中的零值表示硬可行域，不具备不可行策略的违约诊断功能。持续事故调用量不进入货币目标。原始凸二次目标直接由OSQP数值求解，并在未缩放的原约束上审计。记审计后的actual正常态基准出力为 $p^{QP}_{g,k,0}$，固定策略下的完整线性可行域为 $\mathcal P(F,X,z)$。HiGHS随后执行L1线性可行性投影：

$$
\min_{x,\delta^+,\delta^-}
\sum_{k,g}(\delta^+_{g,k}+\delta^-_{g,k})
$$

$$
\text{s.t.}\quad
x\in\mathcal P(F,X,z),\qquad
p^{act}_{g,k,0}-p^{QP}_{g,k,0}
=\delta^+_{g,k}-\delta^-_{g,k},\qquad
\delta^+_{g,k},\delta^-_{g,k}\ge0.
$$

这里投影到完整线性可行域，但L1距离只在actual正常态基准出力坐标上度量。把一个带有可接受小残差的QP点逐坐标锁定可能使exact-fix可行性恢复报告不可行，因此实现允许由L1投影决定最小总移动，并同时审计最大单坐标移动和原始目标偏差：

$$
\Delta p^{max}
\le \max\{10^{-5},10r^{QP}\},
\qquad
r^{QP}=\max\{r^{constr}_{QP},r^{bound}_{QP}\},
$$

$$
|J^{proj}-J^{QP}|
\le \max\{\tau_J,10^{-8}\max(|J^{proj}|,1)\}.
$$

$\tau_J$ 是配置的主目标数值容差，默认 $10^{-5}$。通过投影后，具有正二次成本系数的actual正常态基准出力固定在投影值；剩余线性主成本受 $J^{proj}+\tau_J$ 帽约束，再最小化actual与合同层的持续事故调用总和。该和跨越互斥N-1状态及两层，不能解释为一次运行功率、MWh、期望事件或事故成本。移动包络与目标偏差包络只用于接受或拒绝数值可行投影，统一标记为`numerical_feasibility_projection_envelopes_not_optimality_gap_or_error_certificate`；二者都不是最优间隙、误差证书或全局最优证明。结果必须同时保存OSQP主/对偶残差、原约束最大违约、边界投影、L1移动和投影目标偏差；没有可行对偶下界时只称直接数值QP结果，不称数学精确全局最优。

M3固定策略的actual正常态调度直接优化原始凸二次成本，不再接收PWL切点参数。静态DC状态门的连续验证小时固定为0，不能释放正式容量里程碑。独立连续包络把显式调用轨迹、恢复功率和债务状态跨完整8784小时时间轴链接，其结果使用`released_capacity_model_validated_over_explicit_chronological_sensitivity_trace`口径；由于尚未耦合逐时网络调度和观测业务轨迹，仍不能称为连续运行认证。

### 1.3 已实现的M4确定性B0-B2基线

M4在与M3相同的固定POI、捆绑工程、季度需求和安全状态集合上联合规划季度容量与工程启动。规划变量严格采用`quarter_root_only_no_state_or_scenario`索引；事故态只索引运行见证变量，不能形成按事故或场景自适应的容量计划。三个基线共享

$$
C_k=F_k+X_k,
\qquad
C_k+u^{access}_k=D^{req}_k,
$$

$$
F_k\ge0,\qquad
0\le X_k\le\overline X,\qquad
u^{access}_k\ge0,
$$

$$
C_k\le P^{app},
\qquad
C_k\le\overline C^0_{POI}+\Delta C^{POI}v_k,
$$

$$
F_k\ge F_{k-1},
\qquad
C_k\ge C_{k-1},
$$

以及第4节的单次启动/工期约束和第7节的DC安全约束。基线等式 $C_k+u^{access}_k=D^{req}_k$ 使 $C_k$ 表示当季已接入需求，不建立超过当季需求的空闲合同权，因此这些结果不能用于计算unused MW-year。

记M4事故态调用为 $c^{M4}_{k,c}$。正常态和响应前支路状态不允许调用，响应后持续支路/机组状态允许在X层内调用：

$$
c^{M4}_{k,c}=0,
\quad c\in\mathcal C^{base/immediate},
$$

$$
0\le c^{M4}_{k,c}\le X_k,
\qquad
C_k-c^{M4}_{k,c}\ge F_k,
\quad c\in\mathcal C^{sustained}.
$$

POI负荷为 $P^{DC,M4}_{k,c}=C_k-c^{M4}_{k,c}$。B0-B2只改变容量产品的可用规则，不改变网络、工程工期、纠正再调度或安全集合：

| 基线 | 附加约束 | 解释边界 |
|---|---|---|
| `B0_WAIT` | $X_k=0$；$C_k\le P^{app}v_k$ | 工程投运前全部等待，不能使用既有POI容量 |
| `B1_FIRM` | $X_k=0$ | 可立即使用既有POI firm容量，工程投运后再增加firm |
| `B2_STATIC_FX` | 无额外的 $X_k=0$ 约束 | 允许静态F/X拆分；不含连续事件、能量和恢复债务证明 |

M4不使用任意firm/X价格选择单一点。首先最小化物理接入缺口暴露

$$
U=\sum_k H_k u^{access}_k,
\qquad U^*=\min U,
$$

随后以严格等式 $U=U^*$ 保留主最优面，并分别求条件容量暴露

$$
E^X=\sum_k H_kX_k,
\qquad
E^{X,min}=\min_{U=U^*}E^X,
\qquad
E^{X,max}=\max_{U=U^*}E^X.
$$

$[E^{X,min},E^{X,max}]$ 是必须报告的集合值区间。`primary_tolerance_mwh`和`x_exposure_tolerance_mwh`只是后验数值审计包络，不是后续阶段可以消耗的松弛预算。主目标和各X端点在模型中都用等式锁定。

每个X端点只做非经济规范化：在 $U=U^*$ 和 $E^X=E^{X,e}$ 的等式面上，先最小化工程启动数 $N_z=\sum_kz^{start}_k$，再以 $N_z=N_z^e$ 等式锁定该整数，最后最小化投运暴露 $A_v=\sum_kH_kv_k$。这一步只生成可复现的规划见证，不表示投资成本最小、firm/X经济最优或项目建议。显示结果固定采用minimum-X端点，标签为`conservative_minimum_x_normalization_not_economic_optimum`；规划模型中的事故调用只是可行见证，显示计划仍须固定后交给M3生成规范调度，M3失败则M4整体失败关闭。

每个成功策略必须依次保存10个诊断阶段：主缺口求解、minimum-X求解、maximum-X求解、X区间审计，minimum-X端点的工程数求解/投运暴露求解/端点审计，以及maximum-X端点对应的三阶段。端点审计检查原约束最大违约、整数违约、主目标等式面和X端点等式面；任一求解或审计未接受都不得报告显示端点。

冻结RTS-24运行使用需求路径 $(50,100,200,250)$ MW、季度小时 $(2184,2184,2208,2208)$ h，并得到以下正式基准数值结果：

| 基线 | $U^*$ (MWh) | $[E^{X,min},E^{X,max}]$ (MWh) | minimum-X显示端点 | maximum-X端点 |
|---|---:|---:|---|---|
| B0 | 327600 | $[0,0]$ | $F=C=(0,0,200,250)$ MW，$X=0$ | 与minimum-X相同 |
| B1 | 109200 | $[0,0]$ | $F=C=(50,50,200,250)$ MW，$X=0$ | 与minimum-X相同 |
| B2 | 109200 | $[0,549600]$ | 与B1相同 | $F=(0,0,125,175)$ MW，$X=(50,50,75,75)$ MW，$C=(50,50,200,250)$ MW |

三个策略的规范端点均在q1启动工程、q3投运。静态状态的 $H_k^{val}=0$，所以 $T_{module},T20,T50,T100$ 全部右删失为`q4+`；季度容量路径本身达到阈值不能替代连续验证。以上是`synthetic_non_engineering_baseline_gate`下的冻结数值基线，不是场址或工程证据，不识别经济最优拆分，也不构成安全认证；所有结果保持`security_certified=false`。

### 1.4 M5 B3-B5场景结构门的冻结口径

M5不能把M4的 $C_k+u^{access}_k=D^{req}_k$ 直接复制到随机模型。B3必须在根节点跨需求场景预先承诺季度容量，因此合同权可以高于某一叶当季实际需求。M5恢复第5节的完整合同分层：

$$
D^{conn}_{k,\omega}=\min\{D^{req}_{k,\omega},C_{k,\omega}\},
\qquad
u^{access}_{k,\omega}=D^{req}_{k,\omega}-D^{conn}_{k,\omega},
$$

并继续用独立合同反事实校核完整 $C=F+X$ 的可交付性。可控的 $F/X/z^{start}$ 按B3/B4/B5各自的规划决策等价组索引；自然路径派生的工程可用状态 $v$ 不进入该等值分组。不得再用每个叶的 $D^{req}$ 给共享的 $C$ 加上界，否则会错误禁止静态策略持有尚未使用的合同权。

由于真实firm/X相对价值、闲置容量机会成本和场景概率均未校准，M5小树只使用物理词典序集合值规则。记12叶概率为 $p_\omega$，首先求

$$
U=\sum_{\omega,k}p_\omega H_k u^{access}_{k,\omega},
\qquad U^*=\min U.
$$

只锁定 $U=U^*$ 仍会允许无代价多释放总合同权，因此必须先报告

$$
E^C=\sum_{\omega,k}p_\omega H_k C_{k,\omega},
\qquad
[E^{C,min},E^{C,max}]_{U=U^*}.
$$

展示轨迹固定在 $E^C=E^{C,min}$ 的保守端点，再在该等式面上报告

$$
E^X=\sum_{\omega,k}p_\omega H_kX_{k,\omega},
\qquad
[E^{X,min},E^{X,max}]_{U=U^*,E^C=E^{C,min}}.
$$

只有在 $U$、$E^C$ 和所选 $E^X$ 端点均以严格等式锁定后，才可用期望启动数和投运暴露生成非经济规范见证。所有端点都必须报告；默认展示minimum-$E^C$/minimum-$E^X$端点，不能称经济最优。M5输入冻结为`rts24_b3_b5_synthetic_tree_v1`：四季度、六条递进需求路径乘两个工程交付状态、12叶等权，q1无长期信息、q2前只揭示当前需求类、q3前揭示工程状态、q4前才揭示终端需求。自然节点与策略规划决策组分离，组内等值只作用于 $F/X/z^{start}$，不作用于路径派生的 $v$。它只构成`synthetic scenario-structure mechanism gate`，不是经验概率、正式VMA、工程建议或安全认证。

M5b在相同公共输入签名和完整107态安全集合下得到：

| 基线 | 可实施 | $U^*$ (MWh) | $[E^{C,min},E^{C,max}]$ (MWh) | minimum-$E^C$面上的$[E^{X,min},E^{X,max}]$ (MWh) |
|---|---:|---:|---:|---:|
| B3 | 是 | 403200 | $[880800,880800]$ | $[0,494400]$ |
| B4 | 是 | 274400 | $[954400,1101600]$ | $[0,522000]$ |
| B5 | 否 | 274400 | $[954400,1101600]$ | $[0,522000]$ |

B4相对B3的树内期望接入缺口减少`128800 MWh`，且本冻结树上B4达到B5完美信息下界。三策略各13项求解或审计stage全部通过，最大原约束违约不超过约$1.85\times10^{-10}$。B3/B4的运行可行性按22个自然节点建模；B5因规划变量从q1起逐叶独立，可严格分解为12个单叶模型并按原概率聚合各词典序端点，小系统测试已验证分解与单体模型的五个集合值标量一致。这些仍是树内合成结果；没有独立外样本执行前不得计算或宣称正式VMA。

### 1.5 M5c固定政策合成holdout口径

对训练端点集合$\mathcal P^b=\{\Pi^{b,minX},\Pi^{b,maxX}\}$，$b\in\{B3,B4\}$，holdout执行不再优化$F/X/z^{start}$。在季度$k$开始时只用已经观察到的历史$h_k^o$通过预注册映射$m_k(h_k^o)$读取训练决策组：

$$
(F_{k,o}^{b,e},X_{k,o}^{b,e},z_{k,o}^{b,e})
=\Pi^{b,e}_{m_k(h_k^o)},
\qquad e\in\{minX,maxX\}.
$$

只有发电、潮流和合同允许的X调用重新求解。每个端点政策的holdout接入缺口为

$$
U_{out}^{b,e}=\sum_{o\in\mathcal O}p_o
\sum_k H_k\max\{D^{req}_{k,o}-C_{k,o}^{b,e},0\}.
$$

由于训练只识别端点集合，适应性值报告为

$$
\mathcal V_{out}=\left\{
U_{out}^{B3,e_3}-U_{out}^{B4,e_4}:
e_3,e_4\in\{minX,maxX\}
\right\},
$$

而不是任选一个端点形成单点经济结论。冻结执行得到$U_{out}^{B3,minX}=U_{out}^{B3,maxX}=474780$ MWh，$U_{out}^{B4,minX}=U_{out}^{B4,maxX}=364380$ MWh，因此$[\min\mathcal V_{out},\max\mathcal V_{out}]=[110400,110400]$ MWh。48次固定执行全部通过actual与合同反事实107态校核，firm/X违约为0。

路径级不能宣称B4普遍支配B3：按期工程的6条叶全部改善；延期且终端映射为upper的3条叶持平；延期且terminal映射为lower的3条叶劣化$22080$至$33120$ MWh。当前$p_o=1/12$是平衡确定性holdout权重，不是经验概率，故该集合记为合成holdout适应性值，不能替代具有独立随机样本和统计区间的正式经验VMA。

### 1.6 M6a连续业务包络消融口径

M6a对同一固定调用轨迹依次启用嵌套可行域：

$$
\mathcal F^{F3}\subseteq\mathcal F^{F2}\subseteq\mathcal F^{F1}.
$$

$F1$只保留$0\le c_t^{grid}\le D_t^X$；$F2$再启用第9节响应/ramp和第10.3节持续时间、休息、事件数、累计能量；$F3$进一步启用第10.2节恢复功率、债务递推、债务上限和期末清零。三层必须使用完全相同的$c_t^{grid}$，不得因F3失败而缩小调用幅值。

冻结M3的网络minimum-call证书在actual/contract四季度均为0，故网络幅值回放三层均平凡可行。独立的full-X合同压力轨迹在q3 actual/contract和q4 contract各调用$75$ MW一小时。F1/F2通过；F3因恢复headroom为0而得到

$$
q^{actual}_{q3,end}=75\text{ MWh},\qquad
q^{contract}_{q3,end}=75\text{ MWh},\qquad
q^{contract}_{q4,end}=150\text{ MWh},
$$

违反季度末$q=0$。因此F1/F2下q3/q4合格容量为250 MW、$T100=q3$，F3下仅175 MW、$T100=q4+$。这证明MW-only及无恢复F2会高估可持续X，但因调用轨迹与包络参数均为合成见证，不能解释为概率、合同能力或逐时网络认证。

### 1.7 RTS-GMLC零数据中心AC-aware commitment V3求解口径

令$\mathcal S$为24个冻结的normal/selected-N-1状态，$\mathcal A^j\subseteq\mathcal S$为第$j$轮active set。每轮先在$\mathcal A^j$上求含共享commitment、reserve和正常态调度的master，再固定该轮shared snapshot，对每个$s\in\mathcal S\setminus\mathcal A^j$独立求LP screen。screen为`certified_infeasible`或在注册时限内未解析时，都将该状态加入$\mathcal A^{j+1}$；后一种只能标记为`unresolved_promoted`，不能作为不可行证据。active set不再扩张后，仍必须固定同一shared snapshot求完整$\mathcal S$ LP并执行独立残差审计。proxy最大化与cost最小化从同一冻结seed分别重启，不能继承前一阶段的active set而获得路径优势。

对proxy最大化，完整状态可行incumbent给出下界，所有有效active-master对偶界中的最小值给出上界：

$$
LB^q=q^{S}_{feasible},\qquad
UB^q=\min_j q^{A^j}_{dual}.
$$

对cost最小化，所有有效active-master对偶界中的最大值给出下界，完整状态可行incumbent给出上界：

$$
LB^C=\max_j C^{A^j}_{dual},\qquad
UB^C=C^{S}_{feasible}.
$$

两阶段统一报告

$$
\Delta=UB-LB,\qquad
r=\frac{\Delta}{\max\{|z_{feasible}|,10^{-12}\}}.
$$

这里$z_{feasible}$是对应sense下的完整状态可行incumbent。目标相对gap冻结为$10^{-4}$，最大可接受相对gap冻结为$10^{-3}$；proxy阶段另要求$\Delta\le10^{-3}$。动态更新的是由实际可行界和对偶界形成的$[LB,UB]$，不是验收阈值。达到最大接受门但未达到目标时只能标记`eligible_within_maximum`，不得声称target attained。任何缺失界、界方向冲突、最终24状态审计失败或超过最大门的stage都不能发布候选。

机器记录中的权威target/eligibility字段是stage顶层的`target_attained`、`eligibility_status`和`maximum_acceptance`，它们使用上式的incumbent-relative $r$。嵌套`certificate.relative_gap`与`certificate.target_gap_attained`沿用通用求解器辅助尺度$\Delta/\max\{|LB|,|UB|,1\}$，只作诊断，不得用于V3正式资格或论文target标签；二者在proxy值小于1时可能不同。

cost-normalized最终commitment还必须保留第一阶段proxy性能。令$q^{UB}_1$为第一阶段认证上界、$\hat q_2$为最终commitment独立重算的proxy、$\Delta^q_1$为第一阶段absolute gap，则

$$
R_q=\max\{q^{UB}_1-\hat q_2,0\},\qquad
R_q\le\Delta^q_1+10^{-7}+10^{-6},\qquad
R_q\le0.0010011.
$$

两个上限必须同时成立并写入`primary_proxy_regret`证书；另存的最终candidate residual audit也必须通过。仅有proxy/cost两个stage合格仍不足以发布候选。

求解器容量inventory在当前自动许可证下只允许HiGHS 1.15.1进入正式模型。冻结6小时、24状态重复pilot以非目标值规则选择4线程，再选择exact selected-state constraint generation；thread result manifest为`4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1`，formulation preparation/result manifest为`ae3c19536341c0767f43dcbddb7ccabd60c9607f0baae7ab152507e750cf763a`和`82f1f0cb72d574b2054f193f6354383c5629bd30796b42a919323ef326c0d7e1`。本节只定义候选生成和误差证书，不构成AC见证；六个预算候选各自的checkpoint及包含冻结父基线在内的完整requested frontier原子发布并验证前，不得调用joint AC。

### 1.7.1 repair-009修订：求解器由HiGHS切换为Gurobi

上段“只允许HiGHS 1.15.1进入正式模型”是自动许可证下的容量结论，在repair-009已被取得的Gurobi学术许可解除。原文保留不改写，本小节记录修订后的实际口径。

已独立复算核实的事实：

- `configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml`设`solver_name: gurobi`、`solver_threads: 4`。
- pilot benchmark产物在`results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_gurobi_benchmark_v1/benchmark/`，其`SHA256SUMS`哈希为`63f7398eed5ef95e0de13b38ffb6efc7d08f4531c5df95da4f2fc6ce2af0da8d`，与配置中`gurobi_pilot_benchmark_sha256sums`逐字符一致。
- 引擎版本为Gurobi 13.0.2：候选6的原生日志首行为`Gurobi Optimizer version 13.0.2 build v13.0.2rc1 (win64)`，环境内`gurobipy`报告同一版本。

本修订尚未复核的项：pilot benchmark内部的线程选择时间、gap与残差明细未在本次修订中读取，只核对了其manifest哈希。引用具体pilot数值前必须先读取该产物。

因pilot模块与`src/grid/rts_gmlc_formal_cg_adapter.py`均被预注册哈希链锁定，切换以runner-009加载期的两处monkeypatch实现，不改动被锁文件：

1. `_frozen_pilot._solve_handle = _gurobi_solve_handle`。影响iteration≥2的proxy master、screening、full-state audit、level-set与cost bisection。
2. `FormalCgModelAdapter.solve_master`包装器。适配器原判定`globally_infeasible`时硬编码`solver_api == "pyomo.contrib.solver.highs_v2"`，Gurobi实报`gurobi_legacy` + `termination_condition=minFunctionValue` + `solver_status=aborted`，条件永不成立，level-set二分法的不可行性通道对Gurobi恒为关闭。包装器在stage为`level_set_budget_feasibility`、求解器为Gurobi、无可行incumbent、且`raw_lower_bound`有限并严格超过`decision_budget_cap_usd`时置`globally_infeasible=True`，与HiGHS的`provenInfeasible`同等对待。`timeLimit`终止被显式排除，符合`timeout_or_ambiguous_is_infeasibility_evidence: false`；未额外增加数值裕度门槛，因为基线对HiGHS的证书也未要求裕度。超出裕度写入`decision_mip`记录供审计。

**这条链路并非全部Gurobi。** `src/grid/rts_gmlc_v4_initial_proxy_warmstart.py`的`V4InitialProxyWarmStartAdapter.solve_master`在`stage=proxy_maximization && kind=master && iteration==1`时走自有的Appsi/HiGHS warm-start分支，完全绕过`pilot._solve_handle`，因此每个新候选的第一次proxy master仍是单核HiGHS。实测候选5该调用耗时1.71 h，候选6跑满7200 s上限。该文件由repair-004的`warm_start_adapter_sha256`锁定，未改动。

验证状态：`proxy_evidence`链式传参修订已由候选5 checkpoint（`candidate_manifest_sha256=a1bacf3706d7239aebdd1018c593675a2ea3e29c301a330e4bf64bb6d9d22aa9`）在真实链路验证通过。Gurobi不可行通道修订目前只有8项合成单测背书，真实链路验证点为候选6，尚未取得。

未闭合的程序性缺口：`blocker_register.md`要求换求解器须先通过独立重复pilot验证start映射、接受日志、运行时间、最终界和原单位残差，再新建预注册。上述两处monkeypatch属实现变更，其效果尚未经独立重复pilot复核。

## 2. 数据中心基线需求

基线IT功率在数据预处理阶段计算：

$$
P^{IT}_{n,s,w,t}=
\min\left\{
P^{IT,max}_n,
\frac{N^{rack}_n a^{act}_n\varrho^{IT}_{n,s,w,t}p^{rack}_n}{1000}
\right\}.
$$

电网侧需求为

$$
D^{req}_{n,s,w,t}=P^{fixed}_n+PUE_{n,s,w,t}P^{IT}_{n,s,w,t}.
$$

已激活设施的物理取电上限为

$$
D^{phys,max}_{n,s,w,t}=P^{fixed}_n+PUE_{n,s,w,t}
\min\left\{
P^{IT,max}_n,
\frac{N^{rack}_na^{act}_np^{rack}_n}{1000}
\right\}.
$$

它允许把利用率从 $\varrho^{IT}$ 提高以恢复延期业务，但不允许使用尚未激活的机柜。

业务可灵活部分为

$$
0\le D^{flex}_{n,s,w,t}
\le PUE_{n,s,w,t}P^{IT}_{n,s,w,t},
$$

并由业务类型比例或作业数据生成。固定设施负荷不得计入 $D^{flex}$。机柜激活率、IT利用率、额定功率密度和PUE各乘一次；处理脚本必须保存每一项中间结果。

## 3. F/X容量释放

总接入权定义为

$$
C_n=F_n+X_n.
$$

容量边界为

$$
0\le F_n,\qquad 0\le X_n\le \overline X_n,
$$

$$
C_n\le P^{app}.
$$

沿每条场景树路径，firm容量和总接入权不可撤回：

$$
F_n\ge F_{pa(n)},
$$

$$
C_n\ge C_{pa(n)}.
$$

$X_n$不单独要求单调，因为工程投运后允许把既有X转成F；第二个约束保证转换不能减少客户总接入权。

POI设备/合同容量限制为

$$
C_n\le \overline C^0_{POI}
+\sum_{a\in\mathcal A}\Delta C^{POI}_a v_{a,n}.
$$

该约束只是POI设备上限，不能替代网络潮流可交付性校核。

## 4. 工程启动、延期和投运

每个候选工程沿一条路径最多启动一次：

$$
\sum_{m\in anc(n)}z^{start}_{a,m}\le 1,
\qquad \forall a,n.
$$

工程实际可用状态由启动节点和场景路径决定：

$$
v_{a,n}=\sum_{m\in anc(n)}\Gamma_{a,m,n}z^{start}_{a,m}.
$$

$$
v_{a,n}\ge v_{a,pa(n)}.
$$

$\Gamma_{a,m,n}$只能根据从 $m$ 到 $n$ 已实现的工期和延期生成。若工程额定工期为4季度、当前路径实际延期2季度，则它在启动后的前5个季度均不得提供容量，第6个季度起才能使 $v=1$。

影响现有走廊热限额的工程通过

$$
\overline f_{\ell,n,c}
=\overline f^c_{\ell}
+\sum_{a\in\mathcal A_\ell}\Delta f_{\ell,a}v_{a,n}
$$

生效，其中 $\overline f^c_\ell$按正常、短时应急或持续应急状态选取。

## 5. 需求的合同分层

必须区分当前需求中已取得接入权的部分、firm层、conditional层和尚未接入部分：

$$
D^{conn}=\min\{D^{req},C_n\},
$$

$$
D^F=\min\{D^{req},F_n\},
$$

$$
D^X=D^{conn}-D^F,
$$

$$
u^{access}=D^{req}-D^{conn}.
$$

$u^{access}$表示达产需求尚未取得合同容量，不进入电网节点负荷，也不允许被误报成网络负荷损失。

### 5.1 `min`的精确线性化

对常数/已知参数 $a\ge0$、连续变量 $0\le x\le M$、$y=\min(a,x)$，引入二进制变量 $\delta$，采用：

$$
0\le y\le a,\qquad y\le x,
$$

$$
y\ge a-M(1-\delta),
$$

$$
y\ge x-M\delta,
$$

$$
a-x\le M(1-\delta),
$$

$$
x-a\le M\delta.
$$

分别令 $(a,x,y)=(D^{req},F,D^F)$ 和 $(D^{req},C,D^{conn})$。$M$必须不小于 $\max\{P^{app},\max D^{req}\}$，并尽量按节点/小时使用更紧上界；当需求可能超过申请容量时，单独取 $P^{app}$ 并不有效。不得使用求解器默认大常数。

## 6. 实际服务闭环

数据中心实际电网侧功率满足

$$
\begin{aligned}
P^{DC}_{c}
=\;&D^{conn}
-c^{grid}_{c}
-c^{green}
-\ell^{drop}_{c}
-u^F_c-u^X_c
+r^{rec}_c.
\end{aligned}
$$

变量含义互不替代：

- $u^{access}$：尚未取得容量权；
- $c^{grid}$：合同允许的X网络削减；
- $c^{green}$：为CFE目标主动延期且需要恢复的业务；
- $\ell^{drop}$：永久放弃且不进入恢复债务的业务；
- $u^F,u^X$：合同允许范围之外的服务违约；
- $r^{rec}$：偿还历史延期业务造成的额外取电。

网络条件削减只能作用于当前活跃的X层：

$$
0\le c^{grid}_c\le D^X.
$$

非合同缺口边界为

$$
0\le u^F_c\le D^F,
$$

$$
0\le u^X_c\le D^X-c^{grid}_c.
$$

主规划/训练模型对所有正常和关键N-1状态强制

$$
u^F_c=u^X_c=0.
$$

不得用高罚值替代已签约容量的履约约束。$u^F/u^X$只在场景外执行、不可行诊断或明确标记的风险容忍扩展中解锁，用于记录既定策略无法履约的缺口；它们不能被称为正常X调用，也不能帮助训练模型少建网络。

所有减少当期取电的量不能超过已接入需求：

$$
c^{grid}_c+c^{green}+\ell^{drop}_c+u^F_c+u^X_c
\le D^{conn}.
$$

实际取电受接入权限制：

$$
0\le P^{DC}_c\le C_n,
\qquad
P^{DC}_c\le D^{phys,max}.
$$

恢复功率因此会占用当期剩余POI容量，不能在需求之外凭空叠加。

## 7. DC潮流与关键N-1

### 7.1 发电边界

对所有机组和状态：

$$
\underline P_g O^G_{g,c}
\le p_{g,c}
\le \overline P_g A^G_{g,n,s,w,t}O^G_{g,c},
$$

其中 $O^G_{g,c}$ 是状态 $c$ 下机组可用参数。事故后纠正再调度满足

$$
-R^{corr,-}_{g,c}
\le p_{g,c}-p_{g,0}
\le R^{corr,+}_{g,c}.
$$

连续小时之间还需满足正常爬坡：

$$
-R^{dn}_g\Delta t
\le p_{g,t,0}-p_{g,t-1,0}
\le R^{up}_g\Delta t.
$$

当前RTS-24负荷快照诊断另提供静态机组选择变体：

$$
\underline P_g u^{snap}_g O^G_{g,c}
\le p_{g,c}
\le \overline P_g u^{snap}_g O^G_{g,c}.
$$

同一快照的正常态、支路短时/持续态和机组故障态共享同一个 $u^{snap}_g$，因此事故后不能临时启动正常态停机机组。该变量不跨小时，且当前数据没有合法确定启动状态、最小开停机时间和跨时爬坡的条件，所以该变体只称为`single_snapshot_static_unit_selection`，不称为SCUC。系统负荷仍无松弛变量。

静态选择的优化成本以65个切点的凸切线下包络近似原生多项式；截距乘 $u^{snap}_g$，停机机组成本为零。保存的成本是在所选解处按原多项式精确回算，不代表精确MIQP的全局最优目标。源数据启动成本因缺少前一时点状态而不在单快照中使用。

AC复核将同一快照的有功需求写回PYPOWER case，并按各母线原始有功倍率同比缩放无功需求，从而保持原母线功率因数；固定并联补偿不随负荷缩放。$u^{snap}_g=0$仅关闭具有正有功容量的机组，`Pmax=0`的同步调相设备另按源可用状态保留。若原REF母线没有在线正有功机组，则按当前目标出力下实际承担slack的首台机组上调裕度、下调裕度、无功范围和母线号确定性重选REF。普通AC潮流收敛不等于安全，仍显式检查P/Q、电压和两端MVA限额。

### 7.2 现有支路潮流

$$
f_{\ell,c}=O_{\ell,c}B_\ell
(\theta_{o(\ell),c}-\theta_{r(\ell),c}),
\qquad \ell\in\mathcal L^E.
$$

$$
-\overline f_{\ell,n,c}
\le f_{\ell,c}
\le \overline f_{\ell,n,c}.
$$

故障支路的 $O_{\ell,c}=0$，因此其潮流为零。所有热限额均为硬约束，不设置热越限松弛变量。

### 7.3 候选新增回路

对由工程 $a(\ell)$ 建设的候选回路，令

$$
\nu_{\ell,n,c}=v_{a(\ell),n}O_{\ell,c}.
$$

由于 $O$ 是参数，$\nu$是二进制变量与常数的乘积，可直接线性表示。候选回路满足

$$
-M^{flow}_\ell(1-\nu_{\ell,n,c})
\le f_{\ell,c}-B^C_\ell(\theta_{o(\ell),c}-\theta_{r(\ell),c})
\le M^{flow}_\ell(1-\nu_{\ell,n,c}),
$$

$$
-\overline f^C_\ell\nu_{\ell,n,c}
\le f_{\ell,c}
\le \overline f^C_\ell\nu_{\ell,n,c}.
$$

### 7.4 节点功率平衡

对每个节点 $b$：

$$
\sum_{g\in\mathcal G_b}p_{g,c}
-D^{sys}_{b}
-\mathbf 1_{b=b^{dc}}P^{DC}_{c}
=\sum_{\ell\in\delta^+(b)}f_{\ell,c}
-\sum_{\ell\in\delta^-(b)}f_{\ell,c}.
$$

系统原有负荷没有可优化的负荷损失变量。若基础网络在给定N-1状态不可行，应修正数据、事故集合或基准调度，不能让数据中心业务变量替系统缺口买单。

每个连通岛选一个参考节点：

$$
\theta_{b^{ref},c}=0.
$$

同时设置经数据范围验证的相角边界

$$
-\overline\theta_b\le\theta_{b,c}\le\overline\theta_b,
$$

使候选回路的 $M^{flow}$ 有有限且可证明的上界。大M至少覆盖回路断开时 $B^C_\ell(\theta_o-\theta_r)$ 的最大绝对值，但不得任意取 $10^6$。

## 8. 合同容量可交付性校核

实际需求可能低于已释放的F，因此只对实际 $P^{DC}$ 建潮流会把未使用的firm容量误判为可交付。模型必须增加一套带帽变量 $(\widehat p,\widehat\theta,\widehat f)$，在相同系统负荷、机组可用率和工程状态下校核完整合同容量。

正常状态要求全部合同容量可供：

$$
\widehat P^{DC}_{0}=C_n.
$$

关键N-1响应后允许调用X，但不能削减F：

$$
\widehat P^{DC}_{c}=C_n-\widehat c^{grid}_{c},
$$

$$
0\le\widehat c^{grid}_{c}\le X_n,
\qquad c\in\mathcal C^{crit}.
$$

因此 $\widehat P^{DC}_{c}\ge F_n$。带帽变量使用第7节全部发电、潮流、节点平衡、纠正再调度和硬热限额约束。只有同时通过实际运行和合同容量校核的F/X才允许释放。

带帽X调用也必须满足响应速度、单次持续时间和单事件能量边界。关键N-1枚举是互斥安全检查，不能把所有枚举状态的事件次数相加；事件次数和季度累计能量只对实际运行/抽样事故轨迹聚合。

容量认证同样受共享业务预算约束：

$$
\widehat c^{grid}_{t,c}+c^{green}_{t}
\le D^{flex,cert}_{n}.
$$

$D^{flex,cert}_n$是在完整合同负荷下可提供的业务调用能力，且

$$
X_n\le\overline X_n\le D^{flex,cert}_n.
$$

B6才允许网络认证和绿电服务分别占用完整包络。若只在实际运行变量上共享预算、却让容量认证独占全部柔性，仍会形成规划层重复承诺。

## 9. X响应前后安全

X默认为事故后纠正性调用。若有短时应急额定值，容量校核分成两个子状态：

1. 响应前：事故已发生但 $\widehat c^{grid}=0$，完整 $C_n$ 仍在线，支路使用 $\overline f^{ST}$。
2. 响应后：在 $\tau^{resp}$ 内达到削减量，支路使用 $\overline f^{LT}$，且 $0\le\widehat c^{grid}\le X_n$。

若 $\tau^{resp}$ 小于运行时间步长，小时模型表示响应后状态，但响应前短时校核仍应独立执行。若没有可信的 $\overline f^{ST}$，配置必须把相关X调用定义为预防性削减；不能默认事故瞬间无热风险。

响应能力还满足

$$
\widehat c^{grid}_{c}\le R^{curt,max}\tau^{resp},
$$

并在连续事件轨迹中满足

$$
c^{grid}_{t,c}-c^{grid}_{t-1,c}
\le R^{curt,max}\Delta t.
$$

场景生成器必须记录事故触发时点；触发前 $c^{grid}=0$，到响应截止时点必须达到网络安全所需的削减量。若时间步长大于 $\tau^{resp}$，用响应前/后两个子状态校核而不是把响应时间四舍五入为零。

## 10. 统一业务灵活性包络

### 10.1 共享MW预算

网络削减、绿电移峰和永久业务放弃共享同一真实业务资源：

$$
c^{grid}_c+c^{green}+\ell^{drop}_c
\le D^{flex},
\qquad \forall c.
$$

还需受已接入需求限制：

$$
c^{grid}_c+c^{green}+\ell^{drop}_c
\le D^{conn}.
$$

错误基线B6删除第一条联合约束，改为分别限制

$$
c^{grid}_c+\ell^{drop}_c\le D^{flex},
$$

$$
c^{green}\le D^{flex}.
$$

B6的其他数据、目标、安全和时序约束必须与正确模型完全相同。

### 10.2 恢复债务

可恢复削减量定义为

$$
\chi_{t,c}=c^{grid}_{t,c}+c^{green}_{t}.
$$

恢复债务递推为

$$
q_{t+1,c}=q_{t,c}
+\eta^{defer}\chi_{t,c}\Delta t
-\eta^{rec}r^{rec}_{t,c}\Delta t.
$$

$$
0\le q_{t,c}\le Q^{max},
$$

$$
0\le r^{rec}_{t,c}\le R^{rec,max}.
$$

为禁止同一聚合业务在同小时一边延期一边恢复：

$$
r^{rec}_{t,c}\le R^{rec,max}(1-on_{t,c}).
$$

窗口初始债务由上一连续窗口传入。若窗口间存在足够长、经数据证明的恢复间隔，可设置显式转移上界；否则必须链接状态或强制

$$
q_{last(w)+1,c}=q_{first(w),c}.
$$

对跨季度连续链接的窗口，还需满足

$$
q_{n,first(w),c}=q_{pa(n),last(w')+1,c},
$$

其中 $w'$ 是父节点路径上紧邻的连续窗口。若采用季度边界清零，则必须在父节点末端显式强制 $q=0$，不能只在数据装载时重置。

事件状态也必须跨相邻窗口传递：

$$
on_{n,first(w)-1,c}=on_{pa(n),last(w'),c}.
$$

若不链接，则父窗口末端必须强制 $on=0$ 并完成 $H^{rest}$；否则模型会在窗口边界把一次长事件拆成两次短事件。

压力窗口通常使用 $q_{first}=q_{last+1}=0$。禁止在每个代表日把债务重置为零。

$\ell^{drop}$不进入债务递推，而按永久业务损失单独计量。

主模型取 $\eta^{defer}=1$。若某类降频不需要等量恢复，未恢复部分必须作为可解释的服务质量损失重新分类并计入 $\ell^{drop}$ 或专门损失变量，不能仅把 $\eta^{defer}$ 调小使业务能量消失。

核心三组实验默认 $\ell^{drop}=0$，先隔离可恢复灵活性的作用；永久业务放弃只作为明确标记的敏感性扩展，并继续单独报告。

### 10.3 最大持续时间和事件数

令 $L^{max}=\lfloor H^{max}/\Delta t\rfloor$，$L^{rest}=\lceil H^{rest}/\Delta t\rceil$，并设置有运营意义的最小事件功率 $P^{evt,min}$：

$$
P^{evt,min}on_{t,c}
\le\chi_{t,c}
\le D^{flex}_{t}on_{t,c}.
$$

事件开始和结束变量满足

$$
start^{evt}_{t,c}\ge on_{t,c}-on_{t-1,c},
$$

$$
start^{evt}_{t,c}\le on_{t,c},\qquad
start^{evt}_{t,c}\le1-on_{t-1,c},
$$

$$
stop^{evt}_{t,c}\ge on_{t-1,c}-on_{t,c},
$$

$$
stop^{evt}_{t,c}\le on_{t-1,c},\qquad
stop^{evt}_{t,c}\le1-on_{t,c}.
$$

任意长度 $L^{max}+1$ 的连续窗口中：

$$
\sum_{\tau=t}^{t+L^{max}}on_{\tau,c}\le L^{max}.
$$

代表窗口内保持事件的真实连续顺序；季度事件总数使用窗口出现权重聚合：

$$
\sum_{w,t:k(n)=k}\omega_w start^{evt}_{t,c}
\le N^{event,max}_k.
$$

事件结束后的最小恢复时间：

$$
on_{\tau,c}\le1-stop^{evt}_{t,c},
\quad \tau=t,\ldots,t+L^{rest}-1.
$$

累计可恢复削减能量：

$$
\sum_{w,t:k(n)=k}\omega_w\chi_{t,c}\Delta t
\le E^{curt,max}_k.
$$

永久业务损失能量单独满足

$$
\sum_{w,t:k(n)=k}\omega_w\ell^{drop}_{t,c}\Delta t
\le\overline L^{drop}_k.
$$

$\omega_w$绝不乘入单个窗口内的 $q_{t+1}$ 递推或最大连续时间约束；它只表示该连续轨迹在季度/年度总量中出现多少次。

#### RQ2 L5 时序 recourse 与 B6

RQ2 正确模型必须令

$$
\chi_{t,\omega}=c^{grid}_{t,\omega}+c^{green}_{t,\omega}
$$

并对该物理合计量只建立一套 $on/start/stop/q/r^{rec}$ 状态及第10.2-10.3节全部约束。`grid_need` 是网络层在事故发生时所需的响应幅值；时序模型必须另有显式事件指示量决定该需求在哪些小时激活，不得把最坏 N-1 响应容量复制为全时段持续事故。未观测的事件指示只能标为合成敏感性，不能解释为经验事故序列或概率。

B6错误基线模拟“网络服务与绿电服务分开签约且各自认为拥有完整业务柔性”：分别以 $\chi^{grid}=c^{grid}$ 和 $\chi^{green}=c^{green}$ 建立两套相同参数的时序包络，每套均可使用完整 $D^{flex}$、恢复功率和恢复头寸。该重复使用是B6要量化的建模错误，不是物理可行性见证；报告时必须把真实合计调用 $c^{grid}+c^{green}$ 送入唯一物理包络，并由该包络按最早可恢复规则重新调度共享恢复功率，报告物理预算超额、恢复债务和违约。不得把B6求解器任选的一组双包络恢复轨迹相加后冒充物理执行。正确模型与B6除此以外必须使用相同场景、网络需求、时间顺序、参数和经济目标。

#### RQ2 H2 时序场景外执行

H2先分别在training chronology上求解正确模型与B6，冻结各自唯一的一阶段 `D_flex`；之后对每条名称不重叠的holdout chronology固定该值，只允许求解正确共享包络下的运行recourse，禁止根据holdout重新选择 `D_flex`。所有holdout轨迹共同使用相同网络状态集合、包络参数、服务损失系数和求解器。

若固定策略的holdout recourse不可行，另解一个保持 `c_grid[t]>=grid_need[t]`、令green call为零、固定同一`D_flex`的mandatory-grid时序MIP；只有该诊断也返回`proven_infeasible`，才记为hard temporal failure。固定`grid_need[t]`轨迹的单包络审计只用于给出MW、响应/ramp、持续时间、事件数/休息、累计能量、恢复债务或终端边界的解释性violation code，不能单独证明不可行，因为MIP允许`c_grid`高于下界。timeout、未知终止或诊断不支持不可行证明统一记为unresolved，不进入H2正证据。绿电调用可通过显式 `access_shortfall` 欠交付，不能为了制造hard failure而改成不可松弛需求。

窗口末统计期未完成或显式允许活动事件延续时，保留并报告终端事件状态和恢复债务，标记为right-censored；right-censoring单列，不与失败概率相加，也不对未观察到的事件结束或债务清零作反事实判断。当前实现只接受显式零carry-in窗口，尚未把一个holdout窗口的终态链接到下一窗口。

H2的正向`underdelivers`判据只比较服务结果：B6相对correct的失败概率和期望短缺能量都不得改善，且至少一项严格恶化。恢复债务差值单独报告但不作为服务优势抵消项，因为少履约本身会机械降低需要恢复的能量；允许较低债务抵消更高短缺会奖励不服务。若任一服务delta为负，则只报告各delta，不生成单向H2结论。

连续trace场景从Google压力形状与Alibaba工作负荷形状各自的training/holdout时间段抽取完整小时窗口，二者只按独立边缘分布配对，不声称跨数据集同钟相关。归一化除数只能来自training段或投前冻结的外部常数；窗口末追加的零调用恢复尾部及其headroom属于合成敏感性。网络事件由冻结阈值将Google压力指标映射为`network_call_active[t]`，该指标不是观测事故时点。

时序场景缩减只作用于generated training分布。距离向量按`network_call_active[t]`、`green_call_mw[t]`、`data_center_demand_mw[t]`和`system_load_multiplier[t]`四个分量的显式尺度标准化后，按小时顺序展平并使用fast-forward选择；代表轨迹必须是输入training轨迹的子集，只允许把删除轨迹的概率质量重分配给最近代表点。holdout不得参与选择、距离计算或概率重分配。manual/generated/reduced消融使用同一份生成后冻结的holdout，H2跨来源稳健性只作结果报告，不作为correctness gate。

## 11. CFE归属与匹配

CFE只在正常运行状态 $c=0$ 上核算；N-1状态是安全校核，不按事故状态概率重复计入年度用电。

清洁机组归属量满足

$$
0\le a^{CFE}_{g,t}\le p_{g,t,0},
\qquad g\in\mathcal G^{CFE},
$$

$$
a^{CFE}_{g,t}\le\overline G^{attr}_{g,t}.
$$

$$
y^{CFE}_{t}=\sum_{g\in\mathcal G^{CFE}}a^{CFE}_{g,t},
$$

$$
0\le y^{CFE}_{t}\le P^{DC}_{t,0}.
$$

清洁机组出力、数据中心负荷和网络潮流位于同一个节点平衡模型中，因此其注入与取电同时可行；上述归属变量只做电量属性分配，不宣称物理电子追踪。

### 11.1 年度匹配G1

对每个日历年和每条需要履约的场景路径：

$$
\sum_{k\in\mathcal K_y}\sum_{w,t}
\omega_w\Delta t\,y^{CFE}_{k,w,t}
\ge
\alpha^{ann}
\sum_{k\in\mathcal K_y}\sum_{w,t}
\omega_w\Delta t\,P^{DC}_{k,w,t,0}.
$$

年度权重用于能量聚合，但每个连续窗口内部仍保留真实小时顺序。

### 11.2 小时级匹配G2/G3

$$
y^{CFE}_{t}+g^{CFE}_{t}
\ge\alpha^{hr}P^{DC}_{t,0},
\qquad \forall t.
$$

主比较G2设 $g^{CFE}=0$ 或先求最小可行缺口后固定；G3高目标压力测试允许 $g^{CFE}\ge0$ 并单独报告，不能把CFE缺口与服务缺口合并。

## 12. 多阶段随机扩展

自然场景树描述外生历史，规划决策等价组描述B3/B4/B5允许使用的信息。$F/X/z^{start}$ 直接按决策组索引即可自动满足对应非预见性；$v$和运行补救仍按自然节点或叶索引。投资期望成本为

$$
C^{grid}=\sum_{n\in\mathcal N}\pi_n d_n
\sum_{a\in\mathcal A}C^{inv}_az^{start}_{a,n}.
$$

运行期望成本为

$$
\begin{aligned}
C^{op}=\sum_{n,s,w,t}\pi_n\rho_{n,s}d_n\omega_w\Delta t
\bigg[&\sum_g c^E_gp_{g,n,s,w,t,0}
+\kappa^{access}u^{access}
+\kappa^{grid}c^{grid}_{0}\\
&+\kappa^{green}c^{green}
+\kappa^{drop}\ell^{drop}
+\kappa^{breach,F}u^F
+\kappa^{breach,X}u^X
+\kappa^{CFEgap}g^{CFE}\bigg].
\end{aligned}
$$

firm和conditional非合同违约 $u^F/u^X$在主训练模型中固定为零，不通过成本权重交易。事故状态的调用成本按预设事件频率或独立运行场景计入，不能把所有N-1校核状态当作同时发生的年度能量。

## 13. 服务损失CVaR

对完整长期路径 $\omega$，定义服务/业务损失

$$
L_\omega=\sum_{k,w,t}\omega_w\Delta t
\left(
\kappa^{access}u^{access}
+\kappa^{grid}c^{grid}
+\kappa^{green}c^{green}
+\kappa^{drop}\ell^{drop}
+\kappa^{breach,F}u^F
+\kappa^{breach,X}u^X
\right).
$$

CVaR线性化为

$$
\zeta_\omega\ge L_\omega-\eta^{VaR},
\qquad \zeta_\omega\ge0,
$$

$$
CVaR_\beta(L)=\eta^{VaR}
+\frac{1}{1-\beta}\sum_{\omega\in\Omega}p_\omega\zeta_\omega.
$$

CVaR只进入服务和业务损失目标，绝不出现在支路、变压器、POI或N-1热限额约束右侧。

## 14. 目标和优先级

硬可行层不参与经济权衡：系统原有负荷全供、正常/N-1热限额满足、训练模型中 $u^F=u^X=0$、工程状态正确。主研究目标为

$$
\min\; C^{grid}+C^{op}+\lambda^{risk}CVaR_\beta(L).
$$

其中 $\kappa^{access}$ 表示达产业务因尚未获得接入权造成的延期损失，和“已释放但暂未使用的容量”不是同一概念；unused MW-year不进入目标。规定的年度或小时级CFE目标在主比较中作为硬约束，高目标压力测试才允许显式 $g^{CFE}$。

为防止结论由单点货币系数决定，正式实验还必须执行两类审计：

1. 在看结果前固定 $\kappa^{access},\kappa^{grid},\kappa^{green},\kappa^{drop}$ 和 $\lambda^{risk}$ 的范围，报告T指标、物理能量和风险指标随范围的变化。
2. 生成“接入/服务损失上限 versus 总成本”的epsilon约束Pareto点，确认方法排序不是某个任意权重的产物。

调试模型可使用词典序求解定位逻辑错误，例如先最小化合同违约再最小化成本；这种调试目标不得与正式经济结果混用。

## 15. 确定性MVP启用顺序

| 模型门 | 启用内容 | 暂时固定为零/关闭 |
|---|---|---|
| M0 | 基础DC-OPF、现有网络、正常状态 | 数据中心、扩建、N-1、CFE、灵活性 |
| M1 | 关键N-1和纠正再调度 | 数据中心、扩建、CFE、灵活性 |
| M2 | 候选工程、工期、固定POI和确定性季度需求 | F/X分层；把接入容量作为单一 $C$ |
| M3 | F/X、合同容量校核、服务分层和T指标 | 完整持续时间、CFE和随机场景树 |
| M4 | B0-B2确定性/静态基线 | 随机场景树、完整灵活性和CFE |
| M5 | B3两阶段、B4多阶段、B5完美信息和非预见性测试 | 完整灵活性和CFE |
| M6 | 连续窗口、事件、恢复债务和F1-F3消融 | CFE |
| M7 | 年度匹配G1 | 小时级CFE |
| M8 | 小时级CFE、共享预算和B6错误模型 | 无；进入三组核心实验 |

每一门只在上一门测试通过后启用。最终完整模型使用同一组约束，不另写一个无法与MVP对照的“大模型”。
