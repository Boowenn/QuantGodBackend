from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from tools.usdjpy_evidence_os.io_utils import load_json
    from tools.usdjpy_evidence_os.schema import parity_path, parity_public_path
except ModuleNotFoundError:  # pragma: no cover
    from usdjpy_evidence_os.io_utils import load_json
    from usdjpy_evidence_os.schema import parity_path, parity_public_path


def load_existing_parity(runtime_dir: Path) -> Dict[str, Any]:
    return load_json(parity_public_path(runtime_dir)) or load_json(parity_path(runtime_dir))
