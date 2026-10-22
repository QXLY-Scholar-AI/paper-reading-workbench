import copy,json,sys,tempfile,unittest
from pathlib import Path
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import figure_gallery as g
from source_reader import build,figure_regions

class SourceReader(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
        d=fitz.open();p=d.new_page();p.draw_rect(fitz.Rect(50,90,400,300));p.insert_text((55,320),'Figure 1. Synthetic figure context for source links.');self.pdf=self.p/'paper.pdf';d.save(self.pdf);d.close()
        (self.p/'reading.md').write_text('Reading context record')
        self.card={'paper':{'title':'Fixture','source_pdf':str(self.pdf),'sha256':g.sha(self.pdf)},'reading_record':'reading.md','figures':[{'id':'F1','label':'Figure 1','page':1,'bbox':[50,90,400,300],'interpretation':'Figure context','context':[{'page':1,'quote':'Synthetic figure context for source links','role':'caption'}]}]}
    def tearDown(self):self.tmp.cleanup()
    def payload(self):
        s=(self.p/'source.html').read_text(encoding='utf-8');return json.loads(s.split('<script id="payload" type="application/json">')[1].split('</script>')[0])
    def test_gallery_only_has_context_marks_without_fake_reading(self):
        report=build(self.card,self.p,self.p);self.assertTrue(report['source_only']);self.assertEqual(report['matched'],1)
        payload=self.payload();self.assertEqual(payload['card']['steps'],[]);self.assertEqual(len(payload['card']['annotations']),1)
        self.assertTrue(payload['galleryLinks'][0]['available']);self.assertFalse((self.p/'reading.json').exists())
    def test_existing_reading_preserved(self):
        reading={'paper':{'title':'Fixture'},'source':{'sha256':g.sha(self.pdf)},'summary':'Original summary','annotations':[],'steps':[{'id':i,'title':str(i),'paragraphs':[{'title':'Kept','text':'Original text','layer':'analysis','refs':[]}]} for i in range(1,6)]}
        p=self.p/'reading.json';before=json.dumps(reading);p.write_text(before)
        report=build(self.card,self.p,self.p);self.assertFalse(report['source_only']);self.assertEqual(self.payload()['card']['steps'],reading['steps']);self.assertEqual(p.read_text(),before)
    def test_only_reading_hotspots_remind_without_gallery(self):
        with fitz.open(self.pdf) as d:regions=figure_regions(d)
        self.assertEqual(len(regions),1);self.assertFalse(regions[0]['available'])
    def test_mismatched_reading_not_reused(self):
        (self.p/'reading.json').write_text(json.dumps({'source':{'sha256':'b'*64},'steps':[{'id':i} for i in range(1,6)]}))
        self.assertTrue(build(self.card,self.p,self.p)['source_only'])

if __name__=='__main__':unittest.main()
