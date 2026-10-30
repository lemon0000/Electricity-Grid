# F：host Win32 静态重放修复 scope v2

2026-10-30，DRAFT_NONAUTHORITATIVE。承接 [v1 terminal 交接](continuation_handoff_20261030_saved_fresh_host_windows_preparation_v1.md)；资源设计沿用冻结 [design v1](staged_deliverability_c_saved_fresh_host_windows_design_v1.md)。本包只修复 AST 保存表示和阶段解释器绑定，新增模拟跨度0h。

v1 的 saved 断言拒绝已归档，CP14387B / `cf4d9b5edf15dac5dacc83da2366152eafbf865f0f6ea40dcf7fa5d01d58e6f4`仅接受 rejection metadata。完整继承 input1599/92381027B、archive355/45349680B，以及62条不接受记录和累计1570.8727648999768秒；不重写 v1、不退款。新 own95/overlap11/input1683，登记使用实际 exact union。每次继承核验还须将原F合同与v1 registration逐canonical字节比较。

后继 audit 显式启用 `ast.dump(show_empty=True)`（有该参数时），保留所有字段。对冻结 v1 inspect 报告继续 canonical-byte 严格相等；不删除或忽略三组不一致字段。静态诊断比较7组默认/完整表示，固定核对3组差异、已存摘要及一次真实 AST 内容变更；对缺项、源码 SHA、门值、布尔冒充整数、结构摘要做拒绝探针。序列化 round trip 必须完全一致。

每阶段绑定和记录解释器路径 `C:\Python314\python.exe`、版本 `[3,14,3,"final",0]`、implementation `cpython`、106328B / `cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b`，并要求 optimize=0、dont_write_bytecode=true。[runtime manifest](../../experiments/staged_rts24_saved_fresh_host_windows_replay_runtime_v2.json)为14011B / `c1dd92780cd5908ee30e0e3e08a898d217d55e949ed7c77d0e66d717f7f57be7`，固定79文件/19870005B：含71个已加载模块对应文件、exe及解释器目录和DLLs目录中的DLL。ast.py、json包、hashlib及加载的pyd、python314.dll均进入own/input；scope不再依赖inspect.signature。阶段前后逐文件核pin，并拒绝C314目录中新加载而未绑定的模块。该身份用于本静态工具的可复现性，未认证Windows系统DLL、完整runtime或独立TCB。

从冻结 v1 unit.exit.json 严格复用42方法、20 fault cases、原日志和 closed contract，重新核对 IDs/AST/日志对应和所有 source pins；本包不执行 unit、测试模块、项目 Native API、P1、Source49、目标或验证子进程。Python控制进程和普通文件/AST读取仍实际发生。

唯一 register→inspect→独立PRE_SEAL→saved→checkpoint；首次 register 冻结 own，首次拒绝只 checkpoint，后续修复独立 successor。static帽5/6/10/8/5=34秒；不新增unit预算。root10files/4MiB、record1MiB、CP预留1MiB/1slot保持。原F180秒、165秒成功分配及科学/数据/存储/terminal全部上限保持。源实现与42方法证据仍只属 `host_win32_resource_source_and_private_protocol_synthetic_only`；Native-return gap、短命 member、source issuer、真实文件/broker/full-role入口、全工作流 admission 均保持原未决状态。所有29个执行/科学/生产门保持false。
