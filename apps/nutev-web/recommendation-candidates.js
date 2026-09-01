const STAGE_OPERATION='STAGE_RECOMMENDATION_CANDIDATE';
const FINALIZE_OPERATION='FINALIZE_RECOMMENDATION_CANDIDATE';
const DRAFT_TYPE='NUTEV_RECOMMENDATION_CANDIDATE_DRAFT_V1';
const RECORD_TYPE='NUTEV_CANONICAL_RECOMMENDATION_CANDIDATE_RECORD_V1';
let state=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

async function getJson(url){
  const response=await fetch(url,{headers:{Accept:'application/json'},cache:'no-store'});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message||data.error||`HTTP ${response.status}`);
  return data;
}

async function postJson(payload){
  const response=await fetch('/api/synthesis/releases/prepare',{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(payload)});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message||data.error||`HTTP ${response.status}`);
  return data;
}

function finalizedSets(){return Array.isArray(state?.finalized_evidence_sets)?state.finalized_evidence_sets:[];}
function drafts(){return Array.isArray(state?.recommendation_candidate_drafts)?state.recommendation_candidate_drafts:[];}
function finalizedCandidates(){return Array.isArray(state?.finalized_recommendation_candidates)?state.finalized_recommendation_candidates:[];}
function selectedSetIds(){return [...document.querySelectorAll('[data-recommendation-set]:checked')].map(input=>input.value);}

