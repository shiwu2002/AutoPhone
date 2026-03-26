"""
Excel Tools Skill - Excel 文件处理技能

此技能集用于处理 Excel 文件，包括：
- 读取 Excel 文件内容
- 写入数据到 Excel
- 预览 Excel 文件
- 批量执行任务
- 答案对比
"""

import json
from pathlib import Path
from typing import Any, Optional, List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("Warning: pandas not installed. Excel support will be limited.")


def read_excel_execute(
    file_path: str,
    sheet_name: str = None
) -> dict:
    """
    读取 Excel 文件技能执行函数

    Args:
        file_path: Excel 文件路径
        sheet_name: 工作表名称（可选）

    Returns:
        dict: 读取结果
    """
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}

        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file_path}"}

        # 读取 Excel
        if sheet_name:
            df = pd.read_excel(path, sheet_name=sheet_name)
        else:
            # 读取第一个工作表
            excel_file = pd.ExcelFile(path)
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(path, sheet_name=sheet_name)

        # 转换为字典格式
        data = df.to_dict('records')

        return {
            "success": True,
            "columns": df.columns.tolist(),
            "data": data,
            "row_count": len(df),
            "sheet_name": sheet_name,
            "message": f"成功读取 {len(df)} 行数据"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def write_excel_execute(
    file_path: str,
    data: str,
    sheet_name: str = "Sheet1"
) -> dict:
    """
    写入 Excel 文件技能执行函数

    Args:
        file_path: Excel 文件路径
        data: JSON 格式的数据字符串
        sheet_name: 工作表名称

    Returns:
        dict: 写入结果
    """
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}

        # 解析 JSON 数据
        try:
            data_list = json.loads(data)
            if not isinstance(data_list, list):
                data_list = [data_list]
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败：{e}"}

        # 创建 DataFrame 并写入
        df = pd.DataFrame(data_list)

        # 确保目录存在
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 写入 Excel
        df.to_excel(path, sheet_name=sheet_name, index=False)

        return {
            "success": True,
            "file_path": str(file_path),
            "row_count": len(df),
            "sheet_name": sheet_name,
            "message": f"成功写入 {len(df)} 行数据到 {sheet_name}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def preview_excel_execute(
    file_path: str,
    question_column: str = None
) -> dict:
    """
    Excel 文件预览技能执行函数

    Args:
        file_path: Excel 文件路径
        question_column: 问题列名（可选）

    Returns:
        dict: 预览结果
    """
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}

        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file_path}"}

        df = pd.read_excel(path)
        columns = df.columns.tolist()

        # 自动检测问题列
        if not question_column:
            for col in columns:
                col_lower = col.lower()
                if '问题' in col_lower or 'question' in col_lower or '题目' in col_lower:
                    question_column = col
                    break
            if not question_column:
                question_column = columns[0] if columns else None

        if not question_column:
            return {"success": False, "error": "无法确定问题列"}

        # 提取问题列表
        questions = df[question_column].dropna().astype(str).tolist()
        questions = [q.strip() for q in questions if q.strip() and q != 'nan']

        return {
            "success": True,
            "columns": columns,
            "question_column": question_column,
            "questions": questions,
            "count": len(questions),
            "message": f"检测到 {len(questions)} 个问题"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def batch_execute_execute(
    file_path: str,
    task_template: str,
    output_file: str = None,
    embed_screenshot: bool = False,
    column: str = None
) -> dict:
    """
    Excel 批量任务执行技能执行函数

    Args:
        file_path: Excel 文件路径
        task_template: 任务模板描述
        output_file: 输出文件路径
        embed_screenshot: 是否嵌入截图
        column: 问题列名

    Returns:
        dict: 批量执行结果
    """
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}

        # 导入 PhoneAgent
        try:
            from phone_agent import PhoneAgent
            from phone_agent.agent import AgentConfig
            from phone_agent.model import ModelConfig
            from phone_agent.device_factory import get_device_factory

            # 加载配置
            config_path = Path(__file__).parent.parent.parent / "config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            model_config_data = config.get('model', {})
            provider = model_config_data.get('provider', 'local')
            provider_config = model_config_data.get(provider, {})

            model_config = ModelConfig(
                base_url=model_config_data.get('base_url') or provider_config.get('base_url', 'http://localhost:11434/v1'),
                model_name=model_config_data.get('model') or provider_config.get('model', 'qwen3.5:4b'),
                api_key=model_config_data.get('api_key') or provider_config.get('api_key', 'EMPTY'),
                use_thinking=model_config_data.get('use_thinking', False),
                lang=config.get('agent', {}).get('lang', 'cn'),
                provider=provider,
            )

            agent_config = AgentConfig(
                max_steps=int(config.get('agent', {}).get('max_steps', 100)),
                device_id=config.get('agent', {}).get('device_id'),
                lang=config.get('agent', {}).get('lang', 'cn'),
                verbose=bool(config.get('agent', {}).get('verbose', True)),
            )

            PHONE_AGENT_AVAILABLE = True
        except Exception as e:
            print(f"Warning: PhoneAgent not available: {e}")
            PHONE_AGENT_AVAILABLE = False

        # 读取 Excel
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"文件不存在：{file_path}"}

        df = pd.read_excel(path)

        # 确定问题列
        if not column:
            for col in df.columns:
                col_lower = col.lower()
                if '问题' in col_lower or 'question' in col_lower:
                    column = col
                    break
            if not column:
                column = df.columns[0]

        # 获取问题列表
        questions = df[column].dropna().astype(str).tolist()
        questions = [q.strip() for q in questions if q.strip() and q != 'nan']

        results = []
        success_count = 0

        # 处理每个问题
        for i, question in enumerate(questions):
            # 替换任务模板中的占位符
            task = task_template.replace("{question}", question)

            result = {
                "question": question,
                "answer": "",
                "success": False,
                "steps": 0
            }

            if PHONE_AGENT_AVAILABLE:
                try:
                    # 检查设备
                    devices = get_device_factory().list_devices()
                    if not devices:
                        result["error"] = "没有可用的 ADB 设备"
                        results.append(result)
                        continue

                    agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
                    answer = agent.run(task)

                    result["answer"] = str(answer)
                    result["success"] = True
                    result["steps"] = agent.step_count
                    success_count += 1

                except Exception as e:
                    result["error"] = str(e)
            else:
                result["error"] = "PhoneAgent 不可用"

            results.append(result)
            print(f"处理进度：{i+1}/{len(questions)}")

        # 写入结果
        output_path = output_file or file_path

        # 准备输出数据
        output_data = []
        for r in results:
            row = {"question": r["question"], "answer": r["answer"], "success": r["success"]}
            if "error" in r:
                row["error"] = r["error"]
            if "steps" in r:
                row["steps"] = r["steps"]
            output_data.append(row)

        # 写入 Excel
        output_df = pd.DataFrame(output_data)
        output_df.to_excel(output_path, index=False)

        return {
            "success": True,
            "results": [
                {"question": r["question"], "answer": r["answer"], "success": r["success"]}
                for r in results
            ],
            "output_file": str(output_path),
            "statistics": {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            },
            "message": f"批量处理完成，成功 {success_count}/{len(results)}"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def compare_answers_execute(
    ai_answer: str,
    standard_answer: str
) -> dict:
    """
    答案对比技能执行函数

    Args:
        ai_answer: AI 生成的答案
        standard_answer: 标准答案

    Returns:
        dict: 对比结果
    """
    try:
        # 简单文本对比
        ai_text = ai_answer.strip().lower()
        std_text = standard_answer.strip().lower()

        # 完全匹配
        if ai_text == std_text:
            return {
                "success": True,
                "similarity": 1.0,
                "is_correct": True,
                "analysis": "答案完全匹配"
            }

        # 检查是否包含关键内容
        # 简单实现：检查标准答案的关键词是否出现在 AI 答案中
        std_words = set(std_text.split())
        ai_words = set(ai_text.split())

        common_words = std_words & ai_words
        if len(std_words) > 0:
            similarity = len(common_words) / len(std_words)
        else:
            similarity = 0

        # 判断是否正确（相似度超过 50%）
        is_correct = similarity >= 0.5

        return {
            "success": True,
            "similarity": round(similarity, 2),
            "is_correct": is_correct,
            "analysis": f"相似度：{similarity:.0%}，共同关键词：{len(common_words)} 个"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# 主执行函数
def execute(sub_skill_id: str, **kwargs) -> dict:
    """
    Excel Tools 主执行函数

    Args:
        sub_skill_id: 子技能 ID
        **kwargs: 子技能参数

    Returns:
        dict: 执行结果
    """
    executors = {
        "read_excel": read_excel_execute,
        "write_excel": write_excel_execute,
        "preview_excel": preview_excel_execute,
        "batch_execute": batch_execute_execute,
        "compare_answers": compare_answers_execute,
    }

    if sub_skill_id not in executors:
        return {"success": False, "error": f"未知的子技能：{sub_skill_id}"}

    executor = executors[sub_skill_id]
    return executor(**kwargs)
