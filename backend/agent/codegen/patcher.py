"""
patcher.py

补丁应用器：负责把 CodeGen 输出的 Search/Replace 补丁安全地应用到工作区。
核心目标：
- 只处理设计中明确允许的文件
- 尽量采用原子写入，避免中间态损坏文件
- 对补丁格式、目标文件存在性和替换块匹配做清晰校验
"""

from __future__ import annotations

import os
import re
from ..contracts import Patch, PatchResult
from .utils import atomic_write, read_file


class PatchApplyError(Exception):
    """补丁应用失败时抛出的异常。"""


class Patcher:
    """应用结构化补丁的执行器。"""

    SEARCH_RE = re.compile(
        r"^<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE\n?", re.S | re.M
    )

    def __init__(self, repo_root: str):
        self.repo_root = repo_root

    def _resolve_path(self, file_path: str) -> str:
        return os.path.join(self.repo_root, file_path)

    def apply(self, patch: Patch) -> PatchResult:
        path = self._resolve_path(patch.file_path)

        try:
            if patch.change_type == "create":
                create_error = self._validate_create_patch(patch)
                if create_error:
                    return PatchResult(
                        file_path=patch.file_path,
                        applied=False,
                        error=create_error,
                    )
                if os.path.exists(path):
                    return PatchResult(
                        file_path=patch.file_path,
                        applied=False,
                        message="file exists",
                    )
                atomic_write(path, patch.patch)
                return PatchResult(
                    file_path=patch.file_path, applied=True, message="created"
                )

            if patch.change_type == "delete":
                if not os.path.exists(path):
                    return PatchResult(
                        file_path=patch.file_path,
                        applied=False,
                        message="not found",
                    )
                os.remove(path)
                return PatchResult(
                    file_path=patch.file_path, applied=True, message="deleted"
                )

            if patch.change_type != "modify":
                return PatchResult(
                    file_path=patch.file_path,
                    applied=False,
                    message=f"unknown change_type: {patch.change_type}",
                )

            if not os.path.exists(path):
                raise PatchApplyError(f"target file not found: {path}")

            content = read_file(path)
            match = self.SEARCH_RE.search(patch.patch)
            if not match:
                raise PatchApplyError(
                    "patch does not contain a valid SEARCH/REPLACE block"
                )

            old_block, new_block = match.group(1), match.group(2)

            if old_block not in content:
                normalized = content.replace("\r\n", "\n")
                # 如果目标文件已经包含 new_block，则视为补丁已幂等应用
                if new_block.strip() in normalized:
                    return PatchResult(
                        file_path=patch.file_path,
                        applied=True,
                        message="already applied",
                    )
                if old_block.strip() not in normalized:
                    raise PatchApplyError("search block not found in target file")

            new_content = content.replace(old_block, new_block, 1)
            atomic_write(path, new_content)
            return PatchResult(
                file_path=patch.file_path, applied=True, message="modified"
            )

        except PatchApplyError as exc:
            return PatchResult(file_path=patch.file_path, applied=False, error=str(exc))
        except Exception as exc:
            return PatchResult(file_path=patch.file_path, applied=False, error=str(exc))

    def _validate_create_patch(self, patch: Patch) -> str:
        if patch.patch_format != "full_content":
            return "create patch must use full_content format"

        patch_text = (patch.patch or "").strip()
        if not patch_text and patch.file_path.lower().endswith(".py"):
            return "create patch for python file must contain complete file content"

        forbidden_markers = ["<<<<<<< SEARCH", "=======", ">>>>>>> REPLACE", "FILE:"]
        if any(marker in patch_text for marker in forbidden_markers):
            return "create patch must be raw full file content, not a SEARCH/REPLACE block"

        return ""
