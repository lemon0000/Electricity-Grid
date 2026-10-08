# Normal 持久化结果数值重放 v1

状态：DRAFT_NONAUTHORITATIVE。重放只生成数值一致性诊断，不生成 production manifest、
seal、receipt、执行游标或正式实验授权。

## 输入、身份与存储边界

`normal_replay.replay_normal_record` 接受原 normal_store 保存的完整 canonical JSON record，
以及独立保留的 record SHA256、result identity、store identity、replay identity、全部 normal/source
输入与 execution pins、实际规模、solver specification、NormalExecutionBudget 和完整记录字节上限。
它在核查前私有复制 assembly/declaration，前后重建公开来源 pair/normal binding；
原始数据、机制 baseline、初态和时间轴标签的口径保持来源层原定义。

replay identity 绑定本模块、输入 codec、normal_store 和旧 native replay 数值核及其依赖身份。
record identity 独立绑定完整保存内容；仅在记录内自行改写摘要不足以替代调用方保留的外部 pins。
这些身份绑定磁盘实现，不能认证同一 Python 进程的函数未被 monkeypatch 或 runtime instrumentation 修改。
`source_input_binding_verified` 以合作进程确实执行已绑定实现为前提；测试中的 stub binder 是明确的合成边界，
replay identity 不能作为对抗恶意进程的执行真实性证明。

`replay_normal_store` 使用原 normal_store 的合作进程排他锁，要求独立保留的**当前结果 head**，
不能用 genesis 代替；核对 head/result/record 后读取完整记录，重放结束再核对 store inspection。
未完成 intent 或缺失 result 不能进入数值重放。现有 worker 的重开诊断仍可用 genesis，
本模块更严格的入口不改变旧 store 行为。单一 NTFS root 的合作锁不构成跨复制目录全局唯一性。

## 数值检查

1. 只解析严格字段清单与输入类型 allowlist；不反序列化或制造 owned solver result。
   specification、budget、scale 按完整编码摘要核对，保留 bool/int/float 类型区别。
2. 用原 `build_continuous_normal_model` 从独立输入重建固定模型，并核对实际规模。
3. 复用 `grid_evidence_replay._replay` 的纯数值核，复核初值、模型结构、solver/runtime metadata、
   native bound/solution 投影、native→loaded assignment、canonical completions、目标、约束残差和整数性。
4. 原 `audit_normal_assignment` 从保存赋值重新计算完整 NormalAssignmentWitness，内部重放逐小时机组轨迹；
   对见证中的输入/赋值 identity、残差、错误和 terminal carry 逐字段编码比对。未匹配见证不允许接受标志复现。
5. 独立重算完整 core payload 字节数，检查 timing/peak 记录类型；对 core 字节、post peak 和 elapsed
   三个可重算预算错误要求超限时对应错误恰好出现一次，未超限时不出现，同时拒绝漏报、重复和伪造资源拒绝。
   保存的计时值要求有限非负 float，与原执行测量类型一致；预算的合法数值类型保持原合同。
   构模计时清单有 1—3 项；存在 raw 时至少 2 项，有效赋值或接受记录必须恰好 3 项，
   分别对应 admission、native initial、独立 canonical 构模。
   同时核对 total 至少覆盖 preflight/pipeline/audit 之和、嵌套 builder 总时长不超过 preflight+pipeline、
   wrapper 时长至少覆盖 inner total，以及 lifetime peak 的 after 不小于 before。
   只有计时算术偏序允许 1e-6 秒浮点减法/加法误差；原 wall-time 预算比较保持严格阈值。
6. 对照下层已定义规则，重算 normal/source 接受标志、调用数完整性与状态一致性。

本模块采用独立的 `NormalExecutionBudget` 准入与外部 scale pin。
旧 native replay 的公有入口仍要求原 `GridDevelopmentBudget`，旧 20k 等限制和源码均不修改。
纯数值核仅使用其所需的规模字段；本模块不通过伪造旧预算来适配真实规模。
normal/source/kernel/model/旧 replay 文件在本轮保持原字节。

