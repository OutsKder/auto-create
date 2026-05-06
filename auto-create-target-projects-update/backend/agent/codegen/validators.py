"""
validators.py

提供基本的静态校验工具（当前包含 Python 语法检查），用于在应用补丁前后做快速验证。
返回结构化的校验报告，供 DiffBundle.validation 使用。
"""

from __future__ import annotations
import ast
from typing import Tuple, List


def python_syntax_check(source: str) -> Tuple[bool, List[str]]:
    """Check Python syntax by attempting to parse AST.

    Returns (ok, errors)
    """
    try:
        ast.parse(source)
        return True, []
    except Exception as e:
        return False, [str(e)]


def validate_files_syntax(file_map: dict) -> dict:
    """Validate a dict of {path: content} for syntax issues (Python only).

    Returns mapping path -> (ok, errors)
    """
    results = {}
    for path, content in file_map.items():
        ok, errors = python_syntax_check(content)
        results[path] = {"ok": ok, "errors": errors}
    return results
