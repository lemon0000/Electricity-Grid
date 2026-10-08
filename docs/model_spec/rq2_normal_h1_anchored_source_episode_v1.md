# H1 来源绑定父控制器与 anchored collectors

状态：DRAFT_NONAUTHORITATIVE，R3 PRE_SEAL_AUDIT findings 已闭合；无 production seal 或 official verdict。

`normal_h1_anchored_source_episode.py` 在独立父 namespace 中管理固定编号的小时 collector/anchor 目录。每小时先持久化并锚定父 intent，再创建唯一子目录；创建失败、pending 或重开均不授予重试权。不同独立父 namespace 的同一请求尚无全局去重，需后续正式调度层约束。

来源沿用 `normal_h1_source_episode` 的严格加载器：固定 origin 同步推进两个 raw hour，重新加载当前 source，检查 exact observation 类型、identity、静态 network、audit 字节上限；保留原始 workload。来源链 identity 必须连续，实际 power timestamp 恰好前进一小时，time basis 不变。来源审计存入父 chunk payload，不能把整小时 raw 报告重新装回一个父 BLOB。

父 intent 绑定来源 audit、observation、私有 before identity、当前 packet audit identity、新 streaming replay request key、旧 native chain identity、确定的子目录与实现，以及完整小时调用预算。真实输入不足、工作负载超限或来源改变均拒绝推进。全 episode 预算在创建文件前按旧短预算上限预留；每份 pending/rejected intent 都保留完整预算占用。

父 outcome 只引用完整子结果及其独立末锚点 SHA。执行子 owner 关闭后，必须先凭该 SHA 新建仅审计的 child owner，完整重验并逐字段对照执行结果；随后重载父来源与既有 prefix，才提交 outcome。提交后父 restore 再次重新加载来源并重开 child，完整复核 raw 与 projection；只有 exact replay projection 的 request key、before identity、完整阶段数和边界检查通过，才私有重建下一小时 before 并递增 completed_hours。调用者不能提供 before 或 projection 来推进父状态。child 完成但父 outcome 缺失仍为 pending_unknown，预算不退回，不自动补写。

父 journal 同样使用独立的本地受信 anchor root；每个父事件必须锚定成功后才允许后续效果。重开父对象仅能审计，不能继续执行。整个根目录回滚防护、跨父 namespace 去重和可执行恢复均不在该本地机制的声明范围内。

父 restore 采用受信本地目录和合作进程遵守排他 lease 的运行边界；不声明可在绕过 lease 的外部 SQL 并发写入下提供统一 snapshot。该声明不扩张子增量归档已有的独立外部提交检测能力。

该模块只管理 normal 链，不发布 Rref/A/共享业务电网共同前缀。所有 source/native authenticity、published、formal_result 和 formal_execution_ready 标志保持 false。真实 RTS 232 阶段仍超出旧短求解门；单小时 replay size limit 不是执行许可。完整资源准入和正式实验仍待完成。

最终 9 项父控制器测试通过（178.42s），来源绑定与 anchored collector 相关 44 项通过（95.72s）。独立审查确认 fresh child reopen 已移至父 outcome 提交之前，相关损坏/漂移测试保证失败时父日志仅有 intent。

两小时合成来源的 native 开发验证使用总 6 calls × 1s 旧预算，完成 2 小时、6 份持久 accepted raw 报告；最终 `G1` 出力 20、连续运行年龄 2，独立末父锚点 SHA 重开一致。约 116.14s 为含来源加载、构模、I/O 与重放的总耗时，不是 solver 时间或硬 wall 准入。完整父 prefix 在当前短实现中反复重放，不能据此外推真实多日资源。样例与报告清单在 `results/tables/rq2_normal_h1_anchored_source_episode_v1_non_authoritative/`，明确为 synthetic fixture，非真实 RTS 数据实验。
