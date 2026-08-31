const interactiveState={articles:[],filters:{route:'',document_class:'',domain:'',source_provider:'',year:'',full_text_status:''}};

const FILTER_CONFIG={
  route:{label:'Rota'},
  document_class:{label:'Tipo documental'},
  domain:{label:'Domínio'},
  source_provider:{label:'Provider'},
  year:{label:'Ano'},
  full_text_status:{label:'Full text'}
};

const CLASS_LABELS={food_based_dietary_guideline:'Guia alimentar / FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position / scientific statement',framework_model:'Framework / modelo',competency_curriculum:'Competências / currículo',implementation_evaluation:'Implementação / viabilidade',primary_randomized:'Ensaio randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const DOMAIN_LABELS={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social da alimentação',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Medicina do Estilo de Vida',implementation_practice:'Implementação na prática'};
const PROVIDER_LABELS={pubmed:'PubMed',europepmc:'Europe PMC',europe_pmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs_native:'LILACS / BVS',scielo_native:'SciELO'};
const FULL_TEXT_LABELS={retrieved:'Disponível',partial:'Parcial',unavailable:'Indisponível',not_retrieved:'Não recuperado',not_attempted:'Ainda não buscado',unknown:'Não informado'};

const qs=selector=>document.querySelector(selector);
const escHtml=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmtNumber=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));

function effectiveClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function domains(row){return row.review_profile?.operational_domains||[]}
function routes(row){return row.routes||[]}
function unique(values){return [...new Set(values.filter(value=>value!==null&&value!==undefined&&String(value)!==''))]}
function countBy(rows,getter){const result={};for(const row of rows){const key=getter(row);if(!key)continue;result[key]=(result[key]||0)+1}return result}
function sortedEntries(counts){return Object.entries(counts).sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0])))}

function filterArticles(){
  const f=interactiveState.filters;
  return interactiveState.articles.filter(row=>{
    if(f.route&&!routes(row).includes(f.route))return false;
    if(f.document_class&&effectiveClass(row)!==f.document_class)return false;
    if(f.domain&&!domains(row).includes(f.domain))return false;
    if(f.source_provider&&String(row.source_provider||'')!==f.source_provider)return false;
    if(f.year&&String(row.year||'')!==f.year)return false;
    if(f.full_text_status&&String(row.full_text_status||'unknown')!==f.full_text_status)return false;
    return true;
  });
}

function readFiltersFromUrl(){
  const params=new URLSearchParams(location.search);
  for(const key of Object.keys(interactiveState.filters))interactiveState.filters[key]=params.get(key)||'';
}

function syncUrl(){
  const params=new URLSearchParams(location.search);
  for(const [key,value] of Object.entries(interactiveState.filters)){
    if(value)params.set(key,value);else params.delete(key);
  }
  const next=`${location.pathname}${params.toString()?`?${params}`:''}${location.hash||''}`;
  history.replaceState(null,'',next);
}

function optionMarkup(values,labelMap={}){
  return values.map(value=>`<option value="${escHtml(value)}">${escHtml(labelMap[value]||value)}</option>`).join('');
}

function injectFilterBar(){
  if(qs('#dashboardFilters'))return;
  const hero=qs('.project-hero');
  if(!hero)return;
  hero.insertAdjacentHTML('afterend',`<section id="dashboardFilters" class="card dashboard-filterbar" aria-label="Filtros globais do dashboard">
    <div class="dashboard-filter-head"><div><strong>Explore o Tier A</strong><span>Filtros analíticos locais sobre o contexto verificado do Artigo 1.</span></div><div class="dashboard-filter-actions"><button id="copyDashboardLink" class="ghost" type="button">Copiar link</button><button id="clearDashboardFilters" class="ghost" type="button">Limpar filtros</button></div></div>
    <div class="dashboard-filter-grid">
      <label>Rota<select id="filterRoute"><option value="">Todas</option></select></label>
      <label>Tipo documental<select id="filterDocumentClass"><option value="">Todos</option></select></label>
      <label>Domínio<select id="filterDomain"><option value="">Todos</option></select></label>
      <label>Provider<select id="filterProvider"><option value="">Todos</option></select></label>
      <label>Ano<select id="filterYear"><option value="">Todos</option></select></label>
      <label>Full text<select id="filterFullText"><option value="">Todos</option></select></label>
    </div>
    <div class="dashboard-filter-summary"><strong id="filteredDocumentCount">—</strong><span id="filteredDocumentMeta"> documentos no recorte atual</span><div id="activeFilterChips" class="active-filter-chips"></div></div>
    <div class="dashboard-filter-boundary">Os filtros reorganizam somente a visualização do Tier A. Eles não alteram elegibilidade, inclusão, qualidade, risco de viés ou qualquer evento PRISMA.</div>
  </section>`);
}

