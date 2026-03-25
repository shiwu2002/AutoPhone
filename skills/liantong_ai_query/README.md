# 联通 AI 客服问答 Skill

向中国联通 AI 客服提问并获取回复的独立技能包。

## 使用方法

### 方式 1: 直接调用

```python
from skills.liantong_ai_query import execute

result = execute(question="联通安全管家有哪些功能？")
print(result["answer"])
```

### 方式 2: 通过主 Agent 调用

```python
from phone_agent import MasterAgent

agent = MasterAgent()
result = agent.call_skill("liantong_ai_query", question="联通安全管家有哪些功能？")
```

## 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| question | str | 是 | - | 要提问的问题内容 |
| app_name | str | 否 | "中国联通" | 应用名称 |

## 返回值

```python
{
    "success": True,
    "answer": "AI 回复内容",
    "question": "原始问题",
    "skill_id": "liantong_ai_query"
}
```

## 钩子事件

此 Skill 会触发以下钩子事件：

- `on_skill_start`: Skill 开始执行时
- `on_skill_complete`: Skill 执行完成时
- `on_skill_error`: Skill 执行失败时

### 注册钩子示例

```python
from phone_agent import register_hook

register_hook("on_skill_start", lambda skill_id, **kwargs: print(f"Skill 开始：{skill_id}"))
register_hook("on_skill_complete", lambda skill_id, result, **kwargs: print(f"Skill 完成：{result}"))
register_hook("on_skill_error", lambda skill_id, error, **kwargs: print(f"Skill 失败：{error}"))
```

## 执行流程

```
1. 加载项目配置 (config.json)
       ↓
2. 创建 PhoneAgent 实例
       ↓
3. 执行任务：打开 APP → 点击客服 → 发送问题 → 等待回复
       ↓
4. 返回 AI 回复内容
```
