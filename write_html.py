import os, sys

HTML = b"""<!DOCTYPE html>
<html lang="fr" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="Cache-Control" content="no-store,no-cache,must-revalidate"/>
<title>Kazia</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root[data-theme="dark"]{--bg:#0d0f1a;--surface:#13162b;--surface2:#1c2040;--border:#2a2f52;--accent:#7c6fff;--accent2:#a78bfa;--text:#e8eaf6;--muted:#6b7280;--success:#10b981;--error:#ef4444;--radius:12px;--shadow:0 4px 24px rgba(0,0,0,.5);--glow:0 0 32px rgba(124,111,255,.18)}
:root[data-theme="light"]{--bg:#f0f2ff;--surface:#fff;--surface2:#eef0ff;--border:#c7caee;--accent:#5b4fff;--accent2:#7c3aed;--text:#1e1b3a;--muted:#64748b;--success:#059669;--error:#dc2626;--radius:12px;--shadow:0 4px 24px rgba(0,0,0,.08);--glow:0 0 32px rgba(91,79,255,.12)}
html,body{height:100%;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
body{display:flex;height:100vh}
#sidebar{width:280px;min-width:280px;height:100%;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;transition:width .25s,min-width .25s;overflow:hidden;z-index:20}
#sidebar.closed{width:0;min-width:0}
#sidebar-inner{min-width:280px;display:flex;flex-direction:column;height:100%;overflow-y:auto}
#main{flex:1;display:flex;flex-direction:column;height:100vh;overflow:hidden;min-width:0}
.sb-brand{display:flex;align-items:center;gap:.6rem;padding:1.1rem 1rem .9rem;border-bottom:1px solid var(--border)}
.sb-logo{width:32px;height:32px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
.sb-title{font-size:1rem;font-weight:800}.sb-title span{color:var(--accent)}
.sb-sub{font-size:.68rem;color:var(--muted)}
.sb-tabs{display:flex;border-bottom:1px solid var(--border)}
.sb-tab{flex:1;padding:.5rem .25rem;font-size:.73rem;font-weight:600;text-align:center;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;transition:all .15s}
.sb-tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.sb-panel{display:none;flex-direction:column;gap:.75rem;padding:.9rem;flex:1}
.sb-panel.active{display:flex}
.sb-label{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);display:block;margin-bottom:.3rem}
#codeList{max-height:210px;overflow-y:auto;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:.5rem}
.cc{display:flex;align-items:center;gap:.45rem;padding:.2rem 0;font-size:.82rem;cursor:pointer}
.cc input{accent-color:var(--accent)}
.dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.dot.ok{background:var(--success)}.dot.nok{background:var(--error)}
.cc-hint{font-size:.68rem;color:var(--muted);margin-top:.25rem}
.mode-row{display:flex;gap:.4rem}
.mode-btn{flex:1;padding:.45rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--bg);color:var(--muted);font-size:.79rem;font-weight:600;cursor:pointer;transition:all .15s}
.mode-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.slider-row{display:flex;align-items:center;gap:.6rem}
#topKSlider{flex:1;accent-color:var(--accent)}
#topKVal{font-size:.85rem;color:var(--accent);min-width:1.5rem;font-weight:700}
#statusPill{display:inline-flex;align-items:center;gap:.3rem;font-size:.73rem;padding:.22rem .65rem;border-radius:20px;border:1px solid var(--border)}
#statusPill.ok{border-color:var(--success);color:var(--success)}
#statusPill.err{border-color:var(--error);color:var(--error)}
.btn{width:100%;padding:.55rem;border:none;border-radius:var(--radius);font-size:.83rem;cursor:pointer;font-weight:600;transition:opacity .15s;font-family:inherit}
.btn:hover{opacity:.85}.btn:disabled{opacity:.4;cursor:not-allowed}
.btn.primary{background:var(--accent);color:#fff}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text)}
.sep{border:none;border-top:1px solid var(--border)}
.hist-item{padding:.55rem .7rem;border-radius:var(--radius);background:var(--surface2);border:1px solid var(--border);cursor:pointer;transition:border-color .15s}
.hist-item:hover{border-color:var(--accent)}
.hi-title{font-size:.82rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hi-meta{font-size:.7rem;color:var(--muted);margin-top:.1rem}
.sb-footer{padding:.75rem 1rem;border-top:1px solid var(--border);font-size:.68rem;color:var(--muted);line-height:1.7;margin-top:auto}
.sb-footer strong{color:var(--accent2)}
#topbar{display:flex;align-items:center;gap:.75rem;padding:.65rem 1.25rem;border-bottom:1px solid var(--border);background:var(--surface);flex-shrink:0}
#toggleSidebar{background:none;border:none;color:var(--muted);font-size:1.2rem;cursor:pointer;padding:.2rem .3rem;border-radius:6px;line-height:1;transition:color .15s}
#toggleSidebar:hover{color:var(--accent)}
.topbar-brand{display:flex;align-items:center;gap:.5rem;flex:1}
.topbar-logo{width:26px;height:26px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.85rem}
.topbar-name{font-size:.95rem;font-weight:800}.topbar-name span{color:var(--accent)}
.topbar-badge{font-size:.68rem;padding:.15rem .5rem;border-radius:10px;background:var(--surface2);border:1px solid var(--border);color:var(--muted)}
.topbar-badge.active{border-color:var(--accent2);color:var(--accent2)}
.icon-btn{background:none;border:1px solid var(--border);color:var(--muted);border-radius:8px;padding:.3rem .65rem;font-size:.8rem;cursor:pointer;transition:all .15s;font-family:inherit}
.icon-btn:hover{border-color:var(--accent);color:var(--accent)}
#messages{flex:1;overflow-y:auto;padding:1.5rem;display:flex;flex-direction:column;gap:1.25rem;scroll-behavior:smooth}
.msg{max-width:820px;width:100%}
.msg.user{align-self:flex-end}.msg.assistant{align-self:flex-start}
.bubble{padding:.85rem 1.1rem;border-radius:var(--radius);line-height:1.7;font-size:.92rem;word-break:break-word}
.msg.user .bubble{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-bottom-right-radius:3px;white-space:pre-wrap}
.msg.assistant .bubble{background:var(--surface);border:1px solid var(--border);border-bottom-left-radius:3px}
.msg.assistant .bubble h1,.msg.assistant .bubble h2,.msg.assistant .bubble h3{font-size:.97rem;font-weight:700;margin:.75rem 0 .2rem;color:var(--accent2)}
.msg.assistant .bubble p{margin:.3rem 0}
.msg.assistant .bubble > p:first-child{margin-top:0}
.msg.assistant .bubble > p:last-child{margin-bottom:0}
.msg.assistant .bubble ul,.msg.assistant .bubble ol{padding-left:1.3rem;margin:.3rem 0}
.msg.assistant .bubble li{margin:.2rem 0}
.msg.assistant .bubble code{background:var(--bg);border-radius:4px;padding:.1rem .4rem;font-size:.85em}
.msg-footer{display:flex;align-items:center;gap:.45rem;margin-top:.35rem;flex-wrap:wrap;padding:0 .2rem}
.msg-time{font-size:.69rem;color:var(--muted)}
.t-chip{display:inline-block;background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:.04rem .35rem;font-size:.67rem;color:var(--muted)}
.t-chip.hi{color:var(--accent);border-color:var(--accent);font-weight:700}
.act-btn{background:none;border:none;color:var(--muted);font-size:.76rem;cursor:pointer;padding:.1rem .35rem;border-radius:4px;font-family:inherit;transition:color .15s}
.act-btn:hover{color:var(--accent)}
.thinking{display:flex;gap:5px;padding:.25rem 0}
.thinking span{width:7px;height:7px;border-radius:50%;background:var(--accent);animation:blink 1.2s infinite}
.thinking span:nth-child(2){animation-delay:.2s}.thinking span:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
.src-toggle{font-size:.76rem;color:var(--accent);cursor:pointer;background:none;border:none;padding:.25rem 0;display:flex;align-items:center;gap:.3rem;font-family:inherit}
.src-toggle:hover{text-decoration:underline}
.src-list{display:none;margin-top:.4rem;flex-direction:column;gap:.35rem}
.src-list.open{display:flex}
.src-card{background:var(--bg);border:1px solid var(--border);border-left:3px solid var(--accent2);border-radius:var(--radius);padding:.55rem .85rem;font-size:.78rem;line-height:1.55}
.src-card .src-code{font-size:.67rem;color:var(--accent2);font-weight:700;margin-bottom:.12rem}
.src-card .src-title{font-weight:600;color:var(--accent);margin-bottom:.1rem}
.src-card .src-score{color:var(--muted);font-size:.7rem}
.src-card .src-text{color:#a0aec0;margin-top:.2rem}
.sugg-row{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}
.sugg-chip{background:var(--surface2);border:1px solid var(--border);border-radius:20px;padding:.28rem .8rem;font-size:.77rem;cursor:pointer;transition:all .15s;color:var(--text)}
.sugg-chip:hover{border-color:var(--accent);color:var(--accent)}
#welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;min-height:0;overflow-y:auto;gap:1.75rem;padding:2rem;text-align:center}
.wlc-logo{width:72px;height:72px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:2.2rem;box-shadow:var(--glow)}
.wlc-title{font-size:2.2rem;font-weight:900;letter-spacing:-.02em}.wlc-title span{color:var(--accent)}
.wlc-sub-label{font-size:.88rem;color:var(--accent2);font-weight:600}
.wlc-tag{font-size:.73rem;color:var(--muted);background:var(--surface2);border:1px solid var(--border);padding:.25rem .75rem;border-radius:20px;display:inline-block}
.wlc-desc{color:var(--muted);max-width:480px;line-height:1.7;font-size:.93rem}
.wlc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.55rem;max-width:700px;width:100%}
.wlc-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.8rem 1rem;cursor:pointer;text-align:left;transition:all .18s;font-size:.83rem;line-height:1.5}
.wlc-card:hover{border-color:var(--accent);background:var(--surface2);transform:translateY(-2px);box-shadow:var(--shadow)}
.wlc-icon{font-size:1.2rem;margin-bottom:.35rem}
.wlc-q{font-weight:600;color:var(--text)}
.wlc-domain{font-size:.7rem;color:var(--muted);margin-top:.15rem}
.wlc-features{display:flex;gap:.75rem;flex-wrap:wrap;justify-content:center;font-size:.74rem;color:var(--muted)}
.wlc-feat::before{content:"* ";color:var(--accent)}
#inputBar{padding:.85rem 1.5rem 1.1rem;border-top:1px solid var(--border);background:var(--surface);flex-shrink:0}
.input-wrap{display:flex;gap:.6rem;align-items:flex-end;background:var(--bg);border:1px solid var(--border);border-radius:16px;padding:.5rem .5rem .5rem 1rem;transition:border-color .15s}
.input-wrap:focus-within{border-color:var(--accent)}
#questionInput{flex:1;background:none;border:none;color:var(--text);font-size:.92rem;resize:none;min-height:26px;max-height:130px;overflow-y:auto;line-height:1.55;font-family:inherit}
#questionInput:focus{outline:none}
#questionInput::placeholder{color:var(--muted)}
#sendBtn{background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;border-radius:12px;color:#fff;width:42px;height:42px;cursor:pointer;font-size:1.1rem;flex-shrink:0;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(124,111,255,.4);transition:opacity .15s,transform .1s}
#sendBtn:hover{opacity:.9;transform:scale(1.05)}
#sendBtn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.input-meta{display:flex;justify-content:space-between;align-items:center;padding:.35rem .25rem 0;font-size:.72rem;color:var(--muted)}
#autoLabel{display:flex;align-items:center;gap:.3rem;cursor:pointer;user-select:none}
#autoLabel input{accent-color:var(--accent)}
#codeInfo{color:var(--accent);font-weight:600}
#exportModal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:300;align-items:center;justify-content:center}
#exportModal.open{display:flex}
#exportBox{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:1.75rem;width:90%;max-width:420px;box-shadow:var(--shadow)}
#exportBox h3{font-size:1rem;font-weight:700;margin-bottom:.5rem}
#exportBox p{font-size:.83rem;color:var(--muted);margin-bottom:1rem}
.exp-btns{display:flex;gap:.55rem;flex-wrap:wrap}
#toast{position:fixed;bottom:5.5rem;right:1.5rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:.6rem 1rem;font-size:.82rem;z-index:400;opacity:0;transform:translateY(8px);transition:opacity .22s,transform .22s;pointer-events:none;box-shadow:var(--shadow)}
#toast.show{opacity:1;transform:translateY(0)}
#toast.ok{border-color:var(--success);color:var(--success)}
#toast.err{border-color:var(--error);color:var(--error)}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
@media(max-width:768px){#sidebar{position:fixed;top:0;left:0;height:100%;z-index:100;box-shadow:var(--shadow);transition:transform .25s}#sidebar.closed{transform:translateX(-100%);width:280px;min-width:280px}.wlc-grid{grid-template-columns:1fr 1fr}#messages{padding:1rem .75rem}#inputBar{padding:.65rem .75rem .9rem}}
@media(max-width:480px){.wlc-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<aside id="sidebar"><div id="sidebar-inner">
  <div class="sb-brand">
    <div class="sb-logo">&#9878;</div>
    <div><div class="sb-title"><span>Ka</span>zia</div><div class="sb-sub">Assistant Juridique IA</div></div>
    <button class="icon-btn" id="themeToggle" style="margin-left:auto"></button>
  </div>
  <div class="sb-tabs">
    <div class="sb-tab active" data-tab="config">Config</div>
    <div class="sb-tab" data-tab="history">Historique</div>
    <div class="sb-tab" data-tab="about">A propos</div>
  </div>
  <div class="sb-panel active" id="panel-config">
    <div>
      <label class="sb-label">Codes juridiques</label>
      <div id="codeList"><span style="font-size:.8rem;color:var(--muted)">Chargement...</span></div>
      <div class="cc-hint">Vert = indexe &nbsp; Rouge = non indexe</div>
    </div>
    <div>
      <label class="sb-label">Mode de reponse</label>
      <div class="mode-row">
        <button class="mode-btn active" data-mode="citoyen">Citoyen</button>
        <button class="mode-btn" data-mode="avocat">Avocat</button>
      </div>
    </div>
    <div>
      <label class="sb-label">Sources : <span id="topKVal">5</span></label>
      <div class="slider-row"><input type="range" id="topKSlider" min="3" max="15" value="5"/></div>
    </div>
    <div><label class="sb-label">Statut LLM</label><span id="statusPill">...</span></div>
    <hr class="sep"/>
    <button class="btn ghost" id="clearBtn">Nouvelle conversation</button>
    <button class="btn ghost" id="exportBtn">Exporter</button>
  </div>
  <div class="sb-panel" id="panel-history">
    <div id="histList"><span style="font-size:.82rem;color:var(--muted)">Aucun historique.</span></div>
    <button class="btn ghost" id="clearHistBtn" style="margin-top:auto">Effacer l'historique</button>
  </div>
  <div class="sb-panel" id="panel-about">
    <div style="text-align:center;padding:.5rem 0">
      <div style="width:52px;height:52px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.6rem;margin:0 auto .75rem">&#9878;</div>
      <div style="font-size:1.1rem;font-weight:900"><span style="color:var(--accent)">Ka</span>zia</div>
      <div style="font-size:.75rem;color:var(--muted);margin-top:.15rem">v2.0 - Assistant Juridique IA</div>
    </div>
    <div style="font-size:.8rem;line-height:1.8;color:var(--muted)">
      <p><strong style="color:var(--text)">Kazia</strong> rend le droit francais accessible a tous.</p><br/>
      <p><strong style="color:var(--text)">Technologie</strong><br/>Moteur RAG (FAISS) + Google Gemini 2.5 Flash.</p><br/>
      <p><strong style="color:var(--text)">Sources</strong><br/>Legifrance - 29 codes juridiques officiels.</p><br/>
      <p><em>Pour des conseils personnalises, consultez un avocat.</em></p>
    </div>
  </div>
  <div class="sb-footer"><strong>Kazia</strong> - Assistant Juridique IA<br/>Sources : Legifrance &middot; LLM : Google Gemini<br/>&copy; 2026 Kazia</div>
</div></aside>
<main id="main">
  <div id="topbar">
    <button id="toggleSidebar">&#9776;</button>
    <div class="topbar-brand">
      <div class="topbar-logo">&#9878;</div>
      <div class="topbar-name"><span>Ka</span>zia</div>
    </div>
    <span class="topbar-badge" id="autoDetectBadge">Detection auto</span>
    <button class="icon-btn" id="newChatBtn">+ Nouvelle conv.</button>
  </div>
  <div id="welcome">
    <div class="wlc-logo">&#9878;</div>
    <div>
      <div class="wlc-title"><span>Ka</span>zia</div>
      <div class="wlc-sub-label">Votre assistant juridique intelligent</div>
    </div>
    <div class="wlc-tag">Google Gemini &middot; 29 codes juridiques &middot; Legifrance</div>
    <p class="wlc-desc">Posez votre question en francais. Kazia detecte automatiquement les codes concernes et repond avec precision.</p>
    <div class="wlc-grid" id="wlcGrid">
      <div class="wlc-card" data-q="Quelles sont les causes de divorce ?"><div class="wlc-icon">&#10084;</div><div class="wlc-q">Quelles sont les causes de divorce ?</div><div class="wlc-domain">Code civil</div></div>
      <div class="wlc-card" data-q="Comment fonctionne le licenciement abusif ?"><div class="wlc-icon">&#128188;</div><div class="wlc-q">Comment fonctionne le licenciement abusif ?</div><div class="wlc-domain">Code du travail</div></div>
      <div class="wlc-card" data-q="Quels sont mes droits en garde a vue ?"><div class="wlc-icon">&#128659;</div><div class="wlc-q">Quels sont mes droits en garde a vue ?</div><div class="wlc-domain">Code de procedure penale</div></div>
      <div class="wlc-card" data-q="Qui herite en l'absence de testament ?"><div class="wlc-icon">&#128220;</div><div class="wlc-q">Qui herite en l'absence de testament ?</div><div class="wlc-domain">Code civil</div></div>
      <div class="wlc-card" data-q="Qu'est-ce que la responsabilite civile ?"><div class="wlc-icon">&#9888;</div><div class="wlc-q">Qu'est-ce que la responsabilite civile ?</div><div class="wlc-domain">Code civil</div></div>
      <div class="wlc-card" data-q="Quelles infractions tombent sous le Code penal ?"><div class="wlc-icon">&#9878;</div><div class="wlc-q">Quelles infractions tombent sous le Code penal ?</div><div class="wlc-domain">Code penal</div></div>
    </div>
    <div class="wlc-features">
      <span class="wlc-feat">Detection auto</span>
      <span class="wlc-feat">Streaming</span>
      <span class="wlc-feat">Sources citees</span>
      <span class="wlc-feat">Modes Citoyen &amp; Avocat</span>
      <span class="wlc-feat">Lois a jour</span>
    </div>
  </div>
  <div id="messages" style="display:none"></div>
  <div id="inputBar">
    <div class="input-wrap">
      <textarea id="questionInput" rows="1" placeholder="Posez votre question juridique..."></textarea>
      <button id="sendBtn">&#9658;</button>
    </div>
    <div class="input-meta">
      <label id="autoLabel"><input type="checkbox" id="autoDetect" checked/> Detection automatique des codes</label>
      <span id="codeInfo"></span>
    </div>
  </div>
</main>
<div id="exportModal"><div id="exportBox">
  <h3>Exporter la conversation</h3>
  <p>Choisissez le format :</p>
  <div class="exp-btns">
    <button class="btn primary" id="exportTxt" style="flex:1">Texte (.txt)</button>
    <button class="btn primary" id="exportMd" style="flex:1">Markdown (.md)</button>
    <button class="btn ghost" id="exportCancel">Annuler</button>
  </div>
</div></div>
<div id="toast"></div>
<script>
'use strict';
var API='',streaming=false,chatHistory=[],mode='citoyen',allCodes=[],sessions=[],activeSession=null;
function qs(s){return document.querySelector(s);}
function qsa(s){return document.querySelectorAll(s);}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function scrollBottom(){var m=qs('#messages');m.scrollTop=m.scrollHeight;}
function toast(msg,type){var el=qs('#toast');el.textContent=msg;el.className='show '+(type==='err'?'err':'ok');clearTimeout(el._t);el._t=setTimeout(function(){el.className='';},2800);}
window.addEventListener('error',function(){streaming=false;var sb=qs('#sendBtn');if(sb)sb.disabled=false;});
if(typeof marked!=='undefined')marked.setOptions({breaks:false,gfm:true});
function applyTheme(t){document.documentElement.setAttribute('data-theme',t);qs('#themeToggle').textContent=t==='dark'?'Clair':'Sombre';localStorage.setItem('kazia_theme',t);}
applyTheme(localStorage.getItem('kazia_theme')||'dark');
qs('#themeToggle').addEventListener('click',function(){applyTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark');});
qs('#toggleSidebar').addEventListener('click',function(){qs('#sidebar').classList.toggle('closed');});
qsa('.sb-tab').forEach(function(tab){tab.addEventListener('click',function(){qsa('.sb-tab').forEach(function(t){t.classList.remove('active');});qsa('.sb-panel').forEach(function(p){p.classList.remove('active');});tab.classList.add('active');qs('#panel-'+tab.dataset.tab).classList.add('active');});});
qsa('.mode-btn').forEach(function(btn){btn.addEventListener('click',function(){qsa('.mode-btn').forEach(function(b){b.classList.remove('active');});btn.classList.add('active');mode=btn.dataset.mode;});});
qs('#topKSlider').addEventListener('input',function(e){qs('#topKVal').textContent=e.target.value;});
function getSelected(){return Array.from(qsa('#codeList input:checked')).map(function(e){return e.dataset.code;});}
function renderCodes(){
  var c=qs('#codeList');c.innerHTML='';
  allCodes.forEach(function(code){
    var label=document.createElement('label');label.className='cc';
    label.innerHTML='<input type="checkbox" data-code="'+esc(code.name)+'" '+(code.indexed?'':'disabled')+'/>'+
      '<span class="dot '+(code.indexed?'ok':'nok')+'"></span><span>'+esc(code.name)+'</span>';
    c.appendChild(label);
  });
  var civil=qs('#codeList input[data-code="Code civil"]');
  if(civil&&!civil.disabled)civil.checked=true;
  c.querySelectorAll('input').forEach(function(cb){cb.addEventListener('change',updateCodeInfo);});
  updateCodeInfo();
}
function updateCodeInfo(){var sel=getSelected();qs('#codeInfo').textContent=sel.length>1?sel.length+' codes':(sel[0]||'');}
async function loadCodes(){try{var res=await fetch(API+'/api/codes');allCodes=await res.json();renderCodes();}catch(e){var cl=qs('#codeList');cl.innerHTML='<span style="font-size:.78rem;color:var(--error)">Serveur inaccessible. <button onclick="loadCodes()" style="color:var(--accent);background:none;border:none;cursor:pointer;font-size:.78rem;">Reessayer</button></span>';}}
async function checkStatus(){
  try{
    var res=await fetch(API+'/api/status');var data=await res.json();var pill=qs('#statusPill');
    if(data.llm==='gemini_ok'){pill.innerHTML='&#9679; Gemini pret';pill.className='ok';}
    else{pill.innerHTML='&#9679; Cle API absente';pill.className='err';}
  }catch{qs('#statusPill').innerHTML='&#9679; Hors ligne';qs('#statusPill').className='err';}
}
async function detectCodes(q){
  try{
    var res=await fetch(API+'/api/detect-codes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
    var data=await res.json();
    return data.codes.filter(function(c){return c.indexed;}).map(function(c){return c.code;});
  }catch{return null;}
}
function saveSessions(){localStorage.setItem('kazia_sessions',JSON.stringify(sessions.slice(0,50)));}
function loadSessions(){try{sessions=JSON.parse(localStorage.getItem('kazia_sessions')||'[]');if(!Array.isArray(sessions))sessions=[];}catch{sessions=[];}try{renderHist();}catch(e){sessions=[];localStorage.removeItem('kazia_sessions');renderHist();}}
function renderHist(){
  var el=qs('#histList');
  if(!sessions.length){el.innerHTML='<span style="font-size:.82rem;color:var(--muted)">Aucun historique.</span>';return;}
  el.innerHTML='';
  sessions.forEach(function(s,i){
    var hist=Array.isArray(s.history)?s.history:[];
    var d=document.createElement('div');d.className='hist-item';
    d.innerHTML='<div class="hi-title">'+esc(s.title||'Sans titre')+'</div><div class="hi-meta">'+esc(s.date||'')+(hist.length?' - '+Math.floor(hist.length/2)+' echange(s)':'')+'</div>';
    d.addEventListener('click',function(){loadSession(i);});
    el.appendChild(d);
  });
}
function mkSession(q){var s={id:Date.now()+'',title:q.slice(0,60),date:new Date().toLocaleDateString('fr-FR'),history:[],messages:[]};sessions.unshift(s);activeSession=s.id;return s;}
function curSession(){return sessions.find(function(s){return s.id===activeSession;})||null;}
function loadSession(i){
  var s=sessions[i];if(!s)return;
  activeSession=s.id;chatHistory=(s.history||[]).slice();
  qs('#messages').innerHTML='';showMessages();
  (s.messages||[]).forEach(function(m){
    if(m.role==='user'){appendMsg('user',m.content);}
    else{var w=appendMsg('assistant','');var b=w.querySelector('.bubble');if(typeof marked!=='undefined')b.innerHTML=marked.parse(m.content);else b.textContent=m.content;}
  });
  toast('Session chargee');
  if(window.innerWidth<=768)qs('#sidebar').classList.add('closed');
}
qs('#clearHistBtn').addEventListener('click',function(){sessions=[];activeSession=null;saveSessions();renderHist();toast('Historique efface');});
function showMessages(){qs('#welcome').style.display='none';qs('#messages').style.display='flex';qs('#messages').style.flexDirection='column';}
function showWelcome(){qs('#welcome').style.display='';qs('#messages').style.display='none';qs('#messages').innerHTML='';}
function clearConv(){chatHistory=[];activeSession=null;showWelcome();qs('#autoDetectBadge').classList.remove('active');toast('Nouvelle conversation prete');}
qs('#clearBtn').addEventListener('click',clearConv);
qs('#newChatBtn').addEventListener('click',clearConv);
qs('#wlcGrid').addEventListener('click',function(e){var card=e.target.closest('.wlc-card');if(card){qs('#questionInput').value=card.dataset.q;send();}});
qs('#sendBtn').addEventListener('click',send);
qs('#questionInput').addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
async function send(){
  var q=qs('#questionInput').value.trim();if(!q||streaming)return;
  streaming=true;qs('#sendBtn').disabled=true;
  var codes=getSelected();
  if(qs('#autoDetect').checked){
    var detected=await detectCodes(q);
    if(detected&&detected.length){
      codes=detected;
      qsa('#codeList input[type=checkbox]').forEach(function(cb){cb.checked=codes.indexOf(cb.dataset.code)>=0;});
      updateCodeInfo();qs('#autoDetectBadge').classList.add('active');
    }else{qs('#autoDetectBadge').classList.remove('active');}
  }else{qs('#autoDetectBadge').classList.remove('active');}
  if(!codes.length){streaming=false;qs('#sendBtn').disabled=false;toast('Selectionnez au moins un code','err');return;}
  qs('#questionInput').value='';
  if(!activeSession)mkSession(q);
  showMessages();appendMsg('user',q);
  var wrapper=appendMsg('assistant','');
  var bubble=wrapper.querySelector('.bubble');
  bubble.innerHTML='<div class="thinking"><span></span><span></span><span></span></div>';
  var fullText='',sourcesHtml='',timing=null;
  var topK=parseInt(qs('#topKSlider').value);
  var multi=codes.length>1;
  var url=multi?'/api/ask-multi':'/api/ask';
  var body=multi?{question:q,codes:codes,top_k:topK,history:chatHistory.slice(-10),mode:mode}:{question:q,code:codes[0],top_k:topK,history:chatHistory.slice(-10)};
  var ac=new AbortController();
  var watchdog=setTimeout(function(){ac.abort();},90000);
  try{
    var res=await fetch(API+url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:ac.signal});
    if(!res.ok){var err=await res.json().catch(function(){return{detail:res.statusText};});bubble.innerHTML='<span style="color:var(--error)">Erreur : '+esc(err.detail||'Erreur serveur')+'</span>';return;}
    var reader=res.body.getReader(),dec=new TextDecoder(),buf='';
    while(true){
      var chunk=await reader.read();if(chunk.done)break;
      buf+=dec.decode(chunk.value,{stream:true});
      var lines=buf.split('\\n');buf=lines.pop();
      for(var li=0;li<lines.length;li++){
        var line=lines[li];if(!line.startsWith('data: '))continue;
        var pay=JSON.parse(line.slice(6));
        if(pay.type==='sources'){sourcesHtml=buildSourcesHtml(pay.data);}
        else if(pay.type==='token'){if(!fullText)bubble.textContent='';fullText+=pay.text;bubble.textContent=fullText;scrollBottom();}
        else if(pay.type==='timing'){timing=pay;}
        else if(pay.type==='error'){bubble.innerHTML='<span style="color:var(--error)">Erreur : '+esc(pay.text)+'</span>';}
        else if(pay.type==='done'){
          if(fullText&&typeof marked!=='undefined')bubble.innerHTML=marked.parse(fullText);
          if(fullText){
            chatHistory.push({role:'user',content:q});chatHistory.push({role:'assistant',content:fullText});
            var sess=curSession();
            if(sess){
              if(!Array.isArray(sess.messages))sess.messages=[];
              sess.history=chatHistory.slice();
              sess.messages.push({role:'user',content:q});
              sess.messages.push({role:'assistant',content:fullText});
              saveSessions();renderHist();
            }
          }
          if(sourcesHtml){var sd=document.createElement('div');sd.innerHTML=sourcesHtml;wrapper.appendChild(sd);}
          buildFooter(wrapper,timing,fullText);scrollBottom();
          if(fullText)fetchSugg(q,fullText,codes[0]).then(function(suggs){if(suggs.length)appendSugg(wrapper,suggs);});
        }
      }
    }
  }catch(err){
    if(err&&err.name==='AbortError')bubble.innerHTML='<span style="color:var(--error)">Requete trop longue. Reessayez.</span>';
    else bubble.innerHTML='<span style="color:var(--error)">Erreur reseau : '+esc(err.message)+'</span>';
  }finally{
    clearTimeout(watchdog);
    streaming=false;qs('#sendBtn').disabled=false;qs('#questionInput').focus();
  }
}
function appendMsg(role,text){
  var msgs=qs('#messages'),w=document.createElement('div');w.className='msg '+role;
  var b=document.createElement('div');b.className='bubble';b.textContent=text;
  w.appendChild(b);msgs.appendChild(w);scrollBottom();return w;
}
function buildFooter(wrap,timing,fullText){
  var foot=document.createElement('div');foot.className='msg-footer';
  var span=document.createElement('span');span.className='msg-time';span.textContent=new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});foot.appendChild(span);
  if(timing){
    [[''+(timing.total_ms/1000).toFixed(1)+'s',true],['Recherche '+timing.retrieval_ms+'ms',false],[timing.tokens+' tokens',false]].forEach(function(c){var ch=document.createElement('span');ch.className='t-chip'+(c[1]?' hi':'');ch.textContent=c[0];foot.appendChild(ch);});
  }
  if(fullText){var ft=fullText,cp=document.createElement('button');cp.className='act-btn';cp.textContent='Copier';cp.addEventListener('click',function(){navigator.clipboard.writeText(ft).then(function(){toast('Copie !');});});foot.appendChild(cp);}
  wrap.appendChild(foot);
}
function buildSourcesHtml(sources){
  if(!sources||!sources.length)return '';
  var id='src-'+Date.now();
  var cards=sources.map(function(s){
    var title=s.source_file.replace(/^\\d+__/,'').replace(/__Code_[^.]+\\.pdf$/,'').replace(/__/g,' ').replace(/_/g,' ').replace(/\\.pdf$/,'');
    return '<div class="src-card">'+(s.code?'<div class="src-code">'+esc(s.code)+'</div>':'')+
      '<div class="src-title">'+esc(title)+'</div><div class="src-score">Pertinence : '+esc(s.pertinence)+'</div>'+
      '<div class="src-text">'+esc(s.text)+'</div></div>';
  }).join('');
  return '<button class="src-toggle" onclick=\\"toggleSrc(\\\''+id+'\\\')\\">'+ sources.length+' article(s) &#9658; <span id=\\"arr-'+id+'\\">&#9658;</span></button>'+
    '<div id=\\"'+id+'\\" class=\\"src-list\\">'+cards+'</div>';
}
function toggleSrc(id){var el=document.getElementById(id),arr=document.getElementById('arr-'+id);el.classList.toggle('open');if(arr)arr.innerHTML=el.classList.contains('open')?'&#9660;':'&#9658;';}
async function fetchSugg(q,a,code){try{var res=await fetch(API+'/api/suggestions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,answer:a,code:code})});var d=await res.json();return d.suggestions||[];}catch{return [];}}
function appendSugg(wrap,suggs){var row=document.createElement('div');row.className='sugg-row';suggs.forEach(function(s){var chip=document.createElement('span');chip.className='sugg-chip';chip.textContent=s;chip.addEventListener('click',function(){qs('#questionInput').value=s;send();});row.appendChild(chip);});wrap.appendChild(row);scrollBottom();}
qs('#exportBtn').addEventListener('click',function(){if(!chatHistory.length){toast('Aucune conversation','err');return;}qs('#exportModal').classList.add('open');});
qs('#exportCancel').addEventListener('click',function(){qs('#exportModal').classList.remove('open');});
function dlText(name,content,type){var b=new Blob([content],{type:type}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=name;a.click();URL.revokeObjectURL(u);qs('#exportModal').classList.remove('open');toast('Export telecharge');}
qs('#exportTxt').addEventListener('click',function(){var lines=['KAZIA - Assistant Juridique IA','Export du '+new Date().toLocaleString('fr-FR'),'---',''];for(var i=0;i<chatHistory.length;i+=2){if(chatHistory[i])lines.push('QUESTION : '+chatHistory[i].content);if(chatHistory[i+1])lines.push('\\nREPONSE :\\n'+chatHistory[i+1].content);lines.push('---');}dlText('kazia_'+Date.now()+'.txt',lines.join('\\n'),'text/plain');});
qs('#exportMd').addEventListener('click',function(){var lines=['# Kazia',''];for(var i=0;i<chatHistory.length;i+=2){if(chatHistory[i])lines.push('## '+chatHistory[i].content,'');if(chatHistory[i+1])lines.push(chatHistory[i+1].content,'');lines.push('---','');}dlText('kazia_'+Date.now()+'.md',lines.join('\\n'),'text/markdown');});
loadSessions();
Promise.all([loadCodes(),checkStatus()]);
</script>
</body>
</html>"""

path = r'c:\Users\HOME\Desktop\Nouveau dossier (9)\assistant justice ia\static\index.html'
with open(path, 'wb') as f:
    f.write(HTML)

with open(path, 'rb') as f:
    raw = f.read()
print('BOM:', raw[:3] == b'\xef\xbb\xbf')
print('Size:', len(raw), 'bytes')
t = raw.decode('utf-8')
print('Lines:', t.count('\n'))
print('Corrupted:', chr(0xC3) in t and chr(0x83) in t)
print('Done')
