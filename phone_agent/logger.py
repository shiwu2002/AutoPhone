"""全局日志记录系统 - 统一记录智能体操作和工具执行过程。

功能：
1. 统一的日志格式
2. 支持多个输出目标（文件、控制台）
3. 支持日志级别配置
4. 自动按日期分割日志文件
5. 记录智能体操作、工具调用、Skill 执行等

使用示例：
    from phone_agent.logger import get_logger, log_agent_action, log_tool_call

    # 获取 logger
    logger = get_logger("my_module")

    # 记录 Agent 操作
    log_agent_action("click", element=[500, 300], app="微信")

    # 记录工具调用
    log_tool_call("Launch", app="中国联通", result="success")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import json

# 日志格式配置
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 日志文件存储目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class AgentLogger(logging.Logger):
    """自定义 Agent Logger，支持额外的日志方法。"""

    def agent_action(self, action: str, **kwargs):
        """记录 Agent 操作。"""
        extra = {'action_type': 'agent_action', 'action': action, 'params': kwargs}
        self.info(f"ACTION: {action} | {self._format_params(kwargs)}", extra=extra)

    def tool_call(self, tool_name: str, **kwargs):
        """记录工具调用。"""
        result = kwargs.pop('result', None)
        self.info(f"TOOL: {tool_name} | {self._format_params(kwargs)} | result={result}")

    def skill_call(self, skill_id: str, **kwargs):
        """记录 Skill 调用。"""
        result = kwargs.pop('result', None)
        error = kwargs.pop('error', None)
        status = "error" if error else "success"
        msg = f"SKILL: {skill_id} | {self._format_params(kwargs)}"
        if error:
            self.error(f"{msg} | error={error}")
        else:
            self.info(f"{msg} | result={result}")

    def step(self, step_num: int, action: dict, thinking: str = ""):
        """记录 Agent 步骤。"""
        self.info(f"STEP {step_num}: {action.get('action', 'unknown')} | thinking={thinking[:50] if thinking else ''}")

    def task(self, task: str, status: str = "start"):
        """记录任务状态。"""
        emoji = {"start": "[START]", "complete": "[DONE]", "error": "[ERROR]"}.get(status, "[INFO]")
        self.info(f"{emoji} TASK [{status.upper()}]: {task}")

    def _format_params(self, params: dict) -> str:
        """格式化参数字典为字符串。"""
        if not params:
            return ""
        return ", ".join(f"{k}={v}" for k, v in params.items() if k != 'result')


# 注册自定义 Logger
logging.setLoggerClass(AgentLogger)


def get_logger(name: str, level: int = logging.INFO) -> AgentLogger:
    """
    获取配置好的 Logger。

    Args:
        name: Logger 名称（通常是模块名）
        level: 日志级别

    Returns:
        配置好的 AgentLogger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 创建控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)

    # 创建文件 handler（按日期分割）
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的日志
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # 添加 handler
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 全局 Logger 实例
_global_logger: Optional[AgentLogger] = None


def get_global_logger() -> AgentLogger:
    """获取全局 Logger 实例。"""
    global _global_logger
    if _global_logger is None:
        _global_logger = get_logger("agent")
    return _global_logger


# ==================== 便捷日志函数 ====================

def log_agent_action(action: str, **kwargs):
    """记录 Agent 操作。"""
    get_global_logger().agent_action(action, **kwargs)


def log_tool_call(tool_name: str, **kwargs):
    """记录工具调用。"""
    get_global_logger().tool_call(tool_name, **kwargs)


def log_skill_call(skill_id: str, **kwargs):
    """记录 Skill 调用。"""
    get_global_logger().skill_call(skill_id, **kwargs)


def log_step(step_num: int, action: dict, thinking: str = ""):
    """记录 Agent 步骤。"""
    get_global_logger().step(step_num, action, thinking)


def log_task(task: str, status: str = "start"):
    """记录任务状态。"""
    get_global_logger().task(task, status)


def log_event(category: str, message: str, **kwargs):
    """记录通用事件。"""
    logger = get_global_logger()
    extra = {'category': category}
    logger.info(f"{category}: {message}", extra=extra)


# ==================== 钩子集成 ====================

def setup_hook_logging():
    """设置钩子日志记录。"""
    from phone_agent.hooks import register_hook

    # 记录 Skill 执行
    register_hook("on_skill_start", lambda skill_id, **kwargs: log_skill_call(skill_id, status="start", **kwargs))
    register_hook("on_skill_complete", lambda skill_id, result, **kwargs: log_skill_call(skill_id, result=result))
    register_hook("on_skill_error", lambda skill_id, error, **kwargs: log_skill_call(skill_id, error=error))

    # 记录任务状态
    register_hook("on_task_start", lambda task, **kwargs: log_task(task, "start"))
    register_hook("on_task_end", lambda task, result, **kwargs: log_task(task, "complete"))

    # 记录 Agent 操作
    register_hook("on_app_changed", lambda old_app, new_app, **kwargs: log_agent_action("app_changed", old=old_app, new=new_app))
    register_hook("on_wait", lambda duration, **kwargs: log_agent_action("wait", duration=duration))


# 自动设置钩子日志
setup_hook_logging()
