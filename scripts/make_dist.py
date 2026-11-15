#!/usr/bin/env python3
"""打包发布物料（只生成文件，不上传、不推送、不提交给任何市场）。

    python3 scripts/make_dist.py            # 检查 + 出 dist/
    python3 scripts/make_dist.py --samples  # 顺带用无头浏览器导两张样张（慢，需 Edge/Chrome）
    python3 scripts/make_dist.py --strict   # 提交前最后一次：占位署名没换就不出门

产出这些东西：

    dist/repo/                             GitHub 仓库根（README/LICENSE.txt/.gitignore/references/scripts/HTML）
    dist/skill/number-grid-paint/          技能包（SKILL.md + assets/ + references/ + scripts/）
    dist/skill-lite/number-grid-paint/     精简包（同上，去掉 scripts/ 与 .gitignore）
    dist/number-grid-paint-skillhub.zip     给 SkillHub：完整字段 frontmatter + 带探针脚本
    dist/number-grid-paint-openplatform.zip 给 WorkBuddy 开放平台：9 字段 frontmatter + 精简包

zip 用 zipfile 手写：不带 macOS extra field、不带 .DS_Store/__pycache__、时间戳固定，
所以重复打包字节一致；两个包都按**解压后**字节数校验 3MB 上限。
开放平台那边会做静态代码检测，`subprocess.run` / `.exec(` 这类会被报「命令执行风险」，
所以它的包用精简版（产物就是那一个 HTML，探针留在仓库）。

打包前会跑一遍 preflight：许可证在不在、HTML 里有没有网络请求、KERNEL 段在不在、
verify.mjs 过不过、**泄露与脱敏审查**（scripts/leak_scan.py：本机路径/用户目录/账号名/
邮箱/电话/证件/凭据/UUID/PII 字段 + scripts/redact_terms.txt 里声明的名单词）。
这几条不过就退出码 1，不会把半成品打出去；发布物（两个 zip 的包内字节 + 三份目录）
在出门前还会再扫一次。
占位署名（`<你的署名 …>`）单独列为"发布前待办"：本地照样出包，但要带 --strict 才拦。
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from env import SRC  # noqa: E402

ROOT = HERE.parent
DIST = ROOT / 'dist'
HTML = SRC.name
SKILL_NAME = 'number-grid-paint'
#: 成品截图（scripts/shot.py 生成：`python3 scripts/shot.py assets/preview.png
#: '?size=10&copies=1&ans=0&seed=20261115&sum=5,6,7,8&diff=2,3&quota=3' all 1560`）。
#: 市场详情页和 README 都要它——没有图，"打开就能用"只是句声称。
PREVIEW = ROOT / 'assets' / 'preview.png'

# 两个上架平台对 SKILL.md frontmatter 的要求不一样（沿用班级管理工作台那轮踩过的坑）：
#   · SkillHub（skillhub.cn）——完整字段：name/slug/display_name(_en)/displayName(En)/
#     summary/tags/description/description_zh/description_en/category/version/author/homepage
#   · WorkBuddy 开放平台（open.workbuddy.cn）——官方文档的 9 字段简洁格式，
#     多带字段、YAML 里的 " & "、macOS 的 zip extra field 都可能让它"解析失败"
# 所以本地 SKILL.md 写**完整版**（超集），打开放平台包时只重写 frontmatter、正文不动。
SKILLHUB_FIELDS = ['name', 'slug', 'display_name', 'display_name_en',
                   'displayName', 'displayNameEn', 'summary', 'tags',
                   'description', 'description_zh', 'description_en',
                   'category', 'version', 'author', 'homepage']
OPEN_FIELDS = ['name', 'display_name', 'display_name_en', 'description',
               'description_zh', 'description_en', 'category', 'version', 'author']

#: 开放平台按**解压后**字节数校验（报错过原文："解压后超出大小限制（最大 3MB）"）
SIZE_LIMIT = 3 * 1024 * 1024
#: 固定时间戳 + 清空 extra field：重复打包字节一致，也不会带 AppleDouble 之类垃圾
ZIP_DATE = (2026, 1, 1, 0, 0, 0)
SKIP_PARTS = {'__MACOSX', '__pycache__', '.DS_Store'}

# 技能包只带"改了代码要复核"用得上的脚本；开发期的量测探针一起带上，
# 因为版面是量出来的，不带探针等于让别人无法复现回归。
#
# **这一份清单就是"文档与包内文件一致"的真相来源**：README / SKILL / references 里
# 每写一条 `python3 scripts/xxx.py`，那个 xxx.py 必须出现在这里（或那一行带"仓库"字样，
# 表明它讲的是开发仓库里的流程），否则 scripts/doc_check.py 判失败、preflight 不出包。
# 1.0.0 那轮评测说的"照文档执行会卡住、要先调路径"就是这么漏出去的：
# 文档提到 gap_probe.py / half_probe.py / make_dist.py，包里没有；而且脚本只认仓库布局。
SKILL_SCRIPTS = ['verify.mjs', 'env.py', 'size_probe.py', 'width_probe.py',
                 'i18n_probe.py', 'pdf_check.py', 'pdf_export.py', 'shot.py',
                 'gap_probe.py', 'half_probe.py', 'leak_scan.py', 'doc_check.py']
#: 故意不出门的脚本：`make_dist.py` 会整目录清空 dist/ 再重打包，只有在开发仓库里
#: （有 SUBMISSION.md、有 .git/、HTML 在根）才成立。放进技能包等于发一个"跑一次就把
#: 用户目录搞乱"的东西，所以它只写在带"仓库"标记的那几行文档里。
REPO_ONLY_SCRIPTS = ['make_dist.py']
#: 名单词表只留在开发机：真实人名/班级/校名一旦进包就是事故本身。
LOCAL_ONLY = ['redact_terms.txt']
REF_DOCS = ['rules-and-generation.md', 'layout-solver.md', 'i18n.md',
            'verification.md', 'publishing.md']
#: 精简包只带"讲产品"的三份说明。`verification.md` / `publishing.md` 整篇都在讲脚本，
#: 而精简包里一个脚本都没有——放进去就是让读者照着一堆不存在的文件敲命令。
#: 精简包带的参考文献。只带"讲玩法与出题口径"的那一篇——收件人拿它来判断卷子里的
#: 数字为什么一定涂得完；版面解算和双语文案架构是给改代码的人的，通篇都在点
#: `scripts/*` 探针，而平台会按 SKILL.md 同一套规矩挑 references 里的路径，
#: 精简包不带脚本 → 带着它们就是等着"缺少必需资源"。改代码请看源码仓库。
LITE_REF_DOCS = ['rules-and-generation.md']

PLACEHOLDER = re.compile(r'<你的署名|<作者署名|<your name|<user>|<你的仓库地址>')
NETWORK = re.compile(r'\bfetch\s*\(|XMLHttpRequest|new\s+Worker\s*\(|<script[^>]+src=|@import\s+url\(|https?://[^"\'<>\s]+\.(?:js|css|woff2?|ttf)\b')

#: 发布前的泄露与脱敏审查统一由 scripts/leak_scan.py 负责（本机路径、用户目录、账号名、
#: 邮箱、电话、证件、凭据、UUID、PII 字段，加上 scripts/redact_terms.txt 里声明的名单词）。
#: 这一条是班级管理工作台那轮的教训——已公开仓库里混进过未脱敏的本班程序，
#: 而当时所有"功能测试"都查不出来，因为它只测功能不测隐私。
#: 纪律：**任何一次对外发布（push / 上传 / publish）之前必须先跑它，0 命中才出门。**
import leak_scan  # noqa: E402  （HERE 已进 sys.path）


def audit_targets():
    """源码侧要扫的东西：所有会进发布物的文件，一个个点名，不扫整个开发目录。

    不扫 ROOT 是因为 ROOT 下有 out/ 的样张 PDF 和上一轮的 dist/，
    那些命中既不是发布物、又会把真正的信号淹掉。
    """
    fixed = [SRC, ROOT / 'README.md', ROOT / 'LICENSE.txt', ROOT / 'SKILL.md',
             ROOT / 'SUBMISSION.md', ROOT / '.gitignore', ROOT / 'references']
    scripts = [s for s in sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.mjs'))
               if s.name != 'redact_terms.txt']
    return [p for p in fixed + scripts if p.exists()]


def check(strict=False):
    """problems = 打包不出去；warns = 打得出去、但你发布前得自己处理。

    占位署名（<你的署名 …>）归到 warns：那是**只能由你填**的信息，本地物料不该被它
    卡住（否则永远看不到 dist/ 长什么样）。--strict 时把它升级成 problem，
    适合提交前那一次跑。
    """
    problems, notes, warns = [], [], []

    lic = ROOT / 'LICENSE.txt'
    if not lic.exists():
        problems.append('缺 LICENSE.txt')
    elif 'Attribution-NonCommercial-ShareAlike 4.0' not in lic.read_text(encoding='utf-8'):
        problems.append('LICENSE.txt 内容不是 CC BY-NC-SA 4.0 全文')

    for f in ['README.md', 'SKILL.md', 'SUBMISSION.md', HTML, '.gitignore']:
        p = ROOT / f
        if not p.exists():
            problems.append(f'缺 {f}')

    # 占位署名：发布前必须替换，否则归属信息是空的
    for f in [HTML, 'README.md', 'SKILL.md']:
        p = ROOT / f
        if p.exists():
            for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
                if PLACEHOLDER.search(line):
                    msg = f'{f}:{i} 还有占位署名 → {line.strip()[:70]}'
                    (problems if strict else warns).append(msg)

    html = SRC.read_text(encoding='utf-8')
    hits = NETWORK.findall(html)
    if hits:
        problems.append(f'HTML 里出现外部依赖/网络请求：{sorted(set(hits))[:5]}')
    else:
        notes.append('HTML 无网络请求、无外部脚本（离线可用）')

    if 'KERNEL START' not in html or 'KERNEL END' not in html:
        problems.append('找不到 KERNEL 段，verify.mjs 会直接中止')

    for d in REF_DOCS:
        if not (ROOT / 'references' / d).exists():
            problems.append(f'缺 references/{d}')

    # SkillHub 按扩展名过滤，无扩展名的文件（`LICENSE`、`.gitignore` 之类）会 400 拒收整包
    for f in [HTML, 'LICENSE.txt', 'README.md', 'SKILL.md'] + REF_DOCS + SKILL_SCRIPTS:
        if pathlib.Path(f).suffix == '':
            problems.append(f'{f} 没有扩展名，SkillHub 会整包 400 拒收（"不允许的文件类型"）')

    # 泄露与脱敏审查：先扫源码侧（会进发布物的每一类文件），出门前再扫发布物本身。
    # 命中就是 problem——这一条不许"知道但照发"，因为它保护的是别人索引不到的东西。
    hits, todo, _, media_notes = leak_scan.audit(audit_targets())
    if hits:
        problems.append('源码里有未脱敏内容，公开出去就是泄露：\n     '
                        + '\n     '.join(hits[:8]))
    else:
        notes.append('泄露与脱敏审查（源码侧）：通用规则 0 命中')
    for t in todo:
        (problems if strict else warns).append('脱敏声明不完整：' + t)

    # frontmatter：两个平台吃的字段集不同，本地这份必须同时是两处的超集
    fm, _ = fm_read(ROOT / 'SKILL.md')
    if fm is None:
        problems.append('SKILL.md 缺 frontmatter（--- 包裹）')
    else:
        for label, keys in (('SkillHub', SKILLHUB_FIELDS), ('开放平台', OPEN_FIELDS)):
            miss = [k for k in keys if not fm.get(k)]
            if miss:
                problems.append(f'SKILL.md frontmatter 缺 {label} 必填字段：{miss}')
        if fm.get('name') != SKILL_NAME:
            problems.append(f"frontmatter name={fm.get('name')!r} 与包目录名 {SKILL_NAME} 不一致")
        else:
            notes.append(f"SKILL.md frontmatter 完整（{fm.get('version')} · {fm.get('author')}）")

    r = subprocess.run(['node', str(HERE / 'verify.mjs'), str(SRC)],
                       capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    notes.append('verify.mjs → ' + (tail[-1] if tail else '无输出'))
    if r.returncode != 0 or '0 项失败' not in r.stdout:
        problems.append('verify.mjs 没通过，别发')

    kb = len(html.encode('utf-8')) // 1024
    notes.append(f'{HTML} = {kb} KB（单文件）')
    if kb > 400:
        problems.append(f'单文件已涨到 {kb} KB，市场上传可能超限，先确认目标平台上限')

    # 文档 ↔ 实际文件：README/SKILL/references 里写的每条命令和路径，
    # 在**文档将要被装进去的那个布局**里必须真实存在（详见 scripts/doc_check.py）。
    import doc_check
    bad = doc_check.check_layout(ROOT, '仓库') + doc_check.check_versions(ROOT)
    if bad:
        problems.append('文档和实际文件对不上，照文档执行会卡住：\n     '
                        + '\n     '.join(bad[:6]))
    else:
        notes.append('文档 ↔ 文件一致性（仓库布局 + 版本号）：通过')

    if not PREVIEW.exists():
        warns.append(f'缺 {PREVIEW.relative_to(ROOT)}（成品截图）：GitHub README 会没图，'
                     f'市场详情页正文里那张 raw.githubusercontent 的图也会 404 —— '
                     f'跑 `python3 scripts/shot.py {PREVIEW.relative_to(ROOT)} '
                     f'"<地址栏参数>" all 1560` 重截一张')

    # 清单里的脚本必须真的在，否则 copy_common 会在打包中途抛 FileNotFoundError
    miss = [s for s in SKILL_SCRIPTS + REPO_ONLY_SCRIPTS if not (HERE / s).exists()]
    if miss:
        problems.append(f'SKILL_SCRIPTS/REPO_ONLY_SCRIPTS 里点了名但 scripts/ 下没有：{miss}')

    return problems, notes, warns


def fm_read(path: pathlib.Path):
    """把 SKILL.md 拆成 (字段字典, 正文)。解析方式与各平台一致：只按行、只切第一个冒号。"""
    text = path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if line.strip() and ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def fm_dump(fm, keys):
    out = ['---']
    for k in keys:
        v = fm[k].replace(' & ', ' and ')      # YAML 保留字符，开放平台会解析失败
        out.append(f'{k}: {v}')
    out.append('---\n')
    return '\n'.join(out)


def clean_zip(src_dir: pathlib.Path, out_zip: pathlib.Path, skill_md_text=None):
    """手写 zip：无 macOS extra field、无 .DS_Store/__pycache__、时间戳固定。
    skill_md_text 不为空时用给定内容替换包内 SKILL.md（正文不动，只换 frontmatter）。"""
    files = [p for p in sorted(src_dir.rglob('*'))
             if p.is_file() and not (set(p.parts) & SKIP_PARTS)]
    total, dirs_written = 0, set()
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            parts = (src_dir.name,) + p.relative_to(src_dir).parts
            arc = '/'.join(str(x) for x in parts)
            for i in range(1, len(parts)):            # 先把父目录条目补上
                darc = '/'.join(str(x) for x in parts[:i]) + '/'
                if darc not in dirs_written:
                    zi = zipfile.ZipInfo(darc, date_time=ZIP_DATE)
                    zi.external_attr = (0o40755 << 16) | 0x10
                    zi.create_system = 3
                    z.writestr(zi, b'')
                    dirs_written.add(darc)
            data = p.read_bytes()
            if arc.endswith('/SKILL.md') and skill_md_text is not None:
                data = skill_md_text.encode('utf-8')
            zi = zipfile.ZipInfo(arc, date_time=ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zi.create_system = 3
            zi.extra = b''
            z.writestr(zi, data)
            total += len(data)
    return total


#: 文档里按布局分叉的段落，用 HTML 注释当标记（渲染时会被整段删掉，纸面上看不到）。
#: 三个轴，对应三类"这个布局里没有 / 只看得到另一种写法"：
#:   `repo:skip`   只给开发仓库看，**两个市场包都删**（里面是仓库路径、发布流程）；
#:   `lite:skip`   讲脚本与仓库流程，**精简包**里删掉（完整技能包留着）；
#:   `zip:skip` /  `zip:only`   同一件事在仓库 vs 在市场包里的两种写法
#:                  ——目前就是那张成品截图：仓库里是本地文件，市场包里是 raw URL。
#:   `lite:only`   只在精简包里出现的那段说明。
#: 为什么必须有这套分叉：平台会**机械地解析 SKILL.md 里提到的每个路径**，
#: 只要出现 `scripts/pdf_export.py` 而包里没有这个文件，就判"资产包缺少必需资源"直接驳回
#: （WorkBuddy 开放平台 2026-11-15 实测，驳回原文：
#:  `资产包缺少必需资源 1 项：文件「scripts/pdf_export.py」（SKILL.md 引用）`）。
#: 而精简包又不能带脚本——那边的静态检测把 `subprocess.run` 报成「命令执行风险」。
#: 所以同一份源文档必须能渲染出"只提包里有的东西"的那一版。`scripts/doc_check.py`
#: 的 check_skillmd() 会在打包时按这条规则验两个包，不通过就不出 zip。
def _blocks(tag):
    return re.compile(r'[ \t]*<!--\s*' + tag + r':start\s*-->.*?<!--\s*' + tag +
                      r':end\s*-->[ \t]*\n?', re.S)


def _unwrap(tag):
    return re.compile(r'[ \t]*<!--\s*' + tag + r':(start|end)\s*-->[ \t]*\n?')


def _keep(tag):
    """把 `tag:only` 那段展开成它自己（去掉外层标记）。"""
    return re.compile(r'[ \t]*<!--\s*' + tag + r':start\s*-->\n?(.*?)\n?[ \t]*<!--\s*' +
                      tag + r':end\s*-->[ \t]*\n?', re.S)


REPO_SKIP, LITE_SKIP = _blocks('repo:skip'), _blocks('lite:skip')
ZIP_SKIP = _blocks('zip:skip')
LITE_ONLY, ZIP_ONLY = _keep('lite:only'), _keep('zip:only')
TAGS = ('repo:skip', 'lite:skip', 'zip:skip', 'lite:only', 'zip:only')


def render_doc(text: str, kind: str):
    """把带标记的源文档渲染成某个布局该看到的那一版。kind: repo / skill / lite。"""
    if kind == 'repo':
        # 仓库就是全量：所有 skip 段都留着，only 段（那是给包里的替代写法）删掉
        text = LITE_ONLY.sub('', text)
        text = ZIP_ONLY.sub('', text)
    else:
        text = REPO_SKIP.sub('', text)           # 仓库专属段落，两个包都拿掉
        text = ZIP_SKIP.sub('', text)            # 仓库里那种本地写法，包里拿掉
        text = ZIP_ONLY.sub(lambda m: m.group(1) + '\n', text)
        if kind == 'lite':
            text = LITE_SKIP.sub('', text)       # 精简包再拿掉讲脚本的段落
            text = LITE_ONLY.sub(lambda m: m.group(1) + '\n', text)
        else:
            text = LITE_ONLY.sub('', text)
    for tag in TAGS:                            # 剩下没成对的裸标记行也清掉
        text = _unwrap(tag).sub('', text)
    return text


#: 市场包与仓库的差别：SkillHub 会按扩展名过滤文件，**无扩展名的文件直接 400 拒收**
#: （实测 `Error: 请求失败 (400): 不允许的文件类型: LICENSE`），所以包里只留有扩展名的文件，
#  LICENSE 写成 LICENSE.txt；.gitignore 这类只在仓库里。
#  2026-11-15 又实测一条：**图片也不允许**——带 `assets/preview.png` 的包被 400 拒收
#  （`不允许的文件类型: assets/preview.png`）。所以截图只留在仓库，两个市场包都不带，
#  文档里的图改用 raw.githubusercontent 的绝对 URL（那是仓库里的同一张图）。
def copy_common(dst: pathlib.Path, kind='skill'):
    """kind: 'repo' | 'skill' | 'lite' —— 三种布局各自该带什么、文档该渲染成哪一版。"""
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, dst / HTML)
    shutil.copy2(ROOT / 'LICENSE.txt', dst / 'LICENSE.txt')
    for f in ('README.md', 'SKILL.md', 'CHANGELOG.md'):
        (dst / f).write_text(render_doc((ROOT / f).read_text(encoding='utf-8'), kind),
                             encoding='utf-8')
    # SUBMISSION.md **不进市场包**（1.0.1 起）：它是开发仓库的发布日志，
    # 里面全是仓库路径（make_dist.py / dist/ / redact_terms.txt）和平台内部编号，
    # 收件人照它在包里执行只会卡住——正是 1.0.0 评测抱怨的那件事。
    # 包里的发布说明由 references/publishing.md 承担，仓库里另留一份 SUBMISSION.md。
    if kind == 'repo':
        shutil.copy2(ROOT / '.gitignore', dst / '.gitignore')
    refs = dst / 'references'
    refs.mkdir(exist_ok=True)
    for d in (LITE_REF_DOCS if kind == 'lite' else REF_DOCS):
        # 参考文献也要按布局渲染：开发向的几篇（口径/版面/双语）难免点到 `scripts/*`，
        # 精简包不带脚本，平台按 SKILL.md 的那套规矩同样会挑 references 里的路径。
        (refs / d).write_text(render_doc((ROOT / 'references' / d).read_text(encoding='utf-8'), kind),
                              encoding='utf-8')
    if kind != 'lite':                   # 精简包不带脚本（见 build_skill 的说明）
        scr = dst / 'scripts'
        scr.mkdir(exist_ok=True)
        for s in SKILL_SCRIPTS:
            shutil.copy2(HERE / s, scr / s)
    # 成品截图：只随仓库出门（市场包不收图片）；详情页那张图由文档里的 raw URL 提供
    if kind == 'repo' and PREVIEW.exists():
        (dst / 'assets').mkdir(exist_ok=True)
        shutil.copy2(PREVIEW, dst / 'assets' / PREVIEW.name)


def check_raw_urls(repo: pathlib.Path):
    """文档里每一条 raw.githubusercontent 的绝对 URL，必须是仓库里真能取到的文件。

    市场包不收图片，所以详情页/README 那张成品图只能引 GitHub raw 的绝对地址；
    这条链接一旦断，两个市场的正文就是一片 404。断的最常见方式很隐蔽：
    `.gitignore` 里有 `*.png`，本地文件在、`git add` 静默跳过、线上永远没有。
    所以这里同时查三件事——文件在不在 dist/repo、有没有被 .gitignore 挡住、
    以及是不是已经被 git 跟踪（第一次要在 push 之前跑）。
    """
    bad = []
    urls = set()
    docs = [ROOT / f for f in ('README.md', 'SKILL.md', 'CHANGELOG.md', 'SUBMISSION.md')]
    docs += sorted((ROOT / 'references').glob('*.md'))
    for d in docs:
        if not d.exists():
            continue
        for m in re.finditer(r'https://raw\.githubusercontent\.com/[^\s)`"]+',
                             d.read_text(encoding='utf-8')):
            u = m.group(0)
            if '<' in u:                      # 文档里的**写法模板**（`…/<仓库>/main/…`），
                continue                      # 不是要发出去的链接，没法验也不该验
            urls.add(u)
    for u in sorted(urls):
        tail = u.split('/main/', 1)[-1]
        f = repo / tail
        if not f.exists():
            bad.append(f'{u}\n      仓库里没有这个文件（{tail}）')
            continue
        if not (repo / '.git').exists():
            continue                                  # 没 .git 时只查文件存在
        ig = subprocess.run(['git', '-C', str(repo), 'check-ignore', '-q', tail],
                            capture_output=True, text=True)
        if ig.returncode == 0:
            bad.append(f'{u}\n      {tail} 被 .gitignore 挡住了，push 上去还是 404 '
                       f'——要么 git add -f，要么在 .gitignore 里加 !{tail}')
            continue
        tr = subprocess.run(['git', '-C', str(repo), 'ls-files', '--', tail],
                            capture_output=True, text=True)
        if not tr.stdout.strip():
            bad.append(f'{u}\n      {tail} 还没被 git 跟踪（git add 后再 push）')
    return bad


def build_repo():
    dst = DIST / 'repo'
    copy_common(dst, kind='repo')
    shutil.copy2(ROOT / 'SUBMISSION.md', dst / 'SUBMISSION.md')   # 仓库里也留一份，别人想知道怎么改怎么发
    # 仓库里额外带上全部开发脚本，方便别人接着改
    for s in sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.mjs')):
        shutil.copy2(s, dst / 'scripts' / s.name)
    return dst


#: 精简包顶部说明：让人一眼知道校验脚本在哪、为什么不在包里。
#: 插在 frontmatter **之后**——放最前面会让平台读不到 `---` 开头的元数据。
#: 注意这段**不能点到具体脚本名**：平台会机械解析 SKILL.md 里出现的每个路径，
#: 精简包不带 scripts/，写出 `size_probe.py` 这种名字同样算"缺少必需资源"。
#: 连目录写法也不带斜杠（写成 `scripts 目录`）——那边的解析器把 `scripts/` 也当成条目查。
LITE_NOTE = """<!-- 本包为市场上架精简版：只含网页版生成器与说明文档。
     出题内核与版面/双语/PDF 的回归探针在 GitHub 仓库
     https://github.com/seahp/number-grid-paint 的 scripts 目录下，
     改代码时才需要；直接用 HTML 出卷不需要。 -->

