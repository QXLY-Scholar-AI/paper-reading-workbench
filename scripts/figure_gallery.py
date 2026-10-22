"""Extract figure candidates and package AI-reviewed, context-grounded R galleries.
No model calls, no data downloads, no dependency installation.
"""
from pathlib import Path
import argparse, base64, hashlib, html, json, re, shutil, subprocess, sys, io, zipfile
import pymupdf as fitz

SCHEMA='paper-figure-gallery/v1'
MODES={'raw_data':'原始数据重绘','reported_values':'文中数值重绘','digitized':'图像数字化近似','template':'示例数据模板'}
def dump(p,x):
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def scan(pdf,out):
    pdf=Path(pdf).resolve(); out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf); figures=[]; texts=[p.get_text() for p in doc]
    for n,page in enumerate(doc):
        blocks=page.get_text('blocks'); graphics=[fitz.Rect(x['rect']) for x in page.get_drawings() if x['rect'].width>30 and x['rect'].height>20]
        # Text extraction may omit image blocks in newer PyMuPDF versions.
        # Image placement is available independently of those text flags.
        graphics += [fitz.Rect(im['bbox']) for im in page.get_image_info()]
        for b in blocks:
            if b[6]!=0:continue
            cap=b[4].strip(); m=re.match(r'^(?:Figure|Fig\.?|图)\s*([SＡ-ＺA-Za-z]?\d+)[.．:：\s]',cap)
            if not m:continue
            c=fitz.Rect(b[:4]); candidates=[r for r in graphics if r.width>100 and r.height>60 and abs(r.y1-c.y0)<35 and r.x0<c.x0+30 and r.x1>c.x0+80]
            if candidates:
                box=max(candidates,key=lambda r:r.get_area()); method='graphic-frame-near-caption'; confidence='candidate'
            else:
                near=[r for r in graphics if r.y1<=c.y0+5 and r.y1>c.y0-400 and r.x0<c.x1 and r.x1>c.x0]
                if not near or max(r.y1 for r in near)<c.y0-80:continue
                box=fitz.Rect(near[0])
                for r in near[1:]:box|=r
                method='graphics-union-needs-review';confidence='low'
            box=fitz.Rect(box.x0-3,box.y0-3,box.x1+3,box.y1+3)&page.rect
            fid='F'+m.group(1); fid=re.sub(r'[^A-Za-z0-9_-]','',fid)
            if any(f['id']==fid for f in figures):fid+='P'+str(n+1)
            crop=out/(fid+'-original.png');page.get_pixmap(clip=box,matrix=fitz.Matrix(2,2),alpha=False).save(crop)
            page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False).save(out/('page-'+str(n+1)+'.png'))
            mentions=[]
            for j,t in enumerate(texts):
                for q in re.split(r'\n\s*\n',t):
                    if re.search(r'(?:Fig(?:ure)?\.?|图)\s*'+re.escape(m.group(1))+r'(?!\d)',q):
                        mentions.append({'page':j+1,'text':q[:8000]})
            figures.append(dict(id=fid,label='Figure '+m.group(1),page=n+1,bbox=list(box),crop=crop.name,caption=cap,detection=method,confidence=confidence,reviewed=False,mentions=mentions))
    clues=[{'page':i+1,'text':t[:10000]} for i,t in enumerate(texts) if re.search(r'data.shar|data.avail|repository|dataverse|data.access|数据|github',t,re.I)]
    result={'schema':'paper-figure-candidates/v1','source_pdf':str(pdf),'sha256':sha(pdf),'pages':len(doc),'figures':figures,'data_clues':clues,'warning':'候选并非最终图，请逐图目视核对并先精读全文。'}
    dump(out/'candidates.json',result); (out/'fulltext.txt').write_text('\n\n'.join('=== PDF '+str(i+1)+' ===\n'+t for i,t in enumerate(texts)),encoding='utf-8')
    return {'candidates':len(figures),'pages':len(doc),'out':str(out)}

def resolve(base,name):
    p=Path(name);return p.resolve() if p.is_absolute() else (base/p).resolve()
def validate(card,base):
    if card.get('schema')!=SCHEMA:raise ValueError('unsupported gallery schema')
    paper=card['paper'];pdf=Path(paper['source_pdf'])
    if not pdf.is_file() or sha(pdf)!=paper['sha256']:raise ValueError('source PDF missing or hash mismatch')
    if not resolve(base,card['reading_record']).is_file():raise ValueError('先精读：reading_record不存在')
    with fitz.open(pdf) as doc:
        pages=len(doc); page_texts=[p.get_text() for p in doc]
    normalize=lambda s:''.join(c.casefold() for c in s if c.isalnum())
    ids=set()
    for f in card['figures']:
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',f['id']) or f['id'] in ids:raise ValueError('unsafe or duplicate figure id')
        ids.add(f['id'])
        if type(f['page']) is not int or not 1<=f['page']<=pages:raise ValueError('invalid physical page')
        if f['mode'] not in MODES or not f.get('interpretation') or not f.get('caption'):raise ValueError('missing interpretation/caption/mode')
        if not f.get('context') or any(not x.get('quote') or not 1<=x.get('page',0)<=pages for x in f['context']):raise ValueError('先精读：逐图原文语境不能为空')
        if any(normalize(x['quote']) not in normalize(page_texts[x['page']-1]) for x in f['context']):raise ValueError('原文语境与标注页不匹配')
        if f.get('reviewed') is not True:raise ValueError('figure must be visually and semantically reviewed')
        if not f.get('data',{}).get('source') or not f['data'].get('status'):raise ValueError('data provenance required')
        for p in [f['crop'],f['r_script']]+f.get('files',[]):
            if not resolve(base,p).is_file():raise ValueError('missing asset: '+p)
        names=[Path(p).name for p in [f['r_script']]+f.get('files',[])]
        if len(names)!=len(set(names)):raise ValueError('duplicate asset basename')

