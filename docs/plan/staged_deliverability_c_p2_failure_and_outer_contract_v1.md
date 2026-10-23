# C：P2昂贵失败矩阵与父端观察保存开发

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[成功图会计](continuation_handoff_20261023_p2_accounting.md)。本轮完善原P2的失败控制回归，并实现outer所需的quiet后父端观察保存组件；不创建公共执行注册、outer生产manifest/lease、P2目录或任何运行权限，不启动native、solver或长实验。root唯一writer，审阅只读不分叉。

## 失败路径与已花成本

固定319槽：actual41；h1 normal42、h2 normal181，其余为69个firm/raw对。失败槽reservation永久收费，不重试。下表是条件结构位置，尚非实际P2失败观测或wall上界。

| 故障位置 | 已花槽／接受前缀／合同 | 当前后继与证据限制 |
|---|---|---|
| 最后一raw数值未决 | reserved319/imported318；actual10；已成行137 | 已复现数值未决可finish、fresh、parent reopen并保存诊断；包不完整，不推断不可行 |
| 最后一raw transport/quiet未知 | 最多319/318；actual10；最多137行仅内存 | worker不finish、不fresh、不report；先确认全外层Job quiet，才可独立诊断现有文件 |
| 最晚journal.begin_step前检查/prepare失败 | actual阶段已reserved最多40槽（31 reference/recovery＋9 actual）；接受9小时；0合同 | 此处是参考取证后的journal begin；取证前的Cursor.begin_hour为37槽。正常journal begin本身不发布hour；prepare语义失败才可能发布closed reference attempt。CAS或root失败也可能仅留failure/pending；均不增加接受前缀 |
| 最晚commit发布前/后异常 | 最多41槽；Cursor仍只接受9小时 | final可能未发布或已含第10小时；可信fresh可诊断，当前Cursor永久停止，不继续合同、不手工补账 |
| terminal发布前/后异常 | 319/319；actual10；138行仍可能只在内存 | 合同表在finish成功后才保存。terminal存在不等于合同包/父采用完成；当前worker不fresh |
| fresh非零、停止或quiet未知 | 319/319；138行与trusted binding已保存 | 父reopen尚未执行；原包不得称fresh验证成功 |
| parent重放/metrics失败 | 同上，已额外消耗fresh及部分父审计 | report/completion可缺失；不能由writer terminal倒推包成功 |
| Job cleanup/close未知 | 可能已花满319且已有report | quiet前不检查科学结果，保留进程诊断，不将terminal改写为不存在 |
| quiet后父记录写入/读回失败 | worker可能完整，另加父扫描/发布成本 | 父保存状态未决；保留partial/final原字节，不能补写本次成功或自动重试 |

数值失败可额外消耗单点完整停止帽、清理和后续fresh；持久化失败还会写orphan/pending/failure。故319点成功图和P1墙钟不能直接作为失败成本。十小时CAS/摘要、IO阻塞、真实native/getter失败、完整outer尾部wall仍未知；fresh60s＋最多5s收束对65s无进展没有父端余量证据，不在本轮放宽任何帽。

既有证据：P2首次reference/actual失败、reservation不退款及terminal后异常；journal v1/v2保存的reference/actual unresolved、before/after rename、closure删除；guard cleanup/close与完整HANDLE清点。它们各按原范围复用，不能冒称公共P2完整失败物证。新增回归覆盖原P2 point的FakeApi数值/发布错误、真实worker/full_contracts控制流中的最后一槽与fresh/父metrics失败。

## 本轮实现边界

新增`staged_rts24_p2_outer_observation_v1`是父端**观察记录保存组件**，不是完整launcher、包科学采用器或独立数值审计。它接收父端预持有canonical context bytes/SHA及直接supervisor记录；组件无spawn/solver/注册构造接口。context明确为development proposal、public_execution_enabled=false、native_authorized=false、resource_admission=false，注册SHA可为空；绑定context不代表实际来源freshness已重验。

组件先严格核进程记录：exit/stop/error、完整历史成员清点、owner PID/creation、active0、final PIDs空、retained HANDLE全部signaled、总成员一致，以及终态文件/字节/采样内存未越proposal。固定保留原guard的16384B和1文件终态空间，不接受零或缩小reserve。只有成功退出且完整quiet，才调用明确传入的机械检查函数；其他情况只保存进程诊断，不读worker结果。返回采用闭合mechanical schema：固定scope，三个nullable SHA、point/contract计数、机械完整性bool，以及明确未验证的worker full_139/package声明；额外键、权限或科学采用字段和非规范标量均拒绝。保存的caller-supplied mechanical claims不能自动变成独立139证明。

父目录与worker目录分离。canonical记录保留execution、ownership、inspection/package和publication语义，始终scientific_audit_replayed=false、scientific_evidence_adopted=false、full_139_independently_verified=false及formal/resource false；worker terminal保持not_independently_replayed，任何异常不声称terminal不存在。复用原codec Windows create-only pending→flush/fsync→no-overwrite rename→readback协议，保存context SHA和process snapshot；再次核父目录身份与最终原字节。失败保留pending/final，返回携带phase/expected SHA/may-have-published的未决异常，无receipt/seal，也不覆盖重试。

普通测试限pytest tmp：canonical context/record、完整/矛盾/未知Job、恶意inspect返回或异常、context/目录漂移、已有target/pending，以及七个publish阶段和readback故障。P2 worker控制测试使用显式替代transport/journal/fresh，不执行native或独立科学audit；69个解析控制标签只用于固定319槽和137/138行控制流，不能提供69个不同公共事故的科学结论。FakeApi单点检查沿原numeric/backend接口，不创建真实Highs实例。

## 验收与后继

针对性及相关回归、源码首尾pins、独立PRE_SEAL findings、旧绑定和Git状态检查后保存开发报告。没有独立实验attempt或性能诊断，普通测试wall不作预算。原P2七输入、packet、journal、P1/B1–B3和历史失败保持；新代码/测试/合同的完成不解除既有blocker。

完整outer仍需另层绑定实际注册SHA、55+7+outer来源、exe/argv/cwd/limits/目标root并核首尾；quiet后completion core＋精确manifest外白名单＋全目录库存书挡、319点及138合同引用/接受state、fresh/parent metrics；科学采用还需受控fresh对全部raw→snapshot/KKT/point/合法X与journal重放独立复核。本组件只能保存该层将来提供的机械观察，不能取代它。之后才补失败及尾部的有界成本证据、具体稳定包/资源审查和新的native专项授权。C整体、139数值/F-X时序及D/E现实输入/选择/留出和总预算继续OPEN。
