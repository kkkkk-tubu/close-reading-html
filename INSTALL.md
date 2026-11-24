# 安装 close-reading-html

一个把论文/教材章节做成「原文 + 译文 + 注解」三段对照精读 HTML 的 agent skill。
纯 Markdown + Python 标准库脚本，无第三方依赖。

## 方式一：OpenViking（跨机器、跨 harness）

已发布在账号共享根，同一 OpenViking 账号下的任何 harness / 机器都能直接调用：

```
viking://agent/skills/close-reading-html
```

确认装上了：

```bash
ov skills list            # 或
find "把论文做成对照精读" --type skill
```

## 方式二：手动放进本地 skills 目录

把本目录整个复制到你所用 harness 的 skills 目录，目录名保持 `close-reading-html`：

| harness | 位置 |
|---|---|
| DSH | `~/.dsh/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.agents/skills/` |
| Cursor | `~/.cursor/skills/` |
| pi | `~/.pi/agent/skills/` |
| OpenCode | `~/.config/opencode/skills/` |

复制完重启会话（或新开一个），skill 会自动被索引，不需要注册。

## 方式三：从 Git 仓库装

```bash
ov skills add https://github.com/<you>/close-reading-html
# 或
git clone https://github.com/<you>/close-reading-html ~/.dsh/skills/close-reading-html
```

## 依赖

| 项 | 必需性 | 说明 |
|---|---|---|
| Python 3.8+ | 必需 | 只用标准库（re / json / urllib / zipfile） |
| node | 可选 | 有它才做内联 JS 的 `--check` 语法检查；没有则跳过并给提示 |
| MathJax CDN | 可选 | 断网时公式不渲染，但文字照常读 |

## 自检

装完跑一遍，确认脚本可用：

```bash
cd close-reading-html
python scripts/build_from_spec.py examples/spec.example.json -o /tmp/demo.html
python scripts/check_reading_html.py /tmp/demo.html
```

两条命令都应 `exit 0`，第二条第最后一行是「结构性检查全过。」