function populateFilters(){
  const articles=interactiveState.articles;
  const routeValues=unique(articles.flatMap(routes)).sort();
  const classValues=unique(articles.map(effectiveClass)).sort((a,b)=>(CLASS_LABELS[a]||a).localeCompare(CLASS_LABELS[b]||b));
  const domainValues=unique(articles.flatMap(domains)).sort((a,b)=>(DOMAIN_LABELS[a]||a).localeCompare(DOMAIN_LABELS[b]||b));
  const providerValues=unique(articles.map(row=>row.source_provider)).sort((a,b)=>(PROVIDER_LABELS[a]||a).localeCompare(PROVIDER_LABELS[b]||b));
  const yearValues=unique(articles.map(row=>String(row.year||'')).filter(Boolean)).sort((a,b)=>Number(b)-Number(a));
  const fullValues=unique(articles.map(row=>row.full_text_status||'unknown')).sort();
  qs('#filterRoute').insertAdjacentHTML('beforeend',optionMarkup(routeValues));
  qs('#filterDocumentClass').insertAdjacentHTML('beforeend',optionMarkup(classValues,CLASS_LABELS));
  qs('#filterDomain').insertAdjacentHTML('beforeend',optionMarkup(domainValues,DOMAIN_LABELS));
  qs('#filterProvider').insertAdjacentHTML('beforeend',optionMarkup(providerValues,PROVIDER_LABELS));
  qs('#filterYear').insertAdjacentHTML('beforeend',optionMarkup(yearValues));
  qs('#filterFullText').insertAdjacentHTML('beforeend',optionMarkup(fullValues,FULL_TEXT_LABELS));
}

function applyFilterValuesToControls(){
  const map={route:'#filterRoute',document_class:'#filterDocumentClass',domain:'#filterDomain',source_provider:'#filterProvider',year:'#filterYear',full_text_status:'#filterFullText'};
  for(const [key,selector] of Object.entries(map)){
    const node=qs(selector);if(!node)continue;
    const value=interactiveState.filters[key];
    if([...node.options].some(option=>option.value===value))node.value=value;else interactiveState.filters[key]='';
  }
}

function filterLabel(key,value){
  if(key==='document_class')return CLASS_LABELS[value]||value;
  if(key==='domain')return DOMAIN_LABELS[value]||value;
  if(key==='source_provider')return PROVIDER_LABELS[value]||value;
  if(key==='full_text_status')return FULL_TEXT_LABELS[value]||value;
  return value;
}

function renderFilterSummary(rows){
  qs('#filteredDocumentCount').textContent=fmtNumber(rows.length);
  qs('#filteredDocumentMeta').textContent=` de ${fmtNumber(interactiveState.articles.length)} documentos Tier A no recorte atual`;
  const chips=Object.entries(interactiveState.filters).filter(([,value])=>value).map(([key,value])=>`<button type="button" class="filter-chip" data-clear-filter="${escHtml(key)}"><span>${escHtml(FILTER_CONFIG[key].label)}:</span> ${escHtml(filterLabel(key,value))} <b aria-hidden="true">×</b></button>`).join('');
  qs('#activeFilterChips').innerHTML=chips||'<span class="filter-empty">Nenhum filtro ativo.</span>';
}

function corpusHref(extra={}){
  const params=new URLSearchParams();
  const merged={...interactiveState.filters,...extra};
  if(merged.document_class)params.set('document_class',merged.document_class);
  if(merged.source_provider)params.set('source_provider',merged.source_provider);
  if(merged.full_text_status)params.set('full_text_status',merged.full_text_status);
  return `/articles.html${params.toString()?`?${params}`:''}`;
}

