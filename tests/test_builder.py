"""Synthetic fixtures only; no copyrighted paper is bundled."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import pymupdf as fitz

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_viewer.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def card():
    return {'schema':'paper-reading-workbench/v1','paper':{'title':'Synthetic test','authors':'Test'},'summary':'测试',
            'steps':[{'id':i,'title':f'步骤{i}','paragraphs':[{'title':'正文','text':'保留事实。','layer':'author','refs':['E01']}]} for i in range(1,6)],
            'annotations':[{'id':'E01','step':1,'page':1,'title':'证据','quote':'This is a unique sentence for evidence matching.','explanation':'中文解释','layer':'author'}]}

class FakePage:
    def __init__(self,lines):self.lines=lines
    def get_text(self,mode):
        words=[]
        for y,line in enumerate(self.lines):
            for x,text in enumerate(line.split()):words.append((x*40,y*20,x*40+35,y*20+10,text,0,y,x))
        return words

class Matching(unittest.TestCase):
    def test_full_legacy_quote_two_lines(self):
        p=FakePage(['This example proves emphatically that products do not have pro® ts, companies','do.'])
        quote='This example proves emphatically that products do not have profits, companies do.'
        self.assertEqual(b.locate(p,quote)[1],'not_found')
        rects,status=b.locate(p,quote,True)
        self.assertEqual(status,'matched');self.assertEqual(len(rects),2)
    def test_ambiguity_has_candidates_no_highlight(self):
        rects,status,candidates=b.locate_details(FakePage(['Repeated evidence sentence','Repeated evidence sentence']),'Repeated evidence sentence')
        self.assertEqual((rects,status),([], 'ambiguous'));self.assertEqual(len(candidates),2)
    def test_missing_no_highlight(self):self.assertEqual(b.locate(FakePage(['Nothing here']),'This evidence is absent'),([], 'not_found'))
    def test_short_quote(self):self.assertEqual(b.locate(FakePage(['Small']),'Small')[1],'quote_too_short')
    def test_real_registered_symbol_not_expanded(self):self.assertEqual(b.norm('Acme®'),'acme')
    def test_standard_ligature(self):self.assertEqual(b.norm('proﬁts'),'profits')

class Validation(unittest.TestCase):
    def test_new_and_legacy_schema(self):
        c=card();self.assertEqual(b.validate_card(c,1),[]);c['schema']='jzks-pdf-viewer/v1';self.assertEqual(b.validate_card(c,1),[])
    def test_bad_schema(self):
        c=card();c['schema']='invented/v1'
        with self.assertRaisesRegex(ValueError,'schema'):b.validate_card(c,1)
    def test_bad_step(self):
        c=card();c['steps'][0]=None
        with self.assertRaises(ValueError):b.validate_card(c,1)
    def test_duplicate_id(self):
        c=card();c['annotations']*=2
        with self.assertRaises(ValueError):b.validate_card(c,1)
    def test_invalid_reference(self):
        c=card();c['steps'][0]['paragraphs'][0]['refs']=['missing']
        with self.assertRaises(ValueError):b.validate_card(c,1)
    def test_page_boolean(self):
        c=card();c['annotations'][0]['page']=True
        with self.assertRaises(ValueError):b.validate_card(c,1)
    def test_unknown_field_warns(self):
        c=card();c['steps'][0]['paragraphs'][0]['callout']='extra'
        self.assertIn('Ignored paragraph field: callout',b.validate_card(c,1))

class Output(unittest.TestCase):
    def build(self,c):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
        doc=fitz.open();p=doc.new_page(width=500,height=500);p.insert_text((30,40),'This is a unique sentence for evidence matching.',fontsize=11);doc.save(root/'paper.pdf');doc.close()
        (root/'card.json').write_text(json.dumps(c),encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):b.build(root/'paper.pdf',root/'card.json',root/'out')
        return root/'out'
    def test_outputs_and_source_pages(self):
        out=self.build(card());report=json.loads((out/'build-report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['matched'],1);self.assertFalse(report['legacy_ligatures']['enabled'])
        self.assertEqual(report['page_map'][0]['physical_page'],1)
        self.assertEqual(len(list(out.iterdir())),7)
        data=(out/'index.html').read_text(encoding='utf-8');self.assertNotIn('/*__PAYLOAD__*/',data);self.assertNotIn('/*__EXPORT_CODE__*/',data)
    def test_unresolved_in_exported_text(self):
        c=card();c['annotations'][0]['quote']='This quote is nowhere in the document'
        out=self.build(c);self.assertIn('页内位置待定位',(out/'paper-card.md').read_text(encoding='utf-8'))
        report=json.loads((out/'build-report.json').read_text(encoding='utf-8'));self.assertEqual(report['matched'],0)
    def test_long_sidebar_continues_without_clipping(self):
        c=card();c['annotations'][0]['explanation']='长批注需要续页并保留全部内容。'*150
        out=self.build(c);doc=fitz.open(out/'annotated-paper.pdf');self.assertGreater(len(doc),1)
        alltext=''.join(p.get_text() for p in doc);self.assertEqual(alltext.count('长'),150)
        for page in doc:
            for block in page.get_text('blocks'):
                self.assertLessEqual(block[3],page.rect.height+1)

if __name__=='__main__':unittest.main()
