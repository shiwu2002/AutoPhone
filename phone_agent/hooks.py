"""全局钩子系统 - 用于在关键事件发生时触发回调。

钩子是全局的，可以在设置文件中配置，也可以通过代码注册。

支持的钩子事件：
- on_task_start: 任务开始时（主 Agent）
- on_task_end: 任务结束时（主 Agent）
- on_skill_start: Skill 开始执行时
- on_skill_complete: Skill 执行完成时
- on_skill_error: Skill 执行失败时
- on_wait: 执行 Wait 动作时
- on_app_changed: 应用切换时
- on_before_action: 动作执行前
- on_after_action: 动作执行后

使用示例：
    from phone_agent.hooks import register_hook, trigger_hook

    # 注册钩子
    register_hook("on_wait", lambda duration: print(f"等待 {duration} 秒"))

    # 触发钩子
    trigger_hook("on_wait", duration=3)
"""

from typing import Any, Callable, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path

from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class HookConfig:
    """钩子配置。"""
    name: str
    description: str = ""
    enabled: bool = True
    callback: Optional[Callable] = None


class HookRegistry:
    """钩子注册表。"""

    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {}
        self._config: dict[str, HookConfig] = {}
        self._load_from_settings()

    def _load_from_settings(self):
        """从 settings.json 加载钩子配置。"""
        settings_path = Path(__file__).parent.parent / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                hooks_config = settings.get('hooks', {})
                for hook_name, config in hooks_config.items():
                    self._config[hook_name] = HookConfig(
                        name=hook_name,
                        description=config.get('description', ''),
                        enabled=config.get('enabled', True)
                    )
            except Exception as e:
                logger.warning(f"加载钩子配置失败：{e}")

    def register(self, hook_name: str, callback: Callable, description: str = "") -> None:
        """
        注册钩子回调。

        Args:
            hook_name: 钩子名称
            callback: 回调函数
            description: 钩子描述
        """
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

        if hook_name not in self._config:
            self._config[hook_name] = HookConfig(
                name=hook_name,
                description=description,
                enabled=True
            )

        logger.info(f"钩子已注册：{hook_name}")

    def unregister(self, hook_name: str, callback: Optional[Callable] = None) -> None:
        """
        注销钩子回调。

        Args:
            hook_name: 钩子名称
            callback: 要移除的回调（不指定则移除所有）
        """
        if hook_name in self._hooks:
            if callback:
                self._hooks[hook_name].remove(callback)
            else:
                self._hooks[hook_name] = []

    def trigger(self, hook_name: str, **kwargs) -> list[Any]:
        """
        触发钩子。

        Args:
            hook_name: 钩子名称
            **kwargs: 传递给回调的参数

        Returns:
            所有回调的返回值列表
        """
        # 检查钩子是否启用
        if hook_name in self._config and not self._config[hook_name].enabled:
            logger.debug(f"钩子已禁用：{hook_name}")
            return []

        if hook_name not in self._hooks:
            return []

        results = []
        for callback in self._hooks[hook_name]:
            try:
                result = callback(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"钩子回调失败 {hook_name}: {e}")

        return results

    def is_enabled(self, hook_name: str) -> bool:
        """检查钩子是否启用。"""
        if hook_name not in self._config:
            return True  # 默认启用
        return self._config[hook_name].enabled

    def set_enabled(self, hook_name: str, enabled: bool) -> None:
        """设置钩子启用状态。"""
        if hook_name in self._config:
            self._config[hook_name].enabled = enabled
        else:
            self._config[hook_name] = HookConfig(name=hook_name, enabled=enabled)

    def list_hooks(self) -> list[dict[str, Any]]:
        """列出所有已注册的钩子。"""
        return [
            {
                "name": name,
                "enabled": self.is_enabled(name),
                "callbacks_count": len(callbacks),
            }
            for name, callbacks in self._hooks.items()
        ]


# 全局单例
_registry: Optional[HookRegistry] = None


def get_registry() -> HookRegistry:
    """获取全局钩子注册表实例。"""
    global _registry
    if _registry is None:
        _registry = HookRegistry()
    return _registry


def register_hook(hook_name: str, callback: Callable, description: str = "") -> None:
    """注册钩子回调。"""
    get_registry().register(hook_name, callback, description)


def unregister_hook(hook_name: str, callback: Optional[Callable] = None) -> None:
    """注销钩子回调。"""
    get_registry().unregister(hook_name, callback)


def trigger_hook(hook_name: str, **kwargs) -> list[Any]:
    """触发钩子。"""
    return get_registry().trigger(hook_name, **kwargs)


def is_hook_enabled(hook_name: str) -> bool:
    """检查钩子是否启用。"""
    return get_registry().is_enabled(hook_name)


def set_hook_enabled(hook_name: str, enabled: bool) -> None:
    """设置钩子启用状态。"""
    get_registry().set_enabled(hook_name, enabled)


def list_hooks() -> list[dict[str, Any]]:
    """列出所有已注册的钩子。"""
    return get_registry().list_hooks()
