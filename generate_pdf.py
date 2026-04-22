#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Agent 白皮书 PDF 生成脚本
将 17 个 Markdown 文件合并渲染为带水印的 PDF
"""

import os
import sys
import re
import markdown
from pathlib import Path

# 设置 weasyprint 需要的库路径（macOS Homebrew）
os.environ.setdefault('DYLD_LIBRARY_PATH', '/opt/homebrew/lib')

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


def get_md_files(directory):
    """按编号顺序获取所有 Markdown 文件"""
    md_files = sorted(
        [f for f in os.listdir(directory) if f.endswith('.md') and f != 'generate_pdf.py'],
        key=lambda x: int(re.match(r'(\d+)', x).group(1)) if re.match(r'(\d+)', x) else 999
    )
    return md_files


def read_and_combine_md_files(directory, md_files):
    """读取并合并所有 Markdown 文件，在每个文件之间添加分页符"""
    combined_md = []
    for i, md_file in enumerate(md_files):
        filepath = os.path.join(directory, md_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 每章之间添加分页标记（通过 div 实现）
        if i > 0:
            combined_md.append('\n\n<div class="page-break"></div>\n\n')
        
        combined_md.append(content)
    
    return '\n'.join(combined_md)


def render_markdown_to_html(md_content):
    """将 Markdown 渲染为 HTML，启用各种扩展"""
    extensions = [
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.toc',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
        'markdown.extensions.smarty',
        'pymdownx.superfences',
        'pymdownx.highlight',
        'pymdownx.inlinehilite',
        'pymdownx.blocks.admonition',
        'pymdownx.details',
        'pymdownx.tabbed',
        'pymdownx.tasklist',
        'pymdownx.keys',
    ]
    
    md = markdown.Markdown(extensions=extensions, extension_configs={
        'markdown.extensions.toc': {
            'title': '目录',
            'permalink': False,
        },
        'pymdownx.highlight': {
            'auto_title': True,
            'linenums': False,
        },
        'pymdownx.superfences': {
            'custom_fences': [
                {
                    'name': 'mermaid',
                    'class': 'mermaid',
                    'format': lambda source, language, css_class, options, md, **kwargs: f'<pre class="{css_class}"><code>{source}</code></pre>'
                }
            ]
        },
    })
    
    html_body = md.convert(md_content)
    return html_body


def build_css():
    """构建完整的 CSS 样式"""
    css = '''
@page {
    size: A4;
    margin: 2.5cm 2cm 2.5cm 2cm;

    @top-center {
        content: "Hermes Agent 白皮书 · 鲲鹏Talk";
        font-size: 9px;
        color: #888;
        border-bottom: 0.5px solid #ddd;
        padding-bottom: 5px;
    }

    @bottom-center {
        content: counter(page);
        font-size: 10px;
        color: #666;
    }
}

@page cover {
    size: A4;
    margin: 0;
    @top-center { content: none; }
    @bottom-center { content: none; }
}

@page :first {
    @top-center { content: none; }
    @bottom-center { content: none; }
}

/* 全局水印 */
body::before {
    content: "鲲鹏Talk";
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-45deg);
    font-size: 120px;
    color: rgba(0, 0, 0, 0.06);
    z-index: 9999;
    pointer-events: none;
    white-space: nowrap;
    font-family: "Heiti SC", "Hiragino Sans GB", "Songti SC", "Arial Unicode MS", sans-serif;
}

/* 基础排版 */
body {
    font-family: "Heiti SC", "Hiragino Sans GB", "Songti SC", "Arial Unicode MS", sans-serif;
    font-size: 12px;
    line-height: 1.8;
    color: #333;
    text-align: justify;
}

/* 封面样式 */
.cover-page {
    page: cover;
    page-break-after: always;
    margin: 0;
    padding: 0;
    width: 210mm;
    height: 297mm;
    text-align: center;
}

.cover-page img {
    width: 210mm;
    height: 297mm;
    display: block;
}

/* 旧封面样式兼容 */
.cover-title {
    text-align: center;
    margin-top: 30%;
}

.cover-title h1 {
    font-size: 32px;
    color: #1a1a1a;
    margin-bottom: 20px;
    border: none;
}

.cover-author {
    text-align: center;
    font-size: 18px;
    color: #666;
    margin-top: 40px;
}

/* 分页 */
.page-break {
    page-break-before: always;
}

/* 标题样式 */
h1 {
    font-size: 24px;
    font-weight: bold;
    color: #1a1a1a;
    margin-top: 0;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e74c3c;
    page-break-after: avoid;
}

h2 {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
    margin-top: 30px;
    margin-bottom: 15px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ddd;
    page-break-after: avoid;
}

h3 {
    font-size: 15px;
    font-weight: bold;
    color: #34495e;
    margin-top: 25px;
    margin-bottom: 12px;
    page-break-after: avoid;
}

h4 {
    font-size: 13px;
    font-weight: bold;
    color: #555;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

/* 段落 */
p {
    margin: 10px 0;
    text-indent: 0;
}

/* 粗体 */
strong {
    font-weight: bold;
    color: #222;
}

/* 链接 */
a {
    color: #2980b9;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* 代码块 */
pre {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-left: 4px solid #6c757d;
    border-radius: 4px;
    padding: 12px 15px;
    margin: 15px 0;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: "SF Mono", "Fira Code", "Consolas", "Monaco", "Courier New", "Heiti SC", "Hiragino Sans GB", monospace;
    font-size: 10px;
    line-height: 1.5;
}

code {
    font-family: "SF Mono", "Fira Code", "Consolas", "Monaco", "Courier New", "Heiti SC", "Hiragino Sans GB", monospace;
    font-size: 10.5px;
    background-color: #f1f3f4;
    padding: 2px 5px;
    border-radius: 3px;
    color: #c7254e;
}

pre code {
    background-color: transparent;
    padding: 0;
    border-radius: 0;
    color: #333;
}

/* 表格 */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 11px;
    page-break-inside: avoid;
}

th {
    background-color: #2c3e50;
    color: white;
    font-weight: bold;
    padding: 10px 12px;
    text-align: left;
    border: 1px solid #2c3e50;
}

td {
    padding: 8px 12px;
    border: 1px solid #ddd;
    vertical-align: top;
}

tr:nth-child(even) {
    background-color: #f8f9fa;
}

tr:hover {
    background-color: #f1f3f4;
}

/* 引用块 / 提示框 */
blockquote {
    margin: 15px 0;
    padding: 12px 15px 12px 20px;
    border-left: 4px solid #3498db;
    background-color: #f0f7ff;
    color: #2c3e50;
    font-size: 11.5px;
}

blockquote p {
    margin: 5px 0;
}

blockquote p:first-child {
    margin-top: 0;
}

blockquote p:last-child {
    margin-bottom: 0;
}

/* 不同提示类型 */
blockquote:has(strong:contains("Tips")),
blockquote:has(p:first-child strong:contains("Tips")),
blockquote:has(p:first-child:contains("Tips")) {
    border-left-color: #3498db;
    background-color: #f0f7ff;
}

blockquote:has(strong:contains("注意")),
blockquote:has(p:first-child strong:contains("注意")),
blockquote:has(p:first-child:contains("注意")) {
    border-left-color: #e67e22;
    background-color: #fff8f0;
}

blockquote:has(strong:contains("警告")),
blockquote:has(p:first-child strong:contains("警告")),
blockquote:has(p:first-child:contains("警告")) {
    border-left-color: #e74c3c;
    background-color: #fdf2f2;
}

blockquote:has(strong:contains("常见问题")),
blockquote:has(p:first-child strong:contains("常见问题")),
blockquote:has(p:first-child:contains("常见问题")) {
    border-left-color: #27ae60;
    background-color: #f0fff4;
}

/* 列表 */
ul, ol {
    margin: 10px 0;
    padding-left: 25px;
}

li {
    margin: 5px 0;
}

li > ul, li > ol {
    margin: 5px 0;
}

/* 水平线 */
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 30px 0;
}

/* 图片 */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 15px auto;
}

/* 任务列表 */
.task-list-item {
    list-style-type: none;
}

/* 行内代码在表格中 */
td code {
    font-size: 10px;
}

/* ASCII 艺术图容器 */
pre code.language-text,
pre code.language-ascii {
    font-size: 9px;
    line-height: 1.3;
}
'''
    return css


def post_process_html(html_body):
    """对渲染后的 HTML 进行后处理"""
    # 为引用块添加类型识别（基于内容）
    # Tips -> 蓝色
    html_body = re.sub(
        r'<blockquote>\s*<p><strong>Tips</strong>',
        '<blockquote class="tip"><p><strong>Tips</strong>',
        html_body,
        flags=re.IGNORECASE
    )
    
    # 注意 -> 橙色
    html_body = re.sub(
        r'<blockquote>\s*<p><strong>注意</strong>',
        '<blockquote class="warning"><p><strong>注意</strong>',
        html_body,
        flags=re.IGNORECASE
    )
    
    # 警告 -> 红色
    html_body = re.sub(
        r'<blockquote>\s*<p><strong>警告</strong>',
        '<blockquote class="danger"><p><strong>警告</strong>',
        html_body,
        flags=re.IGNORECASE
    )
    
    # 常见问题 -> 绿色
    html_body = re.sub(
        r'<blockquote>\s*<p><strong>常见问题</strong>',
        '<blockquote class="faq"><p><strong>常见问题</strong>',
        html_body,
        flags=re.IGNORECASE
    )
    
    # 本章你将学到 -> 绿色
    html_body = re.sub(
        r'<blockquote>\s*<p><strong>本章你将学到</strong>',
        '<blockquote class="learn"><p><strong>本章你将学到</strong>',
        html_body,
        flags=re.IGNORECASE
    )
    
    return html_body


def add_extra_css():
    """添加额外的引用块样式"""
    return '''
/* 提示框类型样式 */
blockquote.tip {
    border-left-color: #3498db !important;
    background-color: #f0f7ff !important;
}

blockquote.warning {
    border-left-color: #e67e22 !important;
    background-color: #fff8f0 !important;
}

blockquote.danger {
    border-left-color: #e74c3c !important;
    background-color: #fdf2f2 !important;
}

blockquote.faq {
    border-left-color: #27ae60 !important;
    background-color: #f0fff4 !important;
}

blockquote.learn {
    border-left-color: #9b59b6 !important;
    background-color: #f9f0ff !important;
}
'''


def generate_pdf(input_dir, output_path):
    """主函数：生成 PDF"""
    print(f"工作目录: {input_dir}")
    
    # 1. 获取文件列表
    md_files = get_md_files(input_dir)
    print(f"找到 {len(md_files)} 个 Markdown 文件:")
    for f in md_files:
        size = os.path.getsize(os.path.join(input_dir, f)) / 1024
        print(f"  - {f} ({size:.1f} KB)")
    
    # 2. 合并 Markdown
    print("\n正在合并 Markdown 文件...")
    combined_md = read_and_combine_md_files(input_dir, md_files)
    print(f"合并完成，总字数约: {len(combined_md)} 字符")
    
    # 3. 渲染为 HTML
    print("\n正在渲染 Markdown -> HTML...")
    html_body = render_markdown_to_html(combined_md)
    html_body = post_process_html(html_body)
    print("HTML 渲染完成")
    
    # 4. 构建完整 HTML 文档
    css_styles = build_css() + add_extra_css()
    
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Hermes Agent 白皮书 —— 养马从入门到精通</title>
<style>
{css_styles}
</style>
</head>
<body>
{html_body}
</body>
</html>'''
    
    # 5. 生成 PDF
    print("\n正在生成 PDF（这可能需要几分钟，请耐心等待）...")
    font_config = FontConfiguration()
    
    html_doc = HTML(string=full_html, base_url=input_dir)
    html_doc.write_pdf(
        output_path,
        font_config=font_config,
    )
    
    # 6. 验证
    file_size = os.path.getsize(output_path)
    file_size_mb = file_size / (1024 * 1024)
    print(f"\nPDF 生成成功！")
    print(f"输出路径: {output_path}")
    print(f"文件大小: {file_size_mb:.2f} MB")
    
    return output_path


if __name__ == '__main__':
    input_directory = '/Users/jwangkun/Test/hermes/whitepaper'
    output_file = '/Users/jwangkun/Test/hermes/whitepaper/Hermes-Agent白皮书-养马从入门到精通-鲲鹏Talk.pdf'
    
    try:
        generate_pdf(input_directory, output_file)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
