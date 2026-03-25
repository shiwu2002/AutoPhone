"""Skill 模板生成器 - 帮助用户快速创建新的 Skill。

功能：
1. 生成 Skill 代码模板
2. 生成配置 JSON
3. 验证 Skill 结构
4. 提供 Skill 开发指南
"""

import json
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


# ============== Skill 代码模板 ==============

SKILL_CODE_TEMPLATE = '''"""{skill_name} - {skill_description}。

此 Skill 用于 {skill_purpose}。
"""

import json
from pathlib import Path
from typing import Any, Optional

from phone_agent.hooks import trigger_hook
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)

# Skill 元数据
SKILL_METADATA = {{
    "id": "{skill_id}",
    "name": "{skill_name}",
    "description": "{skill_description}",
    "version": "1.0.0",
}}


def execute({execute_params}) -> dict[str, Any]:
    """
    执行 {skill_name} Skill。

    Args:
{execute_docstring_params}

    Returns:
        包含 success 和执行结果的字典
    """
    logger.info(f"[{{SKILL_METADATA['id']}}] 开始执行")

    # 触发 Skill 开始钩子
    trigger_hook("on_skill_start", skill_id=SKILL_METADATA["id"])

    try:
        # ========== 在此处编写你的 Skill 逻辑 ==========
        # 示例：
        # result = do_something(param1, param2)

        result = {{
            "success": True,
            "data": "执行结果数据"
        }}
        # =========================================

        logger.info(f"[{{SKILL_METADATA['id']}}] 执行完成")

        # 触发 Skill 完成钩子
        trigger_hook(
            "on_skill_complete",
            skill_id=SKILL_METADATA["id"],
            result=result
        )

        return result

    except Exception as e:
        logger.error(f"[{{SKILL_METADATA['id']}}] 执行失败：{{e}}", exc_info=True)

        # 触发 Skill 失败钩子
        trigger_hook(
            "on_skill_error",
            skill_id=SKILL_METADATA["id"],
            error=str(e)
        )

        return {{
            "success": False,
            "error": str(e)
        }}


def get_metadata() -> dict:
    """获取 Skill 元数据。"""
    return SKILL_METADATA
'''


# ============== Skill 配置模板 ==============

SKILL_CONFIG_TEMPLATE = {
    "skill_id": "{skill_id}",
    "name": "{skill_name}",
    "description": "{skill_description}",
    "module_path": "{module_path}",
    "execute_function": "execute",
    "version": "1.0.0",
    "enabled": True,
    "parameters": [],
    "config_schema": {
        "type": "object",
        "properties": {}
    },
    "user_config": {},
    "created_at": "{created_at}",
    "updated_at": "{updated_at}"
}


# ============== 参数类型定义 ==============

PARAM_TYPES = {
    "str": {"type": "str", "example": '"文本内容"', "description": "字符串"},
    "int": {"type": "int", "example": "123", "description": "整数"},
    "float": {"type": "float", "example": "3.14", "description": "浮点数"},
    "bool": {"type": "bool", "example": "True/False", "description": "布尔值"},
    "list": {"type": "list", "example": '["item1", "item2"]', "description": "列表"},
    "dict": {"type": "dict", "example": '{"key": "value"}', "description": "字典"},
    "file": {"type": "str", "example": '"path/to/file.xlsx"', "description": "文件路径"},
}


