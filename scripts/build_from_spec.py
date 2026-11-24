# -*- coding: utf-8 -*-
"""从 JSON spec 生成三段对照精读 HTML。

设计要点：**术语靠语法标记，不靠手写 span**。
正文里写 `{key|显示词}`，脚本展开成 `<span class="term" data-t="key">显示词</span>`，
并立即校验 key 是否在 spec["terms"] 里 —— 漏登记当场报错，不会等到用户点开发现空白。

用法：
    python build_from_spec.py spec.json -o 精读_XXX_对照精读.html
    python build_from_spec.py spec.json -o out.html --template ../assets/template.html
"""
import sys
import os
import re
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")

# 允许在 en/zh 里出现的行内标签（其余 < > 全部转义）
ALLOWED_TAGS = ("i", "b", "em", "strong", "sub", "sup")


def esc(s):
    """转义 HTML，但保留白名单行内标签。"""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for t in ALLOWED_TAGS:
        s = re.sub(r"&lt;(/?)%s&gt;" % t, r"<\g<1>%s>" % t, s)
    s = s.replace("&lt;br&gt;", "<br>").replace("&lt;br/&gt;", "<br>")
    return s


TERM_RE = re.compile(r"\{([A-Za-z0-9_\-]+)\|([^{}|]+)\}")


def expand_terms(text, terms, where, problems):
    """把 {key|词} 展开成 span.term；key 未登记则记录问题。"""

    def rep(m):
        key, label = m.group(1), m.group(2)
        if key not in terms:
            problems.append("%s: 引用了未登记的术语 key=`%s`（词：%s）" % (where, key, label))
        return '<span class="term" data-t="%s">%s</span>' % (key, esc(label))

    return TERM_RE.sub(rep, text)


def render_note(note):
    """note 支持两种写法：字符串（一小段）或列表（多条 li）。"""
    if not note:
        return ""
    if isinstance(note, str):
        return esc(note)
    items = "".join("<li>%s</li>" % esc(x) for x in note)
    return '<ul>%s</ul>' % items


def build_cards(cards, terms, problems, sec_label):
    out = []
    for i, c in enumerate(cards, 1):
        where = "%s 第 %d 卡" % (sec_label, i)
        en = expand_terms(esc(c["en"]), terms, where + "/en", problems)
        zh = expand_terms(esc(c["zh"]), terms, where + "/zh", problems)
        note = render_note(c.get("note"))
        if note:
            note = '<span class="lab">注解</span>\n' + note
        link = c.get("linkbox")
        if link:
            # linkbox 里的术语标记也要展开（先转义再展开）
            link = expand_terms(esc(link), terms, where + "/linkbox", problems)
            note += '\n<div class="linkbox"><b>本项目联系</b>：%s</div>' % link
        out.append(
            '<div class="grp">\n<div class="en">%s</div>\n<div class="zh">%s</div>\n'
            '<div class="note">\n%s\n</div>\n</div>' % (en, zh, note)
        )
    return "\n\n".join(out)


