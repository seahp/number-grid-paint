#!/usr/bin/env python3
"""把生成器的某个版面配置直接导成 PDF（不碰浏览器窗口，也不受屏显缩放影响）。

用法：
    python3 scripts/pdf_export.py '<query>' 输出.pdf
    python3 scripts/pdf_export.py '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1' out/标准卷.pdf

query 里能带的参数（和页面地址栏一致，缺省就用页面默认值）：
    size=8|10   mode=quest|duel   quota=1..4   copies=1..4   per=1|2   seed=数字
    hdr/stamp/foot/rule/ans = 0|1     sum=6,7,8  diff=2,3  mul=12,24
    adj=-8..8（手动格子）   copies>1 时份数会一次出多卷

为什么要单独一个导出脚本：版面是"在屏幕上解出来再烘进 PDF"的，
以前窄窗口命中 scale(.5) 预览规则时量测会算出假溢出，格子被压到 5.6mm 下限，
导出的 PDF 就跟着一起小。无头导出固定 1440px 视口，且量测已按缩放比折算，两边都对得上。
"""
import re, html, subprocess, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pdf_check import pages, SRC, EDGE  # noqa: E402

TITLE = """<script>
addEventListener('load',function(){
 setTimeout(function(){
  var s=document.querySelector('.sheet:not(.answers)');
  var cell=0,over='-',stg='-',k='1';
  if(s){k=scaleOf(s).toFixed(2);cell=cellMM();over=overPct();stg=STG;}
  var st=(document.getElementById('stat').textContent||'').replace(/\\s+/g,' ');
  document.title='PROBE::'+JSON.stringify({cell:cell,over:over,stg:stg,k:+k,stat:st});
 },300);
});
</script>"""


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    qs, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
    if not qs.startswith('?'):
        qs = '?' + qs

    # 第一趟：读回版面解（每格毫米数、余量、紧张度），确认导出前版面确实是放得开的
    src = SRC.read_text(encoding='utf-8')
    j = src.rfind('</body>')
    tmp = pathlib.Path('/tmp/pdf_export_probe.html')
    tmp.write_text(src[:j] + TITLE + src[j:], encoding='utf-8')
    d = subprocess.run([EDGE, '--headless', '--disable-gpu', '--window-size=1440,1200',
                        '--virtual-time-budget=60000', '--dump-dom', f'file://{tmp}{qs}'],
                       capture_output=True, text=True, timeout=300).stdout
    m = re.search(r'<title>(.*?)</title>', d, re.S)
    info = {}
    if m:
        try:
            info = json_loads(html.unescape(m.group(1)))
        except Exception as e:
            print('  读版面解失败（不影响导出）：', e)
    if info:
        cell = float(info.get('cell') or 0)
        over = info.get('over')
        st = info.get('stat', '')
        if not cell:
            print('  ★ 页面没出盘面（多半是这套配置超出格子容量），PDF 里是拒答提示：' + st[:160])
        else:
            print(f"  版面：每格 {cell}mm  余量 {over}mm  紧张度 {info.get('stg')}  缩放比 {info.get('k')}")
            try:
                if float(over) > 0.05:
                    print('  ★ 版面仍挤：' + st[-140:])
            except (TypeError, ValueError):
                pass

    # 第二趟：无头打印导出
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([EDGE, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                        '--virtual-time-budget=60000', f'--print-to-pdf={out}',
                        f'file://{SRC}{qs}'], capture_output=True, text=True, timeout=300)
    if not out.exists():
        print('  导出失败：', r.stderr[-300:])
        sys.exit(1)
    n, sizes = pages(out)
    tiny = [i + 1 for i, s in enumerate(sizes) if s < 2000]
    print(f"  已导出 {out}  页数 {n}  每页内容流(KB) {[round(s/1024, 1) for s in sizes]}"
          + (f'  ← 疑似空白页 {tiny}' if tiny else ''))


def json_loads(t):
    import json
    return json.loads(t.split('PROBE::')[1])


main()
