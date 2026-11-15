#!/usr/bin/env python3
"""版面格子尺寸扫描：不同 每页卷数 / 盘面 / 目标数 / 对数 / 版面块 组合下，
   量测最终每格毫米数、四边墨位、单格是否横向顶出、是否溢出。
   用法 python3 scripts/size_probe.py [过滤关键字] [--set sd|mul] [--mode quest|duel] [--quota 13|24] [--lang zh|en]
   --lang en 会把整页（含纸面）切到英文再扫：英文说明块更高、标签列更宽，
   格子尺寸和"单格横向顶出去"两条红线都要单独成立。"""
import json, re, html, subprocess, pathlib, sys

A = sys.argv[1:]
# 过滤词 = 第一个"既不是选项、也不是选项取值"的位置参数（'--set sd' 里的 sd 曾被当成过滤词，
# 结果 144 行明细全被过滤掉，只剩汇总行——异常统计不受影响，但看不到具体是哪一组）。
OPTS = {'--set', '--mode', '--quota'}
FILT = next((x for i, x in enumerate(A)
             if not x.startswith('--') and (i == 0 or A[i - 1] not in OPTS)), '')
def opt(name, dflt):
    for i, x in enumerate(A):
        if x == '--' + name:
            return A[i + 1]
        if x.startswith('--' + name + '='):
            return x.split('=', 1)[1]
    return dflt
SET, MODE, QUOTA, LANG = opt('set', 'sd'), opt('mode', 'quest'), opt('quota', '13'), opt('lang', 'zh')

# 选项取值写错时给一句人话，别只甩 KeyError('duel')——duel 是 --mode 的值不是 --set 的值，
# 这个错我自己犯过两次，traceback 里根本看不出是哪个 flag 写错。
VALID = {'set': ['sd', 'mul'], 'mode': ['quest', 'duel'],
         'quota': ['13', '24'], 'lang': ['zh', 'en']}


def require(name, val):
    if val in VALID[name]:
        return val
    where = [f'--{k}' for k, v in VALID.items() if val in v]
    sys.exit(f'--{name} 只认 {VALID[name]}，收到 {val!r}'
             + (f'（{val} 是 {",".join(where)} 的取值，flag 写串了）' if where else ''))


SET, MODE, QUOTA, LANG = require('set', SET), require('mode', MODE), \
    require('quota', QUOTA), require('lang', LANG)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py

T_SETS = {
    'sd': """[['少',{sum:[6,7],diff:[2],mul:[]},2],
        ['中',{sum:[6,7,8],diff:[2,3],mul:[]},5],
        ['多',{sum:[1,2,3,4,5,6,7,8,9,10],diff:[1,2,3,4],mul:[]},14]]""",
    'mul': """[['少',{sum:[],diff:[],mul:[6,8]},2],
        ['中',{sum:[6,7],diff:[2],mul:[12,24,36]},6],
        ['多',{sum:[6,7,8],diff:[2,3],mul:[2,3,4,6,8,9,12,16,18,24,36,48,63,72,81]},20]]""",
}[SET]
Q_LIST = {'13': '[1,3]', '24': '[2,4]'}[QUOTA]

