"""Remove selected library result types via the Windows system Recycle Bin."""
from pathlib import Path
from datetime import datetime
import copy,json,os,re,shutil,subprocess,uuid
from paper_library import read,atomic,encode,digest
from page_theme import apply_theme

TASKS={'reading','gallery','references','draft'}
FILES={
 'reading':{'index.html','reading.json','paper-card.md','build-report.json','annotated-paper.pdf','annotation-map.json','evidence-index.json','evidence-conclusions.md','build_reading.py','annotated-check.png'},
 'gallery':{'gallery.html','gallery-manifest.json','gallery-report.json','source.html','source-reader-report.json','prepare_gallery.py','reading-context.md','digitization-calibration.json','data-mapping.md'},
 'references':{'references.html','references.json','references-original-columns.txt','extracted-references.json','verification-summary.json'},
 'draft':{'manuscript.html','manuscript.md','draft.json','draft-report.json','sources.json','feasibility.md','images'},
}

def recycle_windows(path):
    if os.name!='nt':raise OSError('系统回收站功能需要Windows')
    # Fixed code; the validated path is passed as data, never interpolated into a command.
    code="$ErrorActionPreference='Stop'; Add-Type -AssemblyName Microsoft.VisualBasic; $p=[Environment]::GetEnvironmentVariable('WORKBENCH_RECYCLE_TARGET'); [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p,[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,[Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)"
    env=os.environ.copy();env['WORKBENCH_RECYCLE_TARGET']=str(path)
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],env=env,capture_output=True,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode or path.exists():raise OSError('移入系统回收站未完成；未执行永久删除。'+p.stderr[-500:])

def drop(path,stage):
    p=path.resolve();s=stage.resolve()
    if p==s or s not in p.parents:raise ValueError('临时文件清理路径越界')
    if path.is_dir():shutil.rmtree(path)
    elif path.exists():path.unlink()

def refresh_nav(result,task_keys):
    labels={'reading':('index.html','文章精读'),'gallery':('gallery.html','进入画廊'),'references':('references.html','参考文献'),'draft':('manuscript.html','论文初稿（Beta）')}
    for p in result.glob('*.html'):
        s=p.read_text(encoding='utf-8');s=re.sub(r'<div class="library-nav"[^>]*>.*?</div>','',s,flags=re.S)
        links='<a href="../../../../index.html">← 论文库</a> '+''.join(f'<a href="{labels[k][0]}">{labels[k][1]}</a> ' for k in labels if k in task_keys and labels[k][0]!=p.name)
        s=s.replace('<body>','<body><div class="library-nav" style="padding:10px 20px;display:flex;gap:20px;flex-wrap:wrap">'+links+'</div>',1)
        p.write_text(apply_theme(s),encoding='utf-8')

def consolidate_latest(stage,paper,source):
    if len(paper['versions'])<2:raise ValueError('没有可删除的历史版本')
    latest=copy.deepcopy(paper['versions'][-1]);vid=latest['id']
    if not re.fullmatch('[A-Za-z0-9-]+',vid):raise ValueError('版本标识无效')
    dest=stage/vid/'result';tasks={}
    # Retain each module's latest result, even if the last save only added references.
    for task,path in paper['latest'].items():
        if task not in TASKS:raise ValueError('成果类型无效')
        match=re.fullmatch(r'papers/[a-f0-9]{64}/([A-Za-z0-9-]+)/result/([A-Za-z-]+\.html)',path)
        if not match:raise ValueError('成果路径无效')
        old=stage/match[1]/'result'
        if not old.is_dir():raise ValueError('历史成果缺失，尚未删除')
        names=set(FILES[task])
        if task=='reading':names.update(p.name for p in old.glob('page-*.png'))
        if task=='gallery':
            g=read(old/'gallery-manifest.json');names.update(f['id'] for f in g['figures'])
        if old!=dest:
            for name in names:
                src=old/name;target=dest/name
                if src.resolve()!=src or stage.resolve() not in src.resolve().parents:raise ValueError('成果材料路径越界')
                if src.is_dir():shutil.copytree(src,target,dirs_exist_ok=True)
                elif src.is_file():shutil.copy2(src,target)
        tasks[task]=f"papers/{paper['sha256']}/{vid}/result/{match[2]}"
    if 'gallery' in tasks:
        gallery=read(dest/'gallery-manifest.json');gallery['paper']['source_pdf']=str(stage/vid/'original.pdf')
        if digest(stage/vid/'original.pdf')!=paper['sha256']:raise ValueError('原PDF指纹不匹配')
        from source_reader import build as build_source
        if 'reading' in tasks:gallery['reading_card']=str(dest/'reading.json')
        build_source(gallery,dest,dest,reuse_reading='reading' in tasks)
        gpage=dest/'gallery.html';text=gpage.read_text(encoding='utf-8')
        text=re.sub(r'"reader"\s*:\s*"(?:index|source).html"','"reader": "'+('index.html' if 'reading' in tasks else 'source.html')+'"',text);gpage.write_text(text,encoding='utf-8')
        if 'reading' in tasks:
            marker='<script id="payload" type="application/json">'
            source_payload=json.loads((dest/'source.html').read_text(encoding='utf-8').split(marker)[1].split('</script>')[0])
            page=dest/'index.html';text=page.read_text(encoding='utf-8');raw=text.split(marker)[1].split('</script>')[0];payload=json.loads(raw)
            payload['galleryLinks']=source_payload['galleryLinks'];payload['card']=source_payload['card']
            encoded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
            page.write_text(text.replace(marker+raw,marker+encoded,1),encoding='utf-8')
    latest['tasks']=tasks
    (stage/vid/'version.json').write_text(encode(latest),encoding='utf-8');refresh_nav(dest,tasks)
    for version in paper['versions'][:-1]:
        old_id=version['id']
        if not re.fullmatch('[A-Za-z0-9-]+',old_id):raise ValueError('版本标识无效')
        drop(stage/old_id,stage)
    return latest


