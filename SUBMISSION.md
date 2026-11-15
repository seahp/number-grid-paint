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

## 1. 现在的发布状态（2026-11-15）

| 平台 | 状态 | 说明 |
| --- | --- | --- |
| SkillHub | **已上线 v1.0.0** | https://skillhub.cn/skills/user_1db801dd/number-grid-paint （skillId 322080）；`skillhub install` 已跑通，签名校验通过，内容指纹 `ef3e1ecf…10bee4` |
| GitHub | **待凭据** | 钥匙串里的 PAT 返回 `401 Bad credentials`，`ssh -T git@github.com` 返回 `Permission denied (publickey)`，本机没有 `gh`。需要你给一条能用的凭据，见第 3 节 |
| WorkBuddy 开放平台 | **待你登录 + 入驻认证** | 打开 https://open.workbuddy.cn 会停在登录页（微信扫码 / 手机号 / QQ / 邮箱 / SSO），登录后首次进控制台要求选认证方式（个人 / 企业 / 其他组织机构）。实名与身份认证只能你本人做，见第 4 节 |

SkillHub 上那一份是**做这套审查之前**的物料打的包，但我把线上下载回来的包重扫过：**0 命中**，
签名与内容指纹一致，所以**不重发**（用户 2026-11-15 定：只要没问题就不用重发）。
本地物料比线上多的只是 `leak_scan.py` 和这几份发布纪律文档，不影响已上线内容的正确性——
等下一次真改版（1.0.1）时随包一起带上去，届时照常走 `make_dist.py --strict` → `leak_scan` → `publish`。

---

## 2. 物料

先跑一次总打包：

```bash
cd 纸笔游戏-数格涂涂
python3 scripts/make_dist.py --strict      # 缺文件/网络请求/frontmatter 缺字段/未脱敏内容会直接拦下
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

提交前再确认这三件事：

1. **署名**：物料里写的是 `粉笔与代码`，出处写的是
   `https://github.com/seahp/number-grid-paint`（仓库还没建，名字是按你既有仓库风格定的）。
   要改就改这三处，改完重跑 `make_dist.py`：
   - `README.md` 的「署名」「许可证」两节
   - `数格涂涂_生成器.html` 顶部注释里的 `Copyright / 版权所有` 与 `署名与出处`
   - `SKILL.md` frontmatter 的 `author` 与 `homepage`
2. **仓库名**：GitHub 上实际建的名字要和 README/HTML/SKILL.md 里的 URL 一致，
   否则署名指向 404。
3. **非商业条款要落实**：CC BY-NC-SA 4.0 里 NC = 不可商用。三个平台上架时
   **一律选"免费"**（SkillHub 的 `pay_mode` 保持 0，开放平台不要勾付费/内购），
   也不要把打印卷收钱卖。想收钱得先换成 CC BY-SA 或另做商业授权，那是另一个决定。

---

## 3. GitHub（待你给凭据）

远端仓库先在 https://github.com/new 手动建（**Public**，不初始化 README，避免首推冲突）。
名称建议 `number-grid-paint`，About 填 `Printable math-game worksheet generator · single offline HTML · zh/en`，
Topics：`math, education, worksheet, printable, offline, single-file, chinese-english`。

凭据二选一：

- **PAT**：https://github.com/settings/tokens → Fine-grained 或 classic（要 `repo` 权限）。
  给我之后我只用它跑一次 `git push`，不写进任何文件、不进 commit、也不进 remote URL。
- **SSH**：把本机那把 `id_ed25519_cmw_push2.pub` 加到账号的 SSH Keys，
  然后 `ssh -T git@github.com` 应该回 `Hi seahp!`。

审过再推（第 0 节的纪律）：

```bash
python3 scripts/leak_scan.py dist/repo            # 退出码必须是 0
cd dist/repo
git init -b main
git add -A
git commit -m "数格涂涂 v1.0.0：单文件离线数学涂色游戏卷生成器（中英双语）"
git remote add origin git@github.com:seahp/number-grid-paint.git   # 或 https 形式
git push -u origin main
```

**commit 作者邮箱也会被爬**：本机 git 全局 `user.email` 是你的个人邮箱，
直接 commit 会把它写进公开历史（爬 GitHub 邮箱是垃圾邮件的老路子）。
在这一份干净副本里改用 GitHub 的 noreply 地址：

```bash
git -c user.email=<你的用户名>@users.noreply.github.com commit -m "…"
# 你自己的 noreply 地址在 https://github.com/settings/admin（Keep my email addresses private）
```

`.gitignore` 已排除 `out/`、`dist/`、`*.pdf`、`*.png`。历史里一旦混进真实班级/学生信息
就删不干净（force push 也留在 reflog 和平台缓存里），所以别在开发目录里直接 `git init`，
用 `dist/repo` 这份干净副本。

可选：开 Pages 让老师不用下载就能打开——
Settings → Pages → Deploy from branch → `main` / `/`，再把
`https://seahp.github.io/number-grid-paint/数格涂涂_生成器.html` 写进 README 顶部。
文件名带中文，Pages 能用但 URL 会转义；介意的话在仓库里额外放一份 `index.html`（内容与
生成器完全相同，只是 ASCII 名）。

---

## 4. WorkBuddy 开放平台（待你登录）

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
| 版本 | 1.0.0 |
| 作者 | 粉笔与代码 |
| 简介（中） | 抄 `description_zh` |
| 简介（英） | 抄 `description_en` |
| 触发说明 | 抄 `description`（已带 6 个以上触发词，别删） |
| 收费模式 | **免费**（CC BY-NC-SA 的 NC 要求） |

已知会让它「解析失败 / 超限」的几件事，这个包都处理过了：

- frontmatter 字段多于官方 9 字段 → 精简掉了（`slug/summary/tags/homepage` 不在开放平台包里）
- 值里的 ` & ` 是 YAML 保留字符 → 打包时自动换成 ` and `
- macOS 的 zip extra field、`.DS_Store`、`__MACOSX` → 手写 zip，全部为 0
- **解压后**总大小 ≤ 3MB（它校验的是解压后字节数，不是 zip 文件大小）→ 当前 163 KB（改文档就会浮动，看下面那条自查命令）
- 静态检测「命令执行风险」→ 包里不含脚本
- **上传前**再跑 `python3 scripts/leak_scan.py dist/number-grid-paint-openplatform.zip`
  （它扫的是 zip 里的实际字节，不是目录）

审核前后自己复核一遍（本地命令，不联网）：

```bash
python3 -c "import zipfile;z=zipfile.ZipFile('dist/number-grid-paint-openplatform.zip');\
print('解压后 KB', sum(i.file_size for i in z.infolist())//1024, '| extra field 条目', sum(1 for i in z.infolist() if i.extra))"
```

期望：`解压后 KB 163 | extra field 条目 0`（数字会随文档增删浮动，**extra field 必须是 0**，
解压后必须 ≤ 3072 KB）。

上架后如果需要同时保留旧版本，注意平台侧同名技能是覆盖式更新；要下架旧版在后台点
「下架」而不是删包。

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

---

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
线上也复查过：SkillHub 的包能装、签名与内容指纹一致。

**没检查**：GitHub 与开放平台实际的表单字段名和审核口径（会变），
以及 GitHub Pages 在你账号上的可用状态。上传时以页面实际提示为准；
哪一步卡住把那一步的报错原文给我，我按报错调包。
