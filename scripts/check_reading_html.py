# -*- coding: utf-8 -*-
"""对照精读 HTML 自检器。

用途：生成/修改 精读_XXX_对照精读.html 后跑一遍，把「肉眼看不出来的结构性缺陷」在交付前拦下来。
当年真实踩过的四个坑全部在这里有对应检查项：

1. 术语引用漏登记 —— 点击后弹空白或 fallback 文案（必须脚本校验差集）
2. div / span 开闭不配平 —— 浏览器容错后版面崩掉，但源码看起来正常
3. MathJax 配置写在 src 之后 —— $...$ 内联公式全部不渲染（静默失败）
4. JS 语法错误 —— 整块交互（术语卡/遮罩/主题）全挂，页面看起来只是「点不动」

用法：
    python check_reading_html.py 精读_XXX_对照精读.html
    python check_reading_html.py 精读_XXX_对照精读.html --json

退出码：0 全过；1 有 ERROR；2 参数错误。
仅用标准库，不依赖 node（找到 node 才做 JS 语法检查）。
"""
import sys
import os
import re
import json
import shutil
import tempfile
import subprocess
import argparse

# node 不一定在 PATH（桌面版 harness、nvm/fnm/volta、便携安装都会绕开 PATH），
# 这里列常见安装根目录做兜底探测，覆盖 Windows / macOS / Linux 三平台。
NODE_HINTS = [
    os.path.expandvars(r"%ProgramFiles%\nodejs"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\nodejs"),
    os.path.expandvars(r"%APPDATA%\nvm"),
    os.path.expandvars(r"%USERPROFILE%\scoop\apps\nodejs\current"),
    os.path.expandvars(r"%USERPROFILE%\.volta\bin"),
    os.path.expandvars(r"%USERPROFILE%\AppData\Roaming\fnm\node-versions"),
    os.path.expandvars(r"%USERPROFILE%\.workbuddy\binaries\node\versions"),
    "/usr/local/bin",
    "/opt/homebrew/bin",
    os.path.expanduser("~/.nvm/versions/node"),
    os.path.expanduser("~/.local/share/fnm/node-versions"),
    os.path.expanduser("~/.volta/bin"),
]


def _iter_nodes(base, depth=2):
    """在 base 下最多 depth 层找 node 可执行文件，兼容 versions/<ver>/node.exe、
    <ver>/installation/node.exe 这类嵌套布局。"""
    if not os.path.isdir(base):
        return
    for name in ("node.exe", "node"):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            yield p
    if depth <= 0:
        return
    try:
        subs = sorted(
            (d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))),
            reverse=True,
        )
    except OSError:
        return
    for d in subs:
        for p in _iter_nodes(os.path.join(base, d), depth - 1):
            yield p


def find_node():
    # 允许用环境变量直接指定（找不到 node 的用户可自行指向任意版本）
    for env in ("NODE", "NODE_EXE"):
        v = os.environ.get(env)
        if v and os.path.isfile(v):
            return v
    exe = shutil.which("node")
    if exe:
        return exe
    for base in NODE_HINTS:
        for p in _iter_nodes(os.path.expanduser(base)):
            return p
    return None


