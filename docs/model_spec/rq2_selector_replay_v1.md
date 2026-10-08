# Reference与actual selector来源绑定重放

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE，限定开发验证完成。

实现`selector_replay.py`，复用已验收的原生证据重审与reference/actual exact assignment audit。
目标是从独立输入验证完整selector选择链，作为完整episode归档/重放的下一前置。
本层不恢复session，不执行原生优化，不改变科学协议或既有selector源码。

## 独立输入及归档

两类公开wrapper分别接收typed info/disclosure/before；actual还接收独立PrescribedDcPower。
调用方另给expected_sha256、expected_input_identity、expected_policy_identity和selector/specification/budget。
input与policy均由当前typed输入重算，前态已有policy时必须一致；不能从archive自取expected值。
公开wrapper不接受外部builder，stage模型只通过对应既有_stage_model构造。
actual来源绑定只验证给定功率下的网侧输入；业务动作→actual功率关系仍须episode层验证。
报告business_power_binding_verified固定false。

归档保存完整selector result、原生stage记录、声明及实现闭包，使用canonical JSON。
外部SHA传递钉住全部嵌入记录，但不是原生solver真实性签名。
写入限定_non_authoritative.json及create-only；不是原子持久化commit或跨进程lease，写失败partial文件保留。

## 完整链重算

1. 从独立network的完整sorted UID库存推导n+2 reference或n+1 actual stages；检查原数值/规模/预算门。
2. 对每级核index、label、purpose、previous objective及hex；frozen只能来自已验证prefix的重新计算目标。
3. 用内置builder调用原生记录重审。仅complete_native_record且replay_consistent时，才进入selector stage审计。
4. 复用原_stage audit重算physical witness、真实L1、exact deviation及objective lock；复算finite bounds/gap/accepted。
5. 全级成功或首个rejected后停止是唯一合法终止形状；全accepted短prefix、调序、重复和拒绝后suffix均拒绝。
6. 从fresh witness重算末态generation、selected request、origin/previous/policy/selection identity及result identity，
   将完整重建结果与归档canonical bytes比对。归档的state不反序列化为执行前态。

为了复现既有_digest的dataclass类型身份，私有验证作用域会在完整原生记录重审后构造临时typed raw/stage，
并仅从fresh witness构造state/result。这些对象不进入公开diagnostic；公共接口不返回owned结果或可执行cursor。
最终report构造后，再核独立input、policy及实现身份，检查通过才返回。

## 成功、未解决与partial

reproduced_selected_chain表示完整数值选择链与归档一致，selection_accepted=true。
reproduced_unresolved_chain表示完整返回记录及拒绝语义一致，selector_chain_verified可为true，
但selection_accepted=false、selected_state_identity/selected_request_exact为空。
timeout、零解原生infeasible、无合法赋值等不会被解释为已选择末态。

若原生记录含执行中断/缺失证据，最多验证此前accepted prefix，返回partial_native_evidence。
selector_chain_verified、archive_reproduced、selection_accepted均false；不审计后续stage，不补求解，
不构造该stage的owned raw或后继。归档必须保留unresolved、空selected state/request、accepted=false且没有suffix。
verified_stage_count与accepted_prefix_length分列，避免把重现拒绝当作选择成功。
全部stage（包括partial）的typed raw.calls都计入recorded_solver_calls并与result及预算核对，
call_inventory_verified只证明保存的调用库存内部一致，不认证native真实执行。
调用库存还须满足capture阶段语义：仅create异常允许calls=0；solve及以后（包括仅post_snapshot失败）必须为1。
create异常不得同时包含后续阶段错误、原生返回、赋值、preload或目标/残差等post-call证据；
create失败后追加post_snapshot错误仍保留零调用。该检查不能认证错误文本的真实外部来源。
partial结果的error列表须与末stage错误前缀库存一致，但不宣称已证明中断原因或其保存witness。

所有报告固定native_execution_authenticated/formal_result/security_certified/resume_authorized=false，
exact lexicographic、不可行性、容量与因果证书均为空。原生bound只用于复现声明的数值门，不升级为数学最优性证明。
solver_calls_by_replay_module=0，external_builder_accepted=false；测试禁止capture及两类selector的求解入口。

## 验证与下一项

原86项测试通过后，独立pre-seal发现partial的stage.calls与result.solver_calls可同时被改小而通过库存检查。
已按capture真实执行阶段绑定调用数；新增两臂六阶段联动篡改及create实际失败/计数增加反例。
修复后100项针对性通过（78.41s）；独立固定字节100项通过（79.66s），调用库存finding复核闭合，无新增实质finding。
七文件相关回归348项通过（223.48s，exit 0）。命令前缀为
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`；
目标文件为`tests/test_rq2_selector_replay_v1.py`，相关回归另含grid_evidence_replay、reference_selector、
actual_dispatch_selector、hourly_transaction、episode_coordinator、common_request_adapter对应的`test_rq2_*_v1.py`。
旧原生重放核、小时事务、episode及两类selector源hash与前轮一致。开发SHA256（非production seal）：

- source：`86b015e2bb9475fb7a8e9f1a8f154952a58b6b0ca0b8a2a96fcdb00aaabde2b6`
- test：`8586e32631f1d2a43a026f55fad1183ee9519bb5a2769189ff048a86a6ffcab5`

下一项连接共同请求适配、业务动作、actual调度、资源预留及外层提交，
形成完整episode归档的跨进程只读重放；跨进程唯一发布与安全恢复仍待单独验收。
完整连续输入、训练容量、恢复/right-censoring、正式规模及科学/运行门保持开放。


## 2026-09-20 完整返回episode归档与来源绑定重放

`episode_replay.py`已连接独立初态/逐小时输入、reference选择链、共同映射、四臂业务动作至exact实际功率、actual选择链及外层提交的无solver重放。
完整返回链逐字段比对；partial只报告证据可达prefix，真实actual gap之后可保留未验证后缀；外层中断必须回滚且保留预留。
缺返回不能冒充合法成功或零调用；重审同小时已返回臂并核known/unknown调用及started/skipped/incomplete/unattempted库存。
最终39项targeted通过（170.63s），独立39项通过（176.58s）；限定pre-seal findings闭合。
四文件192项相关回归通过（289.75s），对应最后interrupted-error非空门和相同依赖清单提取之前的直接前驱；最终局部变更由39项完整targeted覆盖，未重跑同范围broad。
合同、精确hash与命令见`docs/model_spec/rq2_episode_replay_v1.md`。原selector重放、hourly transaction与episode coordinator源码保持。
下一必要工作为跨进程唯一执行、持久化提交及安全恢复，包含尚缺invocation journal的in-flight边界；当前不提供可执行恢复游标。
本组件仍为DRAFT_NONAUTHORITATIVE；完整数据、训练容量/固定策略绑定、正式规模、恢复/right-censoring及科学/运行门保持开放。无新真实观测、正式结果或证书。
