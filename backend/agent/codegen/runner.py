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
from typing import List, Optional, Sequence
from .models import SandboxResult


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
        logs = []
        for cmd in commands:
            proc = subprocess.run(
                shlex.split(cmd),
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            logs.append(
                f"$ {cmd}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}\nexit:{proc.returncode}\n"
            )
            if proc.returncode != 0:
                return SandboxResult(
                    passed=False, exit_code=proc.returncode, logs="\n".join(logs)
                )

        return SandboxResult(passed=True, exit_code=0, logs="\n".join(logs))

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
