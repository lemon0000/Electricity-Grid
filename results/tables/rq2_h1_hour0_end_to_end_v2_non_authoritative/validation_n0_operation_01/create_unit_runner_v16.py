"""Fresh diagnostic monitor successor: account for entries without following reparse routes."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'run_unit_bounded_v15.py';target=HERE/'run_unit_bounded_v16.py'
text=source.read_text(encoding='utf-8')
before='''            def failed(error):failures.append(dict(path=error.filename,error=repr(error)))
            for directory,_,names in os.walk(root,onerror=failed,followlinks=False):
                for name in names:
                    path=Path(directory)/name
                    try:total+=path.stat(follow_symlinks=False).st_size
                    except OSError as error:failures.append(dict(path=str(path),error=repr(error)))'''
after='''            pending=[root]
            while pending:
                directory=pending.pop()
                try:
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            try:
                                info=entry.stat(follow_symlinks=False)
                                if stat.S_ISDIR(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400:
                                    pending.append(Path(entry.path))
                                else:total+=info.st_size
                            except OSError as error:failures.append(dict(path=entry.path,error=repr(error)))
                except OSError as error:failures.append(dict(path=str(directory),error=repr(error)))'''
assert text.count(before)==1
text=text.replace('import subprocess\n','import subprocess\nimport stat\n',1).replace(before,after)
text=text.replace('memory_is_sampled=True, source_unchanged=',
    "storage_observation_contract='no_follow_reparse_entries',\n        memory_is_sampled=True, source_unchanged=",1)
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
print(target)
