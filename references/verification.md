# 校验与回归（verification）

分两层：**数学红线**不依赖浏览器，任何机器上都能跑；**版面/双语回归**要一个能无头运行的
Edge 或 Chrome（路径由 `scripts/env.py` 解析，`GRIDPAINT_SRC` / `GRIDPAINT_BROWSER` 可覆盖）。

## 0. 最快的一层：语法 + 数学

```bash
# 把 <script> 段抽出来做语法检查（页面跑不跑得起来，这一步先兜住）
sed -n '/<script>/,/<\/script>/p' 数格涂涂_生成器.html | sed '1d;$d' > /tmp/gk.js && node --check /tmp/gk.js

node scripts/verify.mjs            # 76 项断言
```

`verify.mjs` 用 `node:vm` 直接加载 HTML 里 `KERNEL START/END` 之间那段，
**校验的就是页面在用的那份逻辑**，不是副本。覆盖：

* 网格与相邻边数（`2·size·(size−1)`）、棋盘二分性；
* 三种运算的判等、`factorPairs` / `isMulTarget`（11/13/17/19 必须不可选）；
* `maxMatching` 与容量上限（8×8 = 32 对、10×10 = 50 对）；
* `checkJob` 的拒答边界（和 >10、差 >9、积凑不出）；
* `plant` + `buildBoard`：同种子可复现、目标对互不重叠、`audit()` 全过；
* 大配置压力测试（10×10 和+差+积 12 目标 × 3 对 = 36 对，40 个种子 0 拒答 0 自检失败）。

KERNEL 段以外的排版/打印代码 `verify.mjs` 看不见，靠下面的浏览器探针。

## 1. `size_probe.py` — 版面矩阵（144 组合 × 语言）

```bash
python3 scripts/size_probe.py [--set sd|mul] [--mode quest|duel] [--quota 13|24] [--lang zh|en]
```

在页面里循环改 `S.*` 后 `render()`，每个组合记：每格 mm、`over`、`TOLF`、`FIT`、
四边墨位、盘面尺寸，并统计两类红线：

* **异常** — `over > max(0.2, TOLF)`，即这页真装不下；
* **单格横向顶出去**（`ovf`）— 表格单元 `scrollWidth > clientWidth`。
  `overPct()` 看不见它：内容没超出版心，只是压到隔壁列，一犯就折行、行高翻倍、盘面被压到下限。

`--set mul` 跑乘法目标集，`--quota 24` 跑每目标 2/4 对，`--mode duel` 跑双人抢格。
**改任何字号、内边距、栏宽都要把 zh + en 两套都跑成 异常 0 / 顶格 0。**

## 2. `width_probe.py` — 窗口宽度无关性

```bash
python3 scripts/width_probe.py 1440 760 400 lang=en
```

同一批 16 个配置分别在三档视口宽度下解版面，**每格 mm / FIT / STG / 余量必须完全一致**
（k=1.00 / 0.91 / 0.58）。≤900px 时屏显预览会 `scale(k)`，这条专门盯缩放比折算。

## 3. `i18n_probe.py` — 双语四项检查

```bash
python3 scripts/i18n_probe.py
```

8 组版面 × zh/en = 16 次无头加载，查：

1. **未替换的 `{占位符}`** — 模板写 `{n}`、调用传 `{no}` 这类错配（`setWord` 就踩过，
   纸面直接印出 "Set {n}"）；
2. **英文单复数** — `1 sets` / `2 pair`（数字常包在 `<b>` 里，所以按 `innerText` 查而不是文本节点）；
3. **英文态漏翻** — 渲染文本里还有汉字（`#segLang` 上的"中文"是故意的，整块跳过）；
4. **撑爆列** — `th/td` 的 `scrollWidth > clientWidth`。

## 4. `pdf_check.py` / `pdf_export.py` — 打印回归

