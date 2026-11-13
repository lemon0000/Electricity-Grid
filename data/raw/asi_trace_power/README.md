# ASI trace power（Alibaba 2026 衍生数据）

`v1.0.1/upstream/` 保存论文代码与衍生产品包，以及 GitHub v1.0.0 Release 的 `pod_hourly_agg.parquet`。未下载约 351 GB 的 Alibaba 原始 pod 表；现有聚合表与小时级产品用于复核论文的负荷重建、eligible-power 包络和持续时长—可靠性曲面。

重要边界：原始轨迹没有全站电表；MW 是功率模型重建值。`K_alpha_h` 是未干预基线上的合格负荷持续统计，不是经过任务恢复和期限核验的可交付容量。

版本注意：官方说明中的 858,816 行与实际 Release 文件不一致。已按官方 SHA-256 校验的 Parquet 实测为 1,479,356 行、17 列，详见 `v1.0.1/SOURCE_OBJECTS.json`。

数据与结果表为 CC BY-NC 4.0，并受原 Alibaba 轨迹研究/学习使用条件约束；代码为 MIT。引用原轨迹论文与 ASI 论文。
