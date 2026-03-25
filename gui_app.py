#!/usr/bin/env python3
"""
PhoneAgent GUI - MasterAgent 聊天界面
类似正常聊天应用的体验：
1. 简洁的聊天界面
2. 文件按钮在输入框旁边
3. 支持拖放文件到整个窗口
"""

import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import requests

# 配置
API_BASE_URL = "http://localhost:5001"
CONFIG_PATH = Path(__file__).parent / "config.json"

# 尝试从配置文件读取端口
try:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            port = config.get('server', {}).get('port', 5001)
            API_BASE_URL = f"http://localhost:{port}"
except Exception:
    pass


class ChatMessage(tk.Frame):
    """聊天消息气泡组件。"""

    def __init__(self, parent, content: str, is_user: bool = False, timestamp: str = None):
        super().__init__(parent, bg='#f5f7fa')
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.setup_ui(content)

    def setup_ui(self, content: str):
        """设置 UI。"""
        # 外层容器
        container = tk.Frame(self, bg='#f5f7fa')
        container.pack(fill=tk.X, pady=3, padx=10)

        # 对齐方向
        anchor = tk.E if self.is_user else tk.W

        # 时间戳
        time_label = tk.Label(
            container,
            text=self.timestamp,
            font=('Microsoft YaHei', 8),
            bg='#f5f7fa',
            fg='#999'
        )
        time_label.pack(anchor=anchor)

        # 消息气泡
        bg_color = '#007bff' if self.is_user else '#ffffff'
        fg_color = 'white' if self.is_user else '#333'

        bubble_frame = tk.Frame(container, bg=bg_color, relief=tk.RAISED, bd=1)
        bubble_frame.pack(anchor=anchor, fill=tk.X, padx=5, pady=2)

        # 消息内容
        text = scrolledtext.ScrolledText(
            bubble_frame,
            wrap=tk.WORD,
            font=('Microsoft YaHei', 10),
            bg=bg_color,
            fg=fg_color,
            relief=tk.FLAT,
            padx=12,
            pady=8,
            height=1
        )
        text.insert('1.0', content)
        text.config(state=tk.DISABLED)
        text.pack(fill=tk.X)

        # 动态调整高度（最多 20 行）
        line_count = content.count('\n') + 1
        height = min(line_count + 2, 20)
        text.config(height=height)


