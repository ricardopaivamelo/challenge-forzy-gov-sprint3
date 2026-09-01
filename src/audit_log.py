"""Persistência local append-only para decisões humanas da demonstração."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping


def append_audit_record(path: str | Path, record: Mapping[str, object]) -> None:
    """Acrescenta um registro JSONL e força sua gravação antes de retornar."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(serialized + "\n")
        stream.flush()
        os.fsync(stream.fileno())
