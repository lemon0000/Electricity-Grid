# 公开边缘的连续来源窗口

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`source_window.py`复用`continuation_audit.py`的固定包manifest/member/builder核验、summary合同、
事故schedule逐行审计、训练归一化审计和同split连续chain。
调用方显式指定kind、split、zero-based起点、长度及power outage seed，并提供外部保留的config SHA256。
提取器要求整个窗口落入唯一已验证chain；拒绝缺小时、重复小时、跨split/seed及foreign block。
输出保留CSV原始字符串、完整来源chain及identity basis，不将block probability转为窗口概率。
power额外给出one-based continuous索引；workload保留原relative-hour时钟。

选取前后均核源包及config，普通源变化会被拒绝；没有源写锁或恶意ABA保证。
`window_identity`绑定完整诊断、源manifest/members、两层实现hash及Python/PyYAML版本。
返回值是可变诊断dict，不是owned输入、normal plan、事故披露或可执行episode；将来消费须对可信源重建并核对完整身份。
源窗口可用不代表恢复履约、dispatch、已注册coupling、同钟观测或样本独立。
超过1的workload_fraction原样保留；功率映射、归一化后超界策略、CFE目标和恢复参数不在此层选择。

## 开发样例与可重算入口

`experiments/export_rq2_source_window_v1.py`只create-only写新`*_non_authoritative.json`，不求解。
四个独立25小时样例在`results/tables/rq2_source_windows_v1_non_authoritative/`：

| 文件前缀 | 来源 | split | raw起点 | seed |
|---|---|---|---:|---:|
| power_training | RTS predispatch | training | 0 | 20260822 |
| power_holdout | RTS predispatch | holdout | 4440 | 20260822 |
| workload_training | Alibaba公开派生工作负载 | training | 0 | 不适用 |
| workload_holdout | Alibaba公开派生工作负载 | holdout | 821 | 不适用 |

它们是各chain起点的接口验证例，没有配对或冻结正式窗口选择。
power training链末端为4343，holdout链起点4440；原split边界4392周边被整块排除的小时不能补造。
workload holdout归一化继续引用training peak，不使用holdout重新估计。
Google同钟观测交付保持其原角色，不能与这些独立边缘窗口混称同一时钟。

从仓库根运行，重算须提供新的输出文件路径：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.export_rq2_source_window_v1 --kind power --split training --raw-start 0 --hours 25 --outage-seed 20260822 --expected-config-sha256 0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5 --output results/tables/rq2_source_windows_v1_non_authoritative/power_training_non_authoritative.json
```

其余三例按表替换kind/split/raw-start；workload省略outage-seed。
配置为既有`configs/rq2_joint_deliverability_continuation_audit_v1.DRAFT.yaml`，未修改其内容。

## 验证与余项

source window、旧continuation audit及source normal三文件64项测试通过（4.39s，exit 0），
包括真实power/workload25小时提取、holdout训练归一化及两个真实跨split排除缺口反例。
测试还覆盖重复/缺失/foreign block、seed/split错误、raw值保留、copy隔离和config pin先验拒绝。
四个create-only exporter命令均exit 0，solver_calls=0。
另从源重新提取四个窗口，逐字段比较完整保存记录均一致；exporter源码hash一致。
对已有输出再调用exporter，exit 2且原文件SHA256保持不变。`git diff --check`通过。

四个诊断文件SHA256：

- power_training：`6895d94285296ba355c5ba9526dd1f7b84109681d82dc74339d34d3059c9a024`
- power_holdout：`dbad598eec510e4dfbb5932353c97754d6918ff3c0e486a8064958c4d03bb280`
- workload_training：`7610f6bf0f60044a3fc46e577ad96b0685b4f951961af49a470756e561468df6`
- workload_holdout：`56707a574ac663c898e6a8ee03f66516c4064b38a28a43f6fb94a5cac90ad526`

下一层需将power窗口链身份、seed、source hours与normal assembly/carry显式比对，
再按已登记机制将workload转换为业务输入。此处没有注册该映射、coupling或完整恢复合同。
158 UID执行规模、真实normal assignment、训练容量与固定策略及正式科学/运行门仍开放。

独立pre-seal对最终字节复跑同范围64项通过（4.42s），限定范围无开放实质finding。
四份窗口完整来源重建、window_identity、exporter/source/audit/config hash及证据flags独立核验一致。
该反馈不是official verdict、receipt、seal或正式运行授权。
