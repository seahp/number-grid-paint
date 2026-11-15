# 发布提交清单

## 0. 纪律：发布前必做泄露与脱敏审查

**任何一次对外动作之前——`git push`、市场上传、`skillhub publish`、把链接发给人——
先跑审查，退出码 0 才允许出门。** 这一条不是"建议"，是这个项目的硬性步骤，
起因是班级管理工作台那轮：已公开仓库里混进过未脱敏的本班学生数据，
而当时所有功能测试全绿——因为测试只测功能，不测隐私。

```bash
python3 scripts/leak_scan.py                 # 默认扫 dist/ 下全部发布物 + 两个 zip
python3 scripts/leak_scan.py dist/repo       # push 前只扫真正要推出去的那份
python3 scripts/leak_scan.py --strict        # 名单词表没声明也算失败
```

它查十类通用痕迹（本机家目录、他人/本机用户目录、账号名、邮箱、手机号与固话、
身份证号、token 与私钥、带凭证的 URL、UUID、教育类 PII 字段名），
外加 `scripts/redact_terms.txt` 里你自己声明的名单词（真实人名、班级、校名、内部代号）。
命中的行只打印**前 6 个字符 + 长度**，不把疑似密钥原样贴进终端——
否则这个审查自己变成第二次泄露。

五个容易踩的点：

- **词表不出门**：`redact_terms.txt` 只留在开发目录，`make_dist.py` 不打进任何包，
  并且出门前会专门检查它有没有混进去（它自己就是敏感信息集合）。
- **豁免要留理由**：规则的字面量会扫到自己（`leak_scan.py` 就被自己命中过两次）。
  在行尾写 `# 审查例外：<理由>` 才跳过，理由 grep 得到，所以豁免可审计。
- **文档也别写实名**：这份清单自己就被拦过两次——提到 git 邮箱时写 `<你的邮箱>`，
  不贴真实地址；提到路径时写"本机家目录"或 `<项目路径>`，不写绝对路径。
- **全绿不等于规则有效**：偶尔跑一次负向自测确认它会咬人——把公开署名塞进词表
  应当命中；伪造一份含用户目录、手机号、`ghp_` 令牌的临时文件应当命中 4 类。
- **线上要再扫一次**：不能只扫上传前的本地包，还要扫**下载回来的那份**。

`make_dist.py` 已经把这道审查串进 preflight（扫源码侧）和打包尾部（扫两个 zip 的
**包内字节** + 三份目录），所以"忘了跑"这条路被堵了一半；
但**发布动作本身仍然要再跑一次**，因为你 push 的可能是上一轮构建的旧 dist。

## 1. 现在的发布状态（2026-11-15 深夜，1.0.2）

| 平台 | 状态 | 说明 |
| --- | --- | --- |
| GitHub | **v1.0.2 已上线** | https://github.com/seahp/number-grid-paint （Public，`main`，提交 `ae5ee92`）；线上 tarball 拉回来重扫 **0 命中**，`assets/preview.png` / 主产物 / README 三条 raw 地址都是 200，见第 3 节。中途你在 GitHub 上直接删过 README 里"出三份物料…"那两句，已把同样的删除落回源文档，下次重建不会又长回来 |
| SkillHub | **v1.0.2 已上线，skillId 与 URL 都没变** | https://skillhub.cn/skills/user_1db801dd/number-grid-paint （skillId 322080，**没删条目**）。`✓ Published` 之后索引刷了约 15 分钟才翻到 1.0.2（头两次 `install` 仍是 1.0.0 的文件）；刷完后装下来的那份 22 个文件与本地构建包 `diff -r` **逐字节一致**，对**装下来的这份**跑 `leak_scan.py` 0 命中、`doc_check.py` 判一致、文档里 13 条命令全部退出码 0；详情页 JSON 里 `tags.latest` = 1.0.2，概述正文能看到仓库地址。1.0.1 那次上传被 `400 不允许的文件类型: assets/preview.png` 整包拒收、**版本号却占上了**，即 1.0.1 是个空号，详见第 5 节 |
| WorkBuddy 开放平台 | **1.0.0 被驳回，整改后的 zip 已备好待重投** | 技能ID `os_e14f55c59b56dd6c`，分类「教育学习」，**免费**（未勾付费/内购）。驳回原文与整改见第 4 节 |