class SkillTemplateGenerator:
    """Skill 模板生成器。"""

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化生成器。

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.skills_dir = self.project_root / "skills"

    def create_skill(
        self,
        skill_id: str,
        skill_name: str,
        skill_description: str,
        skill_purpose: str,
        parameters: list[dict[str, Any]],
        config_schema: Optional[dict] = None,
        user_config: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        创建新的 Skill。

        Args:
            skill_id: Skill 唯一标识（英文，如 liantong_ai_query）
            skill_name: Skill 名称（中文，如联通 AI 客服问答）
            skill_description: Skill 描述
            skill_purpose: Skill 用途说明
            parameters: 参数列表，每项包含 name, type, description, required, default
            config_schema: 用户配置 Schema（可选）
            user_config: 默认用户配置（可选）

        Returns:
            包含成功状态和生成文件路径的字典
        """
        try:
            # 1. 创建 Skill 目录
            skill_dir = self.skills_dir / skill_id
            skill_dir.mkdir(parents=True, exist_ok=True)

            # 2. 生成参数相关代码
            execute_params = self._generate_execute_params(parameters)
            execute_docstring_params = self._generate_docstring_params(parameters)

            # 3. 生成 Skill 代码
            code = SKILL_CODE_TEMPLATE.format(
                skill_id=skill_id,
                skill_name=skill_name,
                skill_description=skill_description,
                skill_purpose=skill_purpose,
                execute_params=execute_params,
                execute_docstring_params=execute_docstring_params,
            )

            # 4. 写入 skill.py
            skill_file = skill_dir / "skill.py"
            with open(skill_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # 5. 生成 __init__.py
            init_content = f'''"""{skill_name} Skill 包。"""

from .skill import execute, get_metadata, SKILL_METADATA

__all__ = ["execute", "get_metadata", "SKILL_METADATA"]
'''
            init_file = skill_dir / "__init__.py"
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_content)

            # 6. 生成配置
            config = self._generate_config(
                skill_id=skill_id,
                skill_name=skill_name,
                skill_description=skill_description,
                module_path=f"skills.{skill_id}.skill",
                parameters=parameters,
                config_schema=config_schema,
                user_config=user_config,
            )

            # 7. 更新或创建 skills_config.json
            self._update_skills_config(config)

            logger.info(f"Skill 创建成功：{skill_id}")

            return {
                "success": True,
                "skill_id": skill_id,
                "skill_dir": str(skill_dir),
                "skill_file": str(skill_file),
                "config": config,
                "message": f"Skill '{skill_name}' 创建成功！\n\n文件位置：\n- 代码：{skill_file}\n- 配置已添加到 skills_config.json"
            }

        except Exception as e:
            logger.error(f"创建 Skill 失败：{e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_execute_params(self, parameters: list[dict]) -> str:
        """生成执行函数的参数字符串。"""
        params = []
        for param in parameters:
            name = param.get("name", "param")
            param_type = param.get("type", "str")
            required = param.get("required", True)
            default = param.get("default")

            if not required and default is not None:
                if param_type == "str":
                    params.append(f"{name}: str = \"{default}\"")
                elif param_type == "bool":
                    params.append(f"{name}: bool = {str(default)}")
                else:
                    params.append(f"{name}: {param_type} = {default}")
            else:
                if param_type == "str":
                    params.append(f"{name}: str")
                elif param_type == "int":
                    params.append(f"{name}: int")
                elif param_type == "float":
                    params.append(f"{name}: float")
                elif param_type == "bool":
                    params.append(f"{name}: bool")
                elif param_type == "list":
                    params.append(f"{name}: list")
                elif param_type == "dict":
                    params.append(f"{name}: dict")
                else:
                    params.append(f"{name}: Any")

        return ", ".join(params)

    def _generate_docstring_params(self, parameters: list[dict]) -> str:
        """生成文档字符串中的参数说明。"""
        lines = []
        for param in parameters:
            name = param.get("name", "param")
            param_type = param.get("type", "str")
            description = param.get("description", "")
            required = param.get("required", True)
            default = param.get("default")

            req_str = "必填" if required else "可选"
            default_str = f"，默认值：{default}" if default is not None else ""
            lines.append(f"        {name}: {description}（{req_str}{default_str}）")

        return "\n".join(lines)

    def _generate_config(
        self,
        skill_id: str,
        skill_name: str,
        skill_description: str,
        module_path: str,
        parameters: list[dict],
        config_schema: Optional[dict] = None,
        user_config: Optional[dict] = None,
    ) -> dict:
        """生成 Skill 配置。"""
        now = datetime.now().isoformat()

        config = SKILL_CONFIG_TEMPLATE.copy()
        config["skill_id"] = skill_id
        config["name"] = skill_name
        config["description"] = skill_description
        config["module_path"] = module_path
        config["created_at"] = now
        config["updated_at"] = now
        config["parameters"] = parameters
        config["config_schema"] = config_schema or {"type": "object", "properties": {}}
        config["user_config"] = user_config or {}

        return config

    def _update_skills_config(self, new_config: dict):
        """更新或创建 skills_config.json。"""
        config_file = self.project_root / "skills_config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"version": "1.0", "skills": []}

        # 检查是否已存在
        for i, skill in enumerate(data.get("skills", [])):
            if skill.get("skill_id") == new_config["skill_id"]:
                # 更新现有配置
                data["skills"][i] = new_config
                break
        else:
            # 添加新配置
            data["skills"].append(new_config)

        data["updated_at"] = datetime.now().isoformat()

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def validate_skill(self, skill_id: str) -> dict[str, Any]:
        """
        验证 Skill 是否有效。

        Args:
            skill_id: Skill ID

        Returns:
            验证结果
        """
        errors = []
        warnings = []

        # 检查目录是否存在
        skill_dir = self.skills_dir / skill_id
        if not skill_dir.exists():
            return {"valid": False, "errors": [f"Skill 目录不存在：{skill_dir}"]}

        # 检查 skill.py 是否存在
        skill_file = skill_dir / "skill.py"
        if not skill_file.exists():
            errors.append(f"缺少 skill.py 文件")

        # 检查 __init__.py 是否存在
        init_file = skill_dir / "__init__.py"
        if not init_file.exists():
            warnings.append("缺少 __init__.py 文件（推荐添加）")

        # 尝试导入模块
        try:
            import importlib
            module = importlib.import_module(f"skills.{skill_id}.skill")

            # 检查是否有 execute 函数
            if not hasattr(module, "execute"):
                errors.append("模块中缺少 execute 函数")

            # 检查 execute 函数签名
            if hasattr(module, "execute"):
                import inspect
                sig = inspect.signature(module.execute)
                if len(sig.parameters) == 0:
                    warnings.append("execute 函数没有参数，可能无法接收输入")

        except ImportError as e:
            errors.append(f"无法导入模块：{e}")
        except Exception as e:
            errors.append(f"验证出错：{e}")

        # 检查配置是否存在
        config_file = self.project_root / "skills_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            config_exists = any(
                s.get("skill_id") == skill_id
                for s in config_data.get("skills", [])
            )
            if not config_exists:
                warnings.append("Skill 未在 skills_config.json 中注册")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def get_template_examples(self) -> list[dict]:
        """获取模板示例。"""
        return [
            {
                "id": "query_api",
                "name": "API 查询技能",
                "description": "调用外部 API 获取数据",
                "purpose": "通过 HTTP 请求调用第三方 API 服务",
                "parameters": [
                    {"name": "url", "type": "str", "description": "API 地址", "required": True},
                    {"name": "method", "type": "str", "description": "HTTP 方法", "required": False, "default": "GET"},
                    {"name": "params", "type": "dict", "description": "请求参数", "required": False, "default": None},
                ]
            },
            {
                "id": "file_processor",
                "name": "文件处理技能",
                "description": "处理指定类型的文件",
                "purpose": "读取、转换或分析文件内容",
                "parameters": [
                    {"name": "file", "type": "str", "description": "文件路径", "required": True},
                    {"name": "output_dir", "type": "str", "description": "输出目录", "required": False, "default": "./output"},
                ]
            },
            {
                "id": "data_analyzer",
                "name": "数据分析技能",
                "description": "分析数据并生成报告",
                "purpose": "对数据进行统计分析并输出结果",
                "parameters": [
                    {"name": "data_source", "type": "str", "description": "数据源", "required": True},
                    {"name": "metrics", "type": "list", "description": "分析指标", "required": False, "default": ["count", "sum", "avg"]},
                ]
            }
        ]


# 全局实例
_generator: Optional[SkillTemplateGenerator] = None


def get_generator() -> SkillTemplateGenerator:
    """获取全局生成器实例。"""
    global _generator
    if _generator is None:
        _generator = SkillTemplateGenerator()
    return _generator


def create_skill(**kwargs) -> dict[str, Any]:
    """创建 Skill 的便捷函数。"""
    return get_generator().create_skill(**kwargs)


def validate_skill(skill_id: str) -> dict[str, Any]:
    """验证 Skill。"""
    return get_generator().validate_skill(skill_id)


def get_examples() -> list[dict]:
    """获取模板示例。"""
    return get_generator().get_template_examples()