function renderClickableBars(node,entries,labelMap,hrefBuilder,limit=12){
  if(!node)return;
  const rows=entries.slice(0,limit);const max=Math.max(1,...rows.map(([,value])=>Number(value||0)));
  node.innerHTML=rows.length?`<div class="chart-stack interactive-chart">${rows.map(([key,value])=>`<a class="bar-row interactive-bar" href="${escHtml(hrefBuilder(key))}" title="Abrir ${escHtml(labelMap[key]||key)} · ${fmtNumber(value)} documentos. Contagem não representa força da evidência."><span class="bar-label">${escHtml(labelMap[key]||key)}</span><span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${Math.max(1,100*Number(value||0)/max)}%"></span></span><strong class="bar-value">${fmtNumber(value)}</strong><span class="bar-open" aria-hidden="true">↗</span></a>`).join('')}</div>`:'<div class="small-state">Nenhum documento neste recorte.</div>';
}

function renderClasses(rows){
  renderClickableBars(qs('#classChart'),sortedEntries(countBy(rows,effectiveClass)),CLASS_LABELS,key=>corpusHref({document_class:key}),12);
}

function renderDomains(rows){
  const counts={};for(const row of rows)for(const domain of domains(row))counts[domain]=(counts[domain]||0)+1;
  renderClickableBars(qs('#domainChart'),sortedEntries(counts),DOMAIN_LABELS,key=>`/evidence.html?domain=${encodeURIComponent(key)}`,11);
}

function renderRoutes(rows){
  const b=rows.filter(row=>routes(row).includes('B-NORM')).length;
  const c=rows.filter(row=>routes(row).includes('C-STRUCT')).length;
  const overlap=rows.filter(row=>routes(row).includes('B-NORM')&&routes(row).includes('C-STRUCT')).length;
  const union=rows.filter(row=>routes(row).length).length;
  const unrouted=rows.length-union;
  const node=qs('#routesChart');if(!node)return;
  node.innerHTML=`<div class="route-layout interactive-routes"><a class="route-card" href="/review-routes.html?route=B-NORM" title="Abrir fila B-NORM. Rota não equivale a inclusão."><span>B-NORM</span><strong>${fmtNumber(b)}</strong><small>documentos no recorte</small><b>Open ↗</b></a><a class="route-card" href="/review-routes.html?route=C-STRUCT" title="Abrir fila C-STRUCT. Rota não equivale a inclusão."><span>C-STRUCT</span><strong>${fmtNumber(c)}</strong><small>documentos no recorte</small><b>Open ↗</b></a><div class="route-overlap"><div class="route-mini"><strong>${fmtNumber(overlap)}</strong><span>overlap</span></div><div class="route-mini"><strong>${fmtNumber(union)}</strong><span>união</span></div><div class="route-mini"><strong>${fmtNumber(unrouted)}</strong><span>não roteados</span></div></div></div>`;
}

function renderFullText(rows){
  const counts=countBy(rows,row=>row.full_text_status||'unknown');
  const retrieved=Number(counts.retrieved||0),partial=Number(counts.partial||0),other=Math.max(0,rows.length-retrieved-partial),total=Math.max(1,rows.length);
  const a=100*retrieved/total,b=100*(retrieved+partial)/total;
  const donut=qs('#fullTextDonut');if(donut){donut.style.background=`conic-gradient(var(--dashboard-primary) 0 ${a}%,#d6a321 ${a}% ${b}%,#d9dfdc ${b}% 100%)`;donut.innerHTML=`<div class="donut-center"><strong>${rows.length?`${(100*(retrieved+partial)/rows.length).toLocaleString('pt-BR',{maximumFractionDigits:1})}%`:'—'}</strong><span>retrieved + partial</span></div>`}
  const legend=qs('#fullTextLegend');if(legend)legend.innerHTML=[['retrieved','Retrieved',retrieved,''],['partial','Partial',partial,'partial'],['other','Other / not retrieved',other,'missing']].map(([status,label,value,klass])=>status==='other'?`<div class="legend-item"><span class="legend-dot ${klass}"></span><span>${label}</span><strong>${fmtNumber(value)}</strong></div>`:`<a class="legend-item legend-link" href="${escHtml(corpusHref({full_text_status:status}))}" title="Abrir Corpus Explorer filtrado. Full-text retrieval não equivale a elegibilidade."><span class="legend-dot ${klass}"></span><span>${label}</span><strong>${fmtNumber(value)}</strong><b>↗</b></a>`).join('');
}

