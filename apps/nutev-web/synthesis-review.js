const REVIEW_VERSION='NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1';
const DETAIL_BATCH_LIMIT=18;
const DETAIL_CONCURRENCY=4;
const state={articles:[],search:null,domain:'',findings:[],anchorId:'',draft:null,detailCache:new Map(),loadingToken:0};
const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));

const DOMAIN_ORDER=['nutrition_assessment','dietary_counseling','nutrition_prescription','monitoring_follow_up','food_skills_competencies','food_literacy','social_context','food_based_guidance','nutrition_care_process','lifestyle_medicine','implementation_practice'];
const DOMAIN_LABELS={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social da alimentação',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Medicina do Estilo de Vida',implementation_practice:'Implementação na prática'};
const CLASS_LABELS={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',evidence_synthesis:'Síntese de evidência',implementation_evaluation:'Implementação',primary_observational:'Observacional',primary_randomized:'Randomizado',primary_qualitative:'Qualitativo',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const DIMENSION_OPTIONS=[['SIMILAR','Similar'],['DIFFERENT','Diferente'],['UNCLEAR','Incerto'],['NOT_AVAILABLE','Não disponível']];
const RELATION_OPTIONS=[['','Selecione'],['CONVERGENT','Convergente'],['DIVERGENT','Divergente'],['COMPLEMENTARY','Complementar'],['NOT_COMPARABLE','Não comparável'],['UNCLEAR','Incerta']];

function domains(row){return row.review_profile?.operational_domains||[]}
function documentClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function routes(row){return row.routes||[]}
function availableDomains(){return DOMAIN_ORDER.filter(domain=>state.articles.some(row=>domains(row).includes(domain)&&Number(row.result_bundle_count||0)>0))}
function domainRows(domain){return state.articles.filter(row=>domains(row).includes(domain)&&Number(row.result_bundle_count||0)>0)}
function storageKey(){return `nutev:synthesis-review:${state.search?.search_id||'unknown'}:${state.search?.context_version||'unknown'}`}
function decisionId(anchorId,candidateId){return [anchorId,candidateId].sort().join('::')}

async function fetchJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);return response.json()}
async function fetchJsonl(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);const text=await response.text();return text.split(/\r?\n/).filter(Boolean).map(JSON.parse)}

function blankDraft(){return {version:REVIEW_VERSION,canonical:false,search_id:state.search?.search_id||null,context_version:state.search?.context_version||null,reviewer:'',decisions:{}}}
function loadDraft(){try{const raw=localStorage.getItem(storageKey());const parsed=raw?JSON.parse(raw):null;state.draft=parsed?.version===REVIEW_VERSION&&parsed?.canonical===false?parsed:blankDraft()}catch{state.draft=blankDraft()}}
function saveDraft(){localStorage.setItem(storageKey(),JSON.stringify(state.draft))}

async function detailFor(documentId){
  if(state.detailCache.has(documentId))return state.detailCache.get(documentId);
  const promise=fetchJson(`/api/articles/${encodeURIComponent(documentId)}`).catch(error=>({status:'error',error:error.message,result_bundles:[]}));
  state.detailCache.set(documentId,promise);return promise;
}
async function mapLimited(rows,limit,worker){const output=new Array(rows.length);let index=0;const runners=Array.from({length:Math.min(limit,rows.length)},async()=>{while(true){const current=index++;if(current>=rows.length)return;output[current]=await worker(rows[current],current)}});await Promise.all(runners);return output}
function cleanValues(values){return [...new Set((values||[]).map(value=>String(value||'').trim()).filter(Boolean))]}
function findingFromDetail(row,detail){
  const bundles=Array.isArray(detail?.result_bundles)?detail.result_bundles:[];
  const bundle=bundles.find(item=>item.result_kind==='main_result')||bundles[0];if(!bundle)return null;
  return {document_id:row.document_id,title:row.title||'Sem título',year:row.year,source_provider:row.source_provider,document_class:documentClass(row),routes:routes(row),domains:domains(row),bundle_id:bundle.id||null,result_kind:bundle.result_kind||'result_candidate',source_sentence_sha256:bundle.source_sentence_sha256||null,result_text:String(bundle.result_text||'').trim(),outcomes:cleanValues(bundle.outcomes),effect_measures:cleanValues(bundle.effect_measures),confidence_intervals:cleanValues(bundle.confidence_intervals),p_values:cleanValues(bundle.p_values),reference:bundle.reference||null,status:bundle.status||'machine_candidate_not_evidence_claim'}
}

