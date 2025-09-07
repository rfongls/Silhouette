(function(){
  function markActive(){
    const path = location.pathname;
    const map = [
      {sel:'[data-nav="reports"]', match:/^\/ui\/home\/?$/},
      {sel:'[data-nav="skills"]', match:/^\/ui\/skills\/?/},
    ];
    map.forEach(m => { const a=document.querySelector(m.sel); if(!a) return; if(m.match.test(path)) a.classList.add('active'); });
  }
  window.addEventListener('DOMContentLoaded', markActive);
})();
