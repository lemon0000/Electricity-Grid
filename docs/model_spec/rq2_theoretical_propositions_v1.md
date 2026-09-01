# RQ2 派生理论命题备忘 v1

更新日期：2026-08-25

## 文档角色与不变量

本文件从`docs/model_spec/formulation.md` §10.6–10.7和冻结的RQ2公开边缘v6合同
推导三个可审计命题，不修改模型、estimand、ambiguity set、阈值、runner、配置、
manifest、result schema或任何hash-bound输入。T1–T3是理论命题，避免与文献证据
中的经验P1–P3混淆。

当前证据状态不因这些推导改变：70-cell derived benchmark仍为
`R1=0, R2=0, R3=69, mixed=1, unresolved=0`，original positive H2 unsupported，
且`formal_execution_ready=false`。数学命题的成立不证明现实合同重叠、经验发生率、
因果效应、工程安全或正式实验结果。

共同记号如下：

- 时间集合`T`有限且非空；
- transport行、列边缘`p,q`是有限概率向量；
- `Π(p,q)`只包含保持这两个边缘的非负coupling，除非另行显式编码结构约束；
- `resolved`表示所需数值和求解证据完整，timeout、missing incumbent或不完整证书
  不得当作infeasible或有限outcome。

## T1：instantaneous MW-only共享包络差值的精确界

### 精确定义

给定任意有限非空`T`及非负调用序列`g_t,c_t`，定义

$$
G=\max_{t\in T}g_t,\qquad C=\max_{t\in T}c_t,
$$

$$
R_S=\max_{t\in T}(g_t+c_t),\qquad
R_B=\max\{G,C\}.
$$

`R_S`是同一瞬时MW预算承接两项调用所需的最小reserve；`R_B`是把两项调用分别
按各自峰值记账、再取较大者的MW-only B6 reserve。这里没有duration、event、rest、
energy、recovery或debt状态。

### 最小假设

1. `T`有限且非空，使所有maximum attained；
2. `g_t>=0`且`c_t>=0`；
3. 两个reserve使用同一时间索引和相同功率单位；
4. 结论只比较instantaneous MW peak，不加入跨时状态或可行性约束。

### 正式结论

$$
0\le R_S-R_B\le\min\{G,C\}.
$$

而且严格正差值的充要条件是

$$
R_S-R_B>0
\quad\Longleftrightarrow\quad
\exists t\in T:\ g_t+c_t>\max\{G,C\}.
$$

因此，严格正差要求某个时点两项调用同时为正且合计突破较大的单项峰值；仅有
正值重叠并不充分。

### 证明草图

对每个`t`，`g_t+c_t>=g_t`且`g_t+c_t>=c_t`，故`R_S>=G`且`R_S>=C`，
从而`R_S>=R_B`。另一方面，`g_t+c_t<=G+C`给出`R_S<=G+C`，于是

$$
R_S-R_B\le G+C-\max\{G,C\}=\min\{G,C\}.
$$

严格正条件直接来自`R_S>R_B`与有限maximum的定义。

### Tight、equality与zero-gap例

- **Upper-bound tight，同峰：** `g=(5,1)`、`c=(3,0)`时两个maximum同在首个
  时点，`R_S=8`、`R_B=5`，gap为`3=min(5,3)`。一般地，当`G,C>0`且存在同一
  时点同时达到`G`与`C`时，上界取等。
- **Gap=0，错峰：** `g=(4,0)`、`c=(0,3)`给出`R_S=R_B=4`。
- **Gap=0，被主峰吸收：** `g=(5,3)`、`c=(0,1)`在第二个时点存在正值重叠，
  但合计`4`未突破主峰`5`，仍有`R_S=R_B=5`。

更一般地，gap为零当且仅当所有`t`都满足`g_t+c_t<=R_B`。

### 否定或失效条件

在上述假设内，任何满足非负性和有限性的反例若违反该双边界，即否定T1。
若调用允许负值、时间轴不一致、reserve不是peak定义，或加入跨时状态，结论不是被
经验数据“否定”，而是超出T1作用域。

### 论文主张边界

允许主张：T1精确刻画instantaneous MW-only层中，共享记账相对分离峰值记账的
容量差及其tight/zero条件。

