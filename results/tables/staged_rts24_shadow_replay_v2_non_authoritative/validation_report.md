# 整数键后继：保存P1完整reopen逐调用等价

2026-10-23，DRAFT_NONAUTHORITATIVE。按[v2合同](../../../docs/plan/staged_deliverability_c_shadow_replay_contract_v2.md)完成一次无求解器诊断：固定P1保存五小时前缀的完整原`journal_v2.reopen`中，**2547个实际legacy digest调用的原JSON bytes、v2严格编码bytes与原返回SHA逐调用相等**。旧reopen/policy/audit/child始终驱动科研结果，候选仅旁路比较。

| 预登记项 | 实际终态 |
|---|---|
| digest START / direct-parent JSON RETURN / digest RETURN / strict compare | 各2547 |
| caller分解 | child固定别名118，其他2429 |
| 全部原json.dumps RETURN | 4861，其中非digest-parent2314 |
| 8个stage START/RETURN | reopen1、replay_entry6、prepare10、propose10、accept5、audit_execution17、audit_child_lp118、execution_summary1 |
| unsupported、mismatch及observer/unwind/detach/forbidden错误 | 0；精确counts没有错误项，first_error=null |
| pending / monitor_cleaned | 0 / true |
| 命令与worker退出 | 均0，stop_reason=null |
| 命令wall / Job wall | 18.388875s / 15.125s |
| 采样tree RSS / Job峰值commit | 155459584B / 123772928B |
| 资源退出 | 2/2成员HANDLE signaled，active0，完整库存 |
| 最终保存规模 | 10文件 / 436234B，含采用前8文件及launcher/postquiet |

只执行一次，未超Job60s/无进展30s/RSS512MiB/16MiB/64文件预算；父端准备与末核另计。wall受到旧执行、监控及新候选旁路共同影响，不支持提速对照或P2成本外推。五小时是保存模拟前缀，不能替代完整观察结局。

## 版本化修复与验证

原[v1失败](../staged_rts24_shadow_replay_v1_non_authoritative/validation_report.md)暴露临时child reduction中的整数键映射未被保存根检查覆盖。本[plain_v2](../../../src/staged_rts24_plain_v2.py)仅增加exact `str/int`字典键，按旧`str(k)`转换顺序保留碰撞覆盖及插入位置；bool/IntEnum/子类/未知键仍整根fallback。精确整数位数限制错误原样传播。输入静止、同线程、固定20类/字段及未修改标准库仍是前提。

48项[编码普通检查](../../../tests/test_staged_rts24_plain_v2.py)通过（20.08s）：含403 typed CAS根、581 JSON mapping根、20类、全部15个保存child reduction及键/异常边界。reduction严格bytes/SHA匹配旧编码与保存reduction_sha。公开fallback由普通边界测试验证；完整shadow直接调用严格_walk，没有以fallback凑足成功计数。

[monitor_v2](../../../src/staged_rts24_shadow_monitor_v2.py)继承v1生命周期，显式覆写START/RETURN，在失败时提供有限首错序号/caller/root type，未知类型不探查metaclass或repr，不保留输入/frame。[runtime_v2](../../../src/staged_rts24_shadow_runtime_v2.py)复用v1身份前缀并绑定后继模块/函数，固定38个仓库模块/包、56个关键函数、20类、211个实际加载标准库module及exact compute CPython3.12.12/executable/环境。后继函数自身、依赖别名、模块集合、父类、NAME/TOOL均核验。

82项监控/runtime/controller检查通过（14.50s），74项相关旧回归通过（11.50s）。PRE_SEAL修复了后继runtime自身函数漏绑、合同版本绑定、诊断生成/写盘替换原异常、可变globals/模块集合漏核四类发现。ValueError/MemoryError/KeyboardInterrupt在摘要生成失败、存储失败或已有create-only诊断文件时均保留原异常。最终8个输入源pin首尾一致；早期草稿检查与metadata记录保留，采用最终units_04/preparation_03。两路独立只读审阅无剩余High/Medium，不产生official verdict或receipt。

## 科学结果与保存链

[`report.metrics`](shadow_01/report.json)与原P1 fresh.metrics精确相同，含原genesis/head/state身份和全部汇总。runtime_before/after原字节相同；worker末端和父端quiet后实际runtime/P1/source复核均完成。parent采用前固定8文件的bytes/SHA再次核验，worker stdout/stderr为空。

原科学终态仍为`missing_input`，实际接受h=-2..2五模拟小时；coverage_complete=false，method/full_replay_conditions_satisfied均为null，F/X temporal backing未建立。编码等价不补齐h3..7、不改变原gate或原native_authorized=false注册记录。

独立[stdlib-only后核验](postcheck_01/postcheck.py)exit0，不导入科研实现、不重放/构模/求解。它复核全部计数/caller/事件、终态10文件及8文件采用绑定、54个源、160个声明runtime文件的当前bytes、原683文件/2950863B、B1–B3保存118文件/685条前序路径和此前135个已发布路径。原P1、保存profile及v1失败shadow的旧postcheck stdout均精确复现，见[保存输出](postcheck_01/shadow.stdout.json)。原v1失败包和全部绑定源码保持。

## 后继边界

本结果关闭该固定完整保存reopen的严格输入域和逐调用编码等价缺口。它不证明候选已经驱动科学验收、CAS pack/blob编码可替换、writer失败窗口、未来输入或性能收益。

下一步须确定candidate-only只读接线的实际调用图、身份闭包与旧结果对照，再登记有界资源测量；不全局替换冻结模块，不沿用本shadow身份冒充新执行身份。C整体性能、规模增长/昂贵失败、完整139/F-X时序及D/E现实输入/选择/留出仍OPEN。原P1一次native授权已使用，本包没有新native/P2/D/E或长实验权限，formal/resource flags保持false。
