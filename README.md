# 数格涂涂 · Number Grid Paint

一个**单文件、离线、无依赖**的可打印数学游戏生成器。打开 HTML 就是一份出题器：
设好目标数，它生成一张 10×10（或 8×8）数字盘，孩子把**上、下、左、右相邻的两格**
凑成目标数的**和 / 差 / 积**，用对应颜色涂满或圈出，同时在集章表里写出算式。
版面按 A4 实测自动排，导出 PDF 直接打印就能上课。

English summary below — the file itself is fully bilingual (中文 / English switch in the
top-right corner; it changes both the interface and the printed worksheet).

---

## 30 秒上手

1. 双击 `数格涂涂_生成器.html`，用 Edge / Chrome 打开（不需要联网，不需要装任何东西）。
2. 选难度包（入门 / 标准 / 进阶 / 挑战 / 乘法 / 混排），或者自己勾目标和、差、积。
3. 点 **换一批** 换题，点 **打印 / 存 PDF**（浏览器打印对话框里选"另存为 PDF"）。
4. 想复现同一套题：记下答案页上的**种子**，回到页面填进种子框即可。

英文版：把右上角切到 **EN**，纸面会变成给英语课堂用的本地化措辞（"Stamp Hunt"、
"Cell Battle"、"Show work"），不是逐字翻译。

## 这个游戏练什么

| 玩法 | 说明 |
| --- | --- |
| 闯关集章 | 每人独立涂满盘面，一个目标数一种颜色，涂一对就在集章表写一行算式 |
| 双人抢格 | 两人各一色轮流占格，一格只能用一次，谁找不到合法对谁停手，比谁涂得多 |

三条约定印在纸上：① 一格只能涂一次，涂过的格不能重复使用；② 一个目标数用同一种
颜色，两格都涂满或圈出，并在集章表写出算式；③ 相加超过 10 的不算。

出题内核保证：同一卷里所有目标对**互不重叠**、一定涂得完；`audit()` 会自检并只在真的
没过时才在答案页提示。乘法轮只列两个一位数相乘的积，11 / 13 / 17 / 19 这类凑不出来的
目标不会出现在盘里，勾了乘法的盘内不含 0。

## 版面能力

* **一页一卷 / 一页两卷（裁开）**：两卷共用一张 A4，中间一条裁开线，各带页眉集章表。
* **四个可选块**：页眉（姓名 / 日期 / 用时）、集章表、页脚（满分对数 + 签字）、玩法说明。
* **数表自动放大**：格子边长不是猜的——脚本在浏览器里实测版面，二分搜到这张纸装得下的
  最大格；版面紧时自动换两栏说明、集章表多分一栏、页眉压成一行，把纸让给数表。
* **➕ / ➖ 手动微调**：想再大一点可以按 ➕，按钮会显示"+2mm"，点一下回到"自动"。
* **份数 1–6**：一次出多卷，每卷盘面都不同。

## 地址栏参数（可分享 / 可脚本化）

`?` 后面接任意组合，例：
`数格涂涂_生成器.html?lang=en&size=10&per=2&copies=4&sum=6,7,8&diff=2,3&seed=20261111`

| 参数 | 取值 | 含义 |
| --- | --- | --- |
| `lang` | `zh` \| `en` | 界面与纸面语言（优先级：参数 ＞ 本机上次选择 ＞ 浏览器语言） |
| `size` | `8` \| `10` | 盘面边长 |
| `mode` | `quest` \| `duel` | 闯关集章 / 双人抢格 |
| `sum` `diff` `mul` | 逗号分隔，空值写 `sum=` | 目标和 / 差 / 积集合（`sum=&diff=` 就是纯乘法卷） |
| `quota` | `1`–`4` | 每个目标要涂几对 |
| `copies` | `1`–`6` | 出几卷 |
| `per` | `1` \| `2` | 一页一卷 / 一页两卷裁开 |
| `seed` | 整数 | 出题种子，同种子同题 |
| `hdr` `stamp` `foot` `rule` `ans` | `0` \| `1` | 页眉 / 集章表 / 脚注 / 玩法说明 / 附答案页 |
| `adj` | `-8`…`8` | 手动给格子加减毫米 |
| `p` | `easy` `std` `mid` `hard` `m1` `m2` `m3` `mix` | 直接套难度包 |

## 隐私

完全离线。文件里没有任何网络请求、没有第三方脚本、没有埋点；只用 `localStorage`
记住你上次选的语言（`file://` 下写不进去会自动退回浏览器语言）。题目、种子都只存在于
你手上的那张纸和这个文件里。

## 校验（给要改代码的人）

```bash
node --version                     # 只需要 Node 和 Python3 + Edge/Chrome
node scripts/verify.mjs            # 出题内核 76 项断言（数学红线，不依赖浏览器）
python3 scripts/env.py             # 打印脚本们找到的 HTML 与浏览器路径
python3 scripts/size_probe.py --lang en     # 144 个版面组合 ×语言：不溢出、不折行、不压格
python3 scripts/width_probe.py 1440 760 400 lang=en   # 窗口多宽都解出同一个格子
python3 scripts/i18n_probe.py      # 双语：占位符、单复数、漏翻、撑爆列
python3 scripts/pdf_check.py       # 12 组版面导出 PDF，数页数、查空白页
python3 scripts/pdf_export.py '?size=10&lang=en' out/样张.pdf
python3 scripts/shot.py out/屏显.png '?size=10&lang=en' all
```

