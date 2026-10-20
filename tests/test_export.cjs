// Tests PDF assembly with the real bundled pdf-lib; not a browser visual test.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const PDFLib=require(path.join(root,'assets/vendor/pdf-lib.min.js'));

(async()=>{
  const source=await PDFLib.PDFDocument.create();
  source.addPage([500,500]).drawText('Synthetic source page');
  const pdf=Buffer.from(await source.save()).toString('base64');
  const notes=[];
  const context={PDFLib,Uint8Array,atob:s=>Buffer.from(s,'base64').toString('binary'),
    DATA:{pdf},CARD:{paper:{title:'合成测试'},annotations:[{id:'E01',step:1,page:1,title:'待定位证据',quote:'missing',explanation:'中文解释',layer:'author',anchor_status:'not_found',normalized_rects:[]}]},
    colors:['#2872a7'],manual:[{id:'M1',page:1,rect:[.1,.1,.2,.2],text:'我的个人勾画'},{id:'M2',page:1,rect:[.1,.1,.2,.2],kind:'correction',target:'E01',text:'我的纠正'}]};
  vm.createContext(context);
  // Keep the library and the export function in the same JavaScript realm.
  vm.runInContext(fs.readFileSync(path.join(root,'assets/vendor/pdf-lib.min.js'),'utf8'),context);
  const code=fs.readFileSync(path.join(root,'assets/export-pdf.js'),'utf8');
  vm.runInContext(code,context);
  // Canvas paint is a browser concern; use a valid 1x1 PNG for assembly tests.
  context.noteImages=(note)=>{
    notes.push(note.text);
    return [{png:new Uint8Array(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=','base64')),height:25,desired:note.y}];
  };
  const bytes=await context.makeCombinedPDF();
  const result=await PDFLib.PDFDocument.load(bytes);
  assert.equal(result.getPageCount(),1);
  assert.equal(result.getPage(0).getWidth(),790);
  assert.equal(notes.length,3);
  assert.ok(notes.some(n=>n.includes('页内位置待定位')));
  assert.ok(notes.some(n=>n.includes('我的个人勾画')));
  assert.ok(notes.some(n=>n.includes('我的纠正')));
  const template=fs.readFileSync(path.join(root,'assets/viewer.html'),'utf8');
  const scripts=[...template.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
  const ui=scripts.at(-1)[1].replace('/*__EXPORT_CODE__*/',code);
  new vm.Script(ui);
  console.log('PASS: PDF assembly includes AI, manual and correction layers; unresolved label retained; template JavaScript parses. Canvas rendering/UI remains a browser check.');
})().catch(error=>{console.error(error);process.exitCode=1});