def build(spec, template_path):
    problems = []
    terms = spec.get("terms") or {}

    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    # ---- 正文 ----
    sections_html = []
    for sec in spec.get("sections", []):
        sid = sec.get("id") or ""
        head = sec.get("heading", "")
        label = sec.get("label", head)
        if head:
            sections_html.append(
                '<h2 class="sec"%s>%s</h2>' % (' id="%s"' % sid if sid else "", esc(head))
            )
        if sec.get("intro"):
            sections_html.append('<div class="sub">%s</div>' % esc(sec["intro"]))
        sections_html.append(build_cards(sec.get("cards", []), terms, problems, label))
    body = "\n\n".join(x for x in sections_html if x)

    # ---- 目录 ----
    toc = spec.get("toc")
    if toc is None:
        toc = [{"id": s["id"], "label": s.get("label") or s.get("heading", "")}
               for s in spec.get("sections", []) if s.get("id")]
        toc.append({"id": "glossary", "label": "术语表"})
        toc.append({"id": "pre", "label": "前置知识"})
    toc_html = "\n".join('<a href="#%s">%s</a>' % (t["id"], esc(t["label"])) for t in toc)

    # ---- 术语表（不提供就用 terms 自动生成，保持插入顺序）----
    gl = spec.get("glossary")
    if gl is None:
        gl = [[v.get("en", ""), v.get("zh", ""), v.get("df", "")] for v in terms.values()]
    gl_rows = "\n".join(
        "<tr><td class=\"t-en\">%s</td><td>%s</td><td>%s</td></tr>"
        % (esc(str(r[0])), esc(str(r[1])), esc(str(r[2])))
        for r in gl
    )

    # ---- 前置知识 ----
    pre = spec.get("prereq")
    if isinstance(pre, list):
        pre_html = "\n".join(
            "<li>%s</li>" % (x if isinstance(x, str) and x.startswith("<") else esc(x))
            for x in pre
        )
    else:
        pre_html = pre or ""

    # ---- 术语词典 JSON ----
    terms_json = json.dumps(terms, ensure_ascii=False, indent=1)
    # JSON 里可能含 </script>，会提前闭合脚本块
    terms_json = terms_json.replace("</", "<\\/")

    src = spec.get("source", {})
    repl = {
        "TITLE": esc(spec.get("title", "对照精读")),
        "SUBTITLE": esc(spec.get("subtitle", "")),
        "DOC_TITLE": esc(spec.get("doc_title", spec.get("title", "对照精读"))),
        "DOC_SUB": esc(spec.get("doc_sub", "")),
        "SOURCE_CITATION": esc(src.get("citation", "")),
        "SOURCE_METHOD": esc(src.get("method", "")),
        "COVERAGE": esc(src.get("coverage", "")),
        "TOC_LINKS": toc_html,
        "BODY": body,
        "GLOSSARY_ROWS": gl_rows,
        "PREREQ_ITEMS": pre_html,
        "READING_ORDER": esc(spec.get("reading_order", "")),
        "FOOTNOTE": esc(spec.get("footnote", "")),
        "TERMS_JSON": terms_json,
    }
    for k, v in repl.items():
        tpl = tpl.replace("{{%s}}" % k, v)

    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", tpl)))
    if left:
        problems.append("模板占位符未替换：%s" % ", ".join(left))

    # ---- 术语覆盖统计 ----
    used = set(re.findall(r'data-t="([^"]+)"', tpl))
    missing = sorted(used - set(terms))
    for m in missing:
        problems.append("正文引用了未登记的术语 key=`%s`" % m)
    unused = sorted(set(terms) - used)

    stats = {
        "cards": len(re.findall(r'class="grp"', tpl)),
        "term_marks": len(re.findall(r'class="term"', tpl)),
        "terms_used": len(used),
        "terms_defined": len(terms),
        "unused_terms": unused,
    }
    return tpl, problems, stats


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("spec", help="spec JSON 路径")
    ap.add_argument("-o", "--out", required=True, help="输出 HTML 路径")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE, help="模板路径")
    ap.add_argument("--allow-missing-terms", action="store_true",
                    help="允许引用未登记术语（默认报错退出）")
    args = ap.parse_args()

    # Windows 上用 PowerShell 写出的 JSON 常带 UTF-8 BOM，utf-8-sig 两种都能读
    with open(args.spec, "r", encoding="utf-8-sig") as f:
        spec = json.load(f)

    tpl, problems, stats = build(spec, args.template)

    hard = [p for p in problems if "未登记的术语" in p]
    soft = [p for p in problems if "未登记的术语" not in p]
    if hard and not args.allow_missing_terms:
        print("术语校验未过，未写文件：", file=sys.stderr)
        for p in hard:
            print("  [ERROR] " + p, file=sys.stderr)
        return 1

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(tpl)

    print("已生成：%s  (%.1f KB)" % (os.path.abspath(args.out), os.path.getsize(args.out) / 1024))
    print("句群卡片 %d 个 | 术语标记 %d 处 | 引用术语 %d 个 | 词典 %d 条"
          % (stats["cards"], stats["term_marks"], stats["terms_used"], stats["terms_defined"]))
    if stats["unused_terms"]:
        print("[warn] 词典里未被引用的术语 %d 个：%s"
              % (len(stats["unused_terms"]), ", ".join(stats["unused_terms"])))
    for p in soft:
        print("[warn] " + p)
    print("\n下一步必跑：python scripts/check_reading_html.py %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
