"""Excel 工具 Skill - 主要执行逻辑。

此 Skill 用于从 Excel 读取问题和写入答案。
"""

import json
from pathlib import Path
from typing import Any, Optional

from phone_agent.hooks import trigger_hook
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import pandas
try:
    import pandas as pd
    from openpyxl import load_workbook
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not installed. Excel support will be limited.")


# Skill 元数据
SKILL_METADATA = {
    "id": "excel_tools",
    "name": "Excel 工具",
    "description": "从 Excel 读取问题和写入答案",
    "version": "1.0.0",
}


def get_excel_question(
    file: str,
    row: Optional[int] = None,
    question_column: str = "问题",
    answer_column: str = "答案"
) -> dict[str, Any]:
    """
    从 Excel 读取问题。

    Args:
        file: Excel 文件路径
        row: 行号（不指定则自动获取待处理的行）
        question_column: 问题列名
        answer_column: 答案列名

    Returns:
        包含 file, row, question 的字典
    """
    logger.info(f"[{SKILL_METADATA['id']}] 读取 Excel 问题：{file}")

    trigger_hook("on_skill_start", skill_id=SKILL_METADATA["id"], action="get_question", file=file)

    if not PANDAS_AVAILABLE:
        return {"success": False, "error": "需要安装 pandas 和 openpyxl"}

    try:
        path = Path(file)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file}"}

        df = pd.read_excel(path)

        if question_column not in df.columns:
            return {"success": False, "error": f"列 '{question_column}' 不存在"}

        # 获取指定行或自动获取待处理行
        if row is not None:
            data_index = row - 2
            if data_index < 0 or data_index >= len(df):
                return {"success": False, "error": f"行号超出范围：{row}"}
            question = str(df.iloc[data_index][question_column])
        else:
            data_index = None
            question = None

            if answer_column in df.columns:
                for idx, row_data in df.iterrows():
                    answer = row_data.get(answer_column, '')
                    if pd.isna(answer) or str(answer).strip() == '':
                        data_index = idx
                        question = str(row_data[question_column])
                        row = idx + 2
                        break
            else:
                data_index = 0
                question = str(df.iloc[0][question_column])
                row = 2

            if question is None:
                return {"success": False, "error": "所有行都已处理完成"}

        result = {
            "success": True,
            "file": str(path.absolute()),
            "row": row,
            "question": question
        }

        trigger_hook("on_skill_complete", skill_id=SKILL_METADATA["id"], result=result)
        return result

    except Exception as e:
        logger.error(f"[{SKILL_METADATA['id']}] 读取失败：{e}", exc_info=True)
        trigger_hook("on_skill_error", skill_id=SKILL_METADATA["id"], error=str(e))
        return {"success": False, "error": str(e)}


def write_excel_answer(
    file: str,
    row: int,
    answer: str,
    answer_column: str = "答案"
) -> dict[str, Any]:
    """
    将答案写入 Excel。

    Args:
        file: Excel 文件路径
        row: 行号
        answer: 答案内容
        answer_column: 答案列名

    Returns:
        包含 success 的字典
    """
    logger.info(f"[{SKILL_METADATA['id']}] 写入 Excel 答案：{file}, 行 {row}")

    trigger_hook(
        "on_skill_start",
        skill_id=SKILL_METADATA["id"],
        action="write_answer",
        file=file,
        row=row
    )

    if not PANDAS_AVAILABLE:
        return {"success": False, "error": "需要安装 pandas 和 openpyxl"}

    try:
        path = Path(file)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file}"}

        df = pd.read_excel(path, engine='openpyxl')

        data_index = row - 2
        if data_index < 0 or data_index >= len(df):
            return {"success": False, "error": f"行号超出范围：{row}"}

        if answer_column not in df.columns:
            df[answer_column] = ''

        df.loc[data_index, answer_column] = answer
        df.to_excel(path, index=False, engine='openpyxl')

        result = {
            "success": True,
            "file": str(path.absolute()),
            "row": row,
            "answer": answer
        }

        trigger_hook("on_skill_complete", skill_id=SKILL_METADATA["id"], result=result)
        return result

    except Exception as e:
        logger.error(f"[{SKILL_METADATA['id']}] 写入失败：{e}", exc_info=True)
        trigger_hook("on_skill_error", skill_id=SKILL_METADATA["id"], error=str(e))
        return {"success": False, "error": str(e)}


def execute_excel_batch(
    file: str,
    question_column: str = "问题",
    max_questions: int = 0,
    answer_column: str = "答案"
) -> dict[str, Any]:
    """
    批量执行 Excel 中的任务。

    Args:
        file: Excel 文件路径
        question_column: 问题列名
        max_questions: 最大问题数
        answer_column: 答案列名

    Returns:
        包含待处理问题列表的字典
    """
    logger.info(f"[{SKILL_METADATA['id']}] 批量执行：{file}")

    trigger_hook("on_skill_start", skill_id=SKILL_METADATA["id"], action="batch", file=file)

    if not PANDAS_AVAILABLE:
        return {"success": False, "error": "需要安装 pandas 和 openpyxl"}

    try:
        path = Path(file)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file}"}

        df = pd.read_excel(path, engine='openpyxl')

        if question_column not in df.columns:
            return {"success": False, "error": f"列 '{question_column}' 不存在"}

        # 获取所有问题
        questions = []
        for idx, row_data in df.iterrows():
            excel_row = idx + 2
            question = str(row_data.get(question_column, ''))
            if question and question.strip() and question != 'nan':
                questions.append({
                    "row": excel_row,
                    "question": question.strip()
                })

        if max_questions > 0:
            questions = questions[:max_questions]

        result = {
            "success": True,
            "file": str(path.absolute()),
            "total": len(questions),
            "questions": questions,
        }

        trigger_hook("on_skill_complete", skill_id=SKILL_METADATA["id"], result=result)
        return result

    except Exception as e:
        logger.error(f"[{SKILL_METADATA['id']}] 批量执行失败：{e}", exc_info=True)
        trigger_hook("on_skill_error", skill_id=SKILL_METADATA["id"], error=str(e))
        return {"success": False, "error": str(e)}


def get_metadata() -> dict:
    """获取 Skill 元数据。"""
    return SKILL_METADATA
