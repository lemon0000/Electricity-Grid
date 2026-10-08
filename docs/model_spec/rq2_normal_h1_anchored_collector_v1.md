# H1 本地持久根锚点与采集器集成

状态：DRAFT_NONAUTHORITATIVE；独立 R3 PRE_SEAL_AUDIT findings 已闭合，无 production seal 或 official verdict。

`normal_h1_attempt_anchor.py` 使用独立、明确声明的本地 NTFS 目录作为一次性调用的根锚点。复用排他 lease 与既有 `xb`、完整写入、flush/fsync、fresh readback 文件原语；每条记录新建固定编号文件，不覆盖旧记录。header 绑定目录、collector declaration、记录上限及实现；记录绑定前一记录 SHA、前一 registry head、新 head 与事件 SHA。活跃 owner 保留文件 identity、SHA 和记录数，后续操作检测替换、改动、增删与序号缺口。exact typed receipt 只有与 fresh 读回状态一致才被确认。

该本地目录是显式信任根。仅凭本地 hash chain 不能证明进程退出后整个目录没有被回滚为完整旧副本；本版本不作此声明。可额外传入独立的最终记录 SHA。重开的锚点禁止追加，重开的 collector 禁止调用 solver，因此读回状态不授予恢复执行权。跨 root 去重、来源认证和生产级外部单调根仍属于父控制器集成范围。

`normal_h1_anchored_collector.py` 使用独立 declaration/implementation identity 继承旧 collector 的 checkpoint 状态机，保留旧模块字节。先持久锚定 registry genesis；每个 intent、stage checkpoint、terminal checkpoint、outcome append 返回后，再持久锚定新的 registry head 并 fresh confirm。只有该过程成功，才允许首次 native call、child write、下一 stage 或 outcome 交付。运行中每次高层检查重新确认锚点等于 registry head。

重开时，registry head 来自独立 anchor 记录，child head 来自已锚定 registry checkpoint 的 previous/expected 候选；不自取 child tail。child 提交未知时两种状态都只用于审计，pending_unknown 不交付 projection，也不能重试。registry 已提交而 anchor 未完成时，旧 anchor 不能接纳额外 registry tail；重开校验失败并保留文件，等待独立诊断。

所有旧短求解预算、数值谓词和严格 assignment 审计保持不变。锚点的落盘确认不代表 source/native authenticity、hard process resource admission、正式结果或服务认证。19 项联合回归通过（117.40s）；其后同源代码新增真实进程退出的两个零 solver 测试通过（18.82s），以及五项锚点故障/错误 pin 测试通过（18.88s）。独立审查复核新增故障证据后关闭 findings，未重复运行这些测试。

额外三阶段 native 开发小例按原 3 calls × 1s 求解预算执行，3 份 raw 均经存档与数值重放接受，canonical locks 为 `(20, 1, 20)`，7 条锚点记录落盘。运行至结果返回约 16.30s（包含构模、I/O 与重放，不是求解预算或硬 wall 限）；关闭后凭独立末锚点 SHA 重开结果一致。结果位于 `results/tables/rq2_normal_h1_anchored_collector_v1_non_authoritative/`。该例仅验证本地短链集成；source-normal parent 发布、跨 root 去重和真实 RTS 资源准入仍待完成。
