#!/usr/bin/env python3
"""Reports the public API of the package, one symbol per line.

The names of __all__ and the public members of its own classes are the
published surface; an underscore name is part of the implementation.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import polyspec.ordered_json as package

symbols: set[str] = set()
for name in package.__all__:
    symbols.add(name)
    member = getattr(package, name)
    if inspect.isclass(member) and member.__module__ == package.__name__:
        for attribute in vars(member):
            if not attribute.startswith('_'):
                symbols.add(f'{name}.{attribute}')
        for attribute in getattr(member, '__slots__', ()):
            if not attribute.startswith('_'):
                symbols.add(f'{name}.{attribute}')
print('\n'.join(sorted(symbols)))
