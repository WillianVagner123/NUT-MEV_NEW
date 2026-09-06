const $=selector=>document.querySelector(selector);
const state={profiles:[],profile:null,localRuns:{},review:null};
const STORAGE_KEY='nutev_press_review:article1-scientific-closure-v1';

function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function nowDate(){return new Date().toISOString().slice(0,10)}
function downloadJson(filename,payload){const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}
async function fetchJson(url,options){const response=await fetch(url,options);const payload=await response.json();if(!response.ok)throw new Error(payload.message||payload.error||`HTTP ${response.status}`);return payload}
function strategyKey(strategy){return`${strategy.strategy_id}|${strategy.strategy_version}`}

async function loadProfile(){const payload=await fetchJson('./press-review-profiles.json',{cache:'no-store'});state.profiles=payload.profiles||[];if(!state.profiles.length)throw new Error('Nenhum perfil PRESS configurado.');state.profile=state.profiles[0]}

async function findLocalRuns(){
  state.localRuns={};
  let listing;
  try{listing=await fetchJson('/api/searches?limit=200',{cache:'no-store'})}catch(_error){return}
  const wanted=new Map((state.profile?.strategies||[]).map(strategy=>[strategyKey(strategy),strategy]));
  for(const item of listing.searches||[]){
    if(wanted.size===0)break;
    try{
      const run=await fetchJson(`/api/searches/${encodeURIComponent(item.search_id)}`,{cache:'no-store'});const plan=run.query_plan||{};const key=`${plan.strategy_id||''}|${plan.strategy_version||''}`;
      if(wanted.has(key)&&String(plan.run_class||'').toUpperCase()==='PILOT'&&!state.localRuns[key]){state.localRuns[key]=run;wanted.delete(key)}
    }catch(_error){/* persisted run may have been removed; keep scanning */}
  }
}

function localRunNote(strategy){
  const run=state.localRuns[strategyKey(strategy)];
  if(!run)return'<div class="press-warning">Nenhum run PILOT local correspondente foi localizado para esta versão. Isso não equivale a falha científica e não autoriza preencher contagens ou decisões por inferência.</div>';
  const provider=(run.providers||[]).find(item=>item.provider===strategy.provider);const details=provider?.search_details||{};const count=details.count??provider?.total_found??'—';const warnings=details.warninglist&&Object.keys(details.warninglist).length?Object.values(details.warninglist).flat().filter(Boolean).length:0;
  return `<div class="qa-state ok"><strong>Run PILOT local localizado.</strong> ${esc(run.search_id)} · count ${esc(count)} · ${warnings?`${warnings} warning(s)`:'sem warnings registrados'}.</div>`;
}

function evidenceMarkup(evidence){
  const count=evidence.count===undefined?'<span class="muted">não registrado</span>':Number(evidence.count).toLocaleString('pt-BR');
  const sentinel=evidence.sentinels_expected===undefined?'não registrado':`${evidence.sentinels_found}/${evidence.sentinels_expected}`;
  return `<div class="press-evidence"><div><span>PILOT count</span><strong>${count}</strong></div><div><span>Sentinelas</span><strong>${esc(sentinel)}</strong></div><div><span>Estado</span><strong>${esc(evidence.decision||'PENDING')}</strong></div></div>`;
}

function queryMarkup(strategy){
  if(strategy.query)return `<details><summary>Query provider-native exata</summary><code>${esc(strategy.query)}</code></details>`;
  return `<div class="press-warning"><strong>Query provider-native ainda não congelada.</strong> ${esc(strategy.query_note||'A string final depende do fechamento PRESS e da validação nativa por base.')}</div>`;
}

