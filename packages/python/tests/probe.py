#!/usr/bin/env python3
"""Adapter of the shared verifier.

Reads a document path on each input line and answers one JSON line per
document. No test cases or expectations live here; the common verifier
supplies the documents.
"""

import json
import sys
from pathlib import Path

from polyspec.ordered_json import ParseError, Value, parse_bytes, stringify
from shape import rebuild, tree


for line in sys.stdin:
    data = Path(line.rstrip("\r\n")).read_bytes()
    try:
        value = parse_bytes(data)
    except ParseError as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "offset": error.offset,
                    "unit": "byte",
                    "kind": error.kind,
                }
            ),
            flush=True,
        )
        continue
    serialized = stringify(value)
    roundtrip = parse_bytes(serialized.encode("utf-8"))
    factory = stringify(Value.string('quote " slash \\ line\n 한 🌍'))
    print(
        json.dumps(
            {
                "ok": True,
                "raw": value.raw,
                "serialized": serialized,
                "compact": value.compact(),
                "tree": tree(value),
                "roundtrip": stringify(roundtrip),
                "roundtrip_tree": tree(roundtrip),
                "rebuilt": stringify(rebuild(value)),
                "factory": factory,
            }
        ),
        flush=True,
    )
