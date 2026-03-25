"""MainAgent - 主 Agent 任务编排系统。

主 Agent 负责接收用户指令，调用 Skill（子 Agent）执行手机操作，
然后处理结果并操作文档。
"""

from mainAgent.agent import MasterAgent, MasterAgentConfig

__version__ = '1.0.0'
__all__ = [
    'MasterAgent',
    'MasterAgentConfig',
]
