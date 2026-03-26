"""
PhoneAgent Tools Skill - 主技能包

此技能集用于管理 PhoneAgent 的核心功能，包括：
- ADB 设备连接/断开
- 模型配置管理
- 任务执行
- 历史记录查询
- Excel 批量处理
"""

from .skill import execute

__all__ = ["execute"]
