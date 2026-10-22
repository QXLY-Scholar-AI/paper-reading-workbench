"""Package a host-written draft and its evidence ledger; does not generate research."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re
import shutil

REQUIRED = {'abstract','introduction','literature','methods','results','discussion','conclusion'}

def build(card_path: str, out: str) -> dict:
    src=Path(card_path).resolve(); c=json.loads(src.read_text(encoding='utf-8-sig'))
    if c.get('schema')!='paper-manuscript/v1' or not re.fullmatch('[a-f0-9]{64}',c.get('source_sha256','')):
        raise ValueError('稿件格式或核心PDF指纹无效')
    if not c.get('topic') or not c.get('title') or c.get('kind') not in {'review','proposal','empirical'}:
        raise ValueError('需要课题、标题和稿件类型')
    if c['kind']=='empirical' and (c.get('user_data',{}).get('provided') is not True or not c['user_data'].get('description') or not c['user_data'].get('locator')):
        raise ValueError('实证稿需要已提供的用户研究数据及来源')
    cores=c.get('core_papers',[])
    if c['source_sha256'] not in cores or any(not re.fullmatch('[a-f0-9]{64}',s) for s in cores):
        raise ValueError('核心文献清单需包含归档PDF指纹')
    sources={}
    for s in c['sources']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',s['id']) or s['id'] in sources or s.get('level') not in {'full_text','abstract','introduction','metadata'} or not s.get('citation') or not s.get('locator') or not s.get('note') or s.get('verified') is not True:
            raise ValueError('材料账本缺失、重复或未核验')
        sources[s['id']]=s
    sections=c['sections']; ids=[s['id'] for s in sections]
    if len(ids)!=len(set(ids)) or not REQUIRED.issubset(ids):
        raise ValueError('论文结构缺失或章节重复')
    used=set()
    def check_refs(refs):
        for key in refs:
            if key not in sources or sources[key]['level']=='metadata':
                raise ValueError('引用不存在或仅有题录，不能支撑正文/插图')
            used.add(key)
    for s in sections:
        if not s.get('title') or not s.get('paragraphs'):raise ValueError('章节不能是空模板')
        for p in s['paragraphs']:
            if not p.get('text') or not p.get('locator') or not isinstance(p.get('citations'),list):raise ValueError('段落需正文、证据位置/分析说明和引用清单')
            check_refs(p['citations'])
    images=[]
    for i,f in enumerate(c.get('figures',[]),1):
        path=(src.parent/f['file']).resolve()
        if src.parent not in path.parents or path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'} or not path.is_file() or not f.get('caption') or not f.get('source_ids'):
            raise ValueError('插图需包内图片、来源与图注')
        check_refs(f['source_ids']); images.append((path,f,'images/figure-'+str(i)+path.suffix.lower()))
    dest=Path(out).resolve()
    if dest.exists() and any(dest.iterdir()):raise ValueError('请使用新的空目录，保留旧稿')
    dest.mkdir(parents=True,exist_ok=True)
    e=html.escape
    md=['# '+c['title'],'','> 论文初稿 beta · '+c['kind'],'','关键词：'+'；'.join(c.get('keywords',[])),'']
    blocks=['<h1>'+e(c['title'])+'</h1><p>论文初稿 beta · '+e(c['kind'])+'</p><p>关键词：'+e('；'.join(c.get('keywords',[])))+'</p>']
    for s in sections:
        md+=['## '+s['title'],''];blocks+=['<h2>'+e(s['title'])+'</h2>']
        for p in s['paragraphs']:
            cite=' '.join('['+r+']' for r in p['citations']);md += [p['text']+' '+cite,'']
            blocks+=['<p>'+e(p['text']).replace('\n','<br>')+' '+ ' '.join('<a href="#ref-'+e(r)+'">['+e(r)+']</a>' for r in p['citations'])+'</p><details><summary>证据位置 / 分析说明</summary>'+e(p['locator'])+'</details>']
    for path,f,rel in images:
        (dest/'images').mkdir(exist_ok=True);shutil.copy2(path,dest/rel)
        md+=['!['+f['caption'].replace(']','')+']('+rel+')',''];blocks+=['<figure><img src="'+rel+'"><figcaption>'+e(f['caption'])+' · '+e(', '.join(f['source_ids']))+'</figcaption></figure>']
    md+=['## 参考文献',''];blocks+=['<h2>参考文献</h2>']
    for key,s in sources.items():
        if key in used:
            md+=['['+key+'] '+s['citation'],''];blocks+=['<p id="ref-'+e(key)+'">['+e(key)+'] '+e(s['citation'])+'</p>']
    md+=['## 待补与材料边界','']+['- '+str(g) for g in c.get('gaps',[])]
    blocks+=['<h2>待补与材料边界</h2>']+['<p>'+e(str(g))+'</p>' for g in c.get('gaps',[])]
    blocks+=['<h2>材料账本</h2>']
    for key,s in sources.items():
        blocks+=['<details><summary>['+e(key)+'] '+e(s['citation'])+' · '+e(s['level'])+'</summary><p>'+e(s['locator'])+'</p><p>'+e(s['note'])+'</p></details>']
    (dest/'manuscript.md').write_text('\n'.join(md),encoding='utf-8')
    (dest/'sources.json').write_text(json.dumps(c['sources'],ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(c['title'])+'</title><style>body{max-width:920px;margin:40px auto;padding:0 24px;background:#fffdf8;color:#253e35;font:16px/1.9 "Microsoft YaHei",sans-serif}h1,h2{line-height:1.5}p{white-space:pre-wrap}details{font-size:13px;background:#edf2e8;padding:10px;margin:8px 0}img{max-width:100%}a{color:#286047}</style><body><nav><a href="manuscript.md" download>下载 Markdown</a> · <a href="sources.json" download>下载材料账本</a></nav>'+''.join(blocks)+'</body></html>'
    from page_theme import apply_theme
    (dest/'manuscript.html').write_text(apply_theme(page),encoding='utf-8')
    report={'source_sha256':c['source_sha256'],'topic':c['topic'],'title':c['title'],'kind':c['kind'],'sources':len(sources),'cited_sources':len(used),'figures':len(images),'checks':'结构与引用关联检查；不代表自动核验科学结论','markdown_sha256':hashlib.sha256((dest/'manuscript.md').read_bytes()).hexdigest()}
    (dest/'draft-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--card',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:print(json.dumps(build(a.card,a.out),ensure_ascii=False))
    except (ValueError,KeyError,OSError,TypeError) as ex:p.exit(2,str(ex)+'\n')
