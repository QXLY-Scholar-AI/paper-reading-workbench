import json
import sys
import tempfile
import unittest
from pathlib import Path
import pymupdf
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import paper_library as lib
import reference_links as refs

class Library(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.root=self.p/'library'
    def tearDown(self):self.tmp.cleanup()
    def fixture(self,name,kind='reading'):
        pdf=self.p/(name+'.pdf');d=pymupdf.open();pg=d.new_page();pg.insert_text((40,40),name);d.save(pdf);d.close()
        r=self.p/(name+'-'+kind);r.mkdir();page={'reading':'index.html','gallery':'gallery.html'}[kind];report={'reading':'build-report.json','gallery':'gallery-report.json'}[kind]
        (r/page).write_text('<html><body>fixture '+name+'</body></html>',encoding='utf-8');(r/report).write_text(json.dumps({'source_sha256':lib.digest(pdf)}))
        return pdf,r
    def test_new_paper_keeps_old_files(self):
        a,ra=self.fixture('A');lib.register(str(a),str(ra),str(self.root),'Paper A');before={p.relative_to(self.root).as_posix():p.read_bytes() for p in (self.root/'papers').rglob('*') if p.is_file()}
        b,rb=self.fixture('B');lib.register(str(b),str(rb),str(self.root),'Paper B')
        self.assertEqual(len(lib.read(self.root/'library.json')['papers']),2)
        for path,data in before.items():self.assertEqual((self.root/path).read_bytes(),data)
    def test_same_paper_new_version_preserves_reading(self):
        pdf,r=self.fixture('A');first=lib.register(str(pdf),str(r),str(self.root),'A');g=self.p/'gallery-result';g.mkdir();(g/'gallery.html').write_text('<body>gallery</body>');(g/'gallery-report.json').write_text(json.dumps({'source_sha256':lib.digest(pdf)}))
        lib.register(str(pdf),str(g),str(self.root),'A');a=lib.read(self.root/'library.json')['papers'][0]
        self.assertEqual(len(a['versions']),2);self.assertEqual(set(a['latest']),{'reading','gallery'});self.assertIn(first['version'],a['latest']['reading'])
    def test_mismatch_does_not_register(self):
        pdf,r=self.fixture('A');(r/'build-report.json').write_text('{}')
        with self.assertRaises(ValueError):lib.register(str(pdf),str(r),str(self.root),'A')
        self.assertFalse((self.root/'library.json').exists())
    def test_navigation_relative_and_source_untouched(self):
        pdf,r=self.fixture('A');v=lib.register(str(pdf),str(r),str(self.root),'A');original=(r/'index.html').read_text();self.assertNotIn('library-nav',original)
        text=(self.root/'papers'/v['paper_id']/v['version']/'result/index.html').read_text(encoding='utf-8');self.assertIn('../../../../index.html',text)
    def test_backup_blocks_recursive_and_overwrite(self):
        pdf,r=self.fixture('A');lib.register(str(pdf),str(r),str(self.root),'A')
        with self.assertRaises(ValueError):lib.backup(str(self.root),str(self.root/'backup.zip'))
        dest=self.p/'backup.zip';lib.backup(str(self.root),str(dest))
        with self.assertRaises(ValueError):lib.backup(str(self.root),str(dest))

class References(unittest.TestCase):
    def test_no_unverified_or_unsafe_links(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);card={'schema':'paper-reference-links/v1','source_sha256':'a'*64,'paper_title':'fixture','references':[{'number':1,'citation':'Example','status':'matched','links':[{'url':'javascript:alert(1)','type':'pdf','verified':True,'checked_at':'2026-10-22','evidence':'fixture'}]}]};(p/'card.json').write_text(json.dumps(card))
            with self.assertRaises(ValueError):refs.build(str(p/'card.json'),str(p/'out'))
            card['references'][0]['links'][0]['url']='https://example.com/paper';card['references'][0]['links'][0]['verified']=False;(p/'card.json').write_text(json.dumps(card))
            with self.assertRaises(ValueError):refs.build(str(p/'card.json'),str(p/'out'))
    def test_missing_references_remain(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);card={'schema':'paper-reference-links/v1','source_sha256':'a'*64,'paper_title':'fixture','references':[{'number':7,'citation':'Unknown paper','status':'not_found','links':[]}]};(p/'card.json').write_text(json.dumps(card));r=refs.build(str(p/'card.json'),str(p/'out'));self.assertEqual(r['entries'],1);self.assertEqual(r['with_links'],0)

if __name__=='__main__':unittest.main()