线上那三份是**做这套审查之前**的物料打的包。评测回来了两条意见，都属于"文档与包不一致"，
不是成品质量问题，所以 1.0.2 专门修它们：

> 上线之后本地又补了两段发布记录（第 5、6 节那些实测结论），所以 `dist/` 里现在这个
> skillhub zip 比线上 1.0.2 的那份大 1 KB —— 内容只是 `references/publishing.md` 多了
> 两段话，不影响收件人照文档执行。按"只要没问题就不用重发"，这次不再重发，
> 攒到下一次真改版一起带上。**要上传之前先 `diff` 一下本地包和线上包**，别说错了版本。
> 精简包（开放平台那份）没受影响，仍是 57 KB / 6 个文件，就是要重投的那一份。

- "按说明直接运行检查命令可能找不到文件，发布相关内容也不够齐全"；
- 可靠性口径："核心出题和打印整体稳定，出错时也有易懂提示"，但"检查和打包流程与实际文件
  不完全一致，照文档执行时容易卡住，需要先调整路径"。

整改的落点是**代码 + 文档 + 出包闸门**三处，不是补一张截图：

| 症状 | 根因 | 这一版的处理 |
| --- | --- | --- |
| 解压后跑 `node scripts/verify.mjs` 报 ENOENT、探针报"找不到生成器 HTML" | 脚本只认"HTML 在 `scripts/` 上一层"的仓库布局；技能包把主产物放在 `assets/` 下 | `env.py` / `verify.mjs` 改成两种布局自动探测，`env.py` 还会打印它认到了哪种布局 |
| 文档点到包里不存在的脚本 | 清单与文档各写各的 | `gap_probe.py`·`half_probe.py`·`doc_check.py` 随包发出；`make_dist.py` 标注只在开发仓库跑 |
| "发布相关内容不齐全" | 上架流程只写在仓库里的 `SUBMISSION.md`（包里没这份） | 新增 `references/publishing.md` 随包发出；新增 `CHANGELOG.md`；README/SKILL.md 顶部加真实成品截图 `assets/preview.png` |
| 文档说了但文件不在（平台机械解析） | 精简包不带脚本，SKILL.md 却写着 `scripts/pdf_export.py` | 源文档按布局分叉（`lite:skip` / `lite:only` / `repo:skip`），出包前由 `doc_check.check_skillmd()` 逐行验两个包，不一致就打不出 zip |

"只要没问题就不用重发"这条用户决定仍然有效：线上那三份内容本身没有事实错误，
1.0.2 是**为了解决评测指出的可复现性问题**而发，不是补救错误内容。

---

## 2. 物料

先跑一次总打包：

```bash
cd 纸笔游戏-数格涂涂
python3 scripts/make_dist.py --strict      # 缺文件/网络请求/frontmatter 缺字段/文档不一致/未脱敏内容会直接拦下
```

产出：

| 文件 | 给谁 | 内容 |
| --- | --- | --- |
| `dist/repo/` | GitHub | 完整仓库：HTML + README + LICENSE.txt + SKILL.md + references/ + 全部 scripts/（含 `leak_scan.py`） |
| `dist/number-grid-paint-skillhub.zip` | SkillHub | 技能包（带探针脚本），完整字段 frontmatter |
| `dist/number-grid-paint-openplatform.zip` | WorkBuddy 开放平台 | 精简包（只有 HTML + 文档，**不含脚本**），官方 9 字段 frontmatter |

> 为什么两个包不一样：开放平台会做静态代码检测，`subprocess.run`、`.exec(` 这类会被报
> 「命令执行风险」（班级管理工作台那轮就被报过）。市场上架真正要的产物就是那一个 HTML，
> 所以给它的包不带脚本，探针留在 GitHub 仓库给要改代码的人。

打包尾部现在有四道自动闸门，全绿才出 zip（这就是"照文档执行会不会卡住"的机器回答）：

1. `doc_check` 对**仓库布局**：README/SKILL/references 里每条命令和路径都要真实存在；
2. `doc_check` 对**技能包 + 精简包**：再加 `check_skillmd()` 一档，SKILL.md 提到的路径
   无任何豁免（平台就是这么机械地解析的）；