function renderDomainOptions(){const domainsList=availableDomains();$('#reviewDomain').innerHTML=domainsList.map(domain=>`<option value="${esc(domain)}"${domain===state.domain?' selected':''}>${esc(DOMAIN_LABELS[domain]||domain)}</option>`).join('')||'<option value="">Nenhum domínio finding-ready</option>'}
function renderAnchorOptions(){const rows=state.findings;$('#anchorFinding').innerHTML=rows.map(item=>`<option value="${esc(item.document_id)}"${item.document_id===state.anchorId?' selected':''}>${esc(`${item.year||'s/ano'} · ${item.title}`)}</option>`).join('')||'<option value="">Nenhum achado disponível</option>'}
function metaChips(item){return [...(item.outcomes||[]).map(value=>`Outcome: ${value}`),...(item.effect_measures||[]),...(item.confidence_intervals||[]),...(item.p_values||[]),...(item.routes||[])].slice(0,8)}
function renderAnchor(){const item=state.findings.find(row=>row.document_id===state.anchorId);if(!item){$('#anchorCard').innerHTML='<div class="small-state">Nenhum achado âncora.</div>';return}$('#anchorCard').innerHTML=`<h3>${esc(item.title)}</h3><small>${esc([item.year,item.source_provider,CLASS_LABELS[item.document_class]||item.document_class].filter(Boolean).join(' · '))}</small><p class="anchor-quote">${esc(item.result_text)}</p><div class="anchor-meta">${metaChips(item).map(value=>`<span>${esc(value)}</span>`).join('')}</div><div class="small-state">${esc(item.status)} · source-linked result bundle</div>`}
function optionsHtml(options,current){return options.map(([value,label])=>`<option value="${esc(value)}"${value===current?' selected':''}>${esc(label)}</option>`).join('')}
function currentDecision(candidateId){return state.draft?.decisions?.[decisionId(state.anchorId,candidateId)]||null}

function renderQueue(){
  const anchor=state.findings.find(item=>item.document_id===state.anchorId);const candidates=state.findings.filter(item=>item.document_id!==state.anchorId);
  if(!anchor||!candidates.length){$('#comparisonState').textContent='São necessários pelo menos dois achados candidatos no lote atual.';$('#adjudicationQueue').innerHTML='';renderProgress();return}
  $('#comparisonState').textContent=`${fmt(candidates.length)} comparações disponíveis neste lote. Cada relação é julgamento humano explícito.`;
  $('#adjudicationQueue').innerHTML=candidates.map(item=>{const saved=currentDecision(item.document_id);const dims=saved?.comparability||{};return `<article class="adjudication-card${saved?' reviewed':''}" data-candidate-id="${esc(item.document_id)}"><div class="adjudication-head"><div><h3>${esc(item.title)}</h3><small>${esc([item.year,item.source_provider,CLASS_LABELS[item.document_class]||item.document_class].filter(Boolean).join(' · '))}</small></div>${saved?`<span class="relation-pill ${esc(saved.relation)}">${esc(saved.relation)}</span>`:'<span class="relation-pill">UNREVIEWED</span>'}</div><p class="candidate-quote">${esc(item.result_text)}</p><div class="dimension-grid"><label><span>População</span><select data-dimension="population">${optionsHtml(DIMENSION_OPTIONS,dims.population||'UNCLEAR')}</select></label><label><span>Construct / intervenção</span><select data-dimension="construct_intervention">${optionsHtml(DIMENSION_OPTIONS,dims.construct_intervention||'UNCLEAR')}</select></label><label><span>Outcome</span><select data-dimension="outcome">${optionsHtml(DIMENSION_OPTIONS,dims.outcome||'UNCLEAR')}</select></label><label><span>Tempo / follow-up</span><select data-dimension="timeframe">${optionsHtml(DIMENSION_OPTIONS,dims.timeframe||'UNCLEAR')}</select></label></div><div class="relation-grid"><label><span>Relação humana</span><select data-relation>${optionsHtml(RELATION_OPTIONS,saved?.relation||'')}</select></label><label><span>Justificativa do revisor</span><textarea data-rationale rows="3" maxlength="1200" placeholder="Explique por que os achados são convergentes, divergentes, complementares, não comparáveis ou incertos.">${esc(saved?.rationale||'')}</textarea></label></div><div class="adjudication-actions"><small data-save-state>${saved?`Salvo em ${esc(saved.reviewed_at||'data n/d')}`:'Revisor, relação e justificativa são obrigatórios.'}</small><button type="button" data-save-comparison>Salvar julgamento</button></div></article>`}).join('');renderProgress()
}