JS = """<script>
addEventListener('load',function(){
 var mm=96/25.4,out=[];
 var T=__TSET__;
 var B=[['全开',{hdr:1,stamp:1,foot:1,rule:1}],
        ['关说明',{hdr:1,stamp:1,foot:1,rule:0}],
        ['关集章',{hdr:1,stamp:0,foot:1,rule:1}],
        ['关页眉',{hdr:0,stamp:1,foot:1,rule:1}],
        ['关页脚',{hdr:1,stamp:1,foot:0,rule:1}],
        ['只留盘',{hdr:0,stamp:0,foot:0,rule:0}]];
 for(var pe=1;pe<=2;pe++)for(var sz=0;sz<2;sz++)for(var t=0;t<T.length;t++)for(var qi=0;qi<2;qi++)for(var bi=0;bi<B.length;bi++){
   var tg=T[t][1],bl=B[bi][1];
   S.per=pe;S.size=[8,10][sz];S.mode='__MODE__';S.quota=__Q__[qi];
   S.sum=tg.sum.slice();S.diff=tg.diff.slice();S.mul=tg.mul.slice();
   S.hdr=!!bl.hdr;S.stamp=!!bl.stamp;S.foot=!!bl.foot;S.rule=!!bl.rule;
   S.copies=1;S.withAns=false;S.seed=31337+t*17+qi*5+sz*3+bi;
   S.lang='__LANG__';setKLang(S.lang);
   var rec={id:'卷'+pe+'/'+[8,10][sz]+'/'+T[t][0]+'('+tg.sum.length+tg.diff.length+tg.mul.length+'目)/'+__Q__[qi]+'对/'+B[bi][0]};
   try{render();}catch(e){rec.err=''+e.message;out.push(rec);continue;}
   var fl=document.querySelector('.fail');
   if(fl){rec.fail=(fl.textContent||'').slice(0,28);out.push(rec);continue;}
   var c0=document.querySelector('.sheet:not(.answers) table.board td:not(.rl)');
   rec.cell=c0?Math.round(c0.getBoundingClientRect().width/mm*10)/10:0;
   rec.over=Math.round(overPct()*10)/10;
   rec.TOLF=Math.round(TOLF*100)/100;   /* 这台浏览器上「能装下」的实际判据（噪声底容差） */
   rec.FIT=Math.round(FIT*10)/10;
   var w={t:1e9,b:1e9,l:1e9,r:1e9},ss=document.querySelectorAll('.sheet:not(.answers)');
   for(var i=0;i<ss.length;i++){var sr=ss[i].getBoundingClientRect(),el=ss[i].querySelectorAll('*');
     for(var k=0;k<el.length;k++){var er=el[k].getBoundingClientRect();
       if(er.width<1||er.height<1)continue;
       w.t=Math.min(w.t,er.top-sr.top);w.b=Math.min(w.b,sr.bottom-er.bottom);
       w.l=Math.min(w.l,er.left-sr.left);w.r=Math.min(w.r,sr.right-er.right);}}
   rec.ink=[+(w.t/mm).toFixed(1),+(w.b/mm).toFixed(1),+(w.l/mm).toFixed(1),+(w.r/mm).toFixed(1)].join('/');
   var bb=document.querySelector('.sheet:not(.answers) table.board');
   rec.board=bb?Math.round(bb.getBoundingClientRect().width/mm*10)/10+'x'+Math.round(bb.getBoundingClientRect().height/mm*10)/10:'-';
   /* 单格里横向顶出去（scrollWidth>clientWidth）overBox 看不见：它没超出版心，只是压到隔壁列。
      半页集章表最容易犯这个毛病，一犯就会折行、行高翻倍、盘面被压到下限。 */
   var ov=0,cs=document.querySelectorAll('.sheet:not(.answers) td,.sheet:not(.answers) th');
   for(var z=0;z<cs.length;z++){var e2=cs[z];if(e2.scrollWidth>e2.clientWidth+1)ov++;}
   rec.ovf=ov;
   out.push(rec);
 }
 document.title='PROBE::'+JSON.stringify(out);
});
</script>"""

def main():
    src = SRC.read_text(encoding='utf-8')
    js = JS.replace('__TSET__', T_SETS).replace('__MODE__', MODE).replace('__Q__', Q_LIST).replace('__LANG__', LANG)
    j = src.rfind('</body>')
    tmp = pathlib.Path(f'/tmp/size_probe_{SET}_{MODE}_{QUOTA}_{LANG}.html')
    tmp.write_text(src[:j] + js + src[j:], encoding='utf-8')
    print(f'# set={SET} mode={MODE} quota={QUOTA} lang={LANG}')
    d = subprocess.run([EDGE, '--headless', '--disable-gpu', '--window-size=1440,1200',
                        '--virtual-time-budget=60000', '--dump-dom', f'file://{tmp}'],
                       capture_output=True, text=True, timeout=600).stdout
    m = re.search(r'<title>(.*?)</title>', d, re.S)
    t = html.unescape(m.group(1))
    rows = json.loads(t.split('PROBE::')[1])
    filt = FILT
    ink = lambda r: [float(x) for x in r['ink'].split('/')]
    bad = [r for r in rows if 'err' not in r and 'fail' not in r and (r['over'] > max(0.2, r.get('TOLF', 0.2)) or r.get('ovf')
           or min(ink(r)[0], ink(r)[1]) < 11.5 or min(ink(r)[2], ink(r)[3]) < 12.5)]
    print(f"组合 {len(rows)}  异常 {len(bad)}  抛错 {sum(1 for r in rows if 'err' in r)}  "
          f"生成失败 {sum(1 for r in rows if 'fail' in r)}")
    print(f"单格横向顶出去的组合 {sum(1 for r in rows if r.get('ovf'))}")
    for r in rows:
        if filt and filt not in r['id']:
            continue
        if 'err' in r:
            print(f"  {r['id']:44s} 抛错 {r['err']}")
            continue
        if 'fail' in r:
            print(f"  {r['id']:44s} 生成失败（容量不足，版面不参与量测）")
            continue
        print(f"  {r['id']:44s} 每格 {r['cell']:5.1f}mm  盘面 {r['board']:14s} 墨位 {r['ink']:18s} 收缩 {r['FIT']}  余 {r['over']}  顶格 {r.get('ovf')}")
    for r in bad[:10]:
        print('  !!', r)

main()
