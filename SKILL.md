---
name: number-grid-paint
slug: number-grid-paint
display_name: 数格涂涂 · 数学涂色游戏卷生成器
display_name_en: Number Grid Paint Worksheet Generator
displayName: 数格涂涂 · 数学涂色游戏卷生成器
displayNameEn: Number Grid Paint Worksheet Generator
summary: 单文件离线 HTML，出可打印的相邻两格凑数涂色游戏卷（和/差/积，中英双语，A4）
tags: education, math, printable, worksheet, offline, bilingual
description: 生成可打印的「数格涂涂」数学游戏卷（A4，单文件离线 HTML，中英双语）。10×10 或 8×8 数字盘，孩子把上、下、左、右相邻两格凑成目标数的和/差/积并涂色，同时在集章表写算式；支持闯关集章与双人抢格、一页两卷裁开、1–6 份批量、种子复现。出题内核保证目标对互不重叠、一定涂得完，并自检。当用户需要出数学涂色游戏、口算游戏卷、乘法口诀练习纸、相邻两格凑数、课堂数学游戏、批量出不同题目的数学卷时使用。
description_zh: 给一年级（含表内乘法阶段）出一份双击即用的数学游戏卷。一个 10×10 或 8×8 数字盘，孩子把上下左右相邻的两格凑成目标数的和、差或积，涂色并在集章表写算式；能选难度包、一次出 1–6 份、A4 一页两卷裁开、双人抢格对战，同一个种子永远出同一套题，答案页自带算式清单。界面和纸面都能切中英文。全程本地运行，不联网、不装任何东西。
description_en: A printable math-game worksheet that lives in one offline HTML file. Kids find pairs of cells that touch up, down, left or right whose sum, difference or product equals a target number, colour both cells and write the equation on the stamp card. It offers difficulty presets, 1-6 sets per run, two-up A4 sheets with a cut line, a two-player cell battle mode and reproducible seeds, plus a teacher answer page. Fully bilingual (interface and printed page). No build, no network, no dependencies.
category: education
version: 1.0.0
author: 粉笔与代码
homepage: https://github.com/seahp/number-grid-paint
---

# 数格涂涂 · Number Grid Paint

面向一年级（含表内乘法阶段）的**数学游戏卷生成器**。产出一份单文件、离线、可打印的
A4 HTML：浏览器打开即用，不联网、不依赖任何库，界面与纸面中英双语可切。

## 何时使用

- 要"出一张数学涂色游戏""相邻两格凑数"的课堂活动纸
- 要练 10 以内加减法的**和/差**，或表内乘法**积**，或三者混排（孩子先判断用哪种运算）
- 要一次出多份不同题目的卷子（1–6 份），或一张 A4 出两卷裁开
- 要双人课堂对战版（轮流占格，比谁涂得多）
- 要可复现的题（同种子同题），并附老师用的答案页
- 要英文课堂用的版本（本地化措辞，不是逐字翻译）

## 核心文件

| 文件 | 作用 |
|---|---|
| `assets/数格涂涂_生成器.html` | **主产物**。内核（出题+校验）+ 界面 + 版面解算器 + 打印样式 + 双语字典，全在这一个文件 |
| `scripts/verify.mjs` | 独立数学校验。抽取 HTML 里的 KERNEL 段运行，76 项断言 |
| `scripts/env.py` | 其余开发脚本的路径解析（`GRIDPAINT_SRC` / `GRIDPAINT_BROWSER`） |
| `scripts/size_probe.py` | 144 版面组合 × 语言：不溢出、不折行、单元不顶格 |
| `scripts/width_probe.py` | 窗口多宽都解出同一个格子（缩放比折算） |
| `scripts/i18n_probe.py` | 双语：未替换占位符 / 英文单复数 / 漏翻 / 撑爆列 |
| `scripts/pdf_check.py`·`pdf_export.py` | 打印回归（数页数、查空白页）与样张导出 |
| `scripts/shot.py` | 屏显态截图 |
| `scripts/leak_scan.py` | **发布前泄露与脱敏审查**：`git push` / 市场上传 / `publish` 之前必跑，退出码 0 才出门（名单词表在 `scripts/redact_terms.txt`，只留本地，不进包） |
| `references/rules-and-generation.md` | 出题口径与数学红线（**改内核前必读**） |
| `references/layout-solver.md` | 版面解算器：格子多大是怎么量出来的 |
| `references/i18n.md` | 双语架构与加文案流程 |
| `references/verification.md` | 校验脚本清单与交付前整套 |

