"""联通客服 AI 问答 Skill - 主要执行逻辑。

此 Skill 用于向中国联通 AI 客服提问并获取回复。
"""

import json
from pathlib import Path
from typing import Any, Optional

from phone_agent import PhoneAgent, AgentConfig, ModelConfig
from phone_agent.hooks import trigger_hook
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)

# Skill 元数据
SKILL_METADATA = {
    "id": "liantong_ai_query",
    "name": "联通 AI 客服问答",
    "description": "向中国联通 AI 客服提问并获取回复",
    "version": "1.0.0",
    "parameters": {
        "question": "要提问的问题内容",
        "app_name": "(可选) 应用名称，默认'中国联通'",
    },
    "example": 'liantong_ai_query.execute(question="联通安全管家有哪些功能？")',
}

# 系统提示词
SYSTEM_PROMPT = """你是手机操作助手，专门负责向联通 AI 客服提问并获取回复。

**核心职责：**
1. 打开中国联通 APP
2. 进入首页后点击右上角机器人/客服图标
3. 在 AI 对话界面点击全屏按钮（四个箭头图标）
4. 发送问题给 AI 客服
5. 等待 AI 回复
6. 读取并返回 AI 回复内容

**操作流程：**
1. 检查当前应用是否是中国联通，如果不是则启动
2. 确认在首页，点击右上角机器人/客服图标
3. 进入 AI 对话后，点击全屏按钮
4. 点击输入框，输入问题
5. 发送问题，等待 AI 回复（最多等待 30 秒）
6. 读取 AI 回复内容

**异常处理：**
- 如果自动跳转到其他页面，先返回首页再继续
- 如果没有 AI 对话界面，重新点击右上角机器人/客服图标
- 如果 AI 回复加载失败，尝试重新发送问题

**返回格式：**
成功：{"success": true, "answer": "AI 回复内容"}
失败：{"success": false, "error": "错误原因"}
"""


def _load_config() -> dict:
    """加载 PhoneAgent 配置文件（Skills 专用）。"""
    # 使用独立的 phone_agent_config.json 配置文件
    config_path = Path(__file__).parent.parent.parent / "phone_agent_config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def execute(question: str, app_name: str = "中国联通") -> dict[str, Any]:
    """
    执行联通客服问答 Skill。

    Args:
        question: 要提问的问题
        app_name: 应用名称（默认中国联通）

    Returns:
        包含 success 和 answer/error 的字典
    """
    logger.info(f"[{SKILL_METADATA['id']}] 开始执行：{question}")

    # 触发 Skill 开始钩子
    trigger_hook("on_skill_start", skill_id=SKILL_METADATA["id"], question=question)

    try:
        # 加载配置
        config = _load_config()
        model_config_dict = config.get('model', {})
        provider = model_config_dict.get('provider', 'local')
        provider_config = model_config_dict.get('providers', {}).get(provider, {})

        # 创建模型配置
        model_config = ModelConfig(
            base_url=provider_config.get('base_url', 'http://localhost:11434/v1'),
            model_name=provider_config.get('model', 'qwen3.5:4b'),
            api_key=provider_config.get('api_key', ''),
            lang='cn',
        )

        # 创建 Agent 配置
        agent_config = AgentConfig(
            max_steps=20,
            lang="cn",
            verbose=True,
            max_context_rounds=3,
        )

        # 创建 Agent 实例
        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config,
        )
        agent.agent_config.system_prompt = SYSTEM_PROMPT

        # 构建任务
        task = f"打开{app_name}，进入 AI 客服，提问：{question}，然后返回 AI 的完整回复内容"

        # 执行任务
        result = agent.run(task)

        logger.info(f"[{SKILL_METADATA['id']}] 执行完成")

        # 触发 Skill 完成钩子
        trigger_hook(
            "on_skill_complete",
            skill_id=SKILL_METADATA["id"],
            result=result
        )

        return {
            "success": True,
            "answer": result,
            "question": question,
            "skill_id": SKILL_METADATA["id"],
        }

    except Exception as e:
        logger.error(f"[{SKILL_METADATA['id']}] 执行失败：{e}", exc_info=True)

        # 触发 Skill 失败钩子
        trigger_hook(
            "on_skill_error",
            skill_id=SKILL_METADATA["id"],
            error=str(e)
        )

        return {
            "success": False,
            "error": str(e),
            "question": question,
            "skill_id": SKILL_METADATA["id"],
        }


def get_metadata() -> dict:
    """获取 Skill 元数据。"""
    return SKILL_METADATA
