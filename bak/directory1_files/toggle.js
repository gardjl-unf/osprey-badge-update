(function(){
    const root=document.documentElement,
        toggle=document.getElementById('phosphorToggle'),
        label=document.getElementById('phosphorLabel');

    const saved=localStorage.getItem('phosphor')==='amber';
    apply(saved); toggle.checked=saved;
    toggle.addEventListener('change',()=>apply(toggle.checked));

    function apply(amber){
    if(amber){ root.setAttribute('data-phosphor','amber'); label.textContent='Amber'; }
    else { root.removeAttribute('data-phosphor'); label.textContent='Green'; }
    localStorage.setItem('phosphor', amber ? 'amber' : 'green');
  }
})();