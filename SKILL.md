---
name: qa-to-html
description: 用于将用户提问与AI回答（含深度思考过程、代码块、表格等）制作/格式化为现代高质感HTML卡片或网页。当用户要求导出问答为网页、制作Q&A分享卡片、或将当前对话/特定问答记录保存为美观HTML时使用。
---

# Q&A to HTML Skill

本 Skill 用于将「用户问题（Question）」与「AI回答（Answer）」以及「深度思考链（CoT / Thought）」转换为现代、自包含、高质感的单个 HTML 文件。

## 何时使用本 Skill

- 用户要求将某个问题和回答导出为网页或 HTML 样式文件。
- 用户要求制作问答分享卡片（如适合截图分享的小红书/朋友圈/知乎卡片）。
- 用户需要将技术问答、代码解析或推理过程归档为离线可读、排版精美、支持深浅色切换的 HTML。

---

## 预设主题风格 (Theme)

| 主题名称 | 风格说明 | 推荐适用场景 |
| :--- | :--- | :--- |
| `tech-card` *(默认)* | 现代极客卡片，带状态徽章、模型标注、阴影悬浮与折叠思考区 | 代码解析、算法解答、架构方案设计 |
| `chat-bubble` | 经典聊天气泡，左右分栏，模拟原生对话界面 | 交互式多轮对话、问答回放、聊天记录展示 |
| `share-card` | 社交分享海报，顶栏带渐变装饰条、大号引号装饰，适宜截图 | 精粹知识分享、观点金句、移动端截图转发 |
| `document` | 专业文档/报告，章节编号分明，沉浸式阅读排版 | 深度长文报告、学术概念科普、方案说明书 |

---

## 执行步骤与调用方法

### 方法一：调用预置脚本批量/复杂生成 (推荐)

在技能脚本目录中预置了零依赖渲染引擎：[qa2html.py](./scripts/qa2html.py)。

#### 1. 准备 JSON 数据文件 (推荐处理长文本或包含特殊字符时使用)
在工作区或临时目录创建 `qa_data.json`：
```json
{
  "title": "问题标题或主题",
  "theme": "tech-card",
  "items": [
    {
      "question": "用户的原始问题 (支持完整Markdown语法与代码块)",
      "thought": "可选：模型深度思考推导过程 (支持Markdown)",
      "answer": "AI的正式回答内容 (支持完整Markdown语法、表格与代码块)",
      "model": "Gemini 4 Argon (Pro-grade Reasoning)",
      "time": "2026-10-16 23:30:00"
    }
  ]
}
```

#### 2. 执行渲染命令
```bash
python .agent/skills/qa-to-html/scripts/qa2html.py -f qa_data.json -o output.html
```

#### 3. 命令行单条快速生成 (适用于短文本)
```bash
python .agent/skills/qa-to-html/scripts/qa2html.py \
  -q "用户提问" \
  -a "AI回答" \
  -t "思考过程" \
  --theme tech-card \
  -o result.html
```

---

## 交付规范

生成完成后，**必须**在向用户回复时提供生成的本地 HTML 绝对路径的可点击链接，格式如下：
- [点击预览生成的HTML页面](file:///d:/ai_project/.../output.html)
告知用户可以直接双击在浏览器中打开，支持深浅色切换、复制代码和一键打印/导出PDF。
