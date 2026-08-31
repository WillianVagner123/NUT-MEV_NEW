const state={summary:null,articles:[],radar:null,health:null,workbench:null,manifest:null};
const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const pct=(a,b)=>b?`${(100*Number(a||0)/Number(b)).toLocaleString('pt-BR',{maximumFractionDigits:1})}%`:'—';
const classLabels={food_based_dietary_guideline:'Guia alimentar / FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position / scientific statement',framework_model:'Framework / modelo',competency_curriculum:'Competências / currículo',implementation_evaluation:'Implementação / viabilidade',primary_randomized:'Ensaio randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const domainLabels={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social da alimentação',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Medicina do Estilo de Vida',implementation_practice:'Implementação na prática'};
const providerLabels={pubmed:'PubMed',europepmc:'Europe PMC',europe_pmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs:'LILACS / BVS',lilacs_bvs_native:'LILACS / BVS',scielo:'SciELO',scielo_native:'SciELO',scopus:'Scopus',wos:'Web of Science'};

async function fetchJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return response.json()}
async function fetchJsonl(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);const text=await response.text();return text.split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line))}

function countBy(rows,getter){const counts={};for(const row of rows){const key=getter(row);if(!key)continue;counts[key]=(counts[key]||0)+1}return counts}
function sortedEntries(counts,limit=null){const rows=Object.entries(counts||{}).sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0])));return limit?rows.slice(0,limit):rows}
function statusClass(done,pending=false){return done?'done':pending?'pending':'locked'}
function statusText(done,pendingText='PENDING'){return done?'COMPLETE':pendingText}

async function load(){
  $('#dashboardState').className='loading dashboard-state';
  $('#dashboardState').textContent='Carregando estado científico verificado…';
  $('#dashboardContent').classList.add('hidden');
  const requests=await Promise.allSettled([
    fetchJson('/api/health'),
    fetchJson('/api/articles/status'),
    fetchJson('/agent-context/article1/SEARCH_STATE.json'),
    fetchJsonl('/agent-context/article1/ARTICLE_SUMMARIES.jsonl'),
    fetchJson('/agent-context/article1/CONTEXT_MANIFEST.json'),
    fetchJson('/api/radar')
  ]);
  const [health,workbench,summary,articles,manifest,radar]=requests;
  if(health.status==='fulfilled')state.health=health.value;
  if(workbench.status==='fulfilled')state.workbench=workbench.value;
  if(summary.status==='fulfilled')state.summary=summary.value;
  if(articles.status==='fulfilled')state.articles=articles.value;
  if(manifest.status==='fulfilled')state.manifest=manifest.value;
  if(radar.status==='fulfilled')state.radar=radar.value;

  $('#dashboardHealth').textContent=state.health?.status==='ok'?'engine conectado':'engine parcial';
  $('#dashboardHealth').className=`status-pill ${state.health?.status==='ok'?'ok':'bad'}`;

  if(!state.summary && !state.workbench){
    const reasons=requests.filter(item=>item.status==='rejected').map(item=>item.reason?.message).filter(Boolean);
    $('#dashboardState').className='error dashboard-state';
    $('#dashboardState').innerHTML=`<strong>Dashboard ainda sem contexto suficiente.</strong><div>${esc(reasons.join(' · ')||'Workbench e contexto do Artigo 1 indisponíveis.')}</div><div class="small-state">O painel não usa números demonstrativos.</div>`;
    return;
  }
  render();
}

