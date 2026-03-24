"""Ollama 本地模型客户端实现 - 支持 thinking 功能。"""

import time
from typing import Any

from .base import ModelConfig, ModelResponse
from phone_agent.config.i18n import get_message

# 尝试导入 ollama SDK
try:
    import ollama
    OLLAMA_SDK_AVAILABLE = True
except ImportError:
    OLLAMA_SDK_AVAILABLE = False


class OllamaClient:
    """Ollama 本地模型客户端 - 支持 thinking 功能。"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._use_thinking = config.use_thinking

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """发送请求到 Ollama。"""
        start_time = time.time()

        if OLLAMA_SDK_AVAILABLE and self._use_thinking:
            return self._request_with_thinking(messages, start_time)
        else:
            return self._request_without_thinking(messages, start_time)

    def _request_with_thinking(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """使用 Ollama SDK 发送请求（支持 thinking）。"""
        try:
            # 转换消息格式
            ollama_messages = []
            for msg in messages:
                ollama_msg = {'role': msg['role']}
                content = msg.get('content', '')
                if isinstance(content, list):
                    text_parts = []
                    images = []
                    for item in content:
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        elif item.get('type') == 'image_url':
                            img_url = item.get('image_url', {}).get('url', '')
                            if img_url.startswith('data:'):
                                img_data = img_url.split(',', 1)[1]
                                images.append(img_data)
                    ollama_msg['content'] = ' '.join(text_parts)
                    if images:
                        ollama_msg['images'] = images
                else:
                    ollama_msg['content'] = content
                ollama_messages.append(ollama_msg)

            # 初始化 Ollama 客户端
            base_url = self.config.base_url.replace('/v1', '')
            ollama_client = ollama.Client(host=base_url)

            # 流式请求
            stream = ollama_client.chat(
                model=self.config.model_name,
                messages=ollama_messages,
                think=True,
                stream=True,
                options={
                    'temperature': self.config.temperature,
                    'top_p': self.config.top_p,
                }
            )

            thinking = ""
            content = ""
            in_thinking = False
            thinking_complete = False
            time_to_thinking_end = None

            for chunk in stream:
                if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                    if not in_thinking:
                        in_thinking = True
                        print("Thinking:")
                    print(chunk.message.thinking, end='', flush=True)
                    thinking += chunk.message.thinking
                elif hasattr(chunk.message, 'content') and chunk.message.content:
                    if in_thinking and not thinking_complete:
                        print("\n")
                        thinking_complete = True
                        time_to_thinking_end = time.time() - start_time
                    print(chunk.message.content, end='', flush=True)
                    content += chunk.message.content

            print()
            total_time = time.time() - start_time

            _, action = self._parse_response(content)

            print()
            self._print_metrics(None, time_to_thinking_end, total_time)

            return ModelResponse(
                thinking=thinking,
                action=action,
                raw_content=content,
                time_to_first_token=None,
                time_to_thinking_end=time_to_thinking_end,
                total_time=total_time,
            )

        except Exception as e:
            print(f"Ollama SDK failed: {e}, falling back to OpenAI API...")
            return self._request_without_thinking(messages, start_time)

    def _request_without_thinking(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """不使用 thinking 的请求（降级方案）。"""
        from .openai_client import OpenAIClient
        client = OpenAIClient(self.config)
        return client.request(messages)

    def _parse_response(self, content: str) -> tuple[str, str]:
        """解析响应内容为 thinking 和 action。"""
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = self._clean_thinking(parts[0])
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "finish(message=" + parts[1]
            return thinking, self._clean_action(action)

        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "do(action=" + parts[1]
            return thinking, self._clean_action(action)

        if "</think>" in content:
            parts = content.split("</think>", 1)
            thinking = self._clean_thinking(parts[0])
            action = parts[1].strip()
            return thinking, action

        return "", content

    def _clean_thinking(self, thinking: str) -> str:
        """清理 thinking 内容。"""
        thinking = thinking.replace("<think>", "").replace("</think>", "")
        thinking = thinking.replace("{think}", "").replace("</think>", "")
        thinking = thinking.replace("<answer>", "").replace("</answer>", "")
        return thinking.strip()

    def _clean_action(self, action: str) -> str:
        """清理 action 内容。"""
        action = action.replace("</answer>", "").strip()

        if action.startswith("do(") or action.startswith("finish("):
            last_paren = action.rfind(")")
            if last_paren != -1:
                action = action[:last_paren + 1]

        return action

    def _print_metrics(self, ttft: float | None, tte: float | None, total: float) -> None:
        """打印性能指标。"""
        print()
        print("=" * 50)
        print(f"⏱️  {get_message('performance_metrics', self.config.lang)}:")
        print("-" * 50)
        if ttft is not None:
            print(f"{get_message('time_to_first_token', self.config.lang)}: {ttft:.3f}s")
        if tte is not None:
            print(f"{get_message('time_to_thinking_end', self.config.lang)}: {tte:.3f}s")
        print(f"{get_message('total_inference_time', self.config.lang)}: {total:.3f}s")
        print("=" * 50)
