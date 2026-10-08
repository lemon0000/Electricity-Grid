"""Root-only development example; zero native calls, no Job/worker launch."""
from dataclasses import asdict
import runpy
from pathlib import Path
from experiments import rq2_v2_normal_obligation_binding_development_v1 as m


def main():
    out=Path(__file__).resolve().parent
    prepare=runpy.run_path(str(m.ROOT/'tests/test_rq2_v2_normal_obligation_binding_development_v1.py'))['prepare']
    with m.replay.guard.solver_calls_forbidden():
        resolver=m.open_manifest()
        parent,args,catalog,item=prepare(out/'pending_parent_non_authoritative',resolver)
        try:
            context={k:v for k,v in args.items() if k not in ('resolver','job_budget')}
            context['job_budget']=asdict(args['job_budget'])
            m.io.write_new(out/'inspection_context.json',m.io.encode(context))
            value=m.bind(**args)
            raw=m.io.encode(value)
            m.io.write_new(out/'binding_v1_final.json',raw)
            assert m.inspect(out/'binding_v1_final.json',expected_sha256=m.io.digest(raw),**args)==value
            facts=dict(binding_sha256=m.io.digest(raw),binding_bytes=len(raw),normal_request_key=value['normal_request_key'],
                fresh_inspection_equal=True,solver_calls=0,worker_launches=0,job_launches=0,
                parent_status=parent.inspect().status,example_role='development_pending_input_only',
                accepted_scientific_carry=False,**m.FLAGS)
        finally:
            parent.close()
        m.io.write_new(out/'example_checks.json',m.io.encode(facts))
        print(m.io.encode(facts).decode())


if __name__=='__main__':
    main()
