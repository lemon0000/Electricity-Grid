# H25已有赋值复用的前提核查

状态：DRAFT_NONAUTHORITATIVE。2026-09-28零solver只读核查；不修改normal验收、预算或旧工件。本页区分技术可提交性与现有任务验收适用性。

## 已核实的来源

来源为`results/tables/rq2_normal_task_gurobi_ordered_h25_attempt1_non_authoritative/normal_non_authoritative/normal.sqlite3`。以`mode=ro&immutable=1`读取，`PRAGMA integrity_check=ok`；result payload为6806997 bytes，SHA256为`2fc450ac5e19e434dcb8e2f7408b9beb442e89113e732f1d3cec63967d54173e`，与存储digest及既有结果记录一致。

`GridSolveEvidence.loaded_values`包含22275个唯一变量名，值全部有限，与`initial_values`的有序变量名完全一致。原生返回22250项，另25项来自canonical completion，不能把全体称作原生赋值。记录的assignment_valid=true、optimal=false、calls=1。原完整赋值/见证及零solver回放证据见`rq2_normal_gurobi_ordered_v1.md`；本次只读计数没有重新构模复核全部约束。

输入身份为`d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`。旧结构身份为`e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0`。这些绑定只覆盖该开发输入；不能据此向其他窗口、场景或holdout提供赋值。

本机安装的Pyomo `GurobiDirect._warm_start`遍历Pyomo→Gurobi变量映射，对有值变量设置`GRB.Attr.Start`。这支持实现MIP start的技术可能性，不证明solver已接受该start、能够收敛或会保留同一最优赋值。

## 当前验收上的限制

`normal_execution_gurobi_ordered.py`的接受条件要求`raw.calls == 1`且`raw.optimal`；固定开发声明的求解预算为15秒，当前短开发normal入口的observed-wall cap为60秒。`raw.calls`只计本次`_solve`调用，不计来源链的历史调用。旧normal已经使用一次调用，该内核实测56.4923187秒。

若用旧结果再调用solver，来源链至少包含两次调用，但新后继自己的`raw.calls`仍可为1；当前内核不会自动累计历史求解，也不会仅因来源链有两次调用而触发该字段拒绝。来源链累计是需要新外层合同处理的provenance/accounting要求。新调用的15秒上限不能被称为整条链的累计求解上限；来源生成、读取、审计、start提交和新结果审计成本必须分别记录。只有假设将旧normal生成阶段重跑并嵌入同一次、仍受60秒开发cap约束的新任务，且其耗时仍为56.4923187秒时，其余阶段才仅余3.5076813秒。此条件算术不是新阶段实际耗时预测、正式全任务预算或warm start必然超时的证明。

若将旧结果作为离线预计算输入，则必须明示预计算来源和成本，并定义可复用范围、缓存命中/未命中行为、策略身份及四臂公平性。现有单调用声明没有这个执行契约，不能以新调用单独通过来关闭旧normal门，也不能把旧结果当作零成本外生观测。

因此，已有赋值可作为开发诊断的候选start，但目前不构成现有normal验收的直接修复。先不复制完整warm-start执行链，也不启动H25 warm-start求解。

## 实施前必须解决的事项

1. 明确start在同一次normal内生成，还是来自单独计费的离线阶段；制定完整调用和时间记账，保持旧协议及其结果。
2. 新模型逐变量核对UID、索引、边界、域、固定状态、输入和结构；重新验证canonical completion及全约束。通过`Start`提交，不以fix变量替代，不改变物理初态。
3. 区分start提交、原生接受与最终赋值审计；记录最终LB/UB、gap、残差和全部调用，失败仍为unresolved。
4. 验证同目标的不同normal赋值对后续reference/current及四臂的影响。目标值相等不足以证明策略等价。

## 资源上限的来源与后继工作

进一步检查`normal_execution.py:NormalExecutionBudget.__post_init__`：单次solver最多30秒、observed wall最多60秒是代码中的short normal cap。`rq2_normal_execution_v1.md`将它明确归为短开发范围，并说明`normal_accepted`不是formal-ready或完整服务证书。当前ordered声明进一步固定solver为15秒。

据此应区分以下层次，不能把短开发cap自动提升为论文科学标准：

| 层次 | 当前约束 | 后继处理 |
|---|---|---|
| 旧短开发任务 | 单次15秒求解、normal60秒、768MiB及原结果身份 | 原样保留；不能重写旧结果为通过 |
| 数值与物理验收 | 原gap、LB/UB、残差、完整赋值/见证、来源和回放检查 | 任何后继均保留；timeout不作不可行结论 |
| 真实规模执行资源 | normal、reference、actual、全UID、四臂及总任务的时间/内存/存储与中断规则 | 需要单独完整声明和验证；旧normal通过不自动覆盖 |
| 科学协议 | 机制参数、连续服务、右删失、风险分母、四臂公平性和注册 | 不由资源声明或warm start替代 |

下一项为现有连续规模执行合同补充可审查的真实规模资源方案及验收矩阵，明确normal与完整episode的预算、累计调用及预计算边界，再决定warm start是否值得实现。不得依据这一来源区分直接更改旧代码cap或启动更长求解；新执行方案须走适用的独立审查与运行授权。改变正式协议或认证口径仍按agent.md第7节处理。

### 无solver的完整路径资源算术

沿用`rq2_continuous_scale_execution_contract_v1.md`的完整UID计数，n=158、H=25时，reference每小时160次、四臂actual每小时合计636次，整窗19900次，另加normal一次。现有`EpisodeBudget`最多120次调用/60秒solver预留，不能容纳这一路径；只使normal通过并不能解决此项。

下表只把每阶段假设TimeLimit乘以19900，展示预留量级，不是实测时间、推荐配置或运行授权；normal、构模、审计、存储、回放和重试尚未计入。

| 每个reference/actual阶段假设上限 | 单个H25完整路径solver预留 | 若46 cells各仅执行一个这样的路径 |
|---|---:|---:|
| 1秒 | 19900秒，约5.53小时 | 约254.28小时 |
| 15秒 | 298500秒，约82.92小时 | 约3814.17小时 |
| 30秒 | 597000秒，约165.83小时 | 约7628.33小时 |

46-cell列仅为条件性乘法，不是全实验任务清单；容量搜索、多窗口、seed及holdout会有另外的任务数。正式范围的数量须从最终连续协议派生，不能沿用该假设直接报价或放行。

资源方案应先完成三项，而不是继续独立normal性能探针：列出实际任务数和依赖；分别声明normal与selector的单次/全任务预算及停止规则；评估保持全UID语义的复用或已证明冗余阶段的处理是否必要。任何阶段减少仍须满足既有等价性和数值锁定要求，不能从此算术直接删阶段。

## 本次验证

直接调用现有`EpisodeSession`模块的`_requirements`，上述三个假设分别返回796 calls/hour和整窗19900/298500/597000秒预留；`EpisodeBudget(25,19900,19900)`按现有调用cap拒绝。未调用solver。旧normal源码SHA256仍为`c11b4fc0fc465b67443758bf0469734a17e12f9378528be79d43f1124318f183`，ordered声明SHA256仍为`688c2090f8e26c08b744fea7f61dfef38726d29ed69163727efa23575ccca03d`。`git diff --check`通过。独立pre-seal提出的本次调用/来源链累计区分和60秒开发cap措辞已修正并经独立最终文字复核闭合，限定范围无剩余实质finding；没有关闭正式门。
