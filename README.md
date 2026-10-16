# qa-to-html: AI 问答转现代高质感 HTML 渲染器

用于将用户问题（Question）与 AI 解答（Answer），以及可选的深度思考过程（Chain-of-Thought / Deep Reasoning）快速生成为高质感、现代响应式的自包含单文件 HTML 网页。

## 🌟 核心特性

- **零外部依赖**：基于 Python 3 标准库开发，开箱即用，无需执行 `pip install`。
- **自包含单文件**：生成的 HTML 包含所有 CSS、JS 与内嵌 SVG 样式，断网亦可完美渲染并分享。
- **深度思考过程支持**：完美适配 **Gemini 4 Argon / Pro-grade Deep Reasoning** 等推理模型的思考过程（`<thought>` 折叠展示与回溯）。
- **四款预设主题**：
  1. `tech-card`（默认）：现代极客卡片风格，具备状态徽章、模型标注、阴影浮动。
  2. `chat-bubble`：即时对话气泡风格，左右对齐，拟真聊天窗口。
  3. `share-card`：社交分享/海报卡片风格，带渐变彩条与引用标，适宜截图发圈。
  4. `document`：专业文档/报告风格，章节分明，适宜沉浸式长篇阅读。
- **丰富交互功能**：
  - 🌓 深色 / 浅色模式一键切换（支持记忆与系统偏好自动检测）。
  - 📋 代码块一键复制 & 回答内容一键复制 & 全文纯文本复制。
  - 🖨️ 打印与导出 PDF 专属优化（`@media print` 自动隐藏冗余操作按钮与导航栏）。

---

## 🚀 快速使用

### 1. 命令行快速生成单个问答
```bash
python qa2html.py -q "如何用Python实现单例模式？" -a "可以使用元类或模块实现：\n\n```python\nclass Singleton(type):\n    _instances = {}\n```" -o singleton.html
```

### 2. 带思考过程与指定主题
```bash
python qa2html.py \
  -q "解析两数之和算法的最优解法" \
  -a "使用哈希表可以将时间复杂度降为 O(n)..." \
  -t "首先分析暴力遍历 O(n^2)，然后借助字典记录 target - num 实现单次遍历查找..." \
  --theme tech-card \
  --model "Gemini 4 Argon" \
  -o two_sum.html
```

### 3. 从 JSON 批量文件读取
```bash
python qa2html.py -f examples/demo_tech.json --theme share-card -o share_view.html
```

#### JSON 输入格式示例 (`qa.json`)
```json
{
  "title": "深度对话记录",
  "theme": "tech-card",
  "items": [
    {
      "question": "### 什么是思维链？",
      "thought": "1. 拆解问题核心概念...",
      "answer": "思维链是指模型在生成答案前生成的中间推理步骤...",
      "model": "Gemini 4 Argon (Pro-grade Reasoning)",
      "time": "2026-10-16 23:30:00"
    }
  ]
}
```

---

## 📂 项目结构

```text
qa-to-html/
├── README.md               # 项目使用说明
├── qa2html.py              # 核心转换引擎与CLI工具
├── examples/               # 样例数据与生成预览
│   ├── demo_tech.json      # 示例JSON数据
│   ├── demo_tech.html      # 科技卡片风格预览
│   ├── demo_chat.html      # 聊天气泡风格预览
│   ├── demo_share.html     # 分享海报风格预览
│   └── demo_doc.html       # 知识文档风格预览
└── tests/
    └── test_qa2html.py     # 单元测试
```
