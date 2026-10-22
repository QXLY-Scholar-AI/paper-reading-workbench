"""Reuse the paper viewer for gallery source links, with or without a reading card."""
from pathlib import Path
import base64,copy,hashlib,json,re
import pymupdf as fitz
from build_viewer import locate_details,markdown

def figure_regions(doc,gallery=None):
    if gallery:
        figures=gallery['figures']
    else:
        figures=[]
        for n,p in enumerate(doc):
            graphics=[fitz.Rect(i['bbox']) for i in p.get_image_info()]
            graphics += [fitz.Rect(i['rect']) for i in p.get_drawings() if i['rect'].width>100 and i['rect'].height>60]
            for b in p.get_text('blocks'):
                if b[6]!=0:continue
                m=re.match(r'^(?:Figure|Fig\.?|图)\s*([A-Za-z]?\d+)[.．:：\s]',b[4].strip())
                if not m:continue
                nearby=[r for r in graphics if r.width>80 and r.height>50 and 0<=b[1]-r.y1<80]
                if nearby:
                    box=max(nearby,key=lambda r:r.get_area())
                    figures.append({'id':'F'+m.group(1),'page':n+1,'bbox':list(box),'label':'Figure '+m.group(1)})
    result=[]
    for f in figures:
        page=doc[f['page']-1];r=fitz.Rect(f['bbox'])&page.rect
        result.append({'id':f['id'],'page':f['page'],'label':f['label'],'rect':[r.x0/page.rect.width,r.y0/page.rect.height,r.x1/page.rect.width,r.y1/page.rect.height],'available':bool(gallery)})
    return result

def find_card(gallery,base,sha):
    paths=[]
    if gallery.get('reading_card'):paths.append(base/gallery['reading_card'])
    rec=base/gallery['reading_record'];paths += [rec if rec.suffix=='.json' else rec.with_name('reading.json')]
    config=Path(__file__).parents[1]/'local-runtime.json'
    if config.is_file():
        root=Path(json.loads(config.read_text(encoding='utf-8-sig')).get('library_root',''))
        if (root/'library.json').is_file():
            registry=json.loads((root/'library.json').read_text(encoding='utf-8-sig'))
            paper=next((p for p in registry['papers'] if p['sha256']==sha),None)
            if paper and paper['latest'].get('reading'):paths.append((root/paper['latest']['reading']).with_name('reading.json'))
    for p in paths:
        if p.is_file():
            try:
                card=json.loads(p.read_text(encoding='utf-8-sig'))
                if card.get('source',{}).get('sha256')==sha and [s.get('id') for s in card.get('steps',[])]==[1,2,3,4,5]:return copy.deepcopy(card)
            except (ValueError,KeyError,TypeError):continue
    return None

def build(gallery,base,out,reuse_reading=True):
    base,out=Path(base),Path(out);raw=Path(gallery['paper']['source_pdf']).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    doc=fitz.open(stream=raw,filetype='pdf');card=find_card(gallery,base,sha) if reuse_reading else None;source_only=card is None
    if source_only:card={'paper':gallery['paper'],'summary':'原文阅读窗口；尚未生成五步精读。','steps':[],'annotations':[]}
    card['source']={'sha256':sha,'filename':Path(gallery['paper']['source_pdf']).name,'pages':len(doc)}
    anchors=[]
    card['annotations']=[a for a in card['annotations'] if not a['id'].startswith('GC-')]
    for f in gallery['figures']:
        for i,c in enumerate(f['context']):
            aid=f"GC-{f['id']}-{i}";rects,status,_=locate_details(doc[c['page']-1],c['quote']);p=doc[c['page']-1]
            card['annotations'].append({'id':aid,'page':c['page'],'step':3,'kind':'result','layer':'analysis','title':f['label']+' · '+c['role'],'quote':c['quote'],'explanation':f['interpretation'],'anchor_status':status,'rects':rects,'normalized_rects':[[r[0]/p.rect.width,r[1]/p.rect.height,r[2]/p.rect.width,r[3]/p.rect.height] for r in rects]})
            anchors.append({'id':aid,'page':c['page'],'status':status})
    pages=[]
    for p in doc:
        pix=p.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False,annots=False)
        pages.append({'width':p.rect.width,'height':p.rect.height,'image':'data:image/jpeg;base64,'+base64.b64encode(pix.tobytes('jpeg',jpg_quality=85)).decode()})
    payload={'card':card,'pages':pages,'sourceOnly':source_only,'galleryLinks':figure_regions(doc,gallery),'markdown':markdown(card) if not source_only else '', 'pdf':base64.b64encode(raw).decode(),'annotatedPdf':base64.b64encode(raw).decode()}
    assets=Path(__file__).parents[1]/'assets';template=(assets/'viewer.html').read_text(encoding='utf-8')
    from page_theme import apply_theme
    template=apply_theme(template)
    template=template.replace('<!--__GALLERY_LINK__-->','<a href="gallery.html">图表画廊 ↗</a>').replace('/*__PDFLIB__*/',(assets/'vendor/pdf-lib.min.js').read_text(encoding='utf-8').replace('</script','<\\/script')).replace('/*__EXPORT_CODE__*/',(assets/'export-pdf.js').read_text(encoding='utf-8'))
    data=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (out/'source.html').write_text(template.replace('/*__PAYLOAD__*/',data),encoding='utf-8')
    report={'source_sha256':sha,'source_only':source_only,'anchors':anchors,'matched':sum(a['status']=='matched' for a in anchors)}
    (out/'source-reader-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
