const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const classLabels={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',implementation_evaluation:'Implementação',primary_randomized:'Randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
let articles=[];
const requestedRoute=new URLSearchParams(location.search).get('route');
let route=['B-NORM','C-STRUCT'].includes(requestedRoute)?requestedRoute:'B-NORM';
function syncRouteUrl(){const params=new URLSearchParams(location.search);params.set('route',route);history.replaceState(null,'',`${location.pathname}?${params}`)}
async function init(){
  try{const response=await fetch('/agent-context/article1/ARTICLE_SUMMARIES.jsonl',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);articles=(await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse);$('#routeState').className='hidden';$('#routeContent').classList.remove('hidden');$('#routeHealth').textContent=`${fmt(articles.length)} resumos verificados`;$('#routeHealth').className='status-pill ok';syncRouteUrl();render()}catch(error){$('#routeState').className='error';$('#routeState').innerHTML=`<strong>Review Routes indisponível.</strong><div>${esc(error.message)}</div>`;$('#routeHealth').textContent='contexto indisponível';$('#routeHealth').className='status-pill bad'}
}
function routeRows(name){return articles.filter(row=>(row.routes||[]).includes(name))}
function render(){
  const b=routeRows('B-NORM').length,c=routeRows('C-STRUCT').length,overlap=articles.filter(row=>(row.routes||[]).includes('B-NORM')&&(row.routes||[]).includes('C-STRUCT')).length,union=articles.filter(row=>(row.routes||[]).length).length;
  $('#routeKpis').innerHTML=[['B-NORM',b],['C-STRUCT',c],['Overlap',overlap],['Route union',union]].map(([label,value])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="metric-value">${fmt(value)}</strong></article>`).join('');
  document.querySelectorAll('[data-route]').forEach(button=>button.classList.toggle('active',button.dataset.route===route));
  const rows=routeRows(route);const classes={};for(const row of rows){const cls=row.review_profile?.primary_document_class||row.document_class||'unclassified';classes[cls]=(classes[cls]||0)+1}const mix=Object.entries(classes).sort((a,b)=>b[1]-a[1]).slice(0,8);
  $('#activeRouteTitle').textContent=route;$('#activeRouteMeta').textContent=`${fmt(rows.length)} documentos · ordem desta tela não é Bank rank`;
  $('#routeClassMix').innerHTML=mix.map(([key,value])=>`<span class="mini-pill">${esc(classLabels[key]||key)} · ${fmt(value)}</span>`).join('');
  $('#routeList').innerHTML=rows.map((row,index)=>`<article class="review-route-row"><div class="route-seq">${fmt(index+1)}</div><div><strong>${esc(row.title||'Sem título')}</strong><small>${esc([row.year,row.source_provider,classLabels[row.review_profile?.primary_document_class||row.document_class]].filter(Boolean).join(' · '))}</small><div class="detail-chips">${(row.review_profile?.operational_domains||[]).slice(0,4).map(value=>`<span class="mini-pill">${esc(value.replaceAll('_',' '))}</span>`).join('')}</div></div></article>`).join('')||'<p class="small-state">Nenhum documento nesta rota.</p>';
  $('#routeGuardrail').textContent=`${route} é uma fila de leitura/navegação. Permanecer nesta rota não significa inclusão; ficar fora dela não significa exclusão.`;
}
$('#routeTabs').addEventListener('click',event=>{const button=event.target.closest('[data-route]');if(!button)return;route=button.dataset.route;syncRouteUrl();render()});
init();