"""输入工具集 - 文本输入等操作。"""

import time
import logging
from typing import Any, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.config.timing import TIMING_CONFIG
from phone_agent.device_factory import get_device_factory
from phone_agent.actions.result import ActionResult

logger = logging.getLogger(__name__)


def handle_type(action: dict[str, Any], screenshot: Screenshot, device_id: Optional[str] = None, **kwargs) -> ActionResult:
    """
    处理文本输入动作。

    Args:
        action: 动作字典，包含 text="要输入的文本"
        screenshot: Screenshot 对象
        device_id: 设备 ID

    Returns:
        ActionResult: 执行结果
    """
    text = action.get("text", "")

    device_factory = get_device_factory()

    logger.info(f"🔤 开始输入文本：{text[:30]}..." if len(text) > 30 else f"🔤 开始输入文本：{text}")

    # Switch to ADB keyboard
    original_ime = device_factory.detect_and_set_adb_keyboard(device_id)
    logger.info(f"⌨️  键盘已切换（原始 IME: {original_ime}）")
    time.sleep(TIMING_CONFIG.action.keyboard_switch_delay)

    # Clear existing text and type new text
    device_factory.clear_text(device_id)
    logger.info("🧹 已清除文本")
    time.sleep(TIMING_CONFIG.action.text_clear_delay)

    # Handle multiline text by splitting on newlines
    device_factory.type_text(text, device_id)
    logger.info("⌨️  已输入文本")
    time.sleep(TIMING_CONFIG.action.text_input_delay)

    # Restore original keyboard
    device_factory.restore_keyboard(original_ime, device_id)
    logger.info(f"⌨️  已恢复键盘到：{original_ime}")
    time.sleep(TIMING_CONFIG.action.keyboard_restore_delay)

    return ActionResult(True, False)
