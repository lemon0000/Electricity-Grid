"""Keep reviewed monitor16 behavior, bind only the new diagnostic entry4."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=(HERE/'run_unit_bounded_v16.py').read_text(encoding='utf-8')
assert source.count("HERE/'run_unit_entry_v3.py'")==1
source=source.replace("HERE/'run_unit_entry_v3.py'","HERE/'run_unit_entry_v4.py'")
with (HERE/'run_unit_bounded_v17.py').open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
print(HERE/'run_unit_bounded_v17.py')
