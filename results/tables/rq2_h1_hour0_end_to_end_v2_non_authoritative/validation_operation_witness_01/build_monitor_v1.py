"""Create a scoped development monitor; preserve predecessor monitor bytes."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
template=HERE.parent/'validation_selector_incremental_01/run_bounded.py'
source=template.read_text(encoding='utf-8')
source=source.replace('storage_roots = [HERE]','storage_roots = [out]')
start=source.index('sources = {')
end=source.index('\nsources.update',start)
source=source[:start]+"sources = {Path(__file__).resolve(), REPO / 'experiments/h1_operation_historical_witness_development_v1.py', REPO / 'tests/test_h1_operation_historical_witness_development_v1.py'}"+source[end:]
with (HERE/'run_bounded.py').open('x',encoding='utf-8') as stream:stream.write(source)
print(str(HERE/'run_bounded.py'))