禁止外推：T1不能推出完整duration/event/rest/energy/debt MIP的一般可行域嵌套，
不能证明固定策略场景外风险为正，也不能证明现实中存在双重签约或估计其发生率。
分离轨迹会改变事件分段和恢复状态，完整模型结论必须由冻结MIP与固定策略回放产生。

## T2：transport ambiguity下正效应的robust-sign三分法

### 精确定义

给定有限概率向量`p=(p_i)`、`q=(q_j)`和每个完整、resolved Cartesian pair上的
冻结scalar outcome `Δ_ij`，令

$$
\Pi(p,q)=\left\{\pi\ge0:
\sum_j\pi_{ij}=p_i,\ \sum_i\pi_{ij}=q_j\right\},
$$

$$
\mathrm{LB}_{\Delta}=\min_{\pi\in\Pi(p,q)}
\sum_{ij}\pi_{ij}\Delta_{ij},\qquad
\mathrm{UB}_{\Delta}=\max_{\pi\in\Pi(p,q)}
\sum_{ij}\pi_{ij}\Delta_{ij}.
$$

下文以`LB_Δ,UB_Δ`指代这两个端点。当`Δ`取主容量estimand时，方向固定为
`Δ=D_min^{flex,correct}-D_min^{flex,B6}`，正值表示B6的minimum-flexibility
underprovisioning。

### 最小假设

1. `p,q`非负、有限且各自和为1，因此product coupling保证`Π(p,q)`非空；
2. `Δ_ij`全部有限、冻结且resolved；
3. ambiguity set恰为声明的`Π(p,q)`，任何support、时间或合同结构限制若存在，
   已经显式进入集合；
4. `LB_Δ,UB_Δ`由通过审计的transport LP求得。

### 正式结论

由于`Π(p,q)`是非空紧致polytope，线性expectation的两个端点均attained。因此：

1. `LB_Δ>0`当且仅当**所有**admissible couplings均给出strict-positive
   expectation；
2. `UB_Δ<=0`排除任何strict-positive admissible coupling；
3. `LB_Δ<=0<UB_Δ`表示positivity partially identified：至少存在一个非正
   coupling和一个正coupling。边界`LB_Δ=0<UB_Δ`也属于本类，零值witness已
   attained，不能升级为robust positive。

### 证明草图

`Π(p,q)`由有限线性等式与非负约束定义，并被总质量1有界，故紧致。线性函数
`E_π[Δ]`连续，所以minimum与maximum均由某个coupling witness取得。若`LB_Δ>0`，
每个可行expectation至少为`LB_Δ`；反之，如果每个coupling都strict positive，
取得minimum的coupling也strict positive，故`LB_Δ>0`。其余两类直接由attained
endpoints与次序`LB_Δ<=UB_Δ`得到。

### 2x2反例与independence边界

取uniform marginals `p=q=(1/2,1/2)`及

$$
\Delta=\begin{bmatrix}1&-1\\-1&1\end{bmatrix}.
$$

对角coupling给出`E[Δ]=1`，反对角coupling给出`E[Δ]=-1`，故sharp interval为
`[-1,1]`。independent coupling `π^ind_ij=p_iq_j=1/4`给出mean `0`。它只是
`Π(p,q)`中的一个admissible point，不是跨来源joint law的经验事实。作为
admissible nonpositive witness，它已经排除all-coupling strict positivity，
与`LB_Δ=-1`一致；但它不识别现实未知coupling或population joint law的符号。
区间`[-1,1]`表示真实coupling下的符号partially identified。

### 否定或失效条件

在最小假设内，若存在`LB_Δ>0`但某个admissible coupling expectation非正，或
`LB_Δ<=0<UB_Δ`却不存在相应端点witness，即否定T2。若pair缺失、outcome unresolved、
边缘未归一化、transport证书失败，或实际joint law还受未编码结构约束，则只能说
该应用未满足T2假设，不能据不完整结果判断robust sign。

### 论文主张边界

允许主张：`LB_Δ>0`只支持**相对于已声明ambiguity set**的all-coupling robust
正号；`LB_Δ<=0<UB_Δ`必须报告为partial identification；`UB_Δ<=0`排除该集合内
严格正号。

