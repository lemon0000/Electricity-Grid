"""Change only provisional successor error reporting; no arbitrary exception repr."""
from pathlib import Path
import re

R=Path(__file__).resolve().parents[4]
for name in ('h1_bootstrap_integration_development_v7.py','h1_historical_n0_verifier_development_v6.py'):
    path=R/'experiments'/name;text=path.read_text(encoding='utf-8')
    for value in ('error','failure','cleanup'):
        text=text.replace('repr('+value+')','_failure_description('+value+')')
    text=text.replace('BaseException.add_note(','_note_failure(')
    text=re.sub(r"(\w+(?:\[\d+\])?)\.add_note\(([^\n]+)\)",r'_note_failure(\1,\2)',text)
    # The safe descriptor cannot fail due to user formatting; no typename fallback.
    text=text.replace("try:row['failure']=_failure_description(error)\n            except BaseException:row['failure']='<'+type(error).__name__+': repr failed>'",
        "row['failure']=_failure_description(error)")
    path.write_text(text,encoding='utf-8',newline='\n')
path=R/'experiments/h1_group_execution_roster_development_v5.py'
text=path.read_text(encoding='utf-8').replace('repr(failure)','bootstrap._failure_description(failure)')
text=text.replace('BaseException.add_note(','bootstrap._note_failure(')
text=text.replace("'_run_roster_registry_read','_read_roster_registry_receipts','_cleanup_roster_registry_records',",
    "'_run_roster_registry_read','_read_roster_registry_receipts','_cleanup_roster_registry_records',\n            '_failure_description','_note_failure',")
path.write_text(text,encoding='utf-8',newline='\n')
print('Updated three provisional successor failure reporters')
