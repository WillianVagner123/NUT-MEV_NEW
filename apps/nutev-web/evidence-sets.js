const STAGE_OPERATION='STAGE_EVIDENCE_SET';
const FINALIZE_OPERATION='FINALIZE_EVIDENCE_SET';
const DRAFT_TYPE='NUTEV_EVIDENCE_SET_CONSTRUCTION_DRAFT_V1';
const SET_RECORD_TYPE='NUTEV_CANONICAL_EVIDENCE_SET_RECORD_V1';
let state=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>28?`${text.slice(0,14)}…${text.slice(-9)}`:text||'—'};

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

function eligibleClaims(){
  return (Array.isArray(state?.accepted_evidence_claims)?state.accepted_evidence_claims:[]).filter(item=>item.claim_evaluation_finalized===true);
}
function drafts(){return Array.isArray(state?.evidence_set_drafts)?state.evidence_set_drafts:[];}
function finalizedSets(){return Array.isArray(state?.finalized_evidence_sets)?state.finalized_evidence_sets:[];}

function renderKpis(){
  const counts=state?.evidence_set_draft_counts||{};
  $('setsKpis').innerHTML=[
    ['Eligible claims',eligibleClaims().length,'Accepted + finalized ClaimEvaluation'],
    ['Drafts',counts.DRAFT??0,'Proposed membership only'],
    ['Finalized',state?.finalized_evidence_set_count??0,'Canonical membership records'],
    ['Automatic grouping','0','No clustering / no auto membership'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderEligibleClaims(){
  const rows=eligibleClaims();
  $('eligibleClaims').innerHTML=rows.length?rows.map(claim=>`<label class="eligible-claim">
    <input type="checkbox" class="set-claim-selector" value="${esc(claim.claim_id)}">
    <span><strong>${esc(claim.statement||claim.claim_id)}</strong><p>${esc(claim.claim_id)} · evaluation ${esc(short(claim.claim_evaluation_id))} · EvidenceRecord ${esc(claim.evidence_record_id||'—')}</p></span>
    <span class="membership-count">${esc(claim.evidence_set_membership_count??0)} set(s)</span>
  </label>`).join(''):'<div class="small-empty">Nenhum EvidenceClaim com ClaimEvaluation finalizada está disponível.</div>';
  for(const input of document.querySelectorAll('.set-claim-selector'))input.addEventListener('change',validateStage);
}

function selectedClaimIds(){return [...document.querySelectorAll('.set-claim-selector:checked')].map(input=>input.value);}

function stageScope(){
  return {
    domain:$('scopeDomain').value.trim(),
    population:$('scopePopulation').value.trim(),
    intervention_or_exposure:'',
    comparator:'',
    outcome:$('scopeOutcome').value.trim(),
    timeframe:'',
    context:$('scopeContext').value.trim(),
  };
}

function validateStage(){
  const ready=$('setName').value.trim().length>=3&&$('setLens').value.trim()&&$('setFocus').value.trim().length>=20&&$('setStagedBy').value.trim()&&selectedClaimIds().length>0;
  $('stageSet').disabled=!ready;
}

function memberBlock(member){
  return `<div class="set-member" data-member-claim="${esc(member.claim_id)}">
    <strong>${esc(member.statement||member.claim_id)}</strong>
    <p>${esc(member.claim_id)} · evaluation ${esc(short(member.evaluation_id))} · document ${esc(member.document_id||'—')}</p>
    <label><span>Membership rationale</span><textarea data-membership-rationale="${esc(member.claim_id)}" rows="2" maxlength="1200" placeholder="Por que este claim pertence a este set? (mín. 15 caracteres)"></textarea></label>
  </div>`;
}

function draftCard(draft){
  const final=draft.status==='FINALIZED';
  const members=Array.isArray(draft.members)?draft.members:[];
  return `<article class="set-card" data-draft-id="${esc(draft.draft_id)}">
    <div class="set-card-head"><div><h3>${esc(draft.name||draft.draft_id)}</h3><p>${esc(draft.lens||'no lens')} · ${esc(draft.claim_count??0)} claim(s) · ${esc(short(draft.source_context_fingerprint))}</p></div><span class="set-pill ${final?'ok':''}">${esc(draft.status)}</span></div>
    <p>${esc(draft.focus_statement||'')}</p>
    <div class="set-members">${members.map(memberBlock).join('')}</div>
    ${final?`<div class="small-state">Canonical EvidenceSet: ${esc(draft.canonical_evidence_set_id||'—')}. Membership record finalized; no consensus/certainty was inferred.</div>`:`<div class="set-finalize">
      <div class="set-finalize-grid">
        <label><span>Curator</span><input data-set-field="curator" maxlength="120" placeholder="Nome do curador"></label>
        <label><span>Overall set rationale</span><textarea data-set-field="rationale" rows="3" maxlength="1800" placeholder="Justifique o foco e a composição do set (mín. 30 caracteres)."></textarea></label>
      </div>
      <div class="set-confirmations">
        <label><input data-set-confirm="membership" type="checkbox"><span>Confirmo que selecionei e justifiquei manualmente a membership; não foi resultado de ranking, cluster, LLM ou regra automática.</span></label>
        <label><input data-set-confirm="consensus" type="checkbox"><span>Confirmo que agrupar estes claims não significa agreement, consensus, contradiction ou pooled effect.</span></label>
        <label><input data-set-confirm="boundary" type="checkbox"><span>Confirmo que EvidenceSet não equivale a certainty/GRADE, síntese científica canônica, meta-analysis ou recomendação.</span></label>
      </div>
      <button type="button" data-finalize-set>Finalize EvidenceSet</button>
    </div>`}
  </article>`;
}

function renderDrafts(){
  const rows=drafts();
  $('setDrafts').innerHTML=rows.length?rows.map(draftCard).join(''):'<div class="small-empty">Nenhum EvidenceSet draft foi criado.</div>';
}

function renderFinalizedSets(){
  const rows=finalizedSets();
  $('finalizedSets').innerHTML=rows.length?rows.map(item=>`<article class="final-set">
    <h3>${esc(item.name||item.evidence_set_id)}</h3>
    <div class="final-set-meta"><span>${esc(item.evidence_set_id)}</span><span>lens: ${esc(item.lens||'—')}</span><span>${esc(item.claim_count??0)} claim(s)</span><span>curator: ${esc(item.curator||'—')}</span></div>
    <p>${esc(item.focus_statement||'')}</p>
    <div class="final-set-claims">${(item.claim_ids||[]).map(id=>`<span>${esc(id)}</span>`).join('')}</div>
  </article>`).join(''):'<div class="small-empty">Nenhum EvidenceSet canônico finalizado.</div>';
}

function render(){renderKpis();renderEligibleClaims();renderDrafts();renderFinalizedSets();validateStage();}

async function stage(){
  const claimIds=selectedClaimIds();
  if(!claimIds.length)return;
  $('stageSet').disabled=true;
  $('stageSetState').textContent='Revalidando claims e ClaimEvaluations antes de criar o draft…';
  try{
    const result=await postJson({
      operation:STAGE_OPERATION,
      name:$('setName').value.trim(),
      lens:$('setLens').value.trim(),
      focus_statement:$('setFocus').value.trim(),
      staged_by:$('setStagedBy').value.trim(),
      scope:stageScope(),
      claim_ids:claimIds,
    });
    if(result?.draft_type!==DRAFT_TYPE)throw new Error('EvidenceSet draft contract inválido.');
    $('stageSetState').textContent='Draft criado. Nenhuma membership canônica foi finalizada automaticamente.';
    await load();
  }catch(error){$('stageSetState').textContent=`Bloqueado: ${error.message}`;validateStage();}
}

function value(card,selector){return String(card.querySelector(selector)?.value||'').trim();}
function checked(card,selector){return Boolean(card.querySelector(selector)?.checked);}

async function finalizeSet(card){
  const draftId=card.dataset.draftId;
  const curator=value(card,'[data-set-field="curator"]');
  const rationale=value(card,'[data-set-field="rationale"]');
  if(!curator){alert('Informe o curator.');return;}
  if(rationale.length<30){alert('A rationale geral precisa ter pelo menos 30 caracteres.');return;}
  const membershipRationales={};
  for(const textarea of card.querySelectorAll('[data-membership-rationale]')){
    const text=textarea.value.trim();
    if(text.length<15){alert('Cada membership rationale precisa ter pelo menos 15 caracteres.');return;}
    membershipRationales[textarea.dataset.membershipRationale]=text;
  }
  if(!checked(card,'[data-set-confirm="membership"]')||!checked(card,'[data-set-confirm="consensus"]')||!checked(card,'[data-set-confirm="boundary"]')){
    alert('Confirme as três fronteiras científicas antes de finalizar.');return;
  }
  const button=card.querySelector('[data-finalize-set]');
  if(button)button.disabled=true;
  try{
    const result=await postJson({
      operation:FINALIZE_OPERATION,
      draft_id:draftId,
      curator,
      rationale,
      membership_rationales:membershipRationales,
      membership_human_curated_confirmed:true,
      grouping_is_not_consensus_confirmed:true,
      scientific_boundary_confirmed:true,
    });
    if(result?.canonical_evidence_set_record_type!==SET_RECORD_TYPE)throw new Error('Canonical EvidenceSet contract inválido.');
    await load();
  }catch(error){alert(`Finalização bloqueada: ${error.message}`);if(button)button.disabled=false;}
}

async function load(){
  $('setsHealth').textContent='verificando…';
  $('setsState').classList.remove('hidden');
  $('setsContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('setsState').classList.add('hidden');
    $('setsContent').classList.remove('hidden');
    $('setsHealth').textContent='local EvidenceSet gate conectado';
  }catch(error){$('setsHealth').textContent='local-only / indisponível';$('setsState').textContent=`EvidenceSet Construction indisponível neste navegador: ${error.message}`;}
}

for(const id of ['setName','setLens','setFocus','setStagedBy'])$(id).addEventListener('input',validateStage);
$('stageSet').addEventListener('click',stage);
$('setDrafts').addEventListener('click',event=>{const button=event.target.closest('[data-finalize-set]');if(!button)return;const card=button.closest('.set-card');if(card)finalizeSet(card);});
$('refreshSets').addEventListener('click',load);
load();
