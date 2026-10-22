"""Persistent, append-only paper library. No model or network calls."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import uuid
import zipfile
from urllib.parse import quote
import pymupdf

SCHEMA = 'paper-library/v1'

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))

def atomic(path: Path, data: str) -> None:
    tmp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    tmp.write_text(data, encoding='utf-8')
    os.replace(tmp, path)

def encode(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2).replace('<', '\\u003c')

def register(pdf: str, result: str, library: str, title: str | None = None) -> dict:
    pdf, result, root = Path(pdf).resolve(), Path(result).resolve(), Path(library).resolve()
    if not result.is_dir():
        raise ValueError('成果目录不存在')
    if result == root or result in root.parents or root in result.parents:
        raise ValueError('成果目录与论文库必须分开，避免递归复制')
    sha = digest(pdf)
    artifacts = {}
    reports = [('reading','build-report.json','source_sha256','index.html'),
               ('gallery','gallery-report.json','source_sha256','gallery.html'),
               ('references','references.json','source_sha256','references.html'),
               ('draft','draft-report.json','source_sha256','manuscript.html')]
    for task, report, field, page in reports:
        if (result / page).is_file():
            if not (result / report).is_file() or read(result / report).get(field) != sha:
                raise ValueError(f'{task}成果与原PDF不匹配或缺少构建记录')
            artifacts[task] = page
    if not artifacts:
        raise ValueError('没有可入库的已生成成果')
    if not title:
        meta = result / 'reading.json'
        title = read(meta).get('paper',{}).get('title') if meta.is_file() else None
    if not title:
        meta = result / 'gallery-manifest.json'
        title = read(meta).get('paper',{}).get('title') if meta.is_file() else None
    with pymupdf.open(pdf) as doc:
        pages = len(doc)
        title = title or doc.metadata.get('title') or pdf.stem
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.library.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError('论文库正在写入；稍后重试，不要覆盖索引') from exc
    os.close(fd)
    stage = root / ('.incoming-' + uuid.uuid4().hex)
    try:
        registry = read(root/'library.json') if (root/'library.json').exists() else {'schema':SCHEMA,'papers':[]}
        if registry.get('schema') != SCHEMA:
            raise ValueError('未知论文库格式')
        paper = next((p for p in registry['papers'] if p['sha256']==sha),None)
        if paper is None:
            paper = {'id':sha,'sha256':sha,'title':title,'pages':pages,'versions':[],'latest':{}}
            registry['papers'].append(paper)
        version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
        dest = root/'papers'/sha/version
        stage.mkdir()
        # Immutable snapshots: no symlink traversal or executable runtime folders.
        def ignore(directory: str, names: list[str]) -> set[str]:
            return {n for n in names if n in {'__pycache__','.git','runtime'} or (Path(directory)/n).is_symlink()}
        shutil.copytree(result,stage/'result',ignore=ignore)
        shutil.copy2(pdf,stage/'original.pdf')
        base = Path('papers')/sha/version/'result'
        tasks = {k:(base/v).as_posix() for k,v in artifacts.items()}
        entry={'id':version,'created':datetime.now().astimezone().isoformat(timespec='seconds'),'tasks':tasks}
        (stage/'version.json').write_text(encode(entry),encoding='utf-8')
        # Navigation is local and relocatable. Original files are never modified.
        for name in artifacts.values():
            f=stage/'result'/name
            text=f.read_text(encoding='utf-8')
            links='<a href="../../../../index.html">← 论文库</a> '
            for key,label in [('reading','文章精读'),('gallery','图表画廊'),('references','参考文献'),('draft','论文初稿（Beta）')]:
                if key in artifacts and artifacts[key]!=name:
                    links+=f'<a href="{artifacts[key]}">{label}</a> '
            bar='<div class="library-nav" style="padding:10px 20px;background:#eaf0e6;color:#254b3c;font:13px sans-serif;display:flex;gap:20px;flex-wrap:wrap">'+links+'</div>'
            import re
            text=re.sub(r'<body([^>]*)>',lambda m:m.group(0)+bar,text,count=1)
            f.write_text(text,encoding='utf-8')
        dest.parent.mkdir(parents=True,exist_ok=True)
        stage.rename(dest)  # New unique path; old versions remain untouched.
        paper['versions'].append(entry)
        paper['latest'].update(tasks)
        paper['title']=title
        registry['updated']=datetime.now().astimezone().isoformat(timespec='seconds')
        old=root/'library.json'
        if old.is_file():
            backups=root/'index-history';backups.mkdir(exist_ok=True)
            shutil.copy2(old,backups/(version+'.json'))
        atomic(old,encode(registry))
        template=(Path(__file__).parents[1]/'assets/library.html').read_text(encoding='utf-8')
        from page_theme import apply_theme
        template=apply_theme(template)
        atomic(root/'index.html',template.replace('/*__LIBRARY__*/',encode(registry)))
        (root/'保存与备份说明.txt').write_text('论文和成果按PDF指纹分目录，同篇每次增加版本，新增论文不会删除旧论文。\n备份：复制整个论文精读库文件夹，包括library.json、index.html和papers。\n网页收藏和个人批注在浏览器中，清理缓存或换浏览器前请在各页面导出JSON，再将JSON放入本文件夹一并备份。\n网页没有自动调用模型，也没有新建/上传按钮；请回Codex聊天提供PDF并发出精读/插图分析指令。\n',encoding='utf-8')
        return {'library':str(root/'index.html'),'paper_id':sha,'version':version,'tasks':list(tasks),'papers':len(registry['papers'])}
    finally:
        lock.unlink(missing_ok=True)
        # Failed staging directories are retained for recovery, never deleting old results.

def backup(library: str, out: str) -> dict:
    root, target=Path(library).resolve(),Path(out).resolve()
    if target==root or root in target.parents:
        raise ValueError('备份ZIP请保存在论文库之外')
    if target.exists():raise ValueError('备份文件已存在，请使用新名称')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
        for p in root.rglob('*'):
            if p.is_file() and not p.is_symlink() and '.library.lock'!=p.name and not any(part.startswith('.incoming-') for part in p.relative_to(root).parts):
                z.write(p,p.relative_to(root))
    return {'backup':str(target),'bytes':target.stat().st_size}

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('register');a.add_argument('--pdf',required=True);a.add_argument('--result',required=True);a.add_argument('--library',required=True);a.add_argument('--title')
    a=s.add_parser('backup');a.add_argument('--library',required=True);a.add_argument('--out',required=True)
    a=p.parse_args()
    try:print(encode(register(a.pdf,a.result,a.library,a.title) if a.command=='register' else backup(a.library,a.out)))
    except (ValueError,OSError,KeyError) as e:p.exit(2,str(e)+'\n')
