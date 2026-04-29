"""多模态大模型客户端，支持Anthropic、OpenAI、本地Ollama三种提供商，自动处理格式适配、错误降级、性能统计。"""

import json
import logging
import time
import httpx
from dataclasses import dataclass, field
from typing import Any, Dict

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletionChunk

from phone_agent.config.i18n import get_message

logger = logging.getLogger(__name__)

# 检测Ollama SDK是否安装（可选依赖，用于支持Ollama原生思考模式）
try:
    import ollama
    OLLAMA_SDK_AVAILABLE = True
except ImportError:
    OLLAMA_SDK_AVAILABLE = False


@dataclass
class ModelConfig:
    """大模型配置参数，统一管理不同提供商的连接和推理参数。"""

    base_url: str = "http://localhost:8000/v1"  # API接口地址，本地Ollama默认是http://localhost:11434/v1
    api_key: str = "EMPTY"  # API密钥，本地部署的模型不需要密钥，填EMPTY即可
    model_name: str = "autoglm-phone-9b"  # 模型名称，比如qwen-vl:7b、claude-3-opus-20240229、gpt-4-vision-preview
    max_tokens: int = 3000  # 最大生成token数，控制响应长度
    temperature: float = 0.0  # 温度参数，0=确定性输出，越高越有创造性
    top_p: float = 0.85  # 核采样参数，控制生成多样性
    frequency_penalty: float = 0.2  # 频率惩罚，减少重复内容
    extra_body: Dict[str, Any] = field(default_factory=dict)  # 额外参数，用于传递模型特定配置
    lang: str = "cn"  # UI提示语言：cn=中文，en=英文
    use_thinking: bool = False  # 是否启用模型原生思考模式（仅Ollama支持）
    provider: str = "anthropic"  # 模型提供商：anthropic=克劳德，openai=OpenAI/GPT，local=本地Ollama部署


@dataclass
class ModelResponse:
    """大模型响应结果，结构化存储思考过程、动作指令和性能指标。"""

    thinking: str  # 模型的思考过程（<think>标签内的内容）
    action: str  # 模型输出的动作指令（<answer>标签内的内容，格式为do(...)或finish(...)）
    raw_content: str  # 模型返回的原始完整内容，用于调试
    # 性能指标
    time_to_first_token: float | None = None  # 首token耗时：从请求发起到收到第一个token的时间（秒）
    time_to_thinking_end: float | None = None  # 思考结束耗时：从请求发起到思考部分输出完成的时间（秒）
    total_time: float | None = None  # 总耗时：从请求发起到整个响应完成的时间（秒）


