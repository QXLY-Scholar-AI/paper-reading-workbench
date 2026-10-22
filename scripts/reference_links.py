"""Render host-verified reference links; never downloads documents."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import html
import json
import re

def build(card_path: str, out: str) -> dict:
    card=json.loads(Path(card_path).read_text(encoding='utf-8-sig'))
    if card.get('schema')!='paper-reference-links/v1' or not re.fullmatch('[a-f0-9]{64}',card.get('source_sha256','')):
        raise ValueError('invalid reference card/source hash')
    refs=card.get('references')
    if not isinstance(refs,list):raise ValueError('references must be a list')
    ids=set()
    for r in refs:
        for candidate in r.get('candidate_links',[]):
            u=urlsplit(candidate.get('url',''))
            if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password or candidate.get('verified') is not False or candidate.get('type') not in {'pdf','article'} or not candidate.get('evidence'):
                raise ValueError('candidate link must be safe, traceable and explicitly unverified')
        if r['status']=='not_found' and (r.get('candidate_links') or r.get('matched_metadata')):
            raise ValueError('not_found is reserved for no matching information')
        if str(r['number']) in ids or not r.get('citation') or r['status'] not in {'matched','not_found','uncertain'}:
            raise ValueError('duplicate number or invalid reference')
        ids.add(str(r['number']))
        if not isinstance(r.get('links'),list):raise ValueError('links list required')
        if r['status']!='matched' and r['links']:raise ValueError('unmatched entry cannot have verified links')
        if r['status']=='matched' and not r['links']:raise ValueError('matched requires links')
        for link in r['links']:
            u=urlsplit(link['url'])
            if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password:
                raise ValueError('unsafe reference URL')
            if link.get('verified') is not True or not link.get('evidence') or link['type'] not in {'pdf','article'} or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',link.get('checked_at','')):
                raise ValueError('verified identity, date and correct URL type required')
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(card,ensure_ascii=False,indent=2).replace('<','\\u003c')
    template=(Path(__file__).parents[1]/'assets/reference-links.html').read_text(encoding='utf-8')
    from page_theme import apply_theme
    template=apply_theme(template)
    (dest/'references.html').write_text(template.replace('/*__REFERENCES__*/',encoded),encoding='utf-8')
    (dest/'references.json').write_text(json.dumps(card,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'entries':len(refs),'with_links':sum(bool(r['links']) for r in refs),'page':str(dest/'references.html')}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--card',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:print(json.dumps(build(a.card,a.out),ensure_ascii=False))
    except (ValueError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
