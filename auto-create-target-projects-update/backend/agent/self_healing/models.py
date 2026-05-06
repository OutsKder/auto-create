"""
models.py - 自愈循环数据模型

定义失败分析、错误分类等核心数据结构
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ErrorType(str, Enum):
    """错误分类枚举"""

    SYNTAX_ERROR = "syntax_error"  # Python 语法错误
    IMPORT_ERROR = "import_error"  # 导入问题
    RUNTIME_ERROR = "runtime_error"  # 运行时错误
    ASSERTION_FAILED = "assertion_failed"  # 测试断言失败
    TIMEOUT = "timeout"  # 执行超时
    PERMISSION_ERROR = "permission_error"  # 权限问题
    NETWORK_ERROR = "network_error"  # 网络问题
    ENVIRONMENT_ERROR = "environment_error"  # 环境配置问题
    ATTRIBUTE_ERROR = "attribute_error"  # 属性不存在
    TYPE_ERROR = "type_error"  # 类型错误
    VALUE_ERROR = "value_error"  # 值错误
    KEY_ERROR = "key_error"  # 键错误
    INDEX_ERROR = "index_error"  # 索引错误
    UNRECOVERABLE = "unrecoverable"  # 无法恢复的错误


class FailureAnalysis(BaseModel):
    """失败分析结果"""

    error_type: ErrorType  # 错误类型分类
    error_line: Optional[int] = None  # 错误行号
    error_message: str  # 错误信息文本
    code_snippet: str  # 相关代码片段
    root_cause: str  # 根本原因分析
    suggestion: str  # 给 CodeGen 的修复建议
    confidence: float  # 分析置信度 (0-1)
    context: Dict[str, Any]  # 上下文信息
    remediation_hint: str  # 修复提示
    timestamp: str  # 分析时间戳

    class Config:
        use_enum_values = True


class SelfHealingIteration(BaseModel):
    """单次迭代结果"""

    iteration_num: int  # 迭代次数
    codegen_output: Dict[str, Any]  # CodeGen 输出
    test_result: Dict[str, Any]  # 测试结果
    passed: bool  # 是否通过
    failure_analysis: Optional[FailureAnalysis] = None  # 失败分析

    class Config:
        use_enum_values = True


class SelfHealingReport(BaseModel):
    """自愈循环最终报告"""

    success: bool  # 最终是否成功
    iterations: int  # 迭代总次数
    final_code: List[Dict[str, Any]]  # 最终生成的代码补丁
    test_results: Dict[str, Any]  # 最终测试结果
    failure_history: List[FailureAnalysis]  # 失败历史记录
    final_failure: Optional[FailureAnalysis] = None  # 最终失败原因
    total_time: float  # 总耗时（秒）
    iterations_log: List[SelfHealingIteration]  # 每次迭代详情

    class Config:
        use_enum_values = True