class SettingsPanel(tk.Toplevel):
    """设置面板。"""

    def __init__(self, parent, api_base_url):
        super().__init__(parent)
        self.parent = parent
        self.api_base_url = api_base_url
        self.title("⚙️ 设置")
        self.geometry("800x650")
        self.minsize(600, 500)
        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        # 延迟加载配置，确保 UI 已渲染
        self.after(100, self.load_config)

    def setup_ui(self):
        """设置 UI。"""
        # 标签页
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 工作文件夹设置
        work_frame = tk.Frame(notebook, bg='#f5f7fa')
        notebook.add(work_frame, text="📁 工作文件夹")
        self.setup_work_folder(work_frame)

        # 模型设置（MasterAgent）
        model_frame = tk.Frame(notebook, bg='#f5f7fa')
        notebook.add(model_frame, text="🤖 MasterAgent 模型")
        self.setup_model(model_frame)

        # Skills 配置
        skills_frame = tk.Frame(notebook, bg='#f5f7fa')
        notebook.add(skills_frame, text="🔧 Skills 配置")
        self.setup_skills(skills_frame)

        # 保存按钮
        btn_frame = tk.Frame(self, bg='#f5f7fa')
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        save_btn = tk.Button(
            btn_frame, text="💾 保存设置",
            command=self.save_config,
            bg='#4caf50', fg='white',
            font=('Microsoft YaHei', 11, 'bold'),
            padx=20, pady=10
        )
        save_btn.pack(side=tk.RIGHT)

    def create_scrollable_frame(self, parent):
        """创建可滚动的 Frame。"""
        # 使用 parent 作为 container，不需要额外创建
        parent.configure(bg='#f5f7fa')

        # 创建 Canvas 和滚动条
        canvas = tk.Canvas(parent, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg='#f5f7fa')

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="scrollable_frame")

        def configure_canvas(event):
            """Canvas 大小变化时更新内部 Frame 宽度。"""
            canvas.itemconfig(canvas_window, width=event.width)

        def on_frame_configure(event):
            """内部 Frame 大小变化时更新滚动区域。"""
            canvas.configure(scrollregion=canvas.bbox("all"))

        def mouse_wheel(event):
            """鼠标滚轮事件。"""
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # 绑定事件
        canvas.bind("<Configure>", configure_canvas)
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<MouseWheel>", mouse_wheel)

        # 配置滚动条
        canvas.configure(yscrollcommand=scrollbar.set)

        # 布局
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return parent, scrollable_frame, canvas

    def setup_work_folder(self, parent):
        """工作文件夹设置。"""
        # 创建可滚动区域
        container, scrollable_frame, canvas = self.create_scrollable_frame(parent)

        tk.Label(
            scrollable_frame, text="工作文件夹路径",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        tk.Label(
            scrollable_frame, text="在此文件夹中查找和保存文件",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20, pady=(0, 10))

        self.work_folder_entry = tk.Entry(scrollable_frame, font=('Microsoft YaHei', 10), width=50)
        self.work_folder_entry.pack(fill=tk.X, padx=20, pady=5)

        browse_btn = tk.Button(
            scrollable_frame, text="📂 浏览...",
            command=self.browse_folder,
            bg='#667eea', fg='white',
            font=('Microsoft YaHei', 10),
            padx=15, pady=5
        )
        browse_btn.pack(anchor=tk.W, padx=20, pady=10)

        # 占位符，确保滚动区域有足够空间
        tk.Label(scrollable_frame, text="", bg='#f5f7fa').pack(fill=tk.BOTH, expand=True)

    def setup_model(self, parent):
        """模型设置（MasterAgent 用）。"""
        # 创建可滚动区域
        container, scrollable_frame, canvas = self.create_scrollable_frame(parent)

        # 预设协议选择
        tk.Label(
            scrollable_frame, text="模型协议",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        tk.Label(
            scrollable_frame, text="选择要使用的模型服务协议（MasterAgent 聊天用）",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20, pady=(0, 10))

        self.protocol_var = tk.StringVar(value="local")
        protocol_frame = tk.Frame(scrollable_frame, bg='#f5f7fa')
        protocol_frame.pack(fill=tk.X, padx=20, pady=5)

        protocols = [
            ("local", "Ollama / 本地服务"),
            ("openai", "OpenAI 兼容 (OpenAI、Zhipu、Moonshot 等)"),
            ("anthropic", "Anthropic Claude"),
            ("custom", "自定义协议")
        ]

        for value, label in protocols:
            tk.Radiobutton(
                protocol_frame, text=label, variable=self.protocol_var,
                value=value, bg='#f5f7fa', font=('Microsoft YaHei', 9),
                command=self.on_protocol_change
            ).pack(anchor=tk.W)

        # API Base URL
        tk.Label(
            scrollable_frame, text="API Base URL",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        self.base_url_entry = tk.Entry(scrollable_frame, font=('Microsoft YaHei', 10), width=50)
        self.base_url_entry.pack(padx=20, pady=5)
        tk.Label(
            scrollable_frame, text="例如：http://localhost:11434/v1 或 https://api.openai.com/v1",
            font=('Microsoft YaHei', 8),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        # Model Name
        tk.Label(
            scrollable_frame, text="Model Name",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        self.model_entry = tk.Entry(scrollable_frame, font=('Microsoft YaHei', 10), width=50)
        self.model_entry.pack(padx=20, pady=5)
        tk.Label(
            scrollable_frame, text="例如：qwen3.5:9b 或 gpt-4o",
            font=('Microsoft YaHei', 8),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        # API Key
        tk.Label(
            scrollable_frame, text="API Key",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        self.api_key_entry = tk.Entry(scrollable_frame, font=('Microsoft YaHei', 10), width=50, show='*')
        self.api_key_entry.pack(padx=20, pady=5)

        # 说明标签
        self.protocol_hint = tk.Label(
            scrollable_frame, text="",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#ff9800'
        )
        self.protocol_hint.pack(anchor=tk.W, padx=20, pady=10)

        # 占位符
        tk.Label(scrollable_frame, text="", bg='#f5f7fa').pack(fill=tk.BOTH, expand=True)

    def setup_skills(self, parent):
        """Skills 配置（PhoneAgent 用）。"""
        # 创建可滚动区域
        container, scrollable_frame, canvas = self.create_scrollable_frame(parent)

        # ===== 已注册 Skills 列表 =====
        skills_list_frame = tk.LabelFrame(
            scrollable_frame, text="🔌 已注册的 Skills",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        skills_list_frame.pack(fill=tk.X, padx=20, pady=10)

        self.skills_list_text = scrolledtext.ScrolledText(
            skills_list_frame,
            height=6,
            font=('Consolas', 9),
            wrap=tk.WORD,
            bg='#f9f9f9'
        )
        self.skills_list_text.pack(fill=tk.X)
        self.skills_list_text.config(state=tk.DISABLED)

        # ===== 模型配置 =====
        model_frame = tk.LabelFrame(
            scrollable_frame, text="🤖 模型配置",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        model_frame.pack(fill=tk.X, padx=20, pady=10)

        # 协议选择
        tk.Label(
            model_frame, text="模型协议",
            font=('Microsoft YaHei', 9, 'bold'),
            bg='white'
        ).pack(anchor=tk.W, pady=(0, 5))

        self.skills_protocol_var = tk.StringVar(value="local")
        protocol_frame = tk.Frame(model_frame, bg='white')
        protocol_frame.pack(fill=tk.X, pady=5)

        protocols = [
            ("local", "Ollama / 本地服务"),
            ("openai", "OpenAI 兼容"),
            ("anthropic", "Anthropic Claude"),
            ("custom", "自定义")
        ]
        for value, label in protocols:
            tk.Radiobutton(
                protocol_frame, text=label, variable=self.skills_protocol_var,
                value=value, bg='white', font=('Microsoft YaHei', 9),
                command=self.on_skills_protocol_change
            ).pack(anchor=tk.W)

        # Base URL
        tk.Label(
            model_frame, text="Base URL",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.skills_base_url = tk.Entry(model_frame, font=('Microsoft YaHei', 9), width=60)
        self.skills_base_url.pack(fill=tk.X, pady=2)

        # Model Name
        tk.Label(
            model_frame, text="Model Name",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.skills_model_name = tk.Entry(model_frame, font=('Microsoft YaHei', 9), width=60)
        self.skills_model_name.pack(fill=tk.X, pady=2)

        # API Key
        tk.Label(
            model_frame, text="API Key",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.skills_api_key = tk.Entry(model_frame, font=('Microsoft YaHei', 9), width=60, show='*')
        self.skills_api_key.pack(fill=tk.X, pady=2)

        # ===== 设备配置 =====
        device_frame = tk.LabelFrame(
            scrollable_frame, text="📱 设备配置 (ADB)",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        device_frame.pack(fill=tk.X, padx=20, pady=10)

        # 设备类型
        tk.Label(
            device_frame, text="设备类型",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(0, 5))
        self.device_type_var = tk.StringVar(value="adb")
        device_type_frame = tk.Frame(device_frame, bg='white')
        device_type_frame.pack(fill=tk.X, pady=5)
        tk.Radiobutton(
            device_type_frame, text="本地 ADB", variable=self.device_type_var,
            value="adb", bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W)
        tk.Radiobutton(
            device_type_frame, text="远程连接", variable=self.device_type_var,
            value="remote", bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W)

        # 远程地址
        tk.Label(
            device_frame, text="远程 ADB 地址 (如 192.168.1.100:5555)",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.remote_address = tk.Entry(device_frame, font=('Microsoft YaHei', 9), width=60)
        self.remote_address.pack(fill=tk.X, pady=2)
        tk.Label(
            device_frame, text="留空则使用本地 ADB",
            font=('Microsoft YaHei', 8),
            bg='white', fg='#999'
        ).pack(anchor=tk.W)

        # 自动连接
        self.auto_connect_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            device_frame, text="自动连接设备",
            variable=self.auto_connect_var,
            bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W, pady=5)

        # ===== 坐标优化配置 =====
        coord_frame = tk.LabelFrame(
            scrollable_frame, text="🎯 坐标优化",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        coord_frame.pack(fill=tk.X, padx=20, pady=10)

        # 启用坐标优化
        self.coord_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            coord_frame, text="启用坐标优化",
            variable=self.coord_enabled_var,
            bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W, pady=5)

        # 点击偏移 X
        tk.Label(
            coord_frame, text="点击偏移 X",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.click_offset_x = tk.Entry(coord_frame, font=('Microsoft YaHei', 9), width=20)
        self.click_offset_x.pack(anchor=tk.W, pady=2)

        # 点击偏移 Y
        tk.Label(
            coord_frame, text="点击偏移 Y",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.click_offset_y = tk.Entry(coord_frame, font=('Microsoft YaHei', 9), width=20)
        self.click_offset_y.pack(anchor=tk.W, pady=2)

        # 区域点击
        self.use_region_click_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            coord_frame, text="使用区域点击（而非单点）",
            variable=self.use_region_click_var,
            bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W, pady=5)

        # 最小点击区域
        tk.Label(
            coord_frame, text="最小点击区域大小",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.min_click_region = tk.Entry(coord_frame, font=('Microsoft YaHei', 9), width=20)
        self.min_click_region.pack(anchor=tk.W, pady=2)

        # ===== Agent 配置 =====
        agent_frame = tk.LabelFrame(
            scrollable_frame, text="🤖 Agent 行为",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        agent_frame.pack(fill=tk.X, padx=20, pady=10)

        # 最大步骤数
        tk.Label(
            agent_frame, text="最大执行步骤",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(0, 2))
        self.max_steps = tk.Entry(agent_frame, font=('Microsoft YaHei', 9), width=20)
        self.max_steps.pack(anchor=tk.W, pady=2)

        # 最大重复次数
        tk.Label(
            agent_frame, text="最大重复动作次数",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.max_repeated_actions = tk.Entry(agent_frame, font=('Microsoft YaHei', 9), width=20)
        self.max_repeated_actions.pack(anchor=tk.W, pady=2)

        # 重复检测
        self.enable_repeat_detection_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            agent_frame, text="启用重复动作检测",
            variable=self.enable_repeat_detection_var,
            bg='white', font=('Microsoft YaHei', 9)
        ).pack(anchor=tk.W, pady=5)

        # 上下文轮数
        tk.Label(
            agent_frame, text="最大上下文轮数",
            font=('Microsoft YaHei', 9),
            bg='white'
        ).pack(anchor=tk.W, pady=(10, 2))
        self.max_context_rounds = tk.Entry(agent_frame, font=('Microsoft YaHei', 9), width=20)
        self.max_context_rounds.pack(anchor=tk.W, pady=2)

        # 说明文字
        help_frame = tk.LabelFrame(
            scrollable_frame, text="💡 说明",
            font=('Microsoft YaHei', 10, 'bold'),
            bg='white', fg='#666',
            padx=15, pady=15
        )
        help_frame.pack(fill=tk.X, padx=20, pady=10)

        help_text = """• 模型配置：Skills 执行时使用的 AI 模型
• 设备配置：ADB 连接参数，远程地址留空则使用本地 ADB
• 坐标优化：点击时的偏移和区域设置，提高点击准确度
• Agent 行为：控制任务执行的最大步骤、重复检测等
• 修改后需要重启服务器生效"""

        tk.Label(
            help_frame, text=help_text,
            font=('Microsoft YaHei', 9),
            bg='white', fg='#333',
            justify=tk.LEFT
        ).pack(anchor=tk.W)

        # 占位符
        tk.Label(scrollable_frame, text="", bg='#f5f7fa').pack(fill=tk.BOTH, expand=True)

    def on_protocol_change(self):
        """协议切换时更新提示和默认值（MasterAgent）。"""
        protocol = self.protocol_var.get()

        hints = {
            "local": "💡 Ollama 默认地址：http://localhost:11434/v1",
            "openai": "💡 OpenAI 兼容协议，可使用 OpenAI、智谱、月之暗面等服务",
            "anthropic": "💡 Anthropic Claude API 地址：https://api.anthropic.com",
            "custom": "💡 自定义协议，请填写完整的 API 地址"
        }

        defaults = {
            "local": ("http://localhost:11434/v1", "qwen3.5:9b", "ollama"),
            "openai": ("https://api-inference.modelscope.cn/v1", "ZhipuAI/AutoGLM-Phone-9B", ""),
            "anthropic": ("https://api.anthropic.com", "claude-sonnet-4-6-20250514", ""),
            "custom": ("", "", "")
        }

        self.protocol_hint.config(text=hints.get(protocol, ""))

        # 如果当前输入为空或是默认值，切换到新协议时更新默认值
        current_url = self.base_url_entry.get()
        if not current_url or current_url in [d[0] for d in defaults.values()]:
            url, model, key = defaults.get(protocol, ("", "", ""))
            self.base_url_entry.delete(0, tk.END)
            self.base_url_entry.insert(0, url)
            self.model_entry.delete(0, tk.END)
            self.model_entry.insert(0, model)
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, key)

    def on_skills_protocol_change(self):
        """协议切换时更新默认值（Skills/PhoneAgent）。"""
        protocol = self.skills_protocol_var.get()

        defaults = {
            "local": ("http://localhost:11434/v1", "qwen3.5:4b", "ollama"),
            "openai": ("https://api-inference.modelscope.cn/v1", "ZhipuAI/AutoGLM-Phone-9B", ""),
            "anthropic": ("https://api.anthropic.com", "claude-sonnet-4-6-20250514", ""),
            "custom": ("", "", "")
        }

        url, model, key = defaults.get(protocol, ("", "", ""))

        # 只在当前为空时填充默认值
        if not self.skills_base_url.get():
            self.skills_base_url.delete(0, tk.END)
            self.skills_base_url.insert(0, url)
        if not self.skills_model_name.get():
            self.skills_model_name.delete(0, tk.END)
            self.skills_model_name.insert(0, model)
        if not self.skills_api_key.get():
            self.skills_api_key.delete(0, tk.END)
            self.skills_api_key.insert(0, key)

    def browse_folder(self):
        """浏览选择文件夹。"""
        folder = filedialog.askdirectory(title="选择工作文件夹")
        if folder:
            self.work_folder_entry.delete(0, tk.END)
            self.work_folder_entry.insert(0, folder)

    def open_phone_agent_config(self):
        """打开 PhoneAgent 配置文件。"""
        config_path = Path(__file__).parent.parent / "phone_agent" / "config" / "phone_agent_config.json"
        if config_path.exists():
            import os
            if os.name == 'nt':
                os.startfile(config_path)
            elif sys.platform == 'darwin':
                os.system(f'open "{config_path}"')
            else:
                os.system(f'xdg-open "{config_path}"')
        else:
            messagebox.showwarning("提示", "配置文件不存在，将使用默认配置")

    def load_config(self):
        """加载配置。"""
        # 加载 MasterAgent 配置
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 工作文件夹
            self.work_folder_entry.insert(0, config.get('work_folder', ''))

            # 模型配置
            model_config = config.get('model', {})
            provider = model_config.get('provider', 'local')
            self.protocol_var.set(provider)

            providers = model_config.get('providers', {})
            if provider in providers:
                provider_config = providers[provider]
                self.base_url_entry.insert(0, provider_config.get('base_url', ''))
                self.model_entry.insert(0, provider_config.get('model', ''))
                self.api_key_entry.insert(0, provider_config.get('api_key', ''))

            self.on_protocol_change()

        # 加载 Skills/PhoneAgent 配置
        self.load_skills_config()

        # 加载 Skills 列表
        self.after(200, self.load_skills_list)

    def load_skills_config(self):
        """加载 Skills/PhoneAgent 配置。"""
        config_path = Path(__file__).parent.parent / "phone_agent" / "config" / "phone_agent_config.json"
        if not config_path.exists():
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 模型配置
            model_config = config.get('model', {})
            provider = model_config.get('provider', 'local')
            self.skills_protocol_var.set(provider)

            providers = model_config.get('providers', {})
            if provider in providers:
                provider_config = providers[provider]
                self.skills_base_url.insert(0, provider_config.get('base_url', ''))
                self.skills_model_name.insert(0, provider_config.get('model', ''))
                self.skills_api_key.insert(0, provider_config.get('api_key', ''))

            # 设备配置
            device_config = config.get('device', {})
            self.device_type_var.set(device_config.get('type', 'adb'))
            remote_addr = device_config.get('remote_address')
            if remote_addr:
                self.remote_address.insert(0, remote_addr)
            self.auto_connect_var.set(device_config.get('auto_connect', True))

            # 坐标优化
            coord_config = config.get('coordinate_optimization', {})
            self.coord_enabled_var.set(coord_config.get('enabled', True))
            self.click_offset_x.insert(0, str(coord_config.get('click_offset_x', 8)))
            self.click_offset_y.insert(0, str(coord_config.get('click_offset_y', 8)))
            self.use_region_click_var.set(coord_config.get('use_region_click', True))
            self.min_click_region.insert(0, str(coord_config.get('min_click_region', 30)))

            # Agent 配置
            agent_config = config.get('agent', {})
            self.max_steps.insert(0, str(agent_config.get('max_steps', 20)))
            self.max_repeated_actions.insert(0, str(agent_config.get('max_repeated_actions', 5)))
            self.enable_repeat_detection_var.set(agent_config.get('enable_repeat_detection', True))
            self.max_context_rounds.insert(0, str(agent_config.get('max_context_rounds', 3)))

        except Exception as e:
            print(f"加载 Skills 配置失败：{e}")

    def load_skills_list(self):
        """加载已注册 Skills 列表。"""
        try:
            response = requests.get(f"{API_BASE_URL}/skills", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    skills = data.get('skills', [])
                    output = []
                    output.append(f"已注册 {len(skills)} 个 Skills:\n")
                    output.append("=" * 60 + "\n\n")

                    for skill in skills:
                        skill_id = skill.get('skill_id', skill.get('id', 'unknown'))
                        name = skill.get('name', 'Unknown')
                        desc = skill.get('description', 'No description')
                        enabled = skill.get('enabled', True)
                        status = "✅" if enabled else "⏸️"

                        output.append(f"{status} {skill_id}\n")
                        output.append(f"   名称：{name}\n")
                        output.append(f"   描述：{desc}\n")

                        # 显示参数
                        params = skill.get('parameters', [])
                        if params:
                            output.append("   参数:\n")
                            for param in params:
                                if isinstance(param, dict):
                                    pname = param.get('name', '')
                                    ptype = param.get('type', '')
                                    preq = '必填' if param.get('required') else '可选'
                                    output.append(f"      - {pname} ({ptype}, {preq})\n")
                                else:
                                    output.append(f"      - {param}\n")

                        output.append("\n" + "-" * 60 + "\n\n")

                    self.skills_list_text.config(state=tk.NORMAL)
                    self.skills_list_text.delete('1.0', tk.END)
                    self.skills_list_text.insert('1.0', ''.join(output))
                    self.skills_list_text.config(state=tk.DISABLED)
                else:
                    self.skills_list_text.config(state=tk.NORMAL)
                    self.skills_list_text.delete('1.0', tk.END)
                    self.skills_list_text.insert('1.0', f"❌ 获取 Skills 失败：{data.get('error', 'Unknown error')}")
                    self.skills_list_text.config(state=tk.DISABLED)
            else:
                self.skills_list_text.config(state=tk.NORMAL)
                self.skills_list_text.delete('1.0', tk.END)
                self.skills_list_text.insert('1.0', f"❌ HTTP 错误：{response.status_code}")
                self.skills_list_text.config(state=tk.DISABLED)
        except Exception as e:
            self.skills_list_text.config(state=tk.NORMAL)
            self.skills_list_text.delete('1.0', tk.END)
            self.skills_list_text.insert('1.0', f"❌ 加载失败：{e}\n\n请确保服务器正在运行")
            self.skills_list_text.config(state=tk.DISABLED)

    def save_config(self):
        """保存配置。"""
        # 保存 MasterAgent 配置
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {'model': {'providers': {}}}

        # 更新工作文件夹
        config['work_folder'] = self.work_folder_entry.get()

        # 更新模型配置
        if 'model' not in config:
            config['model'] = {'providers': {}}

        provider = self.protocol_var.get()
        config['model']['provider'] = provider

        config['model']['providers'][provider] = {
            'base_url': self.base_url_entry.get(),
            'model': self.model_entry.get(),
            'api_key': self.api_key_entry.get()
        }

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 保存 Skills/PhoneAgent 配置
        self.save_skills_config()

        messagebox.showinfo("✅ 保存成功", "配置已保存\n\n• MasterAgent 配置：config.json\n• Skills 配置：phone_agent/config/phone_agent_config.json\n\n修改后需要重启服务器生效")
        self.parent.load_config()
        self.destroy()

    def save_skills_config(self):
        """保存 Skills/PhoneAgent 配置。"""
        config_path = Path(__file__).parent.parent / "phone_agent" / "config" / "phone_agent_config.json"

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载现有配置
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        # 模型配置
        provider = self.skills_protocol_var.get()
        config['model'] = {
            'provider': provider,
            'providers': {
                provider: {
                    'base_url': self.skills_base_url.get(),
                    'model': self.skills_model_name.get(),
                    'api_key': self.skills_api_key.get(),
                    'max_tokens': 4096 if provider == 'local' else 2048
                }
            }
        }

        # 设备配置
        config['device'] = {
            'type': self.device_type_var.get(),
            'remote_address': self.remote_address.get() or None,
            'auto_connect': self.auto_connect_var.get()
        }

        # 坐标优化
        config['coordinate_optimization'] = {
            'enabled': self.coord_enabled_var.get(),
            'click_offset_x': int(self.click_offset_x.get() or 8),
            'click_offset_y': int(self.click_offset_y.get() or 8),
            'use_region_click': self.use_region_click_var.get(),
            'min_click_region': int(self.min_click_region.get() or 30)
        }

        # Agent 配置
        config['agent'] = {
            'max_steps': int(self.max_steps.get() or 20),
            'lang': 'cn',
            'verbose': True,
            'max_context_rounds': int(self.max_context_rounds.get() or 3),
            'remember_app_info': True,
            'max_repeated_actions': int(self.max_repeated_actions.get() or 5),
            'enable_repeat_detection': self.enable_repeat_detection_var.get()
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


class MainApp:
    """PhoneAgent 主应用 - 简洁聊天界面。"""

    def __init__(self, root):
        self.root = root
        self.root.title("PhoneAgent - MasterAgent")
        self.root.geometry("900x700")
        self.root.minsize(700, 500)

        self.chat_messages: List[ChatMessage] = []
        self.current_file: Optional[str] = None
        self.is_sending = False

        self.setup_ui()
        self.load_config()
        self.check_server_status()
        self.setup_drag_drop()

        # 欢迎消息
        self.add_welcome_message()

    def setup_ui(self):
        """设置 UI。"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='#f5f7fa')
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 顶部工具栏 =====
        toolbar = tk.Frame(main_frame, bg='#ffffff', height=50)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        # 标题
        title_label = tk.Label(
            toolbar, text="🤖 MasterAgent",
            font=('Microsoft YaHei', 14, 'bold'),
            bg='#ffffff', fg='#333'
        )
        title_label.pack(side=tk.LEFT, padx=15)

        # 状态
        self.status_label = tk.Label(
            toolbar, text="🔌 检测中...",
            font=('Microsoft YaHei', 9),
            bg='#ffffff', fg='#999'
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 右侧按钮
        right_frame = tk.Frame(toolbar, bg='#ffffff')
        right_frame.pack(side=tk.RIGHT, padx=10)

        self.settings_btn = tk.Button(
            right_frame, text="⚙️ 设置",
            command=self.open_settings,
            bg='#f0f0f0', fg='#333',
            font=('Microsoft YaHei', 9),
            padx=10, pady=5
        )
        self.settings_btn.pack(side=tk.RIGHT, padx=5)

        self.clear_btn = tk.Button(
            right_frame, text="🗑️ 清空",
            command=self.clear_chat,
            bg='#f0f0f0', fg='#333',
            font=('Microsoft YaHei', 9),
            padx=10, pady=5
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=5)

        # ===== 聊天区域 =====
        chat_container = tk.Frame(main_frame, bg='#f5f7fa')
        chat_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_canvas = tk.Canvas(chat_container, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(chat_container, orient="vertical", command=self.chat_canvas.yview)

        self.chat_inner = tk.Frame(self.chat_canvas, bg='#f5f7fa')

        self.chat_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat_canvas_window = self.chat_canvas.create_window((0, 0), window=self.chat_inner, anchor="nw")
        self.chat_inner.bind("<Configure>", self._on_chat_configure)
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        # ===== 输入区域 =====
        input_frame = tk.Frame(main_frame, bg='#ffffff', relief=tk.RAISED, bd=1)
        input_frame.pack(fill=tk.X, padx=0, pady=0)

        # 文件信息和附件按钮
        file_info_frame = tk.Frame(input_frame, bg='#ffffff')
        file_info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.file_label = tk.Label(
            file_info_frame, text="",
            font=('Microsoft YaHei', 9),
            bg='#ffffff', fg='#4caf50'
        )
        self.file_label.pack(side=tk.LEFT)

        self.attach_btn = tk.Button(
            file_info_frame, text="📎 附件",
            command=self.attach_file,
            bg='#f0f0f0', fg='#333',
            font=('Microsoft YaHei', 9),
            padx=8, pady=3,
            cursor='hand2'
        )
        self.attach_btn.pack(side=tk.RIGHT)

        # 输入框和发送按钮
        entry_container = tk.Frame(input_frame, bg='#ffffff')
        entry_container.pack(fill=tk.X, padx=10, pady=5)

        self.input_text = scrolledtext.ScrolledText(
            entry_container,
            height=2,
            font=('Microsoft YaHei', 11),
            wrap=tk.WORD,
            bg='#f5f5f5',
            relief=tk.FLAT
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_text.bind('<Return>', self.on_enter_key)

        self.send_btn = tk.Button(
            entry_container, text="发送",
            command=self.send_message,
            bg='#007bff', fg='white',
            font=('Microsoft YaHei', 10, 'bold'),
            padx=15, pady=8,
            cursor='hand2'
        )
        self.send_btn.pack(side=tk.RIGHT)

    def setup_drag_drop(self):
        """设置全局拖放。"""
        self.root.dragdropfiles = True
        self.root.bind('<Enter>', self.on_drag_enter)
        self.root.bind('<Leave>', self.on_drag_leave)
        self.root.bind('<ButtonRelease-1>', self.on_drag_release)

    def on_drag_enter(self, event):
        """拖放进入。"""
        pass

    def on_drag_leave(self, event):
        """拖放离开。"""
        pass

    def on_drag_release(self, event):
        """拖放释放。"""
        try:
            files = self.root.tk.splitlist(self.root.tk.call('tk', 'dnd', 'getfiles'))
            if files:
                self.attach_file(files[0])
        except Exception:
            pass

    def _on_chat_configure(self, event):
        """更新聊天滚动区域。"""
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        self.chat_canvas.itemconfig(self.chat_canvas_window, width=event.width)

    def _on_canvas_configure(self, event):
        """调整聊天内部宽度。"""
        self.chat_canvas.itemconfig(self.chat_canvas_window, width=event.width)

    def add_message(self, content: str, is_user: bool = False):
        """添加消息到聊天。"""
        msg = ChatMessage(self.chat_inner, content, is_user=is_user)
        msg.pack(fill=tk.X, padx=10, pady=2, anchor=tk.E if is_user else tk.W)
        self.chat_messages.append(msg)

        # 滚动到底部
        self.chat_canvas.yview_moveto(1.0)
        self.chat_canvas.update_idletasks()

    def add_welcome_message(self):
        """添加欢迎消息。"""
        welcome = """👋 你好！我是 MasterAgent

我可以帮你：
• 处理 Excel 文件（点击📎上传或直接拖入）
• 联通客服问答
• 执行命令（!命令）

点击 ⚙️ 设置 配置工作文件夹"""
        self.add_message(welcome)

    def attach_file(self, file_path=None):
        """附件文件。"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="选择文件",
                filetypes=[
                    ("Excel 文件", "*.xlsx *.xls"),
                    ("文本文件", "*.txt"),
                    ("所有文件", "*.*")
                ]
            )

        if file_path:
            self.current_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"📎 {filename}")

    def on_enter_key(self, event):
        """回车键发送。"""
        if not event.shift_down:
            self.send_message()
            return "break"
        return None

    def send_message(self):
        """发送消息。"""
        if self.is_sending:
            return

        message = self.input_text.get('1.0', tk.END).strip()
        if not message:
            return

        # 添加到聊天
        self.add_message(message, is_user=True)
        self.input_text.delete('1.0', tk.END)

        # 显示思考中
        self.add_message("思考中...")

        # 执行任务
        self.is_sending = True

        def run_task():
            try:
                # 准备请求
                task_data = {'message': message}
                if self.current_file:
                    task_data['file'] = self.current_file

                # 调用 API
                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    json=task_data,
                    timeout=300
                )

                # 检查响应
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")

                result = response.json()

                # 更新 UI
                self.root.after(0, lambda: self.handle_response(result))

            except Exception as e:
                self.root.after(0, lambda: self.handle_error(str(e)))

        threading.Thread(target=run_task, daemon=True).start()

    def handle_response(self, result):
        """处理响应。"""
        # 移除思考中消息
        if self.chat_inner.winfo_children():
            last = self.chat_inner.winfo_children()[-1]
            last.destroy()

        if result.get('success'):
            reply = result.get('reply', '')
            self.add_message(reply)

            # 清除已上传的文件标记
            self.current_file = None
            self.file_label.config(text="")
        else:
            self.add_message(f"❌ {result.get('error', '未知错误')}")

        self.is_sending = False

    def handle_error(self, error_msg):
        """处理错误。"""
        # 移除思考中消息
        if self.chat_inner.winfo_children():
            last = self.chat_inner.winfo_children()[-1]
            last.destroy()

        self.add_message(f"❌ 请求失败：{error_msg}")
        self.is_sending = False

    def open_settings(self):
        """打开设置。"""
        SettingsPanel(self.root, API_BASE_URL)

    def load_config(self):
        """加载配置。"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                work_folder = config.get('work_folder', '')
                if work_folder:
                    self.add_message(f"📁 工作文件夹：{work_folder}")

                # 显示当前模型配置
                model_config = config.get('model', {})
                provider = model_config.get('provider', 'local')
                providers = model_config.get('providers', {})
                if provider in providers:
                    provider_config = providers[provider]
                    model_name = provider_config.get('model', 'unknown')
                    self.add_message(f"🤖 模型：{model_name}")

    def clear_chat(self):
        """清空聊天。"""
        if messagebox.askyesno("确认", "确定清空对话？"):
            for msg in self.chat_messages:
                msg.destroy()
            self.chat_messages = []
            self.add_welcome_message()
            self.current_file = None
            self.file_label.config(text="")

    def check_server_status(self):
        """检查服务器状态。"""
        def check():
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    self.status_label.config(text="✅ 已连接", fg='#4caf50')
                else:
                    self.status_label.config(text="❌ 连接失败", fg='#f44336')
            except Exception:
                self.status_label.config(text="❌ 未连接", fg='#f44336')

        threading.Thread(target=check, daemon=True).start()


def main():
    """主函数。"""
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
