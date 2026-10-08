# 混合 selector 外层执行接入 v1

## 范围

本 successor 将已封存的 `scale_selector_zero_face` core 接入版本化 store、worker、controller，
并提供 source-bound journal record 回放。旧 store/worker/controller、旧 SQLite、旧记录与
normal/selector 已封存字节不修改。episode 接入、完整资源认证、真实158 UID与全支持成本、
完整科学合同及 training/holdout 仍为外部门。

三个执行模块基于现有对应模块作有限适配：独立 schema、`MixedSelectorRequest`、
`MixedSelectionResult` exact type、新 SQLite application_id、worker 输入类型和实现依赖。
原事务、lease、Job 与文件身份检查继续保留。新请求不能冒充旧请求，旧读取器不接受新 journal。

## 执行与证据合同

- `DevelopmentMixedSelectorStore` 在任何 kernel 调用前提交 durable one-shot intent。
  intent 仍预留全部 UID stage 和完整最坏 solver seconds，解析节省不减少事先预算。
- 返回后记录实际 solver calls。未返回或写入失败保持 `pending_unknown`；lost acknowledgement
  不允许重试。保存结果的状态为 `returned_unverified`，不自动成为数值接受。
- worker 仅解码固定类型词汇、固定有序字段及 canonical 有限 hex，限制输入深度/数量/bytes，
  检查外部 request SHA 与实现身份，生成独立 non-authoritative receipt。
- controller 在 release 前持久保存 request、intent、launch，并使用原 Windows Job 监督。
  退出、PID/creation、whole Job quiet、receipt/request/SQLite/result 绑定均须通过。
  新 controller 复用并绑定既有 `_successful_observation`，要求资源/监测错误为空、
  仅 direct-child-exit marker、Job limit 确已配置、峰值/采样/时长/commit/disk 储备合法、
  observation 内部所有 authority flags 均 false；矛盾的成功退出记录也不能发布 result。
  执行过程不提供 resume；不把 timeout、commit limit、缺结果或未知调用变成数学不可行。
- controller 的成功仅表示 `returned_unverified`；`numerical_evidence_verified`、
  `whole_task_resources_verified`、`formal_result` 仍 false。

`scale_selector_zero_face_archive._verify` 由调用者提供独立保留的 record SHA、journal binding
identity、实现 pin 和 typed request。它先复核 schema、result identity、input/policy/hour/UID/
history/power/完整预算，再调用已封存 core replay 重算全部 native prefix 与 analytic suffix，
要求完整结果 byte equality。selected 才返回重建的状态；unresolved 返回 None，
`archive_reproduced=false`、`selection_accepted=false`。整个回放 solver calls=0。
该接口不凭 record 自报 hash 认证外部执行，调用者仍负责 journal root 与 controller 来源链。

原数值阈值、完整 UID lex 顺序和物理 witness 不变；不把 normal 的验收修复扩展到 selector。
解析目标证明与数值物理可行性的区别继续由封存 core 的独立证据类型表达。
normal plan、初态和当前条件的机制角色保留在绑定请求内，不转换为真实观测。

## 验收矩阵

1. reference/actual 零偏差真实小例，经真实 Job worker、SQLite、receipt、父控制器后返回；
   分别2/1 native calls，仍按3/2完整stage预留；随后单独零solver归档回放通过。
2. reference 非零偏差继续3次完整native路径，外层归档与回放通过。
3. store单次执行、异常/KeyboardInterrupt、lost result acknowledgement、禁止重试及未知调用保留。
4. 新旧namespace隔离；外部record SHA/journal binding/request/implementation/size任一不符均拒绝。
5. worker词汇、重复/额外字段、NaN、错误类型及实现pin反例；错误实现不得创建store。
6. intent/launch持久写失败不得release；receipt与归档不符不得发布controller result。
7. 模拟终态资源失败时保留observation，不发布成功结果；它是故障注入，不冒充实测OOM事件。
8. unresolved archive不能被升格；受影响新测试与旧store/worker/controller相关回归通过；
   原两个sealed包hash均保持。
9. 多种矛盾success observation、mixed/analytic/legacy依赖漂移、反向old application_id和
   自洽重hash后的旧result类型均拒绝，namespace隔离为双向。

测试数量、实际运行命令、pre-seal findings、封存与official verdict另记于closure和blocker register。
本规格不是正式实验准入；新路径仍需versioned episode消费及后续全支持运行成本核算。
