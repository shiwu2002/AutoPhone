"""模型客户端工厂 - 根据配置创建对应的客户端。"""

from typing import Any, Optional

from .base import ModelConfig, ModelResponse


class ModelClient:
    """
    统一的模型客户端入口 - 委托给具体的提供商客户端。

    支持 Anthropic、OpenAI 和本地 Ollama 三种提供商。
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self._client = self._create_provider_client()

    def _create_provider_client(self):
        """根据提供商创建具体的客户端。"""
        provider = self.config.provider.lower()

        if provider == "anthropic":
            from .anthropic_client import AnthropicClient
            return AnthropicClient(self.config)
        elif provider in ("local", "ollama"):
            from .ollama_client import OllamaClient
            return OllamaClient(self.config)
        else:
            # 默认使用 OpenAI 兼容客户端
            from .openai_client import OpenAIClient
            return OpenAIClient(self.config)

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        向模型发送请求。

        Args:
            messages: OpenAI 格式的消息字典列表。

        Returns:
            包含思考和动作的 ModelResponse。
        """
        return self._client.request(messages)


# 工厂函数
def create_model_client(config: Optional[ModelConfig] = None) -> ModelClient:
    """
    创建模型客户端的工厂函数。

    Args:
        config: 模型配置，为空则使用默认配置。

    Returns:
        模型客户端实例。
    """
    return ModelClient(config)
