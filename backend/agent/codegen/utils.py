"""
utils.py

提供常用文件操作与安全写入工具：
- `atomic_write`：原子性写入，防止部分写入导致文件损坏
- `read_file`：读取文件内容
- `iter_lines`：按行迭代文本（保留换行）

这些工具用于 Patcher 与 Runner 的文件读写操作，确保在并发或异常情况下文件安全。
"""

from __future__ import annotations
import os
import tempfile
from typing import Iterator


def atomic_write(path: str, content: str, encoding: str = "utf-8") -> None:
    """Write file atomically to avoid partial writes.

    This helper writes to a temp file in the same directory and then renames it.
    """
    dirpath = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def read_file(path: str, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def iter_lines(text: str) -> Iterator[str]:
    for line in text.splitlines(True):
        yield line
