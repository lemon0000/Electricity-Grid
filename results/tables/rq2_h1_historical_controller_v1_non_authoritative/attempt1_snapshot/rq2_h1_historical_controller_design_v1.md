# H1 historical obligation/controller 接线草稿

2026-10-09，DRAFT_NONAUTHORITATIVE，R3。根代理唯一写入。
本文记录 `/root/outage_origin_design_review` 的只读设计核查；不是实现完成、official verdict 或运行授权。

## 必须保留的链

旧 `rq2_v2_normal_obligation_controller_development_v1.inspect` 要求 obligation 目录恰好停在指定小时。
新 successor 应支持使用旧 header/terminal pins 重验此前已经 accepted 的前缀。
旧 controller 源码不能修改：既有 binding header 绑定其 implementation identity。

新模块绑定旧 controller、historical parent 与所复用 bridge/binding 的实现 identity。
只新增编排，科学义务继续使用旧 `_historical_binding`；每小时 Job/clock 使用旧 `bridge.inspect`。
`additional_content_bound(h)` 继续限制 1..168，不能借历史读取器扩展 N 的生产 horizon。
header 的全部 schema、budget、manifest、parent declaration、clock binding 和 flags 检查照旧保留，
并重新执行 resolver precheck 与完整 enrollment prevalidation。

terminal 从外部旧目标 pin 向前回链，依次验证每小时 terminal→job link→obligation binding，
最终 previous pin 必须等于外部 header pin。不能借当前最新 terminal 推断旧目标。
每小时仍检查 request budget、完整 `_historical_binding`、clock terminal 中 job_pins、
outcome_head、outcome_anchor_sha256 的对应，再调用 `bridge.inspect` 和 timed child replay。

## Timed parent 与 current adapter

普通 HistoricalSnapshot 不足以读取 timed controller declaration。
应仿照 `h1_timed_job_snapshot_development_v1.Snapshot` 的多继承顺序，明确接入 timed
`SourceParent` 的 `_declare/_child`；验收必须证明 declaration 与 Job-backed child 类型正确。

新层私有 `_replay_prefix(..., capture_last)` 统一完成上述全部检查，在 `_after` 验证
accepted ChildInspection、完整 stage 数与 projection identity，并捕获最后一小时 packet/result/after。
current adapter 复用旧 `_decision`，返回前再次用相同 pins 重验 prefix evidence identity、
稳定文件视图与实现 identity。不能只读取序列化 boundary，也不能把可手工构造的对象当作凭据。

## Namespace 与信息边界

obligation prefix 必须每小时含 binding/job/terminal 三件套。
后续名字仅允许 ASCII 三位小时 000..167 与这三类文件，按 binding→job→terminal 的生命周期出现，
编号连续；不完整后续小时之后不能再出现更晚小时。
所有这些普通文件必须 single-link、不同名字不能共享 inode。
后续只检查有界名字、类型与身份，不读取内容；允许合法追加，但已观察项不能删除或替换。
binding header 与一字节 execution.lock 保留固定 identity。
controller root 与 clock root 也需要独立有界 inventory；prefix 内部由现有 helper 继续完整检查。
clock 的小时 h intent 对 h−1 terminal 的关联通过逐小时前缀检查全部覆盖。

## 验收与剩余边界

- 同一没有后续小时的 root，用相同 pins 分别调用旧、新 inspector，比较每小时证据 identity。
- 两小时 accepted root 上用第一小时旧 pins 重建 hour 0 current。
- prefix obligation、Job、clock、parent、child 任一证据破坏必须拒绝。
- 合法后续名字下的未消费内容损坏不能进入旧 prefix 的科学投影；其有效性不获认证。
- 覆盖 inode 替换、hardlink、编号空洞与检查过程中的追加。
- 完整 controller 集成可用现有有界 synthetic worker/Windows Job fixture；必须保留 no_solver guards，
  如实记录测试 Job 数。该测试不证明真实 RTS/native 执行或资源准入。

suffix_chain_verified、current_latest_parent_verified、current_latest_obligation_verified、
live_release_authenticated、live_handoff_authenticated、writer_lock_authenticated、
persistent_lane_owner_implemented、detached_consumer_authenticated、common_prefix_publication_verified、
reference_or_actual_ready、resource_admission、formal_execution_ready、formal_result、native_execution_authorized
均保持 false。已存 Job 记录的历史回放不能重新认证 live Job membership。

本文尚未生成 controller/current adapter 实现与测试；后续仍需独立 PRE_SEAL 审查。
