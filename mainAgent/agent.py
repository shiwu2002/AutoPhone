"""主 Agent (MasterAgent) - 智能任务编排和执行。

类似 OpenClaw 的主控智能体，能够：
1. 理解用户意图，自动编排任务
2. 调用 Skills 执行具体操作
3. 执行命令行操作
4. 管理工作文件夹中的文件
5. 多轮对话，记住上下文
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from mainAgent.skills import execute_skill, list_skills, get_skill_info
from mainAgent.skill_config import get_manager as get_skill_config_manager
from phone_agent.hooks import trigger_hook
from phone_agent.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MasterAgentConfig:
    """主 Agent 配置。"""
    lang: str = "zh"
    verbose: bool = True
    work_folder: str = ""  # 工作文件夹路径
    max_steps: int = 10  # 最大执行步骤
    enable_shell: bool = True  # 是否允许执行 shell 命令


@dataclass
class TaskPlan:
    """任务计划。"""
    steps: List[dict] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""


class MasterAgent:
    """
    主 Agent - 智能任务编排和执行。

    能力：
    1. 对话理解：理解用户意图
    2. 任务编排：自动规划执行步骤
    3. Skill 调用：调用已注册的 Skills
    4. 命令行执行：执行 shell 命令
    5. 文件操作：读写工作文件夹中的文件
    6. 上下文记忆：记住多轮对话历史
    """

    def __init__(self, config: Optional[MasterAgentConfig] = None):
        self.config = config or MasterAgentConfig()
        self._context: List[dict] = []  # 对话历史
        self._current_plan: Optional[TaskPlan] = None
        self._working_files: List[str] = []  # 当前工作文件
        self._load_config()

    def _load_config(self):
        """从配置文件加载配置。"""
        config_path = Path(__file__).parent.parent / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 加载工作文件夹配置
                self.config.work_folder = data.get('work_folder', '')
                # 加载模型配置
                model_config = data.get('model', {})
                self._model_provider = model_config.get('provider', 'local')
                self._model_settings = model_config.get('providers', {}).get(self._model_provider, {})

    def chat(self, message: str) -> str:
        """
        与 MasterAgent 对话。

        Args:
            message: 用户输入

        Returns:
            Agent 回复
        """
        logger.info(f"用户消息：{message}")

        # 添加到上下文
        self._context.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # 触发钩子
        trigger_hook("on_master_chat", message=message)

        # 分析意图并执行
        response = self._process_message(message)

        # 添加回复到上下文
        self._context.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    def _process_message(self, message: str) -> str:
        """处理用户消息。"""
        message_lower = message.lower().strip()

        # 1. 检查是否是命令执行请求
        if message_lower.startswith(('执行命令', 'run command', 'shell:', '!')):
            return self._execute_shell_command(message)

        # 2. 检查是否是文件操作请求
        if any(kw in message_lower for kw in ['读取文件', '打开文件', '查看文件', 'read file', 'open file']):
            return self._handle_file_read(message)

        # 3. 检查是否是批量处理请求
        if any(kw in message_lower for kw in ['批量', 'batch', '处理所有', '全部处理']):
            return self._handle_batch_process(message)

        # 4. 检查是否是 Skill 调用请求
        if any(kw in message_lower for kw in ['调用', '使用', '执行 skill']):
            return self._handle_skill_call(message)

        # 5. 检查是否有文件在上下文中
        if self._working_files:
            return self._handle_file_task(message)

        # 6. 通用意图识别
        return self._general_intent(message)

    def _execute_shell_command(self, message: str) -> str:
        """执行 shell 命令。"""
        if not self.config.enable_shell:
            return "❌ Shell 命令执行已被禁用"

        # 提取命令
        cmd = message
        for prefix in ['执行命令', 'run command', 'shell:', '!']:
            if cmd.startswith(prefix):
                cmd = cmd[len(prefix):].strip()
                break

        logger.info(f"执行命令：{cmd}")

        try:
            # 在工作文件夹中执行
            cwd = self.config.work_folder if self.config.work_folder else os.getcwd()

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=cwd
            )

            output = result.stdout
            error = result.stderr

            response = f"✅ 命令执行完成\n\n"
            if output:
                response += f"输出：\n```\n{output}\n```\n"
            if error:
                response += f"错误：\n```\n{error}\n```\n"

            return response.strip()

        except subprocess.TimeoutExpired:
            return "❌ 命令执行超时（60 秒）"
        except Exception as e:
            return f"❌ 命令执行失败：{str(e)}"

    def _handle_file_read(self, message: str) -> str:
        """处理文件读取请求。"""
        # 尝试提取文件名
        file_match = re.search(r'["\']([^"\']+\.xlsx)["\']', message)
        if not file_match:
            file_match = re.search(r'(\w+\.xlsx)', message)

        if not file_match:
            # 使用当前工作文件
            if not self._working_files:
                return "请指定要读取的文件，或先上传一个文件"
            file_path = self._working_files[-1]
        else:
            file_path = file_match.group(1)

        # 检查文件是否存在
        full_path = Path(self.config.work_folder) / file_path if self.config.work_folder else Path(file_path)
        if not full_path.exists():
            return f"❌ 文件不存在：{file_path}"

        # 读取文件内容
        result = execute_skill("execute_excel_batch", file=str(full_path), max_questions=10)

        if result.get("success"):
            questions = result.get("questions", [])
            self._working_files.append(str(full_path))

            response = f"📄 文件内容预览：{file_path}\n\n"
            response += f"共 {len(questions)} 条数据，前 10 条：\n\n"
            for i, item in enumerate(questions[:10], 1):
                response += f"{i}. 行{item['row']}: {item['question'][:50]}...\n"

            response += f"\n💡 你可以说：\n"
            response += f"- '批量处理这个文件' - 逐个获取答案\n"
            response += f"- '处理前 5 个问题' - 只处理部分\n"

            return response
        else:
            return f"❌ 读取失败：{result.get('error', '未知错误')}"

    def _handle_batch_process(self, message: str) -> str:
        """处理批量任务请求。"""
        # 确定文件
        file_path = None

        # 从消息中提取
        file_match = re.search(r'["\']([^"\']+\.xlsx)["\']', message)
        if file_match:
            file_path = file_match.group(1)
        elif self._working_files:
            file_path = self._working_files[-1]
        else:
            return "请指定要处理的文件，或先上传文件"

        # 确定处理范围
        max_questions = 0
        if '所有' in message or '全部' in message:
            max_questions = 0  # 不限制
        else:
            num_match = re.search(r'(\d+)', message)
            if num_match:
                max_questions = int(num_match.group(1))

        # 确定使用什么 Skill 处理
        use_liantong = any(kw in message.lower() for kw in ['联通', '客服', 'ai', '问答'])

        full_path = Path(self.config.work_folder) / file_path if self.config.work_folder else Path(file_path)
        if not full_path.exists():
            return f"❌ 文件不存在：{file_path}"

        # 获取问题列表
        batch_result = execute_skill("execute_excel_batch", file=str(full_path), max_questions=max_questions)

        if not batch_result.get("success"):
            return f"❌ 获取问题失败：{batch_result.get('error', '未知错误')}"

        questions = batch_result.get("questions", [])
        if not questions:
            return "✅ 所有问题都已处理完成"

        # 逐个处理
        total = len(questions)
        success_count = 0
        results = []

        for i, item in enumerate(questions, 1):
            row = item["row"]
            question = item["question"]

            logger.info(f"处理问题 {i}/{total}: {question[:30]}...")

            if use_liantong:
                # 调用联通客服 Skill
                skill_result = execute_skill("liantong_ai_query", question=question)

                if skill_result.get("success"):
                    answer = skill_result.get("answer", "")
                    # 写入答案
                    write_result = execute_skill(
                        "write_excel_answer",
                        file=str(full_path),
                        row=row,
                        answer=answer
                    )
                    if write_result.get("success"):
                        success_count += 1
                        results.append({"row": row, "status": "成功", "question": question[:20]})
                    else:
                        results.append({"row": row, "status": "写入失败", "question": question[:20]})
                else:
                    results.append({"row": row, "status": "获取失败", "question": question[:20]})
            else:
                results.append({"row": row, "status": "待处理", "question": question[:20]})

        # 生成报告
        response = f"📊 批量处理完成\n\n"
        response += f"文件：{file_path}\n"
        response += f"处理数量：{len(questions)}\n"
        response += f"成功：{success_count}\n"
        response += f"失败：{len(questions) - success_count}\n\n"

        if results:
            response += "详细结果：\n"
            for r in results[:5]:
                response += f"- 行{r['row']}: {r['status']} - {r.get('question', '')}\n"
            if len(results) > 5:
                response += f"... 还有 {len(results) - 5} 条\n"

        response += f"\n📁 结果文件：{file_path}"

        return response

    def _handle_skill_call(self, message: str) -> str:
        """处理 Skill 调用请求。"""
        # 提取 Skill ID
        skill_match = re.search(r'["\'](\w+)["\']', message)
        if not skill_match:
            # 尝试从消息中推断
            if '联通' in message or '客服' in message:
                skill_id = "liantong_ai_query"
            elif 'excel' in message.lower() or '表格' in message:
                skill_id = "excel_tools"
            else:
                return "请指定要调用的 Skill 名称"
        else:
            skill_id = skill_match.group(1)

        # 获取 Skill 信息
        skill_info = get_skill_info(skill_id)
        if not skill_info:
            return f"❌ 未找到 Skill: {skill_id}"

        # 提取参数
        params = {}
        for param in skill_info.get('parameters', []):
            param_name = param.get('name') if isinstance(param, dict) else param
            # 尝试从消息中提取参数值
            value_match = re.search(rf'{param_name}["\']?[:：=]\s*["\']?([^"\'，,]+)', message)
            if value_match:
                params[param_name] = value_match.group(1).strip()

        # 执行 Skill
        result = execute_skill(skill_id, **params)

        if result.get("success"):
            response = f"✅ Skill 调用成功：{skill_id}\n\n"
            response += f"结果：\n{json.dumps(result, ensure_ascii=False, indent=2)}"
        else:
            response = f"❌ Skill 调用失败：{result.get('error', '未知错误')}"

        return response

    def _handle_file_task(self, message: str) -> str:
        """处理与当前文件相关的任务。"""
        if not self._working_files:
            return self._general_intent(message)

        # 默认处理当前文件
        file_path = self._working_files[-1]

        # 判断意图
        if '处理' in message or '执行' in message:
            return self._handle_batch_process(f"处理 {file_path}")
        elif '查看' in message or '读取' in message:
            return self._handle_file_read(f"读取 {file_path}")
        else:
            return self._general_intent(message)

    def _general_intent(self, message: str) -> str:
        """通用意图处理 - 使用 LLM 分析。"""
        # 获取可用 Skills
        skills = list_skills()
        skills_info = "\n".join([
            f"- {s.get('skill_id', s.get('id'))}: {s.get('name', s.get('description', ''))}"
            for s in skills
        ])

        # 构建提示
        prompt = f"""你是一个任务执行助手。用户希望你帮助完成任务。

