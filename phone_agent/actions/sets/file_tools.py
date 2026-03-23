"""文件处理工具集 - Excel 读取和批量执行。"""

import logging
from pathlib import Path
from typing import Any, Optional

from phone_agent.adb.screenshot import Screenshot
from phone_agent.actions.result import ActionResult

logger = logging.getLogger(__name__)

# Try to import pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def handle_read_excel(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    model_config: Any = None,
    agent_config: Any = None,
) -> ActionResult:
    """
    处理读取 Excel 文件动作。

    Args:
        action: 动作字典，包含 file="文件路径", column="列名" (可选)
        screenshot: Screenshot 对象
        device_id: 设备 ID
        model_config: 模型配置
        agent_config: Agent 配置

    Returns:
        ActionResult: 执行结果
    """
    if not PANDAS_AVAILABLE:
        return ActionResult(
            False, False,
            "Excel 工具不可用：需要安装 pandas 和 openpyxl。请运行：pip install pandas openpyxl"
        )

    file_path = action.get("file")
    column = action.get("column", None)

    if not file_path:
        return ActionResult(False, False, "ReadExcel 需要 file 参数")

    path = Path(file_path)
    if not path.exists():
        return ActionResult(False, False, f"文件不存在：{file_path}")

    if path.suffix.lower() not in ['.xlsx', '.xls']:
        return ActionResult(False, False, f"只支持 Excel 文件 (.xlsx, .xls): {file_path}")

    try:
        df = pd.read_excel(path)
        columns = list(df.columns)
        row_count = len(df)

        # 确定读取的列
        if column:
            if column not in columns:
                return ActionResult(
                    False, False,
                    f"列 '{column}' 不存在。可用列：{columns}"
                )
            items = df[column].dropna().tolist()
            preview_items = items[:3]
            preview = ", ".join([str(item) for item in preview_items])
            content_summary = f"列 '{column}' 共 {len(items)} 条数据"
        else:
            # 自动查找"问题"列
            question_col = None
            for col in columns:
                if '问题' in col.lower() or 'question' in col.lower():
                    question_col = col
                    break

            if question_col:
                items = df[question_col].dropna().tolist()
                preview_items = items[:3]
                preview = ", ".join([str(item) for item in preview_items])
                content_summary = f"找到'{question_col}'列，共 {len(items)} 条数据"
                column = question_col
            else:
                preview = f"列：{columns}"
                content_summary = f"共 {row_count} 行，{len(columns)} 列"

        result_message = (
            f"Excel 文件读取成功：{file_path}\n"
            f"列：{columns}\n"
            f"行数：{row_count}\n"
            f"摘要：{content_summary}\n"
            f"前 3 条预览：{preview}\n"
            f"\n请决定如何处理：\n"
            f"- 批量执行：do(action=\"Execute_Excel_Batch\", file=\"{file_path}\", task=\"任务模板\", column=\"{column or '问题'}\")\n"
            f"- 逐个处理：根据内容调用其他工具"
        )

        logger.info(f"Excel 读取成功：{file_path}, {row_count}行")
        return ActionResult(True, False, message=result_message)

    except Exception as e:
        logger.error(f"Excel 读取失败：{e}", exc_info=True)
        return ActionResult(False, False, f"Excel 读取失败：{e}")


def handle_execute_excel_batch(
    action: dict[str, Any],
    screenshot: Screenshot,
    device_id: Optional[str] = None,
    model_config: Any = None,
    agent_config: Any = None,
) -> ActionResult:
    """
    处理 Excel 批量执行动作。

    Args:
        action: 动作字典，包含 file, task, column 等参数
        screenshot: Screenshot 对象
        device_id: 设备 ID
        model_config: 模型配置
        agent_config: Agent 配置

    Returns:
        ActionResult: 执行结果
    """
    if not PANDAS_AVAILABLE:
        return ActionResult(
            False, False,
            "Excel 工具不可用：需要安装 pandas 和 openpyxl。请运行：pip install pandas openpyxl"
        )

    file_path = action.get("file")
    task_template = action.get("task")

    if not file_path or not task_template:
        return ActionResult(
            False, False,
            "Execute_Excel_Batch 需要 file 和 task 参数"
        )

    try:
        from phone_agent.tools.excel_tool import ExcelTool

        # 获取可选参数
        question_column = action.get("column", "问题")
        embed_screenshot = action.get("embed_screenshot", "false").lower() == "true"
        compare_answer = action.get("compare_answer", "false").lower() == "true"
        max_questions = int(action.get("max_questions", 0))

        # 创建 Excel 工具并执行
        tool = ExcelTool(
            model_config=model_config,
            agent_config=agent_config,
        )

        result = tool.execute_batch(
            file_path=file_path,
            task_template=task_template,
            question_column=question_column,
            embed_screenshot=embed_screenshot,
            compare_answer=compare_answer,
            max_questions=max_questions,
        )

        # 返回结果摘要
        summary = result.to_summary()
        logger.info(f"Excel 批量执行完成：{summary}")

        return ActionResult(
            success=True,
            should_finish=False,
            message=f"Excel 批量执行完成：{summary}. 输出文件：{result.output_path}",
        )

    except ImportError as e:
        return ActionResult(
            success=False,
            should_finish=False,
            message=f"Excel 工具不可用：{e}. 请安装：pip install pandas openpyxl",
        )
    except Exception as e:
        logger.error(f"Excel 批量执行失败：{e}", exc_info=True)
        return ActionResult(
            success=False,
            should_finish=False,
            message=f"Excel 批量执行失败：{e}",
        )
