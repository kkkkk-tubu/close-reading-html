# -*- coding: utf-8 -*-
"""分段写的 HTML 合并器。

为什么要分段：单次 Write 超过约 800 行容易截断/漏尾，长精读页一次写不完。
做法：把页面按 <!--PART:xxx--> 切成几段分别写，最后拼回一个文件。

两种用法：
  1) 目录合并（推荐）：把 part1.html part2.html part3.html 按参数顺序拼起来
     python merge_parts.py p1.html p2.html p3.html -o 精读_XXX.html
  2) 占位合并：模板里写 <!--PART:head--> 等标记，用 --slot name=file 逐个替换
     python merge_parts.py base.html -o out.html --slot head=p1.html --slot body=p2.html

合并后会做一次基本检查：<html>/<body>/</html> 是否齐全，div 是否配平。
"""
import sys
import os
import re
import argparse


def read(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def balance(html):
    body = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    opens = len(re.findall(r"<div(?![\w-])", body, re.I))
    closes = len(re.findall(r"</div\s*>", body, re.I))
    return opens, closes


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("parts", nargs="+", help="按顺序合并的片段文件（或模板文件）")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--slot", action="append", default=[],
                    help="name=path，替换 <!--PART:name--> 占位")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.slot:
        tpl = read(args.parts[0])
        for spec in args.slot:
            if "=" not in spec:
                print("--slot 需要 name=path 形式：%s" % spec, file=sys.stderr)
                return 2
            name, path = spec.split("=", 1)
            marker = "<!--PART:%s-->" % name
            if marker not in tpl:
                print("模板里找不到标记 %s" % marker, file=sys.stderr)
                return 2
            tpl = tpl.replace(marker, read(path))
        out = tpl
        left = re.findall(r"<!--PART:(\w+)-->", out)
        if left:
            print("仍有未替换的片段标记：%s" % ", ".join(left), file=sys.stderr)
            return 1
    else:
        out = "".join(read(p) for p in args.parts)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)

    o, c = balance(out)
    size = os.path.getsize(args.out)
    if not args.quiet:
        print("已合并：%s  (%.1f KB)" % (os.path.abspath(args.out), size / 1024))
        print("div 开 %d / 闭 %d %s" % (o, c, "OK" if o == c else "← 不配平，查一下"))
        has_html = "<html" in out.lower()
        has_end = "</html>" in out.lower()
        print("html 外壳：%s" % ("完整" if has_html and has_end else "缺失（片段合并时正常，整页交付时必须补）"))
    return 0 if o == c else 1


if __name__ == "__main__":
    sys.exit(main())