可用的 Skills:
{skills_info}

工作文件夹：{self.config.work_folder or '未设置'}

用户消息：{message}

请分析用户意图，决定：
1. 需要调用哪个 Skill
2. 需要什么参数
3. 执行步骤

回复格式：
【分析】简要分析用户需求
【计划】列出执行步骤
【执行】执行并返回结果
"""

        # 尝试使用 LLM 分析（如果配置了）
        try:
            # 这里可以调用 LLM API
            # 暂时返回友好提示
            return f"""🤔 我理解你想：{message}

我可以帮助你：
1. **处理 Excel 文件** - 上传文件后说"批量处理"
2. **联通客服问答** - 直接提问或说"查询联通 XXX"
3. **执行命令** - 说"执行命令: xxx"或"!xxx"
4. **读取文件** - 说"读取文件 xxx.xlsx"

💡 当前工作文件夹：{self.config.work_folder or '未设置'}
💡 可用 Skills: {skills_info}

请告诉我你想做什么，我会帮你完成！"""

        except Exception as e:
            logger.error(f"LLM 分析失败：{e}")
            return f"处理请求时出错：{str(e)}"

    def set_work_folder(self, path: str) -> bool:
        """设置工作文件夹。"""
        folder = Path(path)
        if folder.exists() and folder.is_dir():
            self.config.work_folder = str(folder.absolute())
            return True
        return False

    def get_context(self) -> List[dict]:
        """获取对话历史。"""
        return self._context

    def clear_context(self):
        """清空对话历史。"""
        self._context = []
        self._working_files = []
        self._current_plan = None

    def get_status(self) -> dict:
        """获取 Agent 状态。"""
        return {
            "work_folder": self.config.work_folder,
            "context_length": len(self._context),
            "working_files": self._working_files,
            "enabled_skills": len(list_skills()),
            "shell_enabled": self.config.enable_shell,
        }
