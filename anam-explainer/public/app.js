// app.js — MutationScientist avatar, client-side bring-your-own-LLM.
//
// The avatar (llmId "CUSTOMER_CLIENT_V1") speaks tokens WE stream from our fine-tuned model via
// /api/chat-stream. Every turn can carry a `contextKey` so the model is grounded in the selected
// mutation x inhibitor pack (real measurements + Boltz prediction + cited evidence). No API key is
// ever in the browser.
import { createClient, AnamEvent } from "https://esm.sh/@anam-ai/js-sdk@latest";

const GREETING =
  "Hi, I'm Dr. Mutasci. Pick one of the mutation and inhibitor pairs, or just ask me a question about " +
  "EGFR drug resistance - and I'll answer from our fine-tuned model, grounded in the real data.";

const $ = (id) => document.getElementById(id);
const startBtn=$("startBtn"), stopBtn=$("stopBtn"), pitchBtn=$("pitchBtn"), askBtn=$("askBtn");
const askInput=$("askInput"), overlay=$("overlay"), statusEl=$("status"), speakingEl=$("speaking"),
      answerEl=$("answer"), heroesEl=$("heroes"), cardEl=$("card"), modelFoot=$("modelFoot");

let anamClient=null, currentAbort=null, currentStream=null;
let activeContextKey=null, contexts=[], live=false, pitchRunning=false;
let personaTurnResolvers=[];

const setStatus=(m)=>{ statusEl.textContent=m; };
const showSpeaking=(on)=>{ speakingEl.style.display=on?"flex":"none"; };

// ---------- load hero packs + model label ----------
async function loadMeta(){
  try{
    const [c,h]=await Promise.all([
      fetch("/api/contexts").then(r=>r.json()),
      fetch("/api/health").then(r=>r.json()),
    ]);
    contexts=c.contexts||[];
    modelFoot.textContent="model: "+(h.resolvedModel||h.model?.detail||"unknown");
    renderHeroes();
  }catch(e){ heroesEl.innerHTML=`<div style="color:var(--bad)">Could not load demos: ${e.message}</div>`; }
}
function renderHeroes(){
  heroesEl.innerHTML="";
  for(const p of contexts){
    const el=document.createElement("button");
    el.className="hero"; el.dataset.key=p.key;
    const tag = p.card?.has_real_prediction ? "has a real Boltz prediction" : "covalent — no prediction, evidence-led";
    el.innerHTML=`<div class="t">${p.title}</div><div class="d">${p.card?.mutation} × ${p.card?.compound} · ${tag}</div>`;
    el.addEventListener("click",()=>selectHero(p.key));
    heroesEl.appendChild(el);
  }
}

// ---------- prediction card ----------
function log10uMtoNM(v){ return Math.pow(10, v+3); } // affinity_pred_value = log10(IC50_nM) - 3
function fmtNM(nm){ return nm>=1000 ? (nm/1000).toFixed(2)+" µM" : nm.toFixed(nm<10?1:0)+" nM"; }

