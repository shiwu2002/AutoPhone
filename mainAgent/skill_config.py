"""Skill 配置管理器 - 动态加载和管理 Skills。

功能：
1. 从配置文件加载 Skills
2. 支持动态添加/删除 Skills
3. 配置格式使用 JSON Schema
4. 支持配置参数验证
"""

import json
import importlib
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SkillParameter:
    """Skill 参数定义。"""
    name: str
    type: str  # str, int, float, bool, list, dict
    description: str
    required: bool = True
    default: Any = None
    options: list = field(default_factory=list)  # 可选值列表


@dataclass
class SkillConfig:
    """Skill 配置数据结构。"""
    skill_id: str
    name: str
    description: str
    module_path: str  # 模块路径，如 "skills.liantong_ai_query.skill"
    execute_function: str  # 执行函数名，默认 "execute"
    version: str = "1.0.0"
    enabled: bool = True
    parameters: list[SkillParameter] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)  # 用户配置 Schema
    user_config: dict = field(default_factory=dict)  # 用户实际配置
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "module_path": self.module_path,
            "execute_function": self.execute_function,
            "version": self.version,
            "enabled": self.enabled,
            "parameters": [asdict(p) for p in self.parameters],
            "config_schema": self.config_schema,
            "user_config": self.user_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillConfig":
        """从字典创建。"""
        params = [
            SkillParameter(**p) if isinstance(p, dict) else p
            for p in data.get("parameters", [])
        ]
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data["description"],
            module_path=data["module_path"],
            execute_function=data.get("execute_function", "execute"),
            version=data.get("version", "1.0.0"),
            enabled=data.get("enabled", True),
            parameters=params,
            config_schema=data.get("config_schema", {}),
            user_config=data.get("user_config", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class SkillConfigManager:
    """Skill 配置管理器。"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器。

        Args:
            config_file: 配置文件路径，默认使用项目根目录 skills_config.json
        """
        self.project_root = Path(__file__).parent.parent
        self.config_file = Path(config_file) if config_file else self.project_root / "skills_config.json"
        self._skills: dict[str, SkillConfig] = {}
        self._handlers: dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """从配置文件加载 Skills 配置。"""
        if not self.config_file.exists():
            logger.info(f"配置文件不存在，使用默认 Skills: {self.config_file}")
            self._register_builtin_skills()
            self.save_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for skill_data in data.get("skills", []):
                config = SkillConfig.from_dict(skill_data)
                self._skills[config.skill_id] = config
                if config.enabled:
                    self._load_skill_handler(config)

            logger.info(f"已加载 {len(self._skills)} 个 Skills")
        except Exception as e:
            logger.error(f"加载配置文件失败：{e}", exc_info=True)
            self._register_builtin_skills()

    def _register_builtin_skills(self):
        """注册内置 Skills（硬编码的默认 Skills）。"""
        # 联通客服问答
        self._skills["liantong_ai_query"] = SkillConfig(
            skill_id="liantong_ai_query",
            name="联通 AI 客服问答",
            description="向中国联通 AI 客服提问并获取回复",
            module_path="skills.liantong_ai_query.skill",
            execute_function="execute",
            parameters=[
                SkillParameter("question", "str", "要提问的问题内容", required=True),
                SkillParameter("app_name", "str", "应用名称", required=False, default="中国联通"),
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "默认应用名称"}
                }
            },
            user_config={"app_name": "中国联通"}
        )

        # Excel 工具
        self._skills["excel_tools"] = SkillConfig(
            skill_id="excel_tools",
            name="Excel 工具",
            description="从 Excel 读取问题和写入答案",
            module_path="skills.excel_tools.skill",
            execute_function="get_excel_question",  # 默认函数，实际通过不同函数调用
            parameters=[
                SkillParameter("file", "str", "Excel 文件路径", required=True),
                SkillParameter("row", "int", "行号", required=False),
                SkillParameter("question_column", "str", "问题列名", required=False, default="问题"),
                SkillParameter("answer_column", "str", "答案列名", required=False, default="答案"),
            ],
            config_schema={
                "type": "object",
                "properties": {
                    "question_column": {"type": "string", "default": "问题"},
                    "answer_column": {"type": "string", "default": "答案"}
                }
            },
            user_config={"question_column": "问题", "answer_column": "答案"}
        )

    def _load_skill_handler(self, config: SkillConfig):
        """动态加载 Skill 处理器。"""
        try:
            module = importlib.import_module(config.module_path)
            handler = getattr(module, config.execute_function, None)

            if handler is None:
                # 尝试获取模块中的 execute 函数
                handler = getattr(module, "execute", None)

            if handler:
                self._handlers[config.skill_id] = handler
                logger.info(f"成功加载 Skill: {config.skill_id}")
            else:
                logger.error(f"Skill {config.skill_id} 未找到执行函数")
        except Exception as e:
            logger.error(f"加载 Skill 模块失败 {config.module_path}: {e}")

    def get_handler(self, skill_id: str) -> Optional[Any]:
        """获取 Skill 处理器。"""
        return self._handlers.get(skill_id)

    def get_config(self, skill_id: str) -> Optional[SkillConfig]:
        """获取 Skill 配置。"""
        return self._skills.get(skill_id)

    def list_skills(self) -> list[dict]:
        """列出所有 Skills。"""
        return [config.to_dict() for config in self._skills.values()]

    def get_skill_info(self, skill_id: str) -> Optional[dict]:
        """获取 Skill 详细信息。"""
        config = self._skills.get(skill_id)
        return config.to_dict() if config else None

    def add_skill(self, config: SkillConfig) -> bool:
        """
        添加新的 Skill。

        Args:
            config: Skill 配置

        Returns:
            是否成功
        """
        if config.skill_id in self._skills:
            logger.error(f"Skill 已存在：{config.skill_id}")
            return False

        self._skills[config.skill_id] = config

        if config.enabled:
            self._load_skill_handler(config)

        self.save_config()
        logger.info(f"添加 Skill: {config.skill_id}")
        return True

    def update_skill(self, skill_id: str, updates: dict) -> bool:
        """
        更新 Skill 配置。

        Args:
            skill_id: Skill ID
            updates: 更新内容

        Returns:
            是否成功
        """
        config = self._skills.get(skill_id)
        if not config:
            logger.error(f"Skill 不存在：{skill_id}")
            return False

        # 更新字段
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.now().isoformat()

        # 重新加载处理器
        if config.enabled:
            self._load_skill_handler(config)
        elif skill_id in self._handlers:
            del self._handlers[skill_id]

        self.save_config()
        logger.info(f"更新 Skill: {skill_id}")
        return True

    def remove_skill(self, skill_id: str) -> bool:
        """移除 Skill。"""
        if skill_id not in self._skills:
            return False

        del self._skills[skill_id]
        if skill_id in self._handlers:
            del self._handlers[skill_id]

        self.save_config()
        logger.info(f"移除 Skill: {skill_id}")
        return True

    def enable_skill(self, skill_id: str) -> bool:
        """启用 Skill。"""
        return self.update_skill(skill_id, {"enabled": True})

    def disable_skill(self, skill_id: str) -> bool:
        """禁用 Skill。"""
        return self.update_skill(skill_id, {"enabled": False})

    def update_user_config(self, skill_id: str, user_config: dict) -> bool:
        """更新用户配置。"""
        config = self._skills.get(skill_id)
        if not config:
            return False

        # 验证配置
        if config.config_schema:
            if not self._validate_config(user_config, config.config_schema):
                return False

        config.user_config = user_config
        config.updated_at = datetime.now().isoformat()
        self.save_config()
        return True

    def _validate_config(self, config: dict, schema: dict) -> bool:
        """验证用户配置是否符合 Schema。"""
        # 简单的 Schema 验证
        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            for key, value in config.items():
                if key in properties:
                    expected_type = properties[key].get("type")
                    if expected_type == "string" and not isinstance(value, str):
                        return False
                    elif expected_type == "integer" and not isinstance(value, int):
                        return False
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        return False
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        return False
        return True

    def save_config(self):
        """保存配置到文件。"""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "skills": [config.to_dict() for config in self._skills.values()],
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存：{self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败：{e}")

    def execute_skill(self, skill_id: str, **kwargs) -> dict[str, Any]:
        """
        执行 Skill。

        Args:
            skill_id: Skill ID
            **kwargs: 执行参数

        Returns:
            执行结果
        """
        handler = self.get_handler(skill_id)
        if not handler:
            return {"success": False, "error": f"Skill 不存在或未启用：{skill_id}"}

        config = self.get_config(skill_id)
        if not config:
            return {"success": False, "error": f"Skill 配置不存在：{skill_id}"}

        try:
            # 合并用户配置和调用参数（调用参数优先级更高）
            merged_kwargs = {**config.user_config, **kwargs}
            result = handler(**merged_kwargs)
            return result
        except Exception as e:
            logger.error(f"Skill 执行失败 {skill_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}


# 全局单例
_manager: Optional[SkillConfigManager] = None


def get_manager() -> SkillConfigManager:
    """获取全局配置管理器实例。"""
    global _manager
    if _manager is None:
        _manager = SkillConfigManager()
    return _manager


def list_skills() -> list[dict]:
    """列出所有 Skills。"""
    return get_manager().list_skills()


def get_skill_info(skill_id: str) -> Optional[dict]:
    """获取 Skill 信息。"""
    return get_manager().get_skill_info(skill_id)


def execute_skill(skill_id: str, **kwargs) -> dict[str, Any]:
    """执行 Skill。"""
    return get_manager().execute_skill(skill_id, **kwargs)


def add_skill(config: SkillConfig) -> bool:
    """添加 Skill。"""
    return get_manager().add_skill(config)


def update_skill(skill_id: str, updates: dict) -> bool:
    """更新 Skill 配置。"""
    return get_manager().update_skill(skill_id, updates)


def remove_skill(skill_id: str) -> bool:
    """移除 Skill。"""
    return get_manager().remove_skill(skill_id)
