const STAGE_OPERATION='STAGE_CLAIM_EVALUATION';
const FINALIZE_OPERATION='FINALIZE_CLAIM_EVALUATION';
const CANDIDATE_TYPE='NUTEV_CLAIM_EVALUATION_CANDIDATE_V1';
const EVALUATION_RECORD_TYPE='NUTEV_CANONICAL_CLAIM_EVALUATION_RECORD_V1';
let state=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>24?`${text.slice(0,12)}…${text.slice(-8)}`:text||'—'};
const titleCase=value=>String(value||'').replaceAll('_',' ').replace(/\b\w/g,ch=>ch.toUpperCase());

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

function acceptedClaims(){return Array.isArray(state?.accepted_evidence_claims)?state.accepted_evidence_claims:[];}
function candidates(){return Array.isArray(state?.claim_evaluation_candidates)?state.claim_evaluation_candidates:[];}
function finalized(){return Array.isArray(state?.finalized_claim_evaluations)?state.finalized_claim_evaluations:[];}
function dimensions(){return state?.claim_evaluation_dimensions||{};}
function judgments(){return Array.isArray(state?.claim_evaluation_judgment_scale)?state.claim_evaluation_judgment_scale:[];}
function basisOptions(){return Array.isArray(state?.claim_evaluation_assessment_basis_options)?state.claim_evaluation_assessment_basis_options:[];}

function mergeEvaluationResult(result){
  state={
    ...state,
    claim_evaluation_method:result.appraisal_method,
    claim_evaluation_candidate_type:result.evaluation_candidate_type,
    claim_evaluation_record_type:result.canonical_evaluation_record_type,
    claim_evaluation_dimensions:result.dimensions,
    claim_evaluation_judgment_scale:result.judgment_scale,
    claim_evaluation_assessment_basis_options:result.assessment_basis_options,
    claim_evaluation_candidate_count:result.candidate_count,
    claim_evaluation_candidate_counts:result.candidate_counts,
    claim_evaluation_candidates:result.candidates,
    finalized_claim_evaluation_count:result.finalized_evaluation_count,
    finalized_claim_evaluations:result.finalized_evaluations,
  };
}

