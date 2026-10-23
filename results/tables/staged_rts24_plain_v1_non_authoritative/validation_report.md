# 严格域plain独立等价原型

2026-10-23，DRAFT_NONAUTHORITATIVE。根据[保存P1剖析](../staged_rts24_saved_profile_v1_non_authoritative/validation_report.md)的递归编码热点，实现[独立helper](../../../src/staged_rts24_plain_v1.py)，按[合同](../../../docs/plan/staged_deliverability_c_plain_candidate_contract_v1.md)完成普通开发检查。原development/plain/digest、journal和P1执行栈保持，原型尚未接线。

| 核验范围 | 实际结果 |
|---|---|
| 所有P1 typed CAS根 | 403个（journal130、point273） |
| 所有P1 JSON mapping根 | 581个，含保存的普通映射和CAS wire映射 |
| 实际覆盖注册dataclass | 20类，覆盖当前codec完整registry |
| 新helper普通检查 | 36 passed / 13.94s，exit0 |
| 相关原development回归 | 35 passed / 7.51s，exit0 |
| P1完整文件首尾 | 683文件 / 2950863B相同 |

相等的是**解码对象经原plain/digest定义产生的规范JSON bytes和SHA**。这不是EvidenceStore.pack/canonical的CAS blob身份重算；原CAS blob未变由独立文件清单SHA证明。测试禁止candidate整根fallback，确保保存语料实际走快路径；旧、新每个根的bytes和digest均相等。输入对象或摘要不跨调用缓存，静态字段名表仅保存已绑定类型的schema。

未知类型、子类、非str键、循环或深度超过64整根回退原plain。反例包含deepcopy/str/items/iter/metaclass副作用、已注册类的未知叶与子类、namedtuple、键1与'1'碰撞、类对象、IntEnum、不支持的JSON叶、63/64/65深度、循环和共享别名，以及NaN/Inf。当前注册类无自定义字段访问或descriptor副作用。等价前提为对象在调用期间静止、同线程且标准库/注册类未修改；不外推并发变更的快照行为。

首轮1 failed / 32 passed日志保留：测试把旧Fraction ABC首次负缓存构建与后续热调用的metaclass副作用直接相比，计数不同。实现字节未改，测试改为同等缓存状态比较，并补齐三个边界例；最终36项通过。新增测试显式拒绝model/solver/CAS put/publication，且确认原plain/digest函数身份保持。相关35项是既有普通回归，包含原Pyomo构建检查，不是新的数值实验或native校准。检查耗时不作性能对照。

原型代码的独立只读PRE_SEAL审阅未发现High/Medium；后续包装复核发现shadow身份闭包要求不全的Medium，已补齐第24行的后继启动前要求，当前没有剩余High/Medium。领域复核支持该静止严格域及保存语料的机械等价候选。该结论尚不覆盖完整reopen中的每次实际plain/digest调用、失败窗口、未来输入类型或性能收益。

下一步最窄后继为版本化只读shadow比较：旧逻辑继续驱动验收，每个实际编码调用旁路比对candidate规范bytes/SHA，不等、超时或未完成均拒绝宣称等价。接线须绑定helper源码、codec源码、20类定义及字段顺序、JSON选项和捕获的legacy fallback；不能沿用原P1注册身份漏绑新实现，也不能全局替换旧c.digest或修改冻结源码。完整实际调用域等价并独立审查后，再设计candidate-only只读重放；writer/native另行审查和授权。

当前普通测试的三个新源pin不构成shadow运行时闭包；这里的结论限本机普通检查。后继登记前还必须固定exact解释器/executable、Python版本和受控环境；candidate/legacy/codec/全部类的实际加载路径、源码SHA和字段签名；dataclasses、fractions、json及实际加载依赖的实现身份。captured fallback须有模块、函数代码来源及首尾书挡，fresh scope必须拒绝module shadow并在调用前后复核身份。当前registry_schema_01.json仅为静态schema观察，不替代该登记和依赖闭包审查。

本检查点不包含新性能attempt、shadow执行、提速结论、P2预算、资源准入、seal或official verdict。C整体、昂贵失败、更长prefix、完整139/F-X时序与D/E输入/选择/留出仍OPEN，原P1唯一native授权已使用。
