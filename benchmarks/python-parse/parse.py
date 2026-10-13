"""One parse of the document of argv[1] with the Python package of this checkout; prints the CPU seconds of the parse.
benchmarks/python-parse/run.py starts it."""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'packages/ordered-json-python/src'))
from polyspec.ordered_json import parse_bytes

data = Path(sys.argv[1]).read_bytes()
started = time.process_time()
value = parse_bytes(data)
elapsed = time.process_time() - started
if len(value.items()) != int(sys.argv[2]):
    raise SystemExit(f'parsed {len(value.items())} items, not {sys.argv[2]}')
print(f'{elapsed:.6f}')