禁止外推：independent/comonotone/countermonotone单点不是现实coupling；这些界
不识别真实合同发生率、因果效应、population joint law或工程风险概率。

## T3：单metric sharp endpoints与多metric共同见证不可拼接

### 精确定义

设每个完整finite Cartesian pair上有两个resolved scalar metrics `A_ij,B_ij`。
分别在同一`Π(p,q)`上求

$$
U_A=\max_{\pi\in\Pi(p,q)}E_\pi[A],\qquad
U_B=\max_{\pi\in\Pi(p,q)}E_\pi[B],
$$

并保存各自optimizing coupling witnesses `π^A,π^B`。逐metric endpoint sharp
表示该端点在声明的ambiguity set内可达；它不表示不同metric的端点由同一个
coupling同时达到。

### 最小假设

1. `p,q`有限且`Π(p,q)`非空；
2. `A_ij,B_ij`覆盖完整Cartesian product，全部finite且resolved；
3. 所有真实结构限制都已进入同一个admissible coupling set；
4. 每个endpoint均有通过边缘与objective复算的coupling witness。

### 正式结论

在这些假设下，每个metric的transport LP endpoint相对声明集合是sharp且attained。
但不同metric的endpoint witnesses一般不同，不能把`U_A`和`U_B`拼成一个可达的
vector或科学区域。多metric区域兼容性必须存在**同一个coupling** `π`，同时满足
该区域的全部metric条件。

若缺少任一pair、存在unresolved outcome，或实际joint law还受未编码的共同时间、
support、因果或合同结构限制，则不得对目标集合称sharp；最多报告当前已编码集合下
的诊断bound或unresolved状态。

### 证明草图

单metric sharpness来自与T2相同的紧致性和线性目标：每个maximum由某个witness
取得。多metric拼接则要求交集
`{π:E_π[A]=U_A} ∩ {π:E_π[B]=U_B}`非空；分别知道两个集合各自非空，并不推出
它们的交集非空。因此区域兼容性是一个共享coupling feasibility问题，而不是逐列
interval检查。

### 2x2共同见证反例

取uniform marginals，并令

$$
A=\begin{bmatrix}1&0\\0&1\end{bmatrix},\qquad
B=\begin{bmatrix}0&1\\1&0\end{bmatrix}.
$$

对角coupling使`E[A]=1`，所以`U_A=1`；反对角coupling使`E[B]=1`，所以`U_B=1`。
但`A_ij+B_ij=1`对每个pair都成立，故任意admissible `π`都有
`E_π[A]+E_π[B]=1`。不存在同一`π`同时达到`E[A]=E[B]=1`；两个逐metric maximum
拼成的点`(1,1)`不可达。

### 否定或失效条件

如果能在该例和相同marginals下构造一个合法coupling同时实现两个maximum，T3的
不可拼接反例即被否定。对实际应用，完整pair、resolved status或结构约束任一缺失
都会使sharpness前提失效；补齐数据或收紧ambiguity set后必须重新求endpoint与共同
witness，不能沿用旧端点。

### 论文主张边界

允许主张：完整且resolved的finite Cartesian outcomes给出相对于声明transport
polytope的逐metric sharp endpoints；多metric区域必须由同一个coupling见证。

禁止外推：不能把不同metric的optimizing witnesses拼成一个联合结果，不能把缺失/
unresolved pair当作零值或不可行，也不能把marginal bootstrap的
`bootstrap endpoint interval`解释为`population identified set`。bootstrap只描述
有限经验边缘重抽样下endpoint估计的变化，不改变条件transport identified set。

## 论文使用清单

1. T1只作为MW-only解析边界，并与完整时序MIP结果分栏报告。
2. T2报告`LB_Δ,UB_Δ`及optimizing witnesses；independence仅作诊断点。
3. T3对每个区域保存一个共同coupling feasibility witness或明确infeasible证书；
   不用逐metric端点拼接区域。
4. 任何theory-to-evidence过渡都保留公开边缘、E0、right-censoring、unresolved和
   certification边界；理论推导不提升实验gate或paper claim状态。
