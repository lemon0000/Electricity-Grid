# Root transcription of independent readonly design findings

Reviewer: `/root/outage_preseal_review`。2026-10-08。仅设计取证，非 official verdict；没有测试、写入或 native/Job。

后继验收设计：`docs/model_spec/rq2_h1_persistent_owner_design_v1.md`，尚未实现 persistent owner。
内部 business hour=t+1、genesis anchor=0，只是 relative business clock compatibility view；真实 raw0
仍没有前驱行。所有 birth/due/last_hour 同步平移，真实来源映射独立审计。需要通过连续状态和 deadline
平移不变量测试，不可仅凭字段类型宣称等价。科学 projection 保留完整业务状态、cohort、envelope、policy
与前驱，排除 raw labels、seed、provenance、旧 trajectory identity；旧 replay cursor 全量保留作审计与重放。

exact wrapper 可在现有开发授权内实施，但必须保持已批准 v2 数学。ContinuationHour/HourlyLimits 的 Real
通道可显式登记 Fraction 并检验旧主体保持 exact；BidirectionalObservation.available_flexibility 的 strict
built-in 通道只能用整数或满足 Fraction(str(float(q)))==q 的无损 decimal 投影。不能把 1/21 静默转 float。
当前 v2 limits：available=f*w，business headroom=beta*max(1-w,0)，CFE surplus取当前allocation，
call_limit=1，max recovery=1。旧主体保留 q+r<=D、原 recovery12位量化和EDF。

阈值探针不是实际合法输入失败证据。适配必须证明 CFE effective 和 Rref normalized 请求均为0或严格大于
exact 1e-6，component/combined分类一致；再验证调用与 recovery 输出阈值。发现差异且无法证明排除的
输入保持 unresolved；任何新增 rounding/epsilon/clipping/活动分类改变需另行科学决定。

独立意见中 Rref request 写成 P_ref 的变量名可能混淆：现有 selector 的 `candidate_grid_request_exact`
实际为 B-P_ref，operational mapping 应消费该 grid request，再除 normalized_unit_mw；不能把剩余供电
P_ref 当作请求。根已直接检查 selector 的 `_reference_assignment` 确认此含义。

冻结合同 `rq2_finite_mechanism_protocol_candidate_v2.md` 的“登记评分与按需后续”节优先于早先交接
中任何“follow-up 不产生新birth”措辞。E=168后的新请求仍执行，其 birth/债务保留，只不扩张登记评分集。
按需继续至全部登记cohort结局可判定或最后due；末债不必为零；已知deadline miss保留，晚恢复不改写成功。
设计文件已纠正该点。未修改冻结合同、旧实现或门限。
