# 共同参考请求的精确业务单位适配

日期：2026-09-19。状态：DRAFT_NONAUTHORITATIVE，独立pre-seal限定范围无开放实质finding。
实现`common_request_adapter.py`，测试`test_rq2_common_request_adapter_v1.py`。
本接口连接已选择reference请求与业务原始输入，不执行solver、不提交业务/网侧状态、不生成容量或因果证书。

## 数值与来源合同

复用business_grid既有`linear_workload_power_no_idle_offset_v1`映射及显式来源配对机制。
U采用正canonical decimal字符串，并绑定对应workload_normalization_sha256；这一绑定是机制声明，
不是从公开CPU/PDU观测识别得到的物理换算。该接口不支持非终止小数的有理数U，不近似替换它。
G及G/U则不受十进制限制，直接使用Fraction，并验证`occupancy * U == current baseline`的精确相等。
请求归一化为G/U，不除baseline，baseline=0不产生除零问题。

既有ContinuationHour检查numbers.Real，capacity_policy/aggregate_response使用Q(str)记账，
prefix_handoff有canonical Fraction编解码，因此1/3可原样进入四臂请求、债务与持久化重放。
adapter只在新的hour副本写入精确grid_request，保留CFE请求及其他来源字段；原hour的grid slot须显式为0，
以免覆盖已有独立请求。hour须为共同JOINT/shared且power_source_hour与当前reference相同。
映射与source normalization hash必须一致。另须提供审计侧owned RequestSourceAudit：
由完整normal inputs及prepared normal产物创建，严格重算normal input identity、核对prepared来源，
从prepared重新生成的current view必须等于reference所用view，随后绑定split、outage seed及当前绝对小时。
business hour的split/seed必须与该审计对象相同；不同hash/trace命名空间仍只按显式pairing声明，
不能从相同时钟推断真实来源同一性。完整normal来源及seed仅用于适配审计，不传入reference选择。

result保存原hour、原G、精确归一化请求和mapped hour，以及浮点投影/hex/精确二进制表示误差。
浮点字段仅供审计，不写入mapped hour、不改变G、不引入新的投影误差接受门。
identity复用prefix_handoff的Fraction编码后再调用网侧digest；不修改旧共享digest或旧模块。
依赖身份包含业务实现闭包、新adapter及reference selector绑定的网络/solver实现和runtime。

## 已选择请求与拒绝

接受owned ReferenceSelectionResult并重验其current input及当前执行policy身份；selected分支要求完整n+2级、
全部accepted/optimal、无错误、最后赋值的G及物理carry与所选state一致、previous/policy/selection摘要一致。
这复用已验selector的owned证据，不重新求解，也不是独立数学最优证书。

| 情形 | 输出与实际动作 |
|---|---|
| 非法U、来源小时/split/seed/normalization/基线不匹配、非共同容器、已有grid请求、错误或漂移身份 | 输入拒绝，不生成mapped hour |
| reference未完成 | unresolved，raw/normalized/mapped均为空，保留reference result identity |
| G>0且G/U<=1e-6，或旧float活动判断使其失去精确值 | unresolved，保留正raw与normalized，mapped为空 |
| 分离grid/CFE与合计请求的活动判断不一致 | unresolved，保留原CFE/request，禁止静默裁剪 |
| 合法精确映射且有效调用值不变 | mapped_exact_common_request，提供新的公共hour候选 |

不实现正请求canonicalize为0的候选例外；该例外需要另行机制声明及baseline零目标见证。
G=0也必须来自完整selected reference。未找到参考赋值时不能用0填充。
即便Q值略高于十进制1e-6，若旧业务float cutoff会把它归零，也明确停止；不改变旧阈值。

## 后续事务边界

adapter无跨小时cursor，固定U/mapping identity须由后续轨迹事务绑定，不能在中途按结果更换U。
业务prefix可以精确重放mapped hour，但自身不包含reference selection或adapter lineage；
它只能证明业务重放，不能单独证明请求来自共同reference。
后续事务必须同时持有reference result、adapter result及mapping identity，核对
`business record.current.observation.hour == mapped_hour`，再绑定各臂业务和网侧前/后态。
网侧不通过时两个实际状态均不提交；同小时只计一次来源暴露。
四臂共同raw请求的保存、CFE-only适用性及完整恢复仍由原业务合同及后续事务处理，本接口不重定义D_C。

## 验证

初批33项通过（12.26s）；增加normalization来源绑定后34项通过（12.32s），六文件219项相关回归通过（99.44s）。
独立pre-seal随后发现当时正例混用了training/seed1 reference与holdout/seed0业务输入，旧测试未覆盖来源隔离。
已新增审计侧RequestSourceAudit及split/seed硬核对，正例统一来源并补来源不匹配反例；
修复后38项targeted通过（18.06s）。同时显式加入continuous_grid_normal.py直接hash依赖及fresh-import闭包测试。
独立复核当前38项通过（21.88s），来源finding闭合，限定范围无开放实质finding；
修复后六文件223项相关回归通过（116.46s），git diff --check通过。
相关范围为adapter、reference selector、capacity policy、aggregate response、
prefix handoff和business grid，均使用`test_rq2_*_v1.py`对应入口。
覆盖G=15 MW、U=45 MW得到精确1/3，并经四臂capacity policy、债务和prefix export/import重放保持；
覆盖正小请求、阈值附近float判断、CFE活动不一致、零baseline、未完成reference、身份和来源漂移。
测试中的基线、U、期限和调用都是合成机制，不能作真实行为或经验风险估计。

targeted命令为`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_common_request_adapter_v1.py`。
测试调用已有微型reference selector（1秒/1线程），adapter本身不调用solver。
当前开发字节SHA256（非production seal）：

- source：`8ed64e2ab2a7a6216f5c972f9f2025e96be4d9126bb10efd1e3daa5433366b02`
- test：`039c618eb3fb1315ff1b344061cb52cd1f560043b5d434d8398604f81da936d4`

下一项为业务/网络小时事务及共同输入持续绑定；正式连续输入、完整恢复、训练容量、科学和执行门仍开放。


## 2026-09-20 四臂连续小时协调开发

`episode_coordinator.py`已连接单对象内存中的四臂共同请求链、固定策略、公平物理/业务初态、整窗最坏预算预检和逐小时预留。
保留各臂独立停止；末小时保留恢复债务，窗口消费完不代表完整履约。完整小时输入、候选、外层提交、已开始/未完成/未开始臂分别记录。
`hourly_transaction.py`同步区分dispatch执行异常与求解前网络输入拒绝，缺失执行结果不猜零调用。
独立pre-seal 31项episode（44.69s）及23项hourly（32.10s）通过，findings闭合；九文件323项相关回归通过（170.08s，exit 0）。
完整合同、开发hash和命令见`docs/model_spec/rq2_episode_coordinator_v1.md`；旧22/291项记录保留为此前版本证据。
下一项为完整episode证据的持久化及无solver重放，再处理跨进程唯一性/恢复；现有业务prefix不能替代reference→mapping→business→actual全链。
本组件仍为DRAFT_NONAUTHORITATIVE。完整连续输入、训练容量与四臂策略绑定、正式规模、恢复/right-censoring及科学/正式运行门未关闭。
所有初态与未识别业务参数保持机制声明；没有新增真实运行观测、正式结果、容量/安全认证或formal-run authority。
