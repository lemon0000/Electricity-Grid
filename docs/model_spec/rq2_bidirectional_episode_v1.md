# 双向容量策略的持久 episode 接入

2026-09-29，`DRAFT_NONAUTHORITATIVE`。本组件消费独立bidirectional小时事务及策略类型，
连接既有混合selector的监督、归档和零solver回放。根代理唯一writer，按R3验证和审查。

## 接入范围

新增 `scale_episode_bidirectional`、`scale_episode_bidirectional_replay`、
`scale_episode_bidirectional_transport`、`scale_episode_bidirectional_worker`、
`scale_episode_bidirectional_controller` 五模块。
业务origin必须为exact `BidirectionalPolicyCursor`，在写episode root前检查。
输入、episode budget、arm setup、hour input、publication/cursor、worker/parent receipt
使用独立type或schema及传递implementation identity；旧mixed接口保持原字节。
共享网侧selector store/worker/controller及Job/lease机制继续使用既有审查产物。

按小时同一reference发布，四臂独立执行其冻结D与固定策略。每小时预留完整四臂最坏调用量，
业务拒绝/网侧unresolved的臂保持成对前状态；后续标注halted，其他臂继续。
结果文件是观察证据，不是可恢复checkpoint；失败不重跑、不resume。
离线audit从输入和归档重建新事务，禁止solver/子任务执行。
外层execute/audit两Job正常结束且全Job静默后，父控制器核验完整回执和归档，再发布结果。

## 验收矩阵

1. 四臂及两小时状态链，B6实际共享容量，保留债务、policy identity和成对提交。
2. 旧policy/cursor、旧transport schema、混淆class tag与已执行successor输入均拒绝。
3. bidirectional policy源文件及传递依赖变更使transport/worker/episode身份失效。
4. 业务拒绝、网侧未决、task中断、write/close失败、错误receipt及来源pin均fail closed。
5. 真实短合成execute→独立audit→parent，回放0solver；归档hash与ordered pins一致。
6. 完整最坏资源预留、两phase成本、host空间与Job监督继承验收，不放宽限额。
7. 已封存bidirectional容量包及此前518成员保持；不修改旧结果，不启动formal实验。

本开发不注册E/F、deadline、预算或评分/停止规则；当前仍消费显式固定小时window。
有限登记按需follow-up控制、normal来源绑定的新类型接入、training证书到holdout绑定、
全支持可行计算与自包含正式协议属于后续门槛。观察窗口结束不自动证明完整服务成功。