function renderKpis(){
  const counts=state?.claim_evaluation_candidate_counts||{};
  $('appraisalKpis').innerHTML=[
    ['Accepted claims',state?.accepted_evidence_claim_count??0,'Source-level EvidenceClaims eligible for appraisal'],
    ['Appraisal queue',state?.claim_evaluation_candidate_count??0,'No aggregate score is calculated'],
    ['Pending',counts.PENDING_APPRAISAL??0,'Human dimensions not finalized'],
    ['Finalized',state?.finalized_claim_evaluation_count??0,'Canonical appraisal records only'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderClaimSelect(){
  const select=$('appraisalClaim');
  const selected=select.value;
  const staged=new Set(candidates().map(item=>item.claim_id));
  const claims=acceptedClaims().filter(claim=>!staged.has(claim.claim_id));
  select.innerHTML='<option value="">Selecione um claim aceito</option>'+claims.map(claim=>`<option value="${esc(claim.claim_id)}">${esc(claim.claim_id)} · ${esc(String(claim.statement||'').slice(0,100))}</option>`).join('');
  if(claims.some(claim=>claim.claim_id===selected))select.value=selected;
  validateStage();
}

function validateStage(){
  $('stageAppraisal').disabled=!($('appraisalClaim').value&&$('appraisalStagedBy').value.trim());
}

function judgmentOptions(){
  return '<option value="">Selecione</option>'+judgments().map(value=>`<option value="${esc(value)}">${esc(value)}</option>`).join('');
}

function basisSelect(){
  return '<option value="">Selecione</option>'+basisOptions().map(value=>`<option value="${esc(value)}">${esc(value)}</option>`).join('');
}

function dimensionCards(){
  return Object.entries(dimensions()).map(([key,definition])=>`<article class="dimension-card" data-dimension="${esc(key)}"><h4>${esc(titleCase(key))}</h4><p>${esc(definition)}</p><select data-field="judgment">${judgmentOptions()}</select><textarea data-field="rationale" rows="3" maxlength="1200" placeholder="Justificativa humana para esta dimensão (mínimo 15 caracteres)."></textarea></article>`).join('');
}

function appraisalCard(candidate){
  const claim=candidate.claim_snapshot||{};
  const source=candidate.source_snapshot||{};
  const final=candidate.status==='FINALIZED';
  return `<article class="appraisal-card" data-candidate-id="${esc(candidate.candidate_id)}">
    <div class="appraisal-card-head"><div><h3>${esc(claim.statement||candidate.claim_id)}</h3><p>${esc(candidate.claim_id)} · ${esc(candidate.evidence_record_id)} · context ${esc(short(candidate.source_context_fingerprint))}</p></div><span class="appraisal-pill ${final?'ok':''}">${esc(candidate.status)}</span></div>
    <div class="appraisal-source-grid">
      <div class="appraisal-claim"><span>Accepted EvidenceClaim</span><blockquote>${esc(claim.statement||'')}</blockquote><p><small>Accepted by ${esc(claim.accepted_by||'unknown label')} · acceptance remains distinct from appraisal.</small></p></div>
      <div class="appraisal-source"><span>Source-linked result snapshot</span><blockquote>${esc(source.result_text||'')}</blockquote><p><small>${esc(source.document_id||'')} · ${esc(source.citation_id||'')} · bundle ${esc(source.bundle_id||'')}</small></p></div>
    </div>
    ${final?`<div class="appraisal-final">Canonical ClaimEvaluation: ${esc(candidate.canonical_claim_evaluation_id||'—')}. This does not create formal RoB, certainty, EvidenceSet or recommendation.</div>`:`<div class="appraisal-form">
      <div class="appraisal-meta-grid">
        <label><span>Assessor</span><input data-field="assessor" type="text" maxlength="120" placeholder="Nome do assessor"></label>
        <label><span>Assessment basis</span><select data-field="assessment_basis">${basisSelect()}</select></label>
        <label><span>Basis details (required only for OTHER)</span><input data-field="basis_details" type="text" maxlength="400" placeholder="Descreva o material adicional utilizado"></label>
        <label><span>Overall rationale</span><textarea data-field="overall_rationale" rows="3" maxlength="1800" placeholder="Síntese do raciocínio do appraisal (mínimo 30 caracteres)."></textarea></label>
      </div>
      <div class="dimension-grid">${dimensionCards()}</div>
      <div class="appraisal-confirmations">
        <label><input data-field="nonformal_method_confirmed" type="checkbox"><span>Confirmo que este appraisal genérico não é RoB 2, ROBINS-I, GRADE nem outro instrumento externo validado.</span></label>
        <label><input data-field="claim_scope_confirmed" type="checkbox"><span>Confirmo que os julgamentos se aplicam a este claim; não estou classificando automaticamente o estudo inteiro.</span></label>
        <label><input data-field="scientific_boundary_confirmed" type="checkbox"><span>Confirmo que ClaimEvaluation não equivale a certainty, EvidenceSet synthesis, recomendação, meta-analysis ou PRISMA.</span></label>
      </div>
      <div class="appraisal-actions"><button type="button" data-action="FINALIZE">Finalize human appraisal</button></div>
    </div>`}
  </article>`;
}

function renderCandidates(){
  const filter=$('appraisalStatusFilter').value;
  const rows=candidates().filter(candidate=>filter==='ALL'||candidate.status===filter);
  $('appraisalCandidates').innerHTML=rows.length?rows.map(appraisalCard).join(''):'<div class="small-empty">Nenhum ClaimEvaluation candidate para este filtro.</div>';
}

function renderFinalized(){
  const rows=finalized();
  $('finalizedAppraisals').innerHTML=rows.length?rows.map(item=>`<article class="finalized-card"><h3>${esc(item.evaluation_id)} · ${esc(item.claim_id)}</h3><div class="finalized-meta"><span>Assessor: ${esc(item.assessor||'—')}</span><span>Basis: ${esc(item.assessment_basis||'—')}</span><span>Formal RoB: ${item.formal_risk_of_bias_assessed?'YES':'NO'}</span><span>Certainty: ${item.certainty_assessed?'YES':'NO'}</span></div><div class="finalized-dimensions">${Object.entries(item.dimensions||{}).map(([key,value])=>`<div><span>${esc(titleCase(key))}</span><strong>${esc(value?.judgment||'—')}</strong></div>`).join('')}</div><p>${esc(item.rationale||'')}</p></article>`).join(''):'<div class="small-empty">Nenhum ClaimEvaluation finalizado ainda.</div>';
}

function render(){renderKpis();renderClaimSelect();renderCandidates();renderFinalized();}

async function stage(){
  const claimId=$('appraisalClaim').value;
  const stagedBy=$('appraisalStagedBy').value.trim();
  if(!claimId||!stagedBy)return;
  $('stageAppraisal').disabled=true;
  $('stageAppraisalState').textContent='Revalidando EvidenceClaim, EvidenceRecord e provenance…';
  try{
    const result=await postJson({operation:STAGE_OPERATION,claim_id:claimId,staged_by:stagedBy});
    if(result?.evaluation_candidate_type!==CANDIDATE_TYPE)throw new Error('ClaimEvaluation candidate contract inválido.');
    mergeEvaluationResult(result);
    $('stageAppraisalState').textContent='Appraisal staged. Nenhuma avaliação foi finalizada automaticamente.';
    render();
  }catch(error){$('stageAppraisalState').textContent=`Bloqueado: ${error.message}`;}finally{validateStage();}
}

function field(card,name){const el=card.querySelector(`[data-field="${name}"]`);return el?.type==='checkbox'?Boolean(el.checked):String(el?.value||'').trim();}

function dimensionPayload(card){
  const result={};
  for(const block of card.querySelectorAll('[data-dimension]')){
    const key=block.dataset.dimension;
    result[key]={judgment:String(block.querySelector('[data-field="judgment"]')?.value||'').trim(),rationale:String(block.querySelector('[data-field="rationale"]')?.value||'').trim()};
  }
  return result;
}

async function finalizeAppraisal(card){
  const assessor=field(card,'assessor');
  const basis=field(card,'assessment_basis');
  const overall=field(card,'overall_rationale');
  const dims=dimensionPayload(card);
  if(!assessor){alert('Informe o assessor.');return;}
  if(!basis){alert('Selecione o assessment basis.');return;}
  if(basis==='OTHER'&&field(card,'basis_details').length<10){alert('Descreva o assessment basis OTHER.');return;}
  if(overall.length<30){alert('A rationale geral precisa ter pelo menos 30 caracteres.');return;}
  for(const [key,value] of Object.entries(dims)){
    if(!value.judgment){alert(`Selecione o julgamento de ${titleCase(key)}.`);return;}
    if(value.rationale.length<15){alert(`A justificativa de ${titleCase(key)} precisa ter pelo menos 15 caracteres.`);return;}
  }
  if(!field(card,'nonformal_method_confirmed')||!field(card,'claim_scope_confirmed')||!field(card,'scientific_boundary_confirmed')){alert('Confirme as três fronteiras científicas antes de finalizar.');return;}
  const button=card.querySelector('[data-action="FINALIZE"]');
  button.disabled=true;
  try{
    const result=await postJson({operation:FINALIZE_OPERATION,candidate_id:card.dataset.candidateId,assessor,rationale:overall,assessment_basis:basis,basis_details:field(card,'basis_details'),dimensions:dims,nonformal_method_confirmed:field(card,'nonformal_method_confirmed'),claim_scope_confirmed:field(card,'claim_scope_confirmed'),scientific_boundary_confirmed:field(card,'scientific_boundary_confirmed')});
    if(result?.canonical_evaluation_record_type!==EVALUATION_RECORD_TYPE)throw new Error('Canonical ClaimEvaluation contract inválido.');
    mergeEvaluationResult(result);
    render();
  }catch(error){alert(`Finalização bloqueada: ${error.message}`);button.disabled=false;}
}

async function load(){
  $('appraisalHealth').textContent='verificando…';
  $('appraisalState').classList.remove('hidden');
  $('appraisalContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('appraisalState').classList.add('hidden');
    $('appraisalContent').classList.remove('hidden');
    $('appraisalHealth').textContent='local appraisal conectado';
  }catch(error){$('appraisalHealth').textContent='local-only / indisponível';$('appraisalState').textContent=`ClaimEvaluation indisponível neste navegador: ${error.message}`;}
}

$('appraisalClaim').addEventListener('change',validateStage);
$('appraisalStagedBy').addEventListener('input',validateStage);
$('stageAppraisal').addEventListener('click',stage);
$('appraisalStatusFilter').addEventListener('change',renderCandidates);
$('appraisalCandidates').addEventListener('click',event=>{const button=event.target.closest('[data-action="FINALIZE"]');if(!button)return;const card=button.closest('.appraisal-card');if(card)finalizeAppraisal(card);});
$('refreshAppraisal').addEventListener('click',load);
load();