function renderCard(key){
  const p=contexts.find(x=>x.key===key); if(!p){cardEl.style.display="none";return;}
  const c=p.card; const cov=(c.covalent||"").toLowerCase().includes("non")?"non":"cov";
  const meas=(c.measurements||[]).map(m=>`${m.relation&&m.relation!=="="?m.relation:""}${m.value} ${m.unit}`).join(" · ");
  let predHtml;
  if(c.has_real_prediction){
    const predNM=fmtNM(log10uMtoNM(c.affinity_pred_value));
    const expNM = c.experimental_affinity_label!=null ? fmtNM(log10uMtoNM(c.experimental_affinity_label)) : "—";
    predHtml=`
      <div class="metrics">
        <div class="metric pred"><div class="k">Boltz-2 predicted</div>
          <div class="v">${c.affinity_pred_value.toFixed(2)} <small>log₁₀µM · ≈${predNM}</small></div></div>
        <div class="metric exp"><div class="k">Experimental label</div>
          <div class="v">${c.experimental_affinity_label?.toFixed(2) ?? "—"} <small>≈${expNM}</small></div></div>
        <div class="metric"><div class="k">Binding probability</div>
          <div class="v">${Math.round((c.affinity_probability_binary||0)*100)}%</div></div>
        <div class="metric"><div class="k">Model confidence</div>
          <div class="v">${(c.confidence_score||0).toFixed(2)}</div></div>
      </div>
      <div class="conv">Measured IC50: ${meas} (${c.measurements?.[0]?.source||"dataset"}). Lower log₁₀ = stronger binding.</div>`;
  }else{
    predHtml=`<div class="nopred">No Boltz-2 prediction — ${c.compound} is <b>covalent</b>, so it has no complex in the
      affinity regression target. The story here is evidence-led.</div>
      <div class="conv">Measured IC50: ${meas} (${c.measurements?.[0]?.source||"dataset"}).</div>`;
  }
  cardEl.innerHTML=`
    <div class="head"><div class="pair">${c.mutation} × ${c.compound}</div>
      <span class="badge ${cov}">${c.covalent||"?"}</span></div>
    <div class="claim">${c.headline_claim||""}</div>
    ${predHtml}`;
  cardEl.style.display="block";
}

function setActiveHero(key){
  activeContextKey=key;
  [...heroesEl.children].forEach(el=>el.classList.toggle("active", el.dataset.key===key));
  renderCard(key);
}

async function selectHero(key){
  setActiveHero(key);
  const p=contexts.find(x=>x.key===key);
  if(!live){ setStatus('Showing the prediction. Click "Start the explainer", then I\'ll talk you through it.'); return; }
  if(pitchRunning) return;
  await askText(p.question, key);
}

// ---------- token helpers ----------
function getSessionToken(){
  return fetch("/api/session-token",{method:"POST"}).then(async r=>{
    if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.detail||e.error||`Token ${r.status}`); }
    const {sessionToken}=await r.json(); if(!sessionToken) throw new Error("no sessionToken"); return sessionToken;
  });
}
function cancelTurn(){
  try{ currentAbort?.abort(); }catch{}
  try{ if(currentStream?.isActive?.()) currentStream.endMessage(); }catch{}
  currentAbort=null; currentStream=null;
}
// Resolve when the persona next finishes a turn (history update whose last msg isn't the user).
function waitForPersonaDone(estWords){
  const est=Math.max(2500, Math.min(30000, (estWords/2.6)*1000+1200));
  return new Promise((resolve)=>{
    let done=false; const fin=()=>{ if(done)return; done=true; resolve(); };
    personaTurnResolvers.push(fin);
    setTimeout(fin, est);
  });
}

// ---------- core: run one grounded model turn, stream to the avatar ----------
async function runModelTurn(messages, contextKey){
  cancelTurn();
  const abort=new AbortController(); currentAbort=abort;
  const talkStream=anamClient.createTalkMessageStream(); currentStream=talkStream;
  setStatus("Thinking…"); answerEl.style.display="block"; answerEl.textContent=""; showSpeaking(true);
  let full="";
  let res;
  try{
    res=await fetch("/api/chat-stream",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({messages,contextKey:contextKey??null}),signal:abort.signal});
  }catch(e){ if(e.name!=="AbortError") setStatus("Model request failed: "+e.message); showSpeaking(false); return ""; }
  if(!res.ok||!res.body){ setStatus("Model request failed ("+res.status+")"); showSpeaking(false); return ""; }

  const reader=res.body.getReader(), dec=new TextDecoder(); let buf="";
  try{
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split("\n"); buf=lines.pop()??"";
      for(const line of lines){
        const s=line.trim(); if(!s) continue;
        let o; try{ o=JSON.parse(s); }catch{ continue; }
        if(o.error){ console.warn("model error:",o.error); continue; }
        if(o.content && talkStream.isActive()){
          await talkStream.streamMessageChunk(o.content,false);
          full+=o.content; answerEl.textContent=full;
        }
      }
    }
    if(talkStream.isActive()) await talkStream.endMessage();
    setStatus("Live. Ask a question, pick a pair, or play the pitch.");
  }catch(e){ if(e.name!=="AbortError"){ console.error(e); setStatus("Streaming error: "+e.message); } }
  finally{ if(currentStream===talkStream){ currentStream=null; currentAbort=null; } }
  return full;
}

