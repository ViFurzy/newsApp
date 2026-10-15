"""
ui/styles.py — All CSS and JS injected into the Streamlit page.

Call inject_styles() once at the top of dashboard.py after set_page_config.
"""
import json
from functools import lru_cache
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from config import TAB_BACKGROUNDS

# ── JS: preconnect / DNS prefetch hints ───────────────────────────────────────
_JS_PRECONNECT = """
<script>
(function(){
    var h = window.parent.document.head;
    [
        {rel:'dns-prefetch',href:'https://images.unsplash.com'},
        {rel:'dns-prefetch',href:'https://flagcdn.com'},
        {rel:'dns-prefetch',href:'https://api.jikan.moe'},
        {rel:'dns-prefetch',href:'https://cdn.gamerpower.com'},
    ].forEach(function(x){
        if(h.querySelector('link[href="'+x.href+'"]'))return;
        var l=window.parent.document.createElement('link');
        l.rel=x.rel;l.href=x.href;
        if(x.co)l.crossOrigin='';
        h.appendChild(l);
    });
})();
</script>
"""

# ── JS: theme toggle (dark ↔ light, persisted to localStorage) ────────────────
_JS_THEME = """
<script>
(function(){
    var p=window.parent.document;
    if(p.getElementById('da-theme-btn'))return;
    var btn=p.createElement('button');
    btn.id='da-theme-btn';
    btn.setAttribute('aria-label','Toggle light or dark theme');
    var sun='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
    var moon='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    var saved;try{saved=window.parent.localStorage.getItem('_da_theme');}catch(e){}
    var light=saved==='light';
    function applyTheme(l){
        if(l){
            p.documentElement.setAttribute('data-theme','light');
            btn.innerHTML=moon;
            btn.style.background='rgba(235,229,220,0.95)';
            btn.style.color='#9b5220';
            btn.style.borderColor='rgba(0,0,0,0.12)';
        }else{
            p.documentElement.removeAttribute('data-theme');
            btn.innerHTML=sun;
            btn.style.background='rgba(14,14,17,0.90)';
            btn.style.color='#c87038';
            btn.style.borderColor='rgba(255,255,255,0.12)';
        }
    }
    btn.style.cssText='position:fixed;bottom:24px;right:24px;width:40px;height:40px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(14,14,17,0.90);color:#c87038;cursor:pointer;z-index:9999999;box-shadow:0 2px 16px rgba(0,0,0,.6);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:all .22s ease;display:flex;align-items:center;justify-content:center;outline:none;';
    applyTheme(light);
    btn.onmouseover=function(){btn.style.borderColor=light?'rgba(0,0,0,0.22)':'rgba(255,255,255,0.26)';};
    btn.onmouseout=function(){btn.style.borderColor=light?'rgba(0,0,0,0.12)':'rgba(255,255,255,0.12)';};
    btn.onclick=function(){
        light=!light;
        try{window.parent.localStorage.setItem('_da_theme',light?'light':'dark');}catch(e){}
        applyTheme(light);
    };
    p.body.appendChild(btn);
})();
</script>
"""

# ── JS: MutationObserver stamps .pagination-row on the horizontal block ───────
_JS_PAGINATION = """
<script>
(function(){
    var p=window.parent.document;
    function mark(){
        p.querySelectorAll('button').forEach(function(b){
            var s=b.textContent.trim();
            if(s==='◀')b.setAttribute('aria-label','Previous page');
            else if(s==='▶')b.setAttribute('aria-label','Next page');
        });
        p.querySelectorAll('.pagination-label').forEach(function(lbl){
            var b=lbl.closest('[data-testid="stHorizontalBlock"]');
            if(b&&!b.classList.contains('pagination-row'))b.classList.add('pagination-row');
        });
    }
    mark();
    if(!window.parent._pgObs){
        window.parent._pgObs=new MutationObserver(mark);
        window.parent._pgObs.observe(p.body,{childList:true,subtree:true});
    }
})();
</script>
"""

