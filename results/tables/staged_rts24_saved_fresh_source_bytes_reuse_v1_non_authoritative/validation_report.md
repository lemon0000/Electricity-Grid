# C：expectation 操作内源码字节复用验证

2026-10-25，`DRAFT_NONAUTHORITATIVE`，起始HEAD `5c3e885cb3b6dd50479ad685593590d5bd0ade86`。范围见[合同](../../../docs/plan/staged_deliverability_c_saved_fresh_source_bytes_reuse_contract_v1.md)，接续[前序报告](../staged_rts24_saved_fresh_expectation_v1_non_authoritative/validation_report.md)。实际F、native owner、solver、B/C/E科学replay调用为零，无新增模拟小时；fresh/parent局部verified、整包科学采用、资源和正式门禁均未开放。

## 实现与失效窗口

原ENTRY仅修改`_expectation_adapter`一个既有函数，新增raw cap常量；tests新增10节点。initial snapshot仍读取和核全部49 source，先核exact集合和expected总bytes；每份原字节逐pin通过后才进入函数局部字典。code比较复用该字典，保留原filename、compile参数、function/code/defaults和globals字典身份检查。两次独立调用重新读取；成功返回binding不持raw，无跨调用/进程cache。

snapshot失败仍独立调用source_pins final；adapter取得后无论compile/code检查成功或失败均运行原adapter.sources final。projection后续原source bookend也保留。只有primary时原对象重抛；primary与final双错由不可序列化SavedExpectationUnresolved强持。2MiB仅约束已核字典raw，当前精确49份为1156762B；当前读取缓冲、compiled code、对象开销及失败traceback均另计。失败可强持raw和缓冲，未宣称已释放或总RAM≤2MiB。

## 当前epoch终态

三源epoch `84b6dafc7793caa2799ec99d3a38a5dfe3f3275448e3d30d3f2f01755a79e419`；ENTRY SHA `8d2398e32336fad3952291011dec70fe532d94e40f99ff5647c6644a44c86854`；tests SHA `e06de1d491d08a6054c539b8539c59e522cff8dde44d60501b59535ea24ba977`。scientific adapter及其余47路径逐字不变。除上述单函数外，全部旧顶层函数/类AST保持。

| 组 | 节点 | 外部帽s | wall s | 终态 |
| --- | ---: | ---: | ---: | --- |
| binding_regression_07 | 18 | 40 | 29.672 | exit 0 |
| expectation_rest_05 | 17 | 35 | 26.781 | exit 0 |
| expectation_rest_06 | 16 | 35 | 20.437 | exit 0 |
| source_bytes_and_smoke_09 | 12 | 30 | 16.203 | exit 0 |

当前精确并集63=10新增+35 expectation回归+18 binding回归，无重复，累计93.093s。首轮source_bytes_and_smoke_04有1 failed/11 passed：测试漏算原adapter.sources对已加载adapter源码的再次读取，正常final应为初读1+selected1+loaded1=3；仅修正测试断言，原source guard保留。其raw、exit、旧epoch测试和helper snapshot均保存，旧11通过不计为本epoch节点。全部pytest attempt累计109.625/160s。历史53/161节点不自动计入当前源码。

新增节点实测单次adapter解析读数为49+49+loaded，两个调用各自重读49，十个code比较没有额外disk read；当前pytest loaded集合36，单次134。负例覆盖错误pin先于compile拒绝、初读后同metadata内容损坏由原final full guard拒绝、initial read/compile primary与final secondary、仅primary保留原对象、raw总帽和boolean/negative size前置拒绝。所有故障使用只读代理/注入，磁盘source/P1未改。三源及执行helper/script在每次检查前后pin一致，并保存对应字节snapshot。

## 单次费用和Python分配观察

见[原始profile](checks_01/projection_profile.json)。补充profile_12固定full capture→projection各一次，tracemalloc在操作内计数；import/setup在操作计时外、仍计外部12s。该profile loaded集合36，full selected-source 174次，projection 223次，后者符合49+2×(49+loaded)+fixture4；逐文件原计数也相符。前序233与当前223相差10；这里只解释十次code磁盘读取复用，source6500整链帽尚未证明。

