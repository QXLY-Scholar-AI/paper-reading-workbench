// Logic checks in a minimal DOM harness. This is NOT a rendered-browser test.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const template=fs.readFileSync(path.join(__dirname,'../assets/gallery.html'),'utf8');
const scripts=[...template.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]).join('\n');
const data={paper:{title:'Fixture',sha256:'a'.repeat(64)},modes:{reported_values:'文中数值',template:'模板'},figures:[1,2,3].map(i=>({id:'F'+i,label:'Figure '+i,page:i,mode:i===2?'template':'reported_values',chart_type:i===3?'森林图':'图型',interpretation:'context '+i,original:'data:image/png;base64,AA',preview:null,run:{status:'not_run'},data:{source:'fixture'},reuse:'replace data',caption:'caption',context:[],code:'plot(1)',downloads:[]}))};
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{value:id==='mode'?'all':'',textContent:'',innerHTML:'',hidden:true,open:false,disabled:false,scrollTop:0,style:{},add(){},focus(){},select(){},addEventListener(){},scrollIntoView(){},showModal(){this.open=true},close(){this.open=false},querySelector(){return null}});return elements.get(id)}
el('data').textContent=JSON.stringify(data);
const saved=new Map();const context={document:{getElementById:el},localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)},Option:function(t,v){this.text=t;this.value=v},navigator:{clipboard:{writeText:async()=>{throw Error('clipboard denied')}}},setTimeout(){},URL:{},Blob:function(){}};
vm.createContext(context);vm.runInContext(scripts,context);
assert.equal((el('cards').innerHTML.match(/class="tile"/g)||[]).length,3);
assert(!el('cards').innerHTML.includes('查看 R 代码'),'overview must not contain full details');
vm.runInContext("openFigure('F1','F1')",context);assert.equal(el('detail-dialog').open,true);assert.equal(el('previous-figure').disabled,true);assert(el('figure-detail').innerHTML.includes('查看 R 代码'));
el('next-figure').onclick();assert(el('detail-label').textContent.includes('Figure 2'));assert(el('figure-detail').innerHTML.includes('示例数据模板'));
el('next-figure').onclick();assert.equal(el('next-figure').disabled,true);el('previous-figure').onclick();assert(el('detail-label').textContent.includes('Figure 2'));
vm.runInContext("handleAction({target:{closest:()=>({dataset:{action:'favorite',id:'F2'}})}})",context);assert(saved.size>0);
vm.runInContext('closeFigure()',context);el('favfilter').onclick();assert.equal((el('cards').innerHTML.match(/class="tile"/g)||[]).length,1);
el('search').value='森林';el('search').oninput();assert.equal((el('cards').innerHTML.match(/class="tile"/g)||[]).length,0);
el('search').value='';el('favfilter').onclick();vm.runInContext("openFigure('F2','F2')",context);
(async()=>{await vm.runInContext("copy('example R code')",context);assert.equal(el('copy-fallback').hidden,false);assert.equal(el('copy-fallback').value,'example R code');console.log('PASS: compact overview, modal, previous/next, favorites/filter, copy fallback logic. Rendered browser not checked.');})().catch(e=>{console.error(e);process.exitCode=1});
