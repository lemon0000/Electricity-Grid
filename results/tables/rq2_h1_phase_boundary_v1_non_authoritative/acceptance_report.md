# phase 边界开发验收及预算阻断

2026-10-20，DRAFT_NONAUTHORITATIVE。已完成原168h/≤24h合同的业务历史与phase判定函数边界核对，以及可复算的整链工作量审计。**目标长连接包整体预算尚未闭合，完整168/192h验证继续OPEN。**

unit_04终态exit0，15 passed in84.34s、outer87.656s；9份事实留存并逐SHA核验。固定180s/1GiB/128MiB未顺延，采样树RSS180867072B、logical309574B，1305 pins未变，观察pytest/conhost两PID均退出。0 Jobs/native。命令、pytest输出、JUnit、监视与tested_bytes均保存在[unit_04](unit_04/terminal.json)。

业务从genesis推进到167、168、169、170、191、192小时，原assessment与attempt/terminal body核验：enrollment零债务仍不能早停；携primary债进入followup；primary清偿可在followup debt仍正时结束；晚恢复保留deadline F；last due小时先恢复再snapshot。精确due用例在业务hour192恢复0.1、有效清偿0.085、debt/snapshot均0，194次原_validate输入历史长度合计18720。完整case、边界和未覆盖层次见[验收矩阵](boundary_acceptance_matrix.md)。

phase-body输入的heads/binding及lane disposition是显式单元元数据；没有生成owner/source凭据、normal/Rref/Actual前缀、paired event或真实episode_terminal。halted U由JUnit断言保留；缺必要followup仅核需要下一小时的assessment，未实际读取缺失source。当前实现缺源的技术行为仍依据旧pending-attempt证据，正式typed右删失终结继续OPEN。

整链审计核到两个结构性阻断：原toy32-event上限在第11小时分支预留即失败，而168/192至少504/576events；动态prefix重放累计二次，嵌套business history验证累计至少三次。完整192h终结/重开/public inspect路径需1546 Reader observations、149380 prefix-hour，parent inspect3092/298760，仍排除独立historical/snapshot/anchor及normal内部。三条lane始终活跃时，仅ready/post业务历史长度下界28311936。计数、DAG、合法复用、失败分支、资源缺口与优先优化见[整链预算](whole_workflow_budget.md)及[机器记录](budget_audit_v1.json)。

旧1299启动pins、1279继承pins、444 owned/465 case文件及报告在本轮开始时全SHA匹配；旧hour0/两小时/三小时主体、36+23 guards和unit06均复用，没有重跑。旧finite-followup930 pins及phase-owner报告的精确绑定也重新匹配，见[继承检查](reused_guard_evidence.json)。canonical plan/blocker仅插入当前进度，全部原字节另存并可恢复；旧报告中的document hashes指原快照，不伪称更新文档仍是原hash。

本轮失败完整保留：unit_01在测试前被过严child监视停止；collection probe确认直接System32 conhost身份；unit_02的相对root及unit_03的intent漏alternate测试元数据分别被原门/原schema拒绝。最终仅修正新增测试与监视，原科学代码和阈值不变。metadata_probe_01为定位工具，不作为独立验收证据。各失败的request、tested_bytes、stdout/stderr、JUnit/terminal均保持原状态。

后续先做versioned owner/business增量验证或operation内复用，证明原oracle等价、依赖闭包、freshness和失效窗口，再取得代表性整链成本、登记完整存储和任务/reuse DAG。预算门闭合前不启动长连接包。正式RTS/native、full192、writer冷重建、persisted atomic-live、crash durability、seal和fresh official review均OPEN；formal_result/resource_admission/formal_execution_ready/native authority均false。
