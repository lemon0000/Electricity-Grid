"""Adapt existing protocol fault coverage for the versioned draft graph."""
from pathlib import Path

R=Path(__file__).resolve().parents[4]
for old,new in (
    ('test_h1_registry_validation_operation_development_v5.py','test_h1_registry_validation_operation_development_v6.py'),
    ('test_h1_consumer_registry_read_development_v6.py','test_h1_consumer_registry_read_development_v7.py'),
):
    source=R/'tests'/old;target=R/'tests'/new;text=source.read_text(encoding='utf-8')
    text=text.replace('h1_historical_n0_verifier_development_v5','h1_historical_n0_verifier_development_v6')
    text=text.replace('h1_bootstrap_integration_development_v6','h1_bootstrap_integration_development_v7')
    text=text.replace('test_h1_registry_validation_operation_development_v5','test_h1_registry_validation_operation_development_v6')
    if 'registry_validation_operation' in old:
        text=text.replace('Successor5','Successor6')
        text=text.replace('open_scope=m._bind_registry_bootstrap(', 'open_scope,bind_consumer=m._bind_registry_bootstrap(')
        text=text.replace('calls=calls,contexts=contexts,', 'bind_consumer=bind_consumer,calls=calls,contexts=contexts,')
    else:
        text=text.replace('_bind_registry_bootstrap=lambda cls,method:open_scope,',
            '_bind_registry_bootstrap=lambda cls,method:(open_scope,None),')
        text=text.replace("SCHEMA='unit_Bootstrap6_consumer',FLAGS=original.FLAGS)",
            "SCHEMA='unit_Bootstrap7_consumer',FLAGS=original.FLAGS,\n        _bind_roster_registry_routes=lambda *args:(None,)*5)")
        text=text.replace("run,read,receipt,cleanup=space['_bind_registry_run']()",
            "run,read,receipt,cleanup,*foreign=space['_bind_registry_run']()")
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
print('Created two versioned protocol test drafts')
