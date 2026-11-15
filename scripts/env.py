#!/usr/bin/env python3
"""开发脚本共用的两处路径解析：生成器 HTML 在哪、用哪个浏览器跑无头量测。

以前这两条在每个脚本里写死成本机的家目录绝对路径和某个 .app 的绝对路径，
换台机器（或发布出去让别人跑）就全红。现在按下面的顺序找，找不到就说清楚缺什么：

  生成器 HTML   GRIDPAINT_SRC 环境变量 → 本脚本同目录的 ../数格涂涂_生成器.html
                → 上级目录里唯一一个 *生成器*.html
  浏览器        GRIDPAINT_BROWSER 环境变量 → macOS 上的 Edge/Chrome/Chromium
                → PATH 里的 msedge / microsoft-edge / chromium / google-chrome

浏览器只需要支持三个无头参数：--headless --dump-dom --screenshot --print-to-pdf，
Edge 和 Chrome 都一样，所以不用挑。
"""
import os
import pathlib
import shutil

_HERE = pathlib.Path(__file__).resolve().parent


def _find_src():
    env = os.environ.get('GRIDPAINT_SRC')
    if env:
        p = pathlib.Path(env).expanduser().resolve()
        if not p.exists():
            raise SystemExit(f'GRIDPAINT_SRC 指向的文件不存在：{p}')
        return p
    p = _HERE.parent / '数格涂涂_生成器.html'
    if p.exists():
        return p
    cands = sorted(_HERE.parent.glob('*生成器*.html'))
    if len(cands) == 1:
        return cands[0]
    raise SystemExit(
        f'找不到生成器 HTML（在 {p.parent} 下）。用 GRIDPAINT_SRC=/path/to/文件.html 指定。')


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
OUT = SRC.parent / 'out'

if __name__ == '__main__':          # python3 scripts/env.py 自查两台机器上的解析结果
    print('生成器 :', SRC)
    print('浏览器 :', EDGE)
    print('输出   :', OUT)
