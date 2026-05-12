from __future__ import annotations

try:
    from tools.case_memory.io_utils import append_jsonl_unique, load_json, read_jsonl, utc_now_iso, write_json
except ModuleNotFoundError:  # pragma: no cover
    from case_memory.io_utils import append_jsonl_unique, load_json, read_jsonl, utc_now_iso, write_json


__all__ = [
    "append_jsonl_unique",
    "load_json",
    "read_jsonl",
    "utc_now_iso",
    "write_json",
]
