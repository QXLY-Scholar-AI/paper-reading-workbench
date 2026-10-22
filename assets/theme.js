(()=>{
 if(typeof window==='undefined')return;
 const key='paper-library-theme',root=document.documentElement;
 let dark=root.dataset.theme==='dark';
 try{dark=localStorage.getItem(key)==='dark'}catch(e){}
 const existing=document.getElementById('theme');
 const button=existing||document.createElement('button');
 if(!existing){button.id='workbench-theme-button';button.type='button';document.body.append(button)}
 const buttons=[button];

 function apply(){root.dataset.theme=dark?'dark':'light';root.style.colorScheme=dark?'dark':'light';buttons.forEach(b=>{b.textContent=dark?'日间模式':'夜间模式';b.setAttribute('aria-label',dark?'切换到日间模式':'切换到夜间模式');b.setAttribute('aria-pressed',String(dark))})}
 buttons.forEach(b=>b.onclick=()=>{dark=!dark;apply();try{localStorage.setItem(key,dark?'dark':'light')}catch(e){}});
 window.addEventListener('storage',e=>{if(e.key===key||e.key===null){dark=e.newValue==='dark';apply()}});
 apply();
})();
