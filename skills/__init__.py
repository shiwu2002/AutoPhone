"""Skills - 独立技能包。

每个 Skill 都是独立的文件夹，包含完整的执行逻辑和配置。

目录结构:
skills/
├── __init__.py          # 包初始化，导出所有 Skill
├── liantong_ai_query/   # 联通客服问答 Skill
│   ├── __init__.py
│   ├── skill.py         # 主要执行逻辑
│   └── README.md        # 使用说明
└── excel_tools/         # Excel 工具 Skill
    ├── __init__.py
    ├── skill.py         # 主要执行逻辑
    └── README.md        # 使用说明
"""

from skills.liantong_ai_query.skill import execute as liantong_ai_query, get_metadata as get_liantong_metadata
from skills.excel_tools.skill import (
    get_excel_question,
    write_excel_answer,
    execute_excel_batch,
    get_metadata as get_excel_metadata,
)

__all__ = [
    'liantong_ai_query',
    'get_excel_question',
    'write_excel_answer',
    'execute_excel_batch',
    'get_liantong_metadata',
    'get_excel_metadata',
]