function render(){
  $('#dashboardState').className='hidden';
  $('#dashboardContent').classList.remove('hidden');
  const summary=state.summary||{};
  const runtime=summary.runtime||{};
  const formal=summary.formal_search||{};
  const routeCounts=runtime.article1_routes?.counts||{};
  const deep=runtime.deepening||{};
  const workbench=state.workbench||{};
  const articles=state.articles||[];

  $('#projectQuestion').textContent=summary.question||'Article 1 — contexto científico do NutEV';
  const chips=[
    ['Discovery',String(summary.master_status||'').includes('DISCOVERY_CLOSED')],
    ['Tier A deepening',String(deep.status||'').toUpperCase()==='COMPLETE'],
    ['PRESS',String(formal.press_status||'').toUpperCase().includes('PASS')],
    ['GF-10',formal.gf10_authorized===true]
  ];
  $('#heroStatuses').innerHTML=chips.map(([label,done],index)=>`<span class="state-chip ${done?'done':index<2?'pending':'locked'}">${esc(label)} · ${done?'complete':index<2?'partial':'pending'}</span>`).join('');

  const tierA=articles.length||Number(routeCounts.tier_records||0);
  const fullCounts=countBy(articles,row=>row.full_text_status||'unknown');
  const fullAvailable=(fullCounts.retrieved||0)+(fullCounts.partial||0);
  const routed=articles.length?articles.filter(row=>(row.routes||[]).length).length:Number(routeCounts.route_union_documents||0);
  const kpis=[
    ['Bank',workbench.articles||runtime.workbench?.counts?.articles||0,'artigos indexados'],
    ['Tier A',tierA,'aprofundamento operacional'],
    ['Cobertura full text',articles.length?pct(fullAvailable,tierA):deep.retrieval_status_counts?`${pct((deep.retrieval_status_counts.retrieved||0)+(deep.retrieval_status_counts.partial||0),tierA)}`:'—',articles.length?`${fmt(fullAvailable)} / ${fmt(tierA)}`:'retrieved + partial'],
    ['Roteados',routed,'B-NORM e/ou C-STRUCT'],
    ['B-NORM',routeCounts['B-NORM']||routeCounts.B_NORM||0,'rota normativa'],
    ['C-STRUCT',routeCounts['C-STRUCT']||routeCounts.C_STRUCT||0,'rota estrutural']
  ];
  $('#kpiGrid').innerHTML=kpis.map(([label,value,note])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span></article>`).join('');

  renderPipeline(summary,workbench);
  renderFunnel(workbench,tierA,routed);
  renderFullText(fullCounts,deep,tierA);
  renderExtraction(deep.extraction_method_counts||{});
  renderRoutes(routeCounts,tierA);
  renderClasses(articles);
  renderDomains(articles);
  renderTimeline(articles);
  renderProviders(state.radar);
  renderReadiness(formal);
  renderProvenance();
}

function renderPipeline(summary,workbench){
  const runtime=summary.runtime||{};const formal=summary.formal_search||{};
  const stages=[
    ['Discovery',String(summary.master_status||'').includes('DISCOVERY_CLOSED'),'harvest fechado'],
    ['Bank',workbench?.status==='ready','índice ativo'],
    ['Deepening',String(runtime.deepening?.status||'').toUpperCase()==='COMPLETE','Tier A'],
    ['Profiles',runtime.review_profiles?.present===true,'perfil v2'],
    ['Routes',String(runtime.article1_routes?.status||'').toUpperCase()==='PASS','B-NORM/C-STRUCT'],
    ['PRESS',String(formal.press_status||'').toUpperCase().includes('PASS'),'revisão da estratégia'],
    ['GF-10',formal.gf10_authorized===true,'gate formal'],
    ['Freeze',formal.query_freeze_complete===true,'query versionada'],
    ['Formal search',formal.formal_provider_search_executed===true,'não inferir'],
    ['PRISMA',formal.prisma_search_event_emitted===true,'evento formal']
  ];
  $('#pipeline').innerHTML=stages.map(([label,done,note],index)=>`<div class="pipeline-step ${statusClass(done,index===5)}"><span class="step-dot"></span><strong>${esc(label)}</strong><small>${esc(done?'concluído':index===5?'pendente':index>5?'bloqueado/pendente':note)}</small></div>`).join('');
}

function renderFunnel(workbench,tierA,routed){
  const bank=Number(workbench?.articles||0);
  const stages=[['Bank',bank],['Tier A',tierA],['Deepened',tierA],['Routed',routed]];
  $('#funnel').innerHTML=stages.map(([label,value],i)=>`${i?'<span class="funnel-arrow">→</span>':''}<div class="funnel-stage"><strong>${fmt(value)}</strong><span>${esc(label)}</span></div>`).join('');
}

function renderFullText(fullCounts,deep,tierA){
  const counts=Object.keys(fullCounts).length?fullCounts:(deep.retrieval_status_counts||{});
  const retrieved=Number(counts.retrieved||0);const partial=Number(counts.partial||0);const missing=Math.max(0,tierA-retrieved-partial);
  const total=Math.max(1,tierA);const a=100*retrieved/total;const b=100*(retrieved+partial)/total;
  const donut=$('#fullTextDonut');donut.style.background=`conic-gradient(var(--dashboard-primary) 0 ${a}%,#d6a321 ${a}% ${b}%,#d9dfdc ${b}% 100%)`;
  donut.innerHTML=`<div class="donut-center"><strong>${pct(retrieved+partial,tierA)}</strong><span>retrieved + partial</span></div>`;
  $('#fullTextLegend').innerHTML=[['Retrieved',retrieved,''],['Partial',partial,'partial'],['Not retrieved / other',missing,'missing']].map(([label,value,klass])=>`<div class="legend-item"><span class="legend-dot ${klass}"></span><span>${esc(label)}</span><strong>${fmt(value)}</strong></div>`).join('');
}

function renderBars(node,entries,labelMap={},limit=12){
  const rows=entries.slice(0,limit);const max=Math.max(1,...rows.map(([,value])=>Number(value||0)));
  node.innerHTML=rows.length?`<div class="chart-stack">${rows.map(([key,value])=>`<div class="bar-row"><span class="bar-label" title="${esc(labelMap[key]||key)}">${esc(labelMap[key]||key)}</span><span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${Math.max(1,100*Number(value||0)/max)}%"></span></span><strong class="bar-value">${fmt(value)}</strong></div>`).join('')}</div>`:'<div class="small-state">Dados ainda não disponíveis.</div>';
}

function renderExtraction(counts){renderBars($('#extractionChart'),sortedEntries(counts),{xml_text:'XML',pdf_text:'PDF',html_text:'HTML',direct_text:'Direct text',abstract_only:'Abstract only',unavailable:'Unavailable'},8)}
function renderRoutes(counts,tierA){
  const b=Number(counts['B-NORM']||0),c=Number(counts['C-STRUCT']||0),overlap=Number(counts.route_overlap_documents||0),unrouted=Number(counts.unrouted_documents||Math.max(0,tierA-(b+c-overlap)));
  $('#routesChart').innerHTML=`<div class="route-layout"><div class="route-card"><span>B-NORM</span><strong>${fmt(b)}</strong><small>documentos na rota normativa</small></div><div class="route-card"><span>C-STRUCT</span><strong>${fmt(c)}</strong><small>documentos na rota estrutural</small></div><div class="route-overlap"><div class="route-mini"><strong>${fmt(overlap)}</strong><span>overlap</span></div><div class="route-mini"><strong>${fmt(Math.max(0,b+c-overlap))}</strong><span>união</span></div><div class="route-mini"><strong>${fmt(unrouted)}</strong><span>não roteados</span></div></div></div>`;
}
function renderClasses(articles){const counts=countBy(articles,row=>row.review_profile?.primary_document_class||row.document_class||'unclassified');renderBars($('#classChart'),sortedEntries(counts),classLabels,12)}
function renderDomains(articles){const counts={};for(const row of articles){for(const domain of row.review_profile?.operational_domains||[]){counts[domain]=(counts[domain]||0)+1}}renderBars($('#domainChart'),sortedEntries(counts),domainLabels,11)}
function renderTimeline(articles){
  const counts=countBy(articles,row=>{const year=Number(row.year);return year>=1900&&year<=2100?String(year):''});
  const entries=Object.entries(counts).map(([year,value])=>[Number(year),value]).sort((a,b)=>a[0]-b[0]);
  const node=$('#timelineChart');
  if(!entries.length){node.innerHTML='<div class="small-state">Ano de publicação ainda não disponível.</div>';$('#timelineAxis').innerHTML='';return}
  const max=Math.max(...entries.map(([,value])=>value));node.innerHTML=entries.map(([year,value])=>`<span class="timeline-bar" style="height:${Math.max(3,100*value/max)}%" title="${year}: ${value}"></span>`).join('');
  $('#timelineAxis').innerHTML=`<span>${entries[0][0]}</span><span>${entries[Math.floor(entries.length/2)][0]}</span><span>${entries.at(-1)[0]}</span>`;
}
function renderProviders(radar){
  const providers=radar?.providers||[];const node=$('#providerBoard');
  node.innerHTML=providers.length?providers.map(item=>{const stateValue=item.state||'unknown';const details=Object.entries(item.status_counts||{}).map(([key,value])=>`${key} ${value}`).join(' · ')||'sem execução registrada';return `<div class="provider-line"><div><strong>${esc(providerLabels[item.provider]||item.provider)}</strong><small>${esc(details)}</small></div><span class="provider-state ${esc(stateValue)}">${esc(stateValue)}</span></div>`}).join(''):'<div class="small-state">Estado operacional de providers indisponível neste snapshot.</div>';
}
function renderReadiness(formal){
  const rows=[['PRESS',String(formal.press_status||'').toUpperCase().includes('PASS'),'PASS','PENDING'],['GF-10',formal.gf10_authorized===true,'AUTHORIZED','LOCKED'],['Query freeze',formal.query_freeze_complete===true,'COMPLETE','NOT COMPLETE'],['Formal search',formal.formal_provider_search_executed===true,'EXECUTED','NOT EXECUTED']];
  $('#readinessGrid').innerHTML=rows.map(([label,done,yes,no])=>`<div class="readiness-item"><span>${esc(label)}</span><strong>${esc(done?yes:no)}</strong></div>`).join('');
  $('#nextAction').innerHTML=`<strong>NEXT REQUIRED ACTION</strong><br>${esc(formal.next_gate||'Verificar o master da busca antes de avançar.')}`;
}
function renderProvenance(){
  const manifest=state.manifest||{};const summary=state.summary||{};
  const items=[['Search ID',summary.search_id||manifest.search_id||'—'],['Context version',summary.context_version||manifest.context_version||'—'],['Context created',summary.created_at||manifest.created_at||'—'],['Manifest status',manifest.status||'—']];
  $('#provenance').innerHTML=items.map(([label,value])=>`<div class="provider-line"><div><strong>${esc(label)}</strong><small>${esc(value)}</small></div></div>`).join('');
}

$('#refreshDashboard').addEventListener('click',load);
$('#presentationToggle').addEventListener('click',()=>{document.body.classList.toggle('presentation-mode');$('#presentationToggle').textContent=document.body.classList.contains('presentation-mode')?'Sair da apresentação':'Presentation View'});
load();
