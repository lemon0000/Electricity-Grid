# 保存P1逐调用shadow：严格输入域未覆盖

2026-10-23，DRAFT_NONAUTHORITATIVE。按[合同](../../../docs/plan/staged_deliverability_c_shadow_replay_contract_v1.md)完成一次固定、无求解器的原P1只读重放旁路比较。结论为 **unresolved：全2547次严格编码等价未建立**。旧reopen主体返回后，monitor完整性门因`strict_unsupported`拒绝。失败包保持原字节，未重试。

| 观察 | 保存结果 |
|---|---|
| 命令退出 / worker退出 | 1 / 2，`child_exit_nonzero` |
| 命令wall / Job wall | 17.095632s / 14.313s |
| 采样tree RSS / Job峰值commit | 151719936B / 123138048B |
| 退出资源 | 2/2成员HANDLE已signaled，active0，完整库存 |
| 预算 | Job60s、无进展30s、RSS512MiB、16MiB/64文件；未触及上限 |
| 失败终态 | 8文件 / 284978B；最后保存的digest进度2432 |
| 当前绑定普通检查 | 52 passed / 9.52s；相关旧回归57 passed / 15.41s |
| 失败后保存域回归 | 1 passed / 2.77s；只解码一个保存query并重建reduction |

原P1包含五个模拟小时；这里的wall是执行耗时，不能用模拟时域替代。监控和候选旁路扰动了耗时，本包不支持提速对照或P2预算。

## 范围、路径和身份

[driver](../../../experiments/staged_rts24_shadow_replay_v1.py)首核683个P1文件、旧runtime和新源 → 一个owned fresh worker → 对一次原`journal_v2.reopen`按code监控 → 旧JSON bytes、严格候选bytes、旧返回SHA逐frame比较 → worker末核 → HANDLE quiet → 父端实际runtime/P1/source/output复核。后两阶段只有worker完整成功才采用。

预登记量为digest START、direct JSON RETURN、digest RETURN和strict compare各2547，含固定child别名118、其他2429；JSON RETURN4861。8个stage的完整固定计数见合同。它们是本次验收要求，**不是本次终态已验证计数**。失败没有保存summary，不能声称unsupported恰好1或118次、其余调用均相等、具体首个caller或`monitor_cleaned=true`。

[runtime](../../../src/staged_rts24_shadow_runtime_v1.py)绑定35个仓库模块/包、20类、关键函数/代码/字段、211个实际加载标准库模块、exact compute CPython3.12.12与受控环境。`_function_pin`只检查已加载模块；包路径/父属性和仓库精确源路径一起核验。父端quiet后重新计算实际runtime，而非仅信任worker保存JSON。身份范围限已声明仓库及加载标准库和原选定第三方，不扩展为完整OS/任意第三方闭包。

PRE_SEAL修复了foreign monitoring/profile/trace退出漂移、应用模块路径自证以及父端quiet后仅信任保存身份的缺口；异常传播表述限定比较callback。只读领域与对抗复审无剩余High/Medium，仅关闭开发预审发现，不构成official verdict、receipt或新native权限。

## 已证明的输入域缺口

原[child reduction](../../../src/staged_rts24_child_optimality_v1.py:30)用整数`g.index`构造`generation_bounds`，`audit_child_lp`随后调用固定别名`digest(r)`。旧plain把字典键转成`str(k)`，严格候选拒绝非精确字符串键。保存CAS中的`ChildLpEvidence`对reduction仅保存`reduction_sha`，未保存临时`generation_bounds`映射；整数键映射在审计时重建，因此403个typed CAS根和581个JSON mapping根的先前检查没有覆盖它。

[保存域回归](../../../tests/test_staged_rts24_shadow_saved_domain_v1.py)只读取`point_0002`（h=-2、`recovery_min_meter`）的query/evidence，核重建reduction SHA等于原证据、键为整数、严格路径拒绝，并核公开helper整根fallback的bytes仍等于旧编码。P1首尾683文件相同；没有完整replay、model或native调用。此例为确定的域缺口，不是运行日志直接观测的首个失败位置。原成功profile中的118次child审计也经过此域，但本次未保存总unsupported计数，不能据此补写118。

## 终态与字节保护

[`failure.json`](shadow_01/failure.json)只记录首错reason与callback函数`dumps`。[`launcher.json`](shadow_01/launcher.json)确认实际拒绝原因是worker非零退出；`adoption_failure.json`的泛化文案并不表示Job quiet失败。

`runtime_after.json`、`shadow.json`、`report.json`、`postquiet.json`均不存在。出口异常阻止了后续metrics、fingerprints和末端P1/source/runtime书挡，因此本attempt没有证明`science_metrics_match`或成功采用。公开candidate的fallback正确性也未被这个严格域失败否定。

后续独立[stdlib-only后核验](postcheck_01/postcheck.py)exit0，读取终态但不重放科研栈：50个attempt绑定源保持；原P1完整683文件/2950863B、B1–B3保存118文件与685条前序路径、前两轮profile/plain的68个路径原字节保持。原P1后核验stdout精确复现SHA `c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473`；保存profile后核验也精确复现。见[后核验输出](postcheck_01/shadow.stdout.json)。这与失败attempt内未执行的末端检查分开。

开发失败日志全部保留：units_02的`_decimal`模块别名路径、units_03的pyexpat数据命名空间、units_07的瞬时子进程成员库存不完整。分别修复身份建模和普通测试子进程观察窗口；最终units_08绑定当前六文件。没有修改旧guard或本失败attempt的绑定源码。

下一步以此保存域反例设计版本化后继，先明确严格路径与根级fallback的计数/等价义务和失败可观测性，再登记任何新诊断。当前不接candidate-only/writer，不扩充本attempt预算。C整体性能、昂贵失败、规模增长、139/F-X完整时序及D/E现实输入/选择/留出仍OPEN，formal/resource flags保持false。原P1一次native授权已用，未启动长实验。
