# 工作负载到功率接口的显式数值投影

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

## 仓库证据与实际阻碍

旧`src/scenarios/rq2_joint_deliverability.py::build_pair_scenario`用`min(raw_workload_fraction,1)`形成occupancy，
并沿用完整CFE deficit `max(alpha-(1-cfe_call_fraction),0)/alpha`。
旧合同继续保留；连续版本不能自动继承clip、24小时边界或配对概率。
既有`CommonRequestMapping`采用显式`linear_workload_power_no_idle_offset_v1`机制，要求
`Fraction(str(occupancy))*Fraction(normalized_unit_mw)==Fraction(str(dc_baseline_mw))`，不能靠浮点近似放行。

实际固定Alibaba包共有training816小时、holdout816小时。raw decimal→float改变了training815个及holdout816个源十进制值。
以250MW为声明基准，普通`float(raw)*250`在training599个、holdout的810个in-range小时中592个不能满足上述精确恒等式。
若先将float的str表示转回有理数、精确乘250再投回float，则分别有553/543个不匹配。
两种构造不同，诊断分别保存公式和计数；不能混称为同一种直接浮点乘法。
这是数值表示冲突，不是物理服务失败；它不证明误差大，也不授权放宽原验证器。
另有holdout6小时原始fraction>1，属于待定映射合同，不能用舍入把它们压入[0,1]。

## 新增开发接口

`workload_projection.project_workload_power`要求原始非负十进制字符串、canonical正十进制MW基准及显式decimal_places（1..12）。
用Fraction精确执行half-even，量化误差逐行保留为有符号numerator/denominator，最大绝对误差为`0.5*10^-decimal_places`。
随后要求occupancy与MW数值的`str(float)`投影精确等于量化后的有理数及其功率乘积，才返回`projected`。
MW单位语法与现有CommonRequestMapping一致；raw字符串不作格式归一化。

下列情形保持unresolved，两个可消费数值均为null：

- raw>1：在任何舍入前拒绝，原值保留，需单独超界合同；
- 正源值被量化为0；
- 浮点投影溢出/非有限；
- occupancy或MW不能满足精确十进制接口恒等式。

投影不是业务拒绝动作、永久任务损失或功率观测；不启动债务，不产生风险分母。
本层不改变CFE公式，也不把CFE请求乘以occupancy；CFE及业务/恢复映射仍需完整协议明确。
小幅量化可影响下游headroom及阈值附近行为，因此正式精度也必须结果前登记，不能因某个精度使结果有利而选择它。

## 全源开发诊断

`experiments/audit_rq2_workload_projection_v1.py`复用固定包校验和continuation归一化核查。
源值逐行保留；报告绑定config、包manifest/members、projection/audit/runner源码和Python/PyYAML版本。
显式开发例为250MW、12 decimal places，未登记为正式值，未根据solver或服务结果选择。

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.audit_rq2_workload_projection_v1 --normalized-unit-mw 250 --decimal-places 12 --expected-config-sha256 0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5 --output results/tables/rq2_source_windows_v1_non_authoritative/workload_projection_250mw_12dp_checked_non_authoritative.json
```

重算需提供新的`*_non_authoritative.json`路径；已有文件不能覆盖。
原`workload_projection_250mw_12dp_non_authoritative.json`保留为两种乘法计数尚未分开标注的中间开发记录，
最终证据使用上面的checked文件；旧记录不能据其旧字段名解释为普通浮点乘法计数。
此例training816小时、holdout810小时成功投影，6个holdout超界小时unresolved。
范围内逐小时满足精确功率等式，归一化量化误差不超过5e-13，换算到250MW不超过1.25e-10 MW。
这是纯数值误差界，不是模型误差、功率映射误差或工程安全余量。
全部窗口和原始公开交付不变；没有新增观测，也没有把6小时从正式样本中删除。

## 验证与剩余工作

测试包含手算half-even正负舍入方向、0/1、超界先拒绝、正数舍入0、非法参数、非canonical单位、
不满足精确功率等式及溢出。独立Decimal/ROUND_HALF_EVEN高精度oracle核对全部1632行，
逐行比较数值、误差账、功率乘积及unresolved值保留。
独立预审提出的MW基准尾随零与CommonRequestMapping不兼容问题已修复并加入反例。

最终四文件97项相关回归通过（14.36s，exit 0），其中本层19项，覆盖现有CommonRequestMapping及来源链。
从当前源重跑audit并逐字段比较最终checked JSON，完整相等；`git diff --check`通过。
最终JSON SHA256：`9c1dfb9c82e4c4b45db84c01c70198418295fec11405b53f959c0ef32b3b6f38`。

开发源码SHA256：

- workload_projection：`59bda5b0aa11b38c8e73b5092d11ce464d927ba73c01b1a017f65e59d1e25474`
- test_rq2_workload_projection_v1：`b7b1cc352a678f1dd1bbf8da1d06805c53102087c953b51c36eabc9d63190fc0`
- audit_rq2_workload_projection_v1：`02e35a36f039147943f46d228f77a5325bc18ed1b6df3d6c82ab82593eb26ac9`

独立pre-seal最终19项通过（0.22s），canonical单位与计数命名findings闭合，限定范围无开放实质finding。
reviewer逐行独立复算两类计数、精确功率等式、signed error/半量化步长界及6项超界null/无clip均一致；
最终JSON和内嵌runner/projection/source-audit哈希匹配。97项broad采用主线程证据，未宣称独立重跑。
此反馈不构成official verdict、seal或正式运行授权。

下一项仍是将投影声明、来源归一化身份、CFE请求与单个显式coupling合同接到业务输入；
正式raw>1处理、coupling支持/权重、deadline/会计期/恢复与删失、真实normal赋值和158 UID执行规模仍未关闭。
