"""Resolve archived surface labels and independently check scalar baseline."""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'results/tables/asi_baseline_reproduction_v1_non_authoritative/attempt_01'
    path=folder/'report.json'; original=path.read_bytes();report=json.loads(original)
    assert hashlib.sha256(original).hexdigest()==(folder/'report.sha256').read_text()
    archive=ROOT/'data/raw/asi_trace_power/v1.0.1/upstream/asi-trace-power-v1.0.1.zip'
    with zipfile.ZipFile(archive) as z:
        def table(name):
            return pd.read_parquet(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('/data/products/'+name+'.parquet')))))
        env=table('envelope_hourly');cluster=table('envelope_cluster_hourly');surface=table('k_surface')
    good=env.good.to_numpy(bool)
    eligible=cluster.pivot(index='cluster_id',columns='t',values='curtail_idle_retained')
    keep=eligible.index[eligible.mean(axis=1)>=.02]
    cluster['workload_rebuilt']=cluster[['floor','shift','curtail','standby']].sum(axis=1)
    workload=cluster.pivot(index='cluster_id',columns='t',values='workload_rebuilt').loc[keep].sum(axis=0).to_numpy()
    workload[~good]=np.nan
    current=eligible.loc[keep].sum(axis=0).to_numpy();current[~good]=np.nan
    rows=[]
    for value in report['surface']:
        h=value['h'];alpha=value['alpha']
        refs=surface[(surface.scope=='fleet')&(surface.n==len(keep))&(surface.h==h)&np.isclose(surface.alpha,alpha)]
        assert len(refs)==1
        ref=refs.iloc[0]
        windows=np.lib.stride_tricks.sliding_window_view(workload,h).min(axis=1)
        scalar=float(np.nanmean(current)/np.nanmean(workload)*np.quantile(windows[np.isfinite(windows)],1-alpha))
        delta=value['k_mw']-float(ref.k_obs);scalar_delta=scalar-float(ref.k_const)
        assert abs(delta)<1e-10 and abs(scalar_delta)<1e-10
        assert value['n_windows']==int(ref.n_windows)
        rows.append(dict(h=h,alpha=alpha,k_rebuilt=value['k_mw'],k_archived=float(ref.k_obs),delta=delta,
                         mean_share_scalar_mw=scalar,scalar_delta=scalar_delta,scalar_ratio=scalar/value['k_mw']))
    result=dict(authority='DRAFT_NONAUTHORITATIVE',source_report_sha256=hashlib.sha256(original).hexdigest(),
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        correction='First report searched scope=top and left reference fields null; archived label is fleet. Original bytes preserved.',
        checks=rows,all_20_curves_and_scalar_baselines_match=True,mean_portfolio_workload_mw=float(np.nanmean(workload)))
    target=folder/'comparison.json'
    if target.exists(): raise FileExistsError(target)
    data=json.dumps(result,indent=2).encode();target.write_bytes(data)
    target.with_suffix('.sha256').write_text(hashlib.sha256(data).hexdigest())
    print('20 curve points, window counts and scalar baselines matched; max error',max(abs(r['delta']) for r in rows))


if __name__=='__main__':
    main()
