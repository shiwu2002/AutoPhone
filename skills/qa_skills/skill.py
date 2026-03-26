"""
QA Skills - 问答技能执行模块

面向用户的问答功能技能，支持通过手机 APP 进行问答。
"""

import json
from pathlib import Path
from typing import Any

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def liantong_qa_execute(question: str) -> dict:
    """
    联通客服问答技能执行函数
    """
    try:
        from phone_agent import PhoneAgent
        from phone_agent.agent import AgentConfig
        from phone_agent.model import ModelConfig
        from phone_agent.device_factory import get_device_factory

        # 加载配置
        config_path = Path(__file__).parent.parent / "config.json"
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
            max_steps=int(config.get('agent', {}).get('max_steps', 15)),
            device_id=config.get('agent', {}).get('device_id'),
            lang=config.get('agent', {}).get('lang', 'cn'),
            verbose=bool(config.get('agent', {}).get('verbose', True)),
        )

        # 检查设备
        devices = get_device_factory().list_devices()
        if not devices:
            return {"success": False, "error": "没有可用的 ADB 设备"}

        # 构建任务提示词
        prompt = f"""你的任务是通过联通 APP 的 AI 客服来回答问题。

问题：{question}

流程：
1. 打开中国联通 APP
2. 点击右上角机器人/客服图标
3. 将问题发送给 AI 客服
4. 等待 AI 回复
5. 记录 AI 的原始回复内容

返回 JSON 格式：
{{"success": true/false, "answer": "AI 客服的回复内容", "message": "执行状态信息"}}"""

        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        result = agent.run(prompt)

        return {
            "success": True,
            "answer": str(result),
            "message": "问答完成"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def excel_qa_batch_execute(
    file_path: str,
    task_template: str,
    output_file: str = None,
    column: str = None
) -> dict:
    """
    Excel 批量问答技能执行函数
    """
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}

        from phone_agent import PhoneAgent
        from phone_agent.agent import AgentConfig
        from phone_agent.model import ModelConfig
        from phone_agent.device_factory import get_device_factory

        # 加载配置
        config_path = Path(__file__).parent.parent / "config.json"
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
            max_steps=int(config.get('agent', {}).get('max_steps', 50)),
            device_id=config.get('agent', {}).get('device_id'),
            lang=config.get('agent', {}).get('lang', 'cn'),
            verbose=bool(config.get('agent', {}).get('verbose', True)),
        )

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

        questions = df[column].dropna().astype(str).tolist()
        questions = [q.strip() for q in questions if q.strip() and q != 'nan']

        results = []
        success_count = 0

        # 检查设备
        devices = get_device_factory().list_devices()
        if not devices:
            return {"success": False, "error": "没有可用的 ADB 设备"}

        for i, question in enumerate(questions):
            task = task_template.replace("{question}", question)
            result_item = {"question": question, "answer": "", "success": False}

            try:
                agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
                answer = agent.run(task)
                result_item["answer"] = str(answer)
                result_item["success"] = True
                success_count += 1
            except Exception as e:
                result_item["error"] = str(e)

            results.append(result_item)
            print(f"处理进度：{i+1}/{len(questions)}")

        # 写入结果
        output_path = output_file or file_path
        output_df = pd.DataFrame([{"question": r["question"], "answer": r["answer"], "success": r["success"]} for r in results])
        output_df.to_excel(output_path, index=False)

        return {
            "success": True,
            "results": [{"question": r["question"], "answer": r["answer"], "success": r["success"]} for r in results],
            "output_file": str(output_path),
            "statistics": {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def compare_answer_execute(ai_answer: str, standard_answer: str) -> dict:
    """
    答案对比技能执行函数
    """
    try:
        ai_text = ai_answer.strip().lower()
        std_text = standard_answer.strip().lower()

        if ai_text == std_text:
            return {
                "success": True,
                "similarity": 1.0,
                "is_correct": True,
                "analysis": "答案完全匹配"
            }

        std_words = set(std_text.split())
        ai_words = set(ai_text.split())
        common_words = std_words & ai_words

        similarity = len(common_words) / len(std_words) if std_words else 0
        is_correct = similarity >= 0.5

        return {
            "success": True,
            "similarity": round(similarity, 2),
            "is_correct": is_correct,
            "analysis": f"相似度：{similarity:.0%}，共同关键词：{len(common_words)} 个"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute(sub_skill_id: str, **kwargs) -> dict:
    """
    QA Skills 主执行函数
    """
    executors = {
        "liantong_qa": liantong_qa_execute,
        "excel_qa_batch": excel_qa_batch_execute,
        "compare_answer": compare_answer_execute,
    }

    if sub_skill_id not in executors:
        return {"success": False, "error": f"未知的子技能：{sub_skill_id}"}

    executor = executors[sub_skill_id]
    return executor(**kwargs)