开发脚本里的 HTML 路径和浏览器路径都由 `scripts/env.py` 统一解析，换机器不用改代码：
设 `GRIDPAINT_SRC` / `GRIDPAINT_BROWSER` 即可。

## 打包与上架

```bash
python3 scripts/make_dist.py --strict
```

出三份物料：`dist/repo/`（GitHub 仓库）、`dist/number-grid-paint-skillhub.zip`、
`dist/number-grid-paint-openplatform.zip`（WorkBuddy 开放平台，精简包）。
preflight 会拦下缺文件、缺许可全文、HTML 里出现网络请求、frontmatter 字段不全、
以及**未脱敏内容**这几类问题。

发布纪律：**`push` / 上传 / `publish` 之前先跑泄露与脱敏审查，退出码 0 才出门。**

```bash
python3 scripts/leak_scan.py dist/repo     # 扫真正要发出去的那份（zip 会扫包内字节）
```

它查本机路径、用户目录、账号名、邮箱、电话、证件号、token、私钥、带凭证的 URL、
UUID、教育类 PII 字段名，外加 `scripts/redact_terms.txt` 里你声明的名单词
（真实人名/班级/校名/内部代号——这份词表只留本地，不打进任何包）。

三个平台上架进度与各自的坑见 [`SUBMISSION.md`](SUBMISSION.md)；
SkillHub 已上线，可直接装：

```bash
skillhub install number-grid-paint --namespace user_1db801dd --dir ~/.workbuddy/skills
```

## 署名

按要求署名即可自由转发与改编（非商业、相同方式共享）：

> Number Grid Paint / 数格涂涂 by **粉笔与代码**，
> 许可证 CC BY-NC-SA 4.0，https://github.com/seahp/number-grid-paint
>
> （仓库地址按本仓库计划名写好，**以你实际创建的仓库为准**；不一致时改这一处和
> HTML 顶部注释里的 `署名与出处` 一行。）

## 许可证

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh) —
署名 / 非商业性使用 / 相同方式共享。完整条款见 [`LICENSE.txt`](LICENSE.txt)。

© 2026 **粉笔与代码**

---

## English

**Number Grid Paint** is a printable math-game generator that lives in one offline HTML
file — no build, no server, no dependencies. It lays out a 10×10 (or 8×8) number grid;
a child finds pairs of cells that touch **up, down, left or right** whose **sum,
difference or product** equals a target number, colours or circles both cells in that
target's colour, and writes the equation on the stamp card.

Two modes: **Stamp Hunt** (solo — fill the grid, one colour per target, one equation per
pair on the card) and **Cell Battle** (two players, one colour each, take turns claiming
cells; whoever cannot find a legal pair stops, most pairs wins).

The generator is deterministic (same seed → same questions, and the seed is printed on
the answer page), supports 1–6 sets per run, and prints either one set per A4 sheet or
two-up on a single sheet with a cut line. Grid size is **solved by measurement**: the
page is measured in the browser and the cell size is binary-searched to the largest value
that still fits, so nothing is clipped and nothing spills onto a second page. When the
layout gets tight it automatically goes two-column for the rules, adds a column to the
stamp card, and compresses the header — the paper is given back to the grid. A ➕/➖ pair
lets you nudge the cell size by hand.

Language switch (top right) changes the interface *and* the printed page. The English
text is written for English-language classrooms rather than translated word for word.

Everything runs locally: no network requests, no third-party scripts, no analytics. The
only storage is a `localStorage` entry remembering your language choice.

To verify or modify: `node scripts/verify.mjs` runs 76 kernel assertions; the Python
probes in `scripts/` check layout overflow, window-width independence, bilingual
placeholders/plurals, and PDF page counts. Paths are resolved by `scripts/env.py`
(`GRIDPAINT_SRC`, `GRIDPAINT_BROWSER`).

To package for publishing: `python3 scripts/make_dist.py --strict` builds a GitHub repo
directory plus two marketplace zips (SkillHub and WorkBuddy open platform, which want
different `SKILL.md` frontmatter). `SUBMISSION.md` documents the actual submission steps
for each platform.

One rule before anything goes out: **run the leak & redaction audit and require exit 0.**
`python3 scripts/leak_scan.py dist/repo` checks hard-coded home/user paths, account names,
emails, phone numbers, ID numbers, tokens and private keys, credentialed URLs, UUIDs and
education-PII field names, plus a local denylist of real names/classes/schools you declare
in `scripts/redact_terms.txt` (that file never ships inside any package). Matched lines are
printed redacted, so the audit itself can't become a second leak. It is wired into
`make_dist.py` on both sides — source tree before building, zip bytes after.

The SkillHub listing is live: `skillhub install number-grid-paint --namespace user_1db801dd`.

Licensed **CC BY-NC-SA 4.0** — attribution, non-commercial, share-alike. Full text in
[`LICENSE.txt`](LICENSE.txt). © 2026 **粉笔与代码 (Fenbi yu Daima)**.