首个profile_11在保存数据之前因observer公式漏算fixture4次而exit1，外部6.140s，操作内数值没有落盘，不能作为观测结果。源码load_fixture读取3份配置及自身compiler SHA，解释该漏项；先保存旧合同和失败helper/source/raw，再在原预算内明确登记补充一次profile_12，外部6.219/12s终态exit0。补充观察先落盘逐文件raw再核公式，没有删减source freshness检查。除此未追加诊断；两次费用均计入40s静态预算。

P1仍为683次/2950863B及53次/94323B；同一当前SF49下caller image逐字相同，image SHA `24a1933f6c009af593d344815090933a267819bb793ecc1a00600e99c9f8bf29`。full_P1_content_verified仍false，未读CAS仍由后续原full hold核验。

| 操作 | Python traced before B | after B | peak B | wall s |
| --- | ---: | ---: | ---: | ---: |
| full_capture | 0 | 5027601 | 13485065 | 2.175692 |
| expectation_projection | 0 | 1706711 | 10388564 | 2.108695 |

tracemalloc只覆盖启用后Python allocator分配并包含探针开销，不覆盖已存在对象/native分配，也不是RSS。两行不能相减当作新增raw dict的隔离内存效应。固定顺序可能受缓存预热影响，探针配置也不同于前序profile；不报告稳定速度比、whole-F节省或整链内存上界。本轮profile及捕获helper有执行前后pin与snapshot，强度限于这些脚本和canonical SF49，不等于传递runtime闭包。

## 保存与下一步

前序3270个保存路径与P1全683文件逐字核验；三份导航既保留旧body，又绑定本轮完整after-body/current whole pins，未来仅准在前面追加。保存层复核指出首个saved_14依赖可变当前ENTRY，不能支持未来reopen的长期保全强度。旧checker/report/support及执行snapshot保留；当前checker改用本地标准库pin/canonical、三源/两mutable及OUTPUT parent字面值，完全不导入当前ENTRY，也不递归运行旧checker。先核3270路径原字节，再解析前序saved_14的冻结exit/stdout/snapshot/source绑定；旧53仅代表其原epoch，旧profile helper execution-time pin仍false，未由本轮反向升级。当前P1 expected pins取自固定SHA外锚，独立核683 exact-set、普通文件/handle/read pin及前后metadata/root/祖先身份。目录书挡仅支持本次扫描期间的身份保持，不证明历史目录身份；这些是保存层完整性证据，不升级G0/H3或full_P1_content_verified。开发预算200s，pytest160/static40；本次包装前静态累计26.514s（嵌套collection记录保守累计），最终包装/checker自身另以终态exit累计。保存核验输出明确排除尚未生成外部exit的当前checker耗时。

保存oracle首轮saved_16因局部循环变量pin遮蔽本地hash函数而在开始读current sources时exit1（0.078s）；改名source_pin后重新核验，旧helper/exit/stderr全部保存。这是保存工具修正，canonical ENTRY/tests及63节点epoch未改变，未重跑已完成pytest。失败耗时仍计原40s预算。

本轮保留全部原49 source观察窗口、G0–G3、parent/fresh独立hold、原B/C/E审计、四个命名库存和host末次full。私有prototype恒real_verified=false；生产transitive global binding、真实G0/H3、trusted role/ACK、issuer/driver、source6500、完整失败读数、180s逐边deadline/episode handoff、最大合法wire、external arming/quiet与host I/O硬停止仍OPEN。P1成功12159仍只是条件算术。

下一步先枚举生产adapter实际传递global依赖与角色能力边，固定可验证闭包和失败窗口，完成真实G0与trusted supervisor/ACK的结构性合同；再接driver及完整调用/资源证明，之后才可提出具体actual F申请。不再把已经完成的十次code重读当作尚未完成项；也不删除当前保留的freshness边。

保存核验：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01/saved_checks.py`。见[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_source_bytes_reuse.md)；未生成production manifest/lease、official verdict/receipt/seal或run authority。
