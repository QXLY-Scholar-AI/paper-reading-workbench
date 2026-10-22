import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
import pymupdf
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import figure_gallery as g

class Gallery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
  d=pymupdf.open();p=d.new_page();p.draw_rect(pymupdf.Rect(50,90,400,300));p.insert_text((55,320),'Figure 1. Synthetic test figure.');p.insert_text((50,50),'Data availability: repository');d.save(self.p/'paper.pdf');d.close()
  self.scan=g.scan(self.p/'paper.pdf',self.p/'scan'); c=json.loads((self.p/'scan'/'candidates.json').read_text(encoding="utf-8"))['figures'][0]
  (self.p/'reading.md').write_text('Actual reading record for test');(self.p/'draw.R').write_text('stop("expected")')
  c['crop']='scan/'+c['crop']
  self.card=dict(schema=g.SCHEMA,paper=dict(title='Synthetic test',source_pdf=str(self.p/'paper.pdf'),sha256=g.sha(self.p/'paper.pdf')),reading_record='reading.md',figures=[dict(c,chart_type='test',mode='template',reviewed=True,interpretation='Synthetic fixture, not research data',context=[dict(page=1,quote='Synthetic test figure',role='caption')],data=dict(source='Synthetic test fixture',status='not_available'),r_script='draw.R',files=[])])
 def tearDown(self):self.tmp.cleanup()
 def test_candidate_not_auto_reviewed(self):
  c=json.loads((self.p/'scan'/'candidates.json').read_text(encoding="utf-8"));self.assertEqual(len(c['figures']),1);self.assertFalse(c['figures'][0]['reviewed']);self.assertTrue(c['data_clues'])
 def test_require_reading_and_context(self):
  self.card['figures'][0]['context']=[]
  with self.assertRaisesRegex(ValueError,'语境'):g.validate(self.card,self.p)
 def test_source_mismatch(self):
  self.card['paper']['sha256']='wrong'
  with self.assertRaisesRegex(ValueError,'hash mismatch'):g.validate(self.card,self.p)
 def test_no_r_does_not_claim_run(self):
  g.dump(self.p/'gallery.json',self.card);r=g.build(self.p/'gallery.json',self.p/'out');self.assertEqual(r['not_run'],1);s=(self.p/'out'/'gallery.html').read_text(encoding='utf-8');self.assertIn('"preview": null',s)
 def test_unsafe_id_rejected(self):
  self.card['figures'][0]['id']='../outside'
  with self.assertRaisesRegex(ValueError,'unsafe'):g.validate(self.card,self.p)
 def test_unreviewed_rejected(self):
  self.card['figures'][0]['reviewed']=False
  with self.assertRaisesRegex(ValueError,'reviewed'):g.validate(self.card,self.p)
 def test_run_failure_not_hidden_by_stale_preview(self):
  # A nonexistent R executable must not pick up a preview from a previous build.
  g.dump(self.p/'gallery.json',self.card);folder=self.p/'out'/'F1'/'run';folder.mkdir(parents=True);(folder/'preview.png').write_bytes(b'stale');(folder/'redraw.pdf').write_bytes(b'stale')
  r=g.build(self.p/'gallery.json',self.p/'out',str(self.p/'missing-Rscript'));self.assertEqual(r['failed'],1);self.assertFalse((folder/'preview.png').exists())

if __name__=='__main__':unittest.main()
