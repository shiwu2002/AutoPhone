#!/usr/bin/env python3
"""
PhoneAgent GUI 应用 - 基于 tkinter 的桌面客户端
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import json
import os
import webbrowser
from pathlib import Path
from datetime import datetime

import requests

# 配置 - 从配置文件读取端口
API_BASE_URL = "http://localhost:5001"  # 默认端口，会从 config.json 读取
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 尝试从配置文件读取端口
try:
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            port = config.get('server', {}).get('port', 5001)
            API_BASE_URL = f"http://localhost:{port}"
except Exception:
    pass  # 使用默认端口


class PhoneAgentGUI:
    """PhoneAgent 桌面 GUI 应用"""

    def __init__(self, root):
        self.root = root
        self.root.title("PhoneAgent - 手机自动化代理")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # 全局变量
        self.selected_file = None
        self.current_token = None

        # 设置样式
        self.setup_styles()

        # 创建界面
        self.create_menu()
        self.create_header()
        self.create_notebook()

        # 初始化状态
        self.check_server_status()
        self.refresh_device_status()

    def setup_styles(self):
        """设置 UI 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        # 配置颜色
        self.colors = {
            'primary': '#667eea',
            'secondary': '#764ba2',
            'success': '#4caf50',
            'error': '#f44336',
            'warning': '#ff9800',
            'info': '#2196f3',
            'bg_light': '#f5f7fa',
            'text_dark': '#333',
            'text_light': '#666',
        }

        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground=self.colors['primary'])
        style.configure('Subtitle.TLabel', font=('Arial', 12), foreground=self.colors['text_light'])
        style.configure('Success.TLabel', foreground=self.colors['success'])
        style.configure('Error.TLabel', foreground=self.colors['error'])
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="退出", command=self.root.quit)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="打开浏览器版", command=self.open_web_version)
        tools_menu.add_command(label="刷新统计", command=self.refresh_stats)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_header(self):
        """创建头部区域"""
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], pady=15)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(
            header_frame,
            text="📱 PhoneAgent",
            font=('Arial', 20, 'bold'),
            bg=self.colors['primary'],
            fg='white'
        )
        title_label.pack()

        subtitle_label = tk.Label(
            header_frame,
            text="AI 驱动的手机自动化代理系统",
            font=('Arial', 10),
            bg=self.colors['primary'],
            fg='white'
        )
        subtitle_label.pack()

        # 设备状态栏
        self.device_status_frame = tk.Frame(self.root, bg=self.colors['bg_light'], pady=10)
        self.device_status_frame.pack(fill=tk.X, padx=20, pady=(10, 0))

        self.device_status_label = tk.Label(
            self.device_status_frame,
            text="🔌 设备状态：检测中...",
            font=('Arial', 10),
            bg=self.colors['bg_light'],
            fg=self.colors['text_dark']
        )
        self.device_status_label.pack(side=tk.LEFT, padx=10)

        self.device_manage_btn = tk.Button(
            self.device_status_frame,
            text="📱 管理设备",
            command=self.show_device_manager,
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        self.device_manage_btn.pack(side=tk.RIGHT, padx=10)

    def create_notebook(self):
        """创建选项卡"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 任务执行标签页
        self.task_frame = ttk.Frame(notebook)
        notebook.add(self.task_frame, text="  执行任务  ")
        self.create_task_tab()

        # 批量任务标签页
        self.batch_frame = ttk.Frame(notebook)
        notebook.add(self.batch_frame, text="  批量任务  ")
        self.create_batch_tab()

        # 历史记录标签页
        self.history_frame = ttk.Frame(notebook)
        notebook.add(self.history_frame, text="  历史记录  ")
        self.create_history_tab()

        # 统计信息标签页
        self.stats_frame = ttk.Frame(notebook)
        notebook.add(self.stats_frame, text="  统计信息  ")
        self.create_stats_tab()

    def create_task_tab(self):
        """创建任务执行标签页"""
        # 任务输入
        input_frame = tk.LabelFrame(self.task_frame, text="任务描述", padx=10, pady=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        self.task_input = scrolledtext.ScrolledText(
            input_frame,
            height=5,
            font=('Arial', 11),
            wrap=tk.WORD,
            bg='white'
        )
        self.task_input.pack(fill=tk.X)
        self.task_input.insert('1.0', '请输入要执行的任务，例如：打开微信并给张三发消息：晚上好')

        # 执行按钮
        self.execute_btn = tk.Button(
            input_frame,
            text="▶️ 执行任务",
            command=self.execute_task,
            bg=self.colors['primary'],
            fg='white',
            font=('Arial', 11, 'bold'),
            relief=tk.FLAT,
            padx=20,
            pady=10
        )
        self.execute_btn.pack(pady=10)

        # 结果区域
        result_frame = tk.LabelFrame(self.task_frame, text="执行结果", padx=10, pady=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.task_result = scrolledtext.ScrolledText(
            result_frame,
            height=10,
            font=('Arial', 10),
            wrap=tk.WORD,
            bg=self.colors['bg_light']
        )
        self.task_result.pack(fill=tk.BOTH, expand=True)

    def create_batch_tab(self):
        """创建批量任务标签页"""
        # 文件选择区域
        file_frame = tk.LabelFrame(self.batch_frame, text="文件选择", padx=10, pady=10)
        file_frame.pack(fill=tk.X, padx=10, pady=10)

        self.file_label = tk.Label(file_frame, text="未选择文件", font=('Arial', 10), fg=self.colors['text_light'])
        self.file_label.pack(side=tk.LEFT, padx=5)

        tk.Button(
            file_frame,
            text="📁 选择文件",
            command=self.select_file,
            bg=self.colors['info'],
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).pack(side=tk.RIGHT, padx=5)

        # 任务模板
        task_frame = tk.LabelFrame(self.batch_frame, text="任务模板（使用 {content} 作为问题占位符）", padx=10, pady=10)
        task_frame.pack(fill=tk.X, padx=10, pady=10)

        self.batch_task_input = scrolledtext.ScrolledText(
            task_frame,
            height=3,
            font=('Arial', 11),
            wrap=tk.WORD,
            bg='white'
        )
        self.batch_task_input.pack(fill=tk.X)
        self.batch_task_input.insert('1.0', '请回答这个问题：{content}')

        # 选项
        option_frame = tk.Frame(self.batch_frame)
        option_frame.pack(fill=tk.X, padx=10, pady=5)

        self.embed_screenshot_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            option_frame,
            text="嵌入截图到 Excel（每个问答的截图会直接嵌入到答案旁边）",
            variable=self.embed_screenshot_var,
            font=('Arial', 10)
        ).pack(anchor=tk.W)

        # 按钮区域
        btn_frame = tk.Frame(self.batch_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(
            btn_frame,
            text="📋 预览文件",
            command=self.preview_file,
            bg=self.colors['info'],
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)

        self.execute_batch_btn = tk.Button(
            btn_frame,
            text="▶️ 开始执行",
            command=self.execute_batch,
            bg=self.colors['success'],
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            padx=20,
            pady=8
        )
        self.execute_batch_btn.pack(side=tk.LEFT, padx=5)

        # 进度区域
        progress_frame = tk.LabelFrame(self.batch_frame, text="执行进度", padx=10, pady=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(progress_frame, text="0 / 0", font=('Arial', 10))
        self.progress_label.pack(pady=5)

        self.current_question_label = tk.Label(progress_frame, text="", font=('Arial', 9), fg=self.colors['text_light'])
        self.current_question_label.pack()

        # 结果区域
        result_frame = tk.LabelFrame(self.batch_frame, text="执行结果", padx=10, pady=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.batch_result = scrolledtext.ScrolledText(
            result_frame,
            height=10,
            font=('Arial', 10),
            wrap=tk.WORD,
            bg=self.colors['bg_light']
        )
        self.batch_result.pack(fill=tk.BOTH, expand=True)

        # 下载按钮
        self.download_btn = tk.Button(
            result_frame,
            text="📥 下载结果文件",
            command=self.download_result,
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=5,
            state=tk.DISABLED
        )
        self.download_btn.pack(pady=5)

    def create_history_tab(self):
        """创建历史记录标签页"""
        # 搜索栏
        search_frame = tk.Frame(self.history_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(search_frame, text="🔍 搜索:").pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(search_frame, font=('Arial', 10), width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(
            search_frame,
            text="搜索",
            command=self.search_history,
            relief=tk.FLAT,
            padx=15,
            bg=self.colors['info'],
            fg='white'
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            search_frame,
            text="🔄 刷新",
            command=self.load_history,
            relief=tk.FLAT,
            padx=15,
            bg=self.colors['bg_light'],
            fg=self.colors['text_dark']
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            search_frame,
            text="🗑️ 清除历史",
            command=self.clear_history,
            relief=tk.FLAT,
            padx=15,
            bg=self.colors['error'],
            fg='white'
        ).pack(side=tk.RIGHT, padx=5)

        # 历史记录表格
        table_frame = tk.Frame(self.history_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('ID', '任务', '结果', '步数', '状态', '时间')
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)

        self.history_tree.column('任务', width=200)
        self.history_tree.column('结果', width=200)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 加载历史
        self.load_history()

    def create_stats_tab(self):
        """创建统计信息标签页"""
        stats_container = tk.Frame(self.stats_frame)
        stats_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 统计卡片
        self.stats_vars = {}
        stat_configs = [
            ('总任务数', 'total_tasks', 0, 0),
            ('成功率', 'success_rate', 0, 1),
            ('平均步数', 'avg_steps', 1, 0),
            ('平均耗时 (秒)', 'avg_duration', 1, 1),
        ]

        for label_text, var_name, row, col in stat_configs:
            frame = tk.Frame(stats_container, bg=self.colors['bg_light'], relief=tk.RAISED, bd=2)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')

            label = tk.Label(frame, text=label_text, font=('Arial', 12), bg=self.colors['bg_light'])
            label.pack(pady=(10, 5))

            var = tk.StringVar(value='-')
            value_label = tk.Label(
                frame,
                textvariable=var,
                font=('Arial', 24, 'bold'),
                fg=self.colors['primary'],
                bg=self.colors['bg_light']
            )
            value_label.pack(pady=(0, 10))

            self.stats_vars[var_name] = var

        stats_container.columnconfigure(0, weight=1)
        stats_container.columnconfigure(1, weight=1)
        stats_container.rowconfigure(0, weight=1)
        stats_container.rowconfigure(1, weight=1)

        # 刷新按钮
        tk.Button(
            self.stats_frame,
            text="🔄 刷新统计",
            command=self.refresh_stats,
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            padx=20,
            pady=10
        ).pack(pady=20)

    def check_server_status(self):
        """检查服务器状态"""
        def check():
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    self.device_status_label.config(
                        text="✅ 服务器已连接",
                        fg=self.colors['success']
                    )
                else:
                    self.device_status_label.config(
                        text="❌ 服务器连接失败",
                        fg=self.colors['error']
                    )
            except Exception:
                self.device_status_label.config(
                    text="❌ 服务器未启动",
                    fg=self.colors['error']
                )

        threading.Thread(target=check, daemon=True).start()

    def refresh_device_status(self):
        """刷新设备状态"""
        def refresh():
            try:
                response = requests.get(f"{API_BASE_URL}/devices", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        count = data.get('count', 0)
                        text = f"🔌 {count} 台设备已连接" if count > 0 else "🔌 未连接设备"
                        self.root.after(0, lambda: self.device_status_label.config(
                            text=text,
                            fg=self.colors['success'] if count > 0 else self.colors['warning']
                        ))
                    else:
                        self.root.after(0, lambda: self.device_status_label.config(
                            text=f"❌ 获取失败：{data.get('error', '未知')}",
                            fg=self.colors['error']
                        ))
                else:
                    self.root.after(0, lambda: self.device_status_label.config(
                        text=f"❌ HTTP {response.status_code}",
                        fg=self.colors['error']
                    ))
            except requests.exceptions.RequestException:
                self.root.after(0, lambda: self.device_status_label.config(
                    text="❌ 服务器未响应",
                    fg=self.colors['error']
                ))
            except Exception:
                pass

        threading.Thread(target=refresh, daemon=True).start()
        # 每 10 秒自动刷新
        self.root.after(10000, self.refresh_device_status)

    def show_device_manager(self):
        """显示设备管理器对话框"""
        device_window = tk.Toplevel(self.root)
        device_window.title("设备管理")
        device_window.geometry("600x400")
        device_window.resizable(False, False)

        # 连接设备区域
        connect_frame = tk.LabelFrame(device_window, text="连接远程设备", padx=10, pady=10)
        connect_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(connect_frame, text="设备地址:").grid(row=0, column=0, padx=5, pady=5)
        address_entry = tk.Entry(connect_frame, width=30, font=('Arial', 10))
        address_entry.grid(row=0, column=1, padx=5, pady=5)
        address_entry.insert(0, "192.168.1.100:5555")

        def connect_device():
            address = address_entry.get().strip()
            if not address:
                messagebox.showwarning("警告", "请输入设备地址")
                return
            try:
                response = requests.post(
                    f"{API_BASE_URL}/devices/connect",
                    json={'address': address},
                    timeout=10
                )
                data = response.json()
                if data.get('success'):
                    messagebox.showinfo("成功", data.get('message', '连接成功'))
                    refresh_devices()
                else:
                    messagebox.showerror("失败", data.get('message', '连接失败'))
            except Exception as e:
                messagebox.showerror("错误", f"连接失败：{str(e)}")

        tk.Button(
            connect_frame,
            text="连接",
            command=connect_device,
            bg=self.colors['primary'],
            fg='white',
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).grid(row=0, column=2, padx=10, pady=5)

        # 设备列表
        list_frame = tk.LabelFrame(device_window, text="已连接设备", padx=10, pady=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        device_listbox = tk.Listbox(list_frame, font=('Arial', 10), height=10)
        device_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=device_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        device_listbox.configure(yscrollcommand=scrollbar.set)

        def refresh_devices():
            device_listbox.delete(0, tk.END)
            try:
                response = requests.get(f"{API_BASE_URL}/devices", timeout=5)
                print(f"设备列表响应状态码：{response.status_code}")
                print(f"设备列表响应内容：{response.text}")

                if response.status_code != 200:
                    device_listbox.insert(tk.END, f"HTTP 错误：{response.status_code}")
                    return

                data = response.json()
                print(f"设备列表解析数据：{data}")

                if data.get('success') and data.get('devices'):
                    for device in data['devices']:
                        info = f"{device['device_id']} | {device['status']} | {device['connection_type']} | {device['model']}"
                        device_listbox.insert(tk.END, info)
                elif data.get('success') and data.get('count', 0) == 0:
                    device_listbox.insert(tk.END, "暂无设备连接")
                else:
                    error = data.get('error', '未知错误')
                    device_listbox.insert(tk.END, f"获取失败：{error}")
            except requests.exceptions.RequestException as e:
                device_listbox.insert(tk.END, f"连接服务器失败：{str(e)}")
            except Exception as e:
                device_listbox.insert(tk.END, f"获取设备列表失败：{str(e)}")

        refresh_btn = tk.Button(
            device_window,
            text="🔄 刷新设备列表",
            command=refresh_devices,
            bg=self.colors['bg_light'],
            relief=tk.FLAT,
            padx=15,
            pady=8
        )
        refresh_btn.pack(pady=10)

        refresh_devices()

    def execute_task(self):
        """执行单个任务"""
        task = self.task_input.get('1.0', tk.END).strip()
        if not task or task == "请输入要执行的任务，例如：打开微信并给张三发消息：晚上好":
            messagebox.showwarning("警告", "请输入任务描述")
            return

        self.execute_btn.config(state=tk.DISABLED, text="执行中...")
        self.task_result.delete('1.0', tk.END)
        self.task_result.insert('1.0', "任务执行中，请稍候...")

        def run_task():
            try:
                response = requests.post(
                    f"{API_BASE_URL}/run",
                    json={'task': task},
                    timeout=300
                )
                data = response.json()
                if data.get('success'):
                    result = data.get('result', '')
                    steps = data.get('steps', 0)
                    self.root.after(0, lambda: self.task_result.delete('1.0', tk.END))
                    self.root.after(0, lambda: self.task_result.insert('1.0', f"执行成功!\n\n结果:\n{result}\n\n步数：{steps}"))
                    self.root.after(0, lambda: self.load_history())
                    self.root.after(0, lambda: self.refresh_stats())
                else:
                    error = data.get('error', '未知错误')
                    self.root.after(0, lambda: self.task_result.delete('1.0', tk.END))
                    self.root.after(0, lambda: self.task_result.insert('1.0', f"执行失败:\n{error}"))
            except Exception as e:
                self.root.after(0, lambda: self.task_result.delete('1.0', tk.END))
                self.root.after(0, lambda: self.task_result.insert('1.0', f"请求失败:\n{str(e)}"))
            finally:
                self.root.after(0, lambda: self.execute_btn.config(state=tk.NORMAL, text="▶️ 执行任务"))

        threading.Thread(target=run_task, daemon=True).start()

    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择 Excel 或文本文件",
            filetypes=[
                ("Excel 文件", "*.xlsx *.xls"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.selected_file = file_path
            self.file_label.config(text=str(Path(file_path).name))

    def preview_file(self):
        """预览文件内容"""
        if not self.selected_file:
            messagebox.showwarning("警告", "请先选择文件")
            return

        # 上传文件
        self.upload_and_preview()

    def upload_and_preview(self):
        """上传文件并预览"""
        def upload():
            try:
                with open(self.selected_file, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=30)
                    data = response.json()
                    if data.get('success'):
                        file_path = data['file_path']
                        # 预览
                        preview_response = requests.post(
                            f"{API_BASE_URL}/excel/preview",
                            json={'file': file_path},
                            timeout=30
                        )
                        preview_data = preview_response.json()
                        if preview_data.get('success'):
                            info = f"文件：{Path(self.selected_file).name}\n"
                            info += f"列：{', '.join(preview_data['columns'])}\n"
                            info += f"问题数：{preview_data['count']}\n"
                            info += f"问题列：{preview_data['question_column']}\n\n"
                            info += "前 10 个问题:\n"
                            for i, q in enumerate(preview_data['questions'][:10], 1):
                                info += f"  {i}. {q}\n"
                            if len(preview_data['questions']) > 10:
                                info += f"  ... 还有 {len(preview_data['questions']) - 10} 个问题"
                            self.root.after(0, lambda: messagebox.showinfo("文件预览", info))
                        else:
                            self.root.after(0, lambda: messagebox.showerror("错误", preview_data.get('error', '预览失败')))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", data.get('error', '上传失败')))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"操作失败：{str(e)}"))

        threading.Thread(target=upload, daemon=True).start()

    def execute_batch(self):
        """执行批量任务"""
        if not self.selected_file:
            messagebox.showwarning("警告", "请先选择文件")
            return

        task = self.batch_task_input.get('1.0', tk.END).strip()
        if not task or task == "请回答这个问题：{content}":
            messagebox.showwarning("警告", "请输入任务模板")
            return

        self.execute_batch_btn.config(state=tk.DISABLED, text="执行中...")
        self.batch_result.delete('1.0', tk.END)
        self.batch_result.insert('1.0', "正在上传文件，请稍候...")
        self.download_btn.config(state=tk.DISABLED)
        self.current_download_file = None

        def run_batch():
            try:
                # 上传文件
                with open(self.selected_file, 'rb') as f:
                    files = {'file': f}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=30)
                    data = response.json()
                    if not data.get('success'):
                        self.root.after(0, lambda: self.batch_result.delete('1.0', tk.END))
                        self.root.after(0, lambda: self.batch_result.insert('1.0', f"上传失败:\n{data.get('error', '未知错误')}"))
                        self.root.after(0, lambda: self.execute_batch_btn.config(state=tk.NORMAL, text="▶️ 开始执行"))
                        return

                    file_path = data['file_path']

                    # 执行批量任务
                    self.root.after(0, lambda: self.batch_result.delete('1.0', tk.END))
                    self.root.after(0, lambda: self.batch_result.insert('1.0', "正在执行批量任务，请稍候...\n\n"))

                    batch_response = requests.post(
                        f"{API_BASE_URL}/excel/batch",
                        json={
                            'file': file_path,
                            'task': task,
                            'embed_screenshot': self.embed_screenshot_var.get()
                        },
                        timeout=600
                    )
                    batch_data = batch_response.json()

                    if batch_data.get('success'):
                        stats = batch_data.get('statistics', {})
                        output_file = batch_data.get('output_file', '')

                        result_text = f"批量任务执行完成!\n\n"
                        result_text += f"总问题数：{stats.get('total', 0)}\n"
                        result_text += f"成功：{stats.get('success', 0)}\n"
                        result_text += f"失败：{stats.get('failed', 0)}\n"
                        result_text += f"成功率：{stats.get('success', 0) / stats.get('total', 1) * 100:.1f}%\n\n"
                        result_text += f"结果文件：{output_file}\n"

                        self.root.after(0, lambda: self.batch_result.delete('1.0', tk.END))
                        self.root.after(0, lambda: self.batch_result.insert('1.0', result_text))
                        self.root.after(0, lambda: self.progress_bar.config(value=100))
                        self.root.after(0, lambda: self.progress_label.config(text=f"{stats.get('total', 0)} / {stats.get('total', 0)}"))
                        self.root.after(0, lambda: self.current_question_label.config(text="执行完成！"))

                        # 保存下载文件路径
                        self.current_download_file = output_file
                        self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))

                        self.root.after(0, lambda: self.load_history())
                        self.root.after(0, lambda: self.refresh_stats())
                    else:
                        error = batch_data.get('error', '未知错误')
                        self.root.after(0, lambda: self.batch_result.delete('1.0', tk.END))
                        self.root.after(0, lambda: self.batch_result.insert('1.0', f"执行失败:\n{error}"))

            except Exception as e:
                self.root.after(0, lambda: self.batch_result.delete('1.0', tk.END))
                self.root.after(0, lambda: self.batch_result.insert('1.0', f"请求失败:\n{str(e)}"))
            finally:
                self.root.after(0, lambda: self.execute_batch_btn.config(state=tk.NORMAL, text="▶️ 开始执行"))

        threading.Thread(target=run_batch, daemon=True).start()

    def download_result(self):
        """下载结果文件"""
        if not self.current_download_file:
            messagebox.showwarning("警告", "没有可下载的文件")
            return

        try:
            # 弹出文件保存对话框
            file_path = filedialog.asksaveasfilename(
                title="保存结果文件",
                defaultextension=".xlsx",
                filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
                initialfile=f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            if file_path:
                # 从服务器下载文件
                response = requests.get(f"{API_BASE_URL}/download", params={'file': self.current_download_file}, timeout=30)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    messagebox.showinfo("成功", f"文件已保存到:\n{file_path}")
                    # 询问是否打开文件
                    if messagebox.askyesno("提示", "是否打开结果文件？"):
                        os.startfile(file_path) if os.name == 'nt' else os.system(f'open "{file_path}"')
                else:
                    messagebox.showerror("错误", "下载失败")
        except Exception as e:
            messagebox.showerror("错误", f"下载失败：{str(e)}")

    def load_history(self):
        """加载历史记录"""
        def load():
            try:
                response = requests.get(f"{API_BASE_URL}/history?limit=50", timeout=10)
                data = response.json()
                if data.get('success') and data.get('records'):
                    records = data['records']
                    self.root.after(0, lambda: self.history_tree.delete(*self.history_tree.get_children()))
                    for record in records:
                        status = "✅ 成功" if record.get('success') else "❌ 失败"
                        self.history_tree.insert('', tk.END, values=(
                            record.get('id', ''),
                            record.get('task', '')[:50] + '...' if len(record.get('task', '')) > 50 else record.get('task', ''),
                            record.get('result', '')[:50] + '...' if len(record.get('result', '')) > 50 else record.get('result', ''),
                            record.get('steps', ''),
                            status,
                            record.get('created_at', '')[:16] if record.get('created_at') else ''
                        ))
                else:
                    self.root.after(0, lambda: self.history_tree.delete(*self.history_tree.get_children()))
                    self.root.after(0, lambda: self.history_tree.insert('', tk.END, values=('', '暂无历史记录', '', '', '', '')))
            except Exception:
                self.root.after(0, lambda: self.history_tree.delete(*self.history_tree.get_children()))
                self.root.after(0, lambda: self.history_tree.insert('', tk.END, values=('', '加载失败', '', '', '', '')))

        threading.Thread(target=load, daemon=True).start()

    def search_history(self):
        """搜索历史记录"""
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.load_history()
            return

        def search():
            try:
                response = requests.get(f"{API_BASE_URL}/history/search?keyword={keyword}", timeout=10)
                data = response.json()
                if data.get('success') and data.get('records'):
                    records = data['records']
                    self.root.after(0, lambda: self.history_tree.delete(*self.history_tree.get_children()))
                    for record in records:
                        status = "✅ 成功" if record.get('success') else "❌ 失败"
                        self.history_tree.insert('', tk.END, values=(
                            record.get('id', ''),
                            record.get('task', '')[:50] + '...' if len(record.get('task', '')) > 50 else record.get('task', ''),
                            record.get('result', '')[:50] + '...' if len(record.get('result', '')) > 50 else record.get('result', ''),
                            record.get('steps', ''),
                            status,
                            record.get('created_at', '')[:16] if record.get('created_at') else ''
                        ))
                else:
                    messagebox.showinfo("搜索结果", "未找到匹配的记录")
            except Exception as e:
                messagebox.showerror("错误", f"搜索失败：{str(e)}")

        threading.Thread(target=search, daemon=True).start()

    def clear_history(self):
        """清除历史记录"""
        if not messagebox.askyesno("确认", "确定要清除所有历史记录吗？\n\n此操作不可撤销！"):
            return

        def clear():
            try:
                response = requests.post(f"{API_BASE_URL}/history/clear", timeout=10)
                data = response.json()
                if data.get('success'):
                    self.root.after(0, lambda: messagebox.showinfo("成功", "历史记录已清除"))
                    self.root.after(0, lambda: self.load_history())
                    self.root.after(0, lambda: self.refresh_stats())
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", data.get('error', '清除失败')))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"清除失败：{str(e)}"))

        threading.Thread(target=clear, daemon=True).start()

    def refresh_stats(self):
        """刷新统计信息"""
        def load():
            try:
                response = requests.get(f"{API_BASE_URL}/history/stats", timeout=10)
                data = response.json()
                if data.get('success'):
                    stats = data.get('statistics', {})
                    self.root.after(0, lambda: self.stats_vars['total_tasks'].set(str(stats.get('total_tasks', '-'))))
                    self.root.after(0, lambda: self.stats_vars['success_rate'].set(f"{stats.get('success_rate', '-'):.1f}%"))
                    self.root.after(0, lambda: self.stats_vars['avg_steps'].set(str(stats.get('average_steps', '-'))))
                    self.root.after(0, lambda: self.stats_vars['avg_duration'].set(str(stats.get('average_duration_seconds', '-'))))
            except Exception:
                pass

        threading.Thread(target=load, daemon=True).start()

    def open_web_version(self):
        """打开浏览器版本"""
        webbrowser.open(f"{API_BASE_URL}")

    def show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于 PhoneAgent",
            "PhoneAgent - 手机自动化代理系统\n\n"
            "版本：1.0.0\n\n"
            "AI 驱动的手机自动化代理系统,\n"
            "可以通过自然语言指令控制手机执行各种任务。\n\n"
            "© 2025 PhoneAgent"
        )


def main():
    """主函数"""
    root = tk.Tk()
    app = PhoneAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
