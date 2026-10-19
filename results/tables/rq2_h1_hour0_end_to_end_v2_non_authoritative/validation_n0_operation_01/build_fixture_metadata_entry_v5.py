"""Extend the existing resolver's observation windows, preserving its helpers."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=HERE/'run_unit_entry_v4.py';new=HERE/'run_unit_entry_v5.py'
source=old.read_text();needle='    class Windows:\n'
assert source.count(needle)==1
hook='''    class Windows:
        fixture_scope_active=False

        @pytest.hookimpl(tryfirst=True,hookwrapper=True)
        def pytest_fixture_setup(self,fixturedef,request):
            # Dependencies normally finish before this hook. Dynamically
            # requested nested fixtures borrow the outer metadata window.
            if fixturedef.argname not in ('example','setup','numerical','prepared') or self.fixture_scope_active:
                yield
                return
            self.fixture_scope_active=True;reader=None
            try:
                parsed.begin_discovery_window()
                distribution_scope,reader=distribution_operation(parsed,metadata)
                with distribution_scope:
                    outcome=yield
                    outcome.get_result()
            finally:
                self.fixture_scope_active=False
                if reader is not None:
                    resolver_receipts.append(dict(scope='fixture',fixture=fixturedef.argname,
                        nodeid=request.node.nodeid,receipt=reader()))

'''
source=source.replace(needle,hook)
source=source.replace("resolver_receipts.append(dict(nodeid=item.nodeid,receipt=reader()))",
    "resolver_receipts.append(dict(scope='body',nodeid=item.nodeid,receipt=reader()))")
with new.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
old_monitor=HERE/'run_unit_bounded_v17.py';new_monitor=HERE/'run_unit_bounded_v18.py'
monitor=old_monitor.read_text();assert monitor.count('run_unit_entry_v4.py')==1
with new_monitor.open('x',encoding='utf-8',newline='\n') as stream:
    stream.write(monitor.replace('run_unit_entry_v4.py','run_unit_entry_v5.py'))
value=dict(status='DRAFT_NONAUTHORITATIVE',entry_predecessor_sha256=sha256(old.read_bytes()).hexdigest(),
    entry_sha256=sha256(new.read_bytes()).hexdigest(),monitor_predecessor_sha256=sha256(old_monitor.read_bytes()).hexdigest(),
    monitor_sha256=sha256(new_monitor.read_bytes()).hexdigest(),
    change='Original resolver now independently enters/exits for four named heavy fixture bodies; nested dynamic fixtures borrow. Test-body scope and all original parser/discovery/cleanup checks remain.',
    helper_code_changed=False,scientific_code_changed=False,formal_result=False,resource_admission=False)
out=HERE/'whole_workflow_optimization_01_non_authoritative/fixture_metadata_entry5_draft_origin_139.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(value))
