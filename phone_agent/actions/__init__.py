"""Phone Agent 的动作处理模块。"""

# 导入动作集以触发注册表初始化
from phone_agent.actions import sets  # noqa: F401
from phone_agent.actions.handler import ActionHandler, ActionResult

__all__ = ["ActionHandler", "ActionResult"]
