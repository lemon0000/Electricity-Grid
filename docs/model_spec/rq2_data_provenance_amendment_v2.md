# RQ2数据Provenance修订 v2

## 修订原因

独立R3审查发现，冻结CFE v1的`summary.json`记录了旧
`derivation_module_sha256`，而当前模块SHA-256为
`27944b3ac9e30173f1b6d9708d2b8c7d15875ec73d187d2500028f4af837d1e6`。
冻结preregistration中的predecessor记录还保留了另一历史哈希。三者不一致，
因此CFE v1只能作为冻结数值predecessor，不能作为当前代码的可复现
provenance证明。

## 修订方式

- 不修改CFE v1、冻结preregistration或70-cell结果；
- 发布`rts_gmlc_hourly_cfe_deficit_250mw_v2`；
- v2记录当前config、builder和derivation module的真实SHA-256；
- v2重新生成的8,784行CSV与v1字节一致，SHA-256仍为
  `f1c483fdf20ccc1ddc8e484d719b51f5b67a497bd99fd9bd7347dc57518586a5`；
- 发布`rq2_data_readiness_v2`，逐包比较summary中的provenance SHA与当前
  live文件，并将v1记录为superseded predecessor；
- 高风险gate保持显式fail-closed，不通过弱证据布尔组合自动开启。

## 科学影响

本修订不改变CFE序列、相图cell分类或论文结果。它只修复数据包的可复现
provenance，并阻止未来代码漂移被manifest自洽检查掩盖。冻结70-cell统计
仍为R1=0、R2=0、R3=69、mixed=1、unresolved=0。
