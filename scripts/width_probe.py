#!/usr/bin/env python3
"""窗口宽度无关性回归：同一批配置分别在多个视口宽度下解版面，格子 / FIT / STG / 余量必须完全一致，
   且 ➕➖ 真的能改格子。≤900px 时屏显预览会 transform 缩小整张纸，比例由 JS 按窗口宽度算
   （1440→不缩、900→≈1.0、700→≈0.85、520→≈0.62、400→≈0.47），所以这里正好覆盖一串 k。
   背景：getBoundingClientRect 给的是缩放后的像素，getComputedStyle 的 padding 是布局像素，
   两者混用会凭空多出 padding×(1−k) 的假溢出（左右各 6.5mm、上 6mm），而且它跟格子大小无关，
   二分怎么收都收不掉 → 盘面砸到 5.6mm 下限、三档全"放不下"、➕➖ 集体失效。
   用法 python3 scripts/width_probe.py [宽度...] [lang=zh|en]（默认 1440 700，中文）
   lang=en 整页切英文再跑同一批配置：验证"窗口多宽都解出同一个格子"这条性质与语言无关。"""
import json, re, html, subprocess, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py
WS = [x for x in sys.argv[1:] if x.isdigit()] or ['1440', '700']
LANG = next((x.split('=', 1)[1] for x in sys.argv[1:] if x.startswith('lang=')), 'zh')

# 每行：per, size, hdr, stamp, foot, rule, sum, diff, mul, adj
CFG = """[
 [1,10,1,1,1,1,[6,7,8],[2,3],[],0],
 [1,10,1,1,1,1,[1,2,3,4,5,6,7,8,9,10],[1,2,3,4],[],0],
 [1,10,1,1,1,1,[6,7,8],[2,3],[],2],
 [1,10,1,1,1,1,[6,7,8],[2,3],[],-3],
 [1,10,1,1,1,0,[6,7,8],[2,3],[],0],
 [1,10,1,1,0,1,[6,7,8],[2,3],[],0],
 [1,10,0,0,1,0,[6,7,8],[2,3],[],0],
 [1,10,0,0,1,0,[6,7,8],[2,3],[],4],
 [1,10,0,1,1,0,[1,2,3,4,5,6,7,8,9,10],[1,2,3,4],[],0],
 [1,8,1,1,1,1,[6,7,8],[2,3],[],0],
 [1,8,0,0,1,0,[6,7],[],[],0],
 [1,10,1,1,1,1,[6,7],[2],[],0],
 [2,10,0,0,1,0,[6,7,8],[2,3],[],0],
 [2,10,0,1,1,0,[6,7,8],[2,3],[],0],
 [2,10,0,1,0,0,[6,7,8],[2,3],[],0],
 [2,10,0,1,1,0,[1,2,3,4,5,6],[1,2],[],0]
]"""

JS = """<script>
addEventListener('load',function(){
 var out=[],CFG=__CFG__;
 for(var c=0;c<CFG.length;c++){
   var g=CFG[c];
   S.per=g[0];S.size=g[1];S.hdr=!!g[2];S.stamp=!!g[3];S.foot=!!g[4];S.rule=!!g[5];
   S.sum=g[6].slice();S.diff=g[7].slice();S.mul=g[8].slice();S.cellAdj=g[9];
   S.mode='quest';S.quota=3;S.copies=1;S.withAns=false;S.seed=31337+c;
   S.lang='__LANG__';setKLang(S.lang);
   var id='卷'+g[0]+'/'+g[1]+'目'+(g[6].length+g[7].length+g[8].length)+"/H"+g[2]+g[3]+g[4]+g[5]+(g[9]?'adj'+(g[9]>0?'+':'')+g[9]:'');
   var rec={id:id};
   try{render();}catch(e){rec.err=''+e.message;out.push(rec);continue;}
   if(document.querySelector('.fail')){rec.fail=1;out.push(rec);continue;}
   rec.cell=cellMM();rec.FIT=Math.round(FIT*10)/10;rec.STG=STG;rec.over=Math.round(overPct()*10)/10;
   rec.k=scaleOf(document.querySelector('.sheet:not(.answers)'));
   out.push(rec);
 }
 document.title='PROBE::'+JSON.stringify(out);
});
</script>"""


def run(width):
    src = SRC.read_text(encoding='utf-8')
    j = src.rfind('</body>')
    tmp = pathlib.Path(f'/tmp/width_probe_{width}.html')
    tmp.write_text(src[:j] + JS.replace('__CFG__', CFG).replace('__LANG__', LANG) + src[j:], encoding='utf-8')
    d = subprocess.run([EDGE, '--headless', '--disable-gpu', f'--window-size={width},1200',
                        '--virtual-time-budget=90000', '--dump-dom', f'file://{tmp}'],
                       capture_output=True, text=True, timeout=900).stdout
    m = re.search(r'<title>(.*?)</title>', d, re.S)
    return {r['id']: r for r in json.loads(html.unescape(m.group(1))[7:])}


print('# 视口宽度对照：' + ' / '.join(w + 'px' for w in WS))
R = [run(w) for w in WS]
A = R[0]
bad = 0
for k in A:
    xs = [r.get(k, {}) for r in R]
    x = xs[0]
    if any(y.get('fail') or 'err' in y for y in xs):
        print(f"  {k:26s} 生成失败/抛错（版面不参与量测）")
        continue
    same = all(all(x.get(f) == y.get(f) for f in ('cell', 'FIT', 'STG', 'over')) for y in xs)
    if not same:
        bad += 1
    print(f"  {k:26s} " + '  |  '.join(
        f"{w}: {y['cell']:5.1f}mm FIT{y['FIT']:4} STG{y['STG']} 余{y['over']:4} k={y['k']:.2f}"
        for w, y in zip(WS, xs)) + ('  一致' if same else '  ★不一致'))
print(f"配置 {len(A)}  不一致 {bad}")
sys.exit(1 if bad else 0)