function renderPackage(){
  const profile=state.profile;$('#pressProfileState').className='qa-state ok';$('#pressProfileState').innerHTML=`Gate atual <strong>${esc(profile.gate_id)}</strong> · próximo gate <strong>${esc(profile.downstream_gate_id||'—')}</strong> · ${esc(profile.gate_status_before_review)}`;
  $('#pressPackage').innerHTML=`<div class="press-package-grid">${profile.strategies.map(strategy=>{
    const evidence=strategy.pilot_evidence||{};
    return `<article class="press-strategy"><h3>${esc(strategy.strategy_id)} <span class="muted">${esc(strategy.strategy_version)}</span></h3><div class="press-meta">${esc(strategy.role)} · ${esc(strategy.status)}</div>${evidenceMarkup(evidence)}${localRunNote(strategy)}<details><summary>Racional / histórico</summary><ul class="press-history">${(strategy.version_history||[]).map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details>${queryMarkup(strategy)}</article>`
  }).join('')}</div><div class="press-warning"><strong>Guardrail:</strong> ${esc(profile.freeze_guardrail)}</div>`;
  $('#downloadPackageBtn').disabled=false;
}

function renderChecklist(){
  const root=$('#pressChecklist');root.innerHTML=state.profile.checklist.map(item=>`<div class="press-check-item" data-id="${esc(item.id)}"><div class="press-check-head"><span class="press-check-id">${esc(item.id)}</span><div>${esc(item.label)}</div><select class="press-item-verdict" aria-label="Conclusão ${esc(item.id)}"><option value="">— concluir —</option><option value="OK">Adequado</option><option value="MINOR">Observação não material</option><option value="MATERIAL">Alteração material necessária</option><option value="NA">Não aplicável</option></select></div><textarea class="press-item-comment" rows="3" placeholder="Observação do revisor para ${esc(item.id)}"></textarea></div>`).join('');
}

function populateDecisionOptions(){const select=$('#pressDecision');select.innerHTML='<option value="">— decisão final —</option>';for(const option of state.profile.decision_options||[]){const node=document.createElement('option');node.value=option.value;node.textContent=option.label;select.appendChild(node)}}

function packagePayload(){return{schema_version:2,created_at:new Date().toISOString(),profile_id:state.profile.profile_id,gate_id:state.profile.gate_id,downstream_gate_id:state.profile.downstream_gate_id,source_search_master:state.profile.source_search_master,source_query_draft:state.profile.source_query_draft,source_press_record:state.profile.source_press_record,review_title:state.profile.review_title,reviewer_requirement:state.profile.reviewer_requirement,freeze_guardrail:state.profile.freeze_guardrail,strategies:state.profile.strategies.map(strategy=>({...strategy,local_web_run:state.localRuns[strategyKey(strategy)]?.search_id||null})),checklist:state.profile.checklist,decision_options:state.profile.decision_options}}

function collectReview(){
  const checklist=[...document.querySelectorAll('.press-check-item')].map(node=>({id:node.dataset.id,verdict:node.querySelector('.press-item-verdict').value,comment:node.querySelector('.press-item-comment').value.trim()}));
  return{schema_version:2,created_at:new Date().toISOString(),profile_id:state.profile.profile_id,gate_id:state.profile.gate_id,downstream_gate_id:state.profile.downstream_gate_id,reviewer:{name:$('#reviewerName').value.trim(),affiliation:$('#reviewerAffiliation').value.trim(),email:$('#reviewerEmail').value.trim(),review_date:$('#reviewDate').value,independent_attestation:$('#independentAttestation').checked},checklist,decision:$('#pressDecision').value,affected_strategy:$('#affectedStrategy').value,final_comments:$('#finalComments').value.trim(),suggested_changes:$('#suggestedChanges').value.trim()}
}

function evaluateReview(review){
  const missing=[];if(!review.reviewer.name)missing.push('nome do revisor');if(!review.reviewer.affiliation)missing.push('instituição/vínculo');if(!review.reviewer.review_date)missing.push('data da revisão');if(!review.reviewer.independent_attestation)missing.push('declaração de independência');
  const unresolved=review.checklist.filter(item=>!item.verdict).map(item=>item.id);if(unresolved.length)missing.push(`checklist sem conclusão: ${unresolved.join(', ')}`);if(!review.decision)missing.push('decisão final');
  if(missing.length)return{status:'INCOMPLETE',gate_result:'PRESS_IN_REVIEW',freeze_authorized:false,gf10_authorized:false,css:'press-gate-pending',title:'PRESS ainda incompleto',details:missing.join(' · ')};
  const materialItems=review.checklist.filter(item=>item.verdict==='MATERIAL').map(item=>item.id);const materialDecision=review.decision==='MATERIAL_REVISION';
  if(materialItems.length||materialDecision)return{status:'COMPLETE',gate_result:'REVISION_REQUIRED',freeze_authorized:false,gf10_authorized:false,css:'press-gate-return',title:'Alteração material — revisão necessária',details:`PRESS não pode ser registrado como PASS. ${materialItems.length?`Itens materiais: ${materialItems.join(', ')}. `:''}Atualize a estratégia, repita os testes afetados e submeta nova revisão.`};
  if(review.decision==='REJECT')return{status:'COMPLETE',gate_result:'PRESS_FAIL',freeze_authorized:false,gf10_authorized:false,css:'press-gate-block',title:'PRESS não aprovado',details:'PRESS permanece FAIL. GF-10, query freeze, busca formal e PRISMA continuam bloqueados.'};
  if(['ACCEPT','ACCEPT_MINOR'].includes(review.decision))return{status:'COMPLETE',gate_result:'PRESS_REVIEW_COMPLETE_PENDING_CANONICAL_REGISTRATION',freeze_authorized:false,gf10_authorized:false,css:'press-gate-ready',title:'Parecer PRESS concluído — ainda não é GF-10',details:'O parecer humano pode ser incorporado ao registro canônico. Antes de GF-10 ainda é obrigatório fechar os delta tests, decidir C4, validar sintaxe provider-native, known-item/sentinels e tradução entre bases.'};
  return{status:'INCOMPLETE',gate_result:'PRESS_IN_REVIEW',freeze_authorized:false,gf10_authorized:false,css:'press-gate-pending',title:'PRESS pendente',details:'Selecione uma decisão final válida.'}
}

function renderGate(result){const root=$('#pressGate');root.className=`qa-state ${result.css}`;root.innerHTML=`<div class="press-gate-title">${esc(result.title)}</div><div class="press-gate-details">${esc(result.details)}</div>`;$('#downloadReviewBtn').disabled=result.status!=='COMPLETE'}
function saveDraft(review){localStorage.setItem(STORAGE_KEY,JSON.stringify(review))}
function restoreDraft(){let review;try{review=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null')}catch(_error){return}if(!review)return;$('#reviewerName').value=review.reviewer?.name||'';$('#reviewerAffiliation').value=review.reviewer?.affiliation||'';$('#reviewerEmail').value=review.reviewer?.email||'';$('#reviewDate').value=review.reviewer?.review_date||nowDate();$('#independentAttestation').checked=Boolean(review.reviewer?.independent_attestation);for(const item of review.checklist||[]){const node=document.querySelector(`.press-check-item[data-id="${CSS.escape(item.id)}"]`);if(node){node.querySelector('.press-item-verdict').value=item.verdict||'';node.querySelector('.press-item-comment').value=item.comment||''}}$('#pressDecision').value=review.decision||'';$('#affectedStrategy').value=review.affected_strategy||'NONE';$('#finalComments').value=review.final_comments||'';$('#suggestedChanges').value=review.suggested_changes||''}

async function refresh(){
  $('#pressHealth').textContent='carregando…';$('#pressHealth').className='status-pill';$('#downloadPackageBtn').disabled=true;$('#downloadReviewBtn').disabled=true;
  try{await loadProfile();await findLocalRuns();renderPackage();renderChecklist();populateDecisionOptions();if(!$('#reviewDate').value)$('#reviewDate').value=nowDate();restoreDraft();$('#pressHealth').textContent='pronto';$('#pressHealth').className='status-pill ok'}catch(error){$('#pressProfileState').className='qa-state bad';$('#pressProfileState').textContent=`Falha: ${error.message}`;$('#pressHealth').textContent='falha';$('#pressHealth').className='status-pill bad'}
}

$('#refreshPress').onclick=()=>location.reload();
$('#downloadPackageBtn').onclick=()=>downloadJson(`PRESS_PACKAGE_${state.profile.profile_id}.json`,packagePayload());
$('#evaluatePressBtn').onclick=()=>{const review=collectReview();const result=evaluateReview(review);review.gate_evaluation=result;review.freeze_authorized=false;review.gf10_authorized=false;review.strategies_reviewed=(state.profile.strategies||[]).map(strategy=>({strategy_id:strategy.strategy_id,strategy_version:strategy.strategy_version}));state.review=review;saveDraft(review);renderGate(result)};
$('#downloadReviewBtn').onclick=()=>{if(!state.review)return;downloadJson(`PRESS_REVIEW_${state.profile.profile_id}_${state.review.reviewer.review_date||nowDate()}.json`,state.review)};

refresh();
