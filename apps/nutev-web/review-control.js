const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));

async function getJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return response.json()}
async function getJsonl(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return (await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse)}

function gate(label,passed,detail){return `<div class="review-gate ${passed?'pass':'locked'}"><span>${esc(label)}</span><strong>${passed?'PASS':'LOCKED'}</strong><small>${esc(detail)}</small></div>`}

async function init(){
  try{
    const [health,state,articles]=await Promise.all([getJson('/api/health'),getJson('/agent-context/article1/SEARCH_STATE.json'),getJsonl('/agent-context/article1/ARTICLE_SUMMARIES.jsonl')]);
    const formal=state.formal_search||{};
    const b=articles.filter(row=>(row.routes||[]).includes('B-NORM')).length;
    const c=articles.filter(row=>(row.routes||[]).includes('C-STRUCT')).length;
    const routed=articles.filter(row=>(row.routes||[]).length).length;
    $('#reviewHealth').textContent=health.status==='ok'?'engine conectado':'engine parcial';$('#reviewHealth').className=`status-pill ${health.status==='ok'?'ok':'bad'}`;
    $('#reviewKpis').innerHTML=[['Calibration corpus',articles.length],['Routed for reading',routed],['B-NORM',b],['C-STRUCT',c]].map(([label,value])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="metric-value">${fmt(value)}</strong></article>`).join('');
    $('#calibrationStatus').innerHTML=`<div class="calibration-card"><strong>AVAILABLE</strong><p>${fmt(articles.length)} documentos Tier A podem ser explorados em filas rank-blind para leitura, calibração de taxonomia e desenvolvimento da estratégia.</p><div class="detail-chips"><span class="mini-pill">navigation only</span><span class="mini-pill">no eligibility decision</span><span class="mini-pill">no PRISMA event</span></div></div>`;
    const press=String(formal.press_status||'').toUpperCase().includes('PASS');
    const gf10=formal.gf10_authorized===true;
    const freeze=formal.query_freeze_complete===true;
    const formalSearch=formal.formal_provider_search_executed===true;
    const prismaSearch=formal.prisma_search_event_emitted===true;
    $('#screeningGates').innerHTML=[gate('PRESS',press,formal.press_status||'PRESS review pending'),gate('GF-10',gf10,'formal gate authorization'),gate('Query freeze',freeze,'exact/versioned provider strings'),gate('Formal provider search',formalSearch,'required formal corpus'),gate('Formal search event',prismaSearch,'explicit scientific event only')].join('');
    const ready=press&&gf10&&freeze&&formalSearch;
    $('#formalReviewLabel').textContent=ready?'Formal corpus exists; reviewer-level article UI still unavailable':'Formal article screening locked';
    $('#formalReviewReason').textContent=ready?'The current NutEV article-screening contract still imports resolved final decisions and does not implement reviewer-level blinded assessments/conflict adjudication UI.':'Article 1 remains before the formal-search gate. Current Tier A route queues are calibration/navigation artifacts, not a formal screening set.';
    $('#reviewState').className='hidden';$('#reviewContent').classList.remove('hidden');
  }catch(error){$('#reviewState').className='error';$('#reviewState').innerHTML=`<strong>Review Control Center indisponível.</strong><div>${esc(error.message)}</div><div class="small-state">Nenhuma decisão é habilitada quando o estado canônico não pode ser verificado.</div>`;$('#reviewHealth').textContent='estado indisponível';$('#reviewHealth').className='status-pill bad'}
}
init();