# P2输入核验成本诊断记录

2026-10-23，DRAFT_NONAUTHORITATIVE。按[固定合同](../../../docs/plan/staged_deliverability_c_p2_input_cost_contract_v1.md)完成唯一measure_01；这是原P2三个只读函数的有界诊断，没有执行公共P2。起始HEAD为ad2325a246c4f464e5135ad6f6c764fe30a87b85。

## 已观测的成本

| 原函数，固定顺序各一次 | cProfile顶层wall，秒 | 原profile函数条目数 |
|---|---:|---:|
| p2.fingerprints | 0.6391264 | 308 |
| p2.load_packet(validate=False) | 0.0027545 | 60 |
| p2.preserve | 1.4016708 | 279 |

[命令终态](execution_observations_01/command_01.exit.json)为exit0、wall7.1231711s；[Job终态](measure_01/launcher.json)为4.640s、23次采样、RSS峰值151965696B、Job commit峰值116768768B，2/2历史成员HANDLE全部signaled、active0、quiet true，stop/monitor/cleanup均null。未触发60s/30s/512MiB/16MiB/64文件停止帽，无重试。Job终态14文件490615B；quiet后采用和launcher保存后完整measure为16文件493559B。命令、Job和三个profile的窗口不同，差额没有进一步细分为导入、书挡或可节省时间。

指纹profile中，原P1 fingerprints累计0.6024139s，Distribution.files三次累计0.4113948s；其中skip_missing_files与4068次exists形成嵌套热点，nt.stat共4430次、自身0.2388719s。preserve profile中，原P1 preserve累计1.1415937s、原stamp881次累计1.0388603s；_io.open1596次自身0.5862506s、read2449次自身0.2799021s；saved.check_p1一次累计0.2556797s。packet profile JSON raw_decode一次自身0.0008779s。这些条目分别来自[原profile及摘要](measure_01/)，累计时间嵌套，不能相加。旧指纹与历史文件核验是本次后继设计的优先对象；没有证据将packet JSON解析认定为主要实际热点。

三目标子路径的准备工件逻辑读取仍为2525843B/14次：四轮hash2021140B，packet解析255146B、context解析249557B。这是原代码结构会计，不是物理磁盘流量观测。完整内部P2的load_packet960/fingerprints1281/preserve3及2345752302B准备工件逻辑读取，仍只沿用[条件成功图会计](../../../docs/plan/staged_deliverability_c_p2_runner_cost_review_v1.md)，本次没有执行这些总次数，不能乘本表时间形成预算或ETA。

## 身份、恢复与保存

实际使用compute CPython3.12.12、-B -s；解释器SHA4a7d81f72d979c088c653b1da12c2f2d81da66bdf8074753c6a9b154d9c86116，controlled environment SHA5a8dfc180910127d8cee4587e94f27859db05295b950c1435182f788caaa4c37。导入按合同显式预热，含pypower case入口；测量是warm、固定顺序、cProfile仪器影响下的单次观察，没有冷启动或速度比较。

66来源文件首尾保持（55准备源＋7已发布P2输入＋4诊断输入）；39应用模块/33选定函数、profiler stdlib/解释器及1929加载模块名单书挡相同，worker还核模块和函数对象身份。_lsprof为本机built-in，由解释器字节绑定。这是选定运行时范围，不构成完整OS或第三方依赖闭包。三个原返回值完整等价于固定预期，raw profiles独立重算摘要并绑定原函数位置；38禁止入口计数全零、观察器恢复，0 native/solver、0科学构模、0新replay。八事件精确核顺序/标签/字段，父端Job quiet后才采用14个输出pins；[独立保存核验](postcheck_01/postcheck.py)另将launcher/postquiet与完整16文件、外命令终态一同核对。

最终[units_04](development_checks_01/units_04.stdout.log)33项普通检查通过（5.70s），[相关回归](development_checks_01/related_01.stdout.log)68项通过（6.38s），三输入首尾相同。早期units_01为19项通过；units_02的32pass/1failure揭示本机_lsprof无__file__，该失败原样保留；修复后的units_03为33项通过，随后预热case入口并由units_04绑定最终字节。测试使用微小替代函数、临时目录和无目标调用的fresh setup，不能充作实际成本数据。

PRE_SEAL只读审阅修复并复核了事件/module采用、built-in profiler绑定和case延迟导入；实际保存包复核没有剩余High/Medium。没有official verdict、receipt、seal或新增运行权限。stdlib-only后核验exit0：原P1683文件2950863B、B1–B3118文件/685前序路径、294前次发布路径保持，原P1/P2准备/P2runner三个postcheck stdout逐字节复现。未重放科学状态、未重测三个目标，P2执行目录和registration仍不存在。

## 后继的明确边界

下一步在版本化后继里设计核验复用：固定每个进程内可复用对象、绑定来源和完整输出、失效条件、书挡与漂移发现窗口、失败诊断义务，再用替代文件/模块的普通反例核验。Distribution.files的全清单存在性检查含异常语义，已有历史PermissionError反例；不能先过滤或缓存后宣称原协议等价。准备packet、55/7来源及legacy runtime须分别绑定，不能用“已核过”跳过跨进程或quiet后的采用义务。原P2 v1及全部旧包保持，本轮没有实现优化或接线缓存。

后继还需补outer launcher/quiet采用及新注册的开发、65s无进展与fresh60s＋5s收束的父端余量、journal请求构造/prefix重审/存储增长、全成功及昂贵失败DAG成本，再形成具体资源审查和另取native专项授权。原P1一次native授权已使用。P1仍五模拟小时、missing_input/coveragefalse、method/full双null；十小时P2、两帧139数值、完整F/X时序、C整体性能与D/E现实业务/设备工程/选择/留出及预算继续OPEN。目标“推进计划”保持active。
