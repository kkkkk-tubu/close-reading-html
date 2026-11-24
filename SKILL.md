---
name: close-reading-html
description: 把一篇论文（或一章教材/一份规范）做成可双击打开的三段对照精读 HTML：英文原文 + 中文译文 + 中文注解，按「相邻几句」切句群卡片，术语可点击弹注释、可遮住译文自测、术语表可搜索、深/浅色可切换。Use when the user asks to 做精读 / 对照精读 / 原文译文注解 / 翻译一篇论文 / 逐段讲解论文 / 做个可点击术语的阅读页 / 论文精读 HTML / close reading page, or hands over a paper PDF, arXiv 链接、ar5iv 页面 and wants a readable annotated version. Also use when updating or extending an existing 对照精读.html (补章节、补术语、修版面).
---

# 对照精读 HTML 构建 skill

这个 skill 的形态来自一份真实的论文精读页（一篇 CVPR/ICCV 级的经典论文，38 个句群卡片 / 60 个术语 / 96 KB 单文件）。它是「论文读不懂、又不想只拿到一段翻译」时的产物：同一段话摆出原文、译文、注解三层，注解里能挂「自己的工作/项目联系」和「答辩话术」。

**核心约束：单文件、零依赖、双击即开。** 不引本地 CSS/JS、不依赖服务器、不要求联网（MathJax 走 CDN，断网时公式不渲染但文字照读）。

## 什么时候用

- 用户给了论文（PDF / arXiv 号 / ar5iv 链接），要「精读」「逐段讲解」「翻译+注解」。
- 要续写已有的对照精读页（原文里常有「待续：§4、§5、§6」这类标记）。
- 要把一份已有 Markdown 精读稿转成可交互页面。

不适用：只要一份 Word 报告 → 用 `office-docx`；只要翻译 → 直接翻；只要 PPT 讲论文 → 用 `ppt-master` / `office-academic-skill`。

## 交付形态

一份 `.html`，放 `reports/` 下，命名 `精读_<第一作者+年份>_<短标题>_对照精读.html`。

**默认不生成 md 副本、不生成 PDF、不生成逐页截图。** 用户点名要才补。

## 工作流

### 1. 拿正文（这一步决定后面全部质量）

优先级：

1. **ar5iv**：`https://ar5iv.labs.arxiv.org/html/<id>` —— 公式以 LaTeX 存在 `alttext` 属性里，正则可提；直接 Read PDF 会丢公式排版。脚本见 `scripts/extract_paper.py`。
2. **arXiv 官方 PDF**：`https://arxiv.org/pdf/<id>` —— **不要带版本号**，`...pdf/1708.02002` 200 OK，`...pdf/1708.02002v3` 返回 404。
3. 会议/期刊官方 PDF（注意有的文件名和论文标题不一致，如 Elkan 2001 是 `rescale.pdf` 而非 `resample.pdf`）。

**原文必须是真抓的，不许凭记忆写。** 这是这个 skill 唯一不可让步的红线：凭记忆复述的「原文」会在术语、公式号、图号上系统性出错，而精读文档的价值全在可核对。

### 2. 切句群（这是和「整段翻译」的分界）

用户当年原话的反馈是：**一整段翻译太长，要「有联系的几句」为一组。**

切分规则：

- 一个卡片 = **2–4 句**，按论证单元切，不按长度切。
- 遇到以下位置必切：转折（However / In contrast）、立论句、公式引入前、例子开始前。
- 公式单独成段时，与它的解释句同卡。
- 一张卡片的英文字数控制在 **40–120 词**；超 150 词一定拆。

### 3. 三层内容各写什么

| 层 | 写什么 | 禁忌 |
|---|---|---|
| `.en` 原文 | 照抄，词内空格做最小整理，不动措辞 | 不许改写、不许省略号跳过论证 |
| `.zh` 译文 | 术语与原文一致，句序可调以通顺 | 不许意译掉限定词（only / at most / up to） |
| `.note` 注解 | 讲清「这句在论证里干什么」+ 术语的定量含义 + 常见误读 | 不许复述译文，那是废话 |