async function askText(text, contextKey){
  if(!live) return;
  const answer=await runModelTurn([{role:"user",content:text}], contextKey);
  return answer;
}

// ---------- scripted 90-sec pitch ----------
const PITCH=[
  { key:null, q:"In two sentences, introduce yourself and say what this demo shows." },
  { key:"osimertinib_resistance", q:"How does the C797S mutation cause resistance to osimertinib? Use the measured numbers." },
  { key:"blu945_prediction", q:"For BLU-945 against L858R/C797S, what does the Boltz-2 prediction say, and how does it compare to the measured potency?" },
  { key:null, q:"In one sentence, say why grounding the avatar in real predictions and evidence matters." },
];
async function playPitch(){
  if(!live||pitchRunning) return;
  pitchRunning=true; pitchBtn.disabled=true; askBtn.disabled=true;
  setStatus("Playing pitch…");
  try{
    for(const step of PITCH){
      if(!live) break;
      if(step.key){ setActiveHero(step.key); } else { activeContextKey=null; }
      const ans=await askText(step.q, step.key);
      await waitForPersonaDone((ans||"").split(/\s+/).length);
    }
    setStatus("Pitch complete. Ask a follow-up, or pick a pair.");
  } finally { pitchRunning=false; pitchBtn.disabled=!live; askBtn.disabled=!live; }
}

// ---------- lifecycle ----------
async function start(){
  try{
    startBtn.disabled=true; setStatus("Requesting session token…");
    const token=await getSessionToken();
    setStatus("Connecting to avatar…");
    anamClient=createClient(token);

    anamClient.addListener(AnamEvent.MESSAGE_HISTORY_UPDATED,(messages)=>{
      const last=messages?.[messages.length-1];
      if(last && last.role!=="user"){
        // persona finished a turn
        showSpeaking(false);
        const r=personaTurnResolvers; personaTurnResolvers=[]; r.forEach(fn=>fn());
        return;
      }
      if(!last) return;
      if(pitchRunning) return;              // ignore mic during scripted pitch
      runModelTurn(messages, activeContextKey).catch(console.error);
    });
    anamClient.addListener(AnamEvent.TALK_STREAM_INTERRUPTED,()=>{ cancelTurn(); showSpeaking(false); });

    await anamClient.streamToVideoElement("persona-video");
    live=true; overlay.style.display="none";
    stopBtn.disabled=false; pitchBtn.disabled=false; askBtn.disabled=false;
    setStatus("Live. Speak, type a question, pick a pair, or play the pitch.");
    try{ await anamClient.talk(GREETING); }catch(e){ console.warn("greeting failed",e); }
  }catch(e){ console.error(e); setStatus("Error: "+e.message); startBtn.disabled=false; }
}
function stop(){
  live=false; pitchRunning=false; cancelTurn();
  try{ anamClient?.stopStreaming?.(); }catch{}
  anamClient=null; showSpeaking(false);
  stopBtn.disabled=true; pitchBtn.disabled=true; askBtn.disabled=true; startBtn.disabled=false;
  overlay.style.display="flex"; setStatus("Stopped.");
}

startBtn.addEventListener("click",start);
stopBtn.addEventListener("click",stop);
pitchBtn.addEventListener("click",playPitch);
askBtn.addEventListener("click",()=>{ const t=askInput.value.trim(); if(t){ askInput.value=""; askText(t,activeContextKey); } });
askInput.addEventListener("keydown",(e)=>{ if(e.key==="Enter"){ e.preventDefault(); askBtn.click(); } });

loadMeta();
