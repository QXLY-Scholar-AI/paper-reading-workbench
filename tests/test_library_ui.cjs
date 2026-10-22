// DOM logic checks only; this does not claim browser rendering verification.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../assets/library.html'),'utf8');
const script=html.split('<script>').at(-1).split('</script>')[0];
const sha='a'.repeat(64),other='b'.repeat(64),version='20261022T080459-test';
function paper(id,title){return {id,sha256:id,title,pages:10,latest:{reading:`papers/${id}/${version}/result/index.html`},versions:[{id:version,created:'2026-10-22',tasks:{reading:`papers/${id}/${version}/result/index.html`}}]}}
const papers=[paper(sha,'Affordable Housing, Unaffordable Credit?'),paper(other,'Another <paper>')];
const els={};function el(id){return els[id]??=( {value:id==='kind'?'all':'',textContent:'',innerHTML:'',dataset:{},showModal(){this.open=true},close(){this.open=false},focus(){this.focused=true},select(){this.selected=true}})}
el('data').textContent=JSON.stringify({papers});let copied='';
const context=vm.createContext({document:{getElementById:el,documentElement:{dataset:{}},addEventListener(){}},localStorage:{getItem(){return null},setItem(){}},navigator:{clipboard:{async writeText(text){copied=text}}},setTimeout(){}});
vm.runInContext(script,context);
assert(!html.includes('data-prompt='),'top-level copy buttons removed');
assert(el('list').innerHTML.includes('data-task="gallery"'));assert(el('list').innerHTML.includes('论文初稿（Beta）：未生成')); 
assert(el('list').innerHTML.includes(`href="papers/${sha}/${version}/result/index.html"`),'existing result still opens');
vm.runInContext(`openTask('${sha}','gallery')`,context);
assert(el('task-dialog').open);assert(el('task-prompt').value.includes(papers[0].title));
assert(!el('task-prompt').value.includes(papers[1].title));assert(el('task-prompt').value.includes(`${sha}/${version}/original.pdf`));
(async()=>{
 await el('copy-task').onclick();assert.strictEqual(copied,el('task-prompt').value);
 vm.runInContext(`openTask('${other}','draft')`,context);
 assert(el('task-hint').textContent.includes('请填写课题！'));assert(el('task-prompt').value.includes('评估课题是否可写'));assert(el('task-prompt').value.includes(papers[1].title));assert(el('task-prompt').value.includes('大纲'));assert(el('task-prompt').value.includes('不要直接')); 
 context.navigator.clipboard.writeText=async()=>{throw Error('denied')};await el('copy-task').onclick();assert(el('task-prompt').selected);assert(el('task-notice').textContent.includes('Ctrl+C'));
 el('close-task').onclick();assert(!el('task-dialog').open);
 console.log('PASS: per-paper missing-task modal, correct title/PDF, existing links, draft reminder, copy and fallback. Browser rendering not checked.');
})().catch(e=>{console.error(e);process.exitCode=1});
