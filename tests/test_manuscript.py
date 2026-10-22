import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import manuscript_draft as draft
import paper_library as lib
import pymupdf

class Manuscript(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
        pdf=pymupdf.open();pdf.new_page();self.pdf=self.p/'core.pdf';pdf.save(self.pdf);pdf.close()
        sha=lib.digest(self.pdf)
        self.card={'schema':'paper-manuscript/v1','source_sha256':sha,'core_papers':[sha],'topic':'打包测试','title':'测试稿，非科学论文','kind':'review','sources':[{'id':'S1','citation':'测试材料','level':'abstract','locator':'fixture','note':'仅测试结构','verified':True}], 'sections':[{'id':key,'title':key,'paragraphs':[{'text':'测试内容 <script> 不执行。','citations':['S1'],'locator':'fixture'}]} for key in sorted(draft.REQUIRED)],'gaps':['真实课题未提供']}
    def tearDown(self):self.tmp.cleanup()
    def build(self,c=None):
        file=self.p/'draft.json';file.write_text(json.dumps(c or self.card),encoding='utf-8');return draft.build(str(file),str(self.p/'out'))
    def test_package_and_library(self):
        report=self.build();self.assertEqual(report['cited_sources'],1)
        page=(self.p/'out/manuscript.html').read_text(encoding='utf-8');self.assertIn('&lt;script&gt;',page);self.assertNotIn('<script>',page)
        lib.register(str(self.pdf),str(self.p/'out'),str(self.p/'library'),'Core paper')
        self.assertIn('draft',lib.read(self.p/'library/library.json')['papers'][0]['latest'])
        with self.assertRaises(ValueError):self.build()
    def test_unknown_or_metadata_reference_rejected(self):
        c=copy.deepcopy(self.card);c['sources'][0]['level']='metadata'
        with self.assertRaises(ValueError):self.build(c)
        c=copy.deepcopy(self.card);c['sections'][0]['paragraphs'][0]['citations']=['missing']
        with self.assertRaises(ValueError):self.build(c)
    def test_no_data_empirical_and_missing_structure_rejected(self):
        c=copy.deepcopy(self.card);c['kind']='empirical'
        with self.assertRaises(ValueError):self.build(c)
        c=copy.deepcopy(self.card);c['sections'].pop()
        with self.assertRaises(ValueError):self.build(c)
    def test_images_copied(self):
        img=self.p/'plot.png';img.write_bytes(bytes.fromhex('89504e470d0a1a0a'))
        c=copy.deepcopy(self.card);c['figures']=[{'file':'plot.png','caption':'测试图片包装，不展示科学数据','source_ids':['S1']}]
        self.assertEqual(self.build(c)['figures'],1)
        self.assertEqual(img.read_bytes(),(self.p/'out/images/figure-1.png').read_bytes())

if __name__=='__main__':unittest.main()
