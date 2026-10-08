# 共同参考请求 LP 与赋值投影审计

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal限定范围无开放实质finding。
实现`reference_grid.py`，测试`test_rq2_reference_grid_v1.py`。
本组件落实`rq2_common_reference_request_design_v1.md`的第一步构模；后续selector与跨小时扩展见文末及`rq2_reference_selector_v1.md`。

## 显式机制与origin

ReferenceProtocol必须显式声明共同baseline、不含CFE/业务恢复、假定此前reference履约，以及all-current-hours机制范围。
这是测试与DRAFT构模的身份字段，不是已注册的正式小时范围。origin通过现有initialize_actual_carry核对初态，
外层ReferenceGridOrigin采用受控构造，拒绝直接传入各臂ActualStepCarry。
初始化仅允许显式机制origin；后续接受selector受控生成的ReferenceGridState，不会从任意赋值或业务臂状态伪造已选择的reference后继。
已有赋值审计的内部physical carry不等于reference后继；本组件的next_reference_state恒为空。

## 构模

复用当前fixed-power模型的全部generation bounds、normal response、actual ramp、repair、支路方程和容量约束。
仅以变量P_ref替换DC节点负荷，界为`0 <= P_ref <= current baseline`，目标为`baseline-P_ref`。
上游当前信息已要求baseline不超过physical/connected界，因此此变量域也在其内。
不依据fixed-power检查作单调二分，不假定P=0可行，不从事故是否存在跳过构模。
原current_grid_step源码与验收阈值保持。

## 赋值审计与证据

要求reference模型全部变量原赋值，逐项有限；P_ref必须精确落入非负baseline域，不能用1e-6扩展请求定义域。
把P_ref的十进制表示转为有理数MW，删除此额外变量后，独立fresh重建fixed-power模型并审计全部物理赋值。
精确candidate G以`Q(str(baseline))-Q(str(P_ref))`记录分子/分母；未通过物理审计时不提供candidate G。
fixed-power投影检查约束、reference额外变量域和节点平衡，测试同时对照reference模型的canonical约束。
前后重验reference身份；身份包括机制、origin、当前信息/揭示、继承实现闭包及本模块SHA256。

物理可行但非最小G也可产生赋值见证，这不是选定请求。selected_request、next_reference_state、
minimum_request_certificate、causal_certificate及infeasibility_certificate均为空，formal/security为false。
未调用solver、没有最优界或numeric selector，也未归一化业务请求；正小请求的SERVICE_TOLERANCE适配仍待后续。

## 验收

解析上界例：normal/prior=20、ramp=10、external=20、baseline=25，P=10对应G=15可行，P=11违反上升ramp；
P=0/G=25也是可行赋值，但不能据此宣称最小请求已求得。
非单调例：prior=25、normal=20、ramp=10、external=0、baseline=20时P=20与15可行，P=10违反下降ramp 5 MW。
另覆盖B=0、严格请求域、repair cap、generator/branch outage、完整赋值、origin角色、机制声明及身份漂移。
另覆盖远端DC节点与AC故障时DC支路输送，防止变量负荷被放入错误节点。
最终44项针对性测试通过（16.41s）；修复后五文件193项相关回归通过（39.15s，在最后远端例新增前，源码未变）。
独立pre-seal发现expected_identity可被自定义相等对象绕过；已在两个入口共用门严格要求built-in str/64位/lower-hex，
补充10个反例，独立43项通过（17.13s），finding闭合，限定范围无开放实质finding。
fresh-import仓库依赖集合与identity覆盖集合一致；`git diff --check`通过。

实际命令为`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`，相关文件为tests目录的
`test_rq2_reference_grid_v1.py`、`test_rq2_current_grid_step_v1.py`、`test_rq2_current_grid_short_solve_v1.py`、
`test_rq2_grid_information_v1.py`、`test_rq2_event_disclosure_v1.py`。
新增reference测试只构模/解析赋值，相关回归含已有短solver微例；未启动正式计算、下载或清理仓库。

原origin-only开发字节SHA256（历史验收版本），非production seal：

- source：`c2e34ac62c149c2bf3bcfba089a4abb3d3a2143ec0760d6308e85640e7cdb211`
- test：`62860ee785aae5c215647f5e994744c0a0f6f5f865e08d6590ffce983fb5bf62`

后续开发新增ReferenceGridState，绑定origin、previous、selector policy和selection证据；构模/赋值审计共用
受控物理carry提取，保留原origin语义。selector已实现，当前验收状态及检查记录见`rq2_reference_selector_v1.md`。
普通赋值审计仍不生成已选择reference后继。下一必要工作是完成selector验收，再补实际dispatch选择、共同请求适配和逐臂双提交。
当前初态、报告和参考过程都是机制输入，不代表真实观测；完整科学协议、连续输入和正式运行门仍未闭合。
