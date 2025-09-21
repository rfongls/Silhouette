// static/js/pipeline_tray.js
// Reveals per-panel trays (generate, deid, validate, mllp) when their output is present.
(() => {
  'use strict'; const D=document;
  const $=(s,r=D)=>r.querySelector(s), $$=(s,r=D)=>Array.from(r.querySelectorAll(s));
  const PANELS={
    generate:{panel:'generate-panel', tray:'gen-run-tray', outputs:['#gen-output','[data-role="gen-output"]','textarea[name="message"]','pre','.gen-output']},
    deid:{panel:'deid-panel', tray:'deid-run-tray', outputs:['#deid-output','[data-role="deid-output"]','#deidentify-output','pre','.deid-output']},
    validate:{panel:'validate-panel', tray:'validate-run-tray', outputs:['#validate-output','#validation-results','[data-role="validate-output"]','pre','.validate-output']},
    mllp:{panel:'mllp-panel', tray:'mllp-run-tray', outputs:['#mllp-output','#ack-output','[data-role="ack-output"]','pre','.mllp-output']},
    translate:{panel:'translate-panel', tray:'translate-run-tray', outputs:['#translate-output','.translate-output','pre','code']}
  };
  const has=(el)=>el && ((('value'in el)?el.value:el.textContent)||'').trim().length>0;
  function setVis(key,on){const c=PANELS[key];const w=$('#'+c.panel); if(!w)return; const t=w.querySelector('#'+c.tray)||w.querySelector('.action-tray'); if(!t)return; t.hidden=!on; t.classList.toggle('visible',!!on);}
  function findOut(w,cfg){for(const s of cfg.outputs){const el=w.querySelector(s); if(el) return el;} return w.querySelector('textarea,pre,code,output');}
  function watch(key){const cfg=PANELS[key]; const w=$('#'+cfg.panel); if(!w)return; setVis(key,false); const out=findOut(w,cfg);
    const upd=()=>setVis(key,has(findOut(w,cfg)));
    if(out){ ('value'in out)&&out.addEventListener('input',upd); new MutationObserver(upd).observe(out,{childList:true,characterData:true,subtree:true});}
    $$('[data-action]',w).forEach(b=>b.addEventListener('click',()=>{setTimeout(upd,50);setTimeout(upd,500);setTimeout(upd,1500);})); }
  function init(){ Object.keys(PANELS).forEach(watch);
    if(window.InteropUI){const IU=window.InteropUI; const wrap=(fn,k)=>(...a)=>{try{setVis(k,true);}catch{} return fn?.apply(IU,a);};
      if(typeof IU.onGenerateComplete==='function')IU.onGenerateComplete=wrap(IU.onGenerateComplete,'generate');
      if(typeof IU.onDeidentifyComplete==='function')IU.onDeidentifyComplete=wrap(IU.onDeidentifyComplete,'deid');
      if(typeof IU.onValidateComplete==='function')IU.onValidateComplete=wrap(IU.onValidateComplete,'validate');}}
  (D.readyState==='loading')?D.addEventListener('DOMContentLoaded',init):init();
})();
