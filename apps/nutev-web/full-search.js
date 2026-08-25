const state={profile:null,press:null,connected:new Set(),plan:null,validated:false};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function plainTerm(term){const t=String(term||'').trim();if(!t)return'';if(t.includes(' '))return `"${t}"`;return t}
function plainGroup(items){return '('+(items||[]).map(plainTerm).filter(Boolean).join(' OR ')+')'}
function epmcTerm(term){const t=String(term||'').trim();if(!t)return'';return t.includes(' ')?`TITLE_ABS:"${t}"`:`TITLE_ABS:${t}`}
function epmcGroup(items){return '('+(items||[]).map(epmcTerm).filter(Boolean).join(' OR ')+')'}
function boolC(groups,formatter){
  const core=formatter(groups.nutrition_core);
  const care=`(${formatter(groups.structural_care)} AND ${formatter(groups.structural_qualifiers)})`;
  const food=`(${formatter(groups.food_competence)} AND ${formatter(groups.competence_qualifiers)})`;
  const professional=`(${formatter(groups.professional_competence)} AND ${formatter(groups.competence_qualifiers)})`;
  const implementation=formatter(groups.implementation);
  const dietary=`(${formatter(groups.dietary_orientation)} AND ${formatter(groups.orientation_qualifiers)})`;
  return `${core} AND (${care} OR ${food} OR ${professional} OR ${implementation} OR ${dietary})`;
}
function boolB(groups,formatter){return `${formatter(groups.nutrition_core)} AND ${formatter(groups.normative_markers)}`}

function pressStrategy(id){return (state.press?.profiles?.[0]?.strategies||[]).find(s=>s.strategy_id===id)||null}
function queryFor(databaseId,route){
  const g=state.profile.canonical_keywords;
  if(databaseId==='pubmed'){
    const source=route==='B-NORM'?pressStrategy('B-NORM-PUBMED'):route==='C-STRUCT'?pressStrategy('C-STRUCT-PUBMED'):null;
    return source?.query||'';
  }
  if(databaseId==='lilacs_bvs_native'&&route==='B-NORM')return state.profile.regional_query;
  if(databaseId==='scielo_native'&&route==='B-SUPP')return state.profile.regional_query;
  if(databaseId==='scopus'||databaseId==='wos')return state.profile.manual_queries?.[databaseId]?.[route]||'';
  if(databaseId==='europepmc')return route==='B-NORM'?boolB(g,epmcGroup):route==='C-STRUCT'?boolC(g,epmcGroup):'';
  if(['openalex','crossref','doaj','semantic_scholar'].includes(databaseId))return route==='B-NORM'?boolB(g,plainGroup):route==='C-STRUCT'?boolC(g,plainGroup):'';
  return'';
}

function balanced(query){let depth=0;let quoted=false;for(let i=0;i<query.length;i++){const ch=query[i];if(ch==='"'&&query[i-1]!=='\\')quoted=!quoted;if(quoted)continue;if(ch==='(')depth++;if(ch===')')depth--;if(depth<0)return false}return depth===0&&!quoted}
function validateOne(db,route,query){
  const issues=[];const q=String(query||'').trim();
  if(!q)issues.push('query vazia');
  if(q.length>20000)issues.push('query > 20.000 caracteres');
  if(q&&!balanced(q))issues.push('parênteses/aspas desbalanceados');
  if(db.id==='pubmed'&&route!=='B-SUPP'&&!/\[(Mesh|Majr|ti|tiab|pt|Title\/Abstract|Date - Publication)\]/i.test(q))issues.push('sem campos explícitos PubMed');
  if(db.id==='scopus'&&q&&!q.startsWith('TITLE-ABS-KEY('))issues.push('sintaxe Scopus sem TITLE-ABS-KEY');
  if(db.id==='wos'&&q&&!q.startsWith('TS=('))issues.push('sintaxe WoS sem TS=');
  if(db.id==='lilacs_bvs_native'&&q!==state.profile.regional_query)issues.push('rota LILACS diverge da query regional canônica');
  if(db.id==='scielo_native'&&q!==state.profile.regional_query)issues.push('rota SciELO diverge da query regional canônica');
  if(db.id!=='pubmed'&&/\[(Mesh|Majr|ti|tiab|pt|Title\/Abstract|Date - Publication)\]/i.test(q))issues.push('tag PubMed vazou para outra base');
  return {status:issues.length?'FAIL':'PASS_STATIC',issues};
}

function buildPlan(){
  const databases=(state.profile.databases||[]).map(db=>({
    ...db,
    connected:state.connected.has(db.id),
    route_queries:(db.routes||[]).map(route=>{const query=queryFor(db.id,route);return{route,query,validation:validateOne(db,route,query)}})
  }));
  const failures=databases.flatMap(db=>db.route_queries.filter(r=>r.validation.status!=='PASS_STATIC').map(r=>`${db.id}:${r.route}`));
  return {
    schema_version:1,
    created_at:new Date().toISOString(),
    profile_id:state.profile.profile_id,
    question:state.profile.question,
    canonical_keywords:state.profile.canonical_keywords,
    formal_gate:state.profile.formal_gate,
    validation:{status:failures.length?'FAIL':'PASS_STATIC',failures,meaning:'PASS_STATIC valida estrutura/sintaxe local. Não prova aceitação remota nem cobertura da base.'},
    databases
  };
}

