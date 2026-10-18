"""Derive a bounded monitor counting only each attempt's new artifacts."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
root=HERE.parent/'validation_path_optimization_01'
source=(root/'run_bounded.py').read_text(encoding='utf-8')
start=source.index('storage_roots = [HERE]')
end=source.index('\n\n\ndef save',start)
replacement='''if len(arguments)<5 or arguments[0]!='-I':
    raise ValueError('explicit configured-entry invocation required')
launcher=(REPO/arguments[1]).resolve(strict=True)
entry=(HERE/'entry_revision_03').resolve(strict=True)
if launcher!=entry/'launch_validation.py' or not arguments[4].replace('_','').isalnum():
    raise ValueError('fixed entry and unique child attempt label required')
child_output=entry/arguments[4]
if child_output.exists():raise ValueError('fresh child attempt root required')
storage_roots=[out,child_output]
'''
source=source[:start]+replacement+source[end:]
source=source.replace("sources.update((REPO / p).resolve() for p in arguments if p.endswith('.py') and (REPO / p).is_file())",
    "sources.update(p for p in entry.iterdir() if p.is_file())")
source=source.replace("if proc is not None and proc.poll() is None:\n        proc.kill()",
    "if proc is not None and proc.poll() is None:\n        if target is not None:\n            for child in reversed(target.children(recursive=True)):\n                try: child.kill()\n                except psutil.Error: pass\n        proc.kill()")
target=root/'run_bounded_configured_entry_v1.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
print(str(target))
