"""
runner.py

执行器（Runner）模块：在隔离环境中运行测试或命令并返回结构化结果。支持两种模式：
- 本地子进程（用于开发和CI）
- Docker容器（用于更强隔离，需确保 Docker 可用）

返回对象为 `SandboxResult`，包含 `passed`、`exit_code` 和完整日志，便于 Triage 与回环修复。
"""

from __future__ import annotations
import subprocess
import shlex
import os
import re
from typing import List, Optional, Sequence
from ..contracts import SandboxResult


class Runner:
    """Execute test commands in an isolated environment.

    This runner provides two modes:
    - local: run commands via subprocess in `repo_path` (useful for CI or controlled env)
    - docker: attempt to run commands inside a docker container (if configured)

    The docker path is best-effort; caller should ensure docker is available if requested.
    """

    def __init__(
        self,
        use_docker: bool = False,
        docker_image: Optional[str] = None,
        timeout: int = 300,
    ):
        self.use_docker = use_docker
        self.docker_image = docker_image or "python:3.10-slim"
        self.timeout = timeout

    def run_commands(
        self, commands: List[str], repo_path: str, sandbox_config: Optional[dict] = None
    ) -> SandboxResult:
        if self.use_docker:
            return self._run_in_docker(commands, repo_path, sandbox_config or {})
        return self._run_locally(commands, repo_path)

    def _run_locally(self, commands: List[str], repo_path: str) -> SandboxResult:
        import sys

        logs = []
        for cmd in commands:
            compat_result = self._run_windows_compat_command(cmd, repo_path)
            if compat_result is not None:
                logs.append(compat_result.logs)
                if not compat_result.passed:
                    return SandboxResult(
                        passed=False,
                        exit_code=compat_result.exit_code,
                        logs="\n".join(logs),
                    )
                continue

            # 处理 pytest 命令，改为使用完整 Python 路径
            processed_cmd = cmd
            if cmd.strip().startswith("pytest "):
                # 使用当前 Python 解释器的完整路径
                python_exe = sys.executable
                pytest_args = cmd[6:].strip()  # 移除 "pytest " 前缀
                processed_cmd = f'"{python_exe}" -m pytest {pytest_args}'

            try:
                # 在 Windows 上使用 utf-8 编码避免中文处理问题
                proc = subprocess.run(
                    processed_cmd,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    encoding="utf-8",
                    timeout=self.timeout,
                    errors="replace",  # 遇到编码错误时替换
                )
                stdout_text = proc.stdout or ""
                stderr_text = proc.stderr or ""
            except UnicodeDecodeError:
                # 如果仍有编码问题，使用 latin-1（更兼容）
                proc = subprocess.run(
                    processed_cmd,
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                    encoding="latin-1",
                    timeout=self.timeout,
                    errors="replace",
                )
                stdout_text = proc.stdout or ""
                stderr_text = proc.stderr or ""

            logs.append(
                f"$ {cmd}\nstdout:\n{stdout_text}\nstderr:\n{stderr_text}\nexit:{proc.returncode}\n"
            )
            if proc.returncode != 0:
                return SandboxResult(
                    passed=False, exit_code=proc.returncode, logs="\n".join(logs)
                )

        return SandboxResult(passed=True, exit_code=0, logs="\n".join(logs))

    def _run_windows_compat_command(
        self, cmd: str, repo_path: str
    ) -> Optional[SandboxResult]:
        if os.name != "nt":
            return None

        if "git diff --name-only" not in cmd:
            return None

        if "grep -qv" in cmd and "exit 1" in cmd:
            return self._evaluate_git_diff_filter_check(cmd, repo_path, quiet=True)

        if "grep -v" in cmd and "wc -l" in cmd:
            return self._evaluate_git_diff_filter_check(cmd, repo_path, quiet=False)

        if "grep -v" in cmd and "test -z" in cmd:
            return self._evaluate_git_diff_filter_check(cmd, repo_path, quiet=False)

        return None

    def _evaluate_git_diff_filter_check(
        self, cmd: str, repo_path: str, quiet: bool
    ) -> SandboxResult:
        diff_args = ["git", "diff", "--name-only"]
        if "HEAD~1 HEAD" in cmd:
            diff_args.extend(["HEAD~1", "HEAD"])
        elif "HEAD" in cmd:
            diff_args.append("HEAD")

        diff_proc = subprocess.run(
            diff_args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        changed_files = [
            line.strip() for line in diff_proc.stdout.splitlines() if line.strip()
        ]

        pattern_match = re.search(r"grep\s+-q?v\s+'([^']+)'", cmd)
        if not pattern_match:
            return SandboxResult(passed=False, exit_code=1, logs=f"$ {cmd}\nexit:1\n")

        pattern = re.compile(pattern_match.group(1))
        filtered_files = [path for path in changed_files if not pattern.search(path)]

        if quiet:
            if filtered_files:
                error_line = next(
                    (segment for segment in cmd.split("&&") if "echo" in segment), ""
                )
                return SandboxResult(
                    passed=False,
                    exit_code=1,
                    logs=f"$ {cmd}\nstdout:\n\nstderr:\n{error_line.strip()}\nexit:1\n",
                )
            ok_line = cmd.split("||")[-1].strip() if "||" in cmd else ""
            return SandboxResult(
                passed=True,
                exit_code=0,
                logs=f"$ {cmd}\nstdout:\n{ok_line}\nstderr:\nexit:0\n",
            )

        exit_code = 0 if len(filtered_files) == 0 else 1
        return SandboxResult(
            passed=(exit_code == 0),
            exit_code=exit_code,
            logs=f"$ {cmd}\nstdout:\n{len(filtered_files)}\nstderr:\nexit:{exit_code}\n",
        )

    def _run_in_docker(
        self, commands: List[str], repo_path: str, sandbox_config: dict
    ) -> SandboxResult:
        docker_cmd = self._build_docker_command(commands, repo_path, sandbox_config)
        try:
            proc = subprocess.run(
                docker_cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            logs = (
                f"$ {' '.join(docker_cmd)}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}\n"
                f"exit:{proc.returncode}\n"
            )
            return SandboxResult(
                passed=(proc.returncode == 0), exit_code=proc.returncode, logs=logs
            )
        except Exception as e:
            return SandboxResult(passed=False, exit_code=1, logs=str(e))

    def _build_docker_command(
        self, commands: Sequence[str], repo_path: str, sandbox_config: Optional[dict]
    ) -> List[str]:
        """Build a hardened docker command for isolated execution."""
        sandbox_config = sandbox_config or {}
        mount = os.path.abspath(repo_path)
        if os.name == "nt":
            mount = mount.replace("\\", "/")

        read_only = bool(sandbox_config.get("read_only", True))
        network_disabled = bool(sandbox_config.get("network_disabled", True))
        cpus = sandbox_config.get("cpus", "1.0")
        memory = sandbox_config.get("memory", "1g")
        pids_limit = sandbox_config.get("pids_limit", "256")
        tmpfs_size = sandbox_config.get("tmpfs_size", "256m")
        extra_env = sandbox_config.get("environment", {}) or {}

        docker_cmd: List[str] = ["docker", "run", "--rm", "-w", "/workspace"]
        if network_disabled:
            docker_cmd.extend(["--network", "none"])
        docker_cmd.extend(
            [
                "--cpus",
                str(cpus),
                "--memory",
                str(memory),
                "--pids-limit",
                str(pids_limit),
            ]
        )
        docker_cmd.extend(["--cap-drop", "ALL", "--security-opt", "no-new-privileges"])
        if read_only:
            docker_cmd.append("--read-only")
            docker_cmd.extend(["--tmpfs", f"/tmp:rw,nosuid,nodev,size={tmpfs_size}"])

        mount_spec = f"{mount}:/workspace"
        if read_only:
            mount_spec = f"{mount}:/workspace:ro"
        docker_cmd.extend(["-v", mount_spec])

        for key, value in extra_env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        joined = " && ".join(commands)
        docker_cmd.extend([self.docker_image, "/bin/sh", "-lc", joined])
        return docker_cmd
