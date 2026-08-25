# RQ2公开数据鲁棒识别路线图 v6

本文件是v5的科学与执行successor。v5及其202个HiGHS checkpoint保持不变；
v6使用新的Gurobi配置、checkpoint和结果目录。开发机只做代码、测试、诊断和
结果审查，四块cross-solver pilot及正式grid、pairwise、identification均由
执行机完成。

v5冻结manifest记录的旧`formulation.md`字节已不在当前worktree或可达Git
历史中，因此202个checkpoint只保留为非正式诊断证据，不再具备formal resume
资格，也不是v6执行输入。v6从新目录完整重算，不以旧checkpoint支持任何
正式结论。

## 1. 研究问题与科学价值

研究对象是分离签约的网络条件服务与小时级CFE服务对同一业务时序柔性的
重复承诺。当前模型直接优化的是满足full-service training constraints所需的
最小归一化flexibility budget。因此主容量estimand固定为

$$
\Delta D^{flex}_{min}
=D^{flex,correct}_{min}-D^{flex,B6}_{min},
$$

称为`normalized minimum flexibility underprovisioning`。在没有显式
interconnection-capacity变量$X$或可验证映射前，不得称为$X$高估。

## 2. 研究设计与因果逻辑

- RTS-GMLC v4提供541个training和530个holdout 24小时网络+CFE块。
- Alibaba v3提供34个training和34个holdout 24小时业务块。
- 两个来源没有共同日历，只识别保持两边经验边缘的transport polytope。
- training只冻结correct/B6策略；holdout只做固定策略Cartesian replay。
- 每个代表点策略还必须通过完整、grid-evaluable training Cartesian support
  审计。失败cell不进入holdout，不按结果重选代表点或增加容量。

## 3. 方法与统计推断

### 3.1 E0外生电网不可行

若hourly corrective LP在允许`curtailment in [0,D_DC]`时证明不可行，并且
`D_DC=0`端点复算仍证明不可行，则状态为
`exogenous_grid_infeasibility`（E0）。timeout、missing incumbent、
ambiguous termination或solution audit failure均为`unresolved_grid_need`，
不得归入E0。

E0处理固定为：

1. 不删除block，不伪造有限`grid_need`；
2. 无条件报告E0 block probability mass；
3. 对每个E0 power block保留全部Cartesian pair状态行，服务、短缺和债务
   指标为空；
4. contract-risk transport只条件于`finite_grid_need` power blocks并重新
   归一化；
5. E0不计入`R3_common_insufficiency`。

### 3.2 Sharp bounds与共同coupling区域

每个注册metric的transport lower/upper endpoint仍分别是离散transport
polytope上的sharp bound。partial-identification区域兼容性改为在同一个
coupling上同时施加全部metric条件，不能再用不同metric的独立区间拼接一个
不存在的共同见证。identified R1/R2/R3仍要求对应条件对所有允许coupling
成立。

### 3.3 抽样不确定性

在条件finite-grid support上分别对两个经验边缘执行independent marginal
block bootstrap。每个replicate重算transport lower/upper endpoint；正式
设置为200 replicates、seed `20260825`、95% percentile interval。该区间描述
有限经验边缘的抽样变动，不是population identification或经验合同概率。

### 3.4 求解证据

每个SCUC、corrective LP和minimum-flexibility MIP必须记录solver/options、
实际变量数、约束数、incumbent、dual bound、absolute/relative gap和原单位
residual。只有optimal termination、完整solution audit和冻结gap门同时通过
才可标为resolved。

## 4. 结果解释与外推边界

正式结果只允许解释为公开benchmark下：

- E0的无条件经验block质量；
- 条件于finite-grid support的contract-risk sharp bounds；
- correct相对B6的minimum-flexibility underprovisioning、服务损失和恢复债务。

不得外推为Alibaba绝对MW、真实合同违约概率、经验事故概率、PPA/REC履约、
full-N1、AC安全、工程容量认证或$X$高估。

## 5. 学术写作与叙事

主叙事依次为：分离合同为何会重复信用同一时序资源；B6如何形式化该错误；
公开数据为何只识别边缘而不识别联合分布；E0为何必须与业务共同不足分离；
最后报告sharp bounds、共同coupling区域和抽样区间。阴性、部分识别、training
coverage failure和E0均为主结果的一部分，不得选择性删除。

## 6. 审查风险与失败模式

- **结构性风险**：没有显式$X$决策，不能维持“$X$高估”主张。
- **识别风险**：跨源联合分布未知，不能把independent coupling当经验事实。
- **分类风险**：E0若进入R3会把系统本底不可行错误归因于业务柔性。
- **代表性风险**：8x8代表点可行不保证完整training support可行。
- **统计风险**：bootstrap endpoint interval不等于population sharp set。
- **求解风险**：Gurobi与HiGHS若在状态、bound、residual或E0判定上不一致，
  Gurobi successor不得激活。

## 7. 改进与执行路径

1. 开发机完成代码、定向测试、Ruff、manifest和只读R4复核。
2. 执行机运行environment/license/Pyomo tiny-solve preflight。
3. 执行机按固定顺序对普通、拥塞和两个异常block运行HiGHS/Gurobi各两次。
4. pilot通过并回传审查后，机械激活全新的v4 Gurobi grid config。
5. grid package完整发布并验签后才激活pairwise；pairwise验签后才激活
   identification。
6. 执行机回传preflight、pilot、三个正式结果包及activated config。
7. 开发机复核manifest、checkpoint inventory、sharpness、共同coupling
   witness、bootstrap输出和论文claim边界。

当前`formal_execution_ready=false`。这表示handoff已准备但pilot、R4与正式
结果门尚未全部闭合，不表示模型不可行。
