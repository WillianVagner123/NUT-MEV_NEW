const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const labels={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências e habilidades alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social da alimentação',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Medicina do Estilo de Vida',implementation_practice:'Implementação na prática'};
const classLabels={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',implementation_evaluation:'Implementação',primary_randomized:'Randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const params=new URLSearchParams(location.search);
let articles=[];
let selected=params.get('domain')||'';
let selectedClass=params.get('document_class')||'';
let selectedRoute=['B-NORM','C-STRUCT'].includes(params.get('route'))?params.get('route'):'';

function effectiveClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function routeMatch(row){return !selectedRoute||(row.routes||[]).includes(selectedRoute)}
function contextRows(){return articles.filter(row=>(!selectedClass||effectiveClass(row)===selectedClass)&&routeMatch(row))}
function syncDomainUrl(){const next=new URLSearchParams();if(selected)next.set('domain',selected);if(selectedClass)next.set('document_class',selectedClass);if(selectedRoute)next.set('route',selectedRoute);history.replaceState(null,'',`${location.pathname}${next.toString()?`?${next}`:''}`)}
function corpusHref(){const next=new URLSearchParams();if(selectedClass)next.set('document_class',selectedClass);return `/articles.html${next.toString()?`?${next}`:''}`}

async function load(){
  try{
    const response=await fetch('/agent-context/article1/ARTICLE_SUMMARIES.jsonl',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
    articles=(await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse);
    const availableDomains=new Set(articles.flatMap(row=>row.review_profile?.operational_domains||[]));
    const availableClasses=new Set(articles.map(effectiveClass));
    if(selected&&!availableDomains.has(selected))selected='';
    if(selectedClass&&!availableClasses.has(selectedClass))selectedClass='';
    renderDomains();syncDomainUrl();
    $('#evidenceState').className='hidden';$('#evidenceContent').classList.remove('hidden');$('#evidenceHealth').textContent=`${fmt(articles.length)} resumos verificados`;$('#evidenceHealth').className='status-pill ok';
  }catch(error){$('#evidenceState').className='error';$('#evidenceState').innerHTML=`<strong>Evidence Explorer indisponível.</strong><div>${esc(error.message)}</div>`;$('#evidenceHealth').textContent='contexto indisponível';$('#evidenceHealth').className='status-pill bad'}
}
function domainRows(){const counts={};for(const row of contextRows()){for(const domain of row.review_profile?.operational_domains||[]){counts[domain]=(counts[domain]||0)+1}}return Object.entries(counts).sort((a,b)=>b[1]-a[1])}
function renderDomains(){const rows=domainRows();if(!selected&&rows.length)selected=rows[0][0];if(selected&&!rows.some(([domain])=>domain===selected)&&rows.length)selected=rows[0][0];$('#domainCards').innerHTML=rows.map(([domain,count])=>`<button type="button" class="domain-explorer-card${selected===domain?' active':''}" data-domain="${esc(domain)}"><span>${esc(labels[domain]||domain)}</span><strong>${fmt(count)}</strong><small>${(100*count/Math.max(1,contextRows().length)).toLocaleString('pt-BR',{maximumFractionDigits:1})}% do recorte</small></button>`).join('')||'<p class="small-state">Nenhum domínio mapeado neste recorte.</p>';renderDetail()}
function renderDetail(){if(!selected)return;const rows=contextRows().filter(row=>(row.review_profile?.operational_domains||[]).includes(selected));const classCounts={};const routeCounts={};for(const row of rows){const cls=effectiveClass(row);classCounts[cls]=(classCounts[cls]||0)+1;for(const route of row.routes||[])routeCounts[route]=(routeCounts[route]||0)+1}const classes=Object.entries(classCounts).sort((a,b)=>b[1]-a[1]).slice(0,6);const activeFilters=[selectedClass?classLabels[selectedClass]||selectedClass:'',selectedRoute].filter(Boolean);$('#domainTitle').textContent=labels[selected]||selected;$('#domainMeta').textContent=`${fmt(rows.length)} documentos · B-NORM ${fmt(routeCounts['B-NORM']||0)} · C-STRUCT ${fmt(routeCounts['C-STRUCT']||0)}${activeFilters.length?` · filtro ${activeFilters.join(' · ')}`:''}`;$('#domainClassMix').innerHTML=`${activeFilters.map(value=>`<span class="mini-pill">Filtro · ${esc(value)}</span>`).join('')}${classes.map(([key,value])=>`<span class="mini-pill">${esc(classLabels[key]||key)} · ${fmt(value)}</span>`).join('')}`;$('#domainArticles').innerHTML=rows.slice(0,30).map(row=>`<article class="evidence-article"><div><strong>${esc(row.title||'Sem título')}</strong><small>${esc([row.year,row.source_provider,classLabels[effectiveClass(row)]].filter(Boolean).join(' · '))}</small></div><div class="detail-chips">${(row.routes||[]).map(route=>`<span class="mini-pill">${esc(route)}</span>`).join('')}</div></article>`).join('')||'<p class="small-state">Nenhum artigo neste recorte.</p>';$('#domainNote').textContent='Lista de navegação baseada em perfil determinístico. Não é inclusão, exclusão, qualidade ou recomendação.';const corpus=$('#evidenceCorpusLink');if(corpus)corpus.href=corpusHref()}
$('#domainCards').addEventListener('click',event=>{const button=event.target.closest('[data-domain]');if(!button)return;selected=button.dataset.domain;syncDomainUrl();renderDomains()});
load();