"""Skill 系统 - 封装完整的手机操作流程。

Skill 与 Action/Tool 的区别：
- Action/Tool：单个操作（如点击、滑动、启动应用）
- Skill：完整流程（如"打开联通→点击客服→全屏→发送问题→等待回复→返回结果"）

主 Agent 通过调用 Skill 来执行复杂的手机操作任务。

注意：此模块使用项目根目录的 skills 文件夹中的独立 Skill 包。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from abc import ABC, abstractmethod

# 导入项目根目录的 skills 模块
from skills.liantong_ai_query.skill import execute as liantong_ai_query_execute
from skills.excel_tools.skill import (
    get_excel_question as get_excel_question_execute,
    write_excel_answer as write_excel_answer_execute,
    execute_excel_batch as execute_excel_batch_execute,
)

# 导入配置管理器（优先使用）
from mainAgent.skill_config import get_manager as get_skill_config_manager


@dataclass
class SkillMetadata:
    """Skill 元数据。"""
    id: str
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    example: str = ""
    index_prompt: str = ""  # 用于智能体理解何时使用该 Skill


class Skill(ABC):
    """Skill 基类。"""

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        """执行 Skill，返回结果字典。"""
        pass


class SkillRegistry:
    """Skill 注册表。"""

    def __init__(self):
        self._skills: dict[str, SkillMetadata] = {}
        self._handlers: dict[str, Callable] = {}
        self._register_builtin_skills()

    def _register_builtin_skills(self):
        """注册内置 Skill。"""
        # 联通客服问答
        self._skills["liantong_ai_query"] = SkillMetadata(
            id="liantong_ai_query",
            name="联通 AI 客服问答",
            description="向中国联通 AI 客服提问并获取回复",
            parameters={
                "question": "要提问的问题内容",
                "app_name": "(可选) 应用名称，默认'中国联通'",
            },
            example='skill(liantong_ai_query, question="联通安全管家有哪些功能？")',
            index_prompt="联通、客服、AI 问答、提问、业务查询"
        )
        self._handlers["liantong_ai_query"] = liantong_ai_query_execute

        # Excel 工具
        self._skills["get_excel_question"] = SkillMetadata(
            id="get_excel_question",
            name="从 Excel 读取问题",
            description="从 Excel 文件中获取下一道待处理的问题",
            parameters={
                "file": "Excel 文件路径",
                "row": "(可选) 指定行号",
            },
            example='skill(get_excel_question, file="questions.xlsx")',
            index_prompt="Excel、读取、问题、获取"
        )
        self._handlers["get_excel_question"] = get_excel_question_execute

        self._skills["write_excel_answer"] = SkillMetadata(
            id="write_excel_answer",
            name="将答案写入 Excel",
            description="将答案写入 Excel 文件指定的行",
            parameters={
                "file": "Excel 文件路径",
                "row": "行号",
                "answer": "答案内容",
            },
            example='skill(write_excel_answer, file="questions.xlsx", row=2, answer="答案")',
            index_prompt="Excel、写入、答案、保存"
        )
        self._handlers["write_excel_answer"] = write_excel_answer_execute

        self._skills["execute_excel_batch"] = SkillMetadata(
            id="execute_excel_batch",
            name="Excel 批量执行",
            description="批量执行 Excel 中的任务",
            parameters={
                "file": "Excel 文件路径",
                "question_column": "(可选) 问题列名",
                "max_questions": "(可选) 最大问题数",
            },
            example='skill(execute_excel_batch, file="questions.xlsx")',
            index_prompt="Excel、批量、批量执行"
        )
        self._handlers["execute_excel_batch"] = execute_excel_batch_execute

    def register(
        self,
        skill_id: str,
        name: str,
        description: str,
        parameters: Optional[dict[str, str]] = None,
        example: str = "",
        index_prompt: str = ""
    ) -> Callable:
        """注册 Skill 的装饰器。"""
        def decorator(func: Callable) -> Callable:
            self._skills[skill_id] = SkillMetadata(
                id=skill_id,
                name=name,
                description=description,
                parameters=parameters or {},
                example=example,
                index_prompt=index_prompt
            )
            self._handlers[skill_id] = func
            return func
        return decorator

    def get_handler(self, skill_id: str) -> Optional[Callable]:
        """获取 Skill 处理器。"""
        return self._handlers.get(skill_id)

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """获取 Skill 元数据。"""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[dict[str, Any]]:
        """列出所有 Skill。"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
                "example": s.example,
                "index_prompt": s.index_prompt,
            }
            for s in self._skills.values()
        ]

    def search_skills(self, keyword: str) -> list[str]:
        """根据关键词搜索 Skill。"""
        matched = []
        for skill_id, meta in self._skills.items():
            search_text = f"{skill_id} {meta.name} {meta.description} {meta.index_prompt}".lower()
            if keyword.lower() in search_text:
                matched.append(skill_id)
        return matched


# 全局单例
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """获取全局 Skill 注册表实例。"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry


def register_skill(
    skill_id: str,
    name: str,
    description: str,
    parameters: Optional[dict[str, str]] = None,
    example: str = "",
    index_prompt: str = ""
) -> Callable:
    """便捷的 Skill 注册装饰器。"""
    return get_registry().register(skill_id, name, description, parameters, example, index_prompt)


def list_skills() -> list[dict[str, Any]]:
    """列出所有 Skill。"""
    # 合并配置管理器和注册表的 Skills
    skills = []
    seen_ids = set()

    # 先添加配置管理器的 Skills（动态加载）
    try:
        config_manager = get_skill_config_manager()
        for skill in config_manager.list_skills():
            skills.append(skill)
            seen_ids.add(skill["skill_id"])
    except Exception:
        pass

    # 添加注册表的 Skills（向后兼容）
    for skill in get_registry().list_skills():
        if skill["id"] not in seen_ids:
            # 统一格式
            skill["skill_id"] = skill["id"]
            skills.append(skill)

    return skills


def get_skill_info(skill_id: str) -> Optional[dict[str, Any]]:
    """获取 Skill 详细信息。"""
    # 优先从配置管理器获取
    try:
        config_manager = get_skill_config_manager()
        info = config_manager.get_skill_info(skill_id)
        if info:
            return info
    except Exception:
        pass

    # 回退到注册表
    meta = get_registry().get_metadata(skill_id)
    if not meta:
        return None
    return {
        "id": meta.id,
        "name": meta.name,
        "description": meta.description,
        "parameters": meta.parameters,
        "example": meta.example,
        "index_prompt": meta.index_prompt,
    }


def execute_skill(skill_id: str, **kwargs) -> dict[str, Any]:
    """执行 Skill。"""
    # 优先使用配置管理器执行（支持动态加载的 Skills）
    try:
        config_manager = get_skill_config_manager()
        config = config_manager.get_config(skill_id)
        if config:
            return config_manager.execute_skill(skill_id, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"配置管理器执行失败，回退到注册表：{e}")

    # 回退到注册表执行（向后兼容）
    handler = get_registry().get_handler(skill_id)
    if not handler:
        return {"success": False, "error": f"Skill not found: {skill_id}"}
    try:
        result = handler(**kwargs)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
