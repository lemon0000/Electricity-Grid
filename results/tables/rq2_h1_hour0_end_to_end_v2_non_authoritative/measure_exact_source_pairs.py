"""Alternate fresh processes; retain every measurement and exact projection."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

E = Path(__file__).resolve().parent
destination = E / sys.argv[1]
destination.mkdir(exist_ok=False)
script = E / 'profile_saved_exact_source.py'
(destination / script.name).write_bytes(script.read_bytes())
rows = []
reference = None
for pair in range(3):
    order = ('legacy', 'successor') if pair % 2 == 0 else ('successor', 'legacy')
    for mode in order:
        output = destination / f'pair_{pair}_{mode}'
        command = [sys.executable, '-B', str(script), 'D:/h1_chain_05_non_authoritative',
                   str(output), mode, '--timing-only']
        result = subprocess.run(command, timeout=300, capture_output=True, text=True)
        (destination / f'pair_{pair}_{mode}.stdout').write_text(result.stdout, encoding='utf8')
        (destination / f'pair_{pair}_{mode}.stderr').write_text(result.stderr, encoding='utf8')
        if result.returncode:
            raise RuntimeError(f'{mode} failed: {result.stderr}')
        terminal = json.loads((output / 'terminal.json').read_bytes())
        raw = (output / 'scientific_projection.json').read_bytes()
        if reference is None:
            reference = raw
        assert raw == reference and terminal['saved_files_unchanged']
        assert terminal['implementation_before'] == terminal['implementation_after']
        row = dict(pair=pair, mode=mode, elapsed_seconds=terminal['elapsed_seconds'],
                   projection_sha256=hashlib.sha256(raw).hexdigest(), exit_code=result.returncode)
        rows.append(row)
        print(json.dumps(row), flush=True)
legacy = statistics.median(r['elapsed_seconds'] for r in rows if r['mode'] == 'legacy')
successor = statistics.median(r['elapsed_seconds'] for r in rows if r['mode'] == 'successor')
report = dict(rows=rows, legacy_median_seconds=legacy, successor_median_seconds=successor,
              median_reduction_fraction=1-successor/legacy, scientific_projection_equal=True,
              full_chain_passed=False, formal_result=False, real_native_calls=0)
with (destination / 'terminal.json').open('x', encoding='utf8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report), flush=True)
