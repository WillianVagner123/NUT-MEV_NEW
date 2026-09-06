import{canonicalSavedKey,saveArticle,saveArticles,savedKeySet}from'./saved-library.js';

const nativeFetch=window.fetch.bind(window);
let latestSearch=null;
let enhanceToken=0;

function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function requestPath(input){try{return new URL(typeof input==='string'?input:input?.url||'',location.href).pathname}catch{return''}}
function searchContext(data){return{search_id:data?.search_id||'',query:data?.query||'',search_mode:data?.search_mode||''}}
function resultForKey(key){return(latestSearch?.results||[]).find(item=>canonicalSavedKey(item)===key)||null}

function capturePayload(payload){
  const result=payload?.result?.results?payload.result:(payload?.results?payload:null);
  if(!result)return;
  latestSearch=result;
  queueMicrotask(enhance);
}

window.fetch=async(...args)=>{
  const response=await nativeFetch(...args);
  const path=requestPath(args[0]);
  if(response.ok&&(path==='/api/search'||path.startsWith('/api/search/jobs/')||path.startsWith('/api/searches/'))){
    response.clone().json().then(capturePayload).catch(()=>{});
  }
  return response;
};

async function markSavedButtons(){
  const buttons=[...document.querySelectorAll('[data-save-library-key]')];
  if(!buttons.length)return;
  const keys=buttons.map(button=>button.dataset.saveLibraryKey);
  try{
    const saved=await savedKeySet(keys);
    for(const button of buttons){
      const isSaved=saved.has(button.dataset.saveLibraryKey);
      button.textContent=isSaved?'Guardado ✓':'Guardar na Biblioteca';
      button.classList.toggle('saved',isSaved);
      button.setAttribute('aria-pressed',String(isSaved));
    }
  }catch{
    for(const button of buttons){button.title='Biblioteca local indisponível neste navegador.'}
  }
}

async function saveKey(key,{openDossier=false}={}){
  const record=resultForKey(key);if(!record)return;
  const buttons=[...document.querySelectorAll('[data-save-library-key]')].filter(button=>button.dataset.saveLibraryKey===key);
  buttons.forEach(button=>{button.disabled=true;button.textContent='Guardando…'});
  try{
    await saveArticle(record,searchContext(latestSearch));
    buttons.forEach(button=>{button.textContent='Guardado ✓';button.classList.add('saved');button.setAttribute('aria-pressed','true')});
    if(openDossier)location.href=`/articles.html?saved=${encodeURIComponent(key)}`;
  }catch(error){
    buttons.forEach(button=>{button.textContent='Tentar guardar novamente';button.title=error.message||'Falha ao guardar'});
  }finally{buttons.forEach(button=>{button.disabled=false})}
}

async function saveAll(){
  const button=document.querySelector('#saveAllSearchResults');
  const results=latestSearch?.results||[];if(!button||!results.length)return;
  button.disabled=true;button.textContent=`Guardando ${results.length.toLocaleString('pt-BR')}…`;
  try{
    const outcome=await saveArticles(results,searchContext(latestSearch));
    button.textContent=`Biblioteca atualizada · ${outcome.total.toLocaleString('pt-BR')}`;
    await markSavedButtons();
  }catch(error){button.textContent='Falha ao guardar resultados';button.title=error.message||''}
  finally{button.disabled=false}
}

function ensureSummaryActions(){
  const summary=document.querySelector('#summary');if(!summary||summary.classList.contains('hidden')||!latestSearch?.results?.length)return;
  if(summary.querySelector('.search-library-bar'))return;
  const bar=document.createElement('div');bar.className='search-library-bar';
  bar.innerHTML=`<div><strong>Biblioteca</strong><span>Guarde os resultados retornados no CORE local sem alterar o corpus científico verificado.</span></div><div class="search-library-buttons"><button class="ghost" type="button" id="saveAllSearchResults">Guardar todos os resultados retornados</button><a href="/articles.html">Abrir Biblioteca →</a></div>`;
  summary.appendChild(bar);
  bar.querySelector('#saveAllSearchResults').addEventListener('click',saveAll);
}

function ensureCardActions(){
  const cards=[...document.querySelectorAll('#results .result-card')];
  const results=latestSearch?.results||[];
  cards.forEach((card,index)=>{
    const record=results[index];if(!record)return;
    const key=canonicalSavedKey(record);
    const existing=card.querySelector('.saved-library-actions');
    if(existing?.dataset.savedLibraryKey===key)return;
    existing?.remove();
    let links=card.querySelector('.links');
    if(!links){links=document.createElement('div');links.className='links';card.appendChild(links)}
    const actions=document.createElement('span');actions.className='saved-library-actions';actions.dataset.savedLibraryKey=key;
    actions.innerHTML=`<button class="ghost" type="button" data-save-library-key="${esc(key)}" aria-pressed="false">Guardar na Biblioteca</button><button class="ghost" type="button" data-open-saved-key="${esc(key)}">Abrir dossiê</button>`;
    links.prepend(actions);
    actions.querySelector('[data-save-library-key]').addEventListener('click',event=>saveKey(event.currentTarget.dataset.saveLibraryKey));
    actions.querySelector('[data-open-saved-key]').addEventListener('click',event=>saveKey(event.currentTarget.dataset.openSavedKey,{openDossier:true}));
  });
}

async function enhance(){
  const token=++enhanceToken;if(!latestSearch)return;
  ensureSummaryActions();ensureCardActions();
  await markSavedButtons();
  if(token!==enhanceToken)return;
}

const observer=new MutationObserver(()=>queueMicrotask(enhance));
observer.observe(document.documentElement,{subtree:true,childList:true});
window.addEventListener('pageshow',()=>queueMicrotask(enhance));
