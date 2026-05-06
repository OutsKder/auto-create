"""
retry_manager.py - 重试管理

管理迭代循环，防止无限循环和重复错误
"""

from typing import List
from .models import ErrorType, FailureAnalysis


class RetryManager:
    """重试管理器

    职责：
    - 管理重试次数
    - 检测循环（同一错误重复）
    - 判断是否应该继续重试
    """

    def __init__(self, max_retries: int = 3):
        """初始化重试管理器

        Args:
            max_retries: 最大重试次数
        """
        self.max_retries = max_retries
        self.retry_count = 0
        self.failure_history: List[FailureAnalysis] = []

    def should_continue(self, failure: FailureAnalysis) -> bool:
        """
        判断是否应该继续重试

        检查项：
        1. 重试次数是否超限
        2. 错误类型是否可恢复
        3. 是否在重复相同错误（循环检测）

        Args:
            failure: 本次失败分析

        Returns:
            True: 应该继续重试
            False: 应该停止
        """
        # 检查 1: 是否超过最大重试次数
        if self.retry_count >= self.max_retries:
            print(f"⚠️  已达到最大重试次数 ({self.max_retries})")
            return False

        # 检查 2: 错误类型是否可恢复
        if failure.error_type == ErrorType.UNRECOVERABLE:
            print(f"⚠️  错误类型不可恢复: {failure.error_type}")
            return False

        # 检查 3: 是否在重复相同错误
        if self._is_repeating_error(failure):
            print(f"⚠️  检测到循环错误，已重复 2 次相同错误")
            return False

        return True

    def record_failure(self, failure: FailureAnalysis) -> None:
        """记录失败，用于循环检测

        Args:
            failure: 本次失败分析
        """
        self.failure_history.append(failure)
        self.retry_count += 1
        error_type = (
            failure.error_type
            if isinstance(failure.error_type, str)
            else failure.error_type.value
        )
        print(f"📝 记录失败 #{self.retry_count}: {error_type}")

    def _is_repeating_error(self, failure: FailureAnalysis) -> bool:
        """
        检测是否在重复相同的错误

        如果最后两条记录的错误类型和行号相同，则认为是循环

        Args:
            failure: 本次失败分析

        Returns:
            True: 是重复错误
            False: 不是重复错误
        """
        if len(self.failure_history) < 1:
            return False

        last_failure = self.failure_history[-1]

        # 比较错误类型和错误行号
        same_type = failure.error_type == last_failure.error_type
        same_line = failure.error_line == last_failure.error_line

        return same_type and same_line

    def get_status(self) -> dict:
        """获取重试管理器状态

        Returns:
            dict: 状态信息
        """
        last_error = None
        if self.failure_history:
            last_error_obj = self.failure_history[-1].error_type
            last_error = (
                last_error_obj
                if isinstance(last_error_obj, str)
                else last_error_obj.value
            )

        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_continue": self.retry_count < self.max_retries,
            "failure_count": len(self.failure_history),
            "last_error_type": last_error,
        }

    def reset(self) -> None:
        """重置重试管理器（用于新任务）"""
        self.retry_count = 0
        self.failure_history = []
