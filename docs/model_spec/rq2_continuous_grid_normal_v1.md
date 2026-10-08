# 连续 normal 网侧构模与赋值见证

状态：`DRAFT_NONAUTHORITATIVE`。日期：2026-09-16。

## 范围与证据角色

`continuous_grid_normal.py`复用`src/grid/rts_gmlc_scuc.py`的纯context/model构造器，
独立建立任意正整数H的连续normal基线。无事故小时也包含发电、开停、线路、母线平衡和备用约束。
旧SCUC入口、冻结配置与结果字节保持。此组件不执行solver、不注册科学参数，不生成生产manifest或认证。
测试中仅有一个两小时、单线程、1秒上限的HiGHS开发小例。

输入为RTS-GMLC结构、完整正常调度request、显式fixed initial、同边界GridCarry、连续来源小时和时钟解释。
来源小时为传入数据`hourly_points`的1-based索引，首小时等于carry.source_hour+1。
`naive_source_labelled_utc`显式将源文件无时区标签映射为UTC标签，仅为benchmark时间映射，
不声称源观测是UTC物理同钟；`aware_source`要求源时间本身有时区。
机组初态历史保留`mechanism_assumption`或`derived_dispatch_witness`角色；真实观测身份不由本模块建立。
初态source_scope和业务parameter_status必须是非空built-in string；自由文本标签本身不提供来源证明。

## 初态、模型与开放末态

三张fixed initial表必须与request相同，committable子集必须与GridCarry逐项一致；
机组power/ramp/minimum-up/down limits从源generator字段派生，不能由调用方另行放宽。
1h初态age必须是非负built-in integer；1.0、1.5、bool均拒绝。
对于初态on/off对应的源minimum M及已连续完成age a，残余义务为：

`R = max(ceil(M) - a, 0)`。

未来前`min(H,R)`小时固定为初态。其余startup/shutdown、ramp、normal dispatch和成本约束复用旧核心。
没有末端清空或人为补足minimum dwell；末小时切换的age=1随末态传递。
正常基线是零业务柔性、零业务恢复的counterfactual；不允许将事故availability混入normal。
输入复用既有`evaluate_chronological_flexibility`对零调用轨迹校验，保留完整边界状态、
rest、period/envelope inventory与boolean flag约束。

## 输入与候选赋值绑定

构造输入时深拷贝可变来源/request/初态；调用方保存`normal_input_identity`并显式传给build/audit。
identity覆盖完整输入、carry身份、来源索引、时钟解释、合同标识与40项本地导入依赖源码hash，
以及Python、Pyomo、highspy、numpy、scipy、PYPOWER、PyYAML和osqp版本。
独立fresh Python进程测试精确比较实际src导入闭包与显式inventory，包括package初始化文件。
期望摘要仅接受built-in lowercase 64-hex string，不能用自定义相等对象替代。
同一对象内部字典后来变化会改变identity；该摘要不是原始来源签名，不能替代正式输入验签。
源码与包版本记录也不等同于生产locked runtime、安装二进制验签或进程内monkeypatch防护。

`audit_normal_assignment`从可信输入重建canonical模型，要求全部变量的有限数值，
包括发电、开停、startup/shutdown、angles、AC/DC flows、reserve及成本segments。
变量界、构模时fixed值、全部active约束及整数性分别核验，固定开发容差为1e-6，不接受调用方放宽。
仅在这些检查通过后，将整数容差内commitment转为bool、保留原generation，
复用独立`replay_grid_chunk`再验bounds/ramp/dwell并得到terminal carry。
任何失败均不发布terminal carry；不会clip负发电或修补失败值。
审计结果仅由canonical audit内部构造，普通构造及`dataclasses.replace`重标均拒绝；不是可签名认证对象。

输出是给定赋值的normal开发见证，不证明solver来源、最优性、contingency、AC或完整网络安全。
既有`validate_chronological_dispatch`还要求事故状态；本模块不调用它来制造normal-only安全通过。
后续事故响应层须保持原事件时钟、边界状态与所需跨小时约束；其科学合同尚未注册。

## 开发验收

当前测试覆盖H=1/24/25/49、旧入口H<=24不变、on/off残余义务、fractional minimum向上取整、
非法age、功率/线路/备用/整数性反例、输入来源及身份漂移、末小时启动与下一chunk义务、
首小时ramp/startup/shutdown allowance。128组三小时binary轨迹与独立carry回放对照一致。
独立pre-seal指出结果重标、业务边界字段遗漏、expected identity自定义比较绕过、证据角色类型及依赖闭包不足。
均已加修复与反例；2026-09-16最终主线程六文件相关回归325项通过（16.19s），
其中新组件82项，包含上述normal两小时小例与既有四臂短求解小例。
独立pre-seal复核82项通过（14.06s），上述findings已闭合，限定范围无开放finding；不生成official verdict或receipt。
源码SHA256：`44a1249f1b172c07ac71b458ba79fc3817d2ae11bb9c22004e55b22b0e6ef313`。
测试SHA256：`77c16bd08854c5b9bc1b9a85fe88371fb61ecfaa1b842420c9a135f3c36d90f5`。
另从本地已有RTS-GMLC源完成H=25 build-only检查，22,275变量/28,004约束；没有求解该模型。
不宣称任何formal gate通过。

下一必要工作为连续normal执行产物与事故响应的连接、完整源输入绑定和联合验收，
再按完整协议处理training/holdout与服务closure。

只读领域核查确定下一薄层应owned fresh normal build→一次短solve→原生唯一solution→完整assignment audit，
成功后保留全部小时baseline再对active小时调用既有corrective入口。normal构模/求解不以事件schedule作为输入；
连接器可以先校验事件表身份和预算，事件响应只在normal结果验收后求解。
source_hour为1-based，而旧N1事件为zero-based half-open，显式映射`event_index=source_hour-1`，
完整保留原event seed/id/start/end；无事故小时仍保留baseline并记零grid need。
任一小时unresolved使候选不完整。逐小时corrective仍不能证明事故态跨小时ramp；跨seed共同baseline规则
与完整事故时序合同须另行注册。以上为下一开发入口，本组件尚未实现该连接器。

后续开发：该连接器已由独立`continuous_grid_candidate.py`实现，见`rq2_continuous_grid_candidate_v1.md`；
44项targeted与270项相关回归通过，独立pre-seal限定范围无开放finding。事故态跨小时合同仍待补齐。
