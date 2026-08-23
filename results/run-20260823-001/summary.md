# Run run-20260823-001

- source_tag: run-20260823-001
- source_commit: d68bc85ee728ae4dca6d6e9790658d59dccac207
- experiment_kind: rq2-formal-batch
- status: failed
- failure_stage: entrypoint_config_kind_parse
- planned_job_count: 17
- executed_job_count: 0
- experiment_started: false
- security_certified: false
- formal_vma_published: false

标签入口在解析 `configs/experiment.yaml` 的 `kind` 时失败。Python 与 17-job batch 均未启动，未产生 `experiment.log`、`batch_manifest.json` 或任何 batch result。

该终态只记录执行入口的 operational failure；它不提供模型可行性、数学不可行性、H2、工程安全、合同能力或其他科学结论。
