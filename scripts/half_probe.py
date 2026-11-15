#!/usr/bin/env python3
"""用法: python3 half_probe.py "<url query>"  —— 无头 Edge 量测一页两卷版面"""
import json, re, html, subprocess, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py

JS = """<script>
addEventListener('load',function(){
 var mm=96/25.4,out={q:location.search,FIT:FIT,over:overPct(),sheets:[]};
 var ss=document.querySelectorAll('.sheet');
 for(var i=0;i<ss.length;i++){
   var s=ss[i],r=s.getBoundingClientRect(),ans=s.classList.contains('answers');
   var rec={cls:ans?'A':(s.classList.contains('two')?'2':'1'),
     w:+(r.width/mm).toFixed(1),h:+(r.height/mm).toFixed(1),halves:[]};
   var boxes=s.querySelectorAll('.half').length?s.querySelectorAll('.half'):[s];
   for(var j=0;j<boxes.length;j++){
     var b=boxes[j],br=b.getBoundingClientRect(),vis=[],kids=b.children;
     for(var k=0;k<kids.length;k++){var e=kids[k];
       if(e.getBoundingClientRect().height>0&&getComputedStyle(e).display!=='none')vis.push(e);}
     var last=vis[vis.length-1];
     var bd=b.querySelector('table.board'),bb=bd?bd.getBoundingClientRect():null;
     rec.halves.push({over:+overBox(b).toFixed(2),
       h:+(br.height/mm).toFixed(1),
       blocks:vis.map(function(v){return (v.className||v.tagName).split(' ')[0]+':'+
         Math.round(v.getBoundingClientRect().height/mm*10)/10;}).join('+'),
       board:bb?+(bb.width/mm).toFixed(1)+'x'+(+(bb.height/mm).toFixed(1)):'-',
       botGap:+((br.bottom-last.getBoundingClientRect().bottom)/mm).toFixed(2)});
   }
   out.sheets.push(rec);
 }
 /* 墨位离纸边：只看学生页 */
 var w={t:1e9,b:1e9,l:1e9,r:1e9};
 var st=document.querySelectorAll('.sheet:not(.answers)');
 for(var a=0;a<st.length;a++){var sr=st[a].getBoundingClientRect(),el=st[a].querySelectorAll('*');
   for(var c=0;c<el.length;c++){var er=el[c].getBoundingClientRect();
     if(er.width<1||er.height<1)continue;
     w.t=Math.min(w.t,er.top-sr.top);w.b=Math.min(w.b,sr.bottom-er.bottom);
     w.l=Math.min(w.l,er.left-sr.left);w.r=Math.min(w.r,sr.right-er.right);}}
 out.ink={t:+(w.t/mm).toFixed(2),b:+(w.b/mm).toFixed(2),l:+(w.l/mm).toFixed(2),r:+(w.r/mm).toFixed(2)};
 var cut=document.querySelector('.cut');
 out.cutY=cut?+((cut.getBoundingClientRect().top-st[0].getBoundingClientRect().top)/mm).toFixed(1):null;
 out.stat=document.getElementById('stat').textContent;
 out.diag=(document.getElementById('diag').textContent||'').slice(0,300);
 document.title='PROBE::'+JSON.stringify(out);
});
</script>"""

def run(q):
    src = SRC.read_text(encoding='utf-8')
    j = src.rfind('</body>')
    tmp = pathlib.Path('/tmp/half_probe.html')
    tmp.write_text(src[:j] + JS + src[j:], encoding='utf-8')
    d = subprocess.run([EDGE, '--headless', '--disable-gpu', '--window-size=1440,1200',
                        '--virtual-time-budget=8000', '--dump-dom', f'file://{tmp}?{q}&diag=1'],
                       capture_output=True, text=True, timeout=180).stdout
    m = re.search(r'<title>(.*?)</title>', d, re.S)
    if not m:
        return {'error': 'no title', 'html_len': len(d)}
    t = html.unescape(m.group(1))
    return json.loads(t[len('PROBE::'):]) if t.startswith('PROBE::') else {'raw': t[:400]}

if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), ensure_ascii=False, indent=1))
