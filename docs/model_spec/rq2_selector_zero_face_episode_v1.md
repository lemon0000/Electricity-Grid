# 混合 selector 连续小时接入 v1

本候选接续已通过独立审查的混合 selector 外层执行组件。开发期间为DRAFT_NONAUTHORITATIVE；封存状态以对应outer原子发布为准，独立审查结论另存receipt。本规格不授予正式运行权限。

## 接入范围

`scale_hourly_zero_face_transaction` 使用 `MixedSelectorRequest` 和已封存的 source-bound archive replay。reference publication 保留外部 journal binding；reference 与 actual 的每次回放均要求调用者独立提供 record SHA、journal binding 和实现 pin。完整回放接受后，才允许发布 reference 请求或成对提交业务与网侧状态。

`scale_episode_zero_face` 复用既有完整资源声明、lease、每小时 durable intent 和子任务监督。在新 namespace 中消费混合 selector，收集 receipt、SQLite 和控制器记录后，显式向事务传递 `store_binding_identity`。事前调用预算仍按完整 UID 阶段数预留，解析后缀不会减少已经声明的预算。reference 持续推进，已停止的臂保持原状态；未完成小时不发布成对后继，禁止重试或恢复执行。

`scale_episode_zero_face_replay` 从外部保留的 header/intent/result pins 和独立初始输入重建已提交前缀。它使用新 exact result 类型，核对外层来源链并重新回放每个选中阶段；未决记录只能作为未决记录消费。成功 observation 复用封存控制器的严格检查，不能用自洽重写后的资源失败记录冒充正常退出。历史 OS 执行真实性仍不由离线回放认证。

现有业务模型、四臂定义、shared/B6记账、恢复债务、部分响应和拒绝后动作语义沿用旧实现；normal 数值修复不扩展到 selector 阈值。输入中的机制初态及业务功率映射保留机制标签，合成测试不代表实测运行。

`scale_episode_zero_face_transport/worker/controller` 将同一episode接入固定词汇输入、独立execute/audit worker与外部监督。transport仅允许新初始request/episode类型，保持有界canonical编码；worker的audit模式禁用执行入口和native solver；controller继续在release前保存intent/launch，保存退出observation，并以execute保留的外部pins审核audit输出。顶层和子任务均保持one-shot及各自资源声明，source及环境身份贯穿两个worker；环境值不进入归档。

## 必须验证的接入不变量

- 四臂使用同一 reference 请求、固定策略和完整源小时；角色错配及重复 publication 被拒绝。
- 解析与 native 路径均能消费；解析回放无求解调用，业务/网侧状态仅成对提交。
- 跨小时债务连续；恢复受既有 headroom/CFE surplus 限制；网侧未决保留两侧原状态和候选诊断。
- 外部 binding/hash/实现 pin、旧 request/result 类型和依赖漂移不能绕过验收。
- episode 中断、后期子任务失败及已消费归档漂移不得发布小时后继或重试；仍收费完整预留。
- 离线回放拒绝角色交换、重新计算 hash 的状态/预算/来源篡改、额外目录和矛盾 observation。
- 既有 normal、core、外层执行三个封存包逐成员 hash 保持。

本候选必须完成 targeted/regression、pre-seal audit 后才能封存并接受 fresh official review；执行命令、准确计数、交付inventory与审查状态记录在closure及blocker register。真实158 UID成本与全支持计算、完整科学合同、容量及training/holdout证书仍为后续工作；不得把短时合成 episode 称为完整服务认证。
