#!/usr/bin/env python3
"""打印回归：几种版面组合 → PDF，数页数（应与预期一致）并按内容流字节判断空白页。
用法 python3 scripts/pdf_check.py"""
import re, zlib, subprocess, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py
OUT = pathlib.Path('/tmp/pdfchk'); OUT.mkdir(exist_ok=True)

CASES = [
    ('标准_含答案', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1', None),
    ('一页两卷_全开', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1', 1),
    ('一页两卷_多目标3对', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1&quota=3&sum=1,2,3,4,5,6,7,8,9,10&diff=1,2,3,4', 1),
    ('一页两卷_关集章', '?size=10&copies=4&per=2&ans=0&hdr=1&stamp=0&foot=1', 2),
    ('只留盘', '?size=10&copies=2&ans=0&hdr=0&stamp=0&foot=0&rule=0', 2),
    ('关说明_8x8', '?size=8&copies=2&ans=1&hdr=1&stamp=1&foot=1&rule=0', None),
    # 英文版：拉丁词不能像汉字那样逐字断行，说明块变高时最容易多挤出一页
    ('EN_标准_含答案', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&lang=en', None),
    ('EN_一页两卷_全开', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1&lang=en', 1),
    ('EN_一页两卷_多目标3对', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1&quota=3&sum=1,2,3,4,5,6,7,8,9,10&diff=1,2,3,4&lang=en', 1),
    ('EN_一页两卷_关集章', '?size=10&copies=4&per=2&ans=0&hdr=1&stamp=0&foot=1&lang=en', 2),
    ('EN_只留盘', '?size=10&copies=2&ans=0&hdr=0&stamp=0&foot=0&rule=0&lang=en', 2),
    ('EN_乘法_含答案', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&sum=&diff=&mul=12,24,36&lang=en', None),
]

def pages(pdf):
    """按 /Contents 引用逐页取内容流并解压，返回 (页数, [每页内容流字节数])。
    直接把 PDF 里所有 stream 一起解压会混进字体、对象子集之类的小流（十几字节），
    看不出到底哪一页是空的——必须跟着页面字典的 /Contents 走。"""
    data = pdf.read_bytes()
    objs = {}
    for m in re.finditer(rb'(\d+) 0 obj(.{0,400000}?)endobj', data, re.S):
        objs[int(m.group(1))] = m.group(2)
    sizes = []
    for num, body in objs.items():
        if not re.search(rb'/Type\s*/Page\b(?!s)', body):
            continue
        cm = re.search(rb'/Contents\s+(\d+) 0 R', body)
        if not cm:
            sizes.append(-1); continue
        c = objs.get(int(cm.group(1)), b'')
        sm = re.search(rb'stream\r?\n(.{1,4000000}?)endstream', c, re.S)
        if not sm:
            sizes.append(0); continue
        raw = sm.group(1)
        try:
            sizes.append(len(zlib.decompress(raw)))
        except Exception:
            sizes.append(len(raw))
    return len(sizes), sizes

def main():
    bad = []
    for name, q, want in CASES:
        pdf = OUT / (re.sub(r'\W', '_', name) + '.pdf')
        out = subprocess.run([EDGE, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                              '--print-to-pdf=' + str(pdf), '--virtual-time-budget=60000',
                              'file://' + str(SRC) + q], capture_output=True, text=True, timeout=300)
        if not pdf.exists():
            bad.append((name, '无 PDF', out.stderr[-160:])); continue
        n, sizes = pages(pdf)
        ok = want is None or n == want
        tiny = [i + 1 for i, s in enumerate(sizes) if s < 2000]
        flag = ('' if ok else f'  ← 期望 {want} 页') + (f'  ← 空白页 {tiny}' if tiny else '')
        print(f'  {name:22s} 页数 {n}  每页内容流(KB) {[round(s / 1024, 1) for s in sizes]}{flag}')
        if not ok or tiny:
            bad.append((name, n, sizes))
        pdf.unlink(missing_ok=True)
    print('异常', len(bad), bad)

if __name__ == '__main__':
    main()
