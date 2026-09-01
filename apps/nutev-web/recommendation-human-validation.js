const STAGE_OPERATION='STAGE_RECOMMENDATION_HUMAN_VALIDATION';
const DECIDE_OPERATION='DECIDE_RECOMMENDATION_HUMAN_VALIDATION';
const CASE_TYPE='NUTEV_RECOMMENDATION_HUMAN_VALIDATION_CASE_V1';
const RECORD_TYPE='NUTEV_CANONICAL_HUMAN_VALIDATION_RECORD_V1';
let state=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>30?`${text.slice(0,15)}…${text.slice(-10)}`:text||'—'};

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

function candidates(){return Array.isArray(state?.finalized_recommendation_candidates)?state.finalized_recommendation_candidates:[];}
function cases(){return Array.isArray(state?.recommendation_human_validation_cases)?state.recommendation_human_validation_cases:[];}
function finalized(){return Array.isArray(state?.finalized_recommendation_human_validations)?state.finalized_recommendation_human_validations:[];}

function renderKpis(){
  const counts=state?.recommendation_human_validation_counts||{};
  $('validationKpis').innerHTML=[
    ['Candidates',candidates().length,'Finalized RecommendationCandidates'],
    ['Pending',counts.PENDING??0,'Awaiting explicit human decision'],
    ['Accepted',counts.ACCEPT??0,'Declared scope only'],
    ['Rejected / Revise',(counts.REJECT??0)+(counts.REVISE??0),'No upstream mutation'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function stageCard(item){
  const status=item.human_validation_status||'NOT_STAGED';
  const canStage=status==='NOT_STAGED';
  return `<article class="validation-candidate" data-candidate-id="${esc(item.recommendation_candidate_id)}">
    <div class="validation-card-head"><div><h3>${esc(item.statement||item.recommendation_candidate_id)}</h3><p>${esc(item.recommendation_candidate_id)} · ${esc(item.evidence_set_count??0)} EvidenceSet(s) · readiness=${esc(item.readiness||'not_evaluated')}</p></div><span class="validation-pill">${esc(status)}</span></div>
    <p><strong>Audience:</strong> ${esc(item.intended_audience||'—')} · <strong>Context:</strong> ${esc(item.intended_context||'—')}</p>
    ${canStage?`<div class="validation-stage-form">
      <label class="validation-field"><span>Review scope</span><textarea data-stage-field="scope" rows="3" maxlength="1400" placeholder="Defina o escopo exato da decisão humana. Não use certainty/GRADE ou recomendação clínica como atalho."></textarea></label>
      <label class="validation-field"><span>Staged by</span><input data-stage-field="stagedBy" maxlength="120" placeholder="Nome de quem abriu o caso"></label>
      <button type="button" data-stage-validation>Open PENDING HumanValidation</button>
    </div>`:`<div class="small-state">HumanValidation ${esc(status)} · decision ${esc(item.human_validation_decision||'pending')}</div>`}
  </article>`;
}

function renderCandidates(){
  const rows=candidates();
  $('validationCandidates').innerHTML=rows.length?rows.map(stageCard).join(''):'<div class="small-empty">Nenhum RecommendationCandidate finalizado disponível.</div>';
}

function pendingCard(item){
  if(item.status!=='PENDING')return '';
  return `<article class="validation-case" data-validation-id="${esc(item.validation_id)}">
    <div class="validation-card-head"><div><h3>${esc(item.statement||item.recommendation_candidate_id)}</h3><p>${esc(item.validation_id)} · candidate ${esc(short(item.recommendation_candidate_id))} · readiness=${esc(item.readiness||'not_evaluated')}</p></div><span class="validation-pill pending">PENDING</span></div>
    <p><strong>Review scope:</strong> ${esc(item.review_scope||'—')}</p>
    <div class="validation-decision-grid">
      <label class="validation-field"><span>Decision</span><select data-decision-field="decision"><option value="">Selecione explicitamente…</option><option value="ACCEPT">ACCEPT — accepted for declared scope only</option><option value="REJECT">REJECT</option><option value="REVISE">REVISE</option></select></label>
      <label class="validation-field"><span>Reviewer</span><input data-decision-field="reviewer" maxlength="120" placeholder="Nome do reviewer humano"></label>
    </div>
    <label class="validation-field"><span>Rationale</span><textarea data-decision-field="rationale" rows="4" maxlength="2200" placeholder="Justifique a decisão humana (mín. 40 caracteres)."></textarea></label>
    <label class="validation-field"><span>Revision instructions — only for REVISE</span><textarea data-decision-field="revision" rows="3" maxlength="1800" placeholder="Se REVISE, descreva o que deve mudar em um novo RecommendationCandidate. O atual não será editado."></textarea></label>
    <div class="validation-confirmations">
      <label><input data-confirm="human" type="checkbox"><span>Confirmo que a decisão foi inserida explicitamente por humano, sem decisão automática.</span></label>
      <label><input data-confirm="certainty" type="checkbox"><span>Confirmo que HumanValidation não equivale a certainty/GRADE nem formal Risk of Bias.</span></label>
      <label><input data-confirm="clinical" type="checkbox"><span>Confirmo que ACCEPT/REJECT/REVISE não cria clinical ou guideline recommendation automaticamente.</span></label>
      <label><input data-confirm="immutable" type="checkbox"><span>Confirmo que esta decisão não reescreve o RecommendationCandidate upstream nem altera readiness.</span></label>
    </div>
    <button type="button" data-decide-validation>Record HumanValidation decision</button>
  </article>`;
}

function renderPending(){
  const html=cases().map(pendingCard).filter(Boolean).join('');
  $('pendingValidations').innerHTML=html||'<div class="small-empty">Nenhum caso PENDING.</div>';
}

function renderFinalized(){
  const rows=finalized();
  $('finalizedValidations').innerHTML=rows.length?rows.map(item=>`<article class="final-validation">
    <div class="validation-card-head"><div><h3>${esc(String(item.decision||'').toUpperCase())}</h3><p>${esc(item.validation_id)} · candidate ${esc(short(item.recommendation_candidate_id))}</p></div><span class="validation-pill ${item.decision==='accept'?'accepted':''}">${esc(item.decision||'—')}</span></div>
    <p>${esc(item.rationale||'')}</p>
    <p><strong>Reviewer:</strong> ${esc(item.reviewer||'—')} · <strong>Scope:</strong> ${esc(item.review_scope||'—')}</p>
    ${item.revision_instructions?`<p><strong>Revision instructions:</strong> ${esc(item.revision_instructions)}</p>`:''}
    <div class="small-state">accepted for declared scope: ${item.candidate_accepted_for_declared_scope===true?'yes':'no'} · readiness changed: no · clinical recommendation created: no</div>
  </article>`).join(''):'<div class="small-empty">Nenhuma HumanValidation finalizada.</div>';
}

function render(){renderKpis();renderCandidates();renderPending();renderFinalized();}

function field(card,name){return String(card.querySelector(`[data-stage-field="${name}"]`)?.value||'').trim();}
async function stage(card){
  const candidateId=card.dataset.candidateId;
  const scope=field(card,'scope');
  const stagedBy=field(card,'stagedBy');
  if(scope.length<20){alert('Review scope precisa ter pelo menos 20 caracteres.');return;}
  if(!stagedBy){alert('Informe quem abriu a HumanValidation.');return;}
  const button=card.querySelector('[data-stage-validation]');if(button)button.disabled=true;
  try{
    const result=await postJson({operation:STAGE_OPERATION,recommendation_candidate_id:candidateId,review_scope:scope,staged_by:stagedBy});
    if(result?.validation_case_type!==CASE_TYPE)throw new Error('HumanValidation case contract inválido.');
    await load();
  }catch(error){alert(`Staging bloqueado: ${error.message}`);if(button)button.disabled=false;}
}

function decisionField(card,name){return String(card.querySelector(`[data-decision-field="${name}"]`)?.value||'').trim();}
function confirmed(card,name){return Boolean(card.querySelector(`[data-confirm="${name}"]`)?.checked);}
async function decide(card){
  const validationId=card.dataset.validationId;
  const decision=decisionField(card,'decision');
  const reviewer=decisionField(card,'reviewer');
  const rationale=decisionField(card,'rationale');
  const revision=decisionField(card,'revision');
  if(!['ACCEPT','REJECT','REVISE'].includes(decision)){alert('Selecione explicitamente ACCEPT, REJECT ou REVISE.');return;}
  if(!reviewer){alert('Informe o reviewer.');return;}
  if(rationale.length<40){alert('Rationale precisa ter pelo menos 40 caracteres.');return;}
  if(decision==='REVISE'&&revision.length<20){alert('REVISE exige revision instructions com pelo menos 20 caracteres.');return;}
  if(decision!=='REVISE'&&revision){alert('Revision instructions só são permitidas para REVISE.');return;}
  if(!confirmed(card,'human')||!confirmed(card,'certainty')||!confirmed(card,'clinical')||!confirmed(card,'immutable')){alert('Confirme as quatro fronteiras científicas antes de registrar a decisão.');return;}
  const button=card.querySelector('[data-decide-validation]');if(button)button.disabled=true;
  try{
    const result=await postJson({
      operation:DECIDE_OPERATION,
      validation_id:validationId,
      decision,
      reviewer,
      rationale,
      revision_instructions:revision,
      decision_human_entered_confirmed:true,
      decision_is_not_certainty_confirmed:true,
      decision_is_not_clinical_recommendation_confirmed:true,
      upstream_candidate_immutable_confirmed:true,
    });
    if(result?.canonical_human_validation_record_type!==RECORD_TYPE)throw new Error('Canonical HumanValidation contract inválido.');
    await load();
  }catch(error){alert(`Decisão bloqueada: ${error.message}`);if(button)button.disabled=false;}
}

async function load(){
  $('validationHealth').textContent='verificando…';
  $('validationState').classList.remove('hidden');
  $('validationContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('validationState').classList.add('hidden');
    $('validationContent').classList.remove('hidden');
    $('validationHealth').textContent='local HumanValidation gate conectado';
  }catch(error){
    $('validationHealth').textContent='local-only / indisponível';
    $('validationState').textContent=`RecommendationCandidate HumanValidation indisponível neste navegador: ${error.message}`;
  }
}

$('validationCandidates').addEventListener('click',event=>{const button=event.target.closest('[data-stage-validation]');if(!button)return;const card=button.closest('.validation-candidate');if(card)stage(card);});
$('pendingValidations').addEventListener('click',event=>{const button=event.target.closest('[data-decide-validation]');if(!button)return;const card=button.closest('.validation-case');if(card)decide(card);});
$('refreshValidation').addEventListener('click',load);
load();
