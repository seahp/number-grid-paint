#!/usr/bin/env python3
"""版面效果截图（屏显态，非打印态）。

用法：
    python3 scripts/shot.py out/名字.png '?size=10&ans=1&...' [all|answer|student]

第三个参数决定 isolate：
    all     工具栏一起截（默认）
    answer  只留答案页（把学生页藏起来）——用来确认答案页排版
    student 只留学生页

视口宽度必须 >900px，否则命中 @media screen and (max-width:900px) 的 scale(.5)
预览规则，图里的页盒会缩成半张，截出来不好看。
（版面量测本身已经与窗口宽度无关了——overBox 会按 scaleOf() 折算缩放比，
 见 scripts/width_probe.py；但截图还是要宽视口。）
"""
import pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py

HIDE = {
    'all': '',
    'answer': '.toolbar,.sheet:not(.answers){display:none!important}',
    'student': '.toolbar,.sheet.answers{display:none!important}',
}


def main():
    out = pathlib.Path(sys.argv[1])
    qs = sys.argv[2] if len(sys.argv) > 2 else ''
    iso = sys.argv[3] if len(sys.argv) > 3 else 'all'
    css = HIDE[iso]
    src = SRC.read_text(encoding='utf-8')
    extra = f'<style>body{{background:#fff;margin:0}}{css}</style>'
    tmp = pathlib.Path('/tmp/shot.html')
    j = src.rfind('</head>')
    tmp.write_text(src[:j] + extra + src[j:], encoding='utf-8')
    # 页盒 210×297mm ≈ 794×1123px；两页竖排留点余量
    h = 1250 if 'copies=1' in qs or iso != 'all' else 2400
    # 新版 headless 只认 --screenshot=path 这种写法；
    # 拆成 "--screenshot" path 会被当成第二个 target，直接报 Multiple targets are not supported。
    r = subprocess.run([EDGE, '--headless', '--disable-gpu', '--hide-scrollbars',
                        f'--window-size=1440,{h}', '--virtual-time-budget=20000',
                        f'--screenshot={out.resolve()}',
                        f'file://{tmp}?{qs.lstrip("?")}'],
                       capture_output=True, text=True, timeout=300)
    print(out, out.exists(), f'{out.stat().st_size // 1024}KB' if out.exists() else r.stderr[-200:])


main()
