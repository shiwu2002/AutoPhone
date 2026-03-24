"""模型客户端基础模块 - 通用数据类和工具。"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ModelConfig:
    """AI 模型的配置。"""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: Dict[str, Any] = field(default_factory=dict)
    lang: str = "cn"
    use_thinking: bool = False
    provider: str = "local"


@dataclass
class ModelResponse:
    """来自 AI 模型的响应。"""

    thinking: str
    action: str
    raw_content: str
    # 性能指标
    time_to_first_token: float | None = None
    time_to_thinking_end: float | None = None
    total_time: float | None = None


class MessageBuilder:
    """用于构建对话消息的辅助类。"""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """创建系统消息。"""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        创建带有可选图片的用户消息。

        Args:
            text: 文本内容。
            image_base64: 可选的 base64 编码图片。

        Returns:
            消息字典。
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """创建助手消息。"""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        从消息中移除图片内容以节省上下文空间。

        Args:
            message: 消息字典。

        Returns:
            移除了图片的消息。
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        为模型构建屏幕信息字符串。

        Args:
            current_app: 当前应用名称。
            **extra_info: 要包含的额外信息。

        Returns:
            包含屏幕信息的 JSON 字符串。
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
