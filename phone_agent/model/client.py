"""用于 OpenAI 兼容 API 的 AI 推理模型客户端。"""

import json
import time
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletionChunk

from phone_agent.config.i18n import get_message

# Try to import ollama SDK (optional, for enhanced thinking support)
try:
    import ollama
    OLLAMA_SDK_AVAILABLE = True
except ImportError:
    OLLAMA_SDK_AVAILABLE = False


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
    lang: str = "cn"  # Language for UI messages: 'cn' or 'en'
    use_thinking: bool = False  # Whether to use model's built-in thinking feature (Ollama)
    provider: str = "anthropic"  # Model provider: anthropic, openai, local


@dataclass
class ModelResponse:
    """来自 AI 模型的响应。"""

    thinking: str
    action: str
    raw_content: str
    # Performance metrics
    time_to_first_token: float | None = None  # Time to first token (seconds)
    time_to_thinking_end: float | None = None  # Time to thinking end (seconds)
    total_time: float | None = None  # Total inference time (seconds)


class ModelClient:
    """
    用于与 OpenAI 兼容的视觉语言模型交互的客户端。
    支持 Anthropic、OpenAI 和本地 Ollama 三种提供商。

    Args:
        config: 模型配置。
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()

        # Determine if we should use Ollama thinking
        # Use thinking if explicitly enabled OR if using localhost/127.0.0.1 AND provider is local
        self._use_ollama_thinking = (
            (self.config.use_thinking and self.config.provider == "local") or
            ("localhost" in self.config.base_url or "127.0.0.1" in self.config.base_url)
            and self.config.provider == "local"
        )

        # Create HTTP client with SSL verification disabled for local development
        http_client = httpx.Client(verify=False)

        # Initialize client based on provider
        if self.config.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self.client = Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    http_client=http_client
                )
            except ImportError:
                print("⚠️  anthropic SDK not installed, falling back to OpenAI-compatible API")
                print("   Install with: pip install anthropic")
                self.client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    http_client=http_client
                )
        else:
            # OpenAI or local (Ollama uses OpenAI-compatible API)
            self.client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                http_client=http_client
            )

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        向模型发送请求。

        Args:
            messages: OpenAI 格式的消息字典列表。

        Returns:
            包含思考和动作的 ModelResponse。

        Raises:
            ValueError: 如果响应无法解析。
        """
        # Start timing
        start_time = time.time()

        # Use provider-specific request method
        if self.config.provider == "anthropic":
            return self._request_anthropic(messages, start_time)
        elif self._use_ollama_thinking:
            return self._request_with_thinking(messages, start_time)
        else:
            return self._request_openai(messages, start_time)

    def _request_anthropic(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        Request using Anthropic API.

        Args:
            messages: Message list (OpenAI format, will be converted)
            start_time: Request start time

        Returns:
            ModelResponse with thinking and action
        """
        try:
            from anthropic import Anthropic

            # Convert system message to Anthropic format
            system_message = ""
            openai_messages = []

            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')

                if role == 'system':
                    # Anthropic uses system parameter, not system message
                    if isinstance(content, list):
                        system_message = ' '.join(
                            item.get('text', '') for item in content if item.get('type') == 'text'
                        )
                    else:
                        system_message = str(content)
                elif role == 'user':
                    # Convert content format
                    if isinstance(content, list):
                        anthropic_content = []
                        for item in content:
                            if item.get('type') == 'text':
                                anthropic_content.append({'type': 'text', 'text': item.get('text', '')})
                            elif item.get('type') == 'image_url':
                                img_url = item.get('image_url', {}).get('url', '')
                                if img_url.startswith('data:'):
                                    # Extract media type and base64
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
                        openai_messages.append({'role': 'user', 'content': anthropic_content})
                    else:
                        openai_messages.append({'role': 'user', 'content': [{'type': 'text', 'text': str(content)}]})
                elif role == 'assistant':
                    if isinstance(content, list):
                        text_parts = [item.get('text', '') for item in content if item.get('type') == 'text']
                        openai_messages.append({'role': 'assistant', 'content': ' '.join(text_parts)})
                    else:
                        openai_messages.append({'role': 'assistant', 'content': str(content)})

            # Create client if not already created
            if not hasattr(self, 'anthropic_client') or self.client.__class__.__name__ != 'Anthropic':
                http_client = httpx.Client(verify=False)
                self.anthropic_client = Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    http_client=http_client
                )
            else:
                self.anthropic_client = self.client

            # Make request with streaming
            time_to_first_token = None
            time_to_thinking_end = None
            first_token_received = False

            with self.anthropic_client.messages.stream(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                system=system_message,
                messages=openai_messages,
            ) as stream:
                raw_content = ""
                buffer = ""
                action_markers = ["finish(message=", "do(action="]
                in_action_phase = False
                in_thinking = True

                for text in stream.text_stream:
                    raw_content += text

                    # Record time to first token
                    if not first_token_received:
                        time_to_first_token = time.time() - start_time
                        first_token_received = True

                    if in_action_phase:
                        continue

                    buffer += text

                    # Check for action markers
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

                    # Check for XML tags (legacy format)
                    if "</think>" in buffer and "<answer>" in buffer:
                        thinking_end_idx = buffer.find("</think>")
                        thinking_part = buffer[:thinking_end_idx].replace("<think>", "").strip()
                        if thinking_part:
                            print(thinking_part, end="", flush=True)
                            print()
                        in_action_phase = True
                        time_to_thinking_end = time.time() - start_time
                        continue

                    # Check if buffer ends with potential marker prefix
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

            # Calculate total time
            total_time = time.time() - start_time

            # Parse thinking and action from response
            thinking, action = self._parse_response(raw_content)

            # Print performance metrics
            lang = self.config.lang
            print()
            print("=" * 50)
            print(f"⏱️  {get_message('performance_metrics', lang)}:")
            print("-" * 50)
            if time_to_first_token is not None:
                print(f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s")
            if time_to_thinking_end is not None:
                print(f"{get_message('time_to_thinking_end', lang)}: {time_to_thinking_end:.3f}s")
            print(f"{get_message('total_inference_time', lang)}: {total_time:.3f}s")
            print("=" * 50)

            return ModelResponse(
                thinking=thinking,
                action=action,
                raw_content=raw_content,
                time_to_first_token=time_to_first_token,
                time_to_thinking_end=time_to_thinking_end,
                total_time=total_time,
            )

        except Exception as e:
            print(f"Anthropic API error: {e}")
            raise

    def _request_openai(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        Request using OpenAI-compatible API.

        Args:
            messages: Message list (OpenAI format)
            start_time: Request start time

        Returns:
            ModelResponse with thinking and action
        """
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
        print("=" * 50)
        print("Performance metrics:")
        print("-" * 50)
        if time_to_first_token:
            print(f"Time to first token: {time_to_first_token:.3f}s")
        if time_to_thinking_end:
            print(f"Thinking time: {time_to_thinking_end:.3f}s")
        print(f"Total inference time: {total_time:.3f}s")
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _request_with_thinking(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        Request using Ollama SDK with thinking support.
        This supports both text-only and multimodal (image + text) messages.

        Args:
            messages: Message list
            start_time: Request start time

        Returns:
            ModelResponse with thinking and action
        """
        # Always use Ollama SDK with think=True for thinking support
        return self._request_with_fallback(messages, start_time)

    def _request_with_fallback(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        Request using Ollama SDK with thinking support (for images and text).
        Falls back to OpenAI-compatible API if Ollama SDK is not available.

        Args:
            messages: Message list (OpenAI format)
            start_time: Request start time

        Returns:
            ModelResponse with thinking and action
        """
        # Try Ollama SDK first (supports thinking with images)
        if OLLAMA_SDK_AVAILABLE:
            try:
                # Initialize Ollama client with the same host as OpenAI client
                ollama_client = ollama.Client(host=self.config.base_url.replace('/v1', ''))

                # Convert OpenAI format to Ollama format
                ollama_messages = []
                for msg in messages:
                    ollama_msg = {'role': msg['role']}
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        # Handle multimodal content
                        text_parts = []
                        images = []
                        for item in content:
                            if item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                            elif item.get('type') == 'image_url':
                                img_url = item.get('image_url', {}).get('url', '')
                                if img_url.startswith('data:'):
                                    # Extract base64 from data URL
                                    img_data = img_url.split(',', 1)[1]
                                    images.append(img_data)
                        ollama_msg['content'] = ' '.join(text_parts)
                        if images:
                            ollama_msg['images'] = images
                    else:
                        ollama_msg['content'] = content
                    ollama_messages.append(ollama_msg)

                # Call Ollama SDK with thinking enabled (streaming)
                stream = ollama_client.chat(
                    model=self.config.model_name,
                    messages=ollama_messages,
                    think=True,  # Enable thinking feature
                    stream=True,
                    options={
                        'temperature': self.config.temperature,
                        'top_p': self.config.top_p,
                    }
                )

                # Process streaming response
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

                print()  # Newline after streaming complete
                total_time = time.time() - start_time

                # Parse action from content
                _, action = self._parse_response(content)

                # Print performance metrics
                print()
                print("=" * 50)
                print("Performance metrics:")
                print("-" * 50)
                if time_to_thinking_end:
                    print(f"Thinking time: {time_to_thinking_end:.3f}s")
                print(f"Total inference time: {total_time:.3f}s")
                print("=" * 50)

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

        # Fallback to OpenAI-compatible API (non-streaming)
        try:
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

            # Extract content and reasoning/thinking from response
            choice = response.choices[0]
            message = choice.message

            # Ollama uses 'reasoning' field in OpenAI compat mode
            thinking = getattr(message, 'reasoning', None) or getattr(message, 'thinking', None) or ''
            content = message.content or ''

            # If no reasoning field, try to parse from content
            if not thinking:
                thinking, content = self._parse_response(content)

            time_to_thinking_end = time.time() - start_time if thinking else None

            # Parse action from content
            _, action = self._parse_response(content)

            # Print thinking if available
            if thinking:
                print(thinking, flush=True)
                print()

            # Print performance metrics
            print()
            print("=" * 50)
            print("Performance metrics:")
            print("-" * 50)
            if time_to_thinking_end:
                print(f"Thinking time: {time_to_thinking_end:.3f}s")
            print(f"Total inference time: {total_time:.3f}s")
            print("=" * 50)

            return ModelResponse(
                thinking=thinking,
                action=action,
                raw_content=content,
                time_to_first_token=None,
                time_to_thinking_end=time_to_thinking_end,
                total_time=total_time,
            )
        except Exception as e:
            # Final fallback to streaming
            print(f"OpenAI API failed: {e}, using streaming...")
            return self._request_with_streaming(messages, start_time)

    def _request_with_streaming(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        Original streaming implementation (without reasoning/thinking extraction).

        Args:
            messages: Message list
            start_time: Request start time

        Returns:
            ModelResponse with thinking and action
        """
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
        print("=" * 50)
        print("Performance metrics:")
        print("-" * 50)
        if time_to_first_token:
            print(f"Time to first token: {time_to_first_token:.3f}s")
        if time_to_thinking_end:
            print(f"Thinking time: {time_to_thinking_end:.3f}s")
        print(f"Total inference time: {total_time:.3f}s")
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        将模型响应解析为思考和动作部分。

        解析规则（按优先级）：
        1. XML 标签格式：<think>...</think><answer>...</answer>（最高优先级）
        2. finish(message= 格式
        3. do(action= 格式
        4. 简化格式：...</think> action
        5. 无标记：全部作为动作

        Args:
            content: 原始响应内容。

        Returns:
            (思考，动作) 元组。
        """
        # Rule 1: XML tag parsing (highest priority)
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = self._clean_thinking(parts[0])
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 2: Check for finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "finish(message=" + parts[1]
            action = self._clean_action(action)
            return thinking, action

        # Rule 3: Check for do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = self._clean_thinking(parts[0].strip())
            action = "do(action=" + parts[1]
            action = self._clean_action(action)
            return thinking, action

        # Rule 4: Simplified format ...</think> action
        if "</think>" in content:
            parts = content.split("</think>", 1)
            thinking = self._clean_thinking(parts[0])
            action = parts[1].strip()
            return thinking, action

        # Rule 5: No markers found, return content as action
        return "", content

    def _clean_thinking(self, thinking: str) -> str:
        """
        清理思考内容，移除 XML 标签和其他标记。

        Args:
            thinking: 原始思考内容。

        Returns:
            清理后的思考内容。
        """
        thinking = thinking.replace("<think>", "").replace("</think>", "")
        thinking = thinking.replace("{think}", "").replace("</think>", "")
        thinking = thinking.replace("<answer>", "").replace("</answer>", "")
        return thinking.strip()
    
    def _clean_action(self, action: str) -> str:
        """
        通过移除 XML 标签和其他伪影来清理动作字符串。
        
        Args:
            action: 原始动作字符串。
            
        Returns:
            清理后的动作字符串。
        """
        # Remove </answer> tag if present
        action = action.replace("</answer>", "")
        
        # Remove any trailing whitespace
        action = action.strip()
        
        # If action ends with ) and has proper structure, keep it
        # But remove any content after the closing parenthesis
        if action.startswith("do("):
            # Find the last closing parenthesis
            last_paren = action.rfind(")")
            if last_paren != -1:
                action = action[:last_paren + 1]
        elif action.startswith("finish("):
            # Find the last closing parenthesis
            last_paren = action.rfind(")")
            if last_paren != -1:
                action = action[:last_paren + 1]
        
        return action


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
    def build_screen_info(current_app: str, **extra_info) -> str:  # type: ignore[no-untyped-def]
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
