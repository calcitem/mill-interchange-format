#!/usr/bin/env python3
"""Serve the non-normative MIF-INTEROP/1 protocol over stdin/stdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.mif1_adapter import handle_request  # noqa: E402
from reference.jcs import jcs_bytes  # noqa: E402


def reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member after unescape: {key}")
        result[key] = value
    return result


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n", write_through=True)
    sys.stderr.reconfigure(encoding="utf-8", newline="\n", write_through=True)
    for line_number, raw_line in enumerate(sys.stdin.buffer, start=1):
        if not raw_line.endswith(b"\n") or b"\r" in raw_line:
            print(
                f"MIF-INTEROP input line {line_number} is not LF-only terminated",
                file=sys.stderr,
            )
            return 2
        try:
            line = raw_line.decode("utf-8")
            request = json.loads(line, object_pairs_hook=reject_duplicate_members)
            response = handle_request(request)
        except Exception as exc:  # process/protocol faults are not MIF diagnostics
            print(
                f"MIF-INTEROP process failure at line {line_number}: {exc}",
                file=sys.stderr,
            )
            return 2
        sys.stdout.write(jcs_bytes(response).decode("utf-8") + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