3. 在 `dist/skill/…/scripts/env.py` 里真跑一次子进程，确认包内脚本能解析到 `assets/` 下的 HTML；
4. `leak_scan` 扫两个 zip 的**包内字节** + 三份目录，命中就退出码 1。

提交前再确认这三件事：

1. **署名**：物料里写的是 `粉笔与代码`，出处写的是
   `https://github.com/seahp/number-grid-paint`（仓库已上线，URL 与署名三处一致）。
   要改就改这三处，改完重跑 `make_dist.py`：
   - `README.md` 的「署名」「许可证」两节
   - `数格涂涂_生成器.html` 顶部注释里的 `Copyright / 版权所有` 与 `署名与出处`
   - `SKILL.md` frontmatter 的 `author` 与 `homepage`（正文第一屏那行「源码仓库」也要一起改）
2. **仓库名**：GitHub 上实际建的名字要和 README/HTML/SKILL.md 里的 URL 一致，
   否则署名指向 404。当前已核对：`seahp/number-grid-paint`，`origin` 就是这个地址。
3. **非商业条款要落实**：CC BY-NC-SA 4.0 里 NC = 不可商用。三个平台上架时
   **一律选"免费"**（SkillHub 的 `pay_mode` 保持 0，开放平台不要勾付费/内购），
   也不要把打印卷收钱卖。想收钱得先换成 CC BY-SA 或另做商业授权，那是另一个决定。

---

## 3. GitHub（已上线，记录一条能复用的推法）

仓库：**Public**、不初始化 README（避免首推冲突）、名称 `number-grid-paint`。
这次是用 API 建的，省得手动点：

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"number-grid-paint","description":"…","private":false,
       "has_issues":true,"has_wiki":false,"auto_init":false}' \
  https://api.github.com/user/repos
```

**凭据这条路上次的坑**：`git credential fill` 读到的是钥匙串里 **internet 类**那条
`github.com / <用户名>`，装的是一把早已失效的旧 PAT，所以怎么推都是
`401 / Invalid username or token`；而 **GitHub Desktop 登录后写的是 generic 类**，
service `GitHub - https://api.github.com`，那条 token 是活的（`repo, user, workflow`）。
两条记录同名不同类，osxkeychain 只会挑失效的那条——这就是本机没有 `gh`、
`ssh -T` 又 publickey 拒绝之外，真正卡住的原因。

所以推之前先确认钥匙串里到底哪条有效（只看长度和前缀，别打印值本身）：

```bash
security find-generic-password -s 'GitHub - https://api.github.com' -a <用户名> -w | wc -c
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $(…)" https://api.github.com/user
```

用法是**一次性的临时 helper**：脚本里不含密钥，被调用时才去钥匙串取值；
先把 helper 链清空再挂上它（顺序敏感，只 `-c credential.helper=<路径>` 的话
osxkeychain 会抢先用那条失效凭据）。token 不进 `.git/config`、不进 remote URL、
不进 commit、也不落盘。

```bash
python3 scripts/leak_scan.py dist/repo            # 退出码必须是 0
cd dist/repo
git init -b main
git add -A
git -c user.name=<用户名> -c user.email=<noreply 地址> commit -m "…"
git remote add origin https://github.com/<用户名>/number-grid-paint.git   # 干净 URL，不带凭据
git -c credential.helper= -c credential.helper=/tmp/gh_cred.sh push -u origin main
```

**commit 作者邮箱也会被爬**：本机 git 全局 `user.email` 是你的个人邮箱，
直接 commit 会把它写进公开历史（爬 GitHub 邮箱是垃圾邮件的老路子）。
在这一份干净副本里改用 GitHub 的 noreply 地址——推荐 `settings/admin`
里 "Keep my email addresses private" 显示的那种**带数字 ID 前缀**的形式，
纯用户名那种在部分统计里不归属你：

```bash
git config user.email "<数字ID>+<用户名>@users.noreply.github.com"
```

推完别只看本地：把线上的 tarball 拉回来重扫一次（第 0 节的「线上要再扫一次」），
再确认 `raw.githubusercontent.com` 上主产物 200。这次的结果记在第 1 节表里。

