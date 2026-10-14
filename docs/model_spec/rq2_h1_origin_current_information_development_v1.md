# H1 accepted-N / approved-registry current join

DRAFT_NONAUTHORITATIVE。`h1_origin_current_information_development_v1.prepare`将既有accepted N
reader、已批准origin/cap registry和first-aware physical frame接入同一次fresh调用；不修改旧模块。

公开输入只有root、外部binding/terminal pins、completed_hours和expected_registry_identity。
拒绝caller提供raw坐标、mode、protocol、repair cap或detached Prefix。completed_hours仍为1..168，
对应现有enrollment reader；不会将F≤24误当作新enrollment。

从fresh N audit的parent declaration唯一派生split、seed、source origin与当前坐标。registry
只准备已完成N长度的prefix。join逐字段比较末条power raw row和固定package；以N normal_before
重建当前packet、再用normal_after重建公开N view，核对input identity、clock/time basis和decision
bytes。新physical frame复核完整normal边界、inventory和generation；source protocol的全部
component必须在enabled network，所有已观察repair cap须不超过对应source nameplate。

raw0只接受registry FirstAction；其后chronology transition source clock为t-1→t。
ordinary/generated action t的source clock为t→t+1。mode由origin决定，不由caller设置。
完整prefix只在prepare内部使用，返回仅保留source origin、当前action、当前frame和审计摘要。

`PreparedCurrent.decision`是policy view，仅含当前N信息和规范化当前outage projection；无event ID、
seed、真实clock、origin kind、raw rows或未来prefix。frame/source_action/source_origin属于owned
consumer的因果核验参数，不属于policy view；origin kind与完整prefix audit仅以审计摘要绑定。
对象禁止直接构造、copy、deepcopy和pickle，但exact type不是认证凭据。

返回前再次调用N reader和registry prepare、验证pinned current observation，并核实现身份。
`current_source_correspondence_checked`和`registry_action_and_cap_lookup_checked`表示该调用内
执行的开发检查。测试中的accepted N和registry source loader是明确的synthetic seam，真实
accepted-root到registry的完整集成尚未作为科研执行见证，accepted_root_integration_verified=false。

本入口不提交lane、不认证后续持有者，也不接受caller-built carry用于续接。后继持久owner必须
在同一owned transaction内fresh准备并消费这些对象，绑定原始N和registry外部pins、前序科学/
审计heads及source action，返回前重验。prepared对象离开本次调用后不能直接充当fresh凭据。
persistent_lane_owner、detached_consumer_authenticated、common_publication、192小时执行、资源、
formal/native门均false；三链隔离与paired commit仍需独立实现和审查。