function reviewedDecisions(){return Object.values(state.draft?.decisions||{})}
function renderProgress(){const currentCandidates=state.findings.filter(item=>item.document_id!==state.anchorId);const ids=new Set(currentCandidates.map(item=>decisionId(state.anchorId,item.document_id)));const done=reviewedDecisions().filter(item=>ids.has(item.decision_id)).length;$('#reviewProgress').textContent=`${fmt(done)} / ${fmt(currentCandidates.length)}`}
function renderLedger(){const decisions=reviewedDecisions().sort((a,b)=>String(b.reviewed_at||'').localeCompare(String(a.reviewed_at||'')));$('#reviewLedger').innerHTML=decisions.length?decisions.map(item=>`<div class="ledger-row"><div><strong>${esc(item.anchor.title)}</strong><small>Âncora · ${esc(item.domain_label||item.domain)}</small></div><div><strong>${esc(item.candidate.title)}</strong><small>Comparado · ${esc(item.candidate.year||'s/ano')}</small></div><span class="relation-pill ${esc(item.relation)}">${esc(item.relation)}</span><div class="ledger-rationale">${esc(item.rationale)}<small>${esc(item.reviewed_at||'')} · ${esc(item.reviewer||'revisor não identificado')}</small></div></div>`).join(''):'<div class="empty-ledger">Nenhum julgamento humano salvo neste rascunho.</div>'}

function sourceSnapshot(item){return {document_id:item.document_id,title:item.title,year:item.year,source_provider:item.source_provider,document_class:item.document_class,routes:item.routes,bundle_id:item.bundle_id,result_kind:item.result_kind,source_sentence_sha256:item.source_sentence_sha256,result_text:item.result_text,outcomes:item.outcomes,effect_measures:item.effect_measures,confidence_intervals:item.confidence_intervals,p_values:item.p_values,status:item.status,reference:item.reference}}
function saveComparison(card){
  const candidateId=card.dataset.candidateId;const anchor=state.findings.find(item=>item.document_id===state.anchorId);const candidate=state.findings.find(item=>item.document_id===candidateId);if(!anchor||!candidate)return;
  const relation=card.querySelector('[data-relation]').value;const rationale=card.querySelector('[data-rationale]').value.trim();const statusNode=card.querySelector('[data-save-state]');const reviewer=(state.draft.reviewer||'').trim();
  if(!reviewer){statusNode.textContent='Informe o nome do revisor antes de salvar.';$('#reviewerName').focus();return}if(!relation){statusNode.textContent='Selecione a relação antes de salvar.';return}if(rationale.length<20){statusNode.textContent='Registre uma justificativa com pelo menos 20 caracteres.';return}
  const comparability={};card.querySelectorAll('[data-dimension]').forEach(select=>{comparability[select.dataset.dimension]=select.value});const id=decisionId(anchor.document_id,candidate.document_id);const reviewedAt=new Date().toISOString();
  state.draft.decisions[id]={decision_id:id,domain:state.domain,domain_label:DOMAIN_LABELS[state.domain]||state.domain,anchor:sourceSnapshot(anchor),candidate:sourceSnapshot(candidate),comparability,relation,rationale,reviewer,reviewed_at:reviewedAt,human_entered:true,canonical:false};saveDraft();renderQueue();renderLedger()
}

async function loadDomain(domain){
  const token=++state.loadingToken;state.domain=domain;state.findings=[];state.anchorId='';renderDomainOptions();$('#comparisonState').textContent='Carregando achados candidatos…';$('#adjudicationQueue').innerHTML='';
  const rows=domainRows(domain).sort((a,b)=>String(a.title||'').localeCompare(String(b.title||''))||String(a.document_id).localeCompare(String(b.document_id))).slice(0,DETAIL_BATCH_LIMIT);
  const details=await mapLimited(rows,DETAIL_CONCURRENCY,async row=>findingFromDetail(row,await detailFor(row.document_id)));if(token!==state.loadingToken)return;state.findings=details.filter(Boolean);state.anchorId=state.findings[0]?.document_id||'';renderAnchorOptions();renderAnchor();renderQueue();renderLedger();const params=new URLSearchParams(location.search);if(domain)params.set('domain',domain);history.replaceState(null,'',`${location.pathname}${params.toString()?`?${params}`:''}`)
}

