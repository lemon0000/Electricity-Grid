# 流式 normal 模型与同步数值内核

日期：2026-09-21。状态：DRAFT_NONAUTHORITATIVE。

## 实施边界

`continuous_grid_normal_stream.py` 为旧 normal 模型和 assignment 审计提供独立实现后继。
年度输入身份使用已验证的 `identity_stream`，保留旧内容身份；外部必须另行保留并提供
`expected_implementation_identity`。新实现身份绑定本文件、流式编码和旧模型依赖。
模型构造前后均核实现身份，审计末端再次核验；返回的旧类型 witness 仅证明内容与赋值，
不能作为旧实现运行过的证明。

变量、目标、所有 normal 约束、初态残余 minimum up/down dwell、完整变量赋值检查、
残差及 integrality 阈值、独立机组 chronology/carry 回放保持原语义。

`normal_execution_stream.py` 复用旧独立 `NormalExecutionBudget` 和原生 `_solve`，
在私有完整输入快照、各次 fresh build 及返回核查中使用流式输入身份。
其独立 execution identity 绑定新内核、旧预算实现、新模型实现、原生依赖及运行时、
solver specification、规模和 budget。新 owned 类型 `StreamingNormalExecutionResult`
与旧结果类型区分，旧 execution pin 不能授权新内核。

单次最多一次求解、无自动重试，timeout/缺界/gap/赋值失败继续 unresolved；
pipeline 无完整 raw 返回时 solver_calls=null，不能推断为零。
原生已返回但 witness 审计失败时保留 raw 与已知调用数。
结果和 witness 小型证据 payload 仍按旧编码计量；本次替换针对年度输入编码。

## 验收矩阵

| 检查 | 方法 |
|---|---|
| 数学模型不变 | H1/H25/H49 × 4组 commitment/minimum dwell/age，逐项比较变量域/界/fixed、全部约束上下界及独立线性系数、目标方向和系数 |
| assignment 不变 | 正常及功率、flow、integrality、reserve、缺变量反例；比较旧 witness |
| 独立身份 | 错误内容/实现 pin、构模中实现漂移、输入变更、旧执行 pin、新模型实现漂移 |
| 流式路径 | 禁止旧 annual input/build/audit 入口后执行完整 tiny kernel |
| 数值与资源语义 | 原生故障注入、gap/bound/assignment、调用记账、时限/内存/payload接受门、caller mutation、源码依赖闭包 |

## 证据范围与下一项

本轮验证使用 tiny 合成网络；H25/H49 是合成时间长度，不是 RTS-GMLC 真实规模求解。
现有真实 H25 证据仍止于完整 prepare，见 `rq2_normal_task_inputs_stream_v1.md`。
同步内核保留 `hard_resource_limits_enforced=false`、`durable_invocation_tracking=false`、
`public_source_binding_verified=false`、`formal_result=false`，不是任务监督入口。
模型初态及 workload-power 参数继续是明确机制假设。

下一必要工作是消费独立新 source/prepare/binding pins 的来源执行后继，再连接
store、独立 replay 与 controller；保留原预算并验证真实规模的完整执行资源。
本模块不关闭 current/四臂、恢复右删失、风险分母、科学注册或正式启动门。
旧源码、冻结协议、结果及既有诊断工件均保留。

## 本轮验证记录

命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_continuous_grid_normal_stream_v1.py tests/test_rq2_normal_execution_stream_v1.py tests/test_rq2_continuous_grid_normal_v1.py tests/test_rq2_normal_execution_v1.py tests/test_rq2_identity_stream_v1.py`。
结果：242 passed in63.40s；首轮两新文件77项通过后补3项successor专属测试，包含在242项内，不重复相加。
`git diff --check` 无错误；五批既有诊断索引22+13+11+13+15项bytes/hash一致。

| 文件 | 本轮 SHA256 |
|---|---|
| continuous_grid_normal_stream.py | `451c19a299baa4a33792ad3533d05c27f8733ce6b4f11ce2b971886051095198` |
| normal_execution_stream.py | `4462ebc1731aec2e8a5b314d885a5d1e79c09fd349f63eb43d2d0579c3de7644` |
| test_rq2_continuous_grid_normal_stream_v1.py | `7363e0ca2f53ceae03ad73c492c0582749f053e14ee726e961aa13d26df21cfc` |
| test_rq2_normal_execution_stream_v1.py | `88703b2cd99a59fc0ab7642275247f63f0f094634b92fd575edf6afa6a5d2803` |

以上为开发记录，不是production seal或review receipt。

独立只读 R3 pre-seal 审查完成逐段旧实现比较及两新文件测试：80 passed in32.28s，
未发现需返工的实质finding。审查确认模型、数值门、调用记账和身份闭包保持上述边界。
仍须明确：输入deepcopy发生在首次同步peak检查之前，必须由外层Job监督承担硬资源限制；
后继source execution必须消费预先独立保留的新prepare/source/binding pins，
并验证返回类型、数值结果绑定、前后来源一致性及post-source失败时的调用证据保留。
真实规模执行、store/replay/controller尚未验证；此次不是official verdict，不打开正式门。
