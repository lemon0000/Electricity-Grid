"""Preserve exact draft inputs before Common source-factory integration."""
from hashlib import sha256
import json
from pathlib import Path


def main():
    directory=Path(__file__).resolve().parent
    repository=directory.parents[4]
    origin=json.loads((directory/'common_typed_graph_origin_205.json').read_text(encoding='utf-8'))
    paths=[row['target'] for row in origin['files']]
    paths.extend(('experiments/h1_bootstrap_integration_development_v7.py',
        'experiments/h1_common_registry_factory_development_v1.py',
        'tests/test_h1_common_registry_factory_development_v1.py',
        'experiments/h1_common_registry_provenance_development_v1.py',
        'experiments/h1_validation_callable_state_development_v1.py'))
    destination=directory/'common_preintegration_226_preserved_non_authoritative'
    destination.mkdir(exist_ok=False)
    records=[]
    for relative in paths:
        source=repository/relative
        data=source.read_bytes()
        saved=destination/relative
        saved.parent.mkdir(parents=True,exist_ok=True)
        with saved.open('xb') as stream:stream.write(data)
        digest=sha256(data).hexdigest()
        if sha256(saved.read_bytes()).hexdigest()!=digest or source.read_bytes()!=data:
            raise ValueError('preintegration copy/source differs')
        records.append(dict(path=source.relative_to(repository).as_posix(),
            saved=saved.relative_to(repository).as_posix(),sha256=digest,size=len(data)))
    record=dict(schema='h1_common_preintegration_226',status='DRAFT_NONAUTHORITATIVE',
        files=records,scope='Exact current typed drafts, Bootstrap7 and provenance helpers before integration.',
        source_factory_unit_terminal='source_factory_units_225/terminal.json',
        independent_findings_closed=False,common_authorized=False,
        full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
        formal_execution_ready=False,formal_run_authority=False,formal_result=False,
        resource_admission=False,new_N0_Jobs=0,real_native_calls=0)
    payload=(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    with (directory/'common_preintegration_evidence_226.json').open('xb') as stream:stream.write(payload)
    print(json.dumps(dict(files=len(records),bytes=sum(row['size'] for row in records),
        manifest_sha256=sha256(payload).hexdigest())))


if __name__=='__main__':main()
