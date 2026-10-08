# Gurobi direct normal 完整链开发后继

状态：DRAFT_NONAUTHORITATIVE。目标是将已验证的direct接口接入已有normal执行、来源绑定、记录与独立回放；不改模型、机制输入或数值/资源验收。旧numeric与5秒HiGHS源码、配置和结果保持原字节。

## 最小作用范围

`continuous_grid_native_gurobi_direct.py` 的 `_solve` 与既有 `continuous_grid_candidate._solve` AST完全一致；模型结构、原生变量清单、显式加载、独立canonical重建、残差、integrality、objective/bounds及最优性判定全部复用。它显式绑定direct factory，并有独立execution identity，包含旧native身份、adapter实现身份及自身源码。沿用原 `GridSolveEvidence` 类型，只在带独立契约/身份的新normal记录中使用。每次调用仍至多一次native solve。

`normal_execution_gurobi_direct.py` 保留原numeric输入编码、完整身份复查位置、admission/build/rebuild、witness审计和资源检查，只改native引用、契约和owned result类型。共享 `continuous_grid_normal_stream_numeric.py` 与 `identity_stream_numeric.py`，没有新建或重写正常状态数学模型。adapter的纯 `validate_spec` 在身份计算时即拒绝非固定5秒/1thread/Gurobi13.0.2/seed0/gap1e-8/容差1e-9的规格，不构造solver。

其余七个 `*_gurobi_direct.py` 后继覆盖source、declared execution/store/replay、archive capture、worker和controller。相对numeric仅改import、contract/schema、owned类型及数据库application ID `0x4e474431`；source依赖闭包加入direct native和adapter。旧schema/type/pin不能授权新后继。独立回放仍使用既有数值重建核心，solver calls=0，不能把原生返回对象或JSON恢复成执行权限。

## 同预算 H25 声明

`configs/rq2_normal_task_gurobi_direct_h25_development_v1.DRAFT.yaml`，SHA256 `bd48dcdd47ac45ef3c667e1bbeada8626d923215b1f3e77e5e32d48199e37c08`。runner为 `experiments/audit_rq2_normal_task_gurobi_direct_v1.py`，从SHA固定的HiGHS五秒声明约束差异并重算完整normal→source→declared→replay→controller身份链。

只改变solver为Gurobi13.0.2 direct及其身份/schema/新目录；单次5秒、1线程、seed0、全部容差/relative gap、normal60秒/768 MiB、execute/replay各240秒和controller600秒均保持。目标目录 `results/tables/rq2_normal_task_gurobi_direct_h25_attempt1_non_authoritative`。不重试、不自动延时、不选择正式引擎；旧跨solver pilot不直接认证当前模型。all-off初态、U250和功率映射仍为机制参数。

## 验证进展

初次核心移植遗漏嵌套函数所需的version/_enum/_raw_number导入，35 failed/41 passed（30.31秒）；补齐后kernel61 passed（33.42秒）。独立pre-seal另发现误导入旧模块 `__name__`，已删除并增加fresh-import模块/函数来源反例；adapter边界docstring相应更新。

最终核心组合为156 passed（151.87秒）：kernel65、adapter15、source/declared76。包括真实Gurobi tiny求解、完整normal witness、AST/实际全局对象一致性、adapter身份漂移拒绝、旧numeric pin拒绝及各数值/resource失败分支。此前source/declared76通过是在模块来源修复前，已由本组合重新覆盖。

真实tiny写入新store并由新回放零solver复算的两项检查通过（18.98秒）；runner20项通过（4.98秒）。下游全组回归进行中，当前不宣称H25执行就绪。worker移植测试中的int/float预算样例需由1更新为5，曾在两次组测中导致1 failed/60 passed、1 failed/20 passed；均为测试样例尚未与固定5秒匹配，第二次运行已加载旧函数，文件修正后单项复测通过（2.89秒），完整受影响组正在重跑。生产资源或数值门未放宽。

最终store/replay为118 passed（680.01秒）；worker/controller/reports为117 passed（341.23秒），均exit0。capture的40项已在前述60 passed组中通过，未因后续worker测试样例调整改变实现。以上为分组检查，不是单次全套统计。

独立只读pre-seal实质finding已闭合，复核五级身份一致、固定预算和新目录不存在；独立core定向3项及runner20项通过。允许推进预先固定的一次受限H25开发任务；不产生official verdict或正式/安全认证。runner SHA256为 `fde49769517ed63d93bb9a5a2661356642d18e88a22d10f66377126821f396f6`。

## 单次H25开发实测

compute Python `-B` 调用上述runner，传入固定声明/runner SHA以及 `--execute-development`。最初外层PowerShell引号错误在启动runner前产生NameError，未创建日志或任务；修正调用包装后仅执行一次任务，无solver重试。日志为 `results/logs/rq2_normal_task_gurobi_direct_h25_attempt1_non_authoritative.log`。

controller229.141秒；execute/replay122.797/102.828秒、exit0且Job静默，commit峰623370240/614858752 bytes。normal42.8698899秒，其中preflight21.5288245、pipeline17.1954283，嵌套builders4.3712107/4.3908041秒，witness0。调用1次，在求解阶段报 `Model too large for size-limited license`，另保留 `structure_options_or_version_drift`。solution_count/objective/LB/UB均null、assignment_valid/optimal/native_infeasible均false。未取得赋值，不是数学不可行或求解性能证据。

record1917165 bytes，SHA256 `a1fb73aede82acb9382ab1fbe1cf7ebc3fd2a173154e2d63e7cf88c22d32fc55`；result identity `8b6c2c2e6bebbf09045f90277e7520c65ce323caee5c8aab554157aaf81665d4`。双capture一致，SQLite application ID为0x4e474431。独立回放archive/source一致、errors=[]、solver calls=0，accepted_record_reproduced=false；replay report SHA256 `cf4577bba82c90be08888d849e594d2df3037a9ab2e61bcb56fc19e405a62261`。API completed_development_replay_diagnostic与落盘validated_before_final_observation_write对应不同写入时点。

宿主GRB_LICENSE_FILE指向存在的本地许可文件，当前受控声明未包含该键，继承normal_worker._environment的exact whitelist也拒绝该键。tiny规模不能暴露容量限制。下一步是显式许可路径传递的最小后继及相同受控环境容量核查，保留本次绑定字节；不把宿主许可文件存在当作当前子进程容量通过。

新122项索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/gurobi_direct_task_attempt1_evidence.json`，SHA256 `289173afc81967b76eeb7cbc58ed8588fd695d5313f9eda2234ecfc79d9c0da0`；另14个历史索引/569条旧证据经root复核一致。全部数据机制/正式门保持原状态。

独立结果审查进一步确认：child使用完整显式environment block，且worker校验其与packet完全一致，宿主许可定位变量确未传入。`structure_options_or_version_drift`为求解抛错后pre_structure仍为None触发的次生guard标签，不能另断言实际发生结构/选项/版本漂移。此次结果也不能表述为宿主学术许可容量不足或五秒搜索未找到incumbent；有效优化尚未开始。后继只需复用已完成的normal内层，补worker/controller许可环境合同并先做同环境容量检查。

独立只读审计已复算122项新证据与569项历史证据一致。calls=1仅为wrapper调用前计数；本记录无SolverResults/solver_records/problem_records，不证明进入optimize。结果审计不产生official verdict或任何正式执行权限。