def build(manifest,out,rscript=None,reader='source.html'):
    path=Path(manifest).resolve();base=path.parent;card=json.loads(path.read_text(encoding='utf-8-sig'));validate(card,base)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True); report=[]; payload=[]
    for f in card['figures']:
        dest=out/f['id'];dest.mkdir(exist_ok=True)
        for name in [f['crop'],f['r_script']]+f.get('files',[]):
            p=resolve(base,name);target=dest/p.name
            if p!=target:shutil.copy2(p,target)
        record={'id':f['id'],'mode':f['mode'],'status':'not_run','exit_code':None,'source_page':f['page']}
        # Previous artifacts never become evidence of a new successful run.
        run_dir=dest/'run'; run_dir.mkdir(exist_ok=True)
        if rscript:
            for name in [f['r_script']]+f.get('files',[]):shutil.copy2(resolve(base,name),run_dir/Path(name).name)
            for name in ['preview.png','redraw.pdf']:
                stale=run_dir/name
                if stale.is_file():stale.unlink()
            try:
                proc=subprocess.run([str(rscript),'--vanilla',str(run_dir/Path(f['r_script']).name)],cwd=run_dir,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
                record['exit_code']=proc.returncode;record['status']='success' if proc.returncode==0 and (run_dir/'preview.png').is_file() and (run_dir/'redraw.pdf').is_file() else 'failed'
                (dest/'run.log').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
            except (OSError,subprocess.TimeoutExpired) as e:
                record['status']='failed';(dest/'run.log').write_text(str(e),encoding='utf-8')
        files=[]
        for name in [f['r_script']]+f.get('files',[]):
            p=resolve(base,name);files.append({'name':p.name,'b64':base64.b64encode(p.read_bytes()).decode()})
        if record['status']=='success':
            p=run_dir/'redraw.pdf';files.append({'name':'redraw.pdf','b64':base64.b64encode(p.read_bytes()).decode()})
            p=run_dir/'preview.png';files.append({'name':'preview.png','b64':base64.b64encode(p.read_bytes()).decode()})
        bundle=io.BytesIO()
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
            for asset in files:z.writestr(asset['name'],base64.b64decode(asset['b64']))
            z.writestr('provenance.json',json.dumps({'figure':f['id'],'mode':f['mode'],'data':f['data'],'context':f['context'],'interpretation':f['interpretation'],'reuse':f.get('reuse',''),'run':record},ensure_ascii=False,indent=2))
        (dest/(f['id']+'-bundle.zip')).write_bytes(bundle.getvalue())
        files.append({'name':f['id']+'-bundle.zip','b64':base64.b64encode(bundle.getvalue()).decode()})
        item=dict(f);item.update(run=record,original='data:image/png;base64,'+base64.b64encode(resolve(base,f['crop']).read_bytes()).decode(),preview=('data:image/png;base64,'+base64.b64encode((run_dir/'preview.png').read_bytes()).decode()) if record['status']=='success' else None,code=resolve(base,f['r_script']).read_text(encoding='utf-8-sig'),downloads=files)
        payload.append(item);report.append(record)
    from source_reader import build as build_source_reader
    build_source_reader(card,base,out)
    data={'paper':card['paper'],'figures':payload,'modes':MODES,'reader':reader}
    template=(Path(__file__).parents[1]/'assets'/'gallery.html').read_text(encoding='utf-8')
    from page_theme import apply_theme
    template=apply_theme(template)
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (out/'gallery.html').write_text(template.replace('/*__GALLERY__*/',encoded),encoding='utf-8')
    dump(out/'gallery-manifest.json',card);dump(out/'gallery-report.json',{'source_sha256':card['paper']['sha256'],'figures':report})
    return {'figures':len(report),'success':sum(r['status']=='success' for r in report),'failed':sum(r['status']=='failed' for r in report),'not_run':sum(r['status']=='not_run' for r in report),'out':str(out)}

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('scan');a.add_argument('--pdf',required=True);a.add_argument('--out',required=True)
    a=s.add_parser('build');a.add_argument('--manifest',required=True);a.add_argument('--out',required=True);a.add_argument('--rscript')
    args=p.parse_args()
    try:print(json.dumps(scan(args.pdf,args.out) if args.command=='scan' else build(args.manifest,args.out,args.rscript),ensure_ascii=False))
    except (ValueError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