注解里值得出现的四类内容（按价值排序）：

1. **定量锚点**：把「压垮」这种词换算成数字（`$10^5$ 个各贡献 0.01 的样本合计约 1000`）。
2. **立论位置**：这句是不是全文因果链的一环，标出来（「这是全文的立论句」）。
3. **常见误读**：作者 reshape 的是损失函数，不是网络结构，也不是数据。
4. **`.linkbox` 与本工作的联系**：只在真正对得上时加。形如：「你的数据正负比是 `5:1`，触发该损失函数的前提并不成立——这是你写迁移边界的定量依据。」关键是**填进你自己的真实数字**，没有数字就别加这个框。

`.linkbox` 一张卡片最多一个；全文密度控制在**每 5–8 个卡片出现一次**，否则整页变成自我引用。

### 4. 标术语

正文里每个专业词首次出现时包 `<span class="term" data-t="KEY">词</span>`，**译文里的对应词也要包同一个 KEY**——两侧同时高亮是这套页面的主要观感来源。

`data-t` 用短横线小写（`class-imbalance`、`focal-loss`、`fg-bg`），不要用中文、不要用空格。

**关键：正文引用的 KEY 必须在 `TERMS` 词典里有条目，否则点开是空白。** 当年真实踩过，所以有校验脚本。

### 5. 生成

```
python scripts/build_from_spec.py spec.json -o 精读_XXX_对照精读.html
```

或手工填 `assets/template.html` 的占位符（占位符清单见 `references/template-slots.md`）。份量大时**分段写再合并**（`scripts/merge_parts.py`），避免单次 Write 过长被截断。

### 6. 自检（必跑，不许跳）

```
python scripts/check_reading_html.py 精读_XXX_对照精读.html
```

七项检查：术语引用漏登记 / div-span 配平 / MathJax 配置顺序 / 重复 id / 目录锚点 / JS 语法 / 占位符残留。退出码 0 才算交付。

再人工看一眼（浏览器打开）：点三个术语、遮住译文、切主题、术语表搜一个词。

## 四个真实踩过的坑

1. **MathJax 必须先配置后加载**：`window.MathJax = {...}` 要写在 `<script src=".../tex-mml-chtml.js" async>` **之前**。顺序反了则 `$...$` 内联公式不渲染（MathJax 默认不启用单 `$`），而且**没有任何报错**。
2. **术语覆盖必须脚本校验**：正则提取 `data-t="..."` 与 `TERMS` 的 key 求差集。漏一个，点开就是空白或 fallback 文案。
3. **JS 语法用 `node --check` 检查**：node 常常不在 PATH（桌面版 harness、nvm/fnm/volta 都会绕开）。校验脚本会先 `shutil.which`，再扫常见安装根目录；实在找不到就跳过这一项并提示，不算失败。要自己指定就设环境变量 `NODE` 指向可执行文件。
4. **HTML 分 3 段写再合并**：先写 `<head>+样式`、再写正文卡片、再写术语表+JS，用 `merge_parts.py` 拼。单次 Write 超过约 800 行容易截断。

## 文件

- `assets/template.html` —— 完整骨架（CSS 变量双主题、句群卡片、术语卡、术语表、遮罩、搜索），占位符 `{{...}}`。
- `scripts/build_from_spec.py` —— 从 JSON spec 生成完整 HTML，自动做术语引用差集检查。
- `scripts/check_reading_html.py` —— 七项结构自检，可 `--json`。
- `scripts/extract_paper.py` —— ar5iv HTML → 带公式的 Markdown。
- `scripts/merge_parts.py` —— 分段 HTML 合并。
- `references/template-slots.md` —— 占位符与 CSS 类名清单。
- `references/writing-guide.md` —— 注解怎么写才有信息量（正反例对照）。
- `examples/spec.example.json` —— 一份最小可用的 spec 样例。
