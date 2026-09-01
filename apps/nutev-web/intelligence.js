const intelligenceState={articles:[],search:null,activeDomain:'',loadedFindings:[],detailCache:new Map(),loadingToken:0};
const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const pct=(a,b)=>b?100*Number(a||0)/Number(b):0;
const FINDING_BATCH_LIMIT=24;
const DETAIL_CONCURRENCY=4;

const DOMAIN_ORDER=['nutrition_assessment','dietary_counseling','nutrition_prescription','monitoring_follow_up','food_skills_competencies','food_literacy','social_context','food_based_guidance','nutrition_care_process','lifestyle_medicine','implementation_practice'];
const DOMAIN_LABELS={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social da alimentação',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Medicina do Estilo de Vida',implementation_practice:'Implementação na prática'};
const CLASS_LABELS={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',evidence_synthesis:'Síntese de evidência',implementation_evaluation:'Implementação',primary_observational:'Observacional',primary_randomized:'Randomizado',primary_qualitative:'Qualitativo',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};

function domains(row){return row.review_profile?.operational_domains||[]}
function documentClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function routes(row){return row.routes||[]}
function countBy(rows,getter){const counts={};for(const row of rows){const key=getter(row);if(!key)continue;counts[key]=(counts[key]||0)+1}return counts}
function topEntries(counts,limit=3){return Object.entries(counts).sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]))).slice(0,limit)}
function domainRows(domain){return intelligenceState.articles.filter(row=>domains(row).includes(domain))}
function availableDomains(){return DOMAIN_ORDER.filter(domain=>intelligenceState.articles.some(row=>domains(row).includes(domain)))}
function cleanOutcome(value){return String(value||'').trim().replace(/\s+/g,' ')}
function outcomeKey(value){return cleanOutcome(value).toLocaleLowerCase('en-US')}

async function fetchJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return response.json()}
async function fetchJsonl(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);const text=await response.text();return text.split(/\r?\n/).filter(Boolean).map(JSON.parse)}

function domainSummary(domain){
  const rows=domainRows(domain);
  const classCounts=countBy(rows,documentClass);
  const findingReady=rows.filter(row=>Number(row.result_bundle_count||0)>0).length;
  const bnorm=rows.filter(row=>routes(row).includes('B-NORM')).length;
  const cstruct=rows.filter(row=>routes(row).includes('C-STRUCT')).length;
  const overlap=rows.filter(row=>routes(row).includes('B-NORM')&&routes(row).includes('C-STRUCT')).length;
  const years=rows.map(row=>Number(row.year)).filter(year=>year>=1900&&year<=2100);
  return {domain,documents:rows.length,findingReady,bnorm,cstruct,overlap,classCounts,yearMin:years.length?Math.min(...years):null,yearMax:years.length?Math.max(...years):null};
}

function structuralExport(){return availableDomains().map(domain=>domainSummary(domain))}

