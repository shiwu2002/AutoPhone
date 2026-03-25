# PhoneAgent 使用指南

## 快速开始

### 1. 启动服务

```bash
# 启动服务器和 GUI
python server.py
```

服务器会自动启动 GUI 界面。

### 2. 配置

点击 **"⚙️ 设置"** 按钮配置：

- **工作文件夹**：MasterAgent 查找和保存文件的默认位置
- **模型配置**：选择模型提供商和 API Key

### 3. 与 MasterAgent 对话

在聊天界面中，你可以：

#### 📄 处理文件
- 拖放文件到输入框上方
- 点击"浏览文件"选择文件
- 说"读取 xxx.xlsx"或"处理这个文件"

#### 📱 联通客服问答
- 直接提问："联通安全管家有哪些功能？"
- 批量处理："批量处理 questions.xlsx 中的所有问题"

#### ⌨️ 执行命令
- "执行命令：dir"
- "!python --version"
- "shell: pip list"

#### 🔧 调用 Skills
- "使用 liantong_ai_query 查询流量套餐"
- "调用 excel_tools 读取文件"

---

## MasterAgent 能力

### 1. 智能任务编排

MasterAgent 会自动分析你的需求，调用相应的 Skills 完成任务。

**示例流程：**
```
用户：批量处理 questions.xlsx
  ↓
MasterAgent 分析意图
  ↓
1. 调用 execute_excel_batch 获取问题列表
2. 对每个问题调用 liantong_ai_query 获取答案
3. 调用 write_excel_answer 写入答案
  ↓
返回执行结果
```

### 2. 命令行执行

支持执行系统命令，在工作文件夹中运行：

```
用户：执行命令：python test.py
MasterAgent → subprocess.run("python test.py", cwd=work_folder)
返回输出结果
```

### 3. 文件操作

自动管理工作文件夹中的文件：

- 上传的文件保存到工作文件夹
- 说"读取 xxx.xlsx"会自动在文件夹中查找
- 批量处理结果也保存在同一位置

### 4. 上下文记忆

MasterAgent 记住对话历史：

```
用户：读取 data.xlsx
Agent：显示文件内容...

用户：处理它
Agent：开始批量处理 data.xlsx...
```

---

## Skills 配置

Skills 的配置在 `skills_config.json` 中，格式如下：

```json
{
  "skill_id": "liantong_ai_query",
  "name": "联通 AI 客服问答",
  "description": "向中国联通 AI 客服提问并获取回复",
  "module_path": "skills.liantong_ai_query.skill",
  "enabled": true,
  "parameters": [
    {"name": "question", "type": "str", "description": "问题内容", "required": true}
  ],
  "user_config": {
    "app_name": "中国联通"
  }
}
```

### 添加新 Skill

1. 在 `skills/` 目录下创建新文件夹
2. 编写 `skill.py` 实现 `execute()` 函数
3. 在 `skills_config.json` 中注册

详见：[docs/SKILL_DEVELOPMENT.md](docs/SKILL_DEVELOPMENT.md)

---

## 架构说明

```
┌─────────────────────────────────────────┐
│           GUI (gui_app.py)              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │  聊天   │  │ 文件上传 │  │  设置   │ │
│  └─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│        Server (server.py)               │
│  ┌───────────────────────────────────┐  │
│  │  /chat  - MasterAgent 聊天        │  │
│  │  /upload - 文件上传               │  │
│  │  /skills - Skills 管理            │  │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│       MasterAgent (agent.py)            │
│  ┌───────────────────────────────────┐  │
│  │  意图识别 → 任务编排 → Skill 调用  │  │
│  │  命令行执行 │ 文件操作 │ 上下文   │  │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│         Skills (skills/)                │
│  ┌─────────────┐  ┌─────────────┐      │
│  │ liantong_   │  │ excel_tools │      │
│  │ ai_query    │  │             │      │
│  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────┘
```

---

## 常见问题

### Q: 工作文件夹有什么用？
A: 所有文件的查找和保存都在此文件夹中进行，避免路径混乱。

### Q: 如何修改模型配置？
A: 点击"设置" → "模型配置"，或编辑 `config.json`。

### Q: Skills 如何配置？
A: Skills 的配置在 `skills_config.json` 中，编辑后重启服务器。

### Q: 命令行执行失败？
A: 检查工作文件夹是否正确，命令是否可执行。

---

## 文件结构

```
e:\Python\AutoPhone\
├── server.py              # HTTP 服务器
├── gui_app.py             # GUI 界面
├── config.json            # 主配置（模型、工作文件夹等）
├── skills_config.json     # Skills 配置
├── mainAgent/
│   ├── agent.py           # MasterAgent 核心
│   ├── skills.py          # Skills 注册和调用
│   ├── skill_config.py    # Skills 配置管理
│   └── skill_template.py  # Skill 模板生成
└── skills/
    ├── liantong_ai_query/ # 联通客服 Skill
    └── excel_tools/       # Excel 工具 Skill
```

---

## 下一步

1. **配置工作文件夹** - 点击"设置"选择你的项目文件夹
2. **上传文件测试** - 拖放一个 Excel 文件试试
3. **开始对话** - 说"你好"或"帮我处理这个文件"

祝你使用愉快！🎉