# ── JS: tab persistence (localStorage) + initial loader overlay ───────────────
_JS_TABS = """
<script>
(function(){
    var p=window.parent.document;
    var TAB_KEYS=['ai','gaming','anime','vibe','design','saved'];
    var LS_KEY='_da_active_tab';

    if(!p.getElementById('da-loader')&&!window.parent._daTabRestored){
        var ov=p.createElement('div');
        ov.id='da-loader';
        ov.style.cssText='position:fixed;inset:0;background:#09090b;z-index:9999999;transition:opacity 0.15s ease;pointer-events:none;';
        p.body.appendChild(ov);
    }

    function hideLoader(){
        var el=p.getElementById('da-loader');
        if(!el)return;
        el.style.opacity='0';
        setTimeout(function(){if(el&&el.parentNode)el.parentNode.removeChild(el);},180);
    }

    function getTabs(){ return p.querySelectorAll('[data-baseweb="tab"]'); }

    function attachListeners(){
        getTabs().forEach(function(tab,idx){
            if(tab._daTracked)return;
            tab._daTracked=true;
            tab.addEventListener('click',function(){
                try{window.parent.localStorage.setItem(LS_KEY,TAB_KEYS[idx]);}catch(e){}
            });
        });
    }

    function restoreTab(){
        if(window.parent._daTabRestored){attachListeners();hideLoader();return;}
        var tabs=getTabs();
        if(!tabs.length)return;
        window.parent._daTabRestored=true;
        var saved;
        try{saved=window.parent.localStorage.getItem(LS_KEY);}catch(e){}
        var idx=TAB_KEYS.indexOf(saved);
        if(idx>0&&tabs[idx]){tabs[idx].click();setTimeout(hideLoader,120);}
        else{hideLoader();}
        attachListeners();
    }

    restoreTab();

    if(!window.parent._daTabObs){
        window.parent._daTabObs=new MutationObserver(function(){
            attachListeners();
            if(!window.parent._daTabRestored)restoreTab();
        });
        window.parent._daTabObs.observe(p.body,{childList:true,subtree:true});
    }
})();
</script>
"""

# ── JS: per-tab background images (cross-fade on tab switch / theme change) ───
_JS_BACKGROUNDS_TPL = """
<script>
(function(){
    var p=window.parent.document;

    var IMGS=__IMGS__;
    var TINTS=__TINTS__;

    function ov(){
        return p.documentElement.getAttribute('data-theme')==='light'
            ? 'rgba(243,237,229,0.90)'
            : 'rgba(17,17,19,0.91)';
    }

    function setup(){
        if(p.getElementById('da-bg-0'))return;
        IMGS.forEach(function(img,i){
            var el=p.createElement('div');
            el.id='da-bg-'+i;
            el.style.cssText=
                'position:fixed;inset:0;pointer-events:none;z-index:0;'+
                'background-size:cover;background-position:center center;'+
                'opacity:0;transition:opacity 1.1s ease;';
            p.body.insertBefore(el,p.body.firstChild);
        });
    }

    function paint(idx){
        var o=ov();
        IMGS.forEach(function(img,i){
            var el=p.getElementById('da-bg-'+i);
            if(!el)return;
            el.style.backgroundImage=
                'linear-gradient('+o+','+o+'),'+
                'radial-gradient(ellipse 110% 60% at 50% -8%,'+TINTS[i]+' 0%,transparent 65%),'+
                'url('+img+')';
            el.style.opacity=(i===idx)?'1':'0';
        });
    }

    function detect(){
        var tabs=p.querySelectorAll('[data-baseweb="tab"]');
        for(var i=0;i<tabs.length;i++){
            if(tabs[i].getAttribute('aria-selected')==='true'){setup();paint(i);return;}
        }
        setup();paint(0);
    }

    detect();
    if(!window.parent._tabColorObs){
        window.parent._tabColorObs=new MutationObserver(function(muts){
            for(var m=0;m<muts.length;m++){
                var a=muts[m].attributeName;
                if(a==='aria-selected'||a==='data-theme'){detect();return;}
            }
        });
        window.parent._tabColorObs.observe(p.body,{attributeFilter:['aria-selected'],subtree:true});
        window.parent._tabColorObs.observe(p.documentElement,{attributeFilter:['data-theme']});
    }
})();
</script>
"""



_JS_BACKGROUNDS = (
    _JS_BACKGROUNDS_TPL
    .replace("__IMGS__", json.dumps([b["image"] for b in TAB_BACKGROUNDS]))
    .replace("__TINTS__", json.dumps([b["tint"] for b in TAB_BACKGROUNDS]))
)