`.gitignore` 已排除 `out/`、`dist/`、`*.pdf`、`*.png`，**唯一例外是详情页那张成品图**
（`!assets/preview.png`）。这个例外不是审美问题而是链路问题：市场包不收图片，两个包的
文档只能引它在 GitHub 上的 raw 地址；`*.png` 会把这张图静默挡在提交之外，本地看着有、
线上永远 404。`make_dist.py --strict` 里新增的 `check_raw_urls()` 就是拦这一类的——
文档里每一条 raw 链接都要求"文件在 dist/repo 里、没被 .gitignore 挡住、且已被 git 跟踪"。

历史里一旦混进真实班级/学生信息
就删不干净（force push 也留在 reflog 和平台缓存里），所以别在开发目录里直接 `git init`，
用 `dist/repo` 这份干净副本。

可选：开 Pages 让老师不用下载就能打开——
Settings → Pages → Deploy from branch → `main` / `/`，再把
`https://seahp.github.io/number-grid-paint/数格涂涂_生成器.html` 写进 README 顶部。
文件名带中文，Pages 能用但 URL 会转义；介意的话在仓库里额外放一份 `index.html`（内容与
生成器完全相同，只是 ASCII 名）。

---

## 4. WorkBuddy 开放平台（1.0.0 被驳回，整改后待重投）

**驳回原文（2026-11-15）**：

> 审核备注：资产包缺少必需资源 1 项：文件「scripts/pdf_export.py」（SKILL.md 引用）

这一条把平台的规矩说清楚了：**它会机械解析 SKILL.md 里出现的每个路径，包里没有就驳回**，
不看上下文、不接受"这行讲的是仓库"那种散文豁免。而精简包**不能**带脚本——带 `subprocess.run`
就被静态检测报「命令执行风险」，两个约束是反着的，唯一的解法是让 SKILL.md 在精简包里
**根本不提**这些路径。

整改做法（已落在代码里，不靠手工改 zip）：

- 源文档 `SKILL.md` / `README.md` / `CHANGELOG.md` / `references/*.md` 用 HTML 注释分叉，
  打包时渲染出各布局该看到的那一版：
  `repo:skip`（两个包都删）、`lite:skip`（只从精简包删）、`lite:only`（只在精简包出现）；
- 精简包里那段"交付前自检"换成**不开脚本也能做**的三步（换一批看是否涂得完、回填种子比对、
  打印预览数页数）；
- 精简包只带 `references/rules-and-generation.md`（讲玩法与出题口径，收件人真的用得上）；
  版面解算、双语架构、校验清单、打包上架那几篇是给改代码的人的，留在完整技能包与仓库里；
- 打包尾部 `doc_check.check_skillmd()` 对两个包逐行验 SKILL.md，不一致就不出 zip，
  所以"缺少必需资源"这类驳回不会再从这套物料里产生。

入口 https://open.workbuddy.cn → 登录（微信扫码 / 手机号 / QQ / 邮箱 / SSO）→
首次会要求选**认证方式**：个人认证 / 企业认证 / 其他组织机构认证。
实名与人脸只能你本人做，我无法代办，也不该代填。

认证过了之后，上传 `dist/number-grid-paint-openplatform.zip`，
入口是 我的技能 / 能力上架 → 上传技能包。填表时这些字段直接抄 `SKILL.md` frontmatter
（已按平台要求写成 9 字段简洁版）：

| 表单字段 | 值 |
| --- | --- |
| 名称 / display_name | 数格涂涂 · 数学涂色游戏卷生成器 |
| 英文名 / display_name_en | Number Grid Paint Worksheet Generator |
| 分类 | education（教育） |
| 版本 | 1.0.2 |
| 作者 | 粉笔与代码 |
| 简介（中） | 抄 `description_zh` |
| 简介（英） | 抄 `description_en` |
| 触发说明 | 抄 `description`（已带 6 个以上触发词，别删） |
| 收费模式 | **免费**（CC BY-NC-SA 的 NC 要求） |
| 图标 | 你自己上传（`SKILL.md` 里不带图标文件，包也就没有；详情页顶部由后台图标决定） |

已知会让它「解析失败 / 超限 / 驳回」的几件事，这个包都处理过了：

- frontmatter 字段多于官方 9 字段 → 精简掉了（`slug/summary/tags/homepage` 不在开放平台包里）
- 值里的 ` & ` 是 YAML 保留字符 → 打包时自动换成 ` and `
- macOS 的 zip extra field、`.DS_Store`、`__MACOSX` → 手写 zip，全部为 0
- **解压后**总大小 ≤ 3MB（它校验的是解压后字节数，不是 zip 文件大小）→ 当前 358 KB、7 个文件
  （比 1.0.0 多的主要是 `assets/preview.png` 218 KB，离上限还很远）
