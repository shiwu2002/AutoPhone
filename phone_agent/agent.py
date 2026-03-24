"""用于编排手机自动化的主 PhoneAgent 类。"""

import json
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import finish, parse_action
from phone_agent.config import get_system_prompt
from phone_agent.config.i18n import get_messages
from phone_agent.device_factory import get_device_factory
from phone_agent.history import get_history_manager
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from phone_agent.utils.logger import setup_logger

# 初始化 logger
logger = setup_logger(__name__)


@dataclass
class AgentConfig:
    """PhoneAgent 的配置。"""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True
    max_context_rounds: int = 5  # 保留最近 N 轮对话
    remember_app_info: bool = True  # 是否在跨步骤中记住应用信息
    max_repeated_actions: int = 3  # 最大连续重复动作次数，0 表示不限制
    enable_repeat_detection: bool = True  # 是否启用重复动作检测

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """代理单步执行的结果。"""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class PhoneAgent:
    """
    用于自动化 Android 手机交互的 AI 驱动代理。

    该代理使用视觉语言模型来理解屏幕内容
    并决定完成用户任务的操作。

    Args:
        model_config: AI 模型的配置。
        agent_config: 代理行为的配置。
        confirmation_callback: 用于敏感操作确认的可选回调。
        takeover_callback: 用于接管请求的可选回调。

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("打开微信并给 John 发送消息")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
            model_config=self.model_config,
            agent_config=self.agent_config,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._app_history: list[str] = []  # 记录应用切换历史
        self._last_screen_info: str | None = None  # 缓存上一步的屏幕信息
        self._recent_actions: list[dict[str, Any]] = []  # 记录最近的动作，用于检测重复

    def run(self, task: str) -> str:
        """
        运行代理以完成任务。

        Args:
            task: 任务的自然语言描述。

        Returns:
            来自代理的最终消息。
        """
        self._context = []
        self._step_count = 0
        
        # 记录开始时间
        start_time = datetime.now()

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            end_time = datetime.now()
            self._save_history(task, result, start_time, end_time)
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        # max_steps <= 0 means unlimited
        while self.agent_config.max_steps <= 0 or self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                end_time = datetime.now()
                self._save_history(task, result, start_time, end_time)
                return result.message or "Task completed"

        # Max steps reached
        end_time = datetime.now()
        self._save_history(
            task,
            result,
            start_time,
            end_time,
            error_message="Max steps reached"
        )
        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        执行代理的单步操作。

        适用于手动控制或调试。

        Args:
            task: 任务描述（仅第一步需要）。

        Returns:
            包含步骤详情的 StepResult。
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """重置代理状态以开始新任务。"""
        self._context = []
        self._step_count = 0
        self._app_history = []
        self._last_screen_info = None
        self._recent_actions = []

    def _manage_context(self) -> None:
        """
        智能管理上下文，平衡记忆力和 token 使用。

        策略：
        1. 保留 system prompt
        2. 保留最近 N 轮完整对话（user + assistant）
        3. 压缩旧消息中的图片以节省空间
        4. 保留关键的应用切换历史
        """
        if len(self._context) <= 1:
            return

        max_rounds = self.agent_config.max_context_rounds
        max_messages = 1 + (max_rounds * 2)  # 1 system + N*2

        if len(self._context) > max_messages:
            # 保留 system prompt 和最近 N 轮对话
            self._context = [self._context[0]] + self._context[-(max_messages - 1):]

            # 压缩旧消息中的图片
            for i, msg in enumerate(self._context[1:], 1):
                if msg.get('role') == 'user':
                    content = msg.get('content', [])
                    if isinstance(content, list):
                        has_image = any(item.get('type') == 'image_url' for item in content)
                        if has_image:
                            # 移除图片，只保留文本
                            msg['content'] = [
                                item for item in content if item.get('type') == 'text'
                            ]

            logger.debug(f"Context managed: kept {len(self._context)} messages (last {max_rounds} rounds)")

    def _check_repeated_action(self, action: dict[str, Any]) -> bool:
        """
        检测动作是否重复执行。

        Args:
            action: 当前动作

        Returns:
            True 如果检测到重复动作，False  otherwise
        """
        if not self.agent_config.enable_repeat_detection:
            return False

        # 获取当前动作的简化签名（只关注 action 类型和关键参数）
        action_type = action.get('action', '')

        # 对于 Swipe 操作，检查方向是否相同
        if action_type == 'Swipe':
            start = action.get('start', [])
            end = action.get('end', [])
            # 简化签名：Swipe + 方向
            action_signature = f"Swipe_{start}_{end}"
        else:
            # 其他操作只检查类型
            action_signature = str(action)

        # 添加到最近动作列表
        self._recent_actions.append(action_signature)

        # 限制最近动作列表大小
        max_repeat = self.agent_config.max_repeated_actions
        if max_repeat <= 0:
            return False

        if len(self._recent_actions) > max_repeat:
            self._recent_actions = self._recent_actions[-max_repeat:]

        # 检查是否连续重复
        if len(self._recent_actions) >= max_repeat:
            if len(set(self._recent_actions[-max_repeat:])) == 1:
                # 检测到连续重复动作
                logger.warning(f"检测到连续 {max_repeat} 次相同动作：{action_type}")
                return True

        return False

    def _build_optimized_user_message(
        self,
        user_prompt: str | None,
        screenshot: Any,
        current_app: str,
        is_first: bool
    ) -> dict[str, Any]:
        """
        构建优化的用户消息，包含智能上下文增强。

        Args:
            user_prompt: 用户指令
            screenshot: 截图对象
            current_app: 当前应用名称
            is_first: 是否是第一步

        Returns:
            优化后的用户消息
        """
        # 检测应用切换
        app_changed = False
        if self._app_history and current_app != self._app_history[-1]:
            self._app_history.append(current_app)
            app_changed = True
            # 限制应用历史记录数量
            if len(self._app_history) > 5:
                self._app_history = self._app_history[-5:]

        # 构建屏幕信息
        extra_info = {}
        if self.agent_config.remember_app_info and self._app_history:
            extra_info['app_history'] = ' -> '.join(self._app_history)

        screen_info = MessageBuilder.build_screen_info(current_app, **extra_info)

        if is_first:
            text_content = f"{user_prompt}\n\n{screen_info}"
        else:
            text_content = f"** Screen Info **\n\n{screen_info}"

        # 缓存屏幕信息用于下一步比较
        self._last_screen_info = screen_info

        return MessageBuilder.create_user_message(
            text=text_content,
            image_base64=screenshot.base64_data
        )

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """执行代理循环的单步操作。"""
        self._step_count += 1

        # Capture current screen state
        device_factory = get_device_factory()
        screenshot = device_factory.get_screenshot(self.agent_config.device_id, enable_compression=True)
        current_app = device_factory.get_current_app(self.agent_config.device_id)

        # Build messages with optimized context management
        if is_first:
            # system_prompt 在 __post_init__ 中确保不为 None
            assert self.agent_config.system_prompt is not None
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )
            # Reset app history for new task
            self._app_history = [current_app]

        # Build optimized user message
        user_message = self._build_optimized_user_message(
            user_prompt=user_prompt,
            screenshot=screenshot,
            current_app=current_app,
            is_first=is_first
        )
        self._context.append(user_message)

        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            logger.info("=" * 50)
            logger.info(f"💭 {msgs['thinking']}:")
            logger.info("-" * 50)
            response = self.model_client.request(self._context)

            # 调试：打印原始响应
            logger.debug(f"Raw response action: {response.action[:200] if response.action else 'EMPTY'}")

            # Log thinking process if available
            if response.thinking and self.agent_config.verbose:
                logger.info(response.thinking)
        except Exception as e:
            logger.error(f"Model request failed: {e}", exc_info=True)
            # Remove the user message we just added to avoid duplicate requests on retry
            if not is_first:
                self._context.pop()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            action = finish(message=response.action)

        # 检测重复动作
        if self._check_repeated_action(action):
            logger.warning("⚠️  检测到重复动作，强制结束任务")
            action = finish(message="检测到重复操作，可能页面已无更多内容，任务强制结束")
            result = self.action_handler.execute(action, screenshot)
            return StepResult(
                success=True,
                finished=True,
                action=action,
                thinking="检测到重复动作",
                message=result.message,
            )

        if self.agent_config.verbose:
            # Print thinking process
            logger.info("-" * 50)
            logger.info(f"🎯 {msgs['action']}:")
            logger.info(json.dumps(action, ensure_ascii=False, indent=2))
            logger.info("=" * 50 + "\n")

        # Remove image from context to save space
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # Execute action
        try:
            result = self.action_handler.execute(
                action, screenshot
            )
        except Exception as e:
            logger.error(f"Action request failed: {e}", exc_info=True)
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot
            )

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # Manage context to keep only recent rounds
        self._manage_context()

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            logger.info("\n" + "🎉 " + "=" * 48)
            logger.info(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}"
            )
            logger.info("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """获取当前对话上下文。"""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """获取当前步数。"""
        return self._step_count
    
    def _save_history(
        self,
        task: str,
        result: StepResult,
        start_time: datetime,
        end_time: datetime,
        error_message: str | None = None
    ) -> None:
        """
        保存任务执行历史。
        
        Args:
            task: 任务描述
            result: 执行结果
            start_time: 开始时间
            end_time: 结束时间
            error_message: 错误消息（可选）
        """
        try:
            history_mgr = get_history_manager()
            device_factory = get_device_factory()
            devices = device_factory.list_devices()
            device_id = devices[0].device_id if devices else None
            
            history_mgr.add_record(
                task=task,
                result=result.message or ("Success" if result.success else "Failed"),
                steps=self._step_count,
                success=result.success and not error_message,
                start_time=start_time,
                end_time=end_time,
                device_id=device_id,
                model_name=self.model_config.model_name,
                error_message=error_message or (None if result.success else result.message)
            )
            logger.info(f"Task history saved: {task[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save task history: {e}")
