const state={providers:[],last:null,currentJob:null};
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];

function esc(v){return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function switchView(name){$$('.view').forEach(x=>x.classList.add('hidden'));$$('.nav-item[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===name));$(`#${name}View`).classList.remove('hidden');if(name==='history')renderHistory()}
function sleep(ms){return new Promise(resolve=>setTimeout(resolve,ms))}
function statusLabel(status){return ({queued:'aguardando',running:'buscando',completed:'concluído',empty:'sem resultados',completed_no_candidates_parsed:'sem candidatos',unavailable:'indisponível',failed:'falhou',skipped:'ignorada'})[status]||status||'aguardando'}
function badgeClass(status){return ['failed','unavailable'].includes(status)?'failed':''}

async function init(){
  $$('.nav-item[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  $('#refreshHistory').onclick=renderHistory;
  try{const [health,providers]=await Promise.all([fetch('/api/health').then(r=>r.json()),fetch('/api/providers').then(r=>r.json())]);$('#health').textContent=health.status==='ok'?'engine conectado':'engine indisponível';$('#health').classList.add(health.status==='ok'?'ok':'bad');state.providers=providers.providers||[];renderProviders()}catch(e){$('#health').textContent='engine indisponível';$('#health').classList.add('bad');$('#searchBtn').disabled=true}
  $('#searchBtn').onclick=runSearch;
  const params=new URLSearchParams(location.search);if(params.get('q')){$('#question').value=params.get('q');runSearch()}
}
function renderProviders(){const root=$('#providerGrid');root.innerHTML=state.providers.map(p=>`<label class="provider-chip"><input type="checkbox" value="${esc(p.id)}" checked> ${esc(p.label)}</label>`).join('');$('#searchHint').textContent=`${state.providers.length} fontes conectadas no modo web`}
function selectedProviders(){return $$('#providerGrid input:checked').map(x=>x.value)}

async function runSearch(){
  const query=$('#question').value.trim();if(!query)return alert('Digite uma pergunta de busca.');
  const providers=selectedProviders();if(!providers.length)return alert('Selecione pelo menos uma fonte.');
  const btn=$('#searchBtn');btn.disabled=true;state.currentJob=null;$('#summary').classList.add('hidden');$('#results').innerHTML='';
  $('#searchState').className='loading';$('#searchState').textContent='Iniciando busca…';
  try{
    const res=await fetch('/api/search/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,providers,per_provider:Number($('#perProvider').value||25),max_results:Number($('#maxResults').value||100)})});
    const job=await res.json();if(!res.ok)throw new Error(job.message||job.error||'Falha ao iniciar busca');
    state.currentJob=job.job_id;renderJob(job);await pollSearchJob(job.job_id);
  }catch(e){$('#searchState').className='error';$('#searchState').textContent=`Falha na busca: ${e.message}`}
  finally{btn.disabled=false;state.currentJob=null}
}

async function pollSearchJob(jobId){
  while(state.currentJob===jobId){
    const res=await fetch(`/api/search/jobs/${encodeURIComponent(jobId)}`,{cache:'no-store'});const job=await res.json();
    if(!res.ok)throw new Error(job.message||job.error||'Job de busca não encontrado');
    renderJob(job);
    if(job.status==='completed'){
      if(!job.result)throw new Error('Busca concluída sem resultado persistido');
      state.last=job.result;renderSearch(job.result);return;
    }
    if(job.status==='failed')throw new Error(job.error||'A busca falhou');
    await sleep(700);
  }
}

function renderJob(job){
  const completed=Number(job.completed_providers||0),total=Number(job.total_providers||0);
  const stage=job.stage==='finalizing'?'Deduplicando e priorizando referências…':job.stage==='persisting'?'Salvando resultado…':`Consultando fontes: ${completed}/${total}`;
  $('#searchState').className='loading';
  $('#searchState').innerHTML=`<div><strong>${esc(stage)}</strong></div><div class="provider-status">${(job.providers||[]).map(p=>`<span class="provider-badge ${badgeClass(p.status)}" title="${esc(p.error||'')}">${esc(p.label)} · ${esc(statusLabel(p.status))}${['queued','running'].includes(p.status)?'':` · ${Number(p.returned||0)}`}</span>`).join('')}</div>`;
}

function renderSearch(data){$('#searchState').className='hidden';const gaps=(data.failed_providers||[]).length+(data.unavailable_providers||[]).length;$('#summary').classList.remove('hidden');$('#summary').innerHTML=`<div class="summary-grid"><div class="kpi"><strong>${data.unique_records}</strong><span>referências únicas</span></div><div class="kpi"><strong>${data.records_before_dedup}</strong><span>antes da deduplicação</span></div><div class="kpi"><strong>${data.returned_records}</strong><span>exibidas</span></div><div class="kpi"><strong>${gaps}</strong><span>fontes indisponíveis/falhas</span></div></div><div class="provider-status">${(data.providers||[]).map(p=>`<span class="provider-badge ${badgeClass(p.status)}" title="${esc(p.error||'')}">${esc(p.label)} · ${esc(statusLabel(p.status))} · ${p.returned}</span>`).join('')}</div><div class="warning">${esc(data.ranking_warning)} ${(data.interactive_limitations||[]).map(esc).join(' ')}</div>`;$('#results').innerHTML=(data.results||[]).map(resultCard).join('')||'<div class="card">Nenhuma referência foi recuperada pelas fontes selecionadas.</div>'}
function resultCard(r){const href=r.doi?`https://doi.org/${String(r.doi).replace(/^https?:\/\/doi\.org\//i,'').replace(/^doi:/i,'')}`:(r.url||'');const id=r.pmid?`PMID ${r.pmid}`:(r.doi?`DOI ${r.doi}`:'');return `<article class="result-card"><div class="result-top"><div class="rank">${esc(r.reference_rank)}</div><div style="flex:1"><h3>${esc(r.title||'(sem título)')}</h3><div class="meta"><span>${esc(r.journal||'—')}</span><span>${esc(r.year||'—')}</span><span>${esc(r.source_provider||r.source||'')}</span><span>${esc(id)}</span></div></div><div class="score"><strong>${Number(r.reference_score||0).toFixed(1)}</strong><span>prioridade</span></div></div>${r.abstract?`<div class="abstract">${esc(r.abstract).slice(0,900)}${String(r.abstract).length>900?'…':''}</div>`:''}${href?`<div class="links"><a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Abrir fonte ↗</a></div>`:''}</article>`}
async function renderHistory(){const root=$('#historyList');root.innerHTML='<p style="color:#667572">Carregando runs do Engine…</p>';try{const res=await fetch('/api/searches?limit=50');const data=await res.json();if(!res.ok)throw new Error(data.message||data.error||'Falha ao carregar histórico');const h=data.searches||[];if(!h.length){root.innerHTML='<p style="color:#667572">Nenhuma busca persistida ainda.</p>';return}root.innerHTML=h.map(x=>`<div class="history-item"><button data-id="${esc(x.search_id)}"><strong>${esc(x.query)}</strong><br><span style="color:#667572;font-size:.78rem">${x.unique_records} únicas · ${x.returned_records} exibidas · ${esc(x.status||'')}</span></button><span class="history-meta">${esc(new Date(x.created_at).toLocaleString('pt-BR'))}</span></div>`).join('');root.querySelectorAll('button[data-id]').forEach(b=>b.onclick=()=>openHistoryRun(b.dataset.id))}catch(e){root.innerHTML=`<p class="error">Falha ao carregar histórico: ${esc(e.message)}</p>`}}
async function openHistoryRun(searchId){try{const res=await fetch(`/api/searches/${encodeURIComponent(searchId)}`);const data=await res.json();if(!res.ok)throw new Error(data.message||data.error||'Busca não encontrada');state.last=data;$('#question').value=data.query||'';switchView('search');renderSearch(data)}catch(e){alert(`Falha ao abrir busca: ${e.message}`)}}
init();
