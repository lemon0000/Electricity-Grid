# C/F：固定Pyomo注册的受限迁移实现

2026-10-26，DRAFT_NONAUTHORITATIVE，起点HEAD `81cfc0caafa4007fdf0ff87952fc687fce342164`。接续[真实取证交接](continuation_handoff_20261026_saved_fresh_machinery_diagnostic_v1.md)。root唯一writer，独立只读PRE_SEAL；只做现有import原语的受限迁移、普通单测/三个短cold及小型保存核对。无native solver、OwnedChild/Job、真实角色或F执行。

## 实现与可证范围

新versioned import policy固定compute EXE/Python、原NumPy/stdlib和两Pyomo raw pins；函数literal固定完整policy长度/SHA，旧profile/失败根不变。factory只compile固定源，绝不exec预期class。按静态源与实际端点注册明确三阶段：B原四对象 → B+同一MovedModuleFinder尾插 → 同一DeferredImportCallbackFinder头插+B+M；阶段单调，不接受跳阶段或任意最终重拍。

审计busy内只观察序列/容器和持有对象，记录observed_stage；busy外显式authenticate完成module/path/class/方法code/default/closure/globals与Loader绑定后记录authenticated_stage。close成功要求两者均为final且无pending；partial、认证失败或任何既有sticky fault均不能洗白。原六个NumPy introspection事件与effect拒绝不扩域。

持有原B/hook/path/cache/modules容器与对象；两个finder必须是固定模块原类的exact实例、空实例dict，Deferred还必须是模块singleton。强持并逐次核class registry对象、module/class/Loader及direct finder globals身份；在非busy位置核固定源码所得函数code/default/closure，并强持原函数与code身份。首次持有后，对这些函数的`object.__setattr__/__delattr__`修改code/default/kwdefault事件立即sticky拒绝，实际caught-effect cold据此验证；非敏感read审计不扩域，原六次NumPy计数保持。认证阶段仅指新增finder的代码/直接绑定书挡，B为构造前现状持有，未独立认证B来源。registry深层mapping/callback、warning等函数的递归行为闭包及任意RAM/无事件ABA仍未认证，full finder behavior/runtime closure、独立expected truth、自锚和角色权限均false。此实现只支持精确结构/绑定及可观察迁移。

反例覆盖：原B等值换对象/重排、同类新M/D、错位/重复/额外/删除、跳阶段/回退/第二次注册、module/class/singleton/registry/global同步替换、方法code/default/closure替换、pending/partial close与故障被捕获；验证正常真实cold CLOSED、caught effect/blocked installation FAULTED。全部来源/阶段/失败及原字节保存。

## 独立预算与保存

前序原账static118.8725048/120、pytest353.8217016/420及9条失败/127文件8,462,120B超帽保持；诊断scope另计static10.4806011/18，全部累计static129.3531059、pytest353.8217016。本scope不转移旧余额、不扩大旧帽、不覆盖旧失败。本scope独立static≤60、pytest≤45、总≤105；报告同时列前序、本次、全累计。

固定阶段帽：baseline登记2s，collection8s＋仅已定位失败后的collection_repair8s，pytest主组20s＋修复重核25s，三个cold合计30s，saved/terminal各5s；static最坏58s，余2s不作自动续时。原初baseline raw另存snapshot，修改只预登记repair路线，原登记费用保留。capture含准备/目标/后置pin及0.5s尾保留；Python初始启动/编辑/审查/Git不计，故不称完整workflow wall。cold normal/caught各≤10s、blocked≤2.5s、parent总≤25s，流帽65536/16384B，超限kill/wait并保存pipe/thread/HANDLE终态；峰值working set仅观察，无RAM硬帽或完整资源准入。caught例仅动态证明真实code setter，同属性其他分支由逻辑反例覆盖，不称所有属性均已冷测。

新根`results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative`≤48文件/2MiB。baseline保留前序Git trees/关键记录/Source49 pin与原snapshot引用；当前变更的ENTRY/tests及实际helper版本保存content-addressed snapshot，复用相同旧snapshot，不重复全历史/完整导航。每动作前后核Source49、当前helper/control、固定外部五文件；artifact保存、collection/admission与后续记录链固定执行epoch。9失败、旧四根和上一诊断字节不改；本根局部合规不抵消旧资源失败。

Source49名称/其他47源、旧科学/wire API及CLI AST保持；允许修改既有import原语和其42测试fixture/断言，并追加有意义的迁移反例。collection必须精确选旧42＋所有新import-policy节点，不丢未知测试。保存oracle独立stdlib核AST增量、真实42+新增集合/Source/helper、cold三case、费用、资源及false门禁。共享导航仅保存短prefix/Git引用，保留旧body及并行论文/绘图。

runtime v2仍UNDECIDED，旧v3 proposal整体admissible=false，所有actual F/run/science/resource/formal gate保持false。下一阶段才连接transitive runtime、真实producer/bootstrap/owner/permit。

## 首次collection失败后的显式工具修订

首次collection实际在5.388268s target窗口超时，charge6.1048414s（帽8），admission/harness均未生成；child已kill/wait且pipe/thread/HANDLE终态闭合。原stdout/stderr/exit及四helper raw snapshot保留。仅为避免第二次重复冷启动，将pytest主组改为collect-and-run：固定prefix选择器完成精确集合后，`pytest_collection_finish`在首个test call前create-only写admission，再在同一进程执行此集合；主组仍≤20s，repair仍≤25s，原static/pytest/total帽不变。外部pytest插件自动加载关闭，项目测试集合及未知新增测试拒绝规则保持。

`revision.json`固定原失败/旧helper snapshot、旧42节点、当前helper pins及允许的工具差异：combined collection、before-test admission、readonly AST/snapshot/review核验补强。它纳入后续control前后pin，main/repair exit实际pin produced admission；cold/saved/terminal锚最新accepted pytest exit。原失败按其历史两control/helper版本核验，后续按revision/新admission核验。此修订不修改旧结果、生产Source或原账，也不将collection超时改成通过。

主组实际94/94通过、charge6.218794s，原成功记录保留；PRE_SEAL随后确认本地conftest额外读取未pin文件，因此由`revision_02.json`明确授权原25s repair，而非把该成功改成失败。v2固定`--noconftest`并清空PYTEST_ADDOPTS/PYTEST_PLUGINS及ini addopts；collection-finish保存publication pin，测试末端严格相等且harness/oracle复核。两revision单向绑定各自前驱helper/记录/当前helper和旧42精确集合。

为使失败历史、repair与saved/terminal都落入原48文件帽，v2后续capture将原始stdout/stderr以base64逐字节嵌入单一exit JSON，原pin仍对解码原bytes核验；历史独立log文件不改，三个cold的子工件仍保留stdout/stderr/row。此为无损容器转换，不删除旧记录、不扩大文件/字节/时间帽；最终小归档复核两种记录格式。