> 路径说明：本表按**技能包**目录写。放进 GitHub 仓库时主产物就在仓库根的
> `数格涂涂_生成器.html`，命令里的 `assets/` 前缀去掉即可，其余路径不变。

## 工作流

### 1. 直接交付（最常见）

把 `assets/数格涂涂_生成器.html` 复制到用户工作区，用浏览器打开。老师自己点
「换一批」「打印 / 存 PDF」。不需要装任何东西。

```
cp assets/数格涂涂_生成器.html ~/Desktop/数格涂涂_生成器.html
```

### 2. 按用户偏好预置默认值

改 HTML 里的 `var S = {...}` 初始值，省得每次手点：

```js
var S={size:10,mode:'quest',sum:[6,7,8],diff:[2,3],mul:[],quota:3,copies:1,seed:20261111,
  withAns:true,rule:true,hdr:true,stamp:true,foot:true,per:1,cellAdj:0,lang:'zh'};
```

也可以不改文件，直接用地址栏参数生成一条可分享的链接（适合"给我 4 份、一页两卷、
只练 6、7、8 的和"这类要求）：

```
?lang=en&size=10&per=2&copies=4&sum=6,7,8&diff=2,3&quota=3&seed=20261111&ans=1&hdr=1&stamp=1&foot=1&rule=1
?p=std        # 难度包：easy std mid hard m1 m2 m3 mix
```

参数全表见 `README.md`。

### 3. 用命令行批量出 PDF

```
python3 scripts/pdf_export.py '?size=10&copies=4&per=2&lang=zh&seed=20261111' out/课堂4份.pdf
python3 scripts/pdf_export.py '?p=m3&size=8&lang=en&seed=777' out/multiplication.pdf
```

无头导出固定 1440px 视口，避免窄窗口预览缩放干扰量测。

### 4. 改玩法 / 改题目口径

先读 `references/rules-and-generation.md`，改 KERNEL 段，然后：

```
node scripts/verify.mjs                       # 数学红线必须 76/0
python3 scripts/size_probe.py --lang zh
python3 scripts/size_probe.py --lang en
```

内核文案要用 `KM('中文','English')` 包，**不要**在 KERNEL 里调 `T()`（KERNEL 不依赖外面的 `S`）。

### 5. 改版面（字号、栏宽、块间距）

先读 `references/layout-solver.md`。格子大小是**实测解出来的**，不是查表——
所以 `node --check` 通过不代表版面没问题，必须跑浏览器探针：

```
python3 scripts/size_probe.py --lang zh   && python3 scripts/size_probe.py --lang en
python3 scripts/width_probe.py 1440 760 400 lang=zh
python3 scripts/pdf_check.py
```

红线：`异常 0`、`单格横向顶出去的组合 0`、`不一致 0`、`页数`与预期一致。

### 6. 加/改双语文案

先读 `references/i18n.md`。三条硬规矩：

1. `L10N_RAW` 每个 key 两条，顺序固定 `[中文, English]`；
2. 英文带数字的要说单复数，用 `{z}` + `PL(n)`；
3. `applyLang()` 必须在 `sync()` 之前跑（否则 ➕➖ 的手动读数被中文覆盖）。

改完跑 `python3 scripts/i18n_probe.py`（问题 0）。

## 关键口径（别改错）

* **和 ≤ 10**：相加超过 10 不算，纸上也这么写。
* **一格只能用一次**：所以 8×8 最多 32 对、10×10 最多 50 对，超了直接拒答并说明原因。
* **积必须是两个一位数之积**：11 / 13 / 17 / 19 这类永远凑不出，禁止选。
* **勾了乘法，盘内不含 0**：0 乘任何数都是 0，会留一堆死格。
* **同种子 = 同题**，种子印在答案页页眉，老师抄下来就能找回同一套题。
* **版面按 A4 实测**：目标数变少或勾掉页眉/集章表/页脚/说明，空出来的高度真的还给盘面。

## 许可与署名

CC BY-NC-SA 4.0（署名 / 非商业 / 相同方式共享），全文见 `LICENSE.txt`。
转发或改编时请保留 HTML 顶部的许可证注释，并注明出处。
