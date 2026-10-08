# H1 单小时固定来源对应

2026-09-30，DRAFT_NONAUTHORITATIVE。实现 `normal_h1_source_binding.py`，沿用已批准 v2 的 250 MW、12 位 half-even workload 映射。

`H1SourceDeclaration` 显式声明 training/holdout、两侧独立 raw hour、power outage seed 与来源配置 SHA256。
`load_pinned_current` 从固定 RTS manifest 及已有 `source_window` 审计路径重建单小时观测，
返回静态网络、选中的 RTS base row、原始 workload 字符串和不可变 audit bytes。
读取函数不求解，不推断 pair 概率、登记选择或实际历史初态。

读取前后核对 RTS manifest/成员、power/workload package 成员及配置 pin。
power package 的 grid manifest 必须与 RTS 相同；window 和行的 split、index、seed 与声明对应。
power raw index 对应 `hourly_points[index]`，continuous index 对应 `index+1`。
RTS naive timestamp 明确按 UTC 标注后与 power timestamp 比较；workload 保留独立索引，不解释为共同观测时钟。
系统总负载比较沿用旧来源对应的 `1e-6 MW` 限，只检验对应性，不改变原始 base row。

全年 RTS loader 和边际 package 审计会读取完整文件。算法接口只暴露选中的当前行；
完整全年数据和 source window 不保留在返回对象中。
source/config/package/window/chain 身份、真实时间与选择坐标全部进入审计身份，
不传入 normal 数值模型或共同计算键。CFE、outage overlay 字段也不进入 normal 模型。

`validate_pinned_current` 要求调用方提供独立保留的 expected identity 和来源路径，
先检查 receipt 自洽，再从 pinned 文件重建并比对；修改字段后自行重算 hash 不能替代来源对应。
`assemble_pinned_current` 只使用重建对象组装现有 H1 packet，调用方另提供 relative hour、DC bus 和前驱。
返回 packet 的计算键仍使用现有 `normal_h1_source.causal_key`；lineage 保存在独立 receipt。
raw workload 大于 1 可以通过来源读取原样保留，但 H1 组装仍由既有 mapper 拒绝，不裁剪或重新归一化。

`load_pinned_current` 生成的是 candidate receipt。只有由调用前独立保留的 expected identity 驱动的
validate/assemble 才证明与该 pin 的重建一致；测试中即算即用的 identity 只验证机制。
两份可变 window 输出均检查 exact schema、完整自洽 hash、实现 hash、负权限和坐标的精确类型；
布尔值不能作为小时整数，row 索引与 seed 必须保留 canonical CSV 字符串。

`source_files_verified/source_correspondence_verified=true` 仅描述固定文件内容对应。
`source_authenticated/selection_registered/shared_observed_clock/observed_power_mapping/formal_result/native_execution_authenticated=false`。
无源文件 writer lock，不声称抵抗 hostile ABA 或认证内存执行历史。
该组件尚未把 receipt 原子绑定进 episode intent，也不登记 E/F 来源选择或三链共同发布。
后续 controller 必须保存并核对这些关系，才能建立正式可消费的来源链。
