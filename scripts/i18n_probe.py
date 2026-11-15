#!/usr/bin/env python3
"""双语回归：把两组版面分别按中英渲染，检查纸面和界面上有没有
  1) 没被替换掉的 {占位符}   —— 模板写了 {n}、调用传了 {no} 这类错配（setWord 就踩过）
  2) 英文单复数错（"1 sets" / "2 pair"）
  3) 中文串漏翻：英文态下页面上还留着汉字（代码注释不算，只看渲染出来的文本）
  4) 拉丁词撑爆表格列（scrollWidth > clientWidth）

用法：python3 scripts/i18n_probe.py
"""
import json, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env import SRC, EDGE  # noqa: E402  路径解析见 scripts/env.py

CASES = [
    ('10目5 全开 含答案', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1'),
    ('10目5 全开 关说明', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=0'),
    ('8x8 3目标', '?size=8&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&sum=6,7&diff=2'),
    ('乘法 12/24/36', '?size=10&copies=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&sum=&diff=&mul=12,24,36'),
    ('1份 一页两卷', '?size=10&copies=2&per=2&ans=0&hdr=1&stamp=1&foot=1'),
    ('4份 一页两卷 12目标', '?size=10&copies=4&per=2&ans=0&hdr=1&stamp=1&foot=1&quota=3&sum=1,2,3,4,5,6,7,8,9,10&diff=1,2,3,4'),
    ('14目标 一页一卷', '?size=10&copies=1&per=1&ans=1&hdr=1&stamp=1&foot=1&rule=1&quota=3&sum=1,2,3,4,5,6,7,8,9,10&diff=1,2,3,4'),
    ('双人抢格', '?size=10&copies=1&ans=1&mode=duel&hdr=1&stamp=1&foot=1&rule=1'),
    ('6份 一页一卷', '?size=10&copies=6&ans=1&hdr=1&stamp=1&foot=1&rule=1'),
]

JS = r"""
var out={ph:[],plural:[],cjk:[],ovf:[],stat:'',hd:''};
/* 1) 未替换的占位符：{字母开头标识符} */
var walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);
var n,txt=[];
while((n=walker.nextNode())){
  var p=n.parentElement;
  if(!p||p.tagName==='SCRIPT'||p.tagName==='STYLE')continue;
  var s=n.nodeValue||'';
  if(s.indexOf('{')>=0)out.ph.push(s.replace(/\s+/g,' ').trim().slice(0,90));
  txt.push({el:p.tagName,s:s});
}
/* 2) 英文态单复数：数字 1 后面跟了复数名词，或 2+ 后面跟了单数名词。
      数字常包在 <b> 里，按文本节点查会漏，所以用 innerText 拿渲染后的整行。 */
var plain=document.body.innerText||'';
var re=/\b(\d+)\s+(sets?|sheets?|targets?|pairs?)\b/g,m;
while((m=re.exec(plain))){
  var num=+m[1],w=m[2];
  var plural=/s$/.test(w);
  if(document.documentElement.lang==='en'&&(num===1)===plural)
    out.plural.push(m[0]+' ← …'+plain.replace(/\s+/g,' ').slice(Math.max(0,m.index-26),m.index+22));
}
/* 3) 英文态漏翻：渲染文本里还有汉字。
      语言开关上的「中文」是故意的——切换按钮要用自己那种语言写，所以整块跳过 #segLang。 */
if(document.documentElement.lang==='en'){
  var w2=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null),x;
  while((x=w2.nextNode())){
    var pp=x.parentElement;
    if(!pp||pp.tagName==='SCRIPT'||pp.tagName==='STYLE')continue;
    if(pp.closest('#segLang'))continue;
    var ss=x.nodeValue||'';
    if(/[一-鿿]/.test(ss))out.cjk.push(pp.tagName+': '+ss.replace(/\s+/g,' ').trim().slice(0,80));
  }
}
/* 4) 表格列被拉丁词撑爆 */
[].forEach.call(document.querySelectorAll('th,td'),function(e){
  if(e.scrollWidth>e.clientWidth+1)out.ovf.push(e.tagName+'「'+e.textContent.replace(/\s+/g,' ').trim()+'」'+e.scrollWidth+'/'+e.clientWidth);
});
out.stat=(document.getElementById('stat').textContent||'').replace(/\s+/g,' ').trim();
var h=document.querySelector('.sheet .hd .ttl');out.hd=h?h.textContent.replace(/\s+/g,' ').trim():'-';
document.title='I18N::'+JSON.stringify(out);
"""


def run(qs, lang):
    src = SRC.read_text(encoding='utf-8')
    tmp = pathlib.Path('/tmp/i18n_probe.html')
    j = src.rfind('</head>')
    # 探针脚本要在页面自己那一段之后跑（它 boot 时才把版面画出来），所以挂 load 事件延一拍
    probe = ("<script>addEventListener('load',function(){setTimeout(function(){try{"
             + JS + "}catch(e){document.title='I18N::'+JSON.stringify({ph:['探针异常:'+e.message],plural:[],cjk:[],ovf:[],stat:'',hd:''});}},600)});</script>")
    tmp.write_text(src[:j] + '<style>body{background:#fff;margin:0}</style>' + probe + src[j:], encoding='utf-8')
    url = f'file://{tmp}{qs}' + ('' if 'lang=' in qs else f'&lang={lang}')
    r = subprocess.run([EDGE, '--headless', '--disable-gpu', '--window-size=1440,1200',
                        '--virtual-time-budget=25000', '--dump-dom', url],
                       capture_output=True, text=True, timeout=300)
    m = re.search(r'I18N::(\{.*?\})</title>', r.stdout, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


bad_total = 0
for name, qs in CASES:
    for lang in ('zh', 'en'):
        d = run(qs, lang)
        if d is None:
            print(f'  {name:22s} {lang}: 探针没跑起来')
            bad_total += 1
            continue
        issues = []
        if d['ph']:
            issues.append('未替换占位符 ' + str(sorted(set(d['ph']))[:4]))
        if d['plural']:
            issues.append('单复数 ' + str(sorted(set(d['plural']))[:3]))
        if d['cjk']:
            issues.append('漏翻 ' + str(sorted(set(d['cjk']))[:4]))
        if d['ovf']:
            issues.append('撑爆列 ' + str(sorted(set(d['ovf']))[:4]))
        bad_total += len(issues)
        tag = 'OK' if not issues else '×'
        print(f'  {name:22s} {lang}: {tag}  页眉「{d["hd"]}」 状态「{d["stat"][:74]}」')
        for it in issues:
            print('        ', it)
print('问题', bad_total)
sys.exit(1 if bad_total else 0)