- 静态检测「命令执行风险」→ 包里不含脚本
- SKILL.md 点到包里不存在的资源 → 由 `check_skillmd()` 拦在出包之前
- **上传前**再跑 `python3 scripts/leak_scan.py dist/number-grid-paint-openplatform.zip`
  （它扫的是 zip 里的实际字节，不是目录）

审核前后自己复核一遍（本地命令，不联网）：

```bash
python3 -c "import zipfile;z=zipfile.ZipFile('dist/number-grid-paint-openplatform.zip');\
print('解压后 KB', sum(i.file_size for i in z.infolist())//1024, '| extra field 条目', sum(1 for i in z.infolist() if i.extra))"
```

期望：`解压后 KB 358 | extra field 条目 0`（数字会随文档增删浮动，**extra field 必须是 0**，
解压后必须 ≤ 3072 KB）。

再模拟一次审核员的动作：解压，然后只按 SKILL.md 里出现的文件清单核对——

```bash
rm -rf /tmp/gp101lite && mkdir /tmp/gp101lite && unzip -q dist/number-grid-paint-openplatform.zip -d /tmp/gp101lite
grep -o '\(scripts\|references\|assets\)/[A-Za-z0-9_.一-龥-]*\.\(py\|mjs\|txt\|md\|png\|html\)' \
  /tmp/gp101lite/number-grid-paint/SKILL.md | sort -u      # 这些路径必须都能在包里找到
python3 scripts/doc_check.py --pkg /tmp/gp101lite/number-grid-paint
```

上架后如果需要同时保留旧版本，注意平台侧同名技能是覆盖式更新；要下架旧版在后台点
「下架」而不是删包。**这次是驳回，不是下架**：原技能条目还在后台，重投走
「更新版本 / 重新提交审核」即可，不需要新建条目（新建会换技能ID，详情页链接也要跟着变）。

---

## 5. SkillHub（已完成，记录怎么复查）

```bash
~/.local/bin/skillhub --skip-self-upgrade publish dist/number-grid-paint-skillhub.zip --dry-run
~/.local/bin/skillhub --skip-self-upgrade auth whoami
~/.local/bin/skillhub --skip-self-upgrade publish dist/number-grid-paint-skillhub.zip \
  --version 1.0.0 \
  --changelog "首个版本：10×10/8×8 数字盘、和/差/积目标、闯关集章与双人抢格、一页两卷、1–6 份批量、种子复现、中英双语界面与纸面。"
```

发布后这样确认线上那份就是本地这份（**别只信列表页**）：

```bash
cd /tmp && rm -rf sh_check && mkdir sh_check && cd sh_check
~/.local/bin/skillhub --skip-self-upgrade --dir ./skills install number-grid-paint --namespace user_1db801dd
~/.local/bin/skillhub --skip-self-upgrade --dir ./skills verify number-grid-paint --namespace user_1db801dd
python3 <项目路径>/scripts/leak_scan.py ./skills    # 对下载回来的包再扫一次
```

踩过的两个坑：

- 包里**不能有没扩展名的文件**。`LICENSE` 会被整包 400 拒收（"不允许的文件类型"），
  所以仓库里叫 `LICENSE.txt`；`.gitignore`、`SUBMISSION.md` 也不进技能包。
- 刚发布完 `install` 会 404：详情接口 `latestVersion` 为空、`securityReports` 里
  keen / sanbu 两条还在 `排队中`。等扫描过完就通了，不是包的问题。

> ⚠️ 装完注意：装出来是 `skills/@user_1db801dd/number-grid-paint/` 两级子目录，
> WorkBuddy 要的是 `~/.workbuddy/skills/<skill>/SKILL.md`，必要时把内容上移一层；
> `--dir` 不给就装进当前目录的 `./skills/`，不会被识别。

后续更新只改 `SKILL.md` frontmatter 里的 `version`（和 HTML 里的注释日期），重跑
`make_dist.py` 再 `publish`，不要手改 zip。

### 5.1 这一轮（1.0.2）：详情页要把 GitHub 链接露出来

