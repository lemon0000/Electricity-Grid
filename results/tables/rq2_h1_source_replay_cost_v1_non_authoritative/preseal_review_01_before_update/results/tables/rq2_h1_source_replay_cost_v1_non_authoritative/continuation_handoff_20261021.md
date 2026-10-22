# Source成本分解续接

主线仍为168h/≤24h阶段边界与episode终结，先完成整链预算。2026-10-21，DRAFT_NONAUTHORITATIVE，根代理唯一writer；旧dirty/冻结/失败原件保留。先核Git/PID、final_verification.json所指最新core及绑定，再读[本轮报告](acceptance_report.md)、[候选设计](constructor_inspection_successor_design_v1.md)和call_dag_and_work_units.json。

profile_02只读重放保存3h的一个原historical Reader，0Job/native，exit0、reader74.837764s/outer79.578s（含cProfile），RSS206053376B、logical2623169B，1302pins未变、观察PID退出。三份normal audit/proof与旧intent相同，465case/444owned SHA不变。原件仍在`D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0/`，禁止writer adopt或接写。

实际两层“2”已拆清：每source batch双Reader；每Reader constructor self.inspect与caller reader.inspect各一次。后者形成当前3h单Reader的12次inspect_job/60次stage.inspect。normal_input_identity1560次、顶层metadata.version10922次，cumulative计时嵌套不可相加。原15个static identity memo targets保留，同一个诊断不代表生产开销。

profile_01失败发生于安装toy source后误调用完整open_manifest进入真实168h source audit，Reader未执行；后续空pstats又报错，外层exit1原件全部留存。profile_02复用前驱的MANIFEST_PIN+私有_resolver编译冻结bytes，未重验真实manifest源，未扩规模/预算。

下一步按候选设计处理constructor首次inspect结果复用。需要新historical/source/validator身份，双Reader和所有后置动态检查保留；先证明构造器返回至后置bookend的逐类fault/依赖/异常等价，再做保存原件对照。当前没有实现，不将条件减半计数称作实测提速。旧业务record缓存负结果继续不采用；当前cross-hour owner已用stable replay，优化N0-only phase owner的重复restore不能冒充本链收益。

全168/192h prefix、真实episode_terminal→checkpoint→close/reopen、typed缺followup右删失、writer重建、persisted atomic-live、crash durability、完整动态闭包/ABA、整链wall/RSS/storage、resource/native/formal/seal/official gate均仍OPEN/false。既有hour0/2h/3h和phase-body按SHA复用，不为换对话重跑。只有预算、合法减少和必要科学证据有依据后才能重审长连接，不推断正式运行授权。
