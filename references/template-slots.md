# 模板占位符与类名清单

模板文件：`assets/template.html`。所有占位符形如 `{{NAME}}`，`build_from_spec.py` 会全部替换；漏一个 `check_reading_html.py` 会报错。

## 占位符

| 占位符 | 填什么 | 备注 |
|---|---|---|
| `{{TITLE}}` | 顶栏标题 | 建议「XXX 精读 · 原文/译文/注解」 |
| `{{SUBTITLE}}` | 顶栏副标题（`<small>` 里的灰字） | 一行说清是谁的哪篇、怎么用 |
| `{{DOC_TITLE}}` | 正文大标题 `<h1>` | 通常是英文原题 + 「— 三段对照精读」 |
| `{{DOC_SUB}}` | 大标题下的灰字 | 阅读定位，如「第 3 章 · 按相邻几句切句群」 |
| `{{SOURCE_CITATION}}` | 完整引文 | 作者、标题、会议/期刊、页码、arXiv 号；这一行要能直接抄进参考文献 |
| `{{SOURCE_METHOD}}` | 取文方式 | 说清是 ar5iv 抓的还是 PDF 转的，公式怎么处理，改了什么没改什么 |
| `{{COVERAGE}}` | 本批覆盖范围 | 明确列出已覆盖章节与「待续」章节，方便下一批接着做 |
| `{{TOC_LINKS}}` | 一行 `<a href="#id">名</a>` | 由 `sections[].id` 自动生成 |
| `{{BODY}}` | 全部句群卡片 | 由 `sections[].cards[]` 生成 |
| `{{GLOSSARY_ROWS}}` | 术语表 `<tr>` | 不给 `glossary` 就用 `terms` 自动生成 |
| `{{PREREQ_ITEMS}}` | 前置知识 `<li>` | 可以是字符串列表或一段 HTML |
| `{{READING_ORDER}}` | 建议阅读顺序 | 一句话，用 `→` 连接 |
| `{{FOOTNOTE}}` | 页脚 | 写「本批结束」+ 下一批要做什么 |
| `{{TERMS_JSON}}` | `TERMS` 词典 JSON | 脚本会把 `</` 转成 `<\/` 防止提前闭合 script |

## 关键 CSS 类名

改版面时必须知道每个类管什么。

| 类 / id | 作用 | 改动风险 |
|---|---|---|
| `:root[data-theme="dark"|"light"]` | 两套主题变量 | 加新颜色要在两套里都加，否则切换后看不见 |
| `.topbar` / `.inner` | 吸顶工具栏 | 位置固定，改宽度要同步改 `.wrap` 的 `max-width`（当前 980px） |
| `.wrap` | 内容容器 | `padding-bottom:120px` 是给术语卡留的滚动余量 |
| `h2.sec` | 章节标题（左侧蓝条） | `id` 是目录锚点，改 id 要同步 `TOC_LINKS` |
| `.grp` | **一个句群卡片**，整套页面就靠这个类计数 | 校验脚本用 `class="grp"` 统计卡片数 |
| `.grp .en` | 英文原文，衬线体、浅蓝 | — |
| `.grp .zh` | 中文译文 | `.hidezh` 时被隐藏，是「遮住译文」的开关 |
| `.grp .note` | 注解区 | — |
| `.lab` | 小标签（`注解`） | — |
| `.linkbox` | 「本项目联系」框 | 密度别超每 5–8 卡一次 |
| `.term` + `data-t` | 可点术语 | `data-t` 必须命中 `TERMS` 的 key |
| `.term.pin` | 当前被点开的术语 | 由 JS 加，别手写 |
| `#card` / `#cardBody` | 浮层术语卡 | `position:fixed`，JS 算位置 |
| `.hidezh` | 加在 `<body>` 上遮译文 | 由按钮切换 |
| `#gl tbody tr` | 术语表行 | 搜索框按 `textContent` 过滤 |
| `.srcbox` | 原文来源框 | 四行结构固定，别删「取文方式」 |

## 脚本顺序（不能改）

```html
<script>window.MathJax = {... inlineMath:[['$','$']] ...};</script>
<script src=".../tex-mml-chtml.js" async></script>
<script>/* TERMS + 交互 */</script>
```

**配置块必须在 CDN 脚本之前**。顺序反了，`$...$` 内联公式全部不渲染，而且控制台不报错——这是最难发现的坑。

## 卡片 HTML 骨架

```html
<div class="grp">
<div class="en">英文原文，术语包 <span class="term" data-t="key">term</span></div>
<div class="zh">中文译文，同一术语也包同一个 key</div>
<div class="note"><span class="lab">注解</span>
<ul>
<li><b>这句在论证里干什么</b>：……</li>
<li><b>定量锚点</b>：……</li>
</ul>
<div class="linkbox"><b>本项目联系</b>：……</div>
</div>
</div>
```

`build_from_spec.py` 生成的正是这个结构，手写时照抄即可。
