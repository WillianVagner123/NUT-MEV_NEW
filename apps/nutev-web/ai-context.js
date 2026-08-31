const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const PROMPT=`Leia primeiro o SEARCH_SUMMARY e o SEARCH_STATE canônicos do Article 1 no NutEV. Depois use ARTICLE_SUMMARIES.jsonl como contexto estruturado rank-blind. Analise apenas o que os dados suportam. Não trate discovery, Bank tier, machine profile, route membership ou full-text retrieval como inclusão científica, qualidade, risco de viés, certeza ou PRISMA. Quando precisar aprofundar um documento específico, use seu document_id no Workbench e mantenha separados artefatos de máquina de decisões humanas.`;
async function getJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json()}
async function init(){
  try{
    const [health,manifest,state]=await Promise.all([getJson('/api/health'),getJson('/agent-context/article1/CONTEXT_MANIFEST.json'),getJson('/agent-context/article1/SEARCH_STATE.json')]);
    $('#aiHealth').textContent=health.status==='ok'?'contexto disponível':'engine parcial';$('#aiHealth').className=`status-pill ${health.status==='ok'?'ok':'bad'}`;
    const outputs=manifest.outputs||{};const runtime=state.runtime||{};
    const cards=[
      ['Context version',state.context_version||manifest.context_version||'—'],
      ['Search ID',state.search_id||manifest.search_id||'—'],
      ['Article summaries',runtime.agent_article_summaries||manifest.counts?.article_summaries||0],
      ['B-NORM',runtime.article1_routes?.counts?.['B-NORM']||0],
      ['C-STRUCT',runtime.article1_routes?.counts?.['C-STRUCT']||0],
      ['Formal gate',state.formal_search?.gf10_authorized?'AUTHORIZED':'LOCKED']
    ];
    $('#contextCards').innerHTML=cards.map(([label,value])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="metric-value ai-value">${typeof value==='number'?fmt(value):esc(value)}</strong></article>`).join('');
    const fileRows=[
      ['SEARCH_SUMMARY.md','/agent-context/article1/SEARCH_SUMMARY.md',outputs.search_summary?.sha256],
      ['SEARCH_STATE.json','/agent-context/article1/SEARCH_STATE.json',outputs.search_state?.sha256],
      ['ARTICLE_SUMMARIES.jsonl','/agent-context/article1/ARTICLE_SUMMARIES.jsonl',outputs.article_summaries?.sha256],
      ['CONTEXT_MANIFEST.json','/agent-context/article1/CONTEXT_MANIFEST.json',null]
    ];
    $('#contextFiles').innerHTML=fileRows.map(([name,url,sha])=>`<a class="context-file" href="${url}" target="_blank" rel="noopener"><div><strong>${esc(name)}</strong><small>${sha?`SHA-256 ${esc(String(sha).slice(0,18))}…`:'manifest de proveniência'}</small></div><span>Open ↗</span></a>`).join('');
    $('#formalState').innerHTML=`<div class="readiness-grid"><div class="readiness-item"><span>PRESS</span><strong>${esc(state.formal_search?.press_status||'—')}</strong></div><div class="readiness-item"><span>GF-10</span><strong>${state.formal_search?.gf10_authorized?'AUTHORIZED':'LOCKED'}</strong></div><div class="readiness-item"><span>Query freeze</span><strong>${state.formal_search?.query_freeze_complete?'COMPLETE':'NOT COMPLETE'}</strong></div><div class="readiness-item"><span>Formal search</span><strong>${state.formal_search?.formal_provider_search_executed?'EXECUTED':'NOT EXECUTED'}</strong></div></div>`;
    $('#contextState').className='hidden';$('#contextContent').classList.remove('hidden');
  }catch(error){$('#contextState').className='error';$('#contextState').innerHTML=`<strong>AI Context ainda não materializado.</strong><div>${esc(error.message)}</div><div class="small-state">Gere o bundle verificado antes de usar esta área.</div>`}
}
$('#agentPrompt').value=PROMPT;
$('#copyPrompt').addEventListener('click',async()=>{await navigator.clipboard.writeText(PROMPT);$('#copyPrompt').textContent='Copiado';setTimeout(()=>$('#copyPrompt').textContent='Copiar prompt',1400)});
init();