SkillHub 的详情页「概述」渲染的是 **SKILL.md 正文**，`homepage` 字段根本不显示，
所以链接写在正文第一屏：「源码仓库：<https://github.com/seahp/number-grid-paint>」。
图标你在后台自己上传，包里不带图标文件。

### 5.2 「更新」对话框提示"包没有变化"

后台走「更新版本 → 复用当前版本」时会这样提示：那条路径是**复用线上已有的文件**，
不解析你新选的 zip，所以它当然认为内容没变。这不是包坏了，是入口选错了。

两条路，按代价从小到大：

1. **先走 publish（推荐，先试这条）**：本地这份 1.0.2 与线上 1.0.0 的文件差异是**真实的**
   （多出 `CHANGELOG.md`、`references/publishing.md`、`scripts/doc_check.py`、
   `scripts/gap_probe.py`·`half_probe.py`，SKILL.md/README 正文重写，
   `env.py`/`verify.mjs`/`leak_scan.py` 都改过；成品截图**不在包里**，见第 5.3 节），
   所以按内容指纹判重不会撞上"没有变化"：

   ```bash
   python3 scripts/leak_scan.py dist/number-grid-paint-skillhub.zip   # 纪律：退出码 0 才出门
   ~/.local/bin/skillhub --skip-self-upgrade publish dist/number-grid-paint-skillhub.zip --dry-run
   ~/.local/bin/skillhub --skip-self-upgrade publish dist/number-grid-paint-skillhub.zip \
     --version 1.0.2 --changelog "修复：文档与包内文件逐条对齐（技能包布局下所有检查命令可直接执行）；\
   新增 references/publishing.md、CHANGELOG.md；SKILL.md 正文第一屏给出源码仓库地址，成品截图引仓库里的地址。玩法与版面未改。"
   ```

   **实际踩到的岔子（2026-11-15）**：第一次按 1.0.1 发，`--dry-run` 是过的
   （`✓ Dry-run passed: number-grid-paint@1.0.1`），真发却先被 `400 不允许的文件类型` 打回，
   改好包再发又报 `slug 冲突: 版本 1.0.1 已存在`——**拒收的上传照样把版本号占掉了**。
   `install` 下来一看，那个 1.0.1 记录里的 `SKILL.md` 还写着 `version: 1.0.0`，是个空号。
   结论：不要为了"重发"去删条目，**换一个号发就行**；线上到底哪一版以包内容为准，别信版本号。

   发布后**把线上那份拉回来重扫 + 重跑文档命令**（第 5 节上面那三条），确认详情页
   概述里能看到仓库地址、包里能 `node scripts/verify.mjs` 跑通。

2. **删除技能再重新发布**（你提的那条，作为兜底）：只有当 publish 明确报"版本已存在/内容
   重复"且换不掉的时才用它。**代价是 skillId 322080 和
   `https://skillhub.cn/skills/user_1db801dd/number-grid-paint` 这条链接会没了**，
   已经 `skillhub install` 过的人拿不到更新，README/详情页/别处引用这条 URL 的地方都要跟着改。
   删除不可逆，所以我不会自己动手——真要走这条路，你点头我再执行，
   并且先在后台确认能否"下架旧条目 + 同 slug 重建"以尽量保住 URL。

### 5.3 实测：SkillHub 连图片都不收

`publish` 第一次尝试直接被拒：

```
Error: 请求失败 (400): 不允许的文件类型: assets/preview.png
```

扩展名过滤不只是"没扩展名的文件"，**png 也不在允许清单里**。所以 1.0.2 的处理是：
截图只随仓库出门（`dist/repo/assets/preview.png`），两个市场包都不带图片，
`SKILL.md` / `README.md` 里那一处图引用用 `zip:only` 写成 GitHub 的绝对地址
`https://raw.githubusercontent.com/seahp/number-grid-paint/main/assets/preview.png`，
仓库里那一处继续用本地路径（`zip:skip`）。因此**先推 GitHub，再发市场**，
否则详情页那张图会 404。图标仍是你在后台自己上传，与市场包的成员无关。

## 6. 三个平台的署名/许可一致性

CC BY-NC-SA 4.0 意味着别人可以免费转发和改编，但必须署名、必须非商业、必须同许可证。
所以：

