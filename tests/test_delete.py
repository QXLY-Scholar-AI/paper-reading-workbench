import json,sys,shutil,tempfile,unittest
from pathlib import Path
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import paper_library as lib
from library_delete import delete_results
from build_viewer import build

class DeleteResults(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.root=self.p/'library';self.bin=self.p/'mock-system-bin';self.bin.mkdir()
  self.pdf=self.p/'fixture.pdf';d=fitz.open();pg=d.new_page();pg.draw_rect(fitz.Rect(50,90,400,300));pg.insert_text((55,320),'Figure 1. Synthetic figure context for source links.');d.save(self.pdf);d.close()
  self.sha=lib.digest(self.pdf);r=self.p/'result';r.mkdir()
  c={'schema':'paper-reading-workbench/v1','paper':{'title':'Fixture'},'summary':'Full reading summary','annotations':[],'steps':[{'id':i,'title':str(i),'paragraphs':[{'title':'Title','text':'Secret reading prose','layer':'author' if i<4 else 'analysis','refs':[]}]} for i in range(1,6)]}
  cp=self.p/'reading.json';cp.write_text(json.dumps(c));build(self.pdf,cp,r)
  g={'paper':{'title':'Fixture','source_pdf':str(self.pdf),'sha256':self.sha},'reading_record':'paper-card.md','figures':[{'id':'F1','label':'Figure 1','page':1,'bbox':[50,90,400,300],'interpretation':'Figure context','context':[{'page':1,'quote':'Synthetic figure context for source links','role':'caption'}]}]}
  (r/'gallery-manifest.json').write_text(json.dumps(g));(r/'gallery.html').write_text('<body><script id="data">{"reader":"index.html"}</script></body>');(r/'gallery-report.json').write_text(json.dumps({'source_sha256':self.sha}));(r/'F1').mkdir();(r/'F1/data.csv').write_text('x,y\n1,2')
  (r/'references.html').write_text('<body>References</body>');(r/'references.json').write_text(json.dumps({'source_sha256':self.sha}));(r/'verification-summary.json').write_text(json.dumps({'source_sha256':self.sha}))
  self.info=lib.register(str(self.pdf),str(r),str(self.root),'Fixture');self.result=self.root/'papers'/self.sha/self.info['version']/'result'
 def tearDown(self):self.tmp.cleanup()
 def recycle(self,p):shutil.move(str(p),str(self.bin/p.name))
 def paper(self):return lib.read(self.root/'library.json')['papers'][0]
 def test_delete_references_keeps_reading_and_gallery(self):
  before=(self.result/'reading.json').read_bytes();delete_results(self.root,self.sha,['references'],self.recycle)
  self.assertEqual(set(self.paper()['latest']),{'reading','gallery'});self.assertFalse((self.result/'references.html').exists());self.assertEqual((self.result/'reading.json').read_bytes(),before);self.assertTrue((self.bin/self.sha).is_dir())
 def test_delete_reading_keeps_source_only(self):
  delete_results(self.root,self.sha,['reading'],self.recycle)
  self.assertFalse((self.result/'index.html').exists());self.assertFalse((self.result/'reading.json').exists())
  text=(self.result/'source.html').read_text(encoding='utf-8');payload=json.loads(text.split('<script id="payload" type="application/json">')[1].split('</script>')[0]);self.assertTrue(payload['sourceOnly']);self.assertEqual(payload['card']['steps'],[]);self.assertNotIn('Secret reading prose',text);self.assertIn('source.html',(self.result/'gallery.html').read_text(encoding='utf-8'))
 def test_delete_gallery_rebuilds_reading_without_available_hotspot(self):
  delete_results(self.root,self.sha,['gallery'],self.recycle);self.assertTrue((self.result/'index.html').exists());self.assertFalse((self.result/'F1').exists());self.assertFalse((self.result/'source.html').exists())
  payload=json.loads((self.result/'index.html').read_text(encoding='utf-8').split('<script id="payload" type="application/json">')[1].split('</script>')[0]);self.assertFalse(payload['galleryLinks'][0]['available'])
 def test_delete_all_removes_entry_preserves_external_original(self):
  before=self.pdf.read_bytes();delete_results(self.root,self.sha,['all'],self.recycle);self.assertEqual(lib.read(self.root/'library.json')['papers'],[]);self.assertFalse((self.root/'papers'/self.sha).exists());self.assertEqual(self.pdf.read_bytes(),before)
 def test_prune_history_keeps_latest_of_every_module(self):
  r=self.p/'references-only';r.mkdir();(r/'references.html').write_text('<body>Newest reference result</body>');(r/'references.json').write_text(json.dumps({'source_sha256':self.sha}))
  info=lib.register(str(self.pdf),str(r),str(self.root),'Fixture');before=(self.result/'F1/data.csv').read_bytes()
  response=delete_results(self.root,self.sha,['history'],self.recycle);paper=self.paper()
  self.assertEqual(len(paper['versions']),1);self.assertEqual(paper['versions'][0]['id'],info['version']);self.assertEqual(set(paper['latest']),{'reading','gallery','references'})
  result=self.root/'papers'/self.sha/info['version']/'result';self.assertEqual((result/'F1/data.csv').read_bytes(),before);self.assertIn('Secret reading prose',(result/'index.html').read_text(encoding='utf-8'));self.assertIn('Newest reference result',(result/'references.html').read_text(encoding='utf-8'))
  self.assertFalse(self.result.exists());self.assertTrue((self.bin/self.sha).exists());self.assertTrue(response['recycled'])
  payload=json.loads((result/'index.html').read_text(encoding='utf-8').split('<script id="payload" type="application/json">')[1].split('</script>')[0]);self.assertTrue(payload['galleryLinks'][0]['available']);self.assertEqual(payload['card']['steps'][0]['paragraphs'][0]['text'],'Secret reading prose')
  for path in paper['latest'].values():self.assertTrue((self.root/path).is_file())
 def test_prune_single_version_and_mixed_scope_rejected(self):
  for tasks in (['history'],['history','reading']):
   with self.assertRaises(ValueError):delete_results(self.root,self.sha,tasks,self.recycle)
  self.assertTrue(self.result.exists());self.assertEqual(len(self.paper()['versions']),1)
 def test_recycler_failure_preserves_original(self):
  before=(self.result/'index.html').read_bytes()
  def fail(p):raise OSError('recycle failed')
  with self.assertRaises(OSError):delete_results(self.root,self.sha,['all'],fail)
  self.assertEqual((self.result/'index.html').read_bytes(),before);self.assertFalse(list(self.root.glob('.delete-stage-*')));self.assertFalse((self.root/'.library.lock').exists())
 def test_invalid_scope_and_path_rejected(self):
  for tasks in ([],['invalid']):
   with self.assertRaises(ValueError):delete_results(self.root,self.sha,tasks,self.recycle)
  with self.assertRaises(ValueError):delete_results(self.root,'../papers',['all'],self.recycle)
 def test_other_paper_unchanged_and_all_versions_removed(self):
  lib.register(str(self.pdf),str(self.p/'result'),str(self.root),'Fixture')
  d=fitz.open();d.new_page();other=self.p/'other.pdf';d.save(other);d.close();r=self.p/'other-result';r.mkdir();(r/'index.html').write_text('<body>other</body>');(r/'build-report.json').write_text(json.dumps({'source_sha256':lib.digest(other)}));v=lib.register(str(other),str(r),str(self.root),'Other');folder=self.root/'papers'/v['paper_id'];before={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
  delete_results(self.root,self.sha,['references'],self.recycle)
  for path,data in before.items():self.assertEqual((folder/path).read_bytes(),data)
  self.assertEqual(len(self.paper()['versions']),2)
  for v in self.paper()['versions']:self.assertNotIn('references',v['tasks']);self.assertFalse((self.root/'papers'/self.sha/v['id']/'result/references.html').exists())
if __name__=='__main__':unittest.main()

