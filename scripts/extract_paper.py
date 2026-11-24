# -*- coding: utf-8 -*-
"""ar5iv HTML → 带公式的 Markdown。

为什么用 ar5iv 而不用 PDF：
  - ar5iv 把公式保留成 LaTeX，藏在 <math alttext="..."> 的 alttext 属性里，可以完整提取；
  - 直接读 PDF 会丢掉公式排版（变成一堆散字符）。
  - 官方 PDF 地址不要带版本号：arxiv.org/pdf/1708.02002 是 200，
    arxiv.org/pdf/1708.02002v3 是 404。

用法：
    python extract_paper.py https://ar5iv.labs.arxiv.org/html/1708.02002 -o focal.md
    python extract_paper.py 本地ar5iv.html -o out.md          # 已下载的页面

只用标准库（urllib + re），不依赖 bs4 / lxml。
"""
import sys
import os
import re
import html as htmllib
import argparse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def fetch(url_or_path):
    if os.path.isfile(url_or_path):
        with open(url_or_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    req = urllib.request.Request(url_or_path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s)


MATH_RE = re.compile(r"<math\b[^>]*?alttext=\"(.*?)\"[^>]*>.*?</math>", re.S)


def math_to_latex(fragment):
    """<math alttext="..."> 换成 $...$ 或 $$...$$。"""

    def rep(m):
        tex = htmllib.unescape(m.group(1)).strip()
        # 多行 / 含 = 且较长的按行间公式处理
        display = ("\\begin{" in tex) or ("\n" in tex)
        return "\n$$\n%s\n$$\n" % tex if display else "$%s$" % tex

    return MATH_RE.sub(rep, fragment)


def convert(html):
    body = html
    m = re.search(r"<article[^>]*>(.*?)</article>", html, re.S)
    if m:
        body = m.group(1)

    body = math_to_latex(body)

    # 标题
    body = re.sub(r"<h([1-6])[^>]*>(.*?)</h\1>", lambda m: "\n%s %s\n" % ("#" * int(m.group(1)), strip_tags(m.group(2)).strip()), body, flags=re.S)
    # 段落
    body = re.sub(r"<p[^>]*>(.*?)</p>", lambda m: "\n\n%s\n\n" % clean_inline(m.group(1)), body, flags=re.S)
    # 列表
    body = re.sub(r"<li[^>]*>(.*?)</li>", lambda m: "\n- %s" % clean_inline(m.group(1)).strip(), body, flags=re.S)
    # 表格：保留成粗略的管道表，够对照阅读即可
    body = re.sub(r"<table[^>]*>.*?</table>", lambda m: "\n\n[表格：原页面见 %s]\n\n" % "表格", body, flags=re.S)
    # 剩下的块级标签换行
    body = re.sub(r"</(div|section|figure|blockquote)>", "\n", body)
    body = re.sub(r"<br\s*/?>", "\n", body)

    # 去掉残留标签与多余空行
    body = re.sub(r"<[^>]+>", "", body)
    body = htmllib.unescape(body)
    body = re.sub(r"[ \t\u00a0]+", " ", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def clean_inline(s):
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s).strip()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("src", help="ar5iv URL 或本地 html 路径")
    ap.add_argument("-o", "--out", required=True, help="输出 markdown 路径")
    ap.add_argument("--raw", action="store_true", help="顺便把原始 HTML 存到同目录 .html")
    args = ap.parse_args()

    html = fetch(args.src)
    if args.raw:
        p = os.path.splitext(args.out)[0] + ".html"
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
        print("原始 HTML: %s (%.1f KB)" % (p, os.path.getsize(p) / 1024))

    md = convert(html)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# 提取自 %s\n\n" % args.src + md)

    n_math = len(re.findall(r"\$", md)) // 2
    print("已生成：%s  (%.1f KB, 约 %d 处公式)"
          % (os.path.abspath(args.out), os.path.getsize(args.out) / 1024, n_math))
    print("\n下一步：人工核对章节号、公式号、图号是否与原文一致，再切句群。")


if __name__ == "__main__":
    sys.exit(main())
