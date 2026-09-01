const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmtBool=value=>value===true?'YES':value===false?'NO':String(value??'—');

const routeLabels={
  'B-NORM':'B-NORM · Normative',
  'C1-CARE-PROCESS':'C1 · Care process',
  'C2-COMPETENCY-LITERACY':'C2 · Competency / literacy',
  'C3-IMPLEMENTATION':'C3 · Implementation',
  'C4-SOCIAL-CONTEXT':'C4 · Social context'
};

function statusClass(value){const text=String(value??'').toUpperCase();if(text==='PASS'||text==='AUTHORIZED'||text==='FROZEN'||value===true)return'ok';if(text.includes('PENDING')||text.includes('DRAFT')||text.includes('CANDIDATE')||text.includes('NOT_YET')||value===false)return'warn';return''}
function pills(items,kind=''){return (items||[]).map(item=>`<span class="strategy-pill ${kind}">${esc(typeof item==='string'?item:item.term||JSON.stringify(item))}</span>`).join('')}
function termBlock(title,items,kind=''){if(!items||!items.length)return'';return `<div class="strategy-term-block"><strong>${esc(title)}</strong><div class="strategy-pills">${pills(items,kind)}</div></div>`}

function renderReadiness(draft,state){const formal=state.formal_search||{};const items=[
  ['Draft',draft.status],
  ['PRESS',formal.press_status||'NOT RECORDED'],
  ['GF-10',formal.gf10_authorized?'AUTHORIZED':'LOCKED'],
  ['Query freeze',formal.query_freeze_complete?'COMPLETE':'NOT COMPLETE'],
  ['Formal search',formal.formal_provider_search_executed?'EXECUTED':'NOT EXECUTED']
];$('#strategyReadiness').innerHTML=items.map(([label,value])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="strategy-status ${statusClass(value)}">${esc(value)}</strong></article>`).join('')}

function routeCard(name,route){
  const status=route.status||'CANDIDATE_FOR_PRESS';
  const blocks=[];
  if(route.blocks){for(const [key,values] of Object.entries(route.blocks))blocks.push(termBlock(key.replaceAll('_',' '),values))}
  if(route.anchor)blocks.push(termBlock('anchor',route.anchor));
  if(route.terms)blocks.push(termBlock('terms',route.terms));
  if(route.social_context_terms)blocks.push(termBlock('social context',route.social_context_terms));
  if(route.operational_marker)blocks.push(termBlock('operational marker',route.operational_marker));
  if(route.press_only_terms)blocks.push(termBlock('PRESS only',route.press_only_terms,'press'));
  return `<article class="strategy-route-card ${name==='C4-SOCIAL-CONTEXT'?'candidate':''}">
    <div class="strategy-route-head"><div><span>${esc(routeLabels[name]||name)}</span><strong>${esc(route.logic||route.aggregation||'')}</strong></div><em class="${statusClass(status)}">${esc(status)}</em></div>
    ${blocks.join('')}
    ${route.reason?`<p>${esc(route.reason)}</p>`:''}
  </article>`
}

function renderRoutes(draft){const routes=draft.routes||{};const cards=[routeCard('B-NORM',routes['B-NORM']||{})];const subs=routes['C-STRUCT']?.subroutes||{};for(const key of ['C1-CARE-PROCESS','C2-COMPETENCY-LITERACY','C3-IMPLEMENTATION','C4-SOCIAL-CONTEXT'])cards.push(routeCard(key,subs[key]||{}));$('#routeCards').innerHTML=cards.join('')}

function renderDecision(target,decision){
  const keep=decision.keep||[];const test=decision.test_in_press_not_auto_add||decision.press_review_candidates||[];const reject=decision.do_not_add_from_audit||[];
  $(target).innerHTML=`<div class="strategy-decision"><div class="decision-label"><span>Decision</span><strong>${esc(decision.decision||'—')}</strong></div><p>${esc(decision.reason||'')}</p>${termBlock('KEEP',keep,'keep')}${termBlock('TEST IN PRESS',test,'press')}${termBlock('DO NOT AUTO-ADD',reject,'reject')}</div>`
}

function renderDeltaTests(draft){const tests=draft.press_plan?.delta_tests||[];$('#deltaTests').innerHTML=tests.map((value,index)=>`<article class="delta-test"><span>${String(index+1).padStart(2,'0')}</span><strong>${esc(value)}</strong><em>PENDING PRESS</em></article>`).join('')||'<p class="small-state">Nenhum delta test registrado.</p>'}

function renderProviderDrafts(draft){const providers=draft.routes?.['B-NORM']?.known_provider_drafts||{};const entries=Object.entries(providers);$('#providerDrafts').innerHTML=entries.map(([provider,query])=>`<article><div><strong>${esc(provider.replaceAll('_',' '))}</strong><span>CANDIDATE · NOT FORMAL</span></div><pre>${esc(query)}</pre></article>`).join('')||'<p class="small-state">Nenhuma string de provider registrada nesta versão.</p>'}

async function load(){
  try{
    const [draftResponse,stateResponse]=await Promise.all([
      fetch('/strategy-data/article1_query_draft_v1.json',{cache:'no-store'}),
      fetch('/agent-context/article1/SEARCH_STATE.json',{cache:'no-store'})
    ]);
    if(!draftResponse.ok)throw new Error(`query draft HTTP ${draftResponse.status}`);if(!stateResponse.ok)throw new Error(`search state HTTP ${stateResponse.status}`);
    const draft=await draftResponse.json(),state=await stateResponse.json();
    $('#draftVersion').textContent=draft.draft_version||'Article 1 query draft';$('#strategyQuestion').textContent=draft.question||state.question||'Pergunta indisponível';
    $('#draftStatus').innerHTML=`<span class="status-chip warn">${esc(draft.status||'DRAFT')}</span><span class="status-chip ${draft.formal_gate?.authorized?'done':'pending'}">GF-10 ${draft.formal_gate?.authorized?'AUTHORIZED':'LOCKED'}</span>`;
    renderReadiness(draft,state);renderRoutes(draft);renderDecision('#bNormDecision',draft.vocabulary_decisions?.['B-NORM']||{});renderDecision('#cStructDecision',draft.vocabulary_decisions?.['C-STRUCT']||{});renderDeltaTests(draft);renderProviderDrafts(draft);
    const formal=state.formal_search||{};$('#versionState').innerHTML=`<strong>${esc(draft.draft_version||'draft')}</strong><p>Esta é a versão canônica pré-PRESS disponível. Nenhuma versão APPROVED/FROZEN é inferida. PRESS = <b>${esc(formal.press_status||'not recorded')}</b>; GF-10 = <b>${fmtBool(formal.gf10_authorized)}</b>.</p>`;
    $('#freezeRule').innerHTML=`<strong>Fail closed</strong><p>${esc(draft.press_plan?.freeze_rule||draft.formal_gate?.guardrail||'Freeze não autorizado.')}</p>`;
    $('#strategyState').className='hidden';$('#strategyContent').classList.remove('hidden');$('#strategyHealth').textContent=`${esc(draft.draft_version)} · ${esc(draft.status)}`;$('#strategyHealth').className='status-pill ok';
  }catch(error){$('#strategyState').className='error';$('#strategyState').innerHTML=`<strong>Strategy Lab indisponível.</strong><div>${esc(error.message)}</div>`;$('#strategyHealth').textContent='estado indisponível';$('#strategyHealth').className='status-pill bad'}
}
load();
