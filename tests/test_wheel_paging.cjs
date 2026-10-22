const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../assets/viewer.html'),'utf8');const code=html.split('// BEGIN WHEEL PAGING')[1].split('// END WHEEL PAGING')[0];
let now=1000,handler,prevented=0,saved=0,moves=[];const load=[];const scroller={scrollTop:100,clientHeight:500,scrollHeight:1200,addEventListener(name,fn,opts){assert.equal(name,'wheel');assert.equal(opts.passive,false);handler=fn}};const image={addEventListener(name,fn,opts){assert.equal(name,'load');assert(opts.once);load.push(fn)}};
const c=vm.createContext({page:2,DATA:{pages:[1,2,3,4]},drawing:false,$:id=>id==='paper-scroll'?scroller:image,Date:{now:()=>now},saveProgress(){saved++},requestAnimationFrame(fn){fn()},movePage(n){moves.push(n);c.page=n;scroller.scrollTop=0}});vm.runInContext(code,c);
function wheel(deltaY,extra={}){handler({deltaY,deltaX:0,deltaMode:0,preventDefault(){prevented++},...extra})}
wheel(120);assert.equal(moves.length,0);assert.equal(prevented,0,'normal scroll remains native');
scroller.scrollTop=700;wheel(30);wheel(30);assert.equal(moves.length,0);wheel(30);assert.equal(c.page,3);assert.equal(scroller.scrollTop,0);
scroller.scrollTop=700;now+=100;wheel(300);assert.equal(moves.length,1,'inertia cannot instantly skip a page');now+=700;wheel(120);assert.equal(c.page,4);
const atLast=moves.length;scroller.scrollTop=700;wheel(120);assert.equal(moves.length,atLast,'last page stops');
now+=700;scroller.scrollTop=0;wheel(-120);assert.equal(c.page,3);assert.equal(scroller.scrollTop,700,'previous page opens at bottom');
now+=700;scroller.scrollTop=0;const before=moves.length;wheel(-120,{ctrlKey:true});wheel(-120,{deltaX:300});c.drawing=true;wheel(-120);c.drawing=false;assert.equal(moves.length,before,'zoom, horizontal scroll and drawing do not turn pages');
c.page=1;scroller.scrollTop=0;wheel(-120);assert.equal(moves.length,before,'first page stops');
c.page=2;now+=700;scroller.scrollTop=700;wheel(3,{deltaMode:1});assert.equal(c.page,2);wheel(3,{deltaMode:1});assert.equal(c.page,3,'line-mode wheels normalize');assert(saved>0);assert(html.includes('overscroll-behavior:contain'));
console.log('PASS: native in-page scroll, accumulated edge intent, next/previous landing, cooldown, first/last limits, modifiers/drawing exclusions and line-mode wheel.');