function renderKpis(){
  const counts=state?.recommendation_candidate_draft_counts||{};
  $('recommendationKpis').innerHTML=[
    ['EvidenceSets',finalizedSets().length,'Finalized sets available for manual selection'],
    ['Drafts',state?.recommendation_candidate_draft_count??0,'Candidate drafts only'],
    ['Pending',counts.DRAFT??0,'Still not validated recommendations'],
    ['Finalized',state?.finalized_recommendation_candidate_count??0,'Canonical candidate records'],
    ['Readiness',state?.recommendation_candidate_readiness_default||'not_evaluated','Never inferred automatically'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderSets(){
  const rows=finalizedSets();
  $('recommendationEvidenceSets').innerHTML=rows.length?rows.map(item=>`<label class="recommendation-set">
    <input type="checkbox" data-recommendation-set value="${esc(item.evidence_set_id)}">
    <div><h3>${esc(item.name||item.evidence_set_id)}</h3><div class="recommendation-meta"><span>${esc(item.evidence_set_id)}</span><span>lens: ${esc(item.lens||'—')}</span><span>${esc(item.claim_count??0)} claim(s)</span><span>existing candidates: ${esc(item.recommendation_candidate_count??0)}</span></div><p>${esc(item.focus_statement||'')}</p></div>
  </label>`).join(''):'<div class="small-empty">Nenhum EvidenceSet finalizado disponível.</div>';
}

function finalizeForm(draft){
  return `<div class="recommendation-finalize">
    <label class="recommendation-field"><span>Finalizer</span><input data-finalize-field="finalizer" maxlength="120" placeholder="Nome de quem concluiu o candidate record"></label>
    <label class="recommendation-field"><span>Finalization rationale</span><textarea data-finalize-field="finalization_rationale" rows="3" maxlength="1600" placeholder="Por que este candidato está completo para seguir à HumanValidation?"></textarea></label>
    <div class="recommendation-confirmations">
      <label><input data-finalize-field="evidence_sets_are_not_certainty_confirmed" type="checkbox"><span>Confirmo que EvidenceSet membership/count não equivale a certainty, consensus ou evidence strength.</span></label>
      <label><input data-finalize-field="candidate_is_not_validated_recommendation_confirmed" type="checkbox"><span>Confirmo que este RecommendationCandidate ainda não é recomendação validada.</span></label>
      <label><input data-finalize-field="human_validation_required_confirmed" type="checkbox"><span>Confirmo que uma HumanValidation explícita será necessária antes de qualquer recomendação aceita.</span></label>
    </div>
    <button type="button" data-finalize-recommendation="${esc(draft.draft_id)}">Finalize candidate record</button>
  </div>`;
}

function renderDrafts(){
  const rows=drafts();
  $('recommendationDrafts').innerHTML=rows.length?rows.map(draft=>`<article class="recommendation-draft" data-draft-id="${esc(draft.draft_id)}">
    <div class="recommendation-draft-head"><div><h3>${esc(draft.statement||draft.draft_id)}</h3><div class="recommendation-meta"><span>${esc(draft.draft_id)}</span><span>${esc(draft.evidence_set_count??0)} EvidenceSet(s)</span><span>readiness: ${esc(draft.readiness||'not_evaluated')}</span></div></div><span class="recommendation-pill ${draft.status==='FINALIZED'?'ok':''}">${esc(draft.status)}</span></div>
    <p>${esc(draft.rationale||'')}</p>
    <div class="recommendation-meta"><span>audience: ${esc(draft.intended_audience||'—')}</span><span>context: ${esc(draft.intended_context||'—')}</span></div>
    ${draft.status==='DRAFT'?finalizeForm(draft):'<p><strong>Candidate record finalizado.</strong> Continua aguardando HumanValidation; readiness não foi avaliado.</p>'}
  </article>`).join(''):'<div class="small-empty">Nenhum RecommendationCandidate draft.</div>';
}

function renderFinalized(){
  const rows=finalizedCandidates();
  $('finalizedRecommendations').innerHTML=rows.length?rows.map(item=>`<article class="finalized-recommendation">
    <div class="finalized-recommendation-head"><div><h3>${esc(item.statement||item.recommendation_candidate_id)}</h3><div class="recommendation-meta"><span>${esc(item.recommendation_candidate_id)}</span><span>${esc(item.evidence_set_count??0)} EvidenceSet(s)</span><span>readiness: ${esc(item.readiness||'not_evaluated')}</span></div></div><span class="recommendation-pill">candidate only</span></div>
    <p>${esc(item.rationale||'')}</p><div class="recommendation-meta"><span>validated recommendation: ${item.recommendation_validated?'YES':'NO'}</span><span>clinical recommendation created: ${item.clinical_recommendation_created?'YES':'NO'}</span><span>HumanValidation: ${esc(item.human_validation_status||'NOT_STAGED')}</span><span>decision: ${esc(item.human_validation_decision||'—')}</span><span>finalizer: ${esc(item.finalizer||'—')}</span></div>
  </article>`).join(''):'<div class="small-empty">Nenhum RecommendationCandidate finalizado.</div>';
}

function validateStage(){
  const ready=selectedSetIds().length>0&&$('recommendationStatement').value.trim().length>=30&&$('recommendationRationale').value.trim().length>=30&&$('recommendationAudience').value.trim().length>=3&&$('recommendationContext').value.trim().length>=10&&$('recommendationStagedBy').value.trim()&&$('humanAuthorship').checked;
  $('stageRecommendation').disabled=!ready;
}

function render(){renderKpis();renderSets();renderDrafts();renderFinalized();validateStage();}

async function stage(){
  const payload={
    operation:STAGE_OPERATION,
    statement:$('recommendationStatement').value.trim(),
    rationale:$('recommendationRationale').value.trim(),
    intended_audience:$('recommendationAudience').value.trim(),
    intended_context:$('recommendationContext').value.trim(),
    staged_by:$('recommendationStagedBy').value.trim(),
    evidence_set_ids:selectedSetIds(),
    statement_human_authored_confirmed:$('humanAuthorship').checked,
  };
  $('stageRecommendation').disabled=true;
  $('stageRecommendationState').textContent='Revalidando EvidenceSets e criando candidate draft…';
  try{
    const result=await postJson(payload);
    if(result?.draft_type!==DRAFT_TYPE)throw new Error('RecommendationCandidate draft contract inválido.');
    state={...state,recommendation_candidate_draft_type:result.draft_type,recommendation_candidate_record_type:result.canonical_recommendation_candidate_record_type,recommendation_candidate_readiness_default:result.readiness_default,recommendation_candidate_draft_count:result.draft_count,recommendation_candidate_draft_counts:result.draft_counts,recommendation_candidate_drafts:result.drafts,finalized_recommendation_candidate_count:result.finalized_recommendation_candidate_count,finalized_recommendation_candidates:result.finalized_recommendation_candidates};
    $('stageRecommendationState').textContent='Draft staged. Nenhuma recomendação foi validada e readiness permanece not_evaluated.';
    render();
  }catch(error){$('stageRecommendationState').textContent=`Bloqueado: ${error.message}`;}finally{validateStage();}
}

function finalizeField(card,name){const el=card.querySelector(`[data-finalize-field="${name}"]`);return el?.type==='checkbox'?Boolean(el.checked):String(el?.value||'').trim();}

async function finalizeCandidate(card,draftId){
  const finalizer=finalizeField(card,'finalizer');
  const finalizationRationale=finalizeField(card,'finalization_rationale');
  if(!finalizer){alert('Informe o finalizer.');return;}
  if(finalizationRationale.length<30){alert('A finalization rationale precisa ter pelo menos 30 caracteres.');return;}
  if(!finalizeField(card,'evidence_sets_are_not_certainty_confirmed')||!finalizeField(card,'candidate_is_not_validated_recommendation_confirmed')||!finalizeField(card,'human_validation_required_confirmed')){alert('Confirme as três fronteiras científicas antes de finalizar.');return;}
  const button=card.querySelector('[data-finalize-recommendation]');
  if(button)button.disabled=true;
  try{
    const result=await postJson({operation:FINALIZE_OPERATION,draft_id:draftId,finalizer,finalization_rationale:finalizationRationale,evidence_sets_are_not_certainty_confirmed:finalizeField(card,'evidence_sets_are_not_certainty_confirmed'),candidate_is_not_validated_recommendation_confirmed:finalizeField(card,'candidate_is_not_validated_recommendation_confirmed'),human_validation_required_confirmed:finalizeField(card,'human_validation_required_confirmed')});
    if(result?.canonical_recommendation_candidate_record_type!==RECORD_TYPE)throw new Error('RecommendationCandidate record contract inválido.');
    state={...state,recommendation_candidate_draft_count:result.draft_count,recommendation_candidate_draft_counts:result.draft_counts,recommendation_candidate_drafts:result.drafts,finalized_recommendation_candidate_count:result.finalized_recommendation_candidate_count,finalized_recommendation_candidates:result.finalized_recommendation_candidates};
    render();
  }catch(error){alert(`Finalização bloqueada: ${error.message}`);if(button)button.disabled=false;}
}

async function load(){
  $('recommendationHealth').textContent='verificando…';
  $('recommendationState').classList.remove('hidden');
  $('recommendationContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('recommendationState').classList.add('hidden');
    $('recommendationContent').classList.remove('hidden');
    $('recommendationHealth').textContent='local candidate gate conectado';
  }catch(error){$('recommendationHealth').textContent='local-only / indisponível';$('recommendationState').textContent=`RecommendationCandidate indisponível neste navegador: ${error.message}`;}
}

for(const id of ['recommendationStatement','recommendationRationale','recommendationAudience','recommendationContext','recommendationStagedBy','humanAuthorship'])$(id).addEventListener('input',validateStage);
$('recommendationEvidenceSets').addEventListener('change',validateStage);
$('stageRecommendation').addEventListener('click',stage);
$('recommendationDrafts').addEventListener('click',event=>{const button=event.target.closest('[data-finalize-recommendation]');if(!button)return;const card=button.closest('.recommendation-draft');if(card)finalizeCandidate(card,button.dataset.finalizeRecommendation);});
$('refreshRecommendations').addEventListener('click',load);
load();
