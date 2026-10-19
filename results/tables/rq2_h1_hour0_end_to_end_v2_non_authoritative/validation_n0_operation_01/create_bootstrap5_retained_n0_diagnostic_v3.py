"""Prepare a fresh one-Job diagnostic with durable callback heads and early returns."""
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
source=(ROOT/'tests/test_h1_registry_validation_fresh_n0_development_v2.py').read_text(encoding='utf-8')
source=source.replace('from dataclasses import fields','from dataclasses import asdict, fields\nimport os')
source=source.replace('test_cold_bootstrap5_registered_development_true_n0_registration_and_close',
    'test_cold_bootstrap5_retained_n0_registration_and_close')
source=source.replace("    retentions=[]\n", """    # This is an external diagnostic retention record, written before callback
    # acknowledgement. A later data-only check need not invent owner heads from
    # an unretained journal suffix. Incomplete staging files are never accepted.
    retention_directory=tmp_path/'external_retention_non_authoritative'
    retention_directory.mkdir()
    retention_previous=[None]
    def persist(name,raw):
        staged=retention_directory/(name+'.staging')
        final_path=retention_directory/name
        with staged.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        staged.rename(final_path)
        assert final_path.read_bytes()==raw
    persist('declaration.json',m.encode(asdict(declaration)))
    retentions=[]
""")
source=source.replace("        return s.retain(root,before,after)", """        result=s.retain(root,before,after)
        assert result==after
        raw=m.encode(dict(sequence=len(retentions),root=str(root),before=before,after=after,
            previous_retention_sha256=retention_previous[0],
            retained_heads=dict(s.heads),diagnostic_only=True,formal_result=False))
        persist(f'{len(retentions):04d}.json',raw)
        retention_previous[0]=m.sha256(raw).hexdigest()
        return result""")
source=source.replace("        result=owner.bootstrap(registered_development=True);trace('N0_registered')", """        result=owner.bootstrap(registered_development=True)
        returned_receipt=result['N0_validation_execution_receipt']
        assert type(returned_receipt) is bytes
        persist('returned_execution_receipt.json',returned_receipt)
        persist('public_bootstrap_return.json',m.encode(dict(result,
            N0_validation_execution_receipt=json.loads(returned_receipt),
            returned_execution_receipt_sha256=m.sha256(returned_receipt).hexdigest(),
            diagnostic_return_format='JSON; exact receipt bytes saved separately')))
        trace('N0_registered')""")
start=source.index('        from experiments import h1_historical_n0_verifier_development_v1 as oracle\n')
end=source.index('        heads=retained(owner,s)\n',start)
source=source[:start]+"""        # Run the predecessor numerical oracle separately on these saved bytes;
        # it does not need to keep the live owner or rerun this synthetic Job.
"""+source[end:]
source=source.replace("            full_hour0_chain_passed=False,**m.FLAGS)",
    "            public_bootstrap_return_verified=True,predecessor_scientific_oracle_verified=False,\n"
    "            externally_persisted_retention_callbacks=len(retentions),\n"
    "            full_hour0_chain_passed=False,**m.FLAGS)")
target=ROOT/'tests/test_h1_registry_validation_retained_n0_development_v3.py'
compile(source,str(target),'exec')
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
print(str(target))
