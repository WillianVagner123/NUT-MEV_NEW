const STAGE_OPERATION='STAGE_RECOMMENDATION_DEVELOPMENT';
const FINALIZE_OPERATION='FINALIZE_RECOMMENDATION_DEVELOPMENT';
const METHOD='NUTEV_GENERIC_RECOMMENDATION_DEVELOPMENT_V1';
const RECORD_TYPE='NUTEV_CANONICAL_RECOMMENDATION_DEVELOPMENT_RECORD_V1';
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

function validations(){return Array.isArray(state?.finalized_recommendation_human_validations)?state.finalized_recommendation_human_validations:[];}
function candidates(){return Array.isArray(state?.finalized_recommendation_candidates)?state.finalized_recommendation_candidates:[];}
function drafts(){return Array.isArray(state?.recommendation_development_drafts)?state.recommendation_development_drafts:[];}
function finalized(){return Array.isArray(state?.finalized_recommendation_developments)?state.finalized_recommendation_developments:[];}
function candidateById(id){return candidates().find(item=>String(item.recommendation_candidate_id||'')===String(id||''));}
function acceptedValidations(){return validations().filter(item=>String(item.decision||'').toLowerCase()==='accept');}

function renderKpis(){
  const counts=state?.recommendation_development_counts||{};
  $('developmentKpis').innerHTML=[
    ['Accepted validations',acceptedValidations().length,'Only HumanValidation ACCEPT can enter'],
    ['Drafts',counts.DRAFT??0,'Generic development worksheets'],
    ['Finalized',counts.FINALIZED??0,'Canonical worksheet records'],
    ['Strength',state?.recommendation_development_strength_default||'not_evaluated','Never inferred automatically'],
    ['Method',state?.recommendation_development_method||METHOD,'Generic NutEV method; not GRADE EtD'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

const fields=[
  ['proposed_recommendation_text','Proposed recommendation text',30,'Escreva um novo wording humano. O source candidate não é copiado automaticamente.'],
  ['population_scope','Population / scope',20,'Delimite explicitamente a população e o escopo.'],
  ['intervention_or_action','Intervention / action',20,'Ação proposta, sem inferência automática.'],
  ['comparator_or_alternative','Comparator / alternative',3,'Alternativa, usual care, no intervention ou N/A justificado.'],
  ['benefits_summary','Benefits consideration',40,'Resumo humano; não pooled benefit magnitude.'],
  ['harms_burdens_summary','Harms / burdens consideration',40,'Inclua harms, burden, opportunity cost e riscos de implementação.'],
  ['values_preferences_summary','Values / preferences',40,'Consideração narrativa; não formal preference assessment.'],
  ['resources_summary','Resources',30,'Recursos e custos; não análise econômica formal.'],
  ['equity_summary','Equity',30,'Acesso, desigualdade, cultural fit e distribuição de efeitos.'],
  ['acceptability_summary','Acceptability',30,'Aceitabilidade para pacientes, profissionais e serviços.'],
  ['feasibility_summary','Feasibility',30,'Viabilidade operacional no contexto declarado.'],
  ['implementation_considerations','Implementation',30,'Condições e salvaguardas para implementação.'],
  ['uncertainty_notes','Uncertainty',30,'Incertezas que permanecem sem certainty grading.'],
  ['developer_rationale','Developer rationale',40,'Por que este wording e este escopo são apropriados para desenvolvimento.'],
];

function stageForm(validation){
  const candidate=candidateById(validation.recommendation_candidate_id)||{};
  const fieldHtml=fields.map(([name,label,min,placeholder])=>`<label class="development-field"><span>${esc(label)}</span><textarea data-development-field="${esc(name)}" rows="${name==='proposed_recommendation_text'?4:3}" maxlength="2200" data-min="${min}" placeholder="${esc(placeholder)}"></textarea></label>`).join('');
  return `<article class="development-card" data-validation-id="${esc(validation.validation_id)}">
    <div class="development-head"><div><h3>HumanValidation ACCEPT</h3><div class="recommendation-meta"><span>${esc(validation.validation_id)}</span><span>reviewer: ${esc(validation.reviewer||'—')}</span><span>development: ${esc(validation.recommendation_development_status||'NOT_STAGED')}</span></div></div><span class="development-pill accept">ACCEPT</span></div>
    <div class="development-source"><strong>Source candidate — read only</strong><p>${esc(candidate.statement||'Source candidate unavailable in bounded status.')}</p><div class="recommendation-meta"><span>candidate: ${esc(validation.recommendation_candidate_id||'—')}</span><span>readiness: ${esc(candidate.readiness||'not_evaluated')}</span><span>scope: ${esc(validation.review_scope||'—')}</span></div></div>
    ${validation.recommendation_development_status&&validation.recommendation_development_status!=='NOT_STAGED'?`<p><strong>Development already ${esc(validation.recommendation_development_status)}.</strong> Este ACCEPT já possui um worksheet registrado.</p>`:`<div class="development-form">${fieldHtml}
      <label class="development-field"><span>Prepared by</span><input data-development-field="prepared_by" maxlength="120" placeholder="Nome de quem preparou o worksheet"></label>
      <div class="development-confirmations">
        <label><input data-development-field="human_authorship_confirmed" type="checkbox"><span>Confirmo que o wording e todas as considerações foram escritos por humano.</span></label>
        <label><input data-development-field="generic_method_confirmed" type="checkbox"><span>Confirmo que este é o método genérico NutEV e não uma aplicação de GRADE Evidence-to-Decision.</span></label>
      </div>
      <button type="button" data-stage-development>Stage development worksheet</button>
      <div class="small-state" data-stage-state>Nenhum campo é pré-preenchido a partir do candidate.</div>
    </div>`}
  </article>`;
}

function finalizeForm(draft){
  return `<div class="development-finalize">
    <label class="development-field"><span>Finalizer</span><input data-finalize-field="finalizer" maxlength="120" placeholder="Nome de quem finalizou o worksheet"></label>
    <label class="development-field"><span>Finalization rationale</span><textarea data-finalize-field="finalization_rationale" rows="3" maxlength="1800" placeholder="Explique por que o worksheet está completo para registro canônico, sem declarar recomendação formal."></textarea></label>
    <div class="development-confirmations">
      <label><input data-finalize-field="no_grade_etd_claim_confirmed" type="checkbox"><span>Confirmo que este registro não declara aplicação de GRADE Evidence-to-Decision.</span></label>
      <label><input data-finalize-field="strength_not_evaluated_confirmed" type="checkbox"><span>Confirmo que recommendation strength permanece not_evaluated.</span></label>
      <label><input data-finalize-field="not_formal_recommendation_confirmed" type="checkbox"><span>Confirmo que finalizar o worksheet não cria clinical/guideline recommendation.</span></label>
      <label><input data-finalize-field="upstream_immutable_confirmed" type="checkbox"><span>Confirmo que HumanValidation e RecommendationCandidate upstream permanecem imutáveis.</span></label>
    </div>
    <button type="button" data-finalize-development="${esc(draft.development_id)}">Finalize development record</button>
  </div>`;
}

function renderAccepted(){
  const rows=acceptedValidations();
  $('acceptedValidations').innerHTML=rows.length?rows.map(stageForm).join(''):'<div class="small-empty">Nenhuma HumanValidation ACCEPT disponível.</div>';
}

function renderDrafts(){
  const rows=drafts();
  $('developmentDrafts').innerHTML=rows.length?rows.map(draft=>`<article class="development-card" data-development-id="${esc(draft.development_id)}">
    <div class="development-head"><div><h3>${esc(draft.proposed_recommendation_text||draft.development_id)}</h3><div class="recommendation-meta"><span>${esc(draft.development_id)}</span><span>source validation: ${esc(draft.human_validation_id)}</span><span>strength: ${esc(draft.recommendation_strength||'not_evaluated')}</span></div></div><span class="development-pill">${esc(draft.status)}</span></div>
    <p><strong>Population:</strong> ${esc(draft.population_scope||'—')}</p>
    ${draft.status==='DRAFT'?finalizeForm(draft):'<p><strong>Canonical development record finalized.</strong> Nenhuma recommendation strength ou guideline status foi criada.</p>'}
  </article>`).join(''):'<div class="small-empty">Nenhum Recommendation Development draft.</div>';
}

function renderFinalized(){
  const rows=finalized();
  $('finalizedDevelopments').innerHTML=rows.length?rows.map(item=>`<article class="development-card">
    <div class="development-head"><div><h3>${esc(item.proposed_recommendation_text||item.development_id)}</h3><div class="recommendation-meta"><span>${esc(item.development_id)}</span><span>strength: ${esc(item.recommendation_strength||'not_evaluated')}</span><span>method: ${esc(item.method||METHOD)}</span></div></div><span class="development-pill ok">FINALIZED</span></div>
    <p><strong>Population:</strong> ${esc(item.population_scope||'—')}</p>
    <div class="recommendation-meta"><span>GRADE EtD applied: ${item.grade_etd_applied?'YES':'NO'}</span><span>validated recommendation: ${item.validated_recommendation_created?'YES':'NO'}</span><span>clinical: ${item.clinical_recommendation_created?'YES':'NO'}</span><span>guideline: ${item.guideline_recommendation_created?'YES':'NO'}</span></div>
  </article>`).join(''):'<div class="small-empty">Nenhum Recommendation Development finalizado.</div>';
}

function render(){renderKpis();renderAccepted();renderDrafts();renderFinalized();}

function value(card,name){
  const el=card.querySelector(`[data-development-field="${name}"]`);
  return el?.type==='checkbox'?Boolean(el.checked):String(el?.value||'').trim();
}

async function stage(card){
  const validationId=card.dataset.validationId;
  const payload={operation:STAGE_OPERATION,human_validation_id:validationId};
  for(const [name,,min] of fields){
    const v=value(card,name);
    if(v.length<min){alert(`${name} precisa ter pelo menos ${min} caracteres.`);return;}
    payload[name]=v;
  }
  payload.prepared_by=value(card,'prepared_by');
  payload.human_authorship_confirmed=value(card,'human_authorship_confirmed');
  payload.generic_method_confirmed=value(card,'generic_method_confirmed');
  if(!payload.prepared_by){alert('Informe prepared_by.');return;}
  if(!payload.human_authorship_confirmed||!payload.generic_method_confirmed){alert('Confirme autoria humana e a fronteira do método genérico antes de staging.');return;}

  const button=card.querySelector('[data-stage-development]');
  const status=card.querySelector('[data-stage-state]');
  if(button)button.disabled=true;
  if(status)status.textContent='Revalidando HumanValidation ACCEPT, candidate e contexto…';
  try{
    const result=await postJson(payload);
    if(result?.method!==METHOD)throw new Error('Recommendation Development method contract inválido.');
    await load();
  }catch(error){if(status)status.textContent=`Bloqueado: ${error.message}`;if(button)button.disabled=false;}
}

function finalizeValue(card,name){const el=card.querySelector(`[data-finalize-field="${name}"]`);return el?.type==='checkbox'?Boolean(el.checked):String(el?.value||'').trim();}

async function finalizeDevelopment(card,developmentId){
  const finalizer=finalizeValue(card,'finalizer');
  const rationale=finalizeValue(card,'finalization_rationale');
  if(!finalizer){alert('Informe o finalizer.');return;}
  if(rationale.length<40){alert('A finalization rationale precisa ter pelo menos 40 caracteres.');return;}
  const confirmations=['no_grade_etd_claim_confirmed','strength_not_evaluated_confirmed','not_formal_recommendation_confirmed','upstream_immutable_confirmed'];
  if(confirmations.some(name=>!finalizeValue(card,name))){alert('Confirme as quatro fronteiras científicas antes de finalizar.');return;}
  const button=card.querySelector('[data-finalize-development]');
  if(button)button.disabled=true;
  try{
    const result=await postJson({operation:FINALIZE_OPERATION,development_id:developmentId,finalizer,finalization_rationale:rationale,no_grade_etd_claim_confirmed:true,strength_not_evaluated_confirmed:true,not_formal_recommendation_confirmed:true,upstream_immutable_confirmed:true});
    if(result?.canonical_recommendation_development_record_type!==RECORD_TYPE)throw new Error('Recommendation Development record contract inválido.');
    await load();
  }catch(error){alert(`Finalização bloqueada: ${error.message}`);if(button)button.disabled=false;}
}

async function load(){
  $('developmentHealth').textContent='verificando…';
  $('developmentState').classList.remove('hidden');
  $('developmentContent').classList.add('hidden');
  try{
    state=await getJson('/api/synthesis/releases');
    render();
    $('developmentState').classList.add('hidden');
    $('developmentContent').classList.remove('hidden');
    $('developmentHealth').textContent='local development gate conectado';
  }catch(error){$('developmentHealth').textContent='local-only / indisponível';$('developmentState').textContent=`Recommendation Development indisponível neste navegador: ${error.message}`;}
}

$('acceptedValidations').addEventListener('click',event=>{const button=event.target.closest('[data-stage-development]');if(!button)return;const card=button.closest('[data-validation-id]');if(card)stage(card);});
$('developmentDrafts').addEventListener('click',event=>{const button=event.target.closest('[data-finalize-development]');if(!button)return;const card=button.closest('[data-development-id]');if(card)finalizeDevelopment(card,button.dataset.finalizeDevelopment);});
$('refreshDevelopment').addEventListener('click',load);
load();
