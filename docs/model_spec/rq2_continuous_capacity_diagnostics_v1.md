# 连续固定容量策略诊断交付 v1

状态：DRAFT_NONAUTHORITATIVE。输入、固定容量、可用柔性与响应参数均为合成机制假设；
状态和汇总是机制推演，不是真实观测、训练容量证书或网络安全认证。

## 范围与复用

`experiments/export_rq2_continuous_capacity_diagnostics_v1.py`复用已有prefix诊断包的
精确Fraction编码、状态快照和六组合成输入，不修改旧包、旧配置或旧manifest。
另加网络短缺停止、CFE部分响应和输入来源断裂三个4小时场景。四臂均用已声明容量执行共享物理策略；
B6这里不执行分离规划，也不替代已有B6规划拒绝后继或旧B6容量估计。

## 记录与汇总语义

- `inputs.jsonl`保留所有配置输入，包括停止后尚未提交的后缀。
- `records.jsonl`每个提交输入一行；`original_current`保存原始观测与可用柔性，
  `executed_request_projection`是声明动作的派生请求投影，不能解释为原始观测。
  投影可能属于未提交候选，须同时读取`candidate_business_validated`、`committed`和`response_status`。
- Fraction以十进制整数字符串的分子/分母保存；微小服务分量不浮点化、不再次清零。
- `before_execution`、`candidate_execution`、`committed_execution`分别表示此前状态、通过业务验证的候选、
  实际提交到机制回放的状态。grid短缺停止时候选仍保留，但已提交状态不前进。
- `evaluated_candidate_*_shortfall_energy`只累计存在业务候选的短缺；
  `committed_*_shortfall_energy`只累计已提交前缀。两者均为归一化功率×小时，包含逐小时容差内的正短缺。
  未通过业务验证而计算出的中间短缺只保留在记录中，不加入上述总量；未评价数单列。
- 不适用的单服务臂指标为null，适用服务在空前缀上的累计量为0；0不能证明完整履约。
- cohort评价只基于最后已提交账本，保留`deadline_missed`、`deadline_unidentified`和
  `right_censored_before_deadline`。停止候选的新增债务不混入已提交账本。
- 原始错误小时标识单列，不把来源断裂的99解释成99小时有效暴露。
  未提交小时及后缀实际结果、完整服务结果和风险概率保持null。

## 工件与验证

交付包含config、inputs、policies、records、summary、evidence、README及本地diagnostic manifest。
本地清单绑定代码/测试/源配置依赖、运行版本、成员字节与hash；验证重新生成完整载荷并逐字节比较。
这是一致性检查，不是签名或production manifest。拒绝覆盖已有目录；部分写入须保留供诊断，不能冒充完整包。

测试覆盖独立功率/债务守恒、四臂来源/投影、候选与提交分离、3个微小短缺累计大于容差、
空前缀、未知/逾期/删失、微分量JSON往返、重算hash后的语义篡改、缺损与依赖漂移。
主线程最终验证：容量诊断15项及容量策略、aggregate、prefix与composite共5文件
91项通过（30.51s）。新进程分别检查运行时和测试导入模块、读取配置均包含于本地依赖清单。
旧prefix包24组/1038条、composite包32组/1330条重放一致；
旧三个冻结包5/14/22成员hash匹配。独立pre-seal审查发现并闭合运行时/测试依赖清单遗漏，
最终限定范围无开放finding；独立15项targeted及91项相关回归通过，另从记录重算36组的所有
submitted/candidate/committed/unassessed/unsubmitted计数和两类shortfall能量，均一致。

已生成`results/tables/rq2_continuous_capacity_diagnostics_v1_non_authoritative/`：36个case-arms、1091条记录。
生成后的独立命令`--verify-existing`确认成员/hash/依赖/完整重放一致。
审查快照源码SHA256：`c72fb698175230eb434be11c027b9420fa760c180af7e8432fb3232fa86ec9dd`；
测试SHA256：`894f84b768d8c835237a2ef194740168e1c9051bab537cae20c2dc0056383daa`。
本次审查只记录draft findings，不生成official verdict/receipt，不开启formal门。

正式closure仍需连续训练容量及其源输入绑定、真实输入loader、连续网侧dispatch、非零carry-in、
多period、完整holdout分母/权重/删失合同和正式科学协议。本诊断不改变这些门。
