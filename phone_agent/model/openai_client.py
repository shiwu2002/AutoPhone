"""OpenAI API 客户端实现 - 兼容 OpenAI 和其他 OpenAI 兼容的 API。"""

import time
import httpx
from typing import Any

from .base import ModelConfig, ModelResponse
from phone_agent.config.i18n import get_message


class OpenAIClient:
    """OpenAI API 客户端 - 支持流式输出。"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.http_client = httpx.Client(verify=False)

        # 创建 OpenAI 客户端
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=config.base_url,
                api_key=config.api_key or "EMPTY",
                http_client=self.http_client
            )
        except ImportError:
            raise ImportError("openai SDK not installed. Install with: pip install openai")

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """发送请求到 OpenAI API。"""
        start_time = time.time()

        try:
            stream = self.client.chat.completions.create(
                messages=messages,
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                extra_body=self.config.extra_body,
                stream=True,
            )
            return self._process_stream(stream, start_time)
        except Exception as e:
            # 降级为非流式请求
            return self._request_non_streaming(messages, start_time)

    def _request_non_streaming(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """非流式请求（降级方案）。"""
        # 本地提供商使用最小参数
        if self.config.provider == "local":
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.config.model_name,
                stream=False,
            )
        else:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                extra_body=self.config.extra_body,
                stream=False,
            )

        total_time = time.time() - start_time
        choice = response.choices[0]
        message = choice.message

        # 提取 thinking（如果有）
        thinking = getattr(message, 'reasoning', None) or getattr(message, 'thinking', None) or ''
        content = message.content or ''

        if not thinking:
            thinking, content = self._parse_response(content)

        time_to_thinking_end = time.time() - start_time if thinking else None

        if thinking:
            print(thinking, flush=True)
            print()

        self._print_metrics(None, time_to_thinking_end, total_time)

        _, action = self._parse_response(content)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=content,
            time_to_first_token=None,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _process_stream(self, stream, start_time: float) -> ModelResponse:
        """处理流式响应。"""
        raw_content = ""
        buffer = ""
        action_markers = ["finish(message=", "do(action="]
        in_action_phase = False
        first_token_received = False
        time_to_first_token = None
        time_to_thinking_end = None

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    continue

                buffer += content

                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        thinking_part = self._clean_thinking(thinking_part)
                        if thinking_part:
                            print(thinking_part, end="", flush=True)
                            print()
                        in_action_phase = True
                        marker_found = True
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time
                        break

                if marker_found:
                    continue

                # 检查 XML 标签
                if "</think>" in buffer and "<answer>" in buffer:
                    thinking_end_idx = buffer.find("</think>")
                    thinking_part = buffer[:thinking_end_idx].replace("<think>", "").strip()
                    if thinking_part:
                        print(thinking_part, end="", flush=True)
                        print()
                    in_action_phase = True
                    if time_to_thinking_end is None:
                        time_to_thinking_end = time.time() - start_time
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

        print()
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
