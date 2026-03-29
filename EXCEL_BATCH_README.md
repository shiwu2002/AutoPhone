# Excel 批量处理 - 极简使用说明

## 快速使用（3 步搞定）

### 1️⃣ 准备 Excel 文件

创建 Excel 文件，包含"问题"列：

| 问题 | 其他列... |
|------|----------|
| 1+1=? | ... |
| 2+2=? | ... |
| 3+3=? | ... |

### 2️⃣ 运行命令

```bash
python batch_processor.py --input 问题.xlsx
```

### 3️⃣ 查看结果

自动生成 `问题_answers.xlsx`，新增"答案"列：

| 问题 | 其他列... | **答案** |
|------|----------|---------|
| 1+1=? | ... | 2 |
| 2+2=? | ... | 4 |
| 3+3=? | ... | 6 |

---

## 常用命令

### 基础用法
```bash
# 使用默认设置（问题列名："问题"，模板："请回答：{content}"）
python batch_processor.py --input 问题.xlsx
```

### 自定义输出文件
```bash
python batch_processor.py --input 问题.xlsx --output 最终答案.xlsx
```

### 自定义问题列
```bash
python batch_processor.py --input 考题.xlsx --column 题目
```

### 自定义任务模板
```bash
# 简单回答
python batch_processor.py --input 问题.xlsx --template "请回答：{content}"

# 详细解答
python batch_processor.py --input 问题.xlsx --template "请详细解释：{content}"

# 带格式要求
python batch_processor.py --input 问题.xlsx --template "请用 JSON 格式回答：{content}"
```

### 显示详细过程
```bash
python batch_processor.py --input 问题.xlsx --verbose
```

---

## 完整参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--input` | `-i` | 输入 Excel 文件路径（必需） | - |
| `--output` | `-o` | 输出 Excel 文件路径 | input_answers.xlsx |
| `--column` | `-c` | 问题所在的列名 | "问题" |
| `--template` | `-t` | 任务模板 | "请回答：{content}" |
| `--verbose` | `-v` | 显示详细输出 | False |

---

## 示例场景

### 场景 1: 批量答题
```bash
python batch_processor.py --input 考试题.xlsx
```

### 场景 2: 多语言翻译
```bash
python batch_processor.py \
  --input 待翻译.xlsx \
  --column 中文句子 \
  --template "请翻译成英文：{content}"
```

### 场景 3: 数据标注
```bash
python batch_processor.py \
  --input 评论数据.xlsx \
  --column 评论内容 \
  --template "请判断这条评论的情感倾向（正面/负面/中性）：{content}"
```

### 场景 4: 知识问答
```bash
python batch_processor.py \
  --input 知识库问答.xlsx \
  --column 问题 \
  --template "请用简洁的语言回答这个问题：{content}"
```

---

## 执行流程

```
1. 读取 Excel 文件
   ↓
2. 提取"问题"列的所有问题
   ↓
3. 使用多设备并行执行（如果有多个设备）
   ↓
4. 收集所有 AI 回复
   ↓
5. 在原 Excel 中新增"答案"列
   ↓
6. 保存为新文件
```

---

## 结果示例

### 输入文件（问题.xlsx）

| 序号 | 问题 | 难度 |
|------|------|------|
| 1 | 水的化学式是什么？ | 简单 |
| 2 | 光合作用的原理？ | 中等 |
| 3 | 量子力学是什么？ | 困难 |

### 输出文件（问题_answers.xlsx）

| 序号 | 问题 | 难度 | **答案** |
|------|------|------|---------|
| 1 | 水的化学式是什么？ | 简单 | H₂O |
| 2 | 光合作用的原理？ | 中等 | 光合作用是植物利用光能将二氧化碳和水转化为有机物的过程... |
| 3 | 量子力学是什么？ | 困难 | 量子力学是研究微观粒子运动规律的物理学分支... |

---

## 性能参考

| 问题数 | 设备数 | 预计耗时 |
|--------|--------|----------|
| 10 | 1 | ~100 秒 |
| 10 | 2 | ~50 秒 |
| 10 | 3 | ~35 秒 |
| 100 | 3 | ~350 秒 |

*注：实际时间取决于问题复杂度和模型响应速度*

---

## 常见问题

### Q: 支持哪些 Excel 格式？
A: 支持 `.xlsx` 和 `.xls` 格式。

### Q: 问题列可以自定义吗？
A: 可以，使用 `--column` 参数指定列名。

### Q: 可以批量处理多个文件吗？
A: 需要多次运行命令，每次处理一个文件。

### Q: 如何处理失败的问题？
A: 失败的问题会在答案列显示错误信息，可以单独提取这些问题的重试。

### Q: 支持 CSV 文件吗？
A: 当前版本只支持 Excel，如需 CSV 支持可以修改代码使用 `pd.read_csv()`。

---

## 依赖安装

确保已安装所需依赖：

```bash
pip install pandas openpyxl
```

---

## 核心代码（供参考）

```python
from main import PhoneAgentAPI
import pandas as pd

# 1. 读取 Excel
df = pd.read_excel("问题.xlsx")
questions = df['问题'].tolist()

# 2. 执行批量任务
api = PhoneAgentAPI()
result = api.run_batch_parallel(
    questions=questions,
    task_template="请回答：{content}"
)

# 3. 保存结果
df['答案'] = [r.answer for r in result.results]
df.to_excel("答案.xlsx", index=False)
```

---

**就这么简单！** 🎉