def delete_results(library,paper_id,tasks,recycle=None):
    root=Path(library).resolve()
    if not re.fullmatch('[a-f0-9]{64}',paper_id):raise ValueError('论文标识无效')
    if not isinstance(tasks,list) or not tasks or any(t not in TASKS|{'all','history'} for t in tasks):raise ValueError('请选择有效的删除范围')
    history=tasks==['history']
    if 'history' in tasks and not history:raise ValueError('删除历史版本请单独操作')
    chosen=TASKS.copy() if 'all' in tasks else set(tasks)
    source=(root/'papers'/paper_id).resolve()
    if root not in source.parents or source!=root/'papers'/paper_id or not source.is_dir():raise ValueError('论文目录不存在或越界')
    for p in source.rglob('*'):
        if p.is_symlink() or source not in p.resolve().parents:raise ValueError('论文目录包含外部链接，拒绝删除')
    lock=root/'.library.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    stage=root/('.delete-stage-'+uuid.uuid4().hex)
    recycled=False
    try:
        registry=read(root/'library.json');paper=next((p for p in registry['papers'] if p['sha256']==paper_id),None)
        if paper is None:raise ValueError('论文未登记')
        if not history and not chosen.intersection(paper['latest']):raise ValueError('所选成果尚未生成')
        new=copy.deepcopy(paper);kept=[]
        # Copy kept material before recycling the ONE original paper directory.
        # Temporary staging is removed after completion; it is not an application trash.
        shutil.copytree(source,stage)
        if history:
            kept=[consolidate_latest(stage,paper,source)]
        else:
            for version in new['versions']:
                vid=version['id']
                if not re.fullmatch('[A-Za-z0-9-]+',vid):raise ValueError('版本标识无效')
                kept_tasks={k:v for k,v in version['tasks'].items() if k not in chosen}
                folder=stage/vid;result=folder/'result'
                if not kept_tasks:drop(folder,stage);continue
                gallery=read(result/'gallery-manifest.json') if (result/'gallery-manifest.json').is_file() else None
                for task in chosen:
                    names=set(FILES[task])
                    if task=='gallery' and gallery:names.update(f['id'] for f in gallery['figures'])
                    if task=='reading':names.update(p.name for p in result.glob('page-*.png'))
                    for name in names:
                        if (result/name).exists():drop(result/name,stage)
                if 'reading' in chosen and 'gallery' in kept_tasks:
                    if not gallery:raise ValueError('保留画廊所需清单缺失，尚未删除')
                    from source_reader import build as build_source
                    gallery['paper']['source_pdf']=str(folder/'original.pdf')
                    if digest(folder/'original.pdf')!=paper_id:raise ValueError('原PDF指纹不匹配')
                    build_source(gallery,result,result,reuse_reading=False)
                    gpage=result/'gallery.html';text=gpage.read_text(encoding='utf-8');text=re.sub(r'"reader"\s*:\s*"index.html"','"reader": "source.html"',text);gpage.write_text(text,encoding='utf-8')
                if 'gallery' in chosen and 'reading' in kept_tasks:
                    from build_viewer import build as build_reading
                    c=read(result/'reading.json');c['annotations']=[a for a in c['annotations'] if not a['id'].startswith('GC-')]
                    clean=folder/'kept-reading.json';clean.write_text(encode(c),encoding='utf-8')
                    build_reading(folder/'original.pdf',clean,result)
                    clean.unlink()
                version['tasks']=kept_tasks;kept.append(version)
                (folder/'version.json').write_text(encode(version),encoding='utf-8');refresh_nav(result,kept_tasks)
        new['versions']=kept;new['latest']={}
        for v in kept:new['latest'].update(v['tasks'])
        # No permanent-delete fallback. The real directory must leave via Recycle Bin.
        (recycle or recycle_windows)(source)
        recycled=not source.exists()
        if source.exists():raise OSError('系统回收站操作未移走目录')
        if kept:stage.rename(source);registry['papers']=[new if p['sha256']==paper_id else p for p in registry['papers']]
        else:registry['papers']=[p for p in registry['papers'] if p['sha256']!=paper_id]
        registry['updated']=datetime.now().astimezone().isoformat(timespec='seconds')
        atomic(root/'library.json',encode(registry))
        template=apply_theme((Path(__file__).parents[1]/'assets/library.html').read_text(encoding='utf-8'))
        atomic(root/'index.html',template.replace('/*__LIBRARY__*/',encode(registry)))
        return {'recycled':True,'deleted_tasks':sorted(chosen),'paper_removed':not kept,'message':'已删除历史版本，只保留最新版本' if history else '已移入Windows系统回收站'}
    finally:
        lock.unlink(missing_ok=True)
        if stage.exists() and not recycled and source.exists():drop(stage,root)
        elif stage.exists() and not kept:drop(stage,root)