function renderTimeline(rows){
  const counts=countBy(rows,row=>{const year=Number(row.year);return year>=1900&&year<=2100?String(year):''});
  const entries=Object.entries(counts).map(([year,value])=>[Number(year),value]).sort((a,b)=>a[0]-b[0]);
  const node=qs('#timelineChart'),axis=qs('#timelineAxis');if(!node||!axis)return;
  if(!entries.length){node.innerHTML='<div class="small-state">Ano de publicação não disponível neste recorte.</div>';axis.innerHTML='';return}
  const max=Math.max(...entries.map(([,value])=>value));
  node.innerHTML=entries.map(([year,value])=>`<button type="button" class="timeline-bar timeline-button${interactiveState.filters.year===String(year)?' active':''}" style="height:${Math.max(3,100*value/max)}%" data-filter-year="${year}" title="${year}: ${fmtNumber(value)} documentos. Clique para filtrar o dashboard; volume não representa força de evidência."><span class="sr-only">${year}: ${fmtNumber(value)} documentos</span></button>`).join('');
  axis.innerHTML=`<span>${entries[0][0]}</span><span>${entries[Math.floor(entries.length/2)][0]}</span><span>${entries.at(-1)[0]}</span>`;
}

function renderFilteredView(){
  const rows=filterArticles();
  renderFilterSummary(rows);
  renderClasses(rows);renderDomains(rows);renderRoutes(rows);renderFullText(rows);renderTimeline(rows);
}

function setFilter(key,value){interactiveState.filters[key]=value||'';applyFilterValuesToControls();syncUrl();renderFilteredView()}

function bindEvents(){
  const bindings={filterRoute:'route',filterDocumentClass:'document_class',filterDomain:'domain',filterProvider:'source_provider',filterYear:'year',filterFullText:'full_text_status'};
  for(const [id,key] of Object.entries(bindings))qs(`#${id}`).addEventListener('change',event=>setFilter(key,event.target.value));
  qs('#clearDashboardFilters').addEventListener('click',()=>{for(const key of Object.keys(interactiveState.filters))interactiveState.filters[key]='';applyFilterValuesToControls();syncUrl();renderFilteredView()});
  qs('#activeFilterChips').addEventListener('click',event=>{const button=event.target.closest('[data-clear-filter]');if(button)setFilter(button.dataset.clearFilter,'')});
  qs('#timelineChart').addEventListener('click',event=>{const button=event.target.closest('[data-filter-year]');if(button)setFilter('year',interactiveState.filters.year===button.dataset.filterYear?'':button.dataset.filterYear)});
  qs('#copyDashboardLink').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);qs('#copyDashboardLink').textContent='Link copiado';setTimeout(()=>qs('#copyDashboardLink').textContent='Copiar link',1300)}catch{qs('#copyDashboardLink').textContent='Copie pela barra do navegador'}});
}

async function waitForBaseDashboard(){
  for(let attempt=0;attempt<80;attempt+=1){if(qs('#dashboardContent')&&!qs('#dashboardContent').classList.contains('hidden'))return true;await new Promise(resolve=>setTimeout(resolve,100))}
  return false;
}

async function initInteractiveDashboard(){
  injectFilterBar();
  try{
    const response=await fetch('/agent-context/article1/ARTICLE_SUMMARIES.jsonl',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
    interactiveState.articles=(await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse);
    readFiltersFromUrl();populateFilters();applyFilterValuesToControls();bindEvents();
    await waitForBaseDashboard();renderFilteredView();syncUrl();
  }catch(error){
    const summary=qs('.dashboard-filter-summary');if(summary)summary.innerHTML=`<span class="small-state">Filtros interativos indisponíveis: ${escHtml(error.message)}</span>`;
  }
}

initInteractiveDashboard();
