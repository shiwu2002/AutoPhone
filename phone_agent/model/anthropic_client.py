"""Anthropic API 客户端实现。"""

import time
import httpx
from typing import Any

from .base import ModelConfig, ModelResponse
from phone_agent.config.i18n import get_message


class AnthropicClient:
    """Anthropic API 客户端 - 支持流式输出和 thinking 解析。"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.http_client = httpx.Client(verify=False)

        # 尝试导入 Anthropic SDK
        try:
            from anthropic import Anthropic
            self.client = Anthropic(
                api_key=config.api_key,
                base_url=config.base_url,
                http_client=self.http_client,
                timeout=60.0,  # 60 秒超时
            )
            self._use_sdk = True
        except ImportError:
            print("⚠️  anthropic SDK not installed, falling back to OpenAI-compatible API")
            self._use_sdk = False

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """发送请求到 Anthropic API。"""
        start_time = time.time()

        if self._use_sdk:
            return self._request_with_sdk(messages, start_time)
        else:
            # 降级为 OpenAI 兼容模式
            from .openai_client import OpenAIClient
            client = OpenAIClient(self.config)
            return client.request(messages)

    def _request_with_sdk(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """使用 Anthropic SDK 发送请求（流式）。"""
        # 转换消息格式
        system_message = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')

            if role == 'system':
                if isinstance(content, list):
                    system_message = ' '.join(
                        item.get('text', '') for item in content if item.get('type') == 'text'
                    )
                else:
                    system_message = str(content)
            elif role == 'user':
                if isinstance(content, list):
                    anthropic_content = []
                    for item in content:
                        if item.get('type') == 'text':
                            anthropic_content.append({'type': 'text', 'text': item.get('text', '')})
                        elif item.get('type') == 'image_url':
                            img_url = item.get('image_url', {}).get('url', '')
                            if img_url.startswith('data:'):
                                parts = img_url.split(',', 1)
                                if len(parts) == 2:
                                    media_type = parts[0].split(':')[1].split(';')[0]
                                    base64_data = parts[1]
                                    anthropic_content.append({
                                        'type': 'image',
                                        'source': {
                                            'type': 'base64',
                                            'media_type': media_type,
                                            'data': base64_data
                                        }
                                    })
                    anthropic_messages.append({'role': 'user', 'content': anthropic_content})
                else:
                    anthropic_messages.append({'role': 'user', 'content': [{'type': 'text', 'text': str(content)}]})
            elif role == 'assistant':
                if isinstance(content, list):
                    text_parts = [item.get('text', '') for item in content if item.get('type') == 'text']
                    anthropic_messages.append({'role': 'assistant', 'content': ' '.join(text_parts)})
                else:
                    anthropic_messages.append({'role': 'assistant', 'content': str(content)})

        # 流式请求
        time_to_first_token = None
        time_to_thinking_end = None
        first_token_received = False
        raw_content = ""
        buffer = ""
        in_action_phase = False
        action_markers = ["finish(message=", "do(action="]

        with self.client.messages.stream(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            system=system_message,
            messages=anthropic_messages,
        ) as stream:
            for text in stream.text_stream:
                raw_content += text

                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    continue

                buffer += text

                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        thinking_part = thinking_part.replace("<think>", "").replace("</think>", "").strip()
                        if thinking_part:
                            print(thinking_part, end="", flush=True)
                            print()
                        in_action_phase = True
                        marker_found = True
                        time_to_thinking_end = time.time() - start_time
                        break

                if marker_found:
                    continue

                # 检查是否为标记前缀
                is_potential_marker = False
                for marker in action_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    print(buffer, end="", flush=True)
                    buffer = ""

        total_time = time.time() - start_time
        thinking, action = self._parse_response(raw_content)

        # 打印性能指标
        self._print_metrics(time_to_first_token, time_to_thinking_end, total_time)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """解析响应内容为 thinking 和 action。"""
        if not content or not content.strip():
            return "", "finish(message=\"模型返回了空响应，请重试\")"

        # Rule 1: XML tags
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = self._clean_thinking(parts[0])
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 2: finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "finish(message=" + parts[1]
            return thinking, self._clean_action(action)

        # Rule 3: do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "do(action=" + parts[1]
            return thinking, self._clean_action(action)

        # Rule 4:</think>
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