class ModelClient:
    """
    多模态大模型统一客户端，自动适配不同提供商的API格式，支持流式输出、思考过程解析、错误降级。
    支持三种提供商：
    1. anthropic：克劳德系列模型（Claude 3/3.5 Opus/Sonnet等）
    2. openai：OpenAI GPT系列模型（GPT-4V等）
    3. local：本地部署的Ollama模型（Qwen-VL、LLaVA、GLM-4V等）

    Args:
        config: 模型配置对象，包含连接地址、密钥、模型名称等参数
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()

        # 判断是否启用Ollama原生思考模式：显式开启+本地部署 或者 本地部署且地址是localhost/127.0.0.1
        self._use_ollama_thinking = (
            (self.config.use_thinking and self.config.provider == "local") or
            ("localhost" in self.config.base_url or "127.0.0.1" in self.config.base_url)
            and self.config.provider == "local"
        )

        # 创建HTTP客户端，本地开发时禁用SSL验证，避免自签名证书报错
        self.http_client = httpx.Client(verify=False)

        # 根据提供商初始化对应的客户端
        if self.config.provider == "anthropic":
            try:
                # 优先使用Anthropic官方SDK
                from anthropic import Anthropic
                self.client = Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    http_client=self.http_client
                )
            except ImportError:
                # 未安装Anthropic SDK时降级到OpenAI兼容模式
                print("⚠️  未安装anthropic SDK，已自动降级到OpenAI兼容模式")
                print("   安装命令：pip install anthropic")
                self.client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    http_client=self.http_client
                )
        else:
            # OpenAI或本地Ollama都使用OpenAI兼容的SDK，Ollama原生支持OpenAI格式的接口
            self.client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                http_client=self.http_client
            )

        # 本地部署时自动检查Ollama服务是否正常运行，以及模型是否已下载
        if self.config.provider == "local":
            self._check_local_service()

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        发送多模态请求到大模型，自动适配不同提供商的API格式。

        Args:
            messages: OpenAI标准格式的消息列表，支持文本和图片，格式示例：
                [
                    {"role": "system", "content": "你是手机操作助手..."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "打开微信"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,xxx"}}
                    ]}
                ]

        Returns:
            ModelResponse: 结构化的响应结果，包含思考过程、动作指令和性能指标

        Raises:
            Exception: 请求失败时抛出异常，包含详细错误信息和解决方案
        """
        # 记录请求开始时间，用于统计性能
        start_time = time.time()

        # 根据提供商选择对应的请求方法
        if self.config.provider == "anthropic":
            # Anthropic Claude系列模型，格式需要特殊转换
            return self._request_anthropic(messages, start_time)
        elif self._use_ollama_thinking:
            # 本地Ollama模型，启用原生思考模式（支持输出思考过程）
            return self._request_with_thinking(messages, start_time)
        else:
            # 其他情况使用OpenAI兼容格式请求，包括OpenAI GPT系列、普通Ollama部署、其他兼容OpenAI接口的模型服务
            return self._request_openai(messages, start_time)

    def _request_anthropic(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        调用Anthropic Claude系列模型的API，自动将OpenAI格式的消息转换成Anthropic要求的格式。

        Args:
            messages: OpenAI格式的消息列表
            start_time: 请求开始时间戳，用于统计性能

        Returns:
            ModelResponse: 结构化的响应结果
        """
        try:
            from anthropic import Anthropic

            # ========== 格式转换：OpenAI格式 → Anthropic格式 ==========
            # Anthropic的系统提示是单独的参数，不是消息列表里的system角色
            system_message = ""
            anthropic_messages = []

            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')

                if role == 'system':
                    # 提取系统提示内容，只保留文本部分，丢弃图片
                    if isinstance(content, list):
                        system_message = ' '.join(
                            item.get('text', '') for item in content if item.get('type') == 'text'
                        )
                    else:
                        system_message = str(content)
                elif role == 'user':
                    # 转换用户消息格式，支持图片+文本
                    if isinstance(content, list):
                        converted_content = []
                        for item in content:
                            if item.get('type') == 'text':
                                converted_content.append({'type': 'text', 'text': item.get('text', '')})
                            elif item.get('type') == 'image_url':
                                # 提取图片的Base64数据和媒体类型，转换成Anthropic要求的image格式
                                img_url = item.get('image_url', {}).get('url', '')
                                if img_url.startswith('data:'):
                                    parts = img_url.split(',', 1)
                                    if len(parts) == 2:
                                        media_type = parts[0].split(':')[1].split(';')[0]
                                        base64_data = parts[1]
                                        converted_content.append({
                                            'type': 'image',
                                            'source': {
                                                'type': 'base64',
                                                'media_type': media_type,
                                                'data': base64_data
                                            }
                                        })
                        anthropic_messages.append({'role': 'user', 'content': converted_content})
                    else:
                        # 纯文本消息
                        anthropic_messages.append({'role': 'user', 'content': [{'type': 'text', 'text': str(content)}]})
                elif role == 'assistant':
                    # 转换助手消息，只保留文本部分
                    if isinstance(content, list):
                        text_parts = [item.get('text', '') for item in content if item.get('type') == 'text']
                        anthropic_messages.append({'role': 'assistant', 'content': ' '.join(text_parts)})
                    else:
                        anthropic_messages.append({'role': 'assistant', 'content': str(content)})

            # 确保Anthropic客户端已初始化
            if not hasattr(self, 'anthropic_client') or self.client.__class__.__name__ != 'Anthropic':
                http_client = httpx.Client(verify=False)
                self.anthropic_client = Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    http_client=http_client
                )
            else:
                self.anthropic_client = self.client

            # ========== 流式请求处理 ==========
            time_to_first_token = None  # 首token耗时
            time_to_thinking_end = None  # 思考结束耗时
            first_token_received = False  # 是否已收到第一个token

            with self.anthropic_client.messages.stream(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                system=system_message,
                messages=anthropic_messages,
            ) as stream:
                raw_content = ""  # 原始响应内容
                buffer = ""  # 缓冲区，用于检测动作标记
                action_markers = ["finish(message=", "do(action="]  # 动作开始标记
                in_action_phase = False  # 是否已进入动作输出阶段
                in_thinking = True  # 是否还在输出思考过程

                for text in stream.text_stream:
                    raw_content += text

                    # 记录首token时间
                    if not first_token_received:
                        time_to_first_token = time.time() - start_time
                        first_token_received = True

                    # 已经进入动作阶段，不需要处理思考内容，直接拼接即可
                    if in_action_phase:
                        continue

                    buffer += text

                    # 检测动作标记：找到do(或finish(，说明思考部分结束，开始输出动作
                    marker_found = False
                    for marker in action_markers:
                        if marker in buffer:
                            # 分割思考和动作部分
                            thinking_part = buffer.split(marker, 1)[0]
                            thinking_part = thinking_part.replace("<think>", "").replace("</think>", "").strip()
                            if thinking_part:
                                # 输出思考过程到控制台
                                print(thinking_part, end="", flush=True)
                                print()
                            in_action_phase = True
                            marker_found = True
                            time_to_thinking_end = time.time() - start_time
                            break

                    if marker_found:
                        continue

                    # 兼容旧格式：检测XML标签 <think>...</think><answer>...</answer>
                    if "</think>" in buffer and "<answer>" in buffer:
                        thinking_end_idx = buffer.find("</think>")
                        thinking_part = buffer[:thinking_end_idx].replace("<think>", "").strip()
                        if thinking_part:
                            print(thinking_part, end="", flush=True)
                            print()
                        in_action_phase = True
                        time_to_thinking_end = time.time() - start_time
                        continue

                    # 检测缓冲区是否以动作标记的前缀结尾，避免截断动作标记
                    is_potential_marker = False
                    for marker in action_markers:
                        for i in range(1, len(marker)):
                            if buffer.endswith(marker[:i]):
                                is_potential_marker = True
                                break
                        if is_potential_marker:
                            break

                    # 不是潜在标记前缀，输出缓冲区内容并清空
                    if not is_potential_marker:
                        print(buffer, end="", flush=True)
                        buffer = ""

            # 计算总耗时
            total_time = time.time() - start_time

            # 解析响应内容，分离思考和动作
            thinking, action = self._parse_response(raw_content)

            # 输出性能指标
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
            print(f"Anthropic API请求失败: {e}")
            raise

    def _request_openai(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        调用OpenAI兼容格式的API，适用于OpenAI GPT系列、本地Ollama部署、以及其他兼容OpenAI接口的模型服务。

        Args:
            messages: OpenAI标准格式的消息列表，支持文本和图片
            start_time: 请求开始时间戳，用于统计性能

        Returns:
            ModelResponse: 结构化的响应结果
        """
        # 创建流式请求，支持实时输出思考过程
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

        raw_content = ""  # 原始响应内容
        buffer = ""  # 缓冲区，用于检测动作标记
        action_markers = ["finish(message=", "do(action="]  # 动作开始标记
        in_action_phase = False  # 是否已进入动作输出阶段
        first_token_received = False  # 是否已收到第一个token
        time_to_first_token = None  # 首token耗时
        time_to_thinking_end = None  # 思考结束耗时

        # 处理流式响应
        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                # 记录首token时间
                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                # 已经进入动作阶段，不需要处理思考内容，直接拼接即可
                if in_action_phase:
                    continue

                buffer += content

                # 检测动作标记：找到do(或finish(，说明思考部分结束，开始输出动作
                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        thinking_part = self._clean_thinking(thinking_part)
                        if thinking_part:
                            # 输出思考过程到控制台
                            print(thinking_part, end="", flush=True)
                            print()
                        in_action_phase = True
                        marker_found = True
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time
                        break

                if marker_found:
                    continue

                # 兼容旧格式：检测XML标签 <think>...</think><answer>...</answer>
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

                # 检测缓冲区是否以动作标记的前缀结尾，避免截断动作标记
                is_potential_marker = False
                for marker in action_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                # 不是潜在标记前缀，输出缓冲区内容并清空
                if not is_potential_marker:
                    print(buffer, end="", flush=True)
                    buffer = ""

        # 计算总耗时
        total_time = time.time() - start_time
        # 解析响应内容，分离思考和动作
        thinking, action = self._parse_response(raw_content)

        # 输出性能指标
        print()
        print("=" * 50)
        print("性能指标:")
        print("-" * 50)
        if time_to_first_token:
            print(f"首token耗时: {time_to_first_token:.3f}s")
        if time_to_thinking_end:
            print(f"思考耗时: {time_to_thinking_end:.3f}s")
        print(f"总推理耗时: {total_time:.3f}s")
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
        使用Ollama SDK调用支持原生思考模式的模型，支持纯文本和多模态（图片+文本）消息。
        适用于本地部署的Qwen、GLM等支持思考输出的模型。

        Args:
            messages: OpenAI格式的消息列表
            start_time: 请求开始时间戳，用于统计性能

        Returns:
            ModelResponse: 结构化的响应结果
        """
        # 始终使用Ollama SDK并开启think=True参数，以获得原生思考支持
        return self._request_with_fallback(messages, start_time)

    def _request_with_fallback(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        带降级机制的Ollama SDK调用，优先使用原生SDK支持多模态思考模式，SDK不可用时自动降级到OpenAI兼容接口。
        保证在各种环境下都能正常工作。

        Args:
            messages: OpenAI格式的消息列表
            start_time: 请求开始时间戳，用于统计性能

        Returns:
            ModelResponse: 结构化的响应结果
        """
        # 优先使用Ollama SDK（支持图片的思考模式）
        if OLLAMA_SDK_AVAILABLE:
            try:
                # 初始化Ollama客户端，使用和OpenAI客户端相同的主机地址，移除/v1后缀
                ollama_client = ollama.Client(host=self.config.base_url.replace('/v1', ''))

                # 将OpenAI格式转换为Ollama格式
                ollama_messages = []
                for msg in messages:
                    ollama_msg = {'role': msg['role']}
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        # 处理多模态内容，分离文本和图片
                        text_parts = []
                        images = []
                        for item in content:
                            if item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                            elif item.get('type') == 'image_url':
                                img_url = item.get('image_url', {}).get('url', '')
                                if img_url.startswith('data:'):
                                    # 从data URL中提取base64图片数据
                                    img_data = img_url.split(',', 1)[1]
                                    images.append(img_data)
                        ollama_msg['content'] = ' '.join(text_parts)
                        if images:
                            ollama_msg['images'] = images
                    else:
                        ollama_msg['content'] = content
                    ollama_messages.append(ollama_msg)

                # 调用Ollama SDK，开启思考模式，使用流式输出
                stream = ollama_client.chat(
                    model=self.config.model_name,
                    messages=ollama_messages,
                    think=True,  # 开启思考模式，输出思考过程
                    stream=True,
                    options={
                        'temperature': self.config.temperature,
                        'top_p': self.config.top_p,
                    }
                )

                # 处理流式响应
                thinking = ""  # 思考过程内容
                content = ""   # 最终输出内容
                in_thinking = False  # 是否正在输出思考过程
                thinking_complete = False  # 思考过程是否已经结束
                time_to_thinking_end = None  # 思考结束时间

                for chunk in stream:
                    if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                        # 处理思考内容
                        if not in_thinking:
                            in_thinking = True
                            print("思考过程:")
                        print(chunk.message.thinking, end='', flush=True)
                        thinking += chunk.message.thinking
                    elif hasattr(chunk.message, 'content') and chunk.message.content:
                        # 处理正式输出内容
                        if in_thinking and not thinking_complete:
                            print("\n")
                            thinking_complete = True
                            time_to_thinking_end = time.time() - start_time
                        print(chunk.message.content, end='', flush=True)
                        content += chunk.message.content

                print()  # 流式输出结束后换行
                total_time = time.time() - start_time

                # 从输出内容中解析动作指令
                _, action = self._parse_response(content)

                # 输出性能指标
                print()
                print("=" * 50)
                print("性能指标:")
                print("-" * 50)
                if time_to_thinking_end:
                    print(f"思考耗时: {time_to_thinking_end:.3f}s")
                print(f"总推理耗时: {total_time:.3f}s")
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
                print(f"Ollama SDK调用失败: {e}, 降级到OpenAI兼容接口...")

        # 降级到OpenAI兼容接口（非流式）
        try:
            # 对于本地/Ollama提供商，使用最少参数避免404错误
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

            # 从响应中提取内容和推理/思考过程
            choice = response.choices[0]
            message = choice.message

            # Ollama在OpenAI兼容模式下使用'reasoning'字段存储思考过程
            thinking = getattr(message, 'reasoning', None) or getattr(message, 'thinking', None) or ''
            content = message.content or ''

            # 如果没有单独的思考字段，尝试从内容中解析
            if not thinking:
                thinking, content = self._parse_response(content)

            time_to_thinking_end = time.time() - start_time if thinking else None

            # 从内容中解析动作指令
            _, action = self._parse_response(content)

            # 如果有思考过程，输出到控制台
            if thinking:
                print(thinking, flush=True)
                print()

            # 输出性能指标
            print()
            print("=" * 50)
            print("性能指标:")
            print("-" * 50)
            if time_to_thinking_end:
                print(f"思考耗时: {time_to_thinking_end:.3f}s")
            print(f"总推理耗时: {total_time:.3f}s")
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
            # 最终降级到流式请求
            print(f"OpenAI API调用失败: {e}, 使用流式请求重试...")
            return self._request_with_streaming(messages, start_time)

    def _request_with_streaming(self, messages: list[dict[str, Any]], start_time: float) -> ModelResponse:
        """
        最终降级的流式请求实现，不依赖SDK的思考提取功能，直接从流式输出中解析思考和动作。
        兼容性最好，几乎支持所有OpenAI兼容接口。

        Args:
            messages: OpenAI格式的消息列表
            start_time: 请求开始时间戳，用于统计性能

        Returns:
            ModelResponse: 结构化的响应结果
        """
        try:
            # 对于本地/Ollama提供商，使用最少参数避免404错误
            if self.config.provider == "local":
                try:
                    stream = self.client.chat.completions.create(
                        messages=messages,
                        model=self.config.model_name,
                        stream=True,
                    )
                except Exception as e:
                    print(f"流式请求失败: {e}, 移除额外参数重试...")
                    stream = self.client.chat.completions.create(
                        messages=messages,
                        model=self.config.model_name,
                        max_tokens=min(self.config.max_tokens, 4096),  # 限制max_tokens提升兼容性
                        stream=True,
                    )
            else:
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

            raw_content = ""  # 原始响应内容
            buffer = ""  # 缓冲区，用于检测动作标记
            action_markers = ["finish(message=", "do(action="]  # 动作开始标记
            in_action_phase = False  # 是否已进入动作输出阶段
            first_token_received = False  # 是否已收到第一个token
            time_to_first_token = None  # 首token耗时
            time_to_thinking_end = None  # 思考结束耗时

            for chunk in stream:
                if len(chunk.choices) == 0:
                    continue
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    raw_content += content

                    # 记录首token时间
                    if not first_token_received:
                        time_to_first_token = time.time() - start_time
                        first_token_received = True

                    # 已经进入动作阶段，不需要处理思考内容，直接拼接即可
                    if in_action_phase:
                        continue

                    buffer += content

                    # 检测动作标记：找到do(或finish(，说明思考部分结束，开始输出动作
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

                    # 兼容旧格式：检测XML标签 <think>...</think><answer>...</answer>
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

                    # 检测缓冲区是否以动作标记的前缀结尾，避免截断动作标记
                    is_potential_marker = False
                    for marker in action_markers:
                        for i in range(1, len(marker)):
                            if buffer.endswith(marker[:i]):
                                is_potential_marker = True
                                break
                        if is_potential_marker:
                            break

                    # 不是潜在标记前缀，输出缓冲区内容并清空
                    if not is_potential_marker:
                        print(buffer, end="", flush=True)
                        buffer = ""

            total_time = time.time() - start_time
            # 解析响应内容，分离思考和动作
            thinking, action = self._parse_response(raw_content)

            # 输出性能指标
            print()
            print("=" * 50)
            print("性能指标:")
            print("-" * 50)
            if time_to_first_token:
                print(f"首token耗时: {time_to_first_token:.3f}s")
            if time_to_thinking_end:
                print(f"思考耗时: {time_to_thinking_end:.3f}s")
            print(f"总推理耗时: {total_time:.3f}s")
            print("=" * 50)

            return ModelResponse(
                thinking=thinking,
                action=action,
                raw_content=raw_content,
                time_to_first_token=time_to_first_token,
                time_to_thinking_end=time_to_thinking_end,
                total_time=total_time,
            )
        except httpx.HTTPStatusError as e:
            # Handle HTTP status errors (including 404)
            self._handle_request_error(e, start_time)
            raise
        except Exception as e:
            # Handle other errors
            self._handle_request_error(e, start_time)
            raise

    def _handle_request_error(self, error: Exception, start_time: float) -> None:
        """
        处理API请求失败，输出友好的错误提示和解决方案。

        Args:
            error: 发生的异常对象
            start_time: 请求开始时间戳，用于统计耗时
        """
        elapsed = time.time() - start_time

        # 专门处理404错误，给出针对性解决方案
        if hasattr(error, 'status_code') and error.status_code == 404:
            print()
            print("=" * 50)
            print("❌ API错误 404 - 未找到资源")
            print("=" * 50)
            print(f"请求地址: {self.config.base_url}")
            print(f"模型名称: {self.config.model_name}")
            print()

            if self.config.provider == "local":
                # 提取Ollama的基础地址，去掉/v1后缀
                base_url = self.config.base_url
                if base_url.endswith("/v1"):
                    base_url = base_url[:-3]

                print("可能的原因:")
                print("1. Ollama服务未启动")
                print(f"   → 启动命令: ollama serve")
                print()
                print("2. 模型未下载")
                print(f"   → 下载命令: ollama pull {self.config.model_name}")
                print()
                print("3. 基础地址配置错误")
                print(f"   → 默认Ollama地址: http://localhost:11434/v1")
                print()

                # 快速诊断服务状态
                print("正在运行诊断...")
                try:
                    response = self.http_client.get(f"{base_url}/api/tags", timeout=3.0)
                    if response.status_code == 200:
                        models = response.json().get("models", [])
                        model_names = [m.get("name", "") for m in models]
                        print(f"✓ Ollama服务运行正常")
                        print(f"✓ 可用模型: {', '.join(model_names) if model_names else '无'}")
                        if self.config.model_name not in model_names:
                            print(f"✗ 模型 '{self.config.model_name}' 不存在")
                    else:
                        print(f"✗ Ollama返回状态码: {response.status_code}")
                except Exception as e:
                    print(f"✗ 无法连接到Ollama服务: {e}")
            else:
                print("请检查你的API密钥和基础地址配置是否正确。")

            print("=" * 50)
            print()

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

    def _check_local_service(self) -> bool:
        """
        检查本地Ollama服务是否正常运行和可访问。
        会自动检测服务状态和可用模型，给出友好提示。

        Returns:
            服务正常返回True，否则返回False
        """
        try:
            # 提取基础地址，去掉/v1后缀
            base_url = self.config.base_url
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]

            # 尝试连接Ollama的API获取模型列表
            response = self.http_client.get(f"{base_url}/api/tags", timeout=5.0)

            if response.status_code == 200:
                # 服务运行正常，检查配置的模型是否存在
                try:
                    data = response.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    # 检查配置的模型是否在可用列表中
                    if self.config.model_name not in model_names:
                        print(f"⚠️  警告: 模型 '{self.config.model_name}' 不存在于Ollama中")
                        print(f"   可用模型: {', '.join(model_names) if model_names else '无'}")
                        print(f"   安装命令: ollama pull {self.config.model_name}")
                except Exception as e:
                    logger.debug(f"无法解析模型列表: {e}")
                return True
            elif response.status_code == 404:
                print(f"❌ Ollama服务返回404 - 端点不存在")
                print(f"   基础地址: {base_url}")
                print(f"   请确认Ollama服务已启动: ollama serve")
                return False
            else:
                print(f"⚠️  Ollama服务返回意外状态码: {response.status_code}")
                return False

        except httpx.ConnectError:
            print(f"❌ 无法连接到Ollama服务，地址: {base_url}")
            print(f"   请确认Ollama服务已启动: ollama serve")
            print(f"   默认端口: 11434")
            return False
        except httpx.ReadTimeout:
            print(f"❌ 连接Ollama服务超时")
            print(f"   基础地址: {base_url}")
            print(f"   请确认Ollama服务运行正常且可访问")
            return False
        except Exception as e:
            print(f"⚠️  检查Ollama服务时出错: {e}")
            return False


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
