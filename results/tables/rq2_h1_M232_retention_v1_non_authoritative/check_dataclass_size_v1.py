"""Observe shared-key instance dict accounting; no project imports or sources."""
from dataclasses import dataclass,asdict,fields,is_dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent


@dataclass
class Record:
    name:str
    power:float
    hour:int


def measure(value):
    seen=set();total=0
    def visit(item):
        nonlocal total
        if id(item) in seen:return
        seen.add(id(item));total+=sys.getsizeof(item)
        if is_dataclass(item):
            total+=sys.getsizeof(vars(item))
            for field in fields(item):visit(getattr(item,field.name))
        elif type(item) in (tuple,list):
            for child in item:visit(child)
    visit(value);return total


def main():
    out=HERE/'dataclass_size_01';out.mkdir()
    first=Record('fixed',1.0,0);semantic_before=asdict(first)
    rows=[dict(other_instances=0,dict_bytes=sys.getsizeof(vars(first)),recursive_bytes=measure(first))]
    retained=[]
    for count in range(1,41):
        retained.append(Record('other',2.0,count))
        rows.append(dict(other_instances=count,dict_bytes=sys.getsizeof(vars(first)),recursive_bytes=measure(first)))
    assert asdict(first)==semantic_before
    assert len({row['dict_bytes'] for row in rows})>1
    value=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=0,Python=sys.version,
        observed_same_object_dict_size_changes=True,original_fields_unchanged=True,
        rows=rows,project_packet_failure_cause_proved=False,
        scope='CPython shared-key dataclass dict sizing mechanism only; not actual packet size measurements',
        source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        model_builds=0,source_loader_invocations=0,Reader_invocations=0,real_native_solver_calls=0,formal_result=False)
    (out/'tested_bytes.py').write_bytes(Path(__file__).read_bytes())
    with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(first_dict=rows[0]['dict_bytes'],last_dict=rows[-1]['dict_bytes'],
        first_recursive=rows[0]['recursive_bytes'],last_recursive=rows[-1]['recursive_bytes'],semantic_equal=True)))


if __name__=='__main__':main()
