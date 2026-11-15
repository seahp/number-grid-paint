#!/usr/bin/env python3
"""文档 ↔ 实际文件一致性检查（新增：因为 1.0.0 那轮评测报的是"照文档执行会卡住"）。

评测原话有两类，都属于本脚本的职责：

  1. "按说明直接运行检查命令可能找不到文件" —— 文档写 `scripts/xxx.py`，包里没这个文件；
     或者文件在，但脚本只认某一种目录布局，换个布局就报"找不到生成器 HTML"。
  2. "发布相关内容不够齐全" —— 打包/发布流程散落在没出门的文件里，包里那份读不通。

所以本脚本做三件事：

  A. 扫 README.md / SKILL.md / SUBMISSION.md / CHANGELOG.md / references/*.md，
     把里面出现过的每一条路径引用抠出来（`scripts/x`、`references/x.md`、`assets/x`、
     `python3 x.py`、`node x.mjs`），逐个确认**在这份文档将要被装进的那个布局里**真实存在。
     仓库布局 = 开发目录；包布局 = dist/skill/number-grid-paint（HTML 在 assets/ 下）。
  B. 只允许"仓库专用"的引用出现在带 `REPO_MARK` 标记（默认「仓库」二字）的**句子**里。
     比如 `python3 scripts/make_dist.py --strict` 在包里跑不通，那它所在的那一句
     就必须写清楚"（仓库）"，读者不会照着在技能包里敲。句子按折行前的逻辑行判断，
     代码块例外——块内的命令要逐行成立，但同一块里的 `#` 注释行可以承担说明。
  C. 顺带核对 frontmatter 的 version 与 CHANGELOG.md 顶部条目、HTML 里的 BUILD 号一致——
     市场详情页显示一个号、包里写着另一个号，也算"发布内容不齐全"。

用法：
    python3 scripts/doc_check.py            # 只查仓库布局（改文档时随手跑）
    python3 scripts/doc_check.py --pkg      # 查刚打出来的技能包布局
    python3 scripts/doc_check.py --both     # 两个都查（make_dist.py 的 preflight 用这条）

退出码：0 全部一致；1 有不一致（逐条打印"哪个文件的第几行提到了什么，缺在哪"）。
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

#: 会被装进技能包、因此文档里可以直接照抄的文档文件
DOCS = ['README.md', 'SKILL.md', 'SUBMISSION.md', 'CHANGELOG.md']
DOC_DIRS = ['references']

#: 行内标记：这一行讲的就是"仓库里才有的流程"，允许引用包里不存在的文件。
#: 文档是中英双语的，所以英文写法也要认——`repositor`（repository/repositories）单独一条，
#: `\brepo\b` 只认独立单词，免得 "repo" 出现在 "report" 里被当成豁免。
REPO_MARK = re.compile(r'仓库|开发机|repositor|\brepo\b')

#: 这些前缀天然只在仓库里存在（打包产物、本机路径），引用它们的行必须带 REPO_MARK
REPO_ONLY_PREFIX = ('dist/', 'out/')

#: 文档里可能出现的几种路径写法
PATH_RE = re.compile(r'(?:^|[\s`(\'"=])(`?)(scripts/[\w.\-]+\.(?:py|mjs|txt)'
                     r'|references/[\w.\-]+\.md|assets/[\w.\-]+\.(?:html|png|jpg|pdf)'
                     r'|[\w.\-]+\.py|[\w.\-]+\.mjs)(`?)(?=$|[\s`.,;:)\'"])')
BARE_RE = re.compile(r'^(?:python3\s+|node\s+)?([\w.\-]+\.(?:py|mjs))$')

SKILL_NAME = 'number-grid-paint'


def doc_files(base: pathlib.Path):
    out = [base / d for d in DOCS if (base / d).exists()]
    for d in DOC_DIRS:
        if (base / d).is_dir():
            out += sorted((base / d).glob('*.md'))
    return out


def resolve(ref: str, base: pathlib.Path):
    """把一条路径引用在给定布局下解析成真实位置；返回 None 表示这个布局里没有。

    技能包把主产物挪进 assets/，`python3 scripts/xxx.py` 这类相对命令的基准仍是包根，
    所以只有 scripts/ 、references/ 、assets/ 三种前缀 + 裸文件名需要特殊处理。
    """
    ref = ref.strip('`')
    if ref.startswith(REPO_ONLY_PREFIX):
        return None
    cand = base / ref
    if cand.exists():
        return cand
    if '/' not in ref:                       # 裸文件名：仓库在根、技能包在 assets/、
        for p in (base / ref, base / 'assets' / ref, base / 'scripts' / ref):
            # 文档小节标题常写短名（`## 2. width_probe.py`），
            # 正文里上一句已经交代过 `scripts/`，所以裸 .py/.mjs 也要能落到 scripts/ 下
            if p.exists():
                return p
    else:                                    # 反过来：文档按技能包写 `assets/x.html`，
        p = base / pathlib.PurePosixPath(ref).name   # 而仓库布局把它放在根
        if p.exists():
            return p
    return None


def logical_line(lines, i):
    """把被排版拆行的**同一句话**拼回来（行号 i 从 1 数）。

    中文文档习惯一行 78 列左右折行，"（这一段讲的是**仓库**里的流程）"经常落在上一行。
    豁免只看物理行的话，写文档的人就被迫把句子挤成一整行——那是检查器在指挥人排版。
    所以按折行回看，最多两行；但只在句子内部回看：遇到空行、标题、新的列表项，
    或上一行已经以句号结尾（说明当前行是**另一句**），就停下——否则上一段的"仓库"
    会把这一句的漏网引用也豁免掉。
    """
    out = [lines[i - 1]]
    j = i - 1                                      # 上一条的**行号**（1 基）
    back = 0
    while j >= 1 and back < 2:
        prev = lines[j - 1].strip()                # 行号 j → 下标 j-1
        if (not prev or prev.startswith(('#', '```', '|', '-', '*'))
                or prev.endswith(('：', ':', '。', '！', '？'))):
            break
        out.insert(0, prev)
        j -= 1
        back += 1
    return ' '.join(out)


def _selftest():
    """logical_line 自己是这段规则的裁判，先让它自己过一遍（写反下标时这里就红）。"""
    L = ['上一句讲的是仓库里的 make_dist.py。',      # 1：句号结尾，不该被下一句借用
         '这一句单独提到 dist/repo，没人豁免它',      # 2
         '折过来的一行讲仓库里的流程，',               # 3：同一句的后半
         '所以 dist/repo 写在下面也没事',             # 4
         '',                                          # 5：空行
         '新段落里的 dist/out 没人管',                # 6
         '- 列表项讲仓库',                            # 7
         '紧跟其后的 dist/repo']                      # 8
    assert '仓库' not in logical_line(L, 2), logical_line(L, 2)
    assert '仓库' in logical_line(L, 4), logical_line(L, 4)
    assert '仓库' not in logical_line(L, 6), logical_line(L, 6)
    assert '仓库' not in logical_line(L, 8), logical_line(L, 8)
    return '折行算同一句；句号/空行/新列表项会断开'


def check_layout(base: pathlib.Path, label: str):
    """返回问题列表：每条是 "文档:行号 → 引用 → 为什么不行"。"""
    bad = []
    for doc in doc_files(base):
        rel = doc.relative_to(base)
        lines = doc.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(lines, 1):
            ctx = logical_line(lines, i)
            for m in PATH_RE.finditer(line):
                ref = m.group(2).strip('`')
                if ref in ('doc_check.py', 'env.py'):     # 本脚本讲道理时难免提到自己
                    pass
                hit = resolve(ref, base)
                if hit is not None:
                    continue
                # 引用不存在，只有两种可接受的情况：
                #   1) 这一句明确说了是仓库/开发机里的流程；
                #   2) 这个引用本来就只存在于仓库，而这一句也这么写了。
                # 判"这一句"而不是"这一行"：折行是排版的事，不该由检查器逼着人挤成一行。
                if REPO_MARK.search(ctx):
                    continue
                bad.append(f'{rel}:{i} 引用 `{ref}` 在{label}布局里不存在，'
                           f'且这一句没写"仓库"标记 → 读者照抄会卡住\n      {line.strip()[:90]}')
        # 代码块里的命令也要成立：```bash 块里每一条 python3/node 命令的第一个参数。
        # 折行在这里不豁免——代码块就是给人整段抄的，但块内的 `#` 注释行可以承担说明。
        inblock = False
        comment = ''
        for i, line in enumerate(lines, 1):
            if line.strip().startswith('```'):
                inblock = not inblock
                comment = ''
                continue
            if not inblock:
                continue
            if line.strip().startswith('#'):
                comment = line
            mm = re.match(r'\s*(?:python3|node)\s+([\w./\-]+\.(?:py|mjs))', line)
            if mm and resolve(mm.group(1), base) is None \
                    and not (REPO_MARK.search(line) or REPO_MARK.search(comment)):
                bad.append(f'{rel}:{i} 代码块里的命令 `{line.strip()[:60]}` 在{label}布局里跑不通'
                           f'（没有这个文件，且块内没写"仓库"）')
    return bad


def check_versions(base: pathlib.Path):
    bad = []
    sk = base / 'SKILL.md'
    if not sk.exists():
        return ['缺 SKILL.md']
    fm = sk.read_text(encoding='utf-8').split('---')[1] if sk.read_text(encoding='utf-8').startswith('---') else ''
    ver = re.search(r'^version:\s*([\w.\-]+)', fm, re.M)
    if not ver:
        return ['SKILL.md frontmatter 没有 version 字段']
    ver = ver.group(1)
    ch = base / 'CHANGELOG.md'
    if ch.exists():
        top = re.search(r'^##\s*\[?([\w.\-]+)\]?', ch.read_text(encoding='utf-8'), re.M)
        if not top:
            bad.append('CHANGELOG.md 里找不到 `## [x.y.z]` 这样的版本标题')
        elif top.group(1) != ver:
            bad.append(f'版本不一致：SKILL.md frontmatter={ver}，CHANGELOG.md 顶部={top.group(1)}')
    html = list((base / 'assets').glob('*.html')) or list(base.glob('*生成器*.html'))
    if html:
        b = re.search(r"var\s+BUILD\s*=\s*'([\d\-]+)'", html[0].read_text(encoding='utf-8'))
        if b:
            print(f'  · 版本对齐：SKILL.md {ver} · HTML BUILD {b.group(1)}'
                  f'{" · CHANGELOG " + ver if ch.exists() else ""}')
    return bad


#: 平台**机械解析** SKILL.md 里提到的路径，缺文件就驳回，不看上下文、不读散文。
#: 实测（WorkBuddy 开放平台，2026-11-15）：
#:   审核备注：资产包缺少必需资源 1 项：文件「scripts/pdf_export.py」（SKILL.md 引用）
#: 所以 SKILL.md 比 README 严格一档：里面提到的每个文件都必须真的在包里，
#: "这行讲的是仓库"那种豁免在这里不成立。
MARKER_LEFT = re.compile(r'(lite|repo|zip):(skip|only):(start|end)')


def check_skillmd(base: pathlib.Path, label: str):
    """SKILL.md 单独一档：每条路径引用都必须在本布局里真实存在，无豁免。"""
    sk = base / 'SKILL.md'
    if not sk.exists():
        return [f'{label}：缺 SKILL.md']
    bad = []
    text = sk.read_text(encoding='utf-8')
    body = re.split(r'^---\n.*?\n---\n', text, flags=re.S)[1] if text.startswith('---') else text
    for i, line in enumerate(body.splitlines(), 1):
        if MARKER_LEFT.search(line):
            bad.append(f'SKILL.md:{i} 渲染后还留着布局标记，'
                       f'说明 make_dist.py 的 render_doc 没跑到这份文件')
            continue
        for m in PATH_RE.finditer(line):
            ref = m.group(2).strip('`')
            if resolve(ref, base) is None:
                bad.append(f'SKILL.md:{i} 提到 `{ref}`，{label}里没有 → '
                           f'平台会按"资产包缺少必需资源"驳回。'
                           f'要么把它装进包，要么用 lite:skip（精简包）/ repo:skip（两个包都）圈起来；'
                           f'若是图片这类平台不收的成员，改用 zip:only 写成仓库里的绝对 URL')
    return bad


def layout_label(base: pathlib.Path):
    """看目录结构认布局：仓库有 dist/，技能包 HTML 在 assets/ 下且带 scripts/，精简包没脚本。

    为什么要认：文档里写的命令，收件人是在**包目录**里解压后敲的，不是在开发仓库里。
    `python3 scripts/doc_check.py --both` 在包里跑，包里没有 dist/，
    这时候"查当前布局"就是它能做的全部事情——不能因此报错或假装通过。

    判据用 make_dist.py 在不在：开发仓库和完整技能包**都有** SKILL.md + assets/ + scripts/，
    光看这三个会认错（2026-11-15 就这么把仓库布局当成技能包查过一次）；
    而打包脚本按定义只留在仓库里，是最干净的区别。
    """
    if (base / 'scripts' / 'make_dist.py').exists():
        return '仓库'
    if (base / 'SKILL.md').exists() and (base / 'assets').is_dir():
        return '技能包' if (base / 'scripts').is_dir() else '精简包'
    return '仓库'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pkg', help='只查某个技能包目录（默认按当前布局自动识别）')
    ap.add_argument('--both', action='store_true',
                    help='当前布局之外，再把 dist/ 下的技能包和精简包一起查（make_dist.py 用这条）')
    ap.add_argument('--quiet', action='store_true')
    opt = ap.parse_args()

    jobs = []
    if opt.pkg:
        pkg = pathlib.Path(opt.pkg)
        if not pkg.exists():
            print(f'技能包目录不存在：{pkg}\n（先跑 python3 scripts/make_dist.py；'
                  f'只想查当前布局就别带 --pkg）')
            sys.exit(1)
        jobs.append((pkg, layout_label(pkg)))
    else:
        jobs.append((ROOT, layout_label(ROOT)))
        if opt.both:
            for sub, lab in (('skill', '技能包'), ('skill-lite', '精简包')):
                d = ROOT / 'dist' / sub / SKILL_NAME
                if d.exists():
                    jobs.append((d, lab))

    try:
        rule = _selftest()
    except AssertionError as e:
        print(f'!! 本脚本自己的"同一句"判定写错了（{e}）——它会误豁免或误报，先修它')
        sys.exit(2)
    if not opt.quiet:
        print(f'  判定自测：{rule}')

    bad = []
    for base, label in jobs:
        problems = check_layout(base, label)
        if label != '仓库':
            problems += check_skillmd(base, label)   # 仓库那份允许讲仓库流程，包不允许
        if not opt.quiet:
            n = len(doc_files(base))
            print(f'== {label}布局 ==（{base}）文档 {n} 份，'
                  f'{"一致" if not problems else f"{len(problems)} 处不一致"}')
        bad += [f'[{label}] {p}' for p in problems]
        if label == '仓库':
            bad += check_versions(base)

    if len(jobs) == 1 and layout_label(ROOT) != '仓库':
        print('   （当前就是包布局，没有 dist/：查的这份正是收件人会看到的那份文档）')

    if bad:
        print(f'\n发现 {len(bad)} 处文档与实际文件不一致：')
        for b in bad:
            print('  -', b)
        print('\n结论：照文档执行会卡住 → 改文档或把文件带上，**不要发布**。')
        sys.exit(1)
    print('\n结论：文档里每一条命令和路径，在对应布局下都真实存在；版本号也对得上。')
    sys.exit(0)


if __name__ == '__main__':
    main()
