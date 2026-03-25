"""
PhoneAgent 包。

基于视觉语言模型的 Android 手机自动化工具。
"""

from phone_agent.agent import PhoneAgent, AgentConfig, StepResult
from phone_agent.model import ModelConfig
from phone_agent.history import TaskHistoryManager, get_history_manager
from phone_agent.utils.logger import setup_logger
from phone_agent.hooks import (
    register_hook,
    unregister_hook,
    trigger_hook,
    is_hook_enabled,
    set_hook_enabled,
    list_hooks,
)

# 全局日志记录系统
from phone_agent.logger import (
    get_logger,
    get_global_logger,
    log_agent_action,
    log_tool_call,
    log_skill_call,
    log_step,
    log_task,
    log_event,
)

__version__ = '1.0.0'
__author__ = 'Your Name'
__all__ = [
    'PhoneAgent',
    'AgentConfig',
    'StepResult',
    'ModelConfig',
    'TaskHistoryManager',
    'get_history_manager',
    'setup_logger',
    # 钩子函数
    'register_hook',
    'unregister_hook',
    'trigger_hook',
    'is_hook_enabled',
    'set_hook_enabled',
    'list_hooks',
    # 全局日志函数
    'get_logger',
    'get_global_logger',
    'log_agent_action',
    'log_tool_call',
    'log_skill_call',
    'log_step',
    'log_task',
    'log_event',
]
