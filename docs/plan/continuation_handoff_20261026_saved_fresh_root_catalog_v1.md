# C/F：有限根 catalog 与实际保存重算检查点

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[迁移检查点](continuation_handoff_20261026_saved_fresh_machinery_transition_v1.md)、[本轮合同](staged_deliverability_c_saved_fresh_root_catalog_scope_v1.md)与[显式修复合同](staged_deliverability_c_saved_fresh_root_catalog_repair_scope_v1.md)。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/production seal。持续推进计划保持active。

## 已落盘及验证范围

新增 `experiments/staged_rts24_saved_fresh_root_catalog_v1.py` 和独立测试。Source49、ENTRY、科学adapter及CLI均未改；current source epoch仍为 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。此前94项和三个cold的证据仅按其原字节/范围复用，本轮不重跑它们。

工具逐字核固定admission/policy/旧33根/catalog合同、Source49及四个外部Python源码，绑定compute EXE/exact Python/`-B -s`/optimize=0；只parse/compile/dis，不import或exec被审计源码，不读P1或执行科学replay。新工具、测试和两controller不属于Source49，由本scope独立helper/input/snapshot pins绑定。

结果根为 `results/tables/staged_rts24_saved_fresh_root_catalog_v1_non_authoritative`。`catalog.json`实为2,959,548B／`4785d6e719fe469e8b9dd68b1fd8bf16c5a8b017f2645c3fcf575cc1ceaef47a`：54个当前根，旧33根完整逐项去向，2,626符号、10,984引用边、25递归SCC。边为static_candidate6236、runtime_required2947、dynamic_open830、external_root_required615、native_open356；即使static_candidate也不等于运行时绑定已经验证。模块初始化、closure/cell、多定义、未知属性与compiler-elided声明均显式开放；该图不是完整运行时调用图。

required-evidence DAG有76节点，完整保留旧38节点、37数据序与23同进程能力边；五角色各有独立的pre-ENTRY/self/cold-main/import/live-lease/full-input前置项。broker握手、controller/parent/fresh issuer/permit、quiet/返回/G0/G1/G2/G3/H3均保留；外部科学协议、资源审查与运行授权分别列出。所有节点UNIMPLEMENTED、无witness或artifact evidence、不发行authority；图的拓扑成立不证明这些能力已存在。

## 实际失败、修复和账

首轮unittest实际28run、27通过、1error，charge0.518539s：CPython省去了无条件顶层raise之后的函数code，工具原先要求每AST声明必有compiled code。原admission/report/exit、stderr原bytes和三helper snapshots完整保留。修复只在新工具的 `StaticModule.facts`/`ReferenceGraph.build` 保留AST引用并标compiler_elided与dynamic_open；原tests/driver不改。revision_01固定旧/新整文件pins，机械核其他AST相同，并将旧3/新2 snapshot全部纳入input pins。

新repair_driver仅消耗原预留12s修复路线：实际28/28通过，charge0.3229288s；静态catalog生成2.209959s；fresh重算保存复验2.1265859s且canonical bytes完全相等。原unit失败仍false，后续严格依赖accepted repair/catalog，不跨过失败前驱。四次实际child均HANDLE/pipe/reader终态、无kill或cleanup错误；生成/重算峰值WS129,187,840／129,757,184B，仅观察，无RAM硬帽。

原登记0.0380042＋修复登记0.0569695，合计0.0949737/2s。本scope最终计费static4.4315186/30、unittest0.8414678/20、总5.2729864/50s，含首次失败，不退款。上游保留static149.7540409、pytest366.4889797；全累计static154.1855595、pytest366.4889797、unittest0.8414678，总521.516007s。计费范围排除最终exit序列化、编辑、审查与Git，不能称完整workflow wall；原static120帽失败和旧8MiB超帽保持。

原11条不接受记录加本轮unit失败共12条，所有前驱及失败原字节保持。生成/保存终态时本根21文件/3,187,115B；独立只读PRE_SEAL无剩余实现finding，补4097B记录后最终22文件/3,191,212B，满足本根≤32files/8MiB及单catalog≤4MiB。该复核不是official verdict。旧迁移44与机械9根完全不改，不把新根算作原48内通过。

## 下一项实质工作

先读本根 `saved.exit.json`、`revision_01.json`、`catalog_report.json` 与本交接，核Git/进程并续账。当前TCB最前端仍OPEN：已有ENTRY direct/self观察均发生在项目模块执行之后，不能反向认证其构造。下一步实现由外部固定raw/pin建立的独立stdlib bootstrap，在项目import前取得实际self观察、比较外部Source49/EXE/profile/argv/env与初始namespace；不能由child现读文件重造expected。其自身及startup TCB必须有独立来源，系统site/`.pth`/sitecustomize/初始module集合尚待具体闭合；本轮两个startup文件只保存当前观测pins。

随后按catalog声明根实现同进程live runtime lease，明确两个finder registry mapping/callback、builtin、class/descriptor及外部/native边界，再连接successor request/context、真实producer/owner/ACK/issuer/permit及完整quiet/返回链。CLOSED import guard、ordinary observation和self HANDLE都不能转换为角色权限。旧runtime v2仍UNDECIDED、v3 proposal整体admissible=false；actual F、native授权、科学/资源/正式及运行门禁均false，未启动F/OwnedChild/Job/native solver或长实验。

Git仅同步本轮新工具/测试、两scope/交接、新结果根与四导航短prefix；并行论文/文献/绘图及共享导航旧body保持。远端hash与最终worktree状态以发布后实时核验为准。
