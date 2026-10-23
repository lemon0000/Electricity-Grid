# C：整数键后继的完整保存重放比较

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。依据[v1失败交接](continuation_handoff_20261023_shadow.md)和保存child reduction整数键反例，建立独立版本化后继。原v1失败包、绑定源码和全部旧P1/B1–B3字节保持；本包不修改旧门限或把根级fallback记作严格成功。

## 候选输入域与等价义务

plain_v2仅将exact dict键域扩展为`type(key) is str or type(key) is int`，按原迭代顺序执行`str(key)`再递归value；字符串化碰撞的最后值与首次插入位置保持。bool、IntEnum、子类或未知键仍整根回退旧plain；未知键不在严格探测阶段执行自定义str。精确整数转字符串的ValueError/资源异常原样传播，不通过fallback重试。20个固定注册dataclass、exact list/tuple/基本叶、Fraction、深度64、cycle和同线程静止前提沿用；不缓存输入或digest。

普通回归覆盖键碰撞双顺序、嵌套/注册类、未知和子类副作用、整数位数限制、原403 CAS根/581 JSON mapping根/20类及全部15个保存child reduction；后者须严格支持且bytes/SHA等于旧编码与保存reduction_sha。保存根及15个reduction回归本身不能代替完整实际调用域。

完整shadow直接调用v2 `_walk`，公开fallback不在该路径。验收仍为全部2547次严格编码bytes/SHA相等、strict_unsupported为0；公开fallback只由普通边界测试核验，不是运行时等价证据。

## 固定DAG与身份闭包

controller核原postcheck SHA与683文件/2950863B、旧runtime、新源/测试/合同 → 独占创建v2 `shadow_01` → 一个原Job guard owned fresh worker → 原fixture/trusted与runtime绑定 → 一次原journal_v2.reopen，按code监控 → 完整计数/旧metrics及runtime/P1/source书挡 → 全Job成员HANDLE quiet → 父端实际runtime、P1/source、保存绑定与8个正常输出文件复核 → 采用。失败分支保存diagnostic、failure、logs、launcher；任何不完整不采用。

科学路径仍为原reopen/policy/audit/child，旧结果驱动验收。monitor_v2真实继承v1事件安装、拒绝入口、清理和完整性逻辑，显式覆写START/RETURN以记录上下文并使用新候选；runtime_v2复用v1闭包前缀并增补三个后继module及实际覆写/候选函数的源码、code、globals/ref身份。继承方法也由原闭包绑定。driver独立核main/import身份、源路径和启动参数；不克隆函数、替换旧模块或调用旧install_observers。

身份须包含exact compute CPython3.12.12/executable及受控环境、38个仓库模块/包、完整20类/schema/fallback、新旧实际函数/代码、加载标准库集合及文件SHA、原所选第三方。新候选/monitor引用、父类和NAME/TOOL也须保持。父端quiet后用原identity/refs重新计算实际runtime，再做P1/source/output末核。可信fresh worker、对象静止及未修改标准库前提沿用v1；不宣称任意外部ABA或完整OS/第三方闭包。

## 调用量、诊断和失败

固定digest START/direct-parent JSON RETURN/digest RETURN/strict compares各2547，含child audit固定别名118和其他2429；json.dumps RETURN4861（非digest-parent2314）。8个stage START/RETURN：reopen1、replay_entry6、prepare_hour10、propose_hour10、accept_hour5、audit_execution17、audit_child_lp118、execution_summary1。任何错误/unsupported/unwind/detach、pending残留或清理失败均拒绝。

START登记单调digest序号、caller代码标签及有限root type标签；标签只按已绑定内建类型/20类身份生成，未知类型统一unknown_exact_type，不读取自定义metaclass名称、repr、字段值或保留对象/frame。第一次比较失败固化reason、ordinal、caller与root type，后错仅计数不覆盖。worker在monitor失败出口保存summary（counter、pending数量、清理状态、首错）再传播异常；若写盘本身失败或进程被停止，摘要可能缺失，仍为incomplete，不能补造计数。比较callback的MemoryError与控制异常传播；生命周期清理异常锁存不完整。old unwind保持原异常。

原科学构模/numeric compile/backend make_model/call_highs/CAS写入/发布/journal writer入口均在body前拒绝。每128个digest RETURN写进展，callback内部事件暂停；候选自身JSON不加入旧计数。此计数口径与原保存profile一致，不依据本次观察调整。

## 单次预算与结论边界

普通检查和只读PRE_SEAL findings闭合后，依agent第9节已有有界开发授权，仅登记一次固定原P1保存五小时前缀、无求解器诊断。Job wall60s、无进展30s、采样tree RSS512MiB、16MiB/64文件；沿用guard进程1GiB/Job2GiB commit及5秒quiet截止。父端准备/末核另计；全命令wall同时记录。任何失败保存原字节，不重试、覆盖、扩大预算或事后改变计数。v1唯一attempt已终态，本包使用独立v2路径和新源码/合同身份。

即使全部通过，仅支持本保存完整重放的逐调用严格编码等价。仪器wall不支持提速；candidate-only、writer/native接线、规模增长/昂贵失败、139/F-X完整时序和C/D/E资源另需证据。原P1 native一次授权已用，本包不授权新native/P2/D/E或长实验，不产生seal、official verdict、receipt或formal result。
