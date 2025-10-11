/* ---------------- Phosphor toggle ---------------- */
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

/* ---------------- Sequential Typewriter with Skip + No-Jump ---------------- */
(function(){
    const SPEED = 28, MAXDUR = 1500;
    const els = Array.from(document.querySelectorAll('p[data-typewriter]'));
    if(!els.length) return;

    let lastCaret = null;
    let skipAll = false;

    // Snapshot text nodes & full text for ALL paragraphs up-front,
    // and lock their min-height so layout won't jump when typing/skip occurs.
    els.forEach(el=>{
        // measure final height using an offscreen clone
        const h = measureHeight(el);
        el.style.minHeight = h + 'px';
        // store text nodes + their full values (preserve links)
        const {nodes, fulls} = snapshotText(el);
        el.__nodes = nodes;
        el.__fulls = fulls;
    });

    function measureHeight(el){
        const rect = el.getBoundingClientRect();
        const clone = el.cloneNode(true);
        clone.style.visibility = 'hidden';
        clone.style.position = 'absolute';
        clone.style.left = '-9999px';
        clone.style.top = '0';
        clone.style.width = rect.width ? rect.width + 'px' : el.offsetWidth + 'px';
        clone.style.minHeight = '0'; // let it size naturally
        document.body.appendChild(clone);
        const h = clone.getBoundingClientRect().height;
        document.body.removeChild(clone);
        return Math.ceil(h);
    }

function snapshotText(root){
    const nodes=[], fulls=[];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(n){ return n.nodeValue.trim().length ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; }
    });
    let n; while((n = walker.nextNode())){ nodes.push(n); fulls.push(n.nodeValue); }
    return {nodes, fulls};
}

function clearNodes(el){
    el.__nodes.forEach(n=>{ n.nodeValue = ""; });
}

function revealNodes(el){
    el.__nodes.forEach((n,i)=>{ n.nodeValue = el.__fulls[i]; });
}

function typeElement(el){
    return new Promise(resolve=>{
        if(el.__typed) return resolve();
        el.__typed = true;

        // make visible now (we reserved space via min-height)
        el.style.visibility = 'visible';

        // caret on this element
        if(lastCaret) lastCaret.classList.remove('caret');
        el.classList.add('caret'); lastCaret = el;

        // instant reveal if skipping
        if(skipAll){
            revealNodes(el);
            return resolve();
        }

        // otherwise type text nodes progressively
        clearNodes(el);

        const total = el.__fulls.reduce((s,t)=>s+t.length,0);
        const step = Math.max(1, Math.round(total / (Math.min(MAXDUR, total * SPEED) / SPEED)));

        let idxNode = 0, idxChar = 0, written = 0;

        const timer = setInterval(()=>{
            if(skipAll){
            clearInterval(timer); revealNodes(el); return resolve();
            }

            let remain = step;
            while(remain > 0 && idxNode < el.__nodes.length){
                const full = el.__fulls[idxNode];
                const take = Math.min(remain, full.length - idxChar);
                if(take > 0){
                    el.__nodes[idxNode].nodeValue += full.slice(idxChar, idxChar + take);
                    idxChar += take; written += take; remain -= take;
                }
                if(idxChar >= full.length){ idxNode++; idxChar = 0; }
            }

            if(written >= total){
                clearInterval(timer);
                // exact final state
                revealNodes(el);
                resolve();
            }
        }, SPEED);
    });
}

  // Run paragraphs sequentially
(async function runSequential(){
    for(const el of els){
        await typeElement(el);
        if(skipAll) break; // if skipped, we'll reveal the rest below
    }
    if(skipAll){
        // reveal any remaining immediately
        els.forEach(el=>{
            if(!el.__typed){
                el.__typed = true;
                el.style.visibility = 'visible';
                revealNodes(el);
            }
        });
        if(els.length){ els[els.length-1].classList.add('caret'); }
    }
})();

// Skip handlers: click / touch / any key
function skipAllTyping(){
    if(skipAll) return;
    skipAll = true;
}

document.addEventListener('click', skipAllTyping, {passive:true});
document.addEventListener('touchstart', skipAllTyping, {passive:true});
document.addEventListener('keydown', skipAllTyping);

})();