"""向后兼容的客户端包装器 - 使用新的模块化架构。"""

# 从新的模块化架构导入，保持向后兼容
from .base import ModelConfig, ModelResponse, MessageBuilder
from .factory import ModelClient, create_model_client

__all__ = [
    "ModelConfig",
    "ModelResponse",
    "MessageBuilder",
    "ModelClient",
    "create_model_client",
]
