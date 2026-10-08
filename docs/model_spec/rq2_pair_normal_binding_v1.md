# 配对动态baseline与normal输入绑定

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`pair_normal_binding.bind_pair_normal`接受独立expected pair/assembly身份，重建完整配对，
在任何RTS来源加载前拒绝unresolved pair。随后复制调用方assembly为私有快照，
复用power_normal_binding检查split、seed、trajectory、原始/continuous小时、timestamp、系统负荷与RTS来源manifest。
对每个小时进一步核验：

`normal.request.dc_requested_mw == paired projected MW == Fraction(str(occupancy))*Fraction(U)`。

校验使用精确十进制等式，不用1e-6容差掩盖baseline错配。
供给侧系统负荷与DC业务baseline分别核验，不混加原始system_load。
常量250MW例、小时错位、错误occupancy或部分窗口均不能替代完整动态baseline。
函数不修改调用方输入，返回的只是身份及对应诊断，不发布normal assignment或执行cursor。

## 真实H=25开发构模

`experiments/audit_rq2_pair_normal_build_v1.py`复用已哈希的normal机制声明和完整pair声明。
它从旧声明保留POI、系统负荷、物理/连接上限、零业务normal包络及全部显式初态，
只把新request的dc_requested_mw显式设为pair的逐小时投影功率；原request及其恒定baseline保存于旧文件，
新产物另存original_dc_requested_mw。carry按配对来源声明新的身份，物理状态仍是此前显式机制例。
这不是实际观测或旧运行checkpoint恢复；初态全关热机并未被证明为可行前序网络状态。
CFE请求不进入normal零业务反事实，target不改变这组normal baseline值。

runner有两个明确模式：

- derive：生成候选assembly身份与完整输入，external_assembly_identity_verified=false、model_builds=0、binding=null。
- verify：必须提供外部保留的expected assembly identity；从源重新组装、核验pair/normal对应后才构建模型。

两种模式均不调用solver、不提供可行赋值或正式门；输出只允许create-only新`*_non_authoritative.json`。
前者不是后者的验收替代物。

从仓库根执行，重算须给新的输出文件路径：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.audit_rq2_pair_normal_build_v1 --mode derive --normal-declaration results/tables/rq2_continuous_source_scale_audit_v1_non_authoritative/build_h25_source_bound_non_authoritative.json --expected-normal-declaration-sha256 ebb6b1d33a4742325e92f93550c0799bd1f28c0ca70adde870479f89b0d8070e --pair-declaration configs/rq2_source_pair_training_example_v1.DRAFT.yaml --expected-pair-declaration-sha256 e4d78a3c4e060f493a8d238e4122a649c7a610cde8c0b2cc882fa091831e5019 --expected-pair-identity d4b56260e8468f0cb7cc93b5b1416d067b9444a920a1576b0255c7eaff8b5c4f --source-root data/raw/rts_gmlc/v0.2.3/upstream --output results/tables/rq2_source_pairs_v1_non_authoritative/normal_dynamic_derived_non_authoritative.json
```

verify使用相同输入参数，改为`--mode verify`，增加
`--expected-assembly-identity 626f7dbe49772302d35da13bb05f2ffb69f1f599e35310484177c00711b32e7a`，
输出`normal_dynamic_verified_non_authoritative.json`。
验证产物绑定完整变更后request/initial/carry、pair声明/身份、power与动态baseline对应、model计数、
既有normal依赖及新增reader/adapter/binder/count模块实际源码hash。

## 验证范围和后续

反例覆盖旧常量baseline、细小不等式、缺小时、小时偏移、occupancy与MW不相符、错误外部pair身份，
未解决配对在network-source前拒绝，以及源码核对期间调用方原始字典变更不污染私有快照。
所有既有状态、包络和电网约束都由原normal验证器负责，不新增放宽路径。

最终五文件152项相关回归通过（17.84s，exit 0），其中本层11项；包含derive/verify外部pin模式互斥反例。
真实derive与verify命令均exit 0，验证构模为22,275 variables / 28,004 constraints，solver_calls=0。
两阶段request/initial/carry完全一致；动态baseline与pair逐行精确相符，原250MW声明另存且不改。
该首25小时例的baseline范围0.0093335315–0.02631222675 MW，属于显式线性机制与所选源窗口输出，
没有证明该映射是实际功率标定、具有代表性或满足CFE/业务履约。正式样本支持尚未选择。
落盘后核模式/外部pin、动态逐小时等式、binding身份、runner hash及原声明保留，断言通过；diff检查通过。

开发产物SHA256：

- derived：`eb46d60fed3c3ef9a2d4824c7aafdc013bbe680689fdb73b83e3ead16ad606f0`
- verified：`8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d`
- pair_normal_binding源码：`bfda25bee227772902ce8eeb29dcf657d3949989d6fe94e239b63f242dec7c10`
- 本层测试：`e61a093af654cadbae2d97f832b3f86c86dbc3102fc8c2b86b09de3cb158151b`
- audit_rq2_pair_normal_build_v1源码：`9026ed32d18537edb12ae79e0cb24ec7a44736e6146027040dd196b07837ceeb`

独立pre-seal限定范围无开放实质finding；两阶段身份、完整输入、baseline等式、模式flags与最终产物hash复核一致。
独立三文件44项通过（4.33s）对应新增两项CLI模式测试之前的测试库存，核心实现字节未变；
最终两项及完整152项由主线程回归覆盖，reviewer最终只读核对当前runner/core/test字节。
该反馈不构成official verdict、seal或运行授权。

下一项是该动态normal输入的实际赋值见证与current输入连接；25小时真实网络仍超出既有短预算变量上限，
158 UID选择器也超出单selector调用上限。需要单独的规模执行合同，不能直接把旧开发预算改大。
正式mapping/coupling、训练容量、完整恢复/right-censoring与科学/运行门仍开放。
