"""Bounded independent reconstruction of pinned ASI derived baseline."""
from pathlib import Path
import io
import zipfile
import json
import hashlib
import time
import tracemalloc
import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[1]


def main():
    start=time.perf_counter();tracemalloc.start()
    out=ROOT/'results/tables/asi_baseline_reproduction_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True,exist_ok=False)
    archive=ROOT/'data/raw/asi_trace_power/v1.0.1/upstream/asi-trace-power-v1.0.1.zip'
    aggregate=archive.parent/'pod_hourly_agg.parquet'
    deps=[archive,aggregate,Path(__file__),ROOT/'docs/plan/asi_baseline_reproduction_v1_contract.md']
    report=dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in deps},stages={})
    def check():
        if time.perf_counter()-start>90: raise TimeoutError('90s budget')
    try:
        with zipfile.ZipFile(archive) as z:
            def read(suffix):
                n=next(n for n in z.namelist() if n.endswith('/'+suffix))
                return z.read(n)
            fleet=pd.read_parquet(io.BytesIO(read('data/products/fleet_hourly_power.parquet')))
            env=pd.read_parquet(io.BytesIO(read('data/products/envelope_hourly.parquet')))
            clusters=pd.read_parquet(io.BytesIO(read('data/products/envelope_cluster_hourly.parquet')))
            surface=pd.read_parquet(io.BytesIO(read('data/products/k_surface.parquet')))
            headline=json.loads(read('results/headline.json'))
            cfg=yaml.safe_load(read('configs/power_curves.yaml'))
            report['zip_members_used']=['data/products/'+s for s in ['fleet_hourly_power.parquet','envelope_hourly.parquet','envelope_cluster_hourly.parquet','k_surface.parquet']]
        assert np.array_equal(env.t,np.arange(len(env)))
        assert np.array_equal(fleet.t,env.t)
        good=env.good.to_numpy(dtype=bool)
        report['time']=dict(grid_hours=len(env),good_hours=int(good.sum()),have_hours=int(fleet.have.sum()),
            bad_t=env.t[~good].tolist(),have_equals_good=bool(np.array_equal(fleet.have,good)))
        matrix=clusters.pivot(index='cluster_id',columns='t',values='curtail_idle_retained').sort_index(axis=1)
        means=matrix.mean(axis=1)
        keep=means.index[means>=0.02]
        series=matrix.loc[keep].sum(axis=0).to_numpy();series[~good]=np.nan
        report['portfolio']=dict(all_clusters=len(matrix),kept_clusters=len(keep),kept_ids=list(keep),mean_mw=float(np.nanmean(series)))
        work=clusters.pivot(index='cluster_id',columns='t',values='workload') if 'workload' in clusters else None
        # Cluster product has no workload column; compare observed K directly.
        values=[]
        for h in (1,2,4,8,24):
            mins=np.lib.stride_tricks.sliding_window_view(series,h).min(axis=1)
            mins=mins[np.isfinite(mins)]
            for alpha in (.5,.9,.95,.99):
                k=float(np.quantile(mins,1-alpha))
                rows=surface[(surface.scope=='top')&(surface.n==len(keep))&(surface.h==h)&np.isclose(surface.alpha,alpha)]
                reference=float(rows.iloc[0].k_obs) if len(rows)==1 else None
                values.append(dict(h=h,alpha=alpha,k_mw=k,n_windows=len(mins),
                    archived_k_mw=reference,delta=None if reference is None else k-reference,
                    empirical_coverage=float(np.mean(mins>=k))))
        report['surface']=values
        report['power_boundaries']={key:float(env.loc[good,col].mean()) for key,col in [('attributed','curtail_attributed'),('idle_retained','curtail_idle_retained'),('node_sleep','curtail_node_sleep')]}
        report['power_boundary_deltas']={key:value-headline['curtail_mw_'+key]['mean'] for key,value in report['power_boundaries'].items()}
        report['stages']['derived_seconds']=time.perf_counter()-start
        check()
        pod=pd.read_parquet(aggregate)
        positive=pod.gpu_hours>0
        report['aggregate']=dict(rows=len(pod),positive_gpu_hours_rows=int(positive.sum()),zero_gpu_hours_rows=int((pod.gpu_hours==0).sum()),
            cluster_count=int(pod.cluster_id.nunique()),columns=list(pod.columns))
        pod=pod.loc[positive].copy()
        t=(pod.day.astype(int)*24+pod.hour.astype(int)).to_numpy()
        report['aggregate']['t_min']=int(t.min());report['aggregate']['t_max']=int(t.max())
        # Central power formula independently transcribed from documented knots.
        phi=cfg['idle_frac']['base'];tdp=[]
        for spec in pod.gpu_spec_public:
            v=cfg['gpu_tdp_w'].get(spec)
            if v is None: v=sum(cfg['xpu_tdp_range_w'])/2 if str(spec).startswith('XPU') else cfg['default_tdp_w']
            tdp.append(v['base'] if isinstance(v,dict) else v)
        tdp=np.asarray(tdp);active=np.zeros(len(pod))
        fam=cfg['curve_families']['anchored'];jt=pod.job_type_public.to_numpy()
        stats=pod[['S0','S25','S50','S75']].to_numpy()
        for kind in np.unique(jt):
            mask=jt==kind;kv=np.asarray(fam.get(kind,fam['default']))
            slopes=np.diff(kv)/.25;coeff=np.r_[slopes[0],np.diff(slopes)]
            active[mask]=stats[mask]@coeff+pod.gpu_hours_null_util.to_numpy()[mask]*cfg['null_util_g']['base']
            if kind=='online_inference':
                c0=max(0,(cfg['online_floor_frac']['base']-phi)/(1-phi))
                active[mask]=c0*pod.gpu_hours.to_numpy()[mask]+max(0,1-c0/kv[-1])*active[mask]
        mask=(pod.priority_class.to_numpy()=='LP')&(pod.state_public.to_numpy()!='Standby')
        energy=tdp*(1-phi)*active*mask/1e6
        rec=np.bincount(t,weights=energy,minlength=len(env))
        assert len(rec)==len(env)
        diff=rec-env.curtail_idle_retained.to_numpy()
        report['reconstruction']=dict(positive_rows_used=len(pod),mean_mw=float(rec[good].mean()),
            max_abs_error_mw=float(np.max(np.abs(diff))),mean_abs_error_mw=float(np.mean(np.abs(diff))),
            matches_archived_hourly=bool(np.allclose(rec,env.curtail_idle_retained,rtol=1e-9,atol=1e-10)))
        check();report['status']='completed'
        pd.DataFrame(values).to_csv(out/'surface.csv',index=False)
    except Exception as exc:
        report['status']='failed';report['error']=repr(exc);raise
    finally:
        report['wall_seconds']=time.perf_counter()-start
        report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        data=json.dumps(report,indent=2).encode();(out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest())
        assert len(data)<5*1024*1024
        assert json.loads((out/'report.json').read_bytes())['status']==report['status']
        print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
