const STAGE_OPERATION='STAGE_EVIDENCE_CLAIM_REVIEW';
const DECIDE_OPERATION='DECIDE_EVIDENCE_CLAIM';
const CANDIDATE_TYPE='NUTEV_EVIDENCE_CLAIM_CANDIDATE_V1';
const CLAIM_RECORD_TYPE='NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1';
let state=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>24?`${text.slice(0,12)}…${text.slice(-8)}`:text||'—'};

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

function publicationRecords(){return Array.isArray(state?.publication_records)?state.publication_records:[];}
function candidates(){return Array.isArray(state?.evidence_claim_candidates)?state.evidence_claim_candidates:[];}
function acceptedClaims(){return Array.isArray(state?.accepted_evidence_claims)?state.accepted_evidence_claims:[];}
function finalizedEvaluations(){return Array.isArray(state?.finalized_claim_evaluations)?state.finalized_claim_evaluations:[];}

function renderKpis(){
  const counts=state?.evidence_claim_candidate_counts||{};
  $('claimsKpis').innerHTML=[
    ['Candidates',state?.evidence_claim_candidate_count??0,'Atomic citation snapshots awaiting/holding human decisions'],
    ['Pending',counts.PENDING_HUMAN_REVIEW??0,'No EvidenceClaim created'],
    ['Revision',counts.REVISION_REQUIRED??0,'Human revision requested; still no accepted claim'],
    ['Accepted',state?.accepted_evidence_claim_count??0,'Canonical source-level claims only'],
    ['Rejected',counts.REJECTED??0,'No canonical claim created'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderManifestSelect(){
  const select=$('claimManifest');
  const selected=select.value;
  const records=publicationRecords();
  select.innerHTML='<option value="">Selecione um manifest</option>'+records.map(record=>`<option value="${esc(record.manifest_id)}">${esc(record.manifest_id)} · ${esc(record.publication_owner||'owner n/a')}</option>`).join('');
  if(records.some(record=>record.manifest_id===selected))select.value=selected;
  validateStage();
}

function validateStage(){
  $('stageClaims').disabled=!($('claimManifest').value&&$('stagedBy').value.trim());
}

function statusClass(candidate){
  if(candidate.status==='ACCEPTED')return 'ok';
  if(candidate.status==='REJECTED')return 'blocked';
  if(candidate.status==='REVISION_REQUIRED')return 'warn';
  return '';
}

function sourceNumbers(candidate){
  const values=[];
  for(const key of ['effect_measures','confidence_intervals','p_values']){
    const raw=candidate?.[key];
    if(Array.isArray(raw))values.push(...raw.map(String));
  }
  return values.filter(Boolean);
}

function candidateCard(candidate){
  const final=candidate.status==='ACCEPTED'||candidate.status==='REJECTED';
  const context=candidate.synthesis_context||{};
  const numbers=sourceNumbers(candidate);
  const acceptedNote=candidate.status==='ACCEPTED'?`Canonical EvidenceClaim: ${candidate.canonical_evidence_claim_id||'—'}`:candidate.status==='REJECTED'?'Final human decision: REJECT':'';
  return `<article class="claim-card" data-candidate-id="${esc(candidate.candidate_id)}">
    <div class="claim-card-head">
      <div><h3>${esc(candidate.title||candidate.document_id)}</h3><p>${esc(candidate.document_id)} · ${esc(candidate.citation_id)} · bundle ${esc(candidate.bundle_id)}</p></div>
      <div class="claim-pills"><span class="claim-pill ${statusClass(candidate)}">${esc(candidate.status)}</span><span class="claim-pill ${candidate.evidence_record_resolved?'ok':'blocked'}">EvidenceRecord ${candidate.evidence_record_resolved?'resolved':'missing'}</span></div>
    </div>
    <div class="claim-source-grid">
      <div class="claim-source"><span>Source-linked result snapshot</span><blockquote>${esc(candidate.result_text||'')}</blockquote>${numbers.length?`<p><strong>Reported numbers:</strong> ${esc(numbers.join(' · '))}</p>`:''}<p><small>source_sentence_sha256: ${esc(short(candidate.source_sentence_sha256))}</small></p></div>
      <div class="claim-context"><span>Pairwise synthesis context — not directly promotable</span><p><strong>${esc(context.relation||'No relation label')}</strong></p><p>${esc(context.statement_text||'No pairwise statement linked.')}</p><p><small>${esc(context.context_semantics||'Pairwise context is not an atomic EvidenceClaim.')}</small></p></div>
    </div>
    ${final?`<div class="claim-final">${esc(acceptedNote)}. Claim acceptance still does not mean screening inclusion, RoB, certainty, EvidenceSet synthesis or recommendation.</div>`:`<div class="claim-review-form">
      <div class="claim-form-grid">
        <label><span>Reviewer</span><input data-field="reviewer" type="text" maxlength="120" placeholder="Nome do revisor"></label>
        <label><span>Evidence type (optional)</span><input data-field="evidence_type" type="text" maxlength="160" placeholder="Ex.: randomized trial result"></label>
        <label class="wide"><span>Human claim statement — starts empty</span><textarea data-field="claim_statement" rows="3" maxlength="1600" placeholder="Escreva a proposição source-level que esta fonte reporta. O result text acima não é copiado automaticamente para este campo."></textarea></label>
        <label><span>Population (optional)</span><input data-field="population" type="text" maxlength="300"></label>
        <label><span>Intervention / exposure (optional)</span><input data-field="intervention_or_exposure" type="text" maxlength="300"></label>
        <label><span>Comparator (optional)</span><input data-field="comparator" type="text" maxlength="300"></label>
        <label><span>Outcome (optional)</span><input data-field="outcome" type="text" maxlength="300"></label>
        <label class="wide"><span>Rationale</span><textarea data-field="rationale" rows="3" maxlength="1600" placeholder="Justifique a decisão humana (mínimo 20 caracteres)."></textarea></label>
      </div>
      <div class="claim-confirmations">
        <label><input data-field="source_attribution_confirmed" type="checkbox"><span>Confirmo que, se eu aceitar, o claim descreve uma proposição reportada pela fonte; não estou declarando que ela é verdadeira/certa apenas por constar no artigo.</span></label>
        <label><input data-field="scientific_boundary_confirmed" type="checkbox"><span>Confirmo que EvidenceClaim acceptance não equivale a inclusão PRISMA, Risk of Bias, certainty, EvidenceSet synthesis, causalidade ou recomendação.</span></label>
      </div>
      <div class="claim-actions"><button class="accept" type="button" data-decision="ACCEPT" ${candidate.evidence_record_resolved?'':'disabled'}>Accept source claim</button><button class="revise" type="button" data-decision="REVISE">Request revision</button><button class="reject" type="button" data-decision="REJECT">Reject claim</button></div>
      ${candidate.evidence_record_resolved?'':'<div class="small-state">ACCEPT bloqueado: o EvidenceRecord correspondente precisa existir em scientific/evidence_records.jsonl. REVISE/REJECT continuam disponíveis.</div>'}
    </div>`}
  </article>`;
}

function renderCandidates(){
  const filter=$('claimStatusFilter').value;
  const rows=candidates().filter(candidate=>filter==='ALL'||candidate.status===filter);
  $('claimCandidates').innerHTML=rows.length?rows.map(candidateCard).join(''):'<div class="small-empty">Nenhum claim candidate para este filtro.</div>';
}

function evaluationStatus(claim){
  if(claim.claim_evaluation_finalized)return {finalized:true,id:claim.claim_evaluation_id||null};
  const found=finalizedEvaluations().find(item=>item.claim_id===claim.claim_id);
  return {finalized:Boolean(found),id:found?.evaluation_id||null};
}

function renderAcceptedClaims(){
  const claims=acceptedClaims();
  $('acceptedClaims').innerHTML=claims.length?claims.map(claim=>{
    const evaluation=evaluationStatus(claim);
    const evaluationText=evaluation.finalized?`FINALIZED · ${evaluation.id||'id unavailable'}`:'NOT FINALIZED';
    return `<article class="accepted-claim">
      <div><span>Statement</span><strong class="statement">${esc(claim.statement)}</strong></div>
      <div><span>Claim id</span><strong>${esc(claim.claim_id)}</strong></div>
      <div><span>EvidenceRecord</span><strong>${esc(claim.evidence_record_id)}</strong></div>
      <div><span>Downstream ClaimEvaluation</span><strong>${esc(evaluationText)}</strong></div>
    </article>`;
  }).join(''):'<div class="small-empty">Nenhum EvidenceClaim canônico aceito ainda.</div>';
}

function render(){renderKpis();renderManifestSelect();renderCandidates();renderAcceptedClaims();}

async function stage(){
  const manifestId=$('claimManifest').value;
  const stagedBy=$('stagedBy').value.trim();
  if(!manifestId||!stagedBy)return;
  $('stageClaims').disabled=true;
  $('stageClaimsState').textContent='Revalidando publication manifest e criando atomic source candidates…';
  try{
    const result=await postJson({operation:STAGE_OPERATION,manifest_id:manifestId,staged_by:stagedBy});
    if(result?.candidate_type!==CANDIDATE_TYPE)throw new Error('Claim candidate contract inválido.');
    state={...state,evidence_claim_candidate_type:result.candidate_type,evidence_claim_record_type:result.canonical_claim_record_type,evidence_claim_candidate_count:result.candidate_count,evidence_claim_candidate_counts:result.candidate_counts,evidence_claim_candidates:result.candidates,accepted_evidence_claim_count:result.accepted_claim_count,accepted_evidence_claims:result.accepted_claims};
    $('stageClaimsState').textContent='Candidates staged. Nenhum EvidenceClaim foi aceito automaticamente.';
    render();
  }catch(error){$('stageClaimsState').textContent=`Bloqueado: ${error.message}`;}finally{validateStage();}
}

function field(card,name){const el=card.querySelector(`[data-field="${name}"]`);return el?.type==='checkbox'?Boolean(el.checked):String(el?.value||'').trim();}

async function decide(card,decision){
  const candidateId=card.dataset.candidateId;
  const candidate=candidates().find(item=>item.candidate_id===candidateId);
  const reviewer=field(card,'reviewer');
  const rationale=field(card,'rationale');
  const claimStatement=field(card,'claim_statement');
  if(!reviewer){alert('Informe o reviewer.');return;}
  if(rationale.length<20){alert('A rationale precisa ter pelo menos 20 caracteres.');return;}
  if(decision==='ACCEPT'){
    if(!candidate?.evidence_record_resolved){alert('ACCEPT bloqueado: EvidenceRecord não resolvido.');return;}
    if(claimStatement.length<20){alert('O claim statement precisa ter pelo menos 20 caracteres.');return;}
    if(!field(card,'source_attribution_confirmed')||!field(card,'scientific_boundary_confirmed')){alert('Confirme as duas fronteiras científicas antes de ACCEPT.');return;}
  }
  for(const button of card.querySelectorAll('[data-decision]'))button.disabled=true;
  try{
    const result=await postJson({
      operation:DECIDE_OPERATION,
      candidate_id:candidateId,
      decision,
      reviewer,
      rationale,
      claim_statement:claimStatement,
      population:field(card,'population'),
      intervention_or_exposure:field(card,'intervention_or_exposure'),
      comparator:field(card,'comparator'),
      outcome:field(card,'outcome'),
      evidence_type:field(card,'evidence_type'),
      source_attribution_confirmed:field(card,'source_attribution_confirmed'),
      scientific_boundary_confirmed:field(card,'scientific_boundary_confirmed'),
    });
    if(result?.canonical_claim_record_type!==CLAIM_RECORD_TYPE)throw new Error('Canonical EvidenceClaim contract inválido.');
    state={...state,evidence_claim_candidate_count:result.candidate_count,evidence_claim_candidate_counts:result.candidate_counts,evidence_claim_candidates:result.candidates,accepted_evidence_claim_count:result.accepted_claim_count,accepted_evidence_claims:result.accepted_claims};
    render();
  }catch(error){alert(`Decisão bloqueada: ${error.message}`);for(const button of card.querySelectorAll('[data-decision]'))button.disabled=false;}
}

async function load(){
  $('claimsHealth').textContent='verificando…';
  $('claimsState').classList.remove('hidden');
  $('claimsContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('claimsState').classList.add('hidden');
    $('claimsContent').classList.remove('hidden');
    $('claimsHealth').textContent='local claim gate conectado';
  }catch(error){$('claimsHealth').textContent='local-only / indisponível';$('claimsState').textContent=`EvidenceClaim Review indisponível neste navegador: ${error.message}`;}
}

$('claimManifest').addEventListener('change',validateStage);
$('stagedBy').addEventListener('input',validateStage);
$('stageClaims').addEventListener('click',stage);
$('claimStatusFilter').addEventListener('change',renderCandidates);
$('claimCandidates').addEventListener('click',event=>{const button=event.target.closest('[data-decision]');if(!button)return;const card=button.closest('.claim-card');if(card)decide(card,button.dataset.decision);});
$('refreshClaims').addEventListener('click',load);
load();