function renderKeywords(){const root=$('#keywordGroups');root.innerHTML=Object.entries(state.profile.canonical_keywords||{}).map(([name,items])=>`<div class="keyword-group"><strong>${esc(name)}</strong><div>${items.map(x=>`<span>${esc(x)}</span>`).join('')}</div></div>`).join('')}
function roleLabel(role){return({FORMAL_CANDIDATE:'formal',FORMAL_SUPPLEMENTARY:'formal suplementar',OPTIONAL_LICENSED:'licenciada opcional',DISCOVERY_ONLY:'descoberta/QA'})[role]||role}
function executionLabel(v){return({CONNECTED:'conectado',CONNECTED_WITH_BROWSER_FALLBACK:'conectado + fallback visual',MANUAL_LICENSED:'manual/licenciado'})[v]||v}
function routeVersion(route){if(route==='B-NORM')return'v0.7-multidb';if(route==='C-STRUCT')return'v0.5.1-multidb';return'regional-2026-08-25'}

function renderPlan(){
  state.plan=buildPlan();
  const formal=state.profile.formal_gate?.gf10_authorized===true;
  $('#gateState').className=`full-state ${formal?'ok':'warning'}`;
  $('#gateState').innerHTML=formal?'<strong>GF-10 AUTORIZADO.</strong> Execução FORMAL pode ser habilitada.':'<strong>Pré-freeze.</strong> GF-10 ainda não está autorizado; apenas PREFLIGHT pode rodar e nenhuma contagem entra no PRISMA.';
  $('#questionCard').innerHTML=`<strong>Pergunta do A1</strong><p>${esc(state.profile.question)}</p>`;
  renderKeywords();
  const automatic=state.plan.databases.filter(db=>db.execution!=='MANUAL_LICENSED');
  $('#databasePlan').innerHTML=automatic.map(db=>renderDb(db)).join('');
  const manual=state.plan.databases.filter(db=>db.execution==='MANUAL_LICENSED');
  $('#manualPlan').innerHTML=manual.map(db=>renderDb(db,true)).join('');
  $('#validationSummary').className=`full-state ${state.plan.validation.status==='PASS_STATIC'?'ok':'bad'}`;
  $('#validationSummary').innerHTML=state.plan.validation.status==='PASS_STATIC'?'<strong>PASS estático em todas as traduções.</strong> Ainda falta a execução real de cada base para confirmação remota.':`<strong>Falha estática.</strong> ${esc(state.plan.validation.failures.join(', '))}`;
  state.validated=state.plan.validation.status==='PASS_STATIC';
  $('#downloadPlan').disabled=!state.validated;
  $('#runPreflight').disabled=!state.validated;
  $('#runFormal').disabled=!(state.validated&&formal);
}

function renderDb(db,manual=false){
  const status=db.route_queries.every(r=>r.validation.status==='PASS_STATIC')?'PASS estático':'revisar';
  return `<article class="db-card"><div class="db-head"><div><strong>${esc(db.label)}</strong><span>${esc(roleLabel(db.article1_role))} · ${esc(executionLabel(db.execution))}${db.connected?' · disponível no servidor':''}</span></div><span class="db-status ${status==='PASS estático'?'ok':'bad'}">${esc(status)}</span></div>${db.route_queries.map(r=>`<details><summary>${esc(r.route)} · ${esc(routeVersion(r.route))}</summary><code>${esc(r.query)}</code>${r.validation.issues.length?`<div class="issue">${r.validation.issues.map(esc).join(' · ')}</div>`:''}<div class="query-actions"><button class="ghost copy-query" type="button" data-query="${esc(r.query)}">Copiar query</button>${manual?'<span>Execute na interface licenciada e exporte RIS/CSV.</span>':''}</div></details>`).join('')}</article>`;
}

