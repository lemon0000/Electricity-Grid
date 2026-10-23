# 保存P1的无求解器性能剖析

2026-10-23，DRAFT_NONAUTHORITATIVE。按[固定合同](../../../docs/plan/staged_deliverability_c_saved_profile_contract_v1.md)执行一次 `profile_01`，命令exit0。原P1的683文件、2,950,863 B及完整重放科学metrics一致；原生工厂、solver、新构模、numeric compile和受观察的科学CAS/publication路径计数均为零。诊断自身创建profile工件。

## 终态和范围

| 项目 | 本次观测 |
|---|---:|
| 完整命令wall | 27.732813 s |
| owned Job wall | 27.218 s |
| 采样tree RSS峰值 | 155,959,296 B |
| peak Job commit | 122,191,872 B |
| 历史成员HANDLE / TotalProcesses | 2 / 2，全部signaled |
| 终态active / final PIDs | 0 / 空集合 |
| worker终态库存 | 10文件 / 220,061 B |
| 追加postquiet和launcher后 | 12文件 / 222,867 B |
| profiled fingerprints | 1次 / 1.2055117 s |
| profiled完整reopen | 1次 / 21.4340412 s |

另有一次未profile的fingerprints尾部书挡；观察器总fingerprints为2次、journal reopen为1次。导入、fixture和首尾完整字节检查在两个profile之外，包含在Job或父端命令wall中。父端准备及quiet后核验没有另设整个命令60秒硬截止；Job帽为60秒，无进展30秒，RSS512 MiB，输出16 MiB/64文件。

[launcher](profile_01/launcher.json)、[postquiet](profile_01/postquiet.json)、[report](profile_01/report.json)与[observations](profile_01/observations.json)保存实际终态。postquiet绑定采用前完整10文件SHA；两个marshal文件为本程序自生成数据，只在本包保存，不从外部反加载。

## 定位结果

| 原组件 | 函数调用 / inclusive观测 | 解释 |
|---|---|---|
| fingerprints | 3次 `Distribution.files`，累计0.9083261 s | 标准库先对全部RECORD条目做缺失过滤，本次触发4,068次 `Path.exists` |
| fingerprints | `nt.stat` 4,289次，self 0.556813 s | 包含上述存在性检查及其他stat，不能全部归为已选择文件读取 |
| fingerprints | 最终selected_application_files为48项 | distribution为37项（highspy11/numpy23/pyomo3），另有7个module和4个runtime条目 |
| 完整reopen | 原 `digest` 2,547次，累计14.6030124 s | 包含嵌套的plain、asdict和JSON编码 |
| 完整reopen | `plain` 4,111,147次，self 3.7076708 s、累计13.5972095 s | dataclass先asdict再plain的递归暴露明显 |
| 完整reopen | `dataclasses.asdict` 2,610次，累计4.5376127 s | 与上两行重叠，不能相加 |

完整数据见[指纹摘要](profile_01/fingerprints_stats.json)和[重放摘要](profile_01/reopen_stats.json)。观察器只统计选定入口；例如其semantic_digest计数不等同cProfile捕获的全部原digest调用。bounded_read的4,885,273 B是所选读取入口的逻辑累计量，未覆盖stamp直接读取，也不是物理磁盘I/O。

cProfile对大量递归调用引入扰动。这些秒数用于定位，不与P1原fresh的12.781秒构成速度比较，不给出P2时长或线性外推。原P1的129次fingerprints及其inclusive成本只说明该路径在原整链中重复暴露；P2如果沿相同point协议，结构上为4×319+5次fingerprints，尚无资源预算。

领域复核搁置RECORD先筛选再exists：未选普通路径的PermissionError也会使旧路径失败，提前过滤会改变失败关闭语义；逐项stat又抵消主要收益。下一候选为严格域的摘要一次遍历，先做独立helper与等价普通测试，证明asdict的deepcopy、精确类型、字典键及失败边界，再决定接线。当前未实现或采用优化。

## 核验

最终21项不同普通测试通过（1.00 s，exit0），覆盖quiet窗口输入漂移、终态声明/计数/schema、缺失或额外profile工件、reparse和独占输出重用；一项实际贯通cProfile、marshal、pstats和摘要validator，仅用tmp普通数据。早期6/14/19项检查日志和各次源码SHA保留，不重复累加测试数。

PRE_SEAL只读审阅的五项发现依次闭合：父端postquiet输入书挡；输入/输出reparse；终态声明与观测schema；完整profile库存；非空profile与实际序列化普通测试。最终源、合同、测试SHA由[prelaunch](development_checks_01/prelaunch_01.json)绑定，审阅没有剩余High/Medium。该审阅不构成official verdict、seal或receipt。

[独立保存后核验](postcheck_01/profile.stdout.json)通过；它只检查字节、绑定、终态和profile算术，不重新执行journal或重建原科学模型。再次执行原P1只读postcheck，输出SHA仍为 `c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473`，与此前完整输出逐字节相同；683个P1文件、118个B1–B3保存物及685个旧检查点路径保持。

C整体性能审查、昂贵真实失败、更长prefix、完整139节点、F/X反事实时序及D/E输入和资源继续OPEN；formal_result/resource_admission等标志为false。原P1唯一一次专项授权已经使用，本次诊断不扩展到新native、P2、D/E或长实验。
