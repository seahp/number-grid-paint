#!/usr/bin/env python3
"""发布前的泄露与脱敏审查（纪律：任何一次对外发布之前必须先跑它，退出码 0 才算过）。

为什么不等于 make_dist.py 里那句"扫本机路径"：本机路径只是最容易漏的一类。
真正会在审核或事后翻车的是这些：

    本机路径与账号名 / 绝对安装路径 / 邮箱 / 手机号 / 身份证 / 各种 token 与私钥 /
    带凭证的 URL / 机器码 UUID / 项目里特有的真实姓名、班级、学校

前九类是通用正则，能自动判；最后那类**机器判不了**，所以本脚本读一份
`scripts/redact_terms.txt`（一行一个词，写你自己项目的真实人名/班级/校名/内部代号），
命中就报。文件不存在或为空 → 记一条待办（--strict 时升级为阻断），
意思是"这一类你还没声明过要保护什么"。

用法：
    python3 scripts/leak_scan.py                    # 默认扫 dist/ 下所有发布物 + 两个 zip
    python3 scripts/leak_scan.py dist/repo          # 只扫某个目录
    python3 scripts/leak_scan.py some.zip other/    # 扫 zip（含包内每一项的实际字节）
    python3 scripts/leak_scan.py --strict           # 待办也算失败
    python3 scripts/leak_scan.py --json             # 机器可读，给别的脚本用

命中行只打印**前几个字符 + 长度**，不把疑似密钥或身份证号原样贴进终端/日志，
否则这个审查本身变成第二次泄露。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
TERMS = HERE / 'redact_terms.txt'

HOME = str(pathlib.Path.home()).rstrip('/')
USER = pathlib.Path(HOME).name

# ---------------------------------------------------------------- 通用规则
# (类别, 正则, 说明)
RULES = [
    ('本机路径',
     re.compile(re.escape(HOME) + r'\b|[A-Z]:\\Users\\' + re.escape(USER) + r'\\|'
                r'[A-Za-z]:\\\\Users\\\\' + re.escape(USER) + r'\\\\|/Volumes/' + re.escape(USER) + r'/'),
     '写死的家目录/账号名，换机器即坏，且暴露本机用户名'),
    ('账号名',
     re.compile(r'(?i)\b' + re.escape(USER) + r'\b'),
     '本机账号短名出现在发布物里（多数时候是不该带出去的）'),
    ('他人/本机用户目录',
     re.compile(r'/Users/(?!Shared\b)[a-z_][\w.\-]{2,}/|/home/(?!runner|admin|user\b)[a-z_][\w.\-]{2,}/'),
     '某个具体机器的用户目录（自己的家目录由上一条规则单独判）'),
    ('临时/安装残留路径',
     re.compile(r'/private/var/folders/|C:\\\\Program Files\\\\'),  # 审查例外：本脚本自己的规则字面量
     '某个具体机器的临时目录或安装路径；应改由 env.py 之类解析'),
    ('邮箱',
     re.compile(r'(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@(?!example\.[a-z]{2,3})[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'),
     '个人邮箱会被抓取；文档里的示例邮箱请用 @example.com'),
    ('手机号/固话',
     re.compile(r'(?<!\d)(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8})(?!\d)'),
     '中国大陆手机号或带区号的固话'),
    ('身份证号',
     re.compile(r'(?<!\d)\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:[0-2]\d|3[01])\d{3}[\dXx](?!\d)'),
     '18 位身份证'),
    ('密钥/令牌',
     re.compile(r'gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|skh_[A-Za-z0-9]{16,}|'
                r'sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[bpars]-[A-Za-z0-9\-]{10,}|'
                r'ya29\.[A-Za-z0-9_\-]{10,}|ntn_[A-Za-z0-9]{10,}'),
     '看起来像真凭据；哪怕已经轮换过也不能出现在公开仓库'),
    ('硬编码口令',
     re.compile(r'(?i)(api[_-]?key|secret|access[_-]?token|password|passwd)\s*[:=]\s*["\'][^"\']{6,}["\']'),
     '写在代码里的口令/密钥字面量'),
    ('私钥块',
     re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
     '私钥，出现即视为事故'),
    ('带凭证的 URL',
     re.compile(r'://[^/\s:@]+:[^/\s:@]+@'),
     'URL 里嵌了用户名密码'),
    ('机器码/UUID',
     re.compile(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b'),
     '设备/会话 UUID，通常没有理由公开'),
    ('个人信息字段',
     re.compile(r'学号|学生名单|班级名单|家长电话|教师姓名|学籍'),  # 审查例外：本脚本自己的规则字面量
     '教育类物料里最贵的一类，出现就要人工确认是不是真实数据'),
]

# 公开、可预期的 URL/标识：命中邮箱或令牌规则时，这些不算问题
BENIGN = re.compile(r'(creativecommons\.org|github\.com/|github\.io|skillhub\.cn|'
                    r'workbuddy\.cn|codebuddy\.cn|tencent\.com|w3\.org|schema\.org|'
                    r'openworkspace|fonts\.googleapis)')
# 服务地址不是个人信息：git remote 里的 git@github.com、noreply 之类
SERVICE_MAIL = re.compile(r'^(git|noreply|no-reply|admin|support|contact|info)@'
                          r'(github\.com|gitlab\.com|bitbucket\.org)$')

#: 行内豁免：规则自己的字面量会扫到自己（leak_scan.py 就命中过两次），
#: 教育类物料里那类"字段名"也常常只是**说明文字**而不是真实数据。
#: 在行尾写 `# 审查例外：<理由>` 就跳过这一行——理由必须写，grep 得到，
#: 所以豁免是可审计的，不是"把规则关掉"。
EXEMPT = re.compile(r'审查例外|leak-scan:\s*ignore')

SKIP_PARTS = {'__MACOSX', '__pycache__', '.DS_Store', '.git'}


def load_terms():
    if not TERMS.exists():
        return None
    return [t.strip() for t in TERMS.read_text(encoding='utf-8').splitlines()
            if t.strip() and not t.strip().startswith('#')]


def scan_text(text: str, tag: str, terms):
    """扫一段文本，返回命中描述。"""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if EXEMPT.search(line):
            continue
        for cat, pat, why in RULES:
            m = pat.search(line)
            if not m:
                continue
            frag = m.group(0)
            if BENIGN.search(line):        # 公开 URL 里的邮箱/域名之类
                continue
            if cat == '邮箱' and SERVICE_MAIL.match(frag):
                continue                   # git@github.com 这种服务地址，不是个人信息
            shown = frag[:6] + ('…' if len(frag) > 6 else '')
            hits.append(f'{tag}:{i} [{cat}] {shown!r}(len {len(frag)}) {line.strip()[:56]} | {why}')
        for t in terms or []:
            if t in line:
                hits.append(f'{tag}:{i} [名单词] {t!r} → {line.strip()[:56]} | 在 redact_terms.txt 里声明为不可公开')
    return hits


def scan_file(path: pathlib.Path, tag: str, terms):
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if b'\0' in data:
        return []
    return scan_text(data.decode('utf-8', 'replace'), tag, terms)


def scan_tree(root: pathlib.Path, terms):
    out = []
    for p in sorted(root.rglob('*')):
        if p == TERMS:            # 词表本身就是敏感词集合，不能自己扫自己
            continue
        if p.is_file() and not (set(p.parts) & SKIP_PARTS):
            out += scan_file(p, str(p.relative_to(root)), terms)
    return out


#: 这些后缀的二进制成员是**已知媒体**（成品截图、字体、样张 PDF），没有文本可扫；
#: 只登记不报警。除此之外任何含 NUL 的成员都当成"包里混进了没人知道是什么的东西"。
MEDIA_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf',
             '.woff', '.woff2', '.ttf', '.otf'}


def scan_zip(z: pathlib.Path, terms, media=None):
    out = []
    with zipfile.ZipFile(z) as zf:
        for name in zf.namelist():
            if set(pathlib.PurePosixPath(name).parts) & SKIP_PARTS or name.endswith('/'):
                continue
            data = zf.read(name)
            if b'\0' in data:
                if pathlib.PurePosixPath(name).suffix.lower() in MEDIA_EXT:
                    if media is not None:
                        media.append(f'{z.name}!{name} ({len(data)} B)')
                    continue
                out.append(f'{z.name}!{name} 二进制成员，需人工确认内容')
                continue
            out += scan_text(data.decode('utf-8', 'replace'), f'{z.name}!{name}', terms)
    return out


def audit(targets):
    """扫一批目标（目录 / zip / 单文件），返回 (命中, 待办, 扫了什么, 说明)。

    命中=必须处理；待办=开发仓库发布前要补的声明（技能包里跑则降级成说明）；
    说明=不阻断但要点名看一眼的东西（例如包内的图片成员）。

    make_dist.py 直接调这个函数，所以这里不含 argparse 与退出码。
    """
    terms = load_terms()
    todo = []
    if terms is None:
        todo.append(f'缺 {TERMS.relative_to(ROOT)}：真实人名/班级/校名这类**只有你知道**的词还没声明')
    elif not terms:
        todo.append(f'{TERMS.relative_to(ROOT)} 是空的：同上，至少写清要保护哪些词')

    hits, scanned, media, notes = [], [], [], []
    for t in targets:
        if t.is_dir():
            for sub in sorted(t.rglob('*')):
                if sub.suffix == '.zip' and sub.is_file():
                    scanned.append(f'zip {sub}')
                    hits += scan_zip(sub, terms, media)
            scanned.append(f'dir {t}')
            hits += scan_tree(t, terms)
        elif t.suffix == '.zip':
            scanned.append(f'zip {t}')
            hits += scan_zip(t, terms, media)
        elif t.is_file():
            scanned.append(f'file {t}')
            hits += scan_file(t, t.name, terms)

    if media:
        # 已知媒体（成品截图/字体）不阻断发布，但必须点名让人看一眼——
        # "包里多了个没人认识的二进制"和"包里的截图"是两回事，都要看得见。
        notes.append('包内媒体成员（内容扫不了，确认一眼是什么）：'
                     + '、'.join(media[:8]) + ('…' if len(media) > 8 else ''))

    # 同一个命中会从"目录"和"包内字节"各报一次，去重
    return list(dict.fromkeys(hits)), todo, scanned, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('targets', nargs='*', help='目录或 zip；默认 dist/ 下的发布物，没有 dist/ 就扫当前目录树')
    ap.add_argument('--strict', action='store_true', help='名单词表缺失/为空也算失败')
    ap.add_argument('--json', action='store_true')
    opt = ap.parse_args()

    if opt.targets:
        targets = [pathlib.Path(t) for t in opt.targets]
        # 传了路径却不存在，必须失败：以前会被静默跳过，扫了 0 个目标还回一句"干净，可以发布"
        missing = [str(t) for t in targets if not t.exists()]
        if missing:
            print(f'目标不存在：{"、".join(missing)}\n'
                  f'（在技能包里跑的话没有 dist/——那层目录是开发仓库的产物。'
                  f'包内自检请用 `python3 scripts/leak_scan.py` 不带参数。）')
            sys.exit(1)
    elif (ROOT / 'dist').exists():
        targets = [ROOT / 'dist']
    else:
        targets = [ROOT]
        print(f'没找到 {ROOT / "dist"}（开发仓库的打包产物），改成扫当前目录树：{ROOT}\n')

    uniq, todo, scanned, notes = audit(targets)
    if not scanned:                      # 一条都没扫到不等于干净
        print('什么都没扫到 → 判为失败（空扫描不算通过）')
        sys.exit(1)

    # 技能包里没有 redact_terms.txt 是**设计如此**（名单词表只留在开发机），
    # 所以从包里跑这条命令的人不该被提示"不要发布"。开发仓库里照旧拦。
    is_package = (ROOT / 'SKILL.md').exists() and (ROOT / 'assets').is_dir() \
        and not (ROOT / 'dist').exists()
    if todo and is_package:
        notes += ['（技能包布局）' + t for t in todo]
        todo = []

    if opt.json:
        print(json.dumps({'scanned': scanned, 'hits': uniq, 'todo': todo, 'notes': notes},
                         ensure_ascii=False, indent=2))
    else:
        print(f'== 泄露与脱敏审查 == 扫了 {len(scanned)} 个目标')
        for s in scanned:
            print('   ·', s)
        if uniq:
            print(f'\n命中 {len(uniq)} 处（发布前必须清掉，或确认它本来就该公开）：')
            for h in uniq[:80]:
                print('  ', h)
            if len(uniq) > 80:
                print(f'   …另 {len(uniq) - 80} 处，用 --json 看全')
        else:
            print('\n通用规则（本机路径/用户目录/账号名/邮箱/电话/证件/凭据/UUID/PII 字段）：0 命中')
        for n in notes:
            print('  说明:', n)
        if todo:
            print()
            for t in todo:
                print('  待办:', t)

    if uniq:
        print('\n结论：有命中 → **不发**。清掉后重跑。')
        sys.exit(1)
    if todo:
        print('\n结论：通用项干净，但名单词表待补 → 可以打包，**不要发布**。' if not opt.strict
              else '\n结论：名单词表未声明，--strict 下不发。')
        sys.exit(2 if not opt.strict else 1)
    print('\n结论：干净，可以发布。')
    sys.exit(0)


if __name__ == '__main__':
    main()
