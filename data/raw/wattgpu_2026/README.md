# WattGPU Power Reference

The ignored `v1/upstream/` directory is populated by:

```bash
PYTHONPATH=. conda run -n compute python \
  experiments/fetch_wattgpu_power_reference.py
```

The source commit, Apache-2.0 license, object sizes, and SHA-256 values are
frozen in `configs/wattgpu_power_reference_v1.yaml`.

The retained subset contains LLM inference measurements on heterogeneous
NVIDIA GPUs. Tesla T4 is an exact hardware-name overlap with the Alibaba PAI
trace. V100 references are not treated as exact because the Alibaba labels do
not establish the same memory variant and form factor. The datasets share no
job identity or clock, so this source does not by itself define PAI job power.
