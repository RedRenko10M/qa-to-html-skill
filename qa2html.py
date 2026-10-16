#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa2html - 将问题与AI回答转换并渲染为现代高质感HTML卡片/页面的工具与引擎
支持单轮/多轮问答、思考过程折叠展示、深浅色模式切换、一键复制、打印PDF友好、多种排版主题。
零外部依赖（纯Python标准库），开箱即用。
"""

import os
import sys
import json
import html
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# 确保在 Windows 控制台环境下输出 Unicode 字符不报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def simple_markdown_to_html(md_text: str) -> str:
    """
    轻量级内建 Markdown 转 HTML 解析器 (零依赖)。
    支持代码块、行内代码、标题、粗体、斜体、引用、列表、表格和超链接。
    """
    if not md_text:
        return ""

    # 1. 提取并保护代码块
    code_blocks = []
    def code_block_sub(match):
        lang = match.group(1) or ""
        code = match.group(2)
        idx = len(code_blocks)
        escaped_code = html.escape(code.strip())
        code_html = f'''<div class="code-container">
            <div class="code-header">
                <span class="code-lang">{html.escape(lang.strip()) if lang.strip() else 'code'}</span>
                <button class="btn-copy-code" onclick="copyCode(this)">复制</button>
            </div>
            <pre><code class="language-{html.escape(lang.strip())}">{escaped_code}</code></pre>
        </div>'''
        code_blocks.append(code_html)
        return f"\n__CODE_BLOCK_{idx}__\n"

    # 匹配 ```lang ... ```
    pattern_code = r"```([a-zA-Z0-9_\-\+\#]*)\n([\s\S]*?)```"
    text = re.sub(pattern_code, code_block_sub, md_text)

    # 2. 提取并保护行内代码
    inline_codes = []
    def inline_code_sub(match):
        code = match.group(1)
        idx = len(inline_codes)
        inline_codes.append(f'<code class="inline-code">{html.escape(code)}</code>')
        return f"__INLINE_CODE_{idx}__"

    text = re.sub(r"`([^`]+)`", inline_code_sub, text)

    lines = text.split("\n")
    html_lines = []
    in_list = False
    list_type = None  # 'ul' or 'ol'
    in_table = False
    table_rows = []

    def close_list():
        nonlocal in_list, list_type
        if in_list:
            html_lines.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def close_table():
        nonlocal in_table, table_rows
        if in_table:
            t_html = ['<div class="table-wrapper"><table>']
            if len(table_rows) > 0:
                # 假设第一行为表头
                t_html.append("<thead><tr>")
                for cell in table_rows[0]:
                    t_html.append(f"<th>{cell}</th>")
                t_html.append("</tr></thead>")
            if len(table_rows) > 1:
                t_html.append("<tbody>")
                for row in table_rows[1:]:
                    t_html.append("<tr>")
                    for cell in row:
                        t_html.append(f"<td>{cell}</td>")
                    t_html.append("</tr>")
                t_html.append("</tbody>")
            t_html.append("</table></div>")
            html_lines.append("\n".join(t_html))
            in_table = False
            table_rows = []

    for line in lines:
        stripped = line.strip()

        # 处理代码块占位符
        if stripped.startswith("__CODE_BLOCK_") and stripped.endswith("__"):
            close_list()
            close_table()
            html_lines.append(stripped)
            continue

        # 处理表格 (| col1 | col2 |)
        if stripped.startswith("|") and stripped.endswith("|"):
            close_list()
            # 过滤分隔线如 |---|---|
            if re.match(r"^\|[\s\:\-\|]+\|$", stripped):
                continue
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            # 处理单元格内的简单加粗等
            cells = [re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", c) for c in cells]
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(cells)
            continue
        else:
            close_table()

        # 标题处理
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            close_list()
            level = len(heading_match.group(1))
            htext = heading_match.group(2).strip()
            htext = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", htext)
            html_lines.append(f"<h{level}>{htext}</h{level}>")
            continue

        # 引用处理
        if line.startswith("> "):
            close_list()
            qtext = line[2:].strip()
            qtext = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", qtext)
            html_lines.append(f"<blockquote>{qtext}</blockquote>")
            continue

        # 无序列表 (- or *)
        ul_match = re.match(r"^[\*\-]\s+(.*)$", line)
        if ul_match:
            if not in_list or list_type != "ul":
                close_list()
                in_list = True
                list_type = "ul"
                html_lines.append("<ul>")
            item_text = ul_match.group(1).strip()
            item_text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", item_text)
            html_lines.append(f"<li>{item_text}</li>")
            continue

        # 有序列表 (1. )
        ol_match = re.match(r"^\d+\.\s+(.*)$", line)
        if ol_match:
            if not in_list or list_type != "ol":
                close_list()
                in_list = True
                list_type = "ol"
                html_lines.append("<ol>")
            item_text = ol_match.group(1).strip()
            item_text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", item_text)
            html_lines.append(f"<li>{item_text}</li>")
            continue

        close_list()

        # 空行
        if not stripped:
            continue

        # 普通段落
        ptext = line
        # 粗体 **text**
        ptext = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", ptext)
        # 斜体 *text*
        ptext = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", ptext)
        # 链接 [text](url)
        ptext = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', ptext)
        html_lines.append(f"<p>{ptext}</p>")

    close_list()
    close_table()

    res_html = "\n".join(html_lines)

    # 还原行内代码与代码块
    for idx, inc in enumerate(inline_codes):
        res_html = res_html.replace(f"__INLINE_CODE_{idx}__", inc)
    for idx, cb in enumerate(code_blocks):
        res_html = res_html.replace(f"__CODE_BLOCK_{idx}__", cb)

    return res_html


def build_qa_html(
    qa_list: List[Dict[str, Any]],
    title: str = "AI 问答记录",
    theme: str = "tech-card",
    model: str = "Gemini 4 Argon (Pro-grade Reasoning)",
    author: str = "User",
    created_at: Optional[str] = None
) -> str:
    """
    渲染问答列表为自包含的现代HTML。
    
    :param qa_list: 列表，每个元素形如:
        {
            "question": "用户的问题文本 (支持Markdown)",
            "answer": "AI回答的内容文本 (支持Markdown)",
            "thought": "可选：AI深度思考过程 (可折叠)",
            "model": "可选：指定单条模型名",
            "time": "可选：指定时间戳"
        }
    :param title: 页面大标题
    :param theme: 主题风格: 'tech-card' (默认现代极客卡片), 'chat-bubble' (对话气泡), 'share-card' (社交分享海报), 'document' (论文文档风格)
    :param model: 默认模型名称
    :param author: 用户名
    :param created_at: 创建时间，默认为当前时间
    """
    if not created_at:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 处理每个QA条目的HTML转换
    rendered_items = []
    for idx, item in enumerate(qa_list, 1):
        q_raw = item.get("question", "")
        a_raw = item.get("answer", "")
        t_raw = item.get("thought", "")
        m_name = item.get("model", model)
        item_time = item.get("time", created_at)

        q_html = simple_markdown_to_html(q_raw)
        a_html = simple_markdown_to_html(a_raw)
        t_html = simple_markdown_to_html(t_raw) if t_raw else ""

        rendered_items.append({
            "index": idx,
            "question_raw": q_raw,
            "question_html": q_html,
            "answer_raw": a_raw,
            "answer_html": a_html,
            "thought_raw": t_raw,
            "thought_html": t_html,
            "model": m_name,
            "time": item_time
        })

    # 根据主题生成特定主体内容
    content_html = ""
    if theme == "chat-bubble":
        content_html = _render_chat_bubble_theme(rendered_items, author)
    elif theme == "share-card":
        content_html = _render_share_card_theme(rendered_items, author, title)
    elif theme == "document":
        content_html = _render_document_theme(rendered_items, author, title)
    else: # 默认 tech-card
        content_html = _render_tech_card_theme(rendered_items, author, title)

    # 整合完整单文件HTML
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <!-- 引入字体与必要的高清图标/样式 -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        {_get_base_css(theme)}
    </style>
</head>
<body class="theme-{theme}">
    <div class="top-nav">
        <div class="brand">
            <span class="brand-icon">✨</span>
            <span class="brand-text">{html.escape(title)}</span>
        </div>
        <div class="nav-actions">
            <button class="nav-btn" onclick="toggleTheme()" title="切换深浅主题">
                <span id="theme-icon">🌙</span> <span id="theme-text">深色模式</span>
            </button>
            <button class="nav-btn" onclick="window.print()" title="打印或保存为PDF">
                🖨️ 导出PDF
            </button>
            <button class="nav-btn primary" onclick="copyAllQA()" title="复制全部问答文本">
                📋 复制纯文本
            </button>
        </div>
    </div>

    <main class="main-container">
        {content_html}
    </main>

    <footer class="page-footer">
        <p>由 <strong>qa2html</strong> 渲染生成 · 模型驱动：{html.escape(model)} · {created_at}</p>
    </footer>

    <script>
        {_get_client_js()}
    </script>
</body>
</html>'''

    return full_html


def _render_tech_card_theme(items: List[Dict[str, Any]], author: str, title: str) -> str:
    """现代科技极客卡片风格"""
    cards = []
    for item in items:
        thought_section = ""
        if item["thought_html"]:
            thought_section = f'''
            <details class="thought-container">
                <summary class="thought-summary">
                    <span class="thought-pill">💭 深度思考过程 (点击展开/折叠)</span>
                    <span class="thought-hint">Pro Deep Reasoning</span>
                </summary>
                <div class="thought-content">
                    {item["thought_html"]}
                </div>
            </details>
            '''

        card = f'''
        <article class="qa-card" id="qa-{item['index']}">
            <div class="card-header">
                <div class="header-badge-group">
                    <span class="badge index-badge">#{item['index']}</span>
                    <span class="badge model-badge">{html.escape(item['model'])}</span>
                </div>
                <div class="card-time">{html.escape(item['time'])}</div>
            </div>

            <!-- 问题区 -->
            <div class="section-box question-box">
                <div class="role-badge user-badge">
                    <span class="role-avatar">👤</span>
                    <span class="role-name">{html.escape(author)}</span>
                </div>
                <div class="markdown-body question-body">
                    {item['question_html']}
                </div>
            </div>

            <!-- 思考过程区 (若有) -->
            {thought_section}

            <!-- 回答区 -->
            <div class="section-box answer-box">
                <div class="role-header">
                    <div class="role-badge ai-badge">
                        <span class="role-avatar">🤖</span>
                        <span class="role-name">AI 解答</span>
                    </div>
                    <div class="answer-actions">
                        <button class="btn-action" onclick="copyAnswerText({item['index']})">复制回答</button>
                    </div>
                </div>
                <div class="markdown-body answer-body" id="answer-content-{item['index']}">
                    {item['answer_html']}
                </div>
            </div>
        </article>
        '''
        cards.append(card)
    return "\n".join(cards)


def _render_chat_bubble_theme(items: List[Dict[str, Any]], author: str) -> str:
    """对话气泡风格"""
    bubbles = []
    for item in items:
        thought_section = ""
        if item["thought_html"]:
            thought_section = f'''
            <details class="thought-bubble-details">
                <summary class="thought-summary">💭 深度思考过程</summary>
                <div class="thought-content">{item["thought_html"]}</div>
            </details>
            '''

        bubble = f'''
        <div class="chat-turn" id="qa-{item['index']}">
            <!-- 用户气泡 (靠右/高亮) -->
            <div class="bubble-row user-row">
                <div class="bubble user-bubble">
                    <div class="bubble-meta">
                        <span class="bubble-sender">{html.escape(author)}</span>
                        <span class="bubble-time">{html.escape(item['time'])}</span>
                    </div>
                    <div class="markdown-body">
                        {item['question_html']}
                    </div>
                </div>
                <div class="avatar-col user-avatar-col">
                    <div class="bubble-avatar user-bg">🧑</div>
                </div>
            </div>

            <!-- AI 气泡 (靠左/宽阔) -->
            <div class="bubble-row ai-row">
                <div class="avatar-col ai-avatar-col">
                    <div class="bubble-avatar ai-bg">✨</div>
                </div>
                <div class="bubble ai-bubble">
                    <div class="bubble-meta">
                        <span class="bubble-sender ai-text">{html.escape(item['model'])}</span>
                        <div class="bubble-actions">
                            <button class="btn-micro" onclick="copyAnswerText({item['index']})">复制</button>
                        </div>
                    </div>
                    {thought_section}
                    <div class="markdown-body" id="answer-content-{item['index']}">
                        {item['answer_html']}
                    </div>
                </div>
            </div>
        </div>
        '''
        bubbles.append(bubble)
    return f'<div class="chat-container">{"".join(bubbles)}</div>'


def _render_share_card_theme(items: List[Dict[str, Any]], author: str, title: str) -> str:
    """社交分享 / 海报卡片风格 (带渐变条与引用装饰，极适宜截图)"""
    cards = []
    for item in items:
        card = f'''
        <div class="share-poster-card" id="qa-{item['index']}">
            <div class="poster-decor-bar"></div>
            <div class="poster-inner">
                <div class="poster-header">
                    <div class="poster-tag">💡 精选问答 · Q&A</div>
                    <div class="poster-model">{html.escape(item['model'])}</div>
                </div>

                <div class="poster-question">
                    <div class="quote-mark">“</div>
                    <div class="markdown-body question-body">
                        {item['question_html']}
                    </div>
                </div>

                <div class="poster-divider">
                    <span class="divider-icon">✦ ✦ ✦</span>
                </div>

                <div class="poster-answer">
                    <div class="answer-badge-inline">💡 回答摘要 / 核心解析</div>
                    <div class="markdown-body answer-body" id="answer-content-{item['index']}">
                        {item['answer_html']}
                    </div>
                </div>

                <div class="poster-footer">
                    <div class="poster-meta">
                        <span>提问者: {html.escape(author)}</span> · <span>{html.escape(item['time'])}</span>
                    </div>
                    <button class="btn-action" onclick="copyAnswerText({item['index']})">复制文本</button>
                </div>
            </div>
        </div>
        '''
        cards.append(card)
    return "\n".join(cards)


def _render_document_theme(items: List[Dict[str, Any]], author: str, title: str) -> str:
    """文章与知识文档风格"""
    docs = []
    for item in items:
        thought_section = ""
        if item["thought_html"]:
            thought_section = f'''
            <div class="doc-thought-callout">
                <div class="doc-thought-title">🧠 思考与推理逻辑</div>
                <div class="doc-thought-body">{item["thought_html"]}</div>
            </div>
            '''

        doc = f'''
        <section class="doc-section" id="qa-{item['index']}">
            <h2 class="doc-h2"><span class="doc-sec-num">Q{item['index']}.</span> 问题陈述</h2>
            <div class="doc-quote-block">
                {item['question_html']}
            </div>

            {thought_section}

            <h2 class="doc-h2"><span class="doc-sec-num">A{item['index']}.</span> 详细解答与分析</h2>
            <div class="doc-body markdown-body" id="answer-content-{item['index']}">
                {item['answer_html']}
            </div>
            
            <div class="doc-meta-bar">
                <span>责任模型: {html.escape(item['model'])}</span>
                <span>记录时间: {html.escape(item['time'])}</span>
                <button class="btn-micro" onclick="copyAnswerText({item['index']})">复制此节回答</button>
            </div>
            <hr class="doc-hr"/>
        </section>
        '''
        docs.append(doc)
    return f'''
    <div class="document-container">
        <header class="doc-header">
            <h1 class="doc-title">{html.escape(title)}</h1>
            <p class="doc-subtitle">生成者: {html.escape(author)} · 共 {len(items)} 个问答片段</p>
        </header>
        {"".join(docs)}
    </div>
    '''


def _get_base_css(theme: str) -> str:
    """生成内嵌现代化CSS，包含CSS变量、排版、响应式设计与打印适配"""
    return '''
        :root {
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            --font-mono: 'Fira Code', Consolas, Monaco, "Courier New", monospace;
            
            /* 浅色模式变量 */
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --bg-card-subtle: #f1f5f9;
            --border-color: #e2e8f0;
            --border-hover: #cbd5e1;
            
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            
            --brand-primary: #3b82f6;
            --brand-gradient: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            
            --user-badge-bg: #eff6ff;
            --user-badge-text: #1d4ed8;
            --ai-badge-bg: #f5f3ff;
            --ai-badge-text: #6d28d9;
            
            --code-bg: #1e293b;
            --code-text: #f8fafc;
            --code-header-bg: #0f172a;
            
            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --card-shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
            
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            --radius-full: 9999px;
        }

        html[data-theme="dark"] {
            /* 深色模式变量 */
            --bg-page: #0b0f19;
            --bg-card: #131a2a;
            --bg-card-subtle: #1a2338;
            --border-color: #232e47;
            --border-hover: #334155;
            
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            
            --brand-primary: #60a5fa;
            --brand-gradient: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
            
            --user-badge-bg: #1e293b;
            --user-badge-text: #93c5fd;
            --ai-badge-bg: #2e1065;
            --ai-badge-text: #c4b5fd;
            
            --code-bg: #070a12;
            --code-text: #f8fafc;
            --code-header-bg: #030509;
            
            --card-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            --card-shadow-hover: 0 10px 20px rgba(0, 0, 0, 0.45);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-sans);
            background-color: var(--bg-page);
            color: var(--text-primary);
            line-height: 1.65;
            transition: background-color 0.25s ease, color 0.25s ease;
            -webkit-font-smoothing: antialiased;
        }

        /* 顶部导航与操作栏 */
        .top-nav {
            position: sticky;
            top: 0;
            z-index: 50;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 24px;
            background: rgba(var(--bg-card), 0.85);
            background-color: var(--bg-card);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border-color);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 1.1rem;
            color: var(--text-primary);
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .nav-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            border-radius: var(--radius-md);
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-secondary);
            transition: all 0.2s ease;
        }

        .nav-btn:hover {
            border-color: var(--border-hover);
            color: var(--text-primary);
            background: var(--bg-card-subtle);
        }

        .nav-btn.primary {
            background: var(--brand-primary);
            color: #ffffff;
            border-color: var(--brand-primary);
        }

        .nav-btn.primary:hover {
            opacity: 0.9;
        }

        /* 主体布局 */
        .main-container {
            max-width: 900px;
            margin: 32px auto;
            padding: 0 20px;
        }

        /* 卡片基础 (tech-card) */
        .qa-card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
            margin-bottom: 28px;
            box-shadow: var(--card-shadow);
            transition: box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .qa-card:hover {
            box-shadow: var(--card-shadow-hover);
            border-color: var(--border-hover);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }

        .header-badge-group {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: var(--radius-full);
            letter-spacing: 0.02em;
        }

        .index-badge {
            background: var(--bg-card-subtle);
            color: var(--text-secondary);
        }

        .model-badge {
            background: var(--ai-badge-bg);
            color: var(--ai-badge-text);
            border: 1px solid rgba(139, 92, 246, 0.2);
        }

        .card-time {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        /* 问题区 */
        .section-box {
            margin-bottom: 18px;
        }

        .question-box {
            background: var(--bg-card-subtle);
            padding: 16px 20px;
            border-radius: var(--radius-md);
            border-left: 4px solid var(--brand-primary);
        }

        .role-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .user-badge {
            color: var(--user-badge-text);
        }

        .ai-badge {
            color: var(--ai-badge-text);
        }

        .role-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .btn-action {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.8rem;
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-action:hover {
            color: var(--text-primary);
            border-color: var(--border-hover);
            background: var(--bg-card-subtle);
        }

        .btn-micro {
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            cursor: pointer;
        }
        .btn-micro:hover {
            background: var(--bg-card-subtle);
            color: var(--text-primary);
        }

        /* 深度思考过程折叠块 */
        .thought-container {
            background: var(--bg-card-subtle);
            border: 1px dashed var(--border-color);
            border-radius: var(--radius-md);
            padding: 10px 14px;
            margin: 16px 0;
            font-size: 0.9rem;
        }

        .thought-summary {
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            font-weight: 600;
            color: var(--text-secondary);
            user-select: none;
        }

        .thought-summary:hover {
            color: var(--text-primary);
        }

        .thought-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .thought-hint {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }

        .thought-content {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.875rem;
            line-height: 1.6;
        }

        /* Markdown 样式渲染 */
        .markdown-body {
            font-size: 0.96rem;
            color: var(--text-primary);
        }

        .markdown-body p {
            margin-bottom: 12px;
        }
        .markdown-body p:last-child {
            margin-bottom: 0;
        }

        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
            margin: 18px 0 10px;
            font-weight: 700;
            line-height: 1.35;
        }

        .markdown-body h1 { font-size: 1.4rem; }
        .markdown-body h2 { font-size: 1.25rem; }
        .markdown-body h3 { font-size: 1.1rem; }

        .markdown-body ul, .markdown-body ol {
            margin: 10px 0 14px 22px;
        }

        .markdown-body li {
            margin-bottom: 6px;
        }

        .markdown-body blockquote {
            border-left: 4px solid var(--border-hover);
            padding: 8px 16px;
            margin: 12px 0;
            color: var(--text-secondary);
            background: var(--bg-card-subtle);
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
        }

        .inline-code {
            font-family: var(--font-mono);
            font-size: 0.88em;
            background: var(--bg-card-subtle);
            color: #e11d48;
            padding: 2px 6px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
        }

        html[data-theme="dark"] .inline-code {
            color: #fb7185;
        }

        /* 代码块容器 */
        .code-container {
            margin: 14px 0;
            border-radius: var(--radius-md);
            overflow: hidden;
            background: var(--code-bg);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 14px;
            background: var(--code-header-bg);
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .code-lang {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            text-transform: uppercase;
            color: #94a3b8;
            font-weight: 600;
        }

        .btn-copy-code {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #cbd5e1;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-copy-code:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }

        .code-container pre {
            margin: 0;
            padding: 14px 16px;
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 0.88rem;
            color: var(--code-text);
            line-height: 1.5;
        }

        /* 表格样式 */
        .table-wrapper {
            overflow-x: auto;
            margin: 14px 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }

        table th, table td {
            padding: 10px 14px;
            text-align: left;
            border: 1px solid var(--border-color);
        }

        table th {
            background: var(--bg-card-subtle);
            font-weight: 600;
        }

        table tr:nth-child(even) {
            background: rgba(0, 0, 0, 0.015);
        }

        /* 对话气泡风格扩展 (chat-bubble) */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .bubble-row {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }

        .user-row {
            justify-content: flex-end;
        }

        .ai-row {
            justify-content: flex-start;
        }

        .bubble {
            max-width: 82%;
            padding: 16px 20px;
            border-radius: 18px;
            box-shadow: var(--card-shadow);
        }

        .user-bubble {
            background: var(--brand-primary);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .user-bubble .markdown-body,
        .user-bubble .bubble-sender {
            color: #ffffff;
        }

        .user-bubble .bubble-time {
            color: rgba(255, 255, 255, 0.7);
        }

        .ai-bubble {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: 4px;
        }

        .bubble-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .bubble-avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            box-shadow: var(--card-shadow);
        }

        .user-bg { background: var(--user-badge-bg); color: var(--user-badge-text); }
        .ai-bg { background: var(--ai-badge-bg); color: var(--ai-badge-text); }

        /* 分享海报卡片 (share-card) */
        .share-poster-card {
            background: var(--bg-card);
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow-hover);
            overflow: hidden;
            margin-bottom: 32px;
        }

        .poster-decor-bar {
            height: 8px;
            background: var(--brand-gradient);
        }

        .poster-inner {
            padding: 30px;
        }

        .poster-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .poster-tag {
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--brand-primary);
            letter-spacing: 0.05em;
        }

        .poster-question {
            position: relative;
            background: var(--bg-card-subtle);
            padding: 20px 24px;
            border-radius: var(--radius-md);
            margin-bottom: 24px;
            font-size: 1.05rem;
            font-weight: 500;
        }

        .quote-mark {
            position: absolute;
            top: 2px;
            left: 8px;
            font-size: 2.5rem;
            color: var(--border-hover);
            line-height: 1;
            user-select: none;
        }

        .poster-divider {
            text-align: center;
            margin: 20px 0;
            color: var(--brand-primary);
            font-size: 0.8rem;
            opacity: 0.6;
        }

        .answer-badge-inline {
            font-weight: 700;
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }

        .poster-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 28px;
            padding-top: 16px;
            border-top: 1px dashed var(--border-color);
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        /* 文档风格 (document) */
        .document-container {
            background: var(--bg-card);
            padding: 40px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-color);
            box-shadow: var(--card-shadow);
        }

        .doc-header {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--border-color);
        }

        .doc-title {
            font-size: 1.8rem;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .doc-subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .doc-h2 {
            font-size: 1.2rem;
            font-weight: 700;
            margin: 24px 0 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .doc-sec-num {
            color: var(--brand-primary);
        }

        .doc-quote-block {
            background: var(--bg-card-subtle);
            border-left: 4px solid var(--brand-primary);
            padding: 14px 18px;
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            margin-bottom: 20px;
        }

        .doc-meta-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 20px;
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .doc-hr {
            margin: 32px 0;
            border: 0;
            border-top: 1px solid var(--border-color);
        }

        /* 页面底部 */
        .page-footer {
            text-align: center;
            padding: 30px 20px;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            margin-top: 40px;
        }

        /* 打印适配样式 (@media print) */
        @media print {
            .top-nav, .nav-actions, .btn-action, .btn-micro, .btn-copy-code, .page-footer {
                display: none !important;
            }
            body {
                background: #ffffff !important;
                color: #000000 !important;
            }
            .qa-card, .share-poster-card, .document-container, .bubble {
                box-shadow: none !important;
                border: 1px solid #ccc !important;
                break-inside: avoid;
            }
            .main-container {
                max-width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            details {
                open: true !important;
            }
        }

        /* 移动端响应式 */
        @media (max-width: 640px) {
            .top-nav {
                padding: 10px 14px;
            }
            .brand-text {
                font-size: 0.95rem;
            }
            .nav-btn span:not(#theme-icon) {
                display: none;
            }
            .main-container {
                padding: 0 12px;
                margin: 16px auto;
            }
            .qa-card, .poster-inner, .document-container {
                padding: 16px;
            }
            .bubble {
                max-width: 90%;
            }
        }
    '''


def _get_client_js() -> str:
    """生成前端交互JS (主题切换、代码复制、全文复制)"""
    return '''
        // 主题切换控制
        function toggleTheme() {
            const html = document.documentElement;
            const current = html.getAttribute('data-theme') || 'light';
            const next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);
            localStorage.setItem('qa_theme_pref', next);
            updateThemeUI(next);
        }

        function updateThemeUI(theme) {
            const icon = document.getElementById('theme-icon');
            const text = document.getElementById('theme-text');
            if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
            if (text) text.textContent = theme === 'dark' ? '浅色模式' : '深色模式';
        }

        // 初始化读取主题首选项
        (function initTheme() {
            const saved = localStorage.getItem('qa_theme_pref');
            if (saved) {
                document.documentElement.setAttribute('data-theme', saved);
                updateThemeUI(saved);
            } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                updateThemeUI('dark');
            }
        })();

        // 复制单个代码块
        function copyCode(btn) {
            const container = btn.closest('.code-container');
            const codeEl = container.querySelector('code');
            if (!codeEl) return;
            const text = codeEl.innerText;
            navigator.clipboard.writeText(text).then(() => {
                const orig = btn.textContent;
                btn.textContent = '已复制!';
                btn.style.color = '#34d399';
                setTimeout(() => {
                    btn.textContent = orig;
                    btn.style.color = '';
                }, 1800);
            }).catch(err => {
                console.error('复制失败', err);
            });
        }

        // 复制单条回答文本
        function copyAnswerText(index) {
            const target = document.getElementById('answer-content-' + index);
            if (!target) return;
            navigator.clipboard.writeText(target.innerText).then(() => {
                alert('回答文本已成功复制到剪贴板！');
            }).catch(err => {
                console.error(err);
            });
        }

        // 复制全文
        function copyAllQA() {
            const main = document.querySelector('.main-container');
            if (!main) return;
            navigator.clipboard.writeText(main.innerText).then(() => {
                alert('页面全部问答内容已复制到剪贴板！');
            }).catch(err => {
                console.error(err);
            });
        }
    '''


def main():
    parser = argparse.ArgumentParser(
        description="qa2html - 将问题与AI回答渲染为高质感现代HTML文件"
    )
    parser.add_argument("-q", "--question", help="用户提出的问题文本 (支持Markdown)")
    parser.add_argument("-a", "--answer", help="AI给出的回答文本 (支持Markdown)")
    parser.add_argument("-t", "--thought", help="可选：AI的深度思考过程 (可折叠展示)")
    parser.add_argument("-f", "--file", help="从JSON文件读取问答数据 (格式详见README)")
    parser.add_argument("-o", "--output", default="qa_output.html", help="输出HTML文件路径 (默认: qa_output.html)")
    parser.add_argument("--title", default="AI 问答记录", help="页面大标题 (默认: AI 问答记录)")
    parser.add_argument("--theme", choices=["tech-card", "chat-bubble", "share-card", "document"], default="tech-card", help="排版主题风格")
    parser.add_argument("--model", default="Gemini 4 Argon (Pro-grade Reasoning)", help="模型名称标注")
    parser.add_argument("--author", default="User", help="用户名称")

    args = parser.parse_args()

    qa_list = []

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[错误] 输入文件不存在: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, list):
                qa_list = data
            elif isinstance(data, dict):
                if "items" in data:
                    qa_list = data["items"]
                    if "title" in data and not args.title:
                        args.title = data["title"]
                    if "theme" in data and args.theme == "tech-card":
                        args.theme = data["theme"]
                else:
                    qa_list = [data]
    elif args.question or args.answer:
        qa_list = [{
            "question": args.question or "未提供问题",
            "answer": args.answer or "未提供回答",
            "thought": args.thought or "",
            "model": args.model
        }]
    else:
        # 如果未传入参数，提示帮助
        parser.print_help()
        print("\n示例: python qa2html.py -q '什么是量化投资？' -a '量化投资是指...' -o demo.html")
        sys.exit(0)

    html_result = build_qa_html(
        qa_list=qa_list,
        title=args.title,
        theme=args.theme,
        model=args.model,
        author=args.author
    )

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write(html_result)

    print(f"✨ 成功生成 HTML 页面: {out_path}")
    print(f"🔗 本地预览路径: file:///{out_path.as_posix()}")


if __name__ == "__main__":
    main()
