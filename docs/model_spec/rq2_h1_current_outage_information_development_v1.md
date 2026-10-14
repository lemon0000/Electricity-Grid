# H1 current outage / accepted N correspondence

R3 DRAFT_NONAUTHORITATIVE。实现位于 experiments；旧src及封存字节保持。

公开 `prepare(root, external header/terminal/window pins, completed_hours, protocol,
repair_limits)` 必须内部fresh调用已存在的accepted N reader。来源split/seed/raw start/config
仅从该reader的parent declaration取得，outage hours严格等于N completed_hours，调用方不能
另传raw coordinates、任意Prefix或未来horizon。当前reader只支持1..168，不能声称192小时覆盖。

同一次调用重建outage prefix与fresh current pinned observation；逐字比较当前raw power row和
package identity，再用observation及accepted normal-before重建原N packet，核验input identity、
normal-after、decision bytes和source clock。protocol必须逐项等于冻结generator/config/upstream
推导的完整211个eligible components（93 generators、118 branches），拒绝漏项及B11/C11等
source-ineligible项；返回前重建inventory。还检查其存在于N static network、generator enabled；
已揭示repair caps均继续检查nameplate。无cap则按旧outage适用性门拒绝。

返回前重新读取accepted N、current observation、outage prefix及implementation identity。
对外decision仅含当前normal view及当前一个DisclosureStep；不暴露prefix steps、raw rows、
未来事件结局或source ID/clock。DisclosureStep中的before/after为已揭示状态摘要。
audit仅保留来源及前缀hash/外部pin，不提供全段policy输入。

本单元是fresh-at-return correspondence检查，尚不是持久lane owner。返回对象不可普通
copy/replace/pickle，但exact type仍不是认证凭据；下游owner须在owned调用中重建并消费。
相同N进度仍可能对不同外部repair cap输入产生不同decision；same-key registry和cap持久来源
必须另行实现。repair_cap_source_registered、persistent_lane_owner_implemented、
detached_consumer_authenticated、common_publication_verified及全部formal/resource/native门保持false。

测试明确使用synthetic source/catalog与N reader seam，实际执行source assembler、outage
prepare、当前投影比较和多次fresh校验；零solver/Job。覆盖当前/未来区分、进度/坐标/row/input
不一致、缺初态、来源漂移、nameplate与外部pin。它不建立真实RTS accepted N/root集成见证，
不证明科学调度可达；完整root-to-lane接线仍需后续验收。

6个缺边界窗口继续input unresolved。chronology-origin初态、holdout生成边界receipt和
repair cap规则均须单独提出科学决定，不能由本接线默认为已批准。
