"""Fallback storage module generated from design fallback.

Reason: 实现轻量本地历史存储能力：1. JSON格式读写历史记录；2. 内置1MB存储阈值校验，超出时自动淘汰最早的历史记录；3. 读写异常容错机制，文件损坏时自动初始化空历史
"""

import json
import os

STORAGE_PATH = "calculator_history.json"
MAX_SIZE = 1 * 1024 * 1024


def load_history() -> list[dict]:
    if not os.path.exists(STORAGE_PATH):
        return []
    try:
        with open(STORAGE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_history(history: list[dict]) -> None:
    while True:
        serialized = json.dumps(history, ensure_ascii=False)
        if len(serialized.encode("utf-8")) <= MAX_SIZE or not history:
            break
        history.pop(0)

    with open(STORAGE_PATH, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
