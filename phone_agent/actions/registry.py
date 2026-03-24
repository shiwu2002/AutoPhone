"""动作注册表 - 使用装饰器模式注册动作处理器。

用法:
    @action_registry.register("Tap")
    def handle_tap(action, screenshot, device_id, **kwargs):
        ...
"""

from typing import Any, Callable, Optional
from dataclasses import dataclass, field


@dataclass
class ActionMetadata:
    """动作元数据。"""
    name: str
    description: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    example: str = ""


class ActionRegistry:
    """
    动作注册表 - 管理所有动作处理器。

    提供装饰器用于注册动作处理函数。
    """

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._metadata: dict[str, ActionMetadata] = {}

    def register(
        self,
        name: str,
        description: str = "",
        parameters: Optional[dict[str, str]] = None,
        example: str = ""
    ) -> Callable:
        """
        注册动作处理器的装饰器。

        Args:
            name: 动作名称
            description: 动作描述
            parameters: 参数说明字典
            example: 使用示例

        Returns:
            装饰器函数

        Example:
            @registry.register("Tap", description="点击屏幕", parameters={"element": "[x,y] 坐标"})
            def handle_tap(action, screenshot, device_id, **kwargs):
                ...
        """
        def decorator(func: Callable) -> Callable:
            self._handlers[name] = func
            self._metadata[name] = ActionMetadata(
                name=name,
                description=description,
                parameters=parameters or {},
                example=example
            )
            return func
        return decorator

    def get_handler(self, name: str) -> Optional[Callable]:
        """获取动作处理器函数。"""
        return self._handlers.get(name)

    def has_handler(self, name: str) -> bool:
        """检查动作处理器是否存在。"""
        return name in self._handlers

    def list_actions(self) -> list[dict[str, Any]]:
        """列出所有已注册的动作。"""
        return [
            {
                "name": meta.name,
                "description": meta.description,
                "parameters": meta.parameters,
                "example": meta.example,
            }
            for meta in self._metadata.values()
        ]

    def get_metadata(self, name: str) -> Optional[ActionMetadata]:
        """获取动作的元数据。"""
        return self._metadata.get(name)

    def register_bulk(self, handlers: dict[str, Callable]) -> None:
        """批量注册动作处理器（用于向后兼容）。"""
        for name, handler in handlers.items():
            self._handlers[name] = handler


# 全局注册表实例
_registry: Optional[ActionRegistry] = None


def get_registry() -> ActionRegistry:
    """获取全局动作注册表实例。"""
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry


def register_action(
    name: str,
    description: str = "",
    parameters: Optional[dict[str, str]] = None,
    example: str = ""
) -> Callable:
    """便捷的注册装饰器（使用全局注册表）。"""
    return get_registry().register(name, description, parameters, example)