"""


def build_skill(lite=False):
    """lite=True：只留 SKILL.md + assets + references + README/LICENSE.txt。
    给开放平台用——那边的静态检测会把 scripts/ 里的 subprocess.run 报成「命令执行风险」，
    而市场上架要的产物就是那个 HTML，探针留在 GitHub 仓库里给改代码的人。

    不带脚本就必须**连文档里的脚本引用一起拿掉**：开放平台会解析 SKILL.md 提到的路径，
    缺文件直接驳回（见 render_doc 上面那段）。分叉写在源文档的
    repo:skip / lite:skip / lite:only / zip:skip / zip:only 标记里。"""
    dst = DIST / ('skill-lite' if lite else 'skill') / SKILL_NAME
    copy_common(dst, kind='lite' if lite else 'skill')
    assets = dst / 'assets'
    assets.mkdir(exist_ok=True)
    shutil.move(str(dst / HTML), str(assets / HTML))          # 技能包：主产物进 assets/
    (dst / 'samples').mkdir(exist_ok=True)
    if lite:
        sk = dst / 'SKILL.md'
        fm, body = fm_read(sk)
        sk.write_text(fm_dump(fm, SKILLHUB_FIELDS) + LITE_NOTE + body, encoding='utf-8')
    return dst



def make_samples(dst: pathlib.Path):
    """两张样张：中文标准卷 + 英文一页两卷。要无头浏览器，跑不通就跳过（不算失败）。"""
    try:
        from env import EDGE  # noqa: F401
    except SystemExit as e:
        print('  跳过样张：', e)
        return []
    cases = [('样张_中文_标准卷.pdf', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&lang=zh&seed=20261111'),
             ('样张_English_two-up.pdf', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1&quota=3&sum=6,7,8,9&diff=2,3&lang=en&seed=20261112')]
    made = []
    for name, q in cases:
        out = dst / 'samples' / name
        r = subprocess.run([sys.executable, str(HERE / 'pdf_export.py'), q, str(out)],
                           capture_output=True, text=True, timeout=300)
        if out.exists():
            made.append(out)
        else:
            print('  样张失败', name, r.stderr[-160:])
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--samples', action='store_true', help='顺带导出样张 PDF（需无头浏览器）')
    ap.add_argument('--keep', action='store_true', help='不清空 dist/，增量覆盖')
    ap.add_argument('--strict', action='store_true',
                    help='把"占位署名"这类待办升级成阻断项；提交前的最后一次跑用这个')
    args = ap.parse_args()

    print('== preflight ==')
    problems, notes, warns = check(args.strict)
    for n in notes:
        print('  ·', n)
    if problems:
        print('\n!! 先解决这些再打包：')
        for p in problems:
            print('   -', p)
        sys.exit(1)
    print('  preflight 通过')
    if warns:
        print('\n<< 发布前待办（不影响本地打包，但市场提交前必须处理）：')
        for w in warns:
            print('   !', w)
        print('   处理完再跑：python3 scripts/make_dist.py --strict')


    if DIST.exists() and not args.keep:
        # dist/repo/.git 是**线上那个仓库的工作副本**（remote、历史、tag 都在里面），
        # 整目录清空会把它一起删掉，下一次就得重新配凭据——2026-11-15 发布那天差点踩上。
        stash = None
        gitdir = DIST / 'repo' / '.git'
        if gitdir.exists():
            stash = pathlib.Path('/tmp/gp_repo_git')
            if stash.exists():
                shutil.rmtree(stash)
            shutil.move(str(gitdir), str(stash))
            print('  （已把 dist/repo/.git 暂存到 /tmp，重建后放回）')
        shutil.rmtree(DIST)
        DIST.mkdir(parents=True)
        if stash and stash.exists():
            (DIST / 'repo').mkdir(parents=True, exist_ok=True)
            shutil.move(str(stash), str(DIST / 'repo' / '.git'))
            print('  （dist/repo/.git 已放回）')
    DIST.mkdir(parents=True, exist_ok=True)

    repo = build_repo()
    print('== 仓库目录 ==', repo)
    skill = build_skill()
    print('== 技能包   ==', skill)
    skill_lite = build_skill(lite=True)
    print('== 精简包   ==', skill_lite)

    # 包布局再查一遍：技能包里 HTML 在 assets/ 下、没有 dist/，
    # 文档在那种布局下也得自洽（这条是 1.0.0 评测"检查命令找不到文件"的正解）。
    import doc_check
    #
    # 两档检查，对应两类驳回：
    #   check_layout  —— 读者视角：照文档敲的命令在这个布局里跑不通（允许"仓库"字样豁免）
    #   check_skillmd —— 平台视角：SKILL.md 里提到的每个路径都会被**机械解析**，
    #                   缺文件直接驳回，散文豁免无效。实测过一条：
    #                     审核备注：资产包缺少必需资源 1 项：
    #                     文件「scripts/pdf_export.py」（SKILL.md 引用）
    # 所以两个包都要过这一档，不通过就不出 zip。
    bad = doc_check.check_layout(skill, '技能包') + doc_check.check_skillmd(skill, '技能包') \
        + doc_check.check_layout(skill_lite, '精简包') + doc_check.check_skillmd(skill_lite, '精简包')
    if bad:
        print('\n!! 包布局下文档和文件对不上，这个包发出去要么卡住、要么被驳回：')
        for b in bad[:12]:
            print('   -', b)
        sys.exit(1)
    print('  文档 ↔ 文件一致性（技能包 + 精简包，含 SKILL.md 无豁免档）：通过')
    # 文档里引到仓库绝对 URL 的东西，仓库这边必须真取到（市场包不收图片，全靠这条）
    raw = check_raw_urls(repo)
    if raw:
        print('\n!! 文档里的仓库绝对链接对不上，市场详情页会 404：')
        for b in raw:
            print('   -', b)
        sys.exit(1)
    print('  仓库绝对链接（raw.githubusercontent）：都能在 dist/repo 里取到')
    # 包里的脚本能不能真的跑起来（只验路径解析，不跑完整回归）
    r = subprocess.run([sys.executable, str(skill / 'scripts' / 'env.py')],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('\n!! 技能包里的 scripts/env.py 跑不通（路径没适配包布局）：')
        print('   ', (r.stdout + r.stderr).strip()[:400])
        sys.exit(1)
    print('  包内 scripts/env.py：', r.stdout.strip().splitlines()[0])

    # 精简包不带脚本，所以它那份 SKILL.md 顶部必须自己说清"校验脚本在仓库里"，
    # 否则读者照着 README 敲命令同样会卡——只是卡在另一个地方。
    lite_sk = (skill_lite / 'SKILL.md').read_text(encoding='utf-8')
    head = lite_sk[:4000]
    if 'scripts 目录' not in head or 'github.com/' not in head:
        print('\n!! 精简包不带脚本，但 SKILL.md 顶部没把这件事讲清楚（要含脚本说明与仓库地址）')
        sys.exit(1)
    # 连目录的斜杠写法也不留：那边把 `scripts/` 当成条目去查，包里没有这个目录。
    if 'scripts/' in lite_sk:
        print('\n!! 精简包 SKILL.md 里还留着 `scripts/` 这种目录写法（平台会按条目去找，包里没有）')
        sys.exit(1)
    print('  精简包：SKILL.md 顶部已说明脚本去处与仓库地址，且不含 scripts/ 目录写法')

    if args.samples:
        for f in make_samples(skill) + make_samples(repo) + make_samples(skill_lite):
            print('  样张', f.relative_to(DIST))

    # 两个 zip：内容按平台裁剪，frontmatter 按平台字段集重写，正文（含精简版那条注释）不动
    fm, _ = fm_read(ROOT / 'SKILL.md')
    for tag, keys, src, out in [
            ('skillhub', SKILLHUB_FIELDS, skill, DIST / f'{SKILL_NAME}-skillhub.zip'),
            ('开放平台', OPEN_FIELDS, skill_lite, DIST / f'{SKILL_NAME}-openplatform.zip')]:
        body = fm_read(src / 'SKILL.md')[1]
        text = fm_dump(fm, keys) + body
        total = clean_zip(src, out, skill_md_text=text)
        n_entries = sum(1 for p in src.rglob('*') if p.is_file())
        print(f'== {tag} zip ==', out.name,
              f'{out.stat().st_size // 1024} KB（解压后 {total // 1024} KB / 上限 3072 KB，{n_entries} 个文件）')
        if total > SIZE_LIMIT:
            print(f'   !! 解压后 {total} B 超了开放平台 3MB 上限')
    print('\n（本地 SKILL.md 保持完整字段版；两个 zip 各自重写 frontmatter，正文没动。）')

    # 出门前最后一道：直接扫 zip 里的实际字节，和扫目录是两回事
    #   （重写 frontmatter、剔除 scripts/ 之后内容变了，只扫目录会漏）
    hits, todo, _, media_notes = leak_scan.audit([
        DIST / f'{SKILL_NAME}-skillhub.zip', DIST / f'{SKILL_NAME}-openplatform.zip',
        repo, skill, skill_lite])
    if hits:
        print('\n!! 发布物里有未脱敏内容，别传：')
        for x in hits[:12]:
            print('   -', x)
        sys.exit(1)
    # 名单词表本身是敏感词集合，混进发布物就是第二次泄露
    stray = [p for d in (repo, skill, skill_lite) for p in d.rglob('redact_terms.txt')]
    if stray:
        print('\n!! 名单词表被带进发布物（它自己就是敏感信息）：', [str(p) for p in stray])
        sys.exit(1)
    print('== 泄露与脱敏审查 == 发布物（两个 zip 的包内字节 + 三份目录）0 命中；'
          '名单词表未随包出门')

    print('\n下一步看 SUBMISSION.md。发布纪律：**push / 上传 / publish 之前**，'
          '对真正要发出去的那份东西再跑一次 `python3 scripts/leak_scan.py <目标>`，'
          '退出码 0 才允许出门（本脚本自身不联网、不上传）。')


main()
