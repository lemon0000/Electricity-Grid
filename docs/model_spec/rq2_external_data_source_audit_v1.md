# RQ2外部数据源审计 v1

## 1. 研究问题与科学价值

筛选标准不是“数据规模大”，而是能否改善RQ2中业务柔性、功率、CFE与网络
调用的可识别性。只有来源可追溯、许可证明确、字段可复算且能进入冻结数据
契约的数据才接入。

## 2. 研究设计与因果逻辑

| 数据源 | 决策 | 主要理由 |
|---|---|---|
| RTS-GMLC | 接入 | 同一benchmark内提供连续负荷、可再生、网络和可靠性参数 |
| Alibaba PAI v2020 core | 接入 | 两个月生产作业、资源请求和匿名相对时钟 |
| Alibaba `pai_sensor_table` | 接入 | 同一PAI作业键上的实际GPU利用量和显存协变量 |
| NLR GenAI Power Profiles v2 | 接入 | 公开H100训练/推理节点功率和动态形状 |
| WattGPU固定子集 | 接入 | 覆盖PAI T4型号的异构GPU inference功率参考 |
| AcmeTrace | 暂不接入 | 公开job trace不含逐job功率、deadline或checkpoint进度；约80 GB utilization不解除当前关键门 |
| MLPerf Power | 暂不接入 | 可验证系统级benchmark功率，但不是生产作业 chronology |
| Hydra等调度器样例 | 不作为观测数据 | deadline/checkpoint为实验设定或模拟输入，不是生产合同证据 |

## 3. 方法与统计推断

已接入源均锁定上游版本、许可证、原始对象SHA-256和处理代码SHA-256。
跨源连接仅允许按明确层级进行：

1. PAI core与sensor可按匿名job/machine键连接；
2. PAI T4与WattGPU Tesla T4只按硬件型号形成外部功率参考；
3. NLR H100与PAI不做硬件或作业配对；
4. RTS-GMLC可靠性抽样只形成benchmark事件，不形成经验事故概率。

## 4. 结果与外推边界

新增证据把“只有GPU请求”推进为“请求、完成时间、生命周期平均实际GPU利用
量及T4同型号功率参考”。它仍没有同一作业的电功率测量，因此不能识别
`P(job power | workload, utilization, hardware)`，只能用于预注册的区间和
参数敏感性。

## 5. 学术写作与叙事

应使用“分源公开benchmark证据链”和“同型号硬件参考”。不得使用“联合实测
数据集”“经验履约概率”或“已校准PAI功率”等表述。

## 6. 评审风险与失败模式

- 用WattGPU inference覆盖PAI training/unknown workload会造成transport
  bias；
- 把PAI生命周期平均利用量展开成逐时曲线会制造不存在的时间信息；
- 把Acme论文中的checkpoint系统描述当作逐job checkpoint观测会发生
  evidence-conclusion mismatch；
- 继续增加不配对trace只增加样本量，不改善核心识别。

## 7. 改进路径

1. 首选获取同一GPU作业上的绝对功率、利用率、作业类型和时间戳；
2. 次选在可控T4/V100/P100硬件上复现实验并冻结跨硬件映射误差；
3. deadline、checkpoint、恢复效率和headroom必须来自合同或可复现实验；
4. 在上述证据缺失时，后续模型必须报告区间结果，不得输出单点认证容量。
