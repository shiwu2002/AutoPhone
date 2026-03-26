"""
PhoneAgent Skills 执行引擎

负责：
1. 加载技能书配置
2. 处理占位符替换（如 {question}）
3. 执行子技能并返回 JSON 结果
4. 管理技能的输入输出
"""

import json
import re
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class ParameterDef:
    """参数定义"""
    name: str
    type: str  # str, int, bool, json
    description: str
    required: bool = True
    default: Any = None


@dataclass
class OutputDef:
    """输出定义"""
    field: str
    type: str  # text, json
    description: str


@dataclass
class SubSkill:
    """子技能定义"""
    id: str
    name: str
    description: str
    prompt_template: str
    input_params: list[ParameterDef] = field(default_factory=list)
    output_config: Optional[OutputDef] = None
    timeout: int = 60
    max_steps: int = 10


@dataclass
class SkillBook:
    """技能书定义"""
    id: str
    name: str
    description: str
    icon: str = "📖"
    version: str = "1.0.0"
    sub_skills: list[SubSkill] = field(default_factory=list)


class SkillManager:
    """技能管理器"""

    def __init__(self, config_path: str = None):
        """
        初始化技能管理器

        Args:
            config_path: skill_books.json 文件路径
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "skill_books.json"
        self.config_path = Path(config_path)
        self.books: dict[str, SkillBook] = {}
        self.sub_skills: dict[str, SubSkill] = {}
        self._load_config()

    def _load_config(self):
        """加载技能书配置"""
        if not self.config_path.exists():
            print(f"Warning: Skill config not found at {self.config_path}")
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for book_data in data.get('books', []):
                book = self._parse_skill_book(book_data)
                self.books[book.id] = book

                for sub_skill in book.sub_skills:
                    key = f"{book.id}/{sub_skill.id}"
                    self.sub_skills[key] = sub_skill

            print(f"Loaded {len(self.books)} skill books, {len(self.sub_skills)} sub-skills")

        except Exception as e:
            print(f"Error loading skill config: {e}")

    def _parse_skill_book(self, data: dict) -> SkillBook:
        """解析技能书数据"""
        sub_skills = []
        for sk_data in data.get('sub_skills', []):
            sub_skill = self._parse_sub_skill(sk_data)
            sub_skills.append(sub_skill)

        return SkillBook(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            icon=data.get('icon', '📖'),
            version=data.get('version', '1.0.0'),
            sub_skills=sub_skills
        )

    def _parse_sub_skill(self, data: dict) -> SubSkill:
        """解析子技能数据"""
        input_params = []
        for p_data in data.get('input_params', []):
            param = ParameterDef(
                name=p_data.get('name', ''),
                type=p_data.get('type', 'str'),
                description=p_data.get('description', ''),
                required=p_data.get('required', True),
                default=p_data.get('default')
            )
            input_params.append(param)

        output_config = None
        if data.get('output_config'):
            oc = data['output_config']
            output_config = OutputDef(
                field=oc.get('field', 'result'),
                type=oc.get('type', 'text'),
                description=oc.get('description', '')
            )

        return SubSkill(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            prompt_template=data.get('prompt_template', ''),
            input_params=input_params,
            output_config=output_config,
            timeout=data.get('timeout', 60),
            max_steps=data.get('max_steps', 10)
        )

    def list_books(self) -> list[str]:
        """列出所有技能书 ID"""
        return list(self.books.keys())

    def get_book(self, book_id: str) -> Optional[SkillBook]:
        """获取技能书"""
        return self.books.get(book_id)

    def get_sub_skill(self, book_id: str, sub_skill_id: str) -> Optional[SubSkill]:
        """获取子技能"""
        key = f"{book_id}/{sub_skill_id}"
        return self.sub_skills.get(key)

    def build_prompt(self, book_id: str, sub_skill_id: str, **kwargs) -> str:
        """
        构建带有占位符替换的提示词

        Args:
            book_id: 技能书 ID
            sub_skill_id: 子技能 ID
            **kwargs: 参数值

        Returns:
            str: 替换后的提示词
        """
        sub_skill = self.get_sub_skill(book_id, sub_skill_id)
        if not sub_skill:
            raise ValueError(f"Sub-skill not found: {book_id}/{sub_skill_id}")

        prompt = sub_skill.prompt_template

        # 替换占位符
        for param in sub_skill.input_params:
            value = kwargs.get(param.name, param.default)
            if value is None and param.required:
                raise ValueError(f"Missing required parameter: {param.name}")

            # 将值转换为字符串并转义 JSON 特殊字符
            if value is not None:
                if param.type == 'json' and isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                prompt = prompt.replace(f"{{{param.name}}}", value_str)

        return prompt

    def execute(
        self,
        book_id: str,
        sub_skill_id: str,
        phone_agent=None,
        **kwargs
    ) -> dict:
        """
        执行子技能

        Args:
            book_id: 技能书 ID
            sub_skill_id: 子技能 ID
            phone_agent: PhoneAgent 实例
            **kwargs: 输入参数

        Returns:
            dict: 执行结果（JSON 格式）
        """
        sub_skill = self.get_sub_skill(book_id, sub_skill_id)
        if not sub_skill:
            return {
                "success": False,
                "error": f"Sub-skill not found: {book_id}/{sub_skill_id}"
            }

        # 构建提示词
        try:
            prompt = self.build_prompt(book_id, sub_skill_id, **kwargs)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # 如果有 phone_agent，使用它执行任务
        if phone_agent:
            try:
                result = phone_agent.run(prompt)
                return self._parse_result(result, sub_skill.output_config)
            except Exception as e:
                return {"success": False, "error": str(e)}

        # 否则尝试使用技能的 execute 函数
        try:
            skill_module = __import__(
                f"skills.{book_id}.skill",
                fromlist=['execute']
            )
            result = skill_module.execute(sub_skill_id, **kwargs)
            return result
        except ImportError:
            return {
                "success": False,
                "error": f"Skill module not found: skills.{book_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _parse_result(self, result: Any, output_config: Optional[OutputDef]) -> dict:
        """解析执行结果"""
        if isinstance(result, dict):
            return result

        if isinstance(result, str):
            # 尝试解析 JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                if output_config:
                    return {output_config.field: result, "success": True}
                return {"result": result, "success": True}

        return {"result": str(result), "success": True}


# 全局管理器实例
_manager: Optional[SkillManager] = None


def get_manager() -> SkillManager:
    """获取技能管理器单例"""
    global _manager
    if _manager is None:
        _manager = SkillManager()
    return _manager


def reload_manager() -> SkillManager:
    """重新加载技能管理器"""
    global _manager
    _manager = SkillManager()
    return _manager
