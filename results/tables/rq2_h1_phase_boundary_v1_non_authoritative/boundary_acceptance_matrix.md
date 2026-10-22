# 原168h / ≤24h合同的边界验收矩阵

2026-10-20，DRAFT_NONAUTHORITATIVE。原phase与business实现、YAML E/F/due/预算和数值限均保持。unit_04已终态exit0，[JUnit](unit_04/junit.xml)为15 passed/0fail/0error/0skip，pytest84.34s、外层87.656s，9份逐case事实按SHA留存于[终态记录](unit_04/terminal.json)。下表在注明的单元作用域通过；完整连接缺口继续OPEN。

| 案例 | 原合同预期 | 本轮验证层次 |
|---|---|---|
| completed business=167、零债务 | 仍需relative_hour167；next phase=enrollment | 完整167小时业务历史、原phase assessment/attempt body |
| 业务第168小时结束且primary全判定 | lane completed；无需relative_hour168，可生成terminal body | 完整168小时carry、completed disposition、原terminal body |
| 第168小时birth仍pending | due=192；进入followup，读取relative_hour168之前应先登记attempt | 原business carry/assessment/attempt body；真实source/Job顺序不由此证明 |
| followup第169小时再birth | due193及债务保留，primary last_due仍192 | 原完整169小时carry，followup不递归扩展评分集 |
| primary在170恢复完成、followup debt仍正 | completed，primary S；保留followup debt17/200 | 原170小时carry及terminal body |
| 旧primary已miss due、随后恢复 | deadline F不擦除；另一个primary pending时继续 | 原170小时carry及attempt body |
| completed business=191、primary pending | 必须消费relative_hour191再判断；不提前终止 | 原191小时carry及attempt body |
| 业务hour192仍未恢复primary | primary F，停止；followup due193 debt保留；末债17/100 | 原192小时carry、completed disposition及terminal body |
| 恰在业务hour192足额恢复 | 先恢复0.1，有效清偿0.085，再记录snapshot=0；primary success_by_due，无第193业务小时 | 从genesis真实推进192小时、原账本/phase；记录原_validate调用与history长度 |
| halted_unresolved lane仍有primary U | 不再推进其两carry；global无active need时允许技术terminal，U保留 | 原业务carry与halted disposition/terminal body；不等于完整合同成功 |
| 缺必要followup | 业务assessment继续need，不能伪造source可用或terminal成功 | 本轮只核原assessment；真实followup source故障/右删失终结仍OPEN |
| 全链事件/历史重放成本 | 原32-event fixture拒绝第11小时；168/192至少504/576events | 原_fits门、独立事件枚举、三小时保存计数及静态整链recurrence |

本轮业务fixture保留自己的显式toy机制，不将其当完整目标科研cell或RTS输入。业务历史从genesis逐小时计算，没有缩短E/F或跳接carry。phase-body测试的heads/binding是显式元数据stand-in，不生成owner、journal、ticket或source credential；completed/active/halted flags对应原transition的分支类型，但没有验证真实paired outcome使该flag变化。

第192小时精确恢复用例保存194次原_validate调用及18720个传入history长度单位；这一实测只描述单条业务构造与assessment/body路径，不是整条owner重放。halted和缺必要followup两项由JUnit中的独立断言核验，没有额外事实JSON；后者没有实际读取缺失source。metadata_probe_01仅用于定位测试元数据构造问题，不作为独立验收证据。

资源终态：sampled树RSS180867072B、logical309574B，低于固定1GiB/128MiB和180s；1305 source pins未变、仅观察到pytest及其直接System32 conhost，两PID均退出。旧unit_01/02/03失败、collection probe及其tested_bytes原件保留，没有转记为成功。新测试文件与预算分析脚本独立新增；原代码、fixture和保存case不修改。

仍需连接验证的项目：连续168h N/Rref/Actual+paired前缀、真实167→168 outcome→completed/followup、长时域source freshness/外部独立heads、真实terminal event写入→关闭重开完整重放、缺必要followup的typed unresolved/right-censor表示，以及整包资源预算。旧三小时missing h3发生在enrollment，继续只作为原范围的拒绝与pending证据。source coverage和本矩阵的业务事实均不能替代这些项目。