重放模块只构模、载入保存值和计算约束/目标；不 create solver、不 solve、不重试 native 调用。
测试在生成记录后将 solver factory、normal kernel 执行入口及 source 执行入口替换为禁止调用函数，
用于验证这一边界。测试的初始记录来自 tiny 合成网络及显式 stub source，不能作为真实 RTS 数值证据。

## 诊断语义

- `archive_consistent`：已检查的结构、来源、数值与状态字段之间未发现矛盾；partial record 仍可能为 true。
- `native_record_scope`：区分 complete native record、partial execution evidence 与 no native record。
- `assignment_recomputed` / `normal_witness_reproduced`：分别说明数值赋值计算与完整见证比较。
- `accepted_record_reproduced`：原始 source 接受为 true，且相关 native、见证、资源记录及标志一致性检查成立。
- status 区分 `replayed_accepted_normal_record`、`replayed_unresolved_normal_record` 和 `inconsistent_normal_record`。

合法 timeout 或部分 native 返回保留 unresolved，缺 raw/inner return 保持原调用计数 unknown；
当前来源重新可读也不会把记录中的 post-source failure 升级为接受。
损坏 schema、外部 pin 或来源准入失败抛错；已解析记录的数值/标志矛盾返回不一致诊断。

`solver_calls_by_replay=0` 仅指本重放实现；不推断原执行调用数为零。
保存的 wall time、进程峰值只能核查内部一致性和声明门，不能事后重新观测；
`resource_measurements_authenticated=false`。保存的 native LB/UB、status、gap 只能核查报告一致性，
不是独立 MIP 最优性证明。`native_execution_authenticated=false`、optimality/infeasibility certificate 为 null。
`normal_pipeline:`、`post_memory:`、`post_source:` 等异常描述按声明保留，核查其必要字段/状态后果，
不能重建或认证当时究竟发生了何种异常。例如异步中断可发生在 post-source 结果已赋值之后，
不能只凭非 null 的 after 字段断言异常未发生。`archive_consistent` 不等于执行历史已完整认证。
`resume_authorized=false`、`formal_result=false`、`security_certified=false` 保持。

## 后续验收

本模块补数值重放开发证据；不由此关闭整体任务资源、系统 commit 储备、磁盘配额、真实规模 normal、
current/四臂连续运行、训练容量/固定策略、完整恢复/右删失、科学参数注册与正式运行门。
现有 H25 来源/build-only 记录仍未升级为真实求解结果。

## 最终开发验证（2026-09-20）

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_replay_v1.py tests/test_rq2_grid_evidence_replay_v1.py tests/test_rq2_normal_execution_v1.py tests/test_rq2_normal_store_v1.py
```

最终相关回归 **177 passed in 148.23s**，exit 0。独立复核运行：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_replay_v1.py
```

独立 targeted **46 passed in 82.15s**，exit 0。资源拒绝精确投影、计时类型/偏序、峰值单调、
合同编码类型及构模清单数量等 pre-seal findings 已闭合；限定范围无开放实质代码 finding。
这不是 official verdict、seal、receipt 或正式门通过。更早 29/33/38/42 项记录属于开发迭代；
上述最终证据对应以下稳定字节：

| 文件 | SHA256 |
|---|---|
| normal_replay.py | `ffd7b17380ecbef1bf22ce825e6eddcf542826a9954077cb696d54f6bcda4e08` |
| test_rq2_normal_replay_v1.py | `5bc1cad5a59fcce4872d2c5c3824d0110ce0aab8562b6c2e3bd834e029932ab1` |

normal_execution、source_normal_execution、normal_store、normal_worker 及 grid_evidence_replay
源码保持原哈希。`git diff --check` 及新增文件 UTF-8/空白检查通过。
