# 电力窗口与continuous normal的来源对应

日期：2026-09-20。状态：DRAFT_NONAUTHORITATIVE。

`power_normal_binding.py`把已有source_normal与source_window连起来：调用方显式提供expected assembly、
window、config三项身份，先从当前固定源重建normal输入及power窗口，再核对：

- carry的split、outage_seed和trajectory_id须分别等于窗口split、seed及已审chain_id；
- raw zero-based与continuous one-based索引、窗口长度、incoming边界和timestamp逐项对应；
- power包已验summary里的grid_source_manifest须等于normal的RTS源manifest；
- 每小时CSV system_load_mw与normal request的nodal load总和在1e-6 MW内一致。

1e-6沿用normal开发数值容差，不是放宽物理安全门。检查的是既有系统负荷，不把DC需求混入该总和。
输出身份绑定两端来源身份、索引及三层适配源码hash；报告仅是对应诊断，没有可执行cursor。
它核验的是固定benchmark来源的一致性，不认证初态历史/前序网络可行性、normal assignment、事故dispatch、
业务功率映射或coupling。naive_source_labelled_utc仍是显式时钟解释，不变成真实UTC来源认证。

## 真实H=25开发例

runner `experiments/audit_rq2_power_normal_binding_v1.py`读取外部hash指定的完整normal构模声明，
将其中的request/initial作为显式机制输入；从power窗口声明新的carry身份，保留原carry身份及全部物理状态。
此动作不属于checkpoint恢复，不把原全关热机初态升级为已观察或已可行状态。
原始声明文件、窗口和之前全部构模产物均不修改。

首次派生记录`power_normal_binding_non_authoritative.json`仅用于得到待核的assembly身份。
预审后runner要求独立提供该身份，最终记录为
`results/tables/rq2_source_windows_v1_non_authoritative/power_normal_binding_verified_non_authoritative.json`。

可重算命令（输出须换成新`*_non_authoritative.json`路径）：

```powershell
D:/Miniconda3/envs/compute/python.exe -B -m experiments.audit_rq2_power_normal_binding_v1 --declaration results/tables/rq2_continuous_source_scale_audit_v1_non_authoritative/build_h25_source_bound_non_authoritative.json --expected-declaration-sha256 ebb6b1d33a4742325e92f93550c0799bd1f28c0ca70adde870479f89b0d8070e --source-root data/raw/rts_gmlc/v0.2.3/upstream --split training --raw-start 0 --hours 25 --outage-seed 20260822 --expected-window-identity b67411c0a354fde54f61ebb922496d260ccbf4cfe0045567278146673277ec62 --expected-assembly-identity 8b778050b729e949d7d0b0436a7144f6f703b61d150341dcad5d4c1142b8b618 --expected-config-sha256 0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5 --output results/tables/rq2_source_windows_v1_non_authoritative/power_normal_binding_verified_non_authoritative.json
```

窗口为training/seed20260822/raw0..24，incoming边界0，continuous1..25。
该来源对应例不是正式样本选择，也没有用新seed重求normal或进行事故响应。
来源重读不提供并发写锁/恶意ABA保证。后续代码或来源改变使身份变化时，必须保留原记录并重新审查新的声明。

## 验证范围

反例覆盖split/seed/trajectory错配、raw与continuous索引、timestamp、负荷偏差/非有限值、
package grid来源错配、独立expected身份错误、自定义SHA256比较对象及runner外部pin传递。
声明JSON回读验证request/initial完全保持、原文件对象不改，carry身份变更仍是机制声明。
真实两端来源复核由上述命令完成，不运行solver或生成normal assignment。

最终五文件相关回归164项通过（18.81s，exit 0），包含18项本层测试及source window、source normal、
continuous normal和continuation audit回归。真实25小时命令exit 0，最大系统负荷差0.0 MW。
落盘后核对外部assembly pin、binding identity、runner/core/两端适配源码hash、小时映射与非认证flags均通过；
`git diff --check`通过。

最终JSON SHA256：`30918806d4e7ed64af3a79e505d78fe9f219ed2d75347e9699eefbcb365220e5`。
开发源码SHA256：

- power_normal_binding：`ac9394238ff0749a36832a60edf7be4dd77423d5175be3ecc68b774721b1e366`
- test_rq2_power_normal_binding_v1：`4adcd82f670c6ef80dc54e4d7f2d4e343b89bf01458006ca0b23cb78e9e09e88`
- audit_rq2_power_normal_binding_v1：`5d285883ebb7c5021f8069b1d04887519c6d018b5af72ed604b74fb737331c79`

独立pre-seal最终18项targeted通过（1.56s），外部pin finding闭合，限定范围无开放实质代码finding。
产物/core/test/runner hash独立核对一致，diff检查通过。该反馈不是official verdict、seal或运行授权。

下一项仍需登记并实现workload→业务功率映射及coupling，连接合法normal赋值与实际披露；
158 UID执行规模、训练容量与固定策略、完整恢复/right-censoring和正式科学/运行门保持开放。
