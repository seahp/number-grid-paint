#!/usr/bin/env python3
"""版面竖向分配扫描：量「页眉 / 说明 / 盘面 / 集章表 / 页脚」各自落在版心的哪一段，
以及块与块之间、最后一块与纸底之间留了多少空白。

用法：
    python3 scripts/gap_probe.py            # 8 种 说明×集章表×页脚 组合 × 2 个尺寸
    python3 scripts/gap_probe.py 10         # 只看 10×10

判读口径（版心高 272mm）：
  · 勾了集章表/页脚 → 这些块应当**贴到 272mm**（gapBot≈0），盘面拿剩下的中间空间；
  · 都没勾          → 盘面上下留白应当大致相等（居中）；
  · 说明块在顶部，它到盘面之间的空白 = 中间余量的一半，不该出现"盘面贴顶、底下空一截"。
"""
import json, re, html, subprocess, sys, pathlib, itertools

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py

JS = """<script>
addEventListener('load',function(){
 var mm=96/25.4,out=[];
 try{
  var s=document.querySelector('.sheet:not(.answers)');
  var cs=getComputedStyle(s),pt=parseFloat(cs.paddingTop)||0,pb=parseFloat(cs.paddingBottom)||0;
  var pl=parseFloat(cs.paddingLeft)||0;
  var box={t:s.getBoundingClientRect().top+pt,l:s.getBoundingClientRect().left+pl,
           b:s.getBoundingClientRect().bottom-pb};
  var kids=s.children,vis=[];
  for(var k=0;k<kids.length;k++){var e=kids[k],r=e.getBoundingClientRect();
    if(r.height<1||getComputedStyle(e).display==='none')continue;
    vis.push({n:(e.className||e.tagName).split(' ')[0],
      t:+((r.top-box.t)/mm).toFixed(1),b:+((r.bottom-box.t)/mm).toFixed(1)});}
  var bd=s.querySelector('table.board'),br=bd?bd.getBoundingClientRect():null;
  /* 第一格是行号栏（固定 5mm），量数字格才代表每格尺寸 */
  var cell=s.querySelector('table.board td:not(.rl)');
  out.push({id:location.search.replace(/^\\?/,''),cls:s.className,
    cell:cell?+(cell.getBoundingClientRect().width/mm).toFixed(1):null,
    board:br?+(br.width/mm).toFixed(1)+'x'+(+(br.height/mm).toFixed(1)):'-',
    blocks:vis,over:+overPct().toFixed(2),FIT:+FIT.toFixed(1),
    gapBot:+((box.b-(vis.length?vis[vis.length-1].b*mm+box.t:box.b))/mm).toFixed(1)});
 }catch(err){out.push({id:location.search,err:String(err).slice(0,90)});}
 document.title='PROBE::'+JSON.stringify(out);
});
</script>"""

NAMES = {'hd': '页眉', 'rulebar': '说明', 'boardzone': '盘面', 'taskzone': '集章表', 'ft': '页脚'}


def run(q):
    src = SRC.read_text(encoding='utf-8')
    j = src.rfind('</body>')
    tmp = pathlib.Path('/tmp/gap_probe.html')
    tmp.write_text(src[:j] + JS + src[j:], encoding='utf-8')
    d = subprocess.run([EDGE, '--headless', '--disable-gpu', '--window-size=1440,1200',
                        '--virtual-time-budget=15000', '--dump-dom', f'file://{tmp}?{q}'],
                       capture_output=True, text=True, timeout=300).stdout
    m = re.search(r'<title>(.*?)</title>', d, re.S)
    if not m:
        return [{'err': 'no title'}]
    t = html.unescape(m.group(1))
    return json.loads(t[len('PROBE::'):]) if t.startswith('PROBE::') else [{'raw': t[:300]}]


def main():
    size = sys.argv[1] if len(sys.argv) > 1 else '10'
    tgt = sys.argv[2] if len(sys.argv) > 2 else '&sum=6,7&diff=2'
    for rule, stamp, foot in itertools.product([1, 0], repeat=3):
        q = (f'size={size}&copies=1&ans=0&seed=31337&hdr=1&per=1'
             f'&rule={rule}&stamp={stamp}&foot={foot}' + tgt)
        r = run(q)[0]
        if 'err' in r:
            print(f'说明{rule} 集章{stamp} 页脚{foot}  抛错 {r["err"]}')
            continue
        seg = ' + '.join(f'{NAMES.get(b["n"], b["n"])} {b["t"]}~{b["b"]}' for b in r['blocks'])
        last = r['blocks'][-1]['n'] if r['blocks'] else '-'
        print(f'说明{rule} 集章{stamp} 页脚{foot} | {r["cls"]:6s} 每格 {r["cell"]}mm 盘面 {r["board"]} '
              f'收缩 {r["FIT"]} 余 {r["over"]} 末块={last} 离底 {r["gapBot"]}mm')
        print(f'      {seg}')


main()
