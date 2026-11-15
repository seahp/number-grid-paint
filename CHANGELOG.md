# 更新记录 CHANGELOG

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 与
[语义化版本](https://semver.org/lang/zh-CN/)。产品本身是单文件 HTML，
它的构建号写在页面状态条末尾（`代码版本 YYYY-MM-DD`），用来识别浏览器里挂着的旧标签页。

## [1.0.1] - 2026-11-15

针对 1.0.0 那轮评测提的两条：**"按说明直接运行检查命令可能找不到文件"** 和
**"发布相关内容不够齐全"**。成品（出题、版面、打印、双语）没动，改的是围绕它的可复现性。

新增

* `references/publishing.md` —— 打包与上架的完整流程（谁进哪个包、两个平台的
  frontmatter 差别、发布前审查、发布后回扫），原来这部分只在仓库里的 `SUBMISSION.md`，
  装完技能包的人看不到。
* `scripts/doc_check.py` —— 文档 ↔ 实际文件一致性检查：把 README / SKILL.md /
  各篇 references 里每条命令和路径抠出来，逐个确认**在文档要被装进去的那个布局里**
  真的存在，并核对 frontmatter 版本与 CHANGELOG 顶部一致。仓库里的 `make_dist.py`
  已把它串进 preflight 与打包尾部，不一致就打不出包。
* `CHANGELOG.md`（本文件）。
* 仓库里的 `assets/preview.png` —— 成品截图，README 与详情页用它代替"口头描述效果"，
  由开发脚本在无头浏览器里截真实页面得到。市场包不收图片文件（实测 SkillHub 400
  "不允许的文件类型"），所以包里那份文档引的是它在 GitHub 上的绝对地址。仓库的
  `.gitignore` 里为它开了例外（`!assets/preview.png`）——否则 `*.png` 会把它静默挡在提交之外，
  线上那条地址就是 404。

修复

* **技能包布局下所有检查命令都报"找不到文件"**：`scripts/env.py` 与
  `scripts/verify.mjs` 原来只认"HTML 在 `scripts/` 上一层"的仓库布局，而技能包把主产物
  放在 `assets/` 下，于是 `node scripts/verify.mjs` 报 ENOENT、
  `python3 scripts/size_probe.py` 报"找不到生成器 HTML"。现在两种布局自动探测
  （仓库根 → `assets/` → 通配兜底），`python3 scripts/env.py` 会顺便打印它认到了哪种布局。
* **文档提到包里根本没有的脚本**：`gap_probe.py`、`half_probe.py` 现在随包发出；
  `make_dist.py` 明确标成"只在开发仓库里跑"（它会整目录清空 `dist/` 再重建，
  放进用户目录里跑是有害的），文档里凡提到它的行都带"仓库"字样。
* **市场按 SKILL.md 机械解析路径，缺文件即驳回**：WorkBuddy 开放平台 2026-11-15 的驳回
  原文是「资产包缺少必需资源 1 项：文件 `scripts/pdf_export.py`（SKILL.md 引用）」。
  现在同一份源文档按布局分叉渲染（`lite:skip` / `lite:only` 标记），出包前逐行验两个包，
  精简包里那份 SKILL.md 只剩包里真有的东西。
* **`leak_scan.py` 扫了个空却报"干净，可以发布"**：传了不存在的路径时以前会被静默跳过。
  现在显式路径不存在直接退出码 1；默认目标 `dist/` 不在（技能包就是这种情形）就改扫当前
  目录树，并在一条都没扫到时判失败——空扫描不算通过。
* **技能包里跑 `leak_scan.py` 会提示"不要发布"**：脱敏名单词表按设计只留在开发机
  （它本身就是敏感词集合），包里本来就没有。现在这种情形降为一句说明，
  通用规则 0 命中即通过。
* **包内媒体成员（截图/字体）以前一律报"需人工确认"**：现在已知图片/字体后缀登记为
  说明项并列出文件名，未知后缀仍按可疑二进制报警。

已知限制

* 版面探针（144 组版面 × 语言、12 组 PDF 页数）要本机装有 Edge/Chrome，
  没有浏览器时 `scripts/env.py` 会给出一句可操作的提示而不是 traceback。
* 导出 PDF 的脚本同样需要无头浏览器；只想出卷的话，直接双击 HTML 用浏览器打印即可，
  不需要跑任何脚本。

## [1.0.0] - 2026-11-15

首个对外版本。GitHub、SkillHub、WorkBuddy 开放平台三处同步，全部**免费**，
许可证 CC BY-NC-SA 4.0。

* 出题内核：10×10 / 8×8 数盘，和 / 差 / 积三种目标，先植桩保证有解；
  同卷目标对互不重叠；`audit()` 自检；同种子必出同题。
* 版面：A4 实测解算（格子边长二分搜到纸装得下的最大值），一页一卷 / 一页两卷裁开，
  页眉 / 集章表 / 页脚 / 玩法说明四个可选块，➕➖ 手动微调，1–6 份批量。
* 双语：界面与纸面都切中英文，英文按英语课堂习惯本地化改写。
* 校验：`verify.mjs` 76 项数学断言，`size_probe.py` / `width_probe.py` /
  `i18n_probe.py` / `pdf_check.py` 四路版面与语言回归。
* 发布物料：仓库里的 `make_dist.py` 一份源码出三个平台的产物，两个平台各重写 frontmatter；
  泄露与脱敏审查 `leak_scan.py` 串进出门前后的两道闸门。
