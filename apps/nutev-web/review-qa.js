const $=selector=>document.querySelector(selector);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const state={profiles:[],profile:null,run:null,report:null,running:false,classifications:{}};

const CLASS_LABELS={
  normativo_estruturante_plausivel:'Normativo/estruturante plausível',
  empirico_off_target:'Empírico / off-target',
  editorial_comment_erratum:'Editorial / comment / erratum',
  sem_conteudo_alimentar_aparente:'Sem conteúdo alimentar aparente',
  ambiguo:'Ambíguo'
};

function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function normalizeDoi(value){return String(value||'').trim().toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//,'').replace(/^doi:\s*/,'').replace(/[\s.,;]+$/,'')}
function recordKey(record){const pmid=String(record?.pmid||'').trim();if(pmid)return`pmid:${pmid}`;const doi=normalizeDoi(record?.doi);if(doi)return`doi:${doi}`;return`title:${String(record?.title||'').trim().toLowerCase()}`}
function flattenMessages(value){if(!value||typeof value!=='object')return[];return Object.entries(value).flatMap(([kind,items])=>(Array.isArray(items)?items:[items]).filter(Boolean).map(item=>`${kind}: ${item}`))}
function providerFor(run,id){return(run?.providers||[]).find(item=>item.provider===id)||null}
function providerCount(provider){const details=provider?.search_details;if(details&&Number.isFinite(Number(details.count)))return Number(details.count);if(Number.isFinite(Number(provider?.total_found)))return Number(provider.total_found);return null}
function runResults(run){return Array.isArray(run?.results)?run.results:[]}

function sentinelFound(records,sentinel){const wantedPmid=String(sentinel.pmid||'').trim();const wantedDoi=normalizeDoi(sentinel.doi);return records.find(record=>{
  if(wantedPmid&&String(record.pmid||'').trim()===wantedPmid)return true;
  if(wantedDoi&&normalizeDoi(record.doi)===wantedDoi)return true;
  return false;
})||null}

function dateRank(record){
  const raw=String(record?.publication_date||record?.year||'').trim();
  const yearMatch=raw.match(/\b(19|20)\d{2}\b/);if(!yearMatch)return 0;
  const year=Number(yearMatch[0]);
  const months={jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
  const lower=raw.toLowerCase();let month=0;for(const [name,num]of Object.entries(months)){if(lower.includes(name)){month=num;break}}
  if(!month){const numeric=raw.match(/\b\d{4}[-\/]([01]?\d)[-\/]([0-3]?\d)\b/);if(numeric)month=Number(numeric[1])}
  let day=0;const dayMatch=raw.match(/\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b/i);if(dayMatch)day=Number(dayMatch[1]);
  const iso=raw.match(/\b\d{4}[-\/]([01]?\d)[-\/]([0-3]?\d)\b/);if(iso)day=Number(iso[2]);
  return year*10000+month*100+day;
}

function mainRunAudit(profile,run){
  const issues=[];const plan=run?.query_plan||{};const provider=providerFor(run,profile.provider);const details=provider?.search_details||{};
  if(plan.mode!=='exact_review')issues.push('O run não está em modo exact_review.');
  if(plan.strategy_id!==profile.strategy_id)issues.push(`Strategy ID esperado: ${profile.strategy_id}.`);
  if(plan.strategy_version!==profile.strategy_version)issues.push(`Versão esperada: ${profile.strategy_version}.`);
  if(String(plan.run_class||'').toUpperCase()!==String(profile.run_class||'').toUpperCase())issues.push(`Classe esperada: ${profile.run_class}.`);
  if(!provider)issues.push(`Provider ${profile.provider} ausente.`);
  if(provider&&provider.status!=='completed')issues.push(`Provider ${profile.provider} não concluiu (${provider.status||'sem status'}).`);
  const count=providerCount(provider);const returned=Number(provider?.returned??run?.returned_records??0);
  if(count!==null&&returned!==count)issues.push(`Recuperação incompleta: ${returned}/${count}.`);
  const warnings=flattenMessages(details.warninglist);const errors=flattenMessages(details.errorlist);
  if(warnings.length)issues.push(`Search Details com ${warnings.length} warning(s).`);
  if(errors.length)issues.push(`Search Details com ${errors.length} erro(s).`);
  if((run?.audit_gaps||[]).length)issues.push(`${run.audit_gaps.length} lacuna(s) de auditoria.`);
  if((run?.failed_providers||[]).length||(run?.unavailable_providers||[]).length)issues.push('Há provider failed/unavailable no run principal.');
  return{ok:issues.length===0,issues,provider,count,returned,warnings,errors};
}

async function fetchJson(url,options){const response=await fetch(url,options);const payload=await response.json();if(!response.ok)throw new Error(payload.message||payload.error||`HTTP ${response.status}`);return payload}

async function loadProfiles(){const payload=await fetchJson('./review-qa-profiles.json',{cache:'no-store'});state.profiles=payload.profiles||[];if(!state.profiles.length)throw new Error('Nenhum perfil de QA configurado.');state.profile=state.profiles[0]}

async function findLatestCompatibleRun(profile){
  const listing=await fetchJson('/api/searches?limit=30',{cache:'no-store'});const items=listing.searches||[];
  for(const item of items.slice(0,20)){
    try{
      const run=await fetchJson(`/api/searches/${encodeURIComponent(item.search_id)}`,{cache:'no-store'});const plan=run.query_plan||{};
      if(plan.mode==='exact_review'&&plan.strategy_id===profile.strategy_id&&plan.strategy_version===profile.strategy_version&&String(plan.run_class||'').toUpperCase()===String(profile.run_class||'').toUpperCase())return run;
    }catch(_error){/* keep scanning persisted runs */}
  }
  return null;
}

function renderMainRun(){
  const root=$('#mainRunCard');const profile=state.profile;const run=state.run;if(!run){root.innerHTML='<div class="qa-state bad">Nenhum run compatível encontrado. Volte a Buscar evidências e conclua a estratégia exata com Strategy ID e Versão exatamente iguais ao perfil.</div>';$('#runQaBtn').disabled=true;return}
  const audit=mainRunAudit(profile,run);const provider=audit.provider;const created=run.created_at?new Date(run.created_at).toLocaleString('pt-BR'):'—';
  root.innerHTML=`<div class="qa-run-grid"><div class="qa-metric">Estratégia<strong>${esc(profile.strategy_id)} ${esc(profile.strategy_version)}</strong></div><div class="qa-metric">Run<strong>${esc(run.search_id||'—')}</strong></div><div class="qa-metric">PubMed count<strong>${esc(audit.count??'—')}</strong></div><div class="qa-metric">Recuperados<strong>${esc(audit.returned)}</strong></div><div class="qa-metric">Executado<strong>${esc(created)}</strong></div></div><div class="qa-state ${audit.ok?'ok':'bad'}">${audit.ok?'<strong>Run principal elegível para QA.</strong> Recuperação completa e Search Details sem gaps.':`<strong>Run ainda não elegível.</strong><ul>${audit.issues.map(issue=>`<li>${esc(issue)}</li>`).join('')}</ul>`}</div>`;
  $('#runQaBtn').disabled=!audit.ok||state.running;
}

async function refresh(){
  $('#profileState').className='qa-state';$('#profileState').textContent='Procurando o último run compatível…';$('#runQaBtn').disabled=true;$('#qaSummary').classList.add('hidden');$('#branchResults').innerHTML='';state.report=null;$('#downloadQaBtn').disabled=true;
  try{await loadProfiles();state.run=await findLatestCompatibleRun(state.profile);$('#profileState').className='qa-state ok';$('#profileState').innerHTML=`Perfil ativo: <strong>${esc(state.profile.strategy_id)} ${esc(state.profile.strategy_version)}</strong> · ${esc(state.profile.branches.length)} ramos · amostra até ${esc(state.profile.sample_size)} exclusivos/ramo.`;renderMainRun();$('#qaHealth').textContent='pronto';$('#qaHealth').className='status-pill ok'}catch(error){$('#profileState').className='qa-state bad';$('#profileState').textContent=`Falha: ${error.message}`;$('#qaHealth').textContent='falha';$('#qaHealth').className='status-pill bad'}
}

async function pollJob(jobId,onUpdate){
  for(;;){const job=await fetchJson(`/api/search/jobs/${encodeURIComponent(jobId)}`,{cache:'no-store'});onUpdate?.(job);if(job.status==='completed'){if(!job.result)throw new Error('Job concluído sem resultado persistido.');return job.result}if(job.status==='failed')throw new Error(job.error||'Job de QA falhou.');await sleep(700)}
}

async function runBranch(profile,branch,index,total){
  $('#qaProgress').className='qa-state';$('#qaProgress').innerHTML=`<strong>Executando ramo ${index+1}/${total}: ${esc(branch.id)}</strong><div>${esc(branch.label)}</div>`;
  const payload={query:`QA ${profile.strategy_id} ${profile.strategy_version} · ${branch.id}`,providers:[profile.provider],strategy:{mode:'exact',strategy_id:`${profile.strategy_id}-QA-${branch.id}`,strategy_version:profile.strategy_version,run_class:'PILOT',provider_queries:{[profile.provider]:branch.query}},per_provider:0,max_results:0};
  const job=await fetchJson('/api/search/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  return pollJob(job.job_id,current=>{const p=(current.providers||[])[0];const returned=Number(p?.returned||0);$('#qaProgress').innerHTML=`<strong>Ramo ${index+1}/${total}: ${esc(branch.id)} · ${esc(current.stage||current.status)}</strong><div>${esc(branch.label)}${returned?` · ${returned} recuperados`:''}</div>`});
}

function branchAudit(profile,branch,result){
  const issues=[];const provider=providerFor(result,profile.provider);const details=provider?.search_details||{};const warnings=flattenMessages(details.warninglist);const errors=flattenMessages(details.errorlist);if(!provider)issues.push('Provider ausente.');else if(provider.status!=='completed')issues.push(`Provider ${provider.status||'sem status'}.`);if(warnings.length)issues.push(`${warnings.length} warning(s).`);if(errors.length)issues.push(`${errors.length} erro(s).`);if((result.audit_gaps||[]).length)issues.push(`${result.audit_gaps.length} audit gap(s).`);return{branch,provider,count:providerCount(provider),warnings,errors,issues,ok:issues.length===0,records:runResults(result),search_id:result.search_id}}

function loadClassifications(){try{state.classifications=JSON.parse(localStorage.getItem(`nutev_review_qa:${state.run.search_id}`)||'{}')||{}}catch(_error){state.classifications={}}}
function saveClassifications(){localStorage.setItem(`nutev_review_qa:${state.run.search_id}`,JSON.stringify(state.classifications));updateClassificationCounter()}
function updateClassificationCounter(){const total=state.report?.branches?.reduce((sum,branch)=>sum+branch.sample.length,0)||0;const done=Object.values(state.classifications).filter(Boolean).length;const node=$('#classificationCounter');if(node)node.textContent=`${done}/${total} amostras classificadas`}

function buildReport(profile,mainRun,branchAudits){
  const mainAudit=mainRunAudit(profile,mainRun);const mainRecords=runResults(mainRun);const allSentinels=[...(profile.required_sentinels||[]),...(profile.informational_sentinels||[])];const sentinels=allSentinels.map(sentinel=>{const found=sentinelFound(mainRecords,sentinel);return{...sentinel,found:Boolean(found),record:found?{pmid:found.pmid||'',doi:found.doi||'',title:found.title||''}:null}});
  const sets=new Map();for(const branchAuditItem of branchAudits){sets.set(branchAuditItem.branch.id,new Set(branchAuditItem.records.map(recordKey)))}const membership=new Map();for(const set of sets.values())for(const key of set)membership.set(key,(membership.get(key)||0)+1);
  const branches=branchAudits.map(item=>{const exclusive=item.records.filter(record=>membership.get(recordKey(record))===1).sort((a,b)=>dateRank(b)-dateRank(a)||String(a.title||'').localeCompare(String(b.title||'')));const sample=exclusive.slice(0,Number(profile.sample_size||10)).map(record=>({key:recordKey(record),pmid:record.pmid||'',doi:record.doi||'',title:record.title||'',journal:record.journal||'',publication_date:record.publication_date||record.year||'',url:record.url||''}));return{id:item.branch.id,label:item.branch.label,search_id:item.search_id,count:item.count,technical_ok:item.ok,technical_issues:item.issues,records_retrieved:item.records.length,exclusive_records:exclusive.length,overlap_records:item.records.length-exclusive.length,sample}});
  const requiredSentinelsOk=sentinels.filter(item=>item.required).every(item=>item.found);const branchesOk=branchAudits.every(item=>item.ok);const technicalPass=mainAudit.ok&&requiredSentinelsOk&&branchesOk;const currentCount=mainAudit.count;const baseline=profile.baseline||{};
  return{schema_version:1,created_at:new Date().toISOString(),profile_id:profile.profile_id,strategy_id:profile.strategy_id,strategy_version:profile.strategy_version,run_class:profile.run_class,main_search_id:mainRun.search_id,main_count:currentCount,baseline:{strategy_version:baseline.strategy_version||'',count:Number(baseline.count||0)},delta_from_baseline:currentCount===null?null:currentCount-Number(baseline.count||0),technical_gate:technicalPass?'PASS':'REVIEW_REQUIRED',scientific_decision:'PENDING_HUMAN_REVIEW',sentinels,branches,guardrails:profile.guardrails||[]};
}

function renderSummary(report){const required=report.sentinels.filter(item=>item.required);const requiredFound=required.filter(item=>item.found).length;const root=$('#qaSummary');root.classList.remove('hidden');root.innerHTML=`<div class="section-head"><div><h2>3. Resultado do QA</h2><p>Controle técnico concluído. A classificação de relevância e a decisão científica permanecem humanas.</p></div><span class="qa-badge ${report.technical_gate==='PASS'?'ok':'warn'}">${esc(report.technical_gate)}</span></div><div class="qa-summary-grid"><div class="qa-metric">Final atual<strong>${esc(report.main_count??'—')}</strong></div><div class="qa-metric">Baseline ${esc(report.baseline.strategy_version)}<strong>${esc(report.baseline.count)}</strong></div><div class="qa-metric">Diferença<strong>${report.delta_from_baseline===null?'—':`${report.delta_from_baseline>=0?'+':''}${esc(report.delta_from_baseline)}`}</strong></div><div class="qa-metric">Sentinelas obrigatórios<strong>${requiredFound}/${required.length}</strong></div><div class="qa-metric">Decisão científica<strong>PENDENTE HUMANO</strong></div></div><div class="qa-sentinel-list">${report.sentinels.map(item=>`<div class="qa-sentinel ${item.found?'pass':'fail'}"><span><strong>${esc(item.id)}</strong> · ${esc(item.label)}</span><span>${item.found?'RECUPERADO':item.required?'NÃO RECUPERADO':'não observado'}</span></div>`).join('')}</div><div class="qa-human-note"><strong id="classificationCounter">0 amostras classificadas</strong><div>Classifique a amostra prospectiva abaixo. O NutEV não transforma ranking nem heurística em elegibilidade científica.</div></div><ul class="qa-guardrails">${report.guardrails.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`;updateClassificationCounter()}

function classificationSelect(branchId,sample){const storageKey=`${branchId}|${sample.key}`;const value=state.classifications[storageKey]||'';const options=state.profile.human_classification_options||Object.keys(CLASS_LABELS);return`<select data-classification-key="${esc(encodeURIComponent(storageKey))}"><option value="">— classificar —</option>${options.map(option=>`<option value="${esc(option)}" ${value===option?'selected':''}>${esc(CLASS_LABELS[option]||option)}</option>`).join('')}</select>`}

function renderBranches(report){const root=$('#branchResults');root.innerHTML=report.branches.map(branch=>`<article class="card qa-branch"><div class="qa-branch-head"><div><h3>${esc(branch.id)} — ${esc(branch.label)}</h3><div class="qa-meta">run ${esc(branch.search_id||'—')} · ordenação da amostra: publication date desc</div></div><span class="qa-badge ${branch.technical_ok?'ok':'warn'}">${branch.technical_ok?'QA técnico OK':'revisar'}</span></div><div class="qa-summary-grid"><div class="qa-metric">Count do ramo<strong>${esc(branch.count??'—')}</strong></div><div class="qa-metric">Exclusivos<strong>${esc(branch.exclusive_records)}</strong></div><div class="qa-metric">Sobrepostos<strong>${esc(branch.overlap_records)}</strong></div><div class="qa-metric">Amostra<strong>${esc(branch.sample.length)}</strong></div></div>${branch.technical_issues.length?`<div class="qa-state bad">${branch.technical_issues.map(issue=>esc(issue)).join(' · ')}</div>`:''}${branch.sample.length?`<table class="qa-sample-table"><thead><tr><th>#</th><th>Registro</th><th>Data</th><th>Classificação humana</th></tr></thead><tbody>${branch.sample.map((sample,index)=>`<tr><td>${index+1}</td><td><div class="qa-title">${esc(sample.title)}</div><div class="qa-meta">${esc(sample.journal)}${sample.pmid?` · PMID ${esc(sample.pmid)}`:''}${sample.doi?` · DOI ${esc(sample.doi)}`:''}</div></td><td>${esc(sample.publication_date||'—')}</td><td>${classificationSelect(branch.id,sample)}</td></tr>`).join('')}</tbody></table>`:'<div class="qa-state">Nenhum registro exclusivo disponível; a sobreposição foi preservada e nenhum caso foi substituído oportunisticamente.</div>'}</article>`).join('');root.querySelectorAll('select[data-classification-key]').forEach(select=>select.addEventListener('change',()=>{const key=decodeURIComponent(select.dataset.classificationKey);if(select.value)state.classifications[key]=select.value;else delete state.classifications[key];saveClassifications()}));updateClassificationCounter()}

async function executeQa(){if(state.running||!state.profile||!state.run)return;const audit=mainRunAudit(state.profile,state.run);if(!audit.ok)return alert('O run principal não está elegível para QA. Atualize a página e confira os bloqueios.');state.running=true;$('#runQaBtn').disabled=true;$('#downloadQaBtn').disabled=true;$('#qaSummary').classList.add('hidden');$('#branchResults').innerHTML='';
  try{const branchAudits=[];for(let index=0;index<state.profile.branches.length;index++){const branch=state.profile.branches[index];const result=await runBranch(state.profile,branch,index,state.profile.branches.length);branchAudits.push(branchAudit(state.profile,branch,result))}state.report=buildReport(state.profile,state.run,branchAudits);loadClassifications();renderSummary(state.report);renderBranches(state.report);$('#qaProgress').className='qa-state ok';$('#qaProgress').innerHTML='<strong>QA de execução concluído.</strong> Agora revise/classifique as amostras. Nenhuma decisão científica foi automatizada.';$('#downloadQaBtn').disabled=false}catch(error){$('#qaProgress').className='qa-state bad';$('#qaProgress').textContent=`QA interrompido: ${error.message}`}finally{state.running=false;renderMainRun()}}

function exportReport(){if(!state.report)return;const payload={...state.report,human_classifications:state.classifications};const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`${state.report.strategy_id}_${state.report.strategy_version}_QA_${state.report.main_search_id}.json`.replaceAll('/','-');document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url)}

$('#refreshQa').addEventListener('click',refresh);$('#runQaBtn').addEventListener('click',executeQa);$('#downloadQaBtn').addEventListener('click',exportReport);refresh();
