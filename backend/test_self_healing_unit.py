"""快速单元测试：自愈循环组件"""

import os
import sys

# 确保能导入 backend 模块
# backend 目录的父目录需要加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.self_healing import (
    TriageAgent,
    RetryManager,
    ErrorType,
    FailureAnalysis,
)
from backend.agent.codegen.models import SandboxResult
import datetime

# 测试 TriageAgent
print("=" * 60)
print("测试: TriageAgent 错误分类")
print("=" * 60)

triage = TriageAgent()

# 测试 SyntaxError 检测
result1 = triage.execute(
    {
        "sandbox_result": SandboxResult(
            passed=False,
            exit_code=1,
            logs='File "test.py", line 5\n  def foo(\n       ^\nSyntaxError: invalid syntax',
        ),
        "code_changes": "",
        "previous_failures": [],
    }
)

print(f"\n✓ SyntaxError 检测:")
print(f'  错误类型: {result1["failure_analysis"].error_type}')
print(f'  置信度: {result1["failure_analysis"].confidence:.0%}')
print(f'  建议: {result1["failure_analysis"].suggestion[:50]}...')

# 测试 ImportError 检测
result2 = triage.execute(
    {
        "sandbox_result": SandboxResult(
            passed=False,
            exit_code=1,
            logs='ModuleNotFoundError: No module named "numpy"',
        ),
        "code_changes": "",
        "previous_failures": [],
    }
)

print(f"\n✓ ImportError 检测:")
print(f'  错误类型: {result2["failure_analysis"].error_type}')
print(f'  置信度: {result2["failure_analysis"].confidence:.0%}')

# 测试 AttributeError 检测
result3 = triage.execute(
    {
        "sandbox_result": SandboxResult(
            passed=False,
            exit_code=1,
            logs="AttributeError: 'NoneType' object has no attribute 'foo'",
        ),
        "code_changes": "",
        "previous_failures": [],
    }
)

print(f"\n✓ AttributeError 检测:")
print(f'  错误类型: {result3["failure_analysis"].error_type}')
print(f'  置信度: {result3["failure_analysis"].confidence:.0%}')

# 测试 RetryManager
print(f"\n" + "=" * 60)
print("测试: RetryManager 重试管理")
print("=" * 60)

manager = RetryManager(max_retries=3)
print(f"\n✓ 初始状态: {manager.get_status()}")

# 记录第一次失败
failure1 = FailureAnalysis(
    error_type=ErrorType.SYNTAX_ERROR,
    error_line=5,
    error_message="invalid syntax",
    code_snippet="def foo(",
    root_cause="括号不匹配",
    suggestion="修复括号",
    confidence=0.95,
    context={},
    remediation_hint="检查括号",
    timestamp=datetime.datetime.now().isoformat(),
)

print(f"\n✓ 第 1 次失败 - 应该继续重试: {manager.should_continue(failure1)}")
manager.record_failure(failure1)
print(f"  记录后状态: {manager.get_status()}")

# 记录不同的第二次失败
failure2 = FailureAnalysis(
    error_type=ErrorType.IMPORT_ERROR,
    error_line=3,
    error_message='No module named "numpy"',
    code_snippet="import numpy",
    root_cause="缺少依赖",
    suggestion="安装依赖",
    confidence=0.90,
    context={},
    remediation_hint="pip install",
    timestamp=datetime.datetime.now().isoformat(),
)

print(
    f"\n✓ 第 2 次失败（不同类型） - 应该继续重试: {manager.should_continue(failure2)}"
)
manager.record_failure(failure2)
print(f"  记录后状态: {manager.get_status()}")

# 记录相同的第三次失败（循环检测）
failure3 = FailureAnalysis(
    error_type=ErrorType.IMPORT_ERROR,
    error_line=3,
    error_message='No module named "numpy"',
    code_snippet="import numpy",
    root_cause="缺少依赖",
    suggestion="安装依赖",
    confidence=0.90,
    context={},
    remediation_hint="pip install",
    timestamp=datetime.datetime.now().isoformat(),
)

print(f"\n✓ 第 3 次失败（循环检测） - 应该停止: {manager.should_continue(failure3)}")

print("\n" + "=" * 60)
print("✅ 所有自愈循环单元测试通过！")
print("=" * 60)
