# H1 逐小时 parent 接入持久科学复核子归档（开发）

新增 `experiments/h1_attested_source_parent_development_v1.py`，继承旧 saved parent
的来源/carry、journal 和 anchor 状态机，用版本化 declaration identity 替换 child
协议。旧源代码、旧 v2/v3、此前开发证据保持原字节。本单元是 R3 非正式开发审查对象。

parent 的注册 schema/implementation identity 更新，intent/outcome 的事件外壳沿用
旧 parent event schema，以复用原 chronology reader；事件增加 child_protocol，
outcome 同时绑定 wrapper identity/terminal 与 core binding/terminal。旧 parent
无法以原 declaration identity 打开这个 successor，不迁移或重封旧包。

每小时 wrapper 根包含 binding、terminal 和独立 `attested_hour_non_authoritative`
子目录。core 根的 exact listing 不会与 wrapper metadata 混合。wrapper binding
固定 parent intent head、source lineage、科学 request、packet audit、stage count、
core binding 和实现身份。core 创建但 wrapper binding 失败仅留下 unresolved 文件。
只有完整 core.finish 成功、返回经独立 reader 核验的 projection/pins 后，才写
wrapper terminal。wrapper terminal 绑定 core binding/terminal、projection payload/
identity 与 replay vectors；fresh wrapper reader 成功后才能向 parent 返回 accepted。

`ChildInspection` 是精确不可变类型，projection 仅允许旧 v3 owned replay projection。
storing 状态无 projection 或 terminal；accepted 校验完整 locks、request、零 solver
replay 及 projection 的 native/certificate/published/formal flags。parent outcome
另核对 stage count、wrapper binding 中的 request/packet audit/source/intent/core
身份和全部 authority false flags。carry 继续由旧 `_after` 校验 before identity、
完整 locks、typed projection 和下一小时 boundary。

wrapper reader 从已锚定 parent outcome 取得外部 terminal pin。它检查 exact bounded
文件拓扑，以所有 core 文件的 byte/hash/identity 视图包围 core 的独立科学 reader
及额外一次 public replay_stream，取得可供 carry 的 owned projection；不通过 JSON
反序列化伪造 owned type。完整重开再次核对 wrapper 的文件视图和输入/实现身份。

父 intent 先于任何 child raw。child 异常、wrapper terminal 已落但未确认、child 成功
而 parent outcome 未落盘时，parent 均停止；重开只能得到 pending_unknown，不能从
子目录自行计算 pin 补做 outcome、恢复、重试或推进 carry。当前 core 无科学拒绝
终态；guard/audit/storage 错误一律 unresolved，不包装成 mathematical infeasibility。
若 outcome journal 已写而 anchor 未推进，重开在外部 head 校验处拒绝；测试还覆盖
取得 owned projection 的重放期间 core 文件变化，要求完整视图后验检查拒绝。

## 验收范围与性能限制

测试使用两个小时、单机组的显式 synthetic 数据，原 native 样本不修改。hour 0 沿用
上轮 test-only TimeLimit 元数据适配；hour 1 根据实际 before carry 构造 startup/
shutdown，重建模型结构、assignment references 和 residual 元数据，再由真实 guard、
完整科学 audit、attestation reader 与 parent/carry 门禁验证。它不是 native capture，
不是 RTS producer 或完整 192×232 覆盖。不能把 hour 0 raw 直接作为 hour 1 证据。

192 小时的 384 parent events/385 anchors 容量继续来自未改动的基类及既有明确标注
test-only child oracle 的证据；本单元不重复运行该长容量用例，不将其扩展解释为新
attested child 的完整覆盖。仍需单独的完整规模/资源验证。

正确性路径有显著重复科学重放：core.finish、自身 wrapper finish、重开构造/显式
inspect、parent restore 都会复核；为取得 typed projection，wrapper 在 core reader
之后还执行 public replay_stream。逐步 restore 对历史小时的重放累计为 O(hours²)，
且常数较大。bounded core_view 避免再做一次完整 core reader，但不消除上述成本。
不能沿用 v3 校准 wall 或旧 non-solver 预算宣称本路径资源就绪。

每 child wrapper 额外两个 2048-byte metadata 上限及一个目录。232-stage child
逻辑上界为 3959123968 bytes、3263 files、237 directories；还未计 parent journal/
anchor、外层 Job 日志、filesystem allocation 或完整任务拓扑，资源准入仍关闭。

独立 hour Job/完整 worker、全分段与 observer、typed missing-tail、失败 storage 分类、
全任务预算、实际 reuse DAG/task manifest、共同 Rref/A、完整 LB/UB、完整准入/封存/
全新 official review 仍待完成。native_execution_authenticated、independent_hour_jobs_integrated、
collector_integrated、producer_coverage_proven、resource_admission、whole_task_resources_verified、
formal_execution_ready、formal_result 均保持 false；任何新 native 运行仍需具体就绪包
另行明确授权。
