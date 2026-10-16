#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
import sys
from pathlib import Path

# 添加上级路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from qa2html import simple_markdown_to_html, build_qa_html

class TestQa2Html(unittest.TestCase):
    def test_markdown_headers_and_code(self):
        md = "### 测试标题\n这里是正文段落。\n```python\nprint('hello world')\n```"
        html = simple_markdown_to_html(md)
        self.assertIn("<h3>测试标题</h3>", html)
        self.assertIn("<p>这里是正文段落。</p>", html)
        self.assertIn('class="language-python"', html)
        self.assertIn("print(&#x27;hello world&#x27;)", html)

    def test_markdown_tables(self):
        md = "| 列A | 列B |\n|---|---|\n| 值1 | 值2 |"
        html = simple_markdown_to_html(md)
        self.assertIn("<table>", html)
        self.assertIn("<th>列A</th>", html)
        self.assertIn("<td>值1</td>", html)

    def test_build_qa_html_themes(self):
        qa_data = [{
            "question": "什么是量子纠缠？",
            "answer": "量子纠缠是量子力学中的基本现象...",
            "thought": "正在检索量子力学标准模型与纠缠态定义...",
            "model": "Gemini 4 Argon"
        }]
        for theme in ["tech-card", "chat-bubble", "share-card", "document"]:
            res = build_qa_html(qa_data, title=f"测试-{theme}", theme=theme)
            self.assertIn(f"测试-{theme}", res)
            self.assertIn("Gemini 4 Argon", res)
            self.assertIn("量子纠缠", res)

if __name__ == "__main__":
    unittest.main()