def read_html(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comments(html):
    """去掉 HTML 注释，避免注释里的示例标签干扰配平统计。"""
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def check_term_refs(html):
    """正文 span.term 的 data-t 必须全部出现在 TERMS 词典里。"""
    errs, warns = [], []
    data_t = re.findall(r'class="term"[^>]*?data-t="([^"]+)"', html)
    data_t += re.findall(r'data-t="([^"]+)"[^>]*?class="term"', html)
    used = sorted(set(data_t))

    # 从 script 里抽 TERMS 对象的顶层 key（形如  "key":{  或  'key':{）
    m = re.search(r"const\s+TERMS\s*=\s*\{(.*?)\}\s*;", html, re.S)
    if not m:
        errs.append("找不到 `const TERMS = { ... };` 代码块")
        return errs, warns, used, []

    block = m.group(1)
    keys = re.findall(r'^\s*"([^"]+)"\s*:\s*\{', block, re.M)
    keys += re.findall(r"^\s*'([^']+)'\s*:\s*\{", block, re.M)
    keyset = set(keys)

    missing = [k for k in used if k not in keyset]
    if missing:
        errs.append(
            "正文引用了未登记的术语（点开会是空白）：%s" % ", ".join(missing)
        )

    unused = sorted(keyset - set(used))
    if unused:
        warns.append(
            "词典里登记了但正文没引用的术语 %d 个（不算错，但可精简）：%s"
            % (len(unused), ", ".join(unused[:12]) + (" ..." if len(unused) > 12 else ""))
        )

    # 每条术语的三个字段必须齐全且非空（key 在 JSON 字面量里是被引号包着的）
    for k in keys:
        m2 = re.search(
            r'"%s"\s*:\s*\{(.*?)\}' % re.escape(k), block, re.S
        )
        if not m2:
            continue
        body = m2.group(1)
        for field in ("en", "zh", "df"):
            # 字段名可能带引号（JSON 字面量）也可能不带（手写 JS 对象），两种都收
            if not re.search(
                r'(?:["\']%s["\']|\b%s)\s*:\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
                % (field, field),
                body,
            ):
                errs.append("术语 `%s` 缺字段 `%s`" % (k, field))

    return errs, warns, used, sorted(keyset)


def check_balance(html):
    """div / span / table 开闭配平。"""
    errs = []
    body = strip_comments(html)
    for tag in ("div", "span", "table", "tbody", "thead", "tr", "td", "th", "ul", "ol", "li"):
        opens = len(re.findall(r"<%s(?![\w-])" % tag, body, re.I))
        closes = len(re.findall(r"</%s\s*>" % tag, body, re.I))
        if opens != closes:
            errs.append("<%s> 开闭不配平：开 %d / 闭 %d" % (tag, opens, closes))
    return errs


def check_mathjax_order(html):
    """MathJax 配置必须在加载脚本之前，否则内联 $..$ 不渲染。"""
    errs, warns = [], []
    if "MathJax" not in html:
        warns.append("页面没有 MathJax（纯文字精读可以不管；有 $公式$ 就必须有）")
        return errs, warns
    cfg = html.find("window.MathJax")
    src = html.find("tex-mml-chtml.js")
    if cfg < 0:
        errs.append("引了 MathJax 但没有 `window.MathJax = {...}` 配置块")
    elif src >= 0 and cfg > src:
        errs.append(
            "MathJax 顺序反了：window.MathJax 配置出现在 tex-mml-chtml.js 之后，"
            "内联 $...$ 不会渲染（当年真实踩过）"
        )
    if 'inlineMath' not in html:
        warns.append("MathJax 配置里没有 inlineMath，单 `$` 内联公式不会渲染")
    return errs, warns


def check_ids(html):
    """重复 id 会让目录锚点和 getElementById 抢同一个元素。"""
    errs = []
    ids = re.findall(r'\sid="([^"]+)"', html)
    seen, dup = set(), set()
    for i in ids:
        (dup if i in seen else seen).add(i)
    if dup:
        errs.append("重复 id：%s" % ", ".join(sorted(dup)))
    # 目录锚点必须有对应目标
    hrefs = re.findall(r'href="#([^"]+)"', html)
    dangling = [h for h in set(hrefs) if h not in seen]
    if dangling:
        errs.append("目录锚点指向不存在的 id：%s" % ", ".join(sorted(dangling)))
    return errs


def check_js(html):
    """抽出全部 <script> 内联块，用 node --check 验语法。"""
    errs, warns = [], []
    node = find_node()
    if not node:
        warns.append("未找到 node，跳过 JS 语法检查（设环境变量 NODE 指向可执行文件可启用）")
        return errs, warns

    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
    blocks = [b for b in blocks if b.strip()]
    if not blocks:
        warns.append("页面没有内联 script，跳过")
        return errs, warns

    for idx, code in enumerate(blocks, 1):
        # 纯配置块（只有 window.MathJax = {...}）也是合法 JS，照样检查
        fd, p = tempfile.mkstemp(suffix=".js", prefix="_cr_block%d_" % idx)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            r = subprocess.run(
                [node, "--check", p],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if r.returncode != 0:
                msg = (r.stderr or "").strip().splitlines()
                head = msg[0] if msg else "未知错误"
                errs.append("第 %d 段 script 语法错误：%s" % (idx, head))
        finally:
            try:
                os.remove(p)
            except OSError:
                pass
    return errs, warns


def check_glossary_table(html, terms_keys):
    """术语表表格行数应与词典条目数大致一致（表是给人看的索引）。"""
    errs, warns = [], []
    m = re.search(r'<tbody>(.*?)</tbody>', html, re.S)
    if not m:
        warns.append("没找到术语表 tbody")
        return errs, warns
    rows = len(re.findall(r"<tr[^>]*>", m.group(1), re.I))
    if rows == 0:
        errs.append("术语表是空的")
    elif terms_keys and abs(rows - len(terms_keys)) > len(terms_keys) * 0.35:
        warns.append(
            "术语表 %d 行 vs 词典 %d 条，差距较大，检查是否漏写索引行"
            % (rows, len(terms_keys))
        )
    return errs, warns


def check_placeholders(html):
    """模板占位符没替换干净是最常见的交付事故。"""
    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", html)))
    if left:
        return ["模板占位符未替换：%s" % ", ".join(left)]
    return []


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("path", help="要检查的 HTML 文件路径")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        print("文件不存在：%s" % args.path, file=sys.stderr)
        return 2

    html = read_html(args.path)
    errs, warns = [], []

    e, w, used, keys = check_term_refs(html)
    errs += e; warns += w

    errs += check_balance(html)
    e, w = check_mathjax_order(html);      errs += e; warns += w
    errs += check_ids(html)
    e, w = check_js(html);                 errs += e; warns += w
    e, w = check_glossary_table(html, keys); errs += e; warns += w
    errs += check_placeholders(html)

    stats = {
        "file": os.path.abspath(args.path),
        "bytes": os.path.getsize(args.path),
        "sentence_groups": len(re.findall(r'class="grp"', html)),
        "term_marks": len(re.findall(r'class="term"', html)),
        "terms_used": len(used),
        "terms_defined": len(keys),
        "mathjax": "MathJax" in html,
    }

    if args.json:
        print(json.dumps(
            {"ok": not errs, "stats": stats, "errors": errs, "warnings": warns},
            ensure_ascii=False, indent=2))
        return 0 if not errs else 1

    print("=" * 70)
    print("文件: %s  (%.1f KB)" % (stats["file"], stats["bytes"] / 1024))
    print("句群卡片 %d 个 | 术语标记 %d 处 | 引用术语 %d 个 | 词典 %d 条"
          % (stats["sentence_groups"], stats["term_marks"],
             stats["terms_used"], stats["terms_defined"]))
    print("=" * 70)
    for x in errs:
        print("[ERROR] " + x)
    for x in warns:
        print("[warn ] " + x)
    if not errs:
        print("结构性检查全过。" + ("（有 %d 条提醒）" % len(warns) if warns else ""))
    else:
        print("共 %d 个 ERROR，改完再验。" % len(errs))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