function downloadJson(name,value){const blob=new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function copyQuery(btn){try{await navigator.clipboard.writeText(btn.dataset.query||'');const old=btn.textContent;btn.textContent='Copiado';setTimeout(()=>btn.textContent=old,900)}catch(_e){alert('Não foi possível copiar automaticamente. Selecione a query manualmente.')}}

function jobProviders(route){
  return state.plan.databases.filter(db=>db.connected&&db.execution!=='MANUAL_LICENSED'&&db.routes.includes(route)).map(db=>db.id).filter(id=>{
    if(route==='B-SUPP')return id==='scielo_native';
    if(route==='C-STRUCT')return !['lilacs_bvs_native','scielo_native'].includes(id);
    if(route==='B-NORM')return id!=='scielo_native';
    return false;
  });
}
function routeQueries(route,providers){const out={};for(const provider of providers){const db=state.plan.databases.find(x=>x.id===provider);const row=db?.route_queries.find(x=>x.route===route);if(row?.query)out[provider]=row.query}return out}
async function createJob(route,{formal=false}={}){
  const providers=jobProviders(route);if(!providers.length)return null;
  const provider_queries=routeQueries(route,providers);
  const strategy={mode:'exact',strategy_id:`A1-${route}-MULTIDB`,strategy_version:routeVersion(route),run_class:formal?'FORMAL':'PREFLIGHT',provider_queries};
  const res=await fetch('/api/search/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:state.profile.question,providers,strategy,per_provider:formal?0:25,max_results:formal?0:300})});
  const data=await res.json();if(!res.ok)throw new Error(data.message||data.error||`Falha ao iniciar ${route}`);return data;
}
async function waitJob(job){let current=job;while(current&&current.status!=='completed'){if(current.status==='failed')throw new Error(current.error||'job falhou');await sleep(800);const res=await fetch(`/api/search/jobs/${encodeURIComponent(current.job_id)}`,{cache:'no-store'});current=await res.json();if(!res.ok)throw new Error(current.message||current.error||'job não encontrado');renderRunProgress(current)}return current}
function renderRunProgress(job){const providers=(job.providers||[]).map(p=>`${p.label}: ${p.status}${p.returned!==undefined?` (${p.returned})`:''}`).join(' · ');$('#runState').className='full-state running';$('#runState').innerHTML=`<strong>${esc(job.query_plan?.strategy_id||'Executando')}</strong><div>${esc(providers)}</div>`}
async function runAll(formal=false){
  if(formal&&state.profile.formal_gate?.gf10_authorized!==true)return alert('GF-10 não autorizado. A busca FORMAL permanece bloqueada.');
  $('#runPreflight').disabled=true;$('#runFormal').disabled=true;$('#runResults').innerHTML='';
  const completed=[];
  try{
    for(const route of ['B-NORM','C-STRUCT','B-SUPP']){
      $('#runState').className='full-state running';$('#runState').innerHTML=`Iniciando ${esc(route)}…`;
      const job=await createJob(route,{formal});if(!job)continue;const done=await waitJob(job);completed.push({route,search_id:done.result?.search_id,status:done.result?.status,failed_providers:done.result?.failed_providers||[],unavailable_providers:done.result?.unavailable_providers||[],non_exhaustive_providers:done.result?.non_exhaustive_providers||[],records_before_dedup:done.result?.records_before_dedup,unique_records:done.result?.unique_records});
      $('#runResults').innerHTML=completed.map(x=>`<div class="run-result"><strong>${esc(x.route)}</strong><span>${esc(x.status||'')}</span><code>${esc(x.search_id||'')}</code><small>únicos: ${Number(x.unique_records||0)} · falhas: ${esc((x.failed_providers||[]).join(', ')||'nenhuma')} · indisponíveis: ${esc((x.unavailable_providers||[]).join(', ')||'nenhum')}</small></div>`).join('');
    }
    $('#runState').className='full-state ok';$('#runState').innerHTML=formal?'<strong>Execução FORMAL concluída.</strong> Revise gaps antes de qualquer PRISMA.':'<strong>PREFLIGHT concluído.</strong> Estes números são QA e não entram no PRISMA.';
  }catch(e){$('#runState').className='full-state bad';$('#runState').textContent=`Falha: ${e.message}`}
  finally{$('#runPreflight').disabled=!state.validated;$('#runFormal').disabled=!(state.validated&&state.profile.formal_gate?.gf10_authorized===true)}
}

async function init(){
  try{
    const [profile,press,providers,health]=await Promise.all([
      fetch('./article1-search-profile.json',{cache:'no-store'}).then(r=>r.json()),
      fetch('./press-review-profiles.json',{cache:'no-store'}).then(r=>r.json()),
      fetch('/api/providers',{cache:'no-store'}).then(r=>r.json()),
      fetch('/api/health',{cache:'no-store'}).then(r=>r.json())
    ]);
    state.profile=profile;state.press=press;state.connected=new Set((providers.providers||[]).map(p=>p.id));
    $('#fullHealth').textContent=health.status==='ok'?'engine conectado':'engine indisponível';$('#fullHealth').classList.add(health.status==='ok'?'ok':'bad');renderPlan();
  }catch(e){$('#fullHealth').textContent='falha ao carregar';$('#fullHealth').classList.add('bad');$('#validationSummary').className='full-state bad';$('#validationSummary').textContent=e.message}
}

$('#refreshPlan').onclick=renderPlan;
$('#validateAll').onclick=renderPlan;
$('#downloadPlan').onclick=()=>downloadJson(`ARTICLE1_MULTI_DATABASE_PLAN_${new Date().toISOString().slice(0,10)}.json`,state.plan);
$('#runPreflight').onclick=()=>runAll(false);
$('#runFormal').onclick=()=>runAll(true);
document.addEventListener('click',event=>{const btn=event.target.closest('.copy-query');if(btn)copyQuery(btn)});
init();
