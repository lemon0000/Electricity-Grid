"""One saved H3 batch; original join/projection identity-bound reconstruction."""
from hashlib import sha256
from pathlib import Path
import sys
from types import ModuleType

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'rq2_h1_constructor_inspection_v2_non_authoritative'
sys.path.insert(0,str(PRIOR))
original=PRIOR/'oracle_saved_v1.py'
text=original.read_text(encoding='utf-8')
substitutions=(
    ('from experiments import h1_phase_exact_source_batch_development_v2 as new',
     'from experiments import h1_phase_exact_source_batch_development_v3 as new'),
    ('from experiments import h1_constructor_source_batch_validation_development_v1 as validator',
     'from experiments import h1_constructor_source_batch_validation_development_v2 as validator'),
    ("oracle_scope='saved_raw_science_plus_original_join_projection_and_fresh_synthetic_source'",
     "oracle_scope='saved_identity_bound_reconstruction_using_original_join_projection'"),
)
for old,new in substitutions:
    if text.count(old)!=1:raise ValueError('exact one saved harness substitution required')
    text=text.replace(old,new)
text=text.replace('old_saved_science_bytes_equal','saved_identity_bound_science_reconstruction_equal')
harness=ModuleType('source_v3_saved_harness')
harness.__file__=str(original)
exec(compile(text,str(original)+' [declared v3 substitutions]','exec'),harness.__dict__)
harness.HERE=HERE
original_save=harness.core.save


def save(root,name,value):
    if name in ('oracle_request.json','oracle_terminal.json'):
        value=dict(value,old_raw_science_bytes_directly_read=False,
            independent_scientific_implementation=False,shared_saved_manifest_pin_resolver=True,
            one_field_packet_projection_standin=True,original_harness_sha256=sha256(original.read_bytes()).hexdigest(),
            declared_source_substitutions=list(substitutions),
            arbitrarily_reflective_mutation_or_unobserved_ABA_covered=False)
    original_save(root,name,value)


harness.core.save=save
if __name__=='__main__':raise SystemExit(harness.main())
