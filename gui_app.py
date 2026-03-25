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
        self.geometry("600x500")
        self.transient(parent)
        self.grab_set()

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """设置 UI。"""
        # 标签页
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 工作文件夹设置
        work_frame = tk.Frame(notebook, bg='#f5f7fa')
        notebook.add(work_frame, text="📁 工作文件夹")
        self.setup_work_folder(work_frame)

        # 模型设置
        model_frame = tk.Frame(notebook, bg='#f5f7fa')
        notebook.add(model_frame, text="🤖 模型配置")
        self.setup_model(model_frame)

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

    def setup_work_folder(self, parent):
        """工作文件夹设置。"""
        tk.Label(
            parent, text="工作文件夹路径",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=15)

        tk.Label(
            parent, text="在此文件夹中查找和保存文件",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        self.work_folder_entry = tk.Entry(parent, font=('Microsoft YaHei', 10), width=50)
        self.work_folder_entry.pack(fill=tk.X, padx=20, pady=10)

        browse_btn = tk.Button(
            parent, text="📂 浏览...",
            command=self.browse_folder,
            bg='#667eea', fg='white',
            font=('Microsoft YaHei', 10),
            padx=15, pady=5
        )
        browse_btn.pack(anchor=tk.W, padx=20)

    def setup_model(self, parent):
        """模型设置。"""
        # 预设协议选择
        tk.Label(
            parent, text="模型协议",
            font=('Microsoft YaHei', 11, 'bold'),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=15)

        tk.Label(
            parent, text="选择要使用的模型服务协议",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        self.protocol_var = tk.StringVar(value="local")
        protocol_frame = tk.Frame(parent, bg='#f5f7fa')
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
            parent, text="API Base URL",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(20, 5))

        self.base_url_entry = tk.Entry(parent, font=('Microsoft YaHei', 10), width=50)
        self.base_url_entry.pack(padx=20, pady=5)
        tk.Label(
            parent, text="例如：http://localhost:11434/v1 或 https://api.openai.com/v1",
            font=('Microsoft YaHei', 8),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        # Model Name
        tk.Label(
            parent, text="Model Name",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        self.model_entry = tk.Entry(parent, font=('Microsoft YaHei', 10), width=50)
        self.model_entry.pack(padx=20, pady=5)
        tk.Label(
            parent, text="例如：qwen3.5:9b 或 gpt-4o",
            font=('Microsoft YaHei', 8),
            bg='#f5f7fa', fg='#666'
        ).pack(anchor=tk.W, padx=20)

        # API Key
        tk.Label(
            parent, text="API Key",
            font=('Microsoft YaHei', 10),
            bg='#f5f7fa'
        ).pack(anchor=tk.W, padx=20, pady=(15, 5))

        self.api_key_entry = tk.Entry(parent, font=('Microsoft YaHei', 10), width=50, show='*')
        self.api_key_entry.pack(padx=20, pady=5)

        # 说明标签
        self.protocol_hint = tk.Label(
            parent, text="",
            font=('Microsoft YaHei', 9),
            bg='#f5f7fa', fg='#ff9800'
        )
        self.protocol_hint.pack(anchor=tk.W, padx=20, pady=10)

    def on_protocol_change(self):
        """协议切换时更新提示和默认值。"""
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

    def browse_folder(self):
        """浏览选择文件夹。"""
        folder = filedialog.askdirectory(title="选择工作文件夹")
        if folder:
            self.work_folder_entry.delete(0, tk.END)
            self.work_folder_entry.insert(0, folder)

    def load_config(self):
        """加载配置。"""
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

    def save_config(self):
        """保存配置。"""
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

        messagebox.showinfo("✅ 保存成功", "配置已保存到 config.json")
        self.parent.load_config()
        self.destroy()


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