function renderKpis(){
  const rows=intelligenceState.articles;
  const mappedDomains=availableDomains();
  const findingReady=rows.filter(row=>Number(row.result_bundle_count||0)>0).length;
  const overlap=rows.filter(row=>routes(row).includes('B-NORM')&&routes(row).includes('C-STRUCT')).length;
  const cards=[
    ['Tier A',rows.length,'resumos rank-blind'],
    ['Domínios',mappedDomains.length,'dimensões operacionais mapeadas'],
    ['Finding-ready',findingReady,'documentos com result bundle materializado'],
    ['Route overlap',overlap,'B-NORM + C-STRUCT; não inclusão']
  ];
  $('#intelligenceKpis').innerHTML=cards.map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${fmt(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderDomainSynthesis(){
  const total=intelligenceState.articles.length||1;
  $('#domainSynthesis').innerHTML=structuralExport().map(item=>{
    const classes=topEntries(item.classCounts).map(([key,value])=>`<span class="mini-chip">${esc(CLASS_LABELS[key]||key)} · ${fmt(value)}</span>`).join('');
    const active=item.domain===intelligenceState.activeDomain?' active':'';
    const yearRange=item.yearMin&&item.yearMax?(item.yearMin===item.yearMax?String(item.yearMin):`${item.yearMin}–${item.yearMax}`):'ano n/d';
    return `<article class="domain-card${active}" data-domain-card="${esc(item.domain)}"><button type="button" data-select-domain="${esc(item.domain)}"><div class="domain-card-head"><div><h3>${esc(DOMAIN_LABELS[item.domain]||item.domain)}</h3><small>${pct(item.documents,total).toLocaleString('pt-BR',{maximumFractionDigits:1})}% do Tier A · ${esc(yearRange)}</small></div><span class="domain-count">${fmt(item.documents)}</span></div><div class="domain-metrics"><div class="domain-metric"><strong>${fmt(item.findingReady)}</strong><span>finding-ready</span></div><div class="domain-metric"><strong>${fmt(item.bnorm)} / ${fmt(item.cstruct)}</strong><span>B-NORM / C-STRUCT</span></div><div class="domain-metric"><strong>${fmt(item.overlap)}</strong><span>route overlap</span></div></div><div class="mini-stack">${classes||'<span class="mini-chip">classes n/d</span>'}</div></button></article>`;
  }).join('')||'<div class="small-state">Nenhum domínio operacional materializado.</div>';
}

function renderDomainSelect(){
  const options=availableDomains().map(domain=>`<option value="${esc(domain)}"${domain===intelligenceState.activeDomain?' selected':''}>${esc(DOMAIN_LABELS[domain]||domain)}</option>`).join('');
  $('#findingDomainSelectWrap').innerHTML=`<select id="findingDomainSelect" class="intelligence-select" aria-label="Domínio para inspeção de achados"><option value="">Selecione um domínio</option>${options}</select>`;
  $('#findingDomainSelect').addEventListener('change',event=>selectDomain(event.target.value));
}

function renderCoverageSignals(){
  const total=intelligenceState.articles.length||1;
  const rows=structuralExport().sort((a,b)=>a.documents-b.documents||String(a.domain).localeCompare(String(b.domain)));
  $('#coverageSignals').innerHTML=rows.map(item=>{
    const share=pct(item.documents,total);
    const bundleCoverage=pct(item.findingReady,item.documents);
    return `<div class="coverage-item"><div class="coverage-row"><strong>${esc(DOMAIN_LABELS[item.domain]||item.domain)}</strong><span>${fmt(item.documents)} docs · ${bundleCoverage.toLocaleString('pt-BR',{maximumFractionDigits:0})}% finding-ready</span></div><div class="coverage-bar" title="${share.toLocaleString('pt-BR',{maximumFractionDigits:1})}% do Tier A"><i style="--coverage:${Math.max(2,share)}%"></i></div><small>Corpus coverage signal only — não classificado como evidence gap.</small></div>`;
  }).join('');
}

async function detailFor(documentId){
  if(intelligenceState.detailCache.has(documentId))return intelligenceState.detailCache.get(documentId);
  const promise=fetchJson(`/api/articles/${encodeURIComponent(documentId)}`).catch(error=>({status:'error',error:error.message,result_bundles:[]}));
  intelligenceState.detailCache.set(documentId,promise);
  return promise;
}

async function mapLimited(rows,limit,worker){
  const output=new Array(rows.length);let index=0;
  const runners=Array.from({length:Math.min(limit,rows.length)},async()=>{while(true){const current=index++;if(current>=rows.length)return;output[current]=await worker(rows[current],current)}});
  await Promise.all(runners);return output;
}

function findingFromDetail(row,detail){
  const bundles=Array.isArray(detail?.result_bundles)?detail.result_bundles:[];
  const bundle=bundles.find(item=>item.result_kind==='main_result')||bundles[0];
  if(!bundle)return null;
  return {
    document_id:row.document_id,title:row.title||'Sem título',year:row.year,source_provider:row.source_provider,
    document_class:documentClass(row),routes:routes(row),domains:domains(row),result_kind:bundle.result_kind||'result_candidate',
    result_text:String(bundle.result_text||'').trim(),outcomes:(bundle.outcomes||[]).map(cleanOutcome).filter(Boolean),
    effect_measures:bundle.effect_measures||[],confidence_intervals:bundle.confidence_intervals||[],p_values:bundle.p_values||[],
    reference:bundle.reference||null,status:bundle.status||'machine_candidate_not_evidence_claim'
  };
}

async function loadDomainFindings(domain){
  const token=++intelligenceState.loadingToken;
  intelligenceState.loadedFindings=[];
  renderFindings();renderRecurrence();renderComparisonQueue();
  if(!domain){$('#findingState').className='small-state';$('#findingState').textContent='Nenhum domínio selecionado.';$('#findingScope').textContent='Selecione um domínio. O NutEV carrega somente um lote limitado de dossiês, sem full text integral.';return}
  const eligible=domainRows(domain).filter(row=>Number(row.result_bundle_count||0)>0).sort((a,b)=>String(a.title||'').localeCompare(String(b.title||''))||String(a.document_id).localeCompare(String(b.document_id)));
  const sample=eligible.slice(0,FINDING_BATCH_LIMIT);
  $('#findingState').className='loading';$('#findingState').textContent=`Carregando ${fmt(sample.length)} dossiês de forma lazy…`;
  $('#findingScope').textContent=`${DOMAIN_LABELS[domain]||domain}: lote operacional de até ${FINDING_BATCH_LIMIT} documentos com result bundles. Não é ranking nem amostra estatística.`;
  const details=await mapLimited(sample,DETAIL_CONCURRENCY,async row=>findingFromDetail(row,await detailFor(row.document_id)));
  if(token!==intelligenceState.loadingToken)return;
  intelligenceState.loadedFindings=details.filter(Boolean);
  $('#findingState').className='small-state';$('#findingState').textContent=`${fmt(intelligenceState.loadedFindings.length)} achados candidatos carregados de ${fmt(eligible.length)} documentos finding-ready neste domínio. Lote limitado para navegação.`;
  renderFindings();renderRecurrence();renderComparisonQueue();
}

function renderFindings(){
  const rows=intelligenceState.loadedFindings;
  $('#findingCandidates').innerHTML=rows.map(item=>{
    const metrics=[...(item.effect_measures||[]),...(item.confidence_intervals||[]),...(item.p_values||[])].slice(0,4);
    const outcomeChips=(item.outcomes||[]).slice(0,4).map(value=>`<span>Outcome: ${esc(value)}</span>`).join('');
    const routeChips=(item.routes||[]).map(value=>`<span>${esc(value)}</span>`).join('');
    return `<article class="finding-card"><div class="finding-card-head"><div><h3>${esc(item.title)}</h3><small>${esc([item.year,item.source_provider,CLASS_LABELS[item.document_class]||item.document_class].filter(Boolean).join(' · '))}</small></div><span class="mini-chip">${esc(item.result_kind)}</span></div><p class="finding-quote">${esc(item.result_text||'Trecho de resultado não materializado.')}</p><div class="finding-meta">${outcomeChips}${routeChips}${metrics.map(value=>`<span>${esc(value)}</span>`).join('')}</div><div class="finding-actions"><button type="button" data-compare-document="${esc(item.document_id)}">Usar na comparação</button></div></article>`;
  }).join('')||'';
}

function recurrenceGroups(){
  const groups=new Map();
  for(const finding of intelligenceState.loadedFindings){for(const label of finding.outcomes||[]){const key=outcomeKey(label);if(!key)continue;if(!groups.has(key))groups.set(key,{label,findings:new Map()});groups.get(key).findings.set(finding.document_id,finding)}}
  return [...groups.values()].map(group=>({label:group.label,findings:[...group.findings.values()]})).filter(group=>group.findings.length>=2).sort((a,b)=>b.findings.length-a.findings.length||a.label.localeCompare(b.label));
}

function renderRecurrence(){
  const groups=recurrenceGroups();
  $('#outcomeRecurrence').innerHTML=groups.slice(0,12).map((group,index)=>`<div class="recurrence-item"><div class="recurrence-row"><strong>${esc(group.label)}</strong><span>${fmt(group.findings.length)} docs</span></div><small>Mesmo rótulo estruturado no lote; direção do resultado não foi inferida.</small><button type="button" data-open-recurrence="${index}">Abrir comparação</button></div>`).join('')||(intelligenceState.loadedFindings.length?'<div class="small-state">Nenhum outcome estruturado apareceu em 2+ documentos deste lote. Isso não demonstra ausência de convergência.</div>':'<div class="small-state">Carregue um domínio para inspecionar recorrências.</div>');
}

function pairHtml(findings,label){
  const pair=findings.slice(0,2);
  if(pair.length<2)return '<div class="small-state">São necessários pelo menos dois documentos materializados para comparação.</div>';
  return `<div class="comparison-item"><strong>${esc(label||'Comparação manual')}</strong><small>Fila humana: o NutEV não conclui concordância, contradição ou certeza.</small><div class="comparison-pair">${pair.map(item=>`<div class="comparison-side"><strong>${esc(item.title)}</strong><p>${esc(item.result_text)}</p></div>`).join('')}</div></div>`;
}

function renderComparisonQueue(selectedDocumentId=null,recurrenceIndex=null){
  const node=$('#comparisonQueue');
  if(recurrenceIndex!==null){const group=recurrenceGroups()[recurrenceIndex];node.innerHTML=group?pairHtml(group.findings,`Outcome recorrente: ${group.label}`):'<div class="small-state">Grupo não disponível.</div>';return}
  if(selectedDocumentId){const chosen=intelligenceState.loadedFindings.find(item=>item.document_id===selectedDocumentId);const other=intelligenceState.loadedFindings.find(item=>item.document_id!==selectedDocumentId);node.innerHTML=chosen&&other?pairHtml([chosen,other],'Comparação manual selecionada'):'<div class="small-state">Outro documento não está disponível no lote atual.</div>';return}
  const groups=recurrenceGroups();
  if(groups.length){node.innerHTML=groups.slice(0,4).map(group=>pairHtml(group.findings,`Outcome recorrente: ${group.label}`)).join('');return}
  node.innerHTML=intelligenceState.loadedFindings.length>=2?pairHtml(intelligenceState.loadedFindings,'Comparação manual sem outcome recorrente'):'<div class="small-state">Carregue pelo menos dois achados candidatos para montar a fila de comparação.</div>';
}

function exportPayload(){return {
  export_type:'NUTEV_SCIENTIFIC_INTELLIGENCE_VIEW_V1',generated_at:new Date().toISOString(),question:intelligenceState.search?.question||null,
  context_version:intelligenceState.search?.context_version||null,structural_domain_synthesis:structuralExport(),active_domain:intelligenceState.activeDomain||null,
  loaded_finding_candidates:intelligenceState.loadedFindings,recurring_outcome_labels:recurrenceGroups().map(group=>({label:group.label,document_ids:group.findings.map(item=>item.document_id)})),
  guardrails:{rank_blind_structural_synthesis:true,full_text_in_export:false,result_bundles_are_not_accepted_evidence_claims:true,recurrence_is_not_consensus:true,convergence_divergence_requires_human_review:true,sparse_mapping_is_not_evidence_gap:true,not_prisma:true}
}}

function downloadExport(){const payload=JSON.stringify(exportPayload(),null,2);const blob=new Blob([payload],{type:'application/json'});const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download='nutev-scientific-intelligence.json';document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url)}

async function selectDomain(domain){intelligenceState.activeDomain=domain;renderDomainSynthesis();renderDomainSelect();await loadDomainFindings(domain)}

function bindEvents(){
  $('#domainSynthesis').addEventListener('click',event=>{const button=event.target.closest('[data-select-domain]');if(button)selectDomain(button.dataset.selectDomain)});
  $('#findingCandidates').addEventListener('click',event=>{const button=event.target.closest('[data-compare-document]');if(button)renderComparisonQueue(button.dataset.compareDocument,null)});
  $('#outcomeRecurrence').addEventListener('click',event=>{const button=event.target.closest('[data-open-recurrence]');if(button)renderComparisonQueue(null,Number(button.dataset.openRecurrence))});
  $('#exportIntelligence').addEventListener('click',downloadExport);$('#printIntelligence').addEventListener('click',()=>window.print());$('#refreshIntelligence').addEventListener('click',()=>load());
}

async function load(){
  intelligenceState.loadingToken++;intelligenceState.loadedFindings=[];intelligenceState.activeDomain='';
  $('#intelligenceState').className='loading dashboard-state';$('#intelligenceState').textContent='Construindo síntese estrutural rank-blind…';$('#intelligenceContent').classList.add('hidden');
  try{
    const [articles,search]=await Promise.all([fetchJsonl('/agent-context/article1/ARTICLE_SUMMARIES.jsonl'),fetchJson('/agent-context/article1/SEARCH_STATE.json')]);
    intelligenceState.articles=articles;intelligenceState.search=search;$('#intelligenceQuestion').textContent=search.question||'Article 1 — contexto científico do NutEV';
    renderKpis();renderCoverageSignals();renderDomainSynthesis();renderDomainSelect();renderFindings();renderRecurrence();renderComparisonQueue();
    $('#intelligenceState').className='hidden';$('#intelligenceContent').classList.remove('hidden');$('#intelligenceHealth').textContent=`${fmt(articles.length)} resumos verificados`;$('#intelligenceHealth').className='status-pill ok';
    const first=availableDomains()[0]||'';if(first)await selectDomain(first);
  }catch(error){$('#intelligenceState').className='error dashboard-state';$('#intelligenceState').innerHTML=`<strong>Scientific Intelligence indisponível.</strong><div>${esc(error.message)}</div>`;$('#intelligenceHealth').textContent='contexto indisponível';$('#intelligenceHealth').className='status-pill bad'}
}

bindEvents();load();