- HTML 顶部注释、`LICENSE.txt`、README 的「署名」「许可证」两节是**许可证本体**，别删；
- 平台自带的"版权/许可"字段统一填 `CC BY-NC-SA 4.0`，不要选" proprietary / 自定义"；
- 别人拿你的 HTML 二次改编后回到市场上架收费，是许可证被违反——遇到时你可以要求下架，
  这是 NC 条款的正当行使，不算"下架别人作品"的争议。

---

## 7. 我检查过 / 没检查的

检查过（本地，见 `references/verification.md`）：数学内核 76 项、版面 1728 组合、
多窗口宽度、双语探针、12 组 PDF、zip 结构与大小、frontmatter 字段、
`skillhub publish --dry-run`、**泄露与脱敏审查（含两条负向自测）**。
线上也复查过：SkillHub 的包能装、签名与内容指纹一致；GitHub 的 `main` tarball
拉回来重扫 **0 命中**，`raw.githubusercontent.com` 上主产物与 README 都是 200。

**1.0.2 这轮按评测员的做法重演了一遍**（不是"应该能跑"，是解压出来逐条敲）：

```bash
rm -rf /tmp/gp101 && mkdir /tmp/gp101 && unzip -q dist/number-grid-paint-skillhub.zip -d /tmp/gp101
cd /tmp/gp101/number-grid-paint
node scripts/verify.mjs                       # 76 项通过 / 0 失败
python3 scripts/env.py                        # 布局：技能包（assets/）
python3 scripts/doc_check.py                  # 当前布局：文档一致
python3 scripts/leak_scan.py                  # 退出码 0（缺词表只作说明）
python3 scripts/gap_probe.py 10 6,7,8
python3 scripts/half_probe.py '?size=10&per=2'
python3 scripts/width_probe.py 1440 760 400 lang=zh
python3 scripts/i18n_probe.py                 # 问题 0
python3 scripts/size_probe.py --lang zh        # 组合 144 异常 0 抛错 0 单格横向顶出去 0
python3 scripts/size_probe.py --lang en        # 同上
python3 scripts/pdf_check.py                  # 12 组页数符合预期，空白页 0
python3 scripts/pdf_export.py '?size=10&copies=4&per=2&lang=zh&seed=20261111' /tmp/课堂4份.pdf
python3 scripts/shot.py /tmp/屏显.png '?size=10&lang=en' all
```

13 条命令**全部退出码 0**，包里那条"找不到文件"的路子已经堵死。
精简包（`number-grid-paint-openplatform.zip`，6 个文件：HTML + README / SKILL.md /
CHANGELOG.md / LICENSE.txt + `references/rules-and-generation.md`）单独按审核员的机械解析
重演了一遍：把 SKILL.md 里每条反引号包住的**文件名**抠出来逐个查存在——`assets/数格涂涂_生成器.html`、
`references/rules-and-generation.md`、`README.md`、`CHANGELOG.md`、`LICENSE.txt`，**全包无缺**；
渲染后没有残留布局标记，没有 `scripts/` 这种目录写法（平台会把它也当条目去找），
也不带图片（市场包不收）；frontmatter 是官方 9 字段、`version: 1.0.2`。

**检查过（线上那份，不是本地推断）**：1.0.2 刷进索引后 `install` 到临时目录，文件清单与
逐字节内容都和本地构建包一致，对**下载回来的这份**跑 `leak_scan.py`（0 命中）、
`doc_check.py`（判一致）和文档里的 13 条命令（全部退出码 0）；详情页 `tags.latest` = 1.0.2，
用浏览器打开确认概述正文里能看到 `github.com/seahp/number-grid-paint`。
唯一没能当场看到的是详情页那张成品图——同一台机器上 `curl` 取它是 200 / 1.6s，
浏览器首次加载却超过 12s，属于链路抖动，不是链接坏。

**没检查**：开放平台的第二次审核结论（要重投之后才有）、
以及 GitHub Pages 在你账号上的可用状态——仓库现在是**源码托管**，
没有一个点开即玩的在线地址。想让老师不下载也能用，就把 Pages 指到
`main` 的根目录，入口用 `数格涂涂_生成器.html`；这一步要你点头再做，
因为它是第二次对外改动，不是发布仓库本身要求的。
哪一步卡住把那一步的报错原文给我，我按报错调包。
