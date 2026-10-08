# H1 child 存储成功／首次失败分类界（开发）

本界仅用于已审 `h1_attested_source_parent_development_v1.SavedSourceParent`
执行其固定 attested child 协议所产生的文件，不改变已有存储上界、raw cap、guard、
科学合同或运行许可。它是后继 Job 资源声明的一个输入，未完成资源准入。

每个成功推进的 stage 必须先通过固定 `guard.saved_report`：原 raw 为 canonical
JSON，满足 v2 grammar，故 raw 长度至多 B=929218 bytes。raw 在 guard 前写盘，
首次失败的 stage 可能留下至多 R=16MiB 的完整或部分 raw。超过 R 的返回值在
写 raw 前拒绝；尚未返回的 producer 输出和内存占用不属于文件内容界。

attested hour 的任何异常 poison，wrapper 和 parent 传播异常并停止；parent 重开
仅允许检查，不能重试或推进。因此在同一执行路径的全部 H 个小时中，最多一份
已保存 raw 没有成功经过 guard；这不是“每小时允许一次失败”。此前成功 raw 均
不超过 B。完成全部阶段后出现 terminal/source/anchor 失败时，没有额外 raw。
这些结论假设执行固定代码且没有外部写入，不覆盖调用者直接篡改内部对象或文件。
固定 parent 路径不直接调用 `Ingress.abort()`，不允许任意 callback 或直接访问
owner 额外写入；不能把该界推广到这些开放接口的任意组合。

设每小时 S stages，1≤H≤192、1≤S≤232。已审 child 上界保守保留所有小时的
non-raw 文件，即使失败路径实际未创建其后文件。每 child 分解为：

- S 个 raw；
- S 个 mapping 与 1 个 projection，各 262144 bytes；
- 12S+14 个 metadata 文件，各 2048 bytes。

令 C=(12S+14)×2048+(S+1)×262144，则完整成功逻辑界为 H×C+H×S×B；
包括首次失败停止的保留内容界为 H×C+(H×S−1)×B+R。最大值在最后一份 raw
失败时取得；对更早停止的路径仍保守。文件／目录数继续使用原 child 上界。
实现核对这一分解与原存储函数相等；旧实现拓扑变化时拒绝计算。

可显式给定 1..65536 的二次幂 allocation quantum，逐文件 cap 向上取整，给出
条件性的 file-content allocation 界。该数字不是已观测磁盘分配或整个文件系统
上界：不含目录项、MFT、日志、稀疏／压缩策略、数据库、parent journal/anchor、
Job 请求/输出/scratch、保存 raw 的上游副本及其他写入。filesystem allocation、
完整任务资源与所有运行门禁保持 false。也未证明累计 O(H²) replay 的时间预算。

测试独立枚举各个首次失败位置，覆盖边界 H/S；真实 fixed child 测试保存超过 B
及达到 R 的无效 raw 后拒绝，后续调用不得创建文件；完整 synthetic 三stage
检查逐文件类别与 cap。这些测试不创建 native capture，不替代 RTS producer覆盖。