function stableValue(value){if(Array.isArray(value))return value.map(stableValue);if(value&&typeof value==='object'){const out={};for(const key of Object.keys(value).sort())out[key]=stableValue(value[key]);return out}return value}
async function sha256(value){const bytes=new TextEncoder().encode(JSON.stringify(stableValue(value)));const digest=await crypto.subtle.digest('SHA-256',bytes);return [...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join('')}
async function exportDraft(){
  const reviewer=(state.draft.reviewer||'').trim();if(!reviewer){$('#reviewHealth').textContent='informe o revisor';$('#reviewHealth').className='status-pill bad';$('#reviewerName').focus();return}const decisions=reviewedDecisions();if(!decisions.length){$('#reviewHealth').textContent='nenhuma decisão';$('#reviewHealth').className='status-pill bad';return}
  const scientificContent={export_type:REVIEW_VERSION,canonical:false,search_id:state.search?.search_id||null,context_version:state.search?.context_version||null,question:state.search?.question||null,reviewer,decisions:decisions.sort((a,b)=>String(a.decision_id).localeCompare(String(b.decision_id))),guardrails:{human_entered_relations:true,automatic_convergence_divergence:false,accepted_evidence_claims_created:false,screening_decisions_created:false,risk_of_bias_assessed:false,certainty_assessed:false,prisma_event_emitted:false,formal_search_state_changed:false}};
  const contentSha256=await sha256(scientificContent);const payload={...scientificContent,content_sha256:contentSha256,generated_at:new Date().toISOString(),artifact_semantics:'Portable human synthesis-review draft. Export does not make the draft canonical.'};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=`nutev-human-synthesis-review-${contentSha256.slice(0,12)}.json`;document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);$('#reviewHealth').textContent='rascunho exportado';$('#reviewHealth').className='status-pill ok'
}

function clearDraft(){if(!window.confirm('Limpar todas as decisões locais deste contexto? O arquivo exportado, se existir, não será afetado.'))return;localStorage.removeItem(storageKey());state.draft=blankDraft();$('#reviewerName').value='';renderQueue();renderLedger();$('#reviewHealth').textContent='rascunho limpo';$('#reviewHealth').className='status-pill'}

function bindEvents(){
  $('#reviewDomain').addEventListener('change',event=>loadDomain(event.target.value));$('#anchorFinding').addEventListener('change',event=>{state.anchorId=event.target.value;renderAnchor();renderQueue()});$('#reviewerName').addEventListener('input',event=>{state.draft.reviewer=event.target.value;saveDraft()});$('#adjudicationQueue').addEventListener('click',event=>{const button=event.target.closest('[data-save-comparison]');if(button)saveComparison(button.closest('[data-candidate-id]'))});$('#exportReview').addEventListener('click',exportDraft);$('#clearReview').addEventListener('click',clearDraft)
}

async function init(){
  try{const [articles,search]=await Promise.all([fetchJsonl('/agent-context/article1/ARTICLE_SUMMARIES.jsonl'),fetchJson('/agent-context/article1/SEARCH_STATE.json')]);state.articles=articles;state.search=search;loadDraft();$('#reviewerName').value=state.draft.reviewer||'';$('#reviewQuestion').textContent=search.question||'Article 1 — contexto científico do NutEV';renderDomainOptions();bindEvents();$('#reviewState').className='hidden';$('#reviewContent').classList.remove('hidden');$('#reviewHealth').textContent='rascunho local';$('#reviewHealth').className='status-pill ok';const requested=new URLSearchParams(location.search).get('domain');const domainsList=availableDomains();const domain=domainsList.includes(requested)?requested:domainsList[0]||'';if(domain)await loadDomain(domain);else{$('#comparisonState').textContent='Nenhum domínio com result bundles materializados.';renderLedger()}}
  catch(error){$('#reviewState').className='error dashboard-state';$('#reviewState').innerHTML=`<strong>Synthesis Review indisponível.</strong><div>${esc(error.message)}</div>`;$('#reviewHealth').textContent='contexto indisponível';$('#reviewHealth').className='status-pill bad'}
}

init();
