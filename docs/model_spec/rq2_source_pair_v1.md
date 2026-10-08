# 独立来源窗口的显式配对与业务请求暂存

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`source_pair.py`连接已验证source windows、workload projection与旧完整CFE请求公式。
`PairDeclaration`显式绑定同一split下两个独立窗口的起点/长度、事故seed、两项外部window identity、
config hash、MW基准、数值精度和既有四档CFE target。
`declared_relative_offset_pairing_v1`只声明第i个电力小时对应第i个工作负载小时，属于机制假设。
这里没有联合概率、经验同钟、样本权重、正式支持选择或已注册coupling。

## 来源、功率与时钟

两个窗口分别从各自固定包重建，比较外部身份后才生成逐行记录。
workload normalization身份绑定源trace/训练peak依据、包manifest、投影规则/精度及线性无idle-offset功率规则/MW基准。
记录保存完整原始行、量化误差账、raw CFE浮点投影误差及hex。
投影后的occupancy和baseline仍满足CommonRequestMapping的精确十进制等式。
该baseline是机制功率，不是设备或任务实际功率观测。

power raw k映射business power_source_hour=k+1；workload raw j独立映射workload_source_hour=j+1。
两者各自前边界为k和j；首个动作前边界可以为0。原始索引完整保留，不把索引同值当作同钟。
此映射满足现有common cursor要求workload首个动作索引>=1，避免原始小时0无法建立前边界。

## 请求与未解决小时

复用旧`raw_cfe_request`：`max(alpha-(1-cfe_call_fraction),0)/alpha`，既有四档alpha为0.5/0.7/0.85/1。
不乘workload、不按available flexibility截断；CFE请求超过baseline时也原样保留，后续业务合同决定能否服务。
本层不构造恢复headroom、call limit、deadline、period或策略动作。

ContinuationHour暂存为JOINT/shared共同输入，`grid_request=0`明确是待共同reference填写的空槽，不是观测到零网络请求。
只有所有小时projection可表示时，顶层hours给出完整连续列表；任一小时unresolved则顶层hours=null，
逐行rows及原始超界/表示错误全部保留。rows中的可表示小时是诊断，不构成越过缺口的可执行后缀。
返回对象是可变诊断dict，不是owned publication/cursor；消费端仍需重建来源并绑定pair_identity。
没有normal赋值、actual dispatch或完整episode；`executable_episode_input=false`。

## 可重算开发例

两个create-only YAML声明：

- `configs/rq2_source_pair_training_example_v1.DRAFT.yaml`：training power0..24/workload0..24，alpha0.7、250MW、12dp。
- `configs/rq2_source_pair_holdout_overload_example_v1.DRAFT.yaml`：holdout power4440..4464/workload1190..1214，相同机制参数。

前者用于完整暂存正例，后者特意覆盖未解决输入的拒绝路径；不是正式代表样本或结果选择。
holdout例包含5个raw>1小时1198、1206、1207、1208、1209，完整25行保留且hours=null。
全公开holdout共有6个raw>1小时，另一个1267不在本例中。

命令从仓库根执行，已有输出不可覆盖；重算需更换新输出路径：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.export_rq2_source_pair_v1 --declaration configs/rq2_source_pair_training_example_v1.DRAFT.yaml --expected-declaration-sha256 e4d78a3c4e060f493a8d238e4122a649c7a610cde8c0b2cc882fa091831e5019 --output results/tables/rq2_source_pairs_v1_non_authoritative/training_example_non_authoritative.json
D:/Miniconda3/envs/compute/python.exe -B -m experiments.export_rq2_source_pair_v1 --declaration configs/rq2_source_pair_holdout_overload_example_v1.DRAFT.yaml --expected-declaration-sha256 942ab1d86fc8a7bba8407ad37ca21c919e933032966a34fb4f70b79a60849323 --output results/tables/rq2_source_pairs_v1_non_authoritative/holdout_overload_example_non_authoritative.json
```

exporter校验外部声明hash，拒绝重复YAML key，通过原构造器校验全部字段，再写新诊断文件。
窗口原始数据、旧冻结协议、旧结果及已有阶段记录均不修改。

## 验收范围与下一项

测试覆盖两个独立时钟、完整CFE超过baseline仍保留、两个外部pin、typed参数、超界/正数投零的整窗unresolved，
真实training25小时的四档CFE公式及真实holdout五个超界小时不丢弃。
本层不重新解释旧CFE公式，不替代未注册的连续科学合同。

最终五文件114项相关回归通过（17.06s，exit 0），含本层17项及projection/source window/common request/continuation audit。
两个exporter命令exit 0；逐份从原始包重建完整pair，与落盘记录逐字段相等，声明/exporter hash核验一致。
`git diff --check`通过。
开发JSON SHA256：

- training例：`e3c849037bcd1d1ac465ab3b752c90b64633c71f1b40d5406c482f46135671f4`
- holdout超界例：`c855919d33568c6bdd34ceca6f09cc710648f91951a3bdcbdacdc0adc8bd8817`

独立pre-seal三文件54项通过（5.46s），限定范围无开放实质finding。
两份JSON、pair_identity、声明/exporter及六个实现hash独立核对匹配；完整/未解决窗口、CFE和证据flags复核一致。
114项broad采用主线程证据。此反馈不构成official verdict、seal或运行授权。

下一项是将完整pair的动态baseline与normal request建立不可错配的来源绑定，再连接normal赋值和current输入。
旧250MW常量构模例不能替代该动态baseline；真实normal赋值、158 UID规模执行、训练容量、恢复/删失及正式coupling门仍开放。