```bash
python3 scripts/pdf_check.py                                  # 12 组（6 zh + 6 en）
python3 scripts/pdf_export.py '?size=10&lang=en' out/样张.pdf  # 单独导一张
```

`pdf_check` 无头打印成 PDF，**跟着页面字典的 `/Contents` 走**逐页取内容流解压，
数页数并找出空白页（小于 2KB 的页）。为什么不能把所有 stream 一起解压：会混进字体、
对象子集之类十几字节的小流，看不出到底哪一页是空的。
页数不对 = 英文说明变高后挤出了第二页，这条就是抓这个的。

`pdf_export` 固定 1440px 视口导出，避免窄窗口命中 `scale(.5)` 预览规则时量测算出假溢出、
把格子压到 5.6mm 下限、导出的 PDF 跟着一起小。

## 5. `shot.py` / `gap_probe.py` / `half_probe.py` — 看图与量块

```bash
python3 scripts/shot.py out/名字.png '?size=10&lang=en' [all|answer|student]
```

屏显态截图（视口要 >900px，否则命中缩放预览规则）。`gap_probe` / `half_probe` 是量
块间距和半页布局的一次性工具，改动版式时用来定位"哪两块之间空了 6mm"。

## 6. 交付前的整套（2026-11-15 实测结果）

```
node --check                OK
verify.mjs                  76 项通过 / 0 失败
size_probe  (sd|mul × quest + duel) × quota 13|24 × zh|en
                            12 次 × 144 = 1728 组合   异常 0，顶格 0
                            （"生成失败 12~36" 是容量不足的目标组合，版面不参与量测，正常）
width_probe 1440/760/400 × zh|en               配置 16 不一致 0
i18n_probe  8 配置 × zh|en                       问题 0
pdf_check  12 组（6 zh + 6 en）                   异常 0，无空白页
leak_scan  源码侧 + 发布物 + 线上包                 0 命中（第 8 节，发布前必跑）
```

`size_probe.py` 现在把选项取值写死校验：`--set duel` 这种串了 flag 的写法以前只甩一个
`KeyError: 'duel'`，现在直接说「duel 是 --mode 的取值，flag 写串了」——全量扫描要跑十几次，
静默少跑一套矩阵比报错更难发现。

## 7. `make_dist.py` — 发布物料与出门闸门（仓库专用）

```bash
python3 scripts/make_dist.py            # 仓库里跑：出 dist/（占位署名之类只提示，不拦）
python3 scripts/make_dist.py --strict   # 仓库里跑：提交前最后一次，待办升级成阻断
python3 scripts/make_dist.py --samples  # 仓库里跑：顺带用无头浏览器导两张样张 PDF
```

它先跑 preflight，再产出 `dist/repo/`（GitHub 仓库）、`dist/skill/…`（SkillHub 包，含探针脚本）、
`dist/skill-lite/…`（开放平台包，只有 HTML + 文档）和两个 zip。

preflight 拦的是这四类，**都不是"看着不顺眼"，是真会让上架失败或让用户踩坑**：

| 检查 | 为什么 |
| --- | --- |
| `LICENSE.txt` 是 CC BY-NC-SA 4.0 全文 | 平台填的许可字段得和包里的文本对得上 |
| README / SKILL / HTML / `.gitignore` 存在 | 少一个就是残缺包 |
| HTML 里无网络请求、无外部脚本 | "离线可用"是卖点，一条 `fetch(` 就把它废了 |
| `KERNEL START/END` 在位 + `verify.mjs` 0 失败 | 内核段被误删的话，收件人无法复核数学 |
| frontmatter 含 SkillHub 15 字段 / 开放平台 9 字段 | 少字段平台直接"解析失败"（`--strict` 还查占位署名） |
| **泄露与脱敏审查**（源码侧 + 包内字节，见第 8 节） | 功能全绿也照样能把本机路径、邮箱、真实班级数据推出去 |

