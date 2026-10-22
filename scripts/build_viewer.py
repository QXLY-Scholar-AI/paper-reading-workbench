"""Build an offline, source-linked paper reader. No model/network calls."""
from pathlib import Path
import argparse,base64,hashlib,html,json,re,unicodedata,io,shutil
import pymupdf as fitz

COLORS=['#2872a7','#7856a0','#27876d','#b27321','#b75463']
SCHEMAS={'jzks-pdf-viewer/v1','paper-reading-workbench/v1'}
# These three symbols are legacy font encoding errors in some older PDFs,
# but can be legitimate characters elsewhere. Never use this fallback first.
LEGACY={'®':'fi','Œ':'ff','¯':'fl'}
def norm(s,legacy=False):
    if legacy:
        for source,target in LEGACY.items():s=s.replace(source,target)
    return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())

def validate_card(card,page_count):
    def require(ok,message):
        if not ok:raise ValueError('Invalid reading card: '+message)
    require(isinstance(card,dict),'expected JSON object')
    require(card.get('schema') in SCHEMAS,'unsupported schema; use paper-reading-workbench/v1 (legacy jzks-pdf-viewer/v1 accepted)')
    require(isinstance(card.get('paper'),dict) and isinstance(card['paper'].get('title'),str) and card['paper']['title'].strip(),'paper.title required')
    require(isinstance(card.get('steps'),list) and all(isinstance(s,dict) for s in card['steps']) and [s.get('id') for s in card['steps']]==[1,2,3,4,5],'steps must be exactly 1..5')
    require(isinstance(card.get('summary',''),str),'summary must be text')
    require(isinstance(card['paper'].get('authors',''),str),'paper.authors must be text')
    require(isinstance(card.get('annotations'),list),'annotations must be a list')
    ids=set()
    warnings=[]
    allowed={'schema','paper','summary','steps','annotations','source'}
    warnings += ['Unknown top-level field: '+key for key in card if key not in allowed]
    warnings += ['Paper metadata retained but not displayed: '+key for key in card['paper'] if key not in {'title','authors','doi'}]
    for a in card['annotations']:
        require(isinstance(a,dict),'annotation must be an object')
        require(isinstance(a.get('id'),str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',a['id']) and a['id'] not in ids,'unique simple annotation id required')
        ids.add(a['id'])
        require(type(a.get('page')) is int and 1<=a['page']<=page_count,a['id']+': invalid physical page')
        require(type(a.get('step')) is int and a['step'] in range(1,6),a['id']+': invalid step')
        require(a.get('layer') in ('author','analysis'),a['id']+': invalid layer')
        require(all(isinstance(a.get(k),str) and a[k].strip() for k in ('title','quote','explanation')),a['id']+': title, quote, explanation required')
        require(a.get('kind','background') in ('background','method','result','question','implication'),a['id']+': invalid kind')
    for s in card['steps']:
        require(isinstance(s.get('title'),str) and isinstance(s.get('paragraphs'),list) and s['paragraphs'],'each step needs title and paragraphs')
        warnings += ['Ignored step field: '+key for key in s if key not in {'id','title','paragraphs'}]
        for p in s['paragraphs']:
            require(isinstance(p,dict) and all(isinstance(p.get(k),str) for k in ('title','text')),'paragraph title/text required')
            require(p.get('layer') in ('author','analysis'),'invalid paragraph layer')
            require(isinstance(p.get('refs'),list) and all(x in ids for x in p['refs']),'paragraph refs must name existing annotations')
            warnings += ['Ignored paragraph field: '+key for key in p if key not in {'title','text','layer','refs'}]
    return warnings

def locate_details(page,quote,legacy=False):
    words=page.get_text('words')
    chars=[]; mapping=[]
    for i,w in enumerate(words):
        s=norm(w[4],legacy);chars.extend(s);mapping.extend([i]*len(s))
    stream=''.join(chars);needle=norm(quote,legacy)
    if len(needle)<12:return [],'quote_too_short',[]
    starts=[m.start() for m in re.finditer(re.escape(needle),stream)]
    if len(starts)!=1:
        candidates=[{'word_start':mapping[start],'word_end':mapping[start+len(needle)-1]} for start in starts]
        return [],'ambiguous' if starts else 'not_found',candidates
    ids=sorted(set(mapping[starts[0]:starts[0]+len(needle)]))
    lines=[]
    for i in ids:
        r=fitz.Rect(words[i][:4])
        if lines and abs(lines[-1].y0-r.y0)<3 and 0<=r.x0-lines[-1].x1<70:
            lines[-1]|=r
        else:lines.append(r)
    return [list(r) for r in lines],'matched',[]

def locate(page,quote,legacy=False):
    rects,status,_=locate_details(page,quote,legacy)
    return rects,status

def markdown(card):
    out=['# '+card['paper']['title'],'',card.get('summary',''),'']
    ann={a['id']:a for a in card['annotations']}
    for s in card['steps']:
        out+=['## '+str(s['id']).zfill(2)+' '+s['title'],'']
        for p in s['paragraphs']:
            tag='作者报告' if p['layer']=='author' else 'AI解读'
            refs='；'.join(f"{x} · PDF第{ann[x]['page']}页"+('（页内位置待定位）' if ann[x]['anchor_status']!='matched' else '') for x in p['refs'])
            out+=['### '+p['title'],'',f'[{tag}] '+p['text'],'','出处：'+refs,'']
    return '\n'.join(out)

def build(pdf,cardpath,out,legacy_ligatures='auto',gallery=None,rscript=None):
    pdf=Path(pdf);out=Path(out)
    raw=pdf.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    doc=fitz.open(stream=raw,filetype='pdf')
    card=json.loads(Path(cardpath).read_text(encoding='utf-8-sig'))
    if gallery:
        gallery_card=json.loads(Path(gallery).read_text(encoding='utf-8-sig'))
        if gallery_card['paper']['sha256']!=sha:raise ValueError('Gallery and reading PDF must match')
        for f in gallery_card['figures']:
            for i,c in enumerate(f['context']):
                aid=f"GC-{f['id']}-{i}"
                if not any(a['id']==aid for a in card['annotations']):
                    card['annotations'].append({'id':aid,'page':c['page'],'step':3,'kind':'result','layer':'analysis','title':f['label']+' · '+c['role'],'quote':c['quote'],'explanation':f['interpretation']})
    warnings=validate_card(card,len(doc))
    out.mkdir(parents=True,exist_ok=True)
    text='\n'.join(page.get_text() for page in doc)
    seen={char:text.count(char) for char in LEGACY if char in text}
    # Repeated mixed markers identify the old font pattern; a lone registered
    # trademark or a mathematical macron must not turn into synthetic letters.
    legacy_enabled=legacy_ligatures=='on' or (legacy_ligatures=='auto' and len(seen)>=2 and sum(seen.values())>=8)
    byid={a['id']:a for a in card['annotations']}
    pages=[];records=[]
    for n,page in enumerate(doc):
        pix=page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False,annots=False)
        image='data:image/jpeg;base64,'+base64.b64encode(pix.tobytes('jpeg',jpg_quality=85)).decode()
        pages.append({'width':page.rect.width,'height':page.rect.height,'image':image})
    for a in card['annotations']:
        a.setdefault('kind',{1:'background',2:'method',3:'result',4:'question',5:'implication'}[a['step']])
        page=doc[a['page']-1];rects,status,candidates=locate_details(page,a['quote'])
        method='unicode'
        if status=='not_found' and legacy_enabled:
            rects,status,candidates=locate_details(page,a['quote'],legacy=True)
            method='legacy_ligature_fallback'
        a['rects']=rects;a['anchor_status']=status
        a['normalized_rects']=[[r[0]/page.rect.width,r[1]/page.rect.height,r[2]/page.rect.width,r[3]/page.rect.height] for r in rects]
        records.append({'id':a['id'],'page':a['page'],'status':status,'rectangles':len(rects),'normalization':method,'candidates':candidates})
    card['source']={'sha256':sha,'filename':pdf.name,'pages':len(doc)}
    md=markdown(card)
    (out/'paper-card.md').write_text(md,encoding='utf-8')
    (out/'reading.json').write_text(json.dumps(card,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'annotation-map.json').write_text(json.dumps({'source_sha256':sha,'annotations':card['annotations']},ensure_ascii=False,indent=2),encoding='utf-8')
    evidence=[{'step':s['id'],'title':p['title'],'claim':p['text'],'layer':p['layer'],'references':[{'id':r,'page':byid[r]['page'],'quote':byid[r]['quote'],'status':byid[r]['anchor_status']} for r in p['refs']]} for s in card['steps'] for p in s['paragraphs']]
    (out/'evidence-index.json').write_text(json.dumps({'source_sha256':sha,'claims':evidence},ensure_ascii=False,indent=2),encoding='utf-8')
    # Original page content stays vector; annotations occupy a new right margin.
    annotated=fitz.open();page_map=[]
    for n,original in enumerate(doc):
        w,h=original.rect.width,original.rect.height
        current=annotated.new_page(width=w+290,height=h)
        page_map.append({'physical_page':n+1,'source_label':original.get_label() or None,'annotated_page':len(annotated)})
        current.show_pdf_page(fitz.Rect(0,0,w,h),doc,n)
        original_display=current
        current.insert_text((w+15,24),f'Paper notes | PDF {n+1}',fontsize=11,color=(.2,.2,.2))
        y=40
        anns=sorted([a for a in card['annotations'] if a['page']==n+1],key=lambda a:a['normalized_rects'][0][1] if a['normalized_rects'] else 0)
        prepared=[]
        for a in anns:
            col=tuple(int(COLORS[a['step']-1][k:k+2],16)/255 for k in [1,3,5])
            for rect in a['rects']:
                highlight=original_display.add_highlight_annot(fitz.Rect(rect));highlight.set_colors(stroke=col);highlight.set_opacity(.22);highlight.set_info(title=a['id'],content=a['explanation']);highlight.update()
            content=f"{a['id']}  {a['title']}\n"+('作者报告' if a['layer']=='author' else 'AI解读')+'｜'+a['explanation']
            if a['anchor_status']!='matched':content+='\n页内位置待定位：'+a['anchor_status']
            # Wrap using the actual CJK font widths; continue on a notes page if needed.
            lines=[]
            for paragraph in content.splitlines():
                line=''
                for ch in paragraph:
                    # Built-in CJK PDF font uses full-width Latin glyph advances.
                    # A fixed-width bound avoids overflowing the annotation margin.
                    if len(line+ch)*9.5>247:lines.append(line);line=''
                    line+=ch
                if line:lines.append(line)
            max_lines=max(1,int((h-100)/14))
            for offset in range(0,len(lines),max_lines):
                prepared.append((a,lines[offset:offset+max_lines],col))
        heights=[len(lines)*14+15 for a,lines,col in prepared]
        positions=[];cursor=40
        for (a,lines,col),height in zip(prepared,heights):
            desired=(a['normalized_rects'][0][1]*h) if a['normalized_rects'] else 40
            positions.append(max(cursor,desired));cursor=positions[-1]+height+8
        if sum(heights)+max(0,len(heights)-1)*8<=h-60:
            end=h-20
            for i in range(len(positions)-1,-1,-1):
                positions[i]=min(positions[i],end-heights[i]);end=positions[i]-8
        else:positions=[]
        for i,(a,lines,col) in enumerate(prepared):
            height=heights[i]
            y=positions[i] if positions else max(y,min((a['normalized_rects'][0][1]*h) if a['normalized_rects'] else 40,h-height-20))
            if y+height>h-20:
                current=annotated.new_page(width=w+290,height=h)
                current.insert_text((20,24),f'Notes continued | original PDF {n+1}',fontsize=11)
                y=45
            current.draw_rect(fitz.Rect(w+10,y-5,w+280,y+height-5),color=col,fill=(.98,.98,.98),width=.5)
            for line in lines:
                current.insert_text((w+17,y+8),line,fontname='china-s',fontsize=9.5,color=(.15,.15,.15));y+=14
            y+=23
    annotated.subset_fonts()
    annotated.save(out/'annotated-paper.pdf',garbage=4,deflate=True)
    payload={'card':card,'pages':pages,'markdown':md,'pdf':base64.b64encode(raw).decode(),'annotatedPdf':base64.b64encode((out/'annotated-paper.pdf').read_bytes()).decode()}
    assets=Path(__file__).resolve().parents[1]/'assets'
    template=(assets/'viewer.html').read_text(encoding='utf-8')
    from page_theme import apply_theme
    template=apply_theme(template)
    from source_reader import figure_regions
    payload['galleryLinks']=figure_regions(doc,json.loads(Path(gallery).read_text(encoding='utf-8-sig')) if gallery else None)
    if gallery:
        from figure_gallery import build as build_gallery
        gallery_card=json.loads(Path(gallery).read_text(encoding='utf-8-sig'))
        if gallery_card['paper']['sha256']!=sha:raise ValueError('Gallery and reading PDF must match')
        build_gallery(gallery,out,rscript,reader='index.html')
        template=template.replace('<!--__GALLERY_LINK__-->','<a href="gallery.html" target="_blank" style="padding:7px 10px;color:#356853">图表画廊 ↗</a>')
    else:template=template.replace('<!--__GALLERY_LINK__-->','')
    template=template.replace('/*__PDFLIB__*/',(assets/'vendor/pdf-lib.min.js').read_text(encoding='utf-8').replace('</script','<\\/script'))
    template=template.replace('/*__EXPORT_CODE__*/',(assets/'export-pdf.js').read_text(encoding='utf-8'))
    data=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    (out/'index.html').write_text(template.replace('/*__PAYLOAD__*/',data),encoding='utf-8')
    result={'pages':len(doc),'annotations':len(records),'matched':sum(x['status']=='matched' for x in records),'unresolved':[x for x in records if x['status']!='matched'],'anchors':records,'source_sha256':sha,'page_map':page_map,'legacy_ligatures':{'mode':legacy_ligatures,'enabled':legacy_enabled,'symbols_seen':seen},'warnings':warnings}
    (out/'build-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('anchors','page_map')},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--card',required=True);p.add_argument('--out',required=True);p.add_argument('--legacy-ligatures',choices=['auto','on','off'],default='auto');p.add_argument('--gallery');p.add_argument('--rscript');a=p.parse_args()
    try:build(a.pdf,a.card,a.out,a.legacy_ligatures,a.gallery,a.rscript)
    except (ValueError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
