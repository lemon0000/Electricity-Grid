# C/F：successor 启动根、静态引用图与证据 DAG

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[迁移交接](continuation_handoff_20261026_saved_fresh_machinery_transition_v1.md)，起点 `dcca3bcfa75632291768e9412c5ff54181229c50`。root 唯一 writer，独立只读 PRE_SEAL。本轮建立真实 successor runtime/bootstrap 所需的有限清单，供下一步实现 live lease 使用。

## 实现合同

新增独立标准库工具与独立单测，当前 Source49、ENTRY、adapter、CLI 和所有旧工件保持原字节。从已接受的 `admission_repair.json` 读取 Source49 描述并逐文件核实；这是当前开发 epoch 的静态输入，不是外部启动 authority。项目源码只 parse/compile/disassemble，不能 exec/import，也不读取 P1 内容。额外分析已固定 import policy 的四个外部 Python 源码；启动 `.pth` 与 `_distutils_hack` 若被观察，仅标为当前文件观测，不成为独立预期。

根集合包含现存 self-anchor、direct-entry、import boundary、expectation、successor/entry/wire data API 和 adapter 实际入口；旧33根完整列出 disposition，不把旧 RoleStore/SavedFileBootstrap/关闭的 issuer 当作 successor 可用能力。符号引用图记录同模块 globals、项目/选定外部源码的 import 别名、class/method、定义期表达式、嵌套 code 和 builtin 查询；显式保留动态名字、对象属性分派、写 globals、未解析名称及未分析外部模块义务。静态解析成功不证明运行时对象、闭包、registry 或行为正确，也不宣称完整调用图。递归引用可形成 SCC，不能因 runtime 图有环就删除依赖。

另建固定、无环的证据 DAG：独立 host expected 与启动 TCB → launch 描述 → 本地 cold-main/self → import transition → live transitive lease → full683 hold → controller/parent/fresh 各自 bootstrap → issuer/permit → quiet/结果收尾。三项外部科学协议、整体资源审查与专项运行授权作为 broker arming 前独立决定包；本地启动/runtime/owner条件分别保留。每个节点列明 future verifier、输入、当前可复用证据的准确边界和 OPEN 义务；不是凭 JSON 自报状态发行能力。所有 runtime/root/role/F/science/resource/formal/production 权限位恒 false。

required-evidence DAG 保留已固定 `capability_edges_v3.json` 的全部38节点、37条数据序和23条同进程能力边，包含 broker owner/ready/START/context/offer/ACK/controller permit，以及 fresh result/quiet、G1/parent quiet/G2/G3/returns/broker quiet/H3。另为五个角色分别列出六个启动/本地观察/runtime/full-input前置节点。science protocol、整体资源审查、专项F运行授权是独立前置决定；执行后的 workflow closure 与科学采用另列。全部节点 UNIMPLEMENTED、evidence_ref/runtime_witness=null、produces_authority=false；同进程 holds 仅按实际角色和原能力边描述。

启动 TCB 必须显式覆盖固定解释器/所需 DLL、kernel API、stdlib/外部库、环境、启动 flags、系统 site/`.pth`/customize 与初始 import machinery；当前 `-B -s` 没有 `-S`。不递归认证整个解释器，不把当前对象自报 module/path 或跨进程 Python id 当独立根。子进程未来须在受控启动边界按外部预期核验本地对象、源/EXE、actual self 与上游 retained owner，之后强持；中窗无事件 RAM/native ABA 不在既有证据范围。两个 finder registry 的 mapping/callback 深层内容必须有显式策略，未知项仍阻断。

## 短验证及保存

新 scope 独立 static≤30s、unittest≤20s、总≤50s，不搬用或扩写原120/420/540、诊断18及迁移60/45/105账。前序全累计 static149.7540409、pytest366.4889797；原11条不接受记录和旧8MiB超帽保留。本轮运行前固定 driver/helper/test/source/profile/legacy-root pins；登记≤2s，单次单测≤8s且只在已定位失败后允许一次≤12s repair，静态生成≤12s、保存复核≤8s，static余量保留收尾。原始 stdout/stderr 逐字节 base64 与 pin、exit/charge/cleanup 状态 create-only 保存；失败保留，不自动重启。

结果根 `results/tables/staged_rts24_saved_fresh_root_catalog_v1_non_authoritative`≤32文件/8MiB，单个 catalog≤4MiB、符号≤4096、引用边≤65536；不重复复制49源或历史全树。仅新工具/测试/driver 保存 raw snapshot，旧文件使用精确引用与 pins。最窄验证覆盖 alias/relative import、builtin shadow、class/nested/global 引用、递归 SCC、DAG 缺依赖/环、缺 root、源漂移、动态未知和源码不执行。保存后 fresh 复核重算静态 catalog，canonical bytes 必须一致；这不是实际 cold dependency import 或真实 saved role。

分析器自身固定 compute EXE raw pin、exact Python、`-B -s` 与 optimize=0，并记录 compile(dont_inherit=True)；该分析 TCB 仍不是外部 authority。计费覆盖 parent 准备至后置检查，目标保留0.7s尾部；最终exit序列化、编辑、审查与Git不计，不能称完整workflow wall。最终注册前固定本根8MiB、单catalog4MiB，所有前驱结果帽及其超帽记录保持原值。

无新 native solver、OwnedChild/Job、实际 F、科学 replay、外部下载或付费查询。所有 production seal、official receipt、运行及科研门禁保持原状态。完成后同步本轮 reviewed scope；四导航只发布新 prefix，保留并行论文/文献/绘图及导航旧 body。
