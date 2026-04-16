# This module provides functions to save and load processed documents in JSON format. It ensures that the output directory exists before saving the file and handles encoding properly.

from __future__ import annotations

import json
from pathlib import Path


def save_processed_document(output_path: str | Path, payload: dict) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_processed_document(input_path: str | Path) -> dict:
    input_path = Path(input_path)

    with input_path.open("r", encoding="utf-8") as f:
        return json.load(f)