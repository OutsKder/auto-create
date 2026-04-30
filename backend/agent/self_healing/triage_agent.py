"""
triage_agent.py - 失败诊断代理

分析失败原因，生成错误分类和修复建议
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from .models import ErrorType, FailureAnalysis


class TriageAgent:
    """失败分析代理

    职责：
    - 解析日志提取错误信息
    - 分类错误类型
    - 分析根本原因
    - 生成修复建议
    """

    def execute(self, context: dict) -> dict:
        """
        执行失败分析

        Args:
            context: {
                "sandbox_result": SandboxResult,
                "code_changes": str (可选),
                "previous_failures": [FailureAnalysis] (可选),
            }

        Returns:
            {
                "failure_analysis": FailureAnalysis,
                "fix_suggestion": str,
                "retry_decision": bool,
                "reason": str,
            }
        """
        sandbox_result = context.get("sandbox_result")
        code_changes = context.get("code_changes", "")
        previous_failures = context.get("previous_failures", [])

        logs = sandbox_result.logs if sandbox_result else ""
        stderr = self._extract_stderr(logs)
        stdout = self._extract_stdout(logs)

        # 1. 解析日志，提取错误信息
        error_info = self._parse_error(stderr, stdout)

        # 2. 识别错误类型
        error_type = self._classify_error(error_info)

        # 3. 解析错误行号
        error_line = self._extract_line_number(error_info)

        # 4. 分析根本原因
        root_cause = self._analyze_root_cause(
            error_type, error_info, code_changes, previous_failures
        )

        # 5. 生成修复建议
        suggestion = self._generate_suggestion(error_type, root_cause, error_info)

        # 6. 生成修复提示
        remediation_hint = self._generate_remediation_hint(error_type)

        # 7. 计算置信度
        confidence = self._calculate_confidence(error_type, error_info)

        # 8. 构建失败分析对象
        failure_analysis = FailureAnalysis(
            error_type=error_type,
            error_line=error_line,
            error_message=error_info.get("message", ""),
            code_snippet=error_info.get("code_snippet", ""),
            root_cause=root_cause,
            suggestion=suggestion,
            confidence=confidence,
            context=error_info,
            remediation_hint=remediation_hint,
            timestamp=datetime.now().isoformat(),
        )

        return {
            "failure_analysis": failure_analysis,
            "fix_suggestion": suggestion,
            "retry_decision": error_type != ErrorType.UNRECOVERABLE,
            "reason": f"错误类型: {error_type.value}, 置信度: {confidence:.1%}",
        }

    def _extract_stderr(self, logs: str) -> str:
        """从日志中提取 stderr 部分"""
        match = re.search(r"stderr:\n(.*?)(?:\n|$)", logs, re.DOTALL)
        return match.group(1) if match else logs

    def _extract_stdout(self, logs: str) -> str:
        """从日志中提取 stdout 部分"""
        match = re.search(r"stdout:\n(.*?)(?:\nstderr|$)", logs, re.DOTALL)
        return match.group(1) if match else ""

    def _parse_error(self, stderr: str, stdout: str) -> dict:
        """解析错误信息

        Returns:
            {
                "message": str,
                "code_snippet": str,
                "traceback": str,
            }
        """
        # 优先使用 stderr
        error_text = stderr if stderr.strip() else stdout

        # 提取最后一行错误信息（通常是最有用的）
        lines = error_text.strip().split("\n")
        last_line = lines[-1] if lines else ""

        # 尝试提取代码片段
        code_snippet = self._extract_code_snippet(error_text)

        return {
            "message": last_line,
            "code_snippet": code_snippet,
            "traceback": error_text[:500],  # 保留前 500 字符
            "full_log": error_text,
        }

    def _classify_error(self, error_info: dict) -> ErrorType:
        """
        分类错误类型

        基于错误信息的关键字进行分类
        """
        message = error_info.get("message", "").lower()
        full_log = error_info.get("full_log", "").lower()

        # 语法错误
        if "syntaxerror" in full_log:
            return ErrorType.SYNTAX_ERROR

        # 导入错误
        if "importerror" in full_log or "no module named" in full_log:
            return ErrorType.IMPORT_ERROR

        # 属性错误
        if "attributeerror" in full_log or "has no attribute" in full_log:
            return ErrorType.ATTRIBUTE_ERROR

        # 类型错误
        if "typeerror" in full_log or "is not callable" in full_log:
            return ErrorType.TYPE_ERROR

        # 值错误
        if "valueerror" in full_log:
            return ErrorType.VALUE_ERROR

        # 键错误
        if "keyerror" in full_log:
            return ErrorType.KEY_ERROR

        # 索引错误
        if "indexerror" in full_log or "index out of range" in full_log:
            return ErrorType.INDEX_ERROR

        # 超时
        if "timeout" in message or "timed out" in full_log:
            return ErrorType.TIMEOUT

        # 权限错误
        if "permission denied" in full_log or "permissionerror" in full_log:
            return ErrorType.PERMISSION_ERROR

        # 网络错误
        if "network" in message or "connection refused" in full_log:
            return ErrorType.NETWORK_ERROR

        # 环境错误
        if "environment" in message or "pythonpath" in full_log:
            return ErrorType.ENVIRONMENT_ERROR

        # 断言失败
        if "assertionerror" in full_log or "assert" in message:
            return ErrorType.ASSERTION_FAILED

        # 运行时错误 (默认)
        if "error" in message or "exception" in full_log:
            return ErrorType.RUNTIME_ERROR

        # 如果无法分类且有明显错误信息
        if message and ("error" in message.lower() or "failed" in message.lower()):
            return ErrorType.RUNTIME_ERROR

        # 默认为不可恢复
        return ErrorType.UNRECOVERABLE

    def _extract_line_number(self, error_info: dict) -> Optional[int]:
        """从错误信息中提取行号"""
        traceback = error_info.get("traceback", "")

        # 查找 "line XXX" 模式
        match = re.search(r"line (\d+)", traceback)
        if match:
            return int(match.group(1))

        # 查找 "File ..., line XXX" 模式
        match = re.search(r"File.*line (\d+)", traceback)
        if match:
            return int(match.group(1))

        return None

    def _extract_code_snippet(self, error_text: str) -> str:
        """从错误文本中提取代码片段"""
        # 查找错误发生的代码行
        lines = error_text.split("\n")

        # 在 traceback 中查找代码行
        for i, line in enumerate(lines):
            if line.strip().startswith(">") or (i > 0 and "line" in lines[i - 1]):
                # 返回周围 3 行作为上下文
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                return "\n".join(lines[start:end])

        # 如果找不到，返回最后几行
        return "\n".join(lines[-3:])

    def _analyze_root_cause(
        self,
        error_type: ErrorType,
        error_info: dict,
        code_changes: str,
        previous_failures: list,
    ) -> str:
        """分析根本原因"""

        message = error_info.get("message", "")

        # 根据错误类型提供具体分析
        analyses = {
            ErrorType.SYNTAX_ERROR: f"代码中存在语法错误。{message}",
            ErrorType.IMPORT_ERROR: f"缺少依赖模块或导入路径错误。{message}",
            ErrorType.ATTRIBUTE_ERROR: f"访问了不存在的对象属性。{message}",
            ErrorType.TYPE_ERROR: f"操作了错误类型的数据。{message}",
            ErrorType.VALUE_ERROR: f"传入了非法的值。{message}",
            ErrorType.KEY_ERROR: f"字典中不存在该键。{message}",
            ErrorType.INDEX_ERROR: f"列表索引越界。{message}",
            ErrorType.ASSERTION_FAILED: f"测试断言失败。{message}",
            ErrorType.TIMEOUT: f"代码执行超过时间限制。可能存在无限循环或阻塞操作。",
            ErrorType.PERMISSION_ERROR: f"没有权限访问资源。{message}",
            ErrorType.NETWORK_ERROR: f"网络连接问题。{message}",
            ErrorType.ENVIRONMENT_ERROR: f"环境配置问题，如 PYTHONPATH 错误。{message}",
            ErrorType.RUNTIME_ERROR: f"运行时出现错误。{message}",
            ErrorType.UNRECOVERABLE: f"发生了无法恢复的错误。{message}",
        }

        return analyses.get(error_type, f"未知错误: {message}")

    def _generate_suggestion(
        self,
        error_type: ErrorType,
        root_cause: str,
        error_info: dict,
    ) -> str:
        """生成给 CodeGen 的修复建议"""

        suggestions = {
            ErrorType.SYNTAX_ERROR: "检查并修复代码语法错误。请确保所有括号、引号、冒号都正确配对。",
            ErrorType.IMPORT_ERROR: "检查导入语句是否正确。可能需要安装缺失的包或修正导入路径。",
            ErrorType.ATTRIBUTE_ERROR: "检查对象的属性名称是否拼写正确，或该对象是否真的拥有此属性。",
            ErrorType.TYPE_ERROR: "确保操作的对象类型正确。可能需要进行类型转换或使用不同的操作方法。",
            ErrorType.VALUE_ERROR: "检查传入函数的参数值是否合法。可能需要添加输入验证。",
            ErrorType.KEY_ERROR: "在访问字典键前检查键是否存在。使用 dict.get() 或 in 操作符。",
            ErrorType.INDEX_ERROR: "检查列表索引是否在合法范围内。添加边界检查。",
            ErrorType.ASSERTION_FAILED: "检查测试逻辑是否与代码实现一致。可能需要修改测试或代码。",
            ErrorType.TIMEOUT: "优化代码性能或增加超时时间。检查是否有无限循环。",
            ErrorType.PERMISSION_ERROR: "检查文件权限或运行权限。可能需要修改权限设置。",
            ErrorType.NETWORK_ERROR: "检查网络连接。如在隔离环境中，可能需要禁用网络访问。",
            ErrorType.ENVIRONMENT_ERROR: "检查环境变量和 PYTHONPATH 配置。确保所有依赖正确安装。",
            ErrorType.RUNTIME_ERROR: "检查代码逻辑是否存在问题。添加错误处理和日志。",
            ErrorType.UNRECOVERABLE: "无法自动修复此错误。需要人工审查。",
        }

        return suggestions.get(error_type, "请检查并修复错误。")

    def _generate_remediation_hint(self, error_type: ErrorType) -> str:
        """生成修复提示"""

        hints = {
            ErrorType.SYNTAX_ERROR: "使用 Python linter（如 flake8）检查语法",
            ErrorType.IMPORT_ERROR: "检查 requirements.txt 或 setup.py",
            ErrorType.ATTRIBUTE_ERROR: "查看对象文档或源代码，确认属性名称",
            ErrorType.TYPE_ERROR: "使用 type() 或 isinstance() 检查对象类型",
            ErrorType.VALUE_ERROR: "添加 try-except 捕获异常，记录输入值",
            ErrorType.KEY_ERROR: "使用 dict.get(key, default) 安全访问",
            ErrorType.INDEX_ERROR: "在访问前检查 len()，使用负索引小心处理",
            ErrorType.ASSERTION_FAILED: "重新审视测试期望值与实际值的对应关系",
            ErrorType.TIMEOUT: "分析代码时间复杂度，是否可优化",
            ErrorType.PERMISSION_ERROR: "检查文件系统权限 (chmod/chown)",
            ErrorType.NETWORK_ERROR: "在隔离环境中应禁用网络请求",
            ErrorType.ENVIRONMENT_ERROR: "验证 sys.path 和环境变量",
            ErrorType.RUNTIME_ERROR: "增加调试日志，逐步排查",
            ErrorType.UNRECOVERABLE: "需要人工干预，检查日志和代码",
        }

        return hints.get(error_type, "检查错误日志获取更多信息")

    def _calculate_confidence(self, error_type: ErrorType, error_info: dict) -> float:
        """计算分析置信度

        Returns:
            float: 0-1 之间的置信度
        """
        # 基础置信度（根据错误类型）
        base_confidence = {
            ErrorType.SYNTAX_ERROR: 0.95,
            ErrorType.IMPORT_ERROR: 0.90,
            ErrorType.ATTRIBUTE_ERROR: 0.92,
            ErrorType.TYPE_ERROR: 0.88,
            ErrorType.RUNTIME_ERROR: 0.80,
            ErrorType.UNRECOVERABLE: 0.50,
        }

        confidence = base_confidence.get(error_type, 0.75)

        # 根据错误信息完整性调整
        if error_info.get("traceback"):
            confidence = min(1.0, confidence + 0.05)

        if not error_info.get("message"):
            confidence = max(0.0, confidence - 0.15)

        return confidence