# ── JS: photo fade-in + broken/slow image fallback ────────────────────────────
# Streamlit strips inline onerror/onload, so this uses capture-phase listeners (load/error do not bubble).
_JS_IMAGES = """
<script>
(function(){
    var p=window.parent.document, SLOW_MS=7000;
    function shown(img){img.classList.add('is-loaded');}
    function fallback(img){
        var fb=img.getAttribute('data-fb');
        if(img.getAttribute('data-fell')||!fb){img.style.visibility='hidden';shown(img);return;}   // fallback failed too
        img.setAttribute('data-fell','1');
        img.removeAttribute('crossorigin');
        img.src=fb;
    }
    function check(img){
        if(img.complete){ if(img.naturalWidth>0)shown(img); else fallback(img); }
        else if(!img._daSlow){
            img._daSlow=setTimeout(function(){ if(!img.classList.contains('is-loaded'))fallback(img); },SLOW_MS);
        }
    }
    function sweep(){p.querySelectorAll('img.nc-photo:not(.is-loaded)').forEach(check);}
    function onEvent(e){
        var t=e.target;
        if(!t||!t.classList||!t.classList.contains('nc-photo'))return;
        if(e.type==='load')shown(t); else fallback(t);
    }
    ['load','error'].forEach(function(n){
        var key='_daImg_'+n;
        if(window.parent[key])p.removeEventListener(n,window.parent[key],true);   // replace, never stack
        window.parent[key]=onEvent;p.addEventListener(n,onEvent,true);
    });
    if(window.parent._daImgObs)window.parent._daImgObs.disconnect();
    window.parent._daImgObs=new MutationObserver(sweep);
    window.parent._daImgObs.observe(p.body,{childList:true,subtree:true});
    sweep();
})();
</script>
"""

# ── JS: read-later stars (kept in this browser's localStorage) + Saved tab ────
_JS_SAVED = """
<script>
(function(){
    var p=window.parent.document, KEY='_da_saved';
    function load(){try{return JSON.parse(window.parent.localStorage.getItem(KEY)||'{}');}catch(e){return {};}}
    function store(o){try{window.parent.localStorage.setItem(KEY,JSON.stringify(o));}catch(e){}}
    function sync(){
        var s=load(), keys=Object.keys(s);
        var box=p.getElementById('da-saved');
        if(box){
            var sig=keys.join('|');
            if(box.getAttribute('data-sig')!==sig||!box.firstChild){
                box.setAttribute('data-sig',sig);
                box.innerHTML=keys.length
                    ?'<div class="bento-grid bg-2">'+keys.slice().reverse().map(function(k){return s[k];}).join('')+'</div>'
                    :'<div class="empty-state">Nothing saved yet. Use the star on any story.</div>';
            }
        }
        p.querySelectorAll('.nc-save').forEach(function(b){
            var on=!!s[b.getAttribute('data-link')];
            if(b.getAttribute('aria-pressed')!==String(on)){
                b.setAttribute('aria-pressed',String(on));
                b.textContent=on?'★':'☆';
                b.setAttribute('aria-label',on?'Remove from saved':'Save for later');
            }
        });
    }
    function onClick(e){
        var b=e.target.closest&&e.target.closest('.nc-save');
        if(!b)return;
        e.preventDefault();e.stopPropagation();
        var link=b.getAttribute('data-link'), s=load();
        if(s[link]){delete s[link];}
        else{
            var c=b.closest('.nc').cloneNode(true), cb=c.querySelector('.nc-save');
            cb.setAttribute('aria-pressed','true');cb.textContent='★';cb.setAttribute('aria-label','Remove from saved');
            s[link]=c.outerHTML;
        }
        store(s);sync();
    }
    // replace (not stack) handlers: this iframe can be recreated on rerun
    if(window.parent._daSaveClick)p.removeEventListener('click',window.parent._daSaveClick,true);
    window.parent._daSaveClick=onClick;p.addEventListener('click',onClick,true);
    if(window.parent._daSaveObs)window.parent._daSaveObs.disconnect();
    window.parent._daSaveObs=new MutationObserver(sync);
    window.parent._daSaveObs.observe(p.body,{childList:true,subtree:true});
    sync();
})();
</script>
"""

# ── Public API ────────────────────────────────────────────────────────────────

_CSS_FILES = [Path(__file__).parent / "fonts.css", Path(__file__).parent / "style.css"]


@lru_cache(maxsize=2)
def _css_for(_mtime: float) -> str:
    return "<style>" + "".join(f.read_text(encoding="utf-8") for f in _CSS_FILES) + "</style>"


def _css() -> str:
    return _css_for(max(f.stat().st_mtime for f in _CSS_FILES))   # edits show up without a restart


def inject_styles() -> None:
    """Inject all CSS and JS into the Streamlit page. Call once after set_page_config."""
    st.markdown(_css(), unsafe_allow_html=True)
    # one iframe for all scripts (each is an independent IIFE)
    components.html("".join((_JS_PRECONNECT, _JS_THEME, _JS_PAGINATION, _JS_TABS, _JS_BACKGROUNDS, _JS_SAVED, _JS_IMAGES)), height=0, width=0)
