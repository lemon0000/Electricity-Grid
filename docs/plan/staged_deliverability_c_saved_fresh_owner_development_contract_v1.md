# C：saved owner/watcher 独立开发合同

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[冻结绑定77交接](continuation_handoff_20261025_saved_fresh_binding_completion.md)，起始HEAD `8528cbe1c7982c83fc7403c54c5990a148c73822`。root唯一writer，独立只读PRE_SEAL；可迭代原ENTRY/tests，保留旧snapshot、失败及冻结记录，科学adapter/旧guard/原scope-budget不改，SF49集合不扩大。

本轮实现独立saved constructor/watcher及读取许可接口；不发行运行许可，不执行真实saved Native owner、P1科学重放、fresh或formal run。public saved CLI、supervise和所有scientific/resource/formal gates保持关闭。冻结77仅归原source epoch，后续新源码不继承“当前77通过”。

## 构造和能力

- SavedOwnerInputs仍是数据，分出immutable entry、prelaunch unbound check和post-bind检查。constructor attempt在任何factory分配前一次claim，绑定原RoleStore/reservation/context/tree/channel、creator和开始时刻；失败不退款。
- public saved constructor只收exact inputs和one-shot SavedChildLaunchPermit，不收factory/argv/cwd/env/descriptor override。permit默认无issuer，发行端本轮不实现；无/伪造/foreign permit在任何Native factory/对象分配/生产preflight前拒绝。未来issuer只能来自已授权、已ACK的actual saved role execution capability。
- 私有测试入口只接受固定枚举fault script，由ENTRY内固定stub执行，结果恒`real_owner=false`；不接收factory或任意callback。使用同一saved构造/监督实现与SCHEMA/production descriptor，不能获得内容读取/科学采用权限。不调用真实OwnedChild constructor；真实RAM通道和当前进程身份仅用于传输单位检查，均不证明真实child。固定类、方法及code身份在构造和post-bind入口复核。
- 先分配owner对象再__init__，捕获实际构造输入/header/startup并在仍suspended时重核source/EXE/env、原start及active deadline。partial owner/channel/inputs/permit、原primary和cleanup异常对象必须强持；失败一次kill→有界quiesce→owner/channel close，任何未决不能转成功。

## 监督和终态

- ordinary wrapper继续拒绝production/saved，不扩大旧record reader接受域。共享核心只根据不可变held domain/binding选择exact descriptor和record scope；无外部字符串/descriptor选择mode。
- saved监督从原reservation.start计时，deadline不超过context绝对帽，fresh保持40+5+5。release前复核；active loop仅kernel/fixed RAM，禁止context/source/目录/工件I/O。原完整历史成员/witness、post-quiesce commit、quiet/close、record帽及错误优先保持。
- saved fresh relay必须是held bootstrap中同一upstream writer对象、固定fresh→parent，不能仅凭同context接受替代对象。inner_quiesce失败仍清理；只有完整quiet/bookend/close后才可inner_terminal。saved标签不沿用ordinary conhost cache例外。
- saved startup/record/reader独立严格schema；unit logic成功不产生physical success/job quiet或采用。只有真实retained owner及完整原witness/close、原始record和末次书挡全部成立才允许未来内容读取；JSON或unit对象不能替代。

## 验证与预算

独立开发预算300s：pytest累计≤240s、collection/静态/保存核验≤60s，逐组预登记node/cap并核剩余预算，单组≤45s、必要affected≤30s。先静态PRE_SEAL闭合再扩回归，所有attempt保留源码snapshot和raw stdout/stderr，无actor自动重试。

覆盖data-only/closed/foreign/replay/creator permit、claim一次、pre/post bind漂移、constructor各partial点和复合cleanup、过active/context deadline、ordinary↔saved mode、精确relay及两phase故障、poll/sample/frame/nonzero/resource/witness/close、record字节帽及quiet前禁读。时间边界允许明确fake clock单位注入；不声称真实40/50/180s硬中断、资源准入或Native saved成功。相关普通stage/guard和角色回归按实际修改域运行。

输出在独立`results/tables/staged_rts24_saved_fresh_owner_v1_non_authoritative/checks_01`。原P1全683、旧研究字节及三导航旧正文保护；17 targets/四份128KiB、8MiB/64、一次parent/fresh、零solver/重试及180s不改。实际issuer/supervise/角色执行、完整调用与最大合法编码、昂贵失败/最终发布、external硬中断/全链资源及整包科学采用继续OPEN。不会生成production lease/manifest、official verdict/receipt/seal或run authority。
