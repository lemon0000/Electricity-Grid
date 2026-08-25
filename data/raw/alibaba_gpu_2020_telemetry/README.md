# Alibaba PAI GPU Telemetry

The ignored `v2020/upstream/` directory is populated by:

```bash
PYTHONPATH=. conda run -n compute python \
  experiments/fetch_alibaba_gpu_2020_telemetry.py
```

The source is the official `pai_sensor_table` from the Alibaba PAI GPU Cluster
Trace v2020. Archive, decompressed-member, and header SHA-256 values are frozen
in `configs/alibaba_gpu_2020_telemetry_v1.yaml`.

The metrics are lifetime averages for an instance, not a continuous time
series. `gpu_wrk_util` is expressed in percent-of-one-GPU units and may exceed
100 for workers using multiple GPUs. The table contains utilization and memory
telemetry but no electrical power measurement.
