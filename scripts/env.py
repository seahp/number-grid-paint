#!/usr/bin/env python3
"""开发脚本共用的两处路径解析：生成器 HTML 在哪、用哪个浏览器跑无头量测。

以前这两条在每个脚本里写死成本机的家目录绝对路径和某个 .app 的绝对路径，
换台机器（或发布出去让别人跑）就全红。现在按下面的顺序找，找不到就说清楚缺什么：

  生成器 HTML   GRIDPAINT_SRC 环境变量 → 仓库布局 数格涂涂_生成器.html（在 scripts/ 上一层）
                → 技能包布局 assets/数格涂涂_生成器.html → 这两层里唯一一个 *生成器*.html
  浏览器        GRIDPAINT_BROWSER 环境变量 → macOS 上的 Edge/Chrome/Chromium
                → PATH 里的 msedge / microsoft-edge / chromium / google-chrome

两种布局都得认，因为**文档里的命令是照技能包写的**：GitHub 仓库把主产物放在根，
技能包（`skillhub install` 下来的那份）放在 `assets/` 下。只认一种，另一处的
`python3 scripts/size_probe.py` 就会报"找不到文件"——这正是 1.0.0 那轮评测里
"按说明直接运行检查命令可能找不到文件"的成因。

浏览器只需要支持三个无头参数：--headless --dump-dom --screenshot --print-to-pdf，
Edge 和 Chrome 都一样，所以不用挑。
"""
import os
import pathlib
import shutil

_HERE = pathlib.Path(__file__).resolve().parent
_MAIN = '数格涂涂_生成器.html'


def _looks_like_src(p):
    """确认这份 HTML 真是生成器（含 KERNEL 段），别把 out/ 里的样张或别的网页当成品。"""
    try:
        return 'KERNEL' in p.read_text(encoding='utf-8', errors='ignore')[:200000]
    except OSError:
        return False


def _candidates():
    """按优先级给出所有可能放主产物的位置（仓库布局 → 技能包布局）。"""
    for base in (_HERE.parent, _HERE.parent / 'assets'):
        yield base / _MAIN
    for base in (_HERE.parent, _HERE.parent / 'assets'):
        yield from sorted(base.glob('*生成器*.html'))


def _find_src():
    env = os.environ.get('GRIDPAINT_SRC')
    if env:
        p = pathlib.Path(env).expanduser().resolve()
        if not p.exists():
            raise SystemExit(f'GRIDPAINT_SRC 指向的文件不存在：{p}')
        return p
    seen, hits = set(), []
    for p in _candidates():
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            hits.append(p)
    ok = [p for p in hits if p.exists() and _looks_like_src(p)]
    if ok:
        return ok[0].resolve()
    raise SystemExit(
        f'找不到生成器 HTML。试过这些位置：{ "、".join(str(p) for p in hits) }。\n'
        f'技能包里它应该在 assets/{_MAIN}；开发仓库里在根目录。\n'
        f'要是你把成品改放了别的位置，用 GRIDPAINT_SRC=/path/to/文件.html 指定。')


def _root_dir():
    """项目根（out/ 落在这里）：主产物在 assets/ 下时往上退一层。"""
    return SRC.parent.parent if SRC.parent.name == 'assets' else SRC.parent



def _find_browser():
    env = os.environ.get('GRIDPAINT_BROWSER')
    if env:
        p = shutil.which(env) or (pathlib.Path(env).expanduser() if pathlib.Path(env).exists() else None)
        if p:
            return str(p)
        raise SystemExit(f'GRIDPAINT_BROWSER 指向的可执行文件不存在：{env}')
    app_paths = [
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    for a in app_paths:
        if pathlib.Path(a).exists():
            return a
    for exe in ('msedge', 'microsoft-edge', 'microsoft-edge-stable', 'chromium',
                'chromium-browser', 'google-chrome', 'google-chrome-stable'):
        w = shutil.which(exe)
        if w:
            return w
    raise SystemExit(
        '没找到无头浏览器。装一个 Edge/Chrome，或用 GRIDPAINT_BROWSER=/path/to/chrome 指定。')


SRC = _find_src()
EDGE = _find_browser()
OUT = _root_dir() / 'out'

if __name__ == '__main__':          # python3 scripts/env.py 自查两台机器上的解析结果
    print('生成器 :', SRC)
    print('布局   :', '技能包（assets/）' if SRC.parent.name == 'assets' else '开发仓库（根目录）')
    print('浏览器 :', EDGE)
    print('输出   :', OUT)
    print('覆盖   : GRIDPAINT_SRC=/path/to/文件.html  GRIDPAINT_BROWSER=/path/to/chrome')
