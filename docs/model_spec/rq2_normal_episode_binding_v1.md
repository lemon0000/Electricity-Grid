# Normal 归档与 mixed episode 初始输入绑定

候选开发期为 DRAFT_NONAUTHORITATIVE，封存状态与独立审查结论由 outer/receipt 记录。目标是把已经通过数值验收、来源重建及完整计划审计的 normal 归档，接到既有 mixed selector episode 输入；四臂、业务动作、债务、selector 和数值阈值沿用已有实现。

## 零求解绑定

`normal_episode_binding.bind_episode` 消费外部 SHA 绑定的 normal/episode bytes、normal request identity、声明大小上限及 bridge binding identity。使用 normal v2 的独立 replay 重建 typed plan；未接受、unknown 或缺少完整计划时拒绝。

normal 与 episode 的完整资源声明按 normals、episodes、envelopes、serial_budget 四字段比较；wrapper 类型不同不影响内容比较。episode 必须引用该 normal task，单独 normal diagnostic 不能产生 episode 依赖。episode 小时连续且被 normal 全窗覆盖，允许具有显式初态的中间子窗。

每小时重新生成 `CurrentGridInformation` 与 `RequestSourceAudit`，分别比较完整编码。当前条件独立于 normal 预测，保持 mechanism_assumption。从 normal 绑定的 PairDeclaration 重新调用已有 source-pair preparation，对完整 ContinuationHour（含 workload 小时、来源标识、CFE 请求）与 CommonRequestMapping 比较；相对位置配对及功率转换仍是机制声明，不能据此推导联合概率或共同观测时钟。

此 bridge 的当前 DC baseline 受既有 pair/common-request 精确对应式约束，必须等于对应 paired baseline；这是该来源接入路径的适用范围。通用 CurrentGridInformation 接口仍允许独立声明的当前条件与 normal 预测不同，其他当前物理条件不会从预测自动复制。

reference/actual origin 用各自声明的 generation、availability、protocol、初始 disclosure 重建；不把 normal terminal carry 当成 incoming origin，也不要求实际初态出力等于 normal 初态。四实际臂保持既有公平初态；业务 anchor 与第一小时相邻。reference input/policy identity 在求解前重算，disclosure 链按逐小时 report 重放。

函数返回绑定报告及同一份完整 typed EpisodeInputs。来源和实现前后复核；绑定期间阻止 normal 求解及 episode 执行入口。

## 接入边界

新增 `normal_episode_transport/worker/controller` 持久接入候选。输入包同时携带 normal request、完整 normal 归档、原 EpisodeInputs、三个内容/请求 pin 和 bridge identity；aggregate wire cap 仍为 16 MiB。worker 执行前后和 parent 发布前独立重建绑定，execute/audit 两份回执以及 parent result 保存同一完整绑定报告，回执重新编码后仍须逐字节比对。

运行检查覆盖三个顶层声明、RTS SHA256SUMS 及其全部成员，以及 config 引用的 power/workload package manifest、全部成员、builder/config 和 power chronology。实际读取的 summary、marginal、power/outage/workload 文件必须列入被 pin 的 members。逐文件核验内容 SHA 与本地文件身份，拒绝路径越界、归一化重复和来源变化；输出与来源目录/文件隔离。parent 在 child release 前复核，worker 每小时执行前及回执发布前复核；最终 full source rebuild 保留。此检查不声称防御恶意瞬时 ABA。

沿用原 mixed episode、Job 监督、one-shot、资源预留及独立 replay；audit 进程使用自己的 scratch，其 episode environment pin 仍重建原 execute 环境以核对旧 header。旧 sealed 实现未修改。

持久失败窗口与 pre-seal 验证完成后，才可封存并交 fresh official review。直接桥接和合成 pipeline 通过都不能单独关闭正式来源或科学门。

验收需覆盖完整 source-pair 篡改、hour/plan/audit/selector pin 错配、资源声明错配、来源漂移、未决 normal、零求解 guard、允许的独立初态与中间子窗，以及连接既有四臂执行器的短合成例。所有 native 历史认证、完整资源认证、formal、exact、安全、capacity 和 causal 标志保持原边界；正式实验未启动。

## 开发验收对应

| 必须保持的行为 | 针对性证据 |
|---|---|
| 完整计划、逐小时来源、pair、selector identity 对应；允许独立初态和覆盖子窗 | `test_rq2_normal_episode_binding_v1.py` |
| 未决 normal 拒绝、single-normal 不授予 episode 依赖、绑定不调用 solver | `test_rq2_normal_episode_binding_guards_v1.py` |
| 完整 wire roundtrip、旧命名空间隔离、内容/请求/bridge pin 错配拒绝 | `test_rq2_normal_episode_transport_v1.py` |
| RTS 成员与间接包成员漂移被检出，实际读取集都有 pin，输出不进入来源 | transport 测试及 `test_rq2_normal_episode_source_inventory_v1.py` |
| execute/audit 回执及 parent result 对应同一绑定，既有四臂 episode 可回放，one-shot 保持 | `test_rq2_normal_episode_pipeline_v1.py` |
| durable launch 后来源变化阻止 release；重新编码的 execute/audit 绑定报告被拒绝 | `test_rq2_normal_episode_pipeline_failures_v1.py` |

实际通过批次、历史失败及代码哈希由 non-authoritative 开发记录保存；测试名称本身不构成通过证据。
