# C严格编码完整保存调用域闭合交接

2026-10-23，DRAFT_NONAUTHORITATIVE，目标“推进计划”继续active。接续[v1失败诊断](continuation_handoff_20261023_shadow.md)，上一已推送检查点`90e2bd6ef2ddc535f39701963b3ec6c278ea4296`。当前Git发布以此交接后的远端readback与worktree为准；共享论文介绍修订和旧工件保持。

## 当前实际完成

按[新合同](staged_deliverability_c_shadow_replay_contract_v2.md)建立plain_v2、monitor_v2、runtime_v2和独立driver。候选仅扩展exact str/int键，旧字符串化碰撞/顺序及异常保持。公开未知域仍整根fallback；shadow只走严格_walk。新monitor继承原生命周期，并增加有限首错信息和失败摘要；runtime复用原闭包，固定总计38模块/56函数/20类/211标准库module身份及固定aliases/集合，自身函数也绑定。

48项编码普通检查（20.08s）、82项监控/控制器检查（14.50s）和74项相关旧回归（11.50s）exit0；PRE_SEAL及领域只读审阅无剩余High/Medium。完整保存根403/581、20类和全部15个child reduction核验严格bytes/SHA。普通检查不替代下面的实际完整调用证据。

v2唯一`shadow_01`已成功：一次原P1保存五小时前缀的完整reopen中，digest START/direct-parent JSON RETURN/digest RETURN/strict compare均2547，caller=child118+other2429，JSON4861，8个stage量全部与预登记相同。first_error=null、pending0、cleanedtrue，没有unsupported/mismatch/observer/unwind/detach/forbidden错误项；原metrics精确相同。worker及父端quiet后runtime/P1/source/8文件采用书挡完成。

命令wall18.388875s、Job15.125s、采样RSS155459584B、Job commit123772928B；2/2成员HANDLE退出、active0，exit0/stopnull，未超60s/512MiB。终态10文件436234B，没有重试。此耗时含监控和旁路，不能称提速或预算外推。

独立[后核验](../../results/tables/staged_rts24_shadow_replay_v2_non_authoritative/postcheck_01/postcheck.py)exit0：54源、160个声明runtime文件、原P1683文件/2950863B、B1–B3保存118文件/685前序路径及之前135个发布路径字节保持；原P1/profile/v1失败shadow的旧postcheck stdout均精确复现。v1失败包未改，也未补写它缺失的计数/首错信息。详见[报告](../../results/tables/staged_rts24_shadow_replay_v2_non_authoritative/validation_report.md)。

## 下一实质步骤

当前已证明固定保存reopen中2547个实际legacy编码输入严格bytes/SHA等价，候选仍是旁路。下一步定位candidate-only只读执行的实际接线点和完整调用图，固定后继源码/函数globals/类和codec/旧结果对照身份，再设计一次有界资源测量。不要全局monkeypatch旧c.digest/plain，也不要把shadow的runtime身份直接当成新执行身份；新路径必须真正执行候选并保留旧验收/失败语义，不能用样本根benchmark代替完整reopen资源。

主范围仍RTS-24公共网络，两母线机制回归。原P1五小时仍missing_input、coveragefalse、method/full双null；没有完整观察结局、139或F/X backing。C整体性能、规模/昂贵失败、D/E现实业务/设备/工程数值、D/选择/平局/敏感性/时域和留出来源/split/seed/reveal仍OPEN。原P1唯一native专项授权已用，没有新native/P2/D/E或长实验授权，formal/resource flags保持false。

恢复先读AGENTS、agent第7–9节、本页、C计划与blocker，刷新Git/进程。root唯一writer，子代理只读且不分叉。保护原P1、B1–B3、两轮shadow及所有失败/历史工件；复用已经闭合的证据，不重复诊断。Git按精确NUL范围、raw bytes/index、远端hash与clean worktree确认。