zip 用 `zipfile` 手写而不是 `shutil.make_archive` / `ditto`：时间戳固定、`extra` 清空、
跳过 `.DS_Store` 与 `__MACOSX`，所以重复打包字节一致，也不会带 macOS 的 AppleDouble 条目
（班级管理工作台那轮就是被这个坑过）。开放平台按**解压后**字节数卡 3MB，脚本会把两个数都打出来。

zip 出门后还能让平台自己再判一次 metadata（不联网、不上传）：

```bash
~/.local/bin/skillhub --skip-self-upgrade publish dist/number-grid-paint-skillhub.zip --dry-run
# ✓ Dry-run passed: number-grid-paint@1.0.0
```

提交步骤（三个平台各一段）和当前发布状态在仓库根 `SUBMISSION.md`。

```
make_dist --strict            preflight 通过（100 KB 单文件 / 76 项 / frontmatter 15+9 字段齐）
                              泄露与脱敏审查：源码侧 0 命中，发布物 0 命中
skillhub zip                  100 KB（解压后 225 KB，17 文件，含 leak_scan.py）
                              —— 两个包的解压后字节数会随文档增删浮动 1 KB 量级，别当回归信号
openplatform zip              70 KB（解压后 163 KB，8 文件，extra field 0）
skillhub publish --dry-run    ✓ Dry-run passed: number-grid-paint@1.0.0
```

## 8. `leak_scan.py` — 发布前的泄露与脱敏审查（纪律，不是可选项）

**规矩：`git push`、市场上传、`skillhub publish`、把链接发给人——之前都要跑它，
退出码 0 才出门。** 起因是班级管理工作台那轮：已公开仓库里混进过未脱敏的本班学生数据，
而当时所有功能测试全绿——测试只测功能，不测隐私。

```bash
python3 scripts/leak_scan.py                 # 默认 dist/：三份目录 + 两个 zip 的包内字节
python3 scripts/leak_scan.py dist/repo       # push 前只扫要推出去的那份
python3 scripts/leak_scan.py --strict        # 名单词表没声明也算失败
```

十类通用痕迹：本机家目录、他人/本机用户目录、账号名、邮箱、手机号与固话、身份证号、
token 与私钥（`ghp_`/`github_pat_`/`skh_`/`sk-`/`AKIA`/`xox*`/`ya29.`/`ntn_` 与硬编码口令）、
带凭证的 URL、UUID、教育类 PII 字段名。
第十类之外还有 仓库里的 `scripts/redact_terms.txt`：**只有你知道不能公开什么**——真实人名、班级、
校名、内部代号，一行一个词，命中就报。这份词表本身是敏感信息集合，所以它不进任何发布物，
仓库里的 `make_dist.py` 出门前专门检查它有没有混进包里。

三个设计上的讲究，都是踩过之后加的：

- **命中行只打印前 6 个字符 + 长度**，不把疑似密钥或证件号原样贴进终端，
  否则这个审查自己变成第二次泄露。
- **豁免可审计**：规则的字面量会扫到自己（`leak_scan.py` 就被自己命中两次），
  行尾写 `# 审查例外：<理由>` 才跳过；理由 grep 得到，不是"把规则关掉"。
- **全绿要自证**：偶尔跑一次负向自测——把公开署名塞进词表应当命中，
  伪造一份含用户目录、手机号、`ghp_` 令牌的临时文件应当命中 4 类。

```
dist/ + 两个 zip + 线上下载回来的包     0 命中
负向自测（注入名单词 / 伪造泄露文件）    3 处 / 4 类，规则会咬人
```

线上那份也要扫：`skillhub install` 到临时目录后 `python3 scripts/leak_scan.py <临时目录>`，
扫的是平台实际存下来的字节，不是你以为发出去的那份。
2026-11-15 扫过线上 1.0.0：0 命中，签名与内容指纹一致 → **不重发**（审查没问题就不动线上，
本地多出的审查工具等下次真改版时随包带上）。

