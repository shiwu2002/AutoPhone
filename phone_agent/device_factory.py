"""ADB 设备操作直接导入 - 移除过度设计的工厂模式。

之前使用 DeviceFactory 但只有 ADB 一个实现，属于过度设计。
现在直接导出 adb 模块的函数，简化调用链。
"""

from phone_agent.adb.device import (
    get_current_app,
    tap,
    double_tap,
    long_press,
    swipe,
    back,
    home,
    launch_app,
)

from phone_agent.adb.screenshot import get_screenshot, Screenshot
from phone_agent.adb.input import type_text, clear_text, detect_and_set_adb_keyboard, restore_keyboard
from phone_agent.adb.connection import list_devices, ADBConnection


class DeviceManager:
    """
    设备管理器 - 简化版的设备操作入口。

    不再使用工厂模式，直接提供 ADB 操作函数。
    """

    @staticmethod
    def get_screenshot(device_id: str | None = None, timeout: int = 10, enable_compression: bool = True) -> Screenshot:
        """获取屏幕截图。"""
        return get_screenshot(device_id, timeout, enable_compression)

    @staticmethod
    def get_current_app(device_id: str | None = None) -> str:
        """获取当前应用名称。"""
        return get_current_app(device_id)

    @staticmethod
    def tap(x: int, y: int, device_id: str | None = None, delay: float | None = None) -> None:
        """点击坐标。"""
        tap(x, y, device_id, delay)

    @staticmethod
    def double_tap(x: int, y: int, device_id: str | None = None, delay: float | None = None) -> None:
        """双击坐标。"""
        double_tap(x, y, device_id, delay)

    @staticmethod
    def long_press(x: int, y: int, duration_ms: int = 3000, device_id: str | None = None, delay: float | None = None) -> None:
        """长按坐标。"""
        long_press(x, y, duration_ms, device_id, delay)

    @staticmethod
    def swipe(start_x: int, start_y: int, end_x: int, end_y: int,
              duration_ms: int | None = None, device_id: str | None = None, delay: float | None = None) -> None:
        """滑动。"""
        swipe(start_x, start_y, end_x, end_y, duration_ms, device_id, delay)

    @staticmethod
    def back(device_id: str | None = None, delay: float | None = None) -> None:
        """返回键。"""
        back(device_id, delay)

    @staticmethod
    def home(device_id: str | None = None, delay: float | None = None) -> None:
        """主页键。"""
        home(device_id, delay)

    @staticmethod
    def launch_app(app_name: str, device_id: str | None = None, delay: float | None = None) -> bool:
        """启动应用。"""
        return launch_app(app_name, device_id, delay)

    @staticmethod
    def type_text(text: str, device_id: str | None = None) -> None:
        """输入文本。"""
        type_text(text, device_id)

    @staticmethod
    def clear_text(device_id: str | None = None) -> None:
        """清除文本。"""
        clear_text(device_id)

    @staticmethod
    def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
        """检测并设置 ADB 键盘。"""
        return detect_and_set_adb_keyboard(device_id)

    @staticmethod
    def restore_keyboard(original_ime: str, device_id: str | None = None) -> None:
        """恢复原始键盘。"""
        restore_keyboard(original_ime, device_id)

    @staticmethod
    def list_devices() -> list:
        """列出已连接设备。"""
        return list_devices()


# 全局单例
_device_manager: DeviceManager | None = None


def get_device_manager() -> DeviceManager:
    """获取全局 DeviceManager 实例。"""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager


# 为了向后兼容，保留旧的函数名
def get_device_factory():
    """向后兼容 - 返回 DeviceManager 实例。"""
    return get_device_manager()
