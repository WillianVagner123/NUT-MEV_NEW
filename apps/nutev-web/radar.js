const state={radar:null};
const $=selector=>document.querySelector(selector);

const PRIORITY_LABELS={P1_HIGH:'P1 · alta',P2_MEDIUM:'P2 · média',P3_LOW:'P3 · baixa',P4_MONITOR:'P4 · monitorar'};
const KIND_LABELS={topic:'Tópico',competency:'Competência',context:'Contexto',implementation:'Implementação',registry:'Registry',watch:'Watch'};
const FLAG_LABELS={no_documents:'sem documentos',low_document_count:'baixo volume',low_provider_diversity:'baixa diversidade de fontes',stale_or_unknown_recency:'recência insuficiente/desconhecida',no_full_text:'sem full text',semantic_incomplete:'semântica incompleta',relational_incomplete:'relações incompletas'};
const STATUS_LABELS={completed:'concluído',empty:'zero verificado',failed:'falhou',partial:'parcial',skipped:'ignorado',planned_not_executed:'não executado',queued:'aguardando',running:'executando',manual:'manual/licenciado',planned:'planejado',unknown:'desconhecido'};
const PROVIDER_LABELS={pubmed:'PubMed',europepmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs:'LILACS / BVS',scielo:'SciELO',scopus:'Scopus',wos:'Web of Science'};
const EVENT_LABELS={baseline_created:'baseline criado',profile_changed:'perfil alterado',profile_version_changed:'versão do perfil alterada',profile_status_changed:'status do perfil alterado',topic_added:'tópico adicionado',topic_removed:'tópico removido',document_added:'documento adicionado',document_removed:'documento removido',document_count_changed:'contagem documental alterada',provider_count_changed:'diversidade de providers alterada',full_text_count_changed:'cobertura de full text alterada',semantic_count_changed:'cobertura semântica alterada',relational_count_changed:'cobertura relacional alterada',provider_added:'provider adicionado',provider_removed:'provider removido',latest_year_changed:'recência alterada',flag_added:'gap adicionado',flag_resolved:'gap resolvido',priority_escalated:'prioridade escalada',priority_deescalated:'prioridade reduzida',priority_changed:'prioridade alterada'};
const CASE_LABELS={PROFILE_CHANGE_REVIEW:'revisar mudança de perfil',COVERAGE_REGRESSION_REVIEW:'revisar regressão de cobertura',NEW_MATERIAL_REVIEW:'revisar material novo',GAP_RESOLUTION_REVIEW:'confirmar resolução de gap'};

function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function formatDate(value){if(!value)return '—';const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'})}
function num(value){return Number(value||0).toLocaleString('pt-BR')}
function priorityRank(value){return ({P1_HIGH:1,P2_MEDIUM:2,P3_LOW:3,P4_MONITOR:4})[value]||99}
function flagLabel(value){return FLAG_LABELS[value]||value}
function providerLabel(value){return PROVIDER_LABELS[value]||value}
function statusLabel(value){return STATUS_LABELS[value]||value||'—'}
function kindLabel(value){return KIND_LABELS[value]||value||'Tópico'}
function eventLabel(value){return EVENT_LABELS[value]||value}
function caseLabel(value){return CASE_LABELS[value]||value}
function priorityClass(value){return ({P1_HIGH:'p1',P2_MEDIUM:'p2',P3_LOW:'p3',P4_MONITOR:'p4'})[value]||'p4'}
function stateClass(value){return ['failed','partial','skipped','manual','planned','completed'].includes(value)?value:'unknown'}

async function init(){
  $('#refreshRadar').onclick=loadRadar;
  $('#jumpChanges').onclick=()=>$('#watchSection').scrollIntoView({behavior:'smooth',block:'start'});
  ['topicFilter','kindFilter','priorityFilter','sortTopics','gapOnly'].forEach(id=>{$(`#${id}`).addEventListener('input',renderTopics)});
  $('#topicCards').addEventListener('click',event=>{const button=event.target.closest('[data-topic-id]');if(button)openTopic(button.dataset.topicId)});
  await loadRadar();
}

async function loadRadar(){
  const refresh=$('#refreshRadar');refresh.disabled=true;
  $('#radarState').className='loading';$('#radarState').textContent='Carregando auditoria verificada…';
  $('#radarContent').classList.add('hidden');
  try{
    const [healthRes,radarRes]=await Promise.all([fetch('/api/health',{cache:'no-store'}),fetch('/api/radar',{cache:'no-store'})]);
    const health=await healthRes.json();
    $('#radarHealth').textContent=health.status==='ok'?'engine conectado':'engine indisponível';
    $('#radarHealth').className=`status-pill ${health.status==='ok'?'ok':'bad'}`;
    const radar=await radarRes.json();
    if(!radarRes.ok)throw new Error(radar.message||radar.error||'Falha ao validar dados do Radar');
    state.radar=radar;
    if(radar.status!=='ready'){renderNotReady(radar);return}
    renderRadar(radar);
  }catch(error){
    $('#radarState').className='error';
    $('#radarState').innerHTML=`<strong>Radar bloqueado.</strong><div>${esc(error.message)}</div><div class="small-state">O painel não exibe métricas quando a cadeia de integridade não fecha.</div>`;
  }finally{refresh.disabled=false}
}

function renderNotReady(data){
  $('#radarState').className='radar-empty card';
  const commands=(data.next_commands||[]).map(command=>`<code>${esc(command)}</code>`).join('');
  $('#radarState').innerHTML=`<div class="empty-mark">⌁</div><div><h2>Radar ainda sem snapshot</h2><p>${esc(data.message||'Nenhuma auditoria disponível.')}</p><p class="small-state">O painel não usa números demonstrativos. Gere primeiro os outputs científicos canônicos.</p><div class="command-stack">${commands}</div></div>`;
}

function renderRadar(data){
  $('#radarState').className='hidden';$('#radarContent').classList.remove('hidden');
  const gate=data.profile?.formal_gate?.authorized===true?'gate formal autorizado':'gate formal não autorizado';
  const watchState=!data.watch?.available?'Watch ainda não executado':data.watch.stale?'Watch desatualizado':data.watch.baseline?'Watch baseline verificado':'Watch verificado';
  $('#radarMeta').innerHTML=`<div><span>Registry</span><strong>${esc(data.profile?.profile_id||'—')}</strong></div><div><span>Versão</span><strong>${esc(data.profile?.version||'—')}</strong></div><div><span>Status</span><strong>${esc(data.profile?.status||'—')}</strong><small>${esc(gate)}</small></div><div><span>Último audit</span><strong>${esc(formatDate(data.generated_from?.topic_audit_created_at))}</strong></div><div><span>Longitudinal</span><strong>${esc(watchState)}</strong></div>`;
  renderSummary(data.summary||{});
  renderPriorities(data.summary?.priority_counts||{});
  renderProviders(data.providers||[]);
  renderTopics();
  renderWatch(data.watch||{});
}

function renderSummary(summary){
  const cards=[
    ['Tópicos / competências',num(summary.topics),'unidades auditadas'],
    ['Documentos únicos',num(summary.unique_documents),'mapeados ao menos uma vez'],
    ['Providers observados',num(summary.providers_observed),'presentes no banco atual'],
    ['Tópicos com gaps',num(summary.topics_with_gaps),'flags técnicas ativas'],
    ['Busca ativa requerida',num(summary.active_search_required),'prioridade P1–P3 ou gap ativo']
  ];
  $('#summaryCards').innerHTML=cards.map(([label,value,note])=>`<div class="radar-kpi card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
}

function renderPriorities(counts){
  const rows=['P1_HIGH','P2_MEDIUM','P3_LOW','P4_MONITOR'];
  $('#priorityBoard').innerHTML=rows.map(priority=>`<button type="button" class="priority-tile ${priorityClass(priority)}" data-priority-filter="${priority}"><span>${esc(PRIORITY_LABELS[priority])}</span><strong>${num(counts[priority]||0)}</strong><small>${priority==='P1_HIGH'?'sem cobertura / ação imediata':priority==='P2_MEDIUM'?'baixo volume ou recência':priority==='P3_LOW'?'completude técnica': 'sem gap atual'}</small></button>`).join('');
  $('#priorityBoard').querySelectorAll('[data-priority-filter]').forEach(button=>button.onclick=()=>{$('#priorityFilter').value=button.dataset.priorityFilter;renderTopics();$('#topicCards').scrollIntoView({behavior:'smooth',block:'start'})});
}

function renderProviders(providers){
  $('#providerBoard').innerHTML=providers.length?providers.map(provider=>{
    const counts=Object.entries(provider.status_counts||{}).map(([status,count])=>`${statusLabel(status)} ${count}`).join(' · ');
    const note=provider.manual_licensed?'manual/licenciado':provider.status_aware?'status-aware':'sem contrato informado';
    return `<div class="provider-row"><div><strong>${esc(providerLabel(provider.provider))}</strong><small>${esc(note)}</small></div><span class="provider-state ${stateClass(provider.state)}">${esc(statusLabel(provider.state))}</span><div class="provider-run-counts">${esc(counts||'sem execução registrada')}</div></div>`
  }).join(''):'<div class="radar-empty-inline">Nenhum estado de provider disponível.</div>';
}

function filteredTopics(){
  const data=state.radar;if(!data)return[];
  const query=$('#topicFilter').value.trim().toLocaleLowerCase('pt-BR');
  const kind=$('#kindFilter').value;const priority=$('#priorityFilter').value;const gapOnly=$('#gapOnly').checked;const sort=$('#sortTopics').value;
  const rows=(data.topics||[]).filter(topic=>{
    const haystack=[topic.label,topic.topic_id,topic.topic_kind,...(topic.flags||[])].join(' ').toLocaleLowerCase('pt-BR');
    return (!query||haystack.includes(query))&&(!kind||topic.topic_kind===kind)&&(!priority||topic.active_search_priority===priority)&&(!gapOnly||(topic.flags||[]).length>0);
  });
  rows.sort((a,b)=>{
    if(sort==='documents')return Number(b.document_count||0)-Number(a.document_count||0)||String(a.label).localeCompare(String(b.label),'pt-BR');
    if(sort==='freshness')return Number(b.latest_year||0)-Number(a.latest_year||0)||String(a.label).localeCompare(String(b.label),'pt-BR');
    if(sort==='label')return String(a.label).localeCompare(String(b.label),'pt-BR');
    return priorityRank(a.active_search_priority)-priorityRank(b.active_search_priority)||Number(b.document_count||0)-Number(a.document_count||0)||String(a.label).localeCompare(String(b.label),'pt-BR');
  });
  return rows;
}

function renderTopics(){
  const rows=filteredTopics();if(!state.radar)return;
  $('#topicCount').textContent=`${rows.length} de ${(state.radar.topics||[]).length} unidades exibidas`;
  $('#topicCards').innerHTML=rows.length?rows.map(renderTopicCard).join(''):'<div class="radar-empty-inline">Nenhum tópico corresponde aos filtros atuais.</div>';
}

function coverageBar(label,count,total,pct){return `<div class="coverage-line"><div><span>${esc(label)}</span><strong>${num(count)} / ${num(total)}</strong></div><div class="meter"><span style="width:${Math.max(0,Math.min(100,Number(pct||0)))}%"></span></div></div>`}

function topicDelta(topic){
  if(!state.radar?.watch?.available)return '<span class="muted-delta">Watch ainda não executado</span>';
  if(state.radar.watch.stale)return '<span class="muted-delta warning-text">Watch desatualizado para este audit</span>';
  const events=topic.watch?.events||[];if(!events.length)return '<span class="muted-delta">sem mudança no último Watch</span>';
  const added=events.filter(event=>event.event_type==='document_added').length;
  const removed=events.filter(event=>event.event_type==='document_removed').length;
  const providerAdded=events.filter(event=>event.event_type==='provider_added').length;
  const flags=events.filter(event=>['flag_added','flag_resolved'].includes(event.event_type)).length;
  const bits=[];if(added)bits.push(`+${added} doc${added===1?'':'s'}`);if(removed)bits.push(`−${removed} doc${removed===1?'':'s'}`);if(providerAdded)bits.push(`+${providerAdded} provider`);if(events.some(event=>event.event_type==='latest_year_changed'))bits.push('recência mudou');if(flags)bits.push(`${flags} mudança${flags===1?'':'s'} de gap`);return `<span class="delta-live">${esc(bits.join(' · ')||`${events.length} evento${events.length===1?'':'s'}`)}</span>`;
}

function renderTopicCard(topic){
  const flags=(topic.flags||[]).map(flag=>`<span class="flag-chip">${esc(flagLabel(flag))}</span>`).join('')||'<span class="flag-chip clear">sem gap atual</span>';
  const cases=topic.watch?.cases||[];const caseBadge=cases.length?`<span class="watch-case-badge">${esc(cases[0].watch_priority||'review')} · ${esc(caseLabel(cases[0].case_type))}</span>`:'';
  return `<article class="topic-card ${priorityClass(topic.active_search_priority)}"><div class="topic-card-head"><div><div class="topic-label-row"><span class="kind-badge">${esc(kindLabel(topic.topic_kind))}</span><span class="priority-badge ${priorityClass(topic.active_search_priority)}">${esc(PRIORITY_LABELS[topic.active_search_priority]||topic.active_search_priority)}</span></div><h3>${esc(topic.label)}</h3><p>${esc(topic.topic_id)}</p></div><button class="ghost detail-btn" type="button" data-topic-id="${esc(topic.topic_id)}">Detalhes</button></div><div class="topic-metrics"><div><strong>${num(topic.document_count)}</strong><span>documentos</span></div><div><strong>${num(topic.provider_count)}</strong><span>providers</span></div><div><strong>${topic.latest_year??'—'}</strong><span>último ano</span></div></div><div class="coverage-mini">${coverageBar('Full text',topic.full_text_count,topic.document_count,topic.coverage?.full_text_pct)}${coverageBar('Semântica',topic.semantic_count,topic.document_count,topic.coverage?.semantic_pct)}${coverageBar('Relações',topic.relational_count,topic.document_count,topic.coverage?.relational_pct)}</div><div class="flag-row">${flags}</div><div class="topic-footer"><div>⌁ ${topicDelta(topic)}</div>${caseBadge}</div></article>`;
}

function renderWatch(watch){
  const badge=$('#watchBadge');
  if(!watch.available){badge.textContent='não executado';badge.className='status-pill';$('#watchSummary').innerHTML=`<div class="watch-notice">${esc(watch.message||'Nenhum Watch disponível.')}</div>`;$('#watchCases').innerHTML='<div class="radar-empty-inline">Sem casos longitudinais.</div>';$('#watchEvents').innerHTML='<div class="radar-empty-inline">Sem eventos longitudinais.</div>';return}
  badge.textContent=watch.stale?'desatualizado':watch.baseline?'baseline':'verificado';badge.className=`status-pill ${watch.stale?'bad':'ok'}`;
  const counts=watch.counts||{};
  $('#watchSummary').innerHTML=`<div class="watch-summary-grid"><div><span>Executado</span><strong>${esc(formatDate(watch.created_at))}</strong></div><div><span>Comparabilidade</span><strong>${esc(watch.comparability||'—')}</strong></div><div><span>Eventos</span><strong>${num(counts.events||0)}</strong></div><div><span>Casos</span><strong>${num(counts.cases||0)}</strong></div></div>${watch.stale?`<div class="warning"><strong>Watch desatualizado.</strong> ${esc(watch.message||'Os deltas pertencem a uma auditoria anterior.')}</div>`:watch.baseline?'<div class="review-result-note">Este é o baseline verificado. Ainda não há comparação longitudinal anterior.</div>':''}`;
  const cases=watch.cases||[];$('#watchCases').innerHTML=cases.length?cases.map(item=>`<div class="watch-item"><div><span class="watch-priority ${String(item.watch_priority||'').toLowerCase()}">${esc(item.watch_priority||'review')}</span><strong>${esc(item.topic_id==='__profile__'?'Registry':topicName(item.topic_id))}</strong></div><p>${esc(caseLabel(item.case_type))}</p><small>${esc(item.action||'revisão humana requerida')}</small></div>`).join(''):'<div class="radar-empty-inline">Nenhum caso de revisão no último Watch.</div>';
  const events=watch.events||[];$('#watchEvents').innerHTML=events.length?events.slice(0,40).map(item=>`<div class="watch-item compact"><div><strong>${esc(item.topic_id==='__watch__'?'Watch':item.topic_id==='__profile__'?'Registry':topicName(item.topic_id))}</strong><span>${esc(eventLabel(item.event_type))}</span></div><small>${esc(eventValue(item))}</small></div>`).join(''):'<div class="radar-empty-inline">Nenhum evento no último Watch.</div>';
}

function topicName(topicId){const topic=(state.radar?.topics||[]).find(item=>item.topic_id===topicId);return topic?.label||topicId}
function eventValue(event){if(event.document_id)return event.document_id;if(event.before!==undefined||event.after!==undefined){const before=typeof event.before==='object'?JSON.stringify(event.before):event.before;const after=typeof event.after==='object'?JSON.stringify(event.after):event.after;return `${before??'—'} → ${after??'—'}`}return event.basis||''}

function openTopic(topicId){
  const topic=(state.radar?.topics||[]).find(item=>item.topic_id===topicId);if(!topic)return;
  $('#dialogKind').textContent=kindLabel(topic.topic_kind);$('#dialogTitle').textContent=topic.label;$('#dialogId').textContent=topic.topic_id;
  const flags=(topic.flags||[]).map(flag=>`<span class="flag-chip">${esc(flagLabel(flag))}</span>`).join('')||'<span class="flag-chip clear">sem gap atual</span>';
  const searchRuns=(topic.search_runs||[]).map(run=>`<tr><td>${esc(providerLabel(run.provider))}</td><td><span class="run-status ${stateClass(run.status)}">${esc(statusLabel(run.status))}</span></td><td>${run.total_found===null||run.total_found===undefined?'—':num(run.total_found)}</td><td>${num(run.total_returned||0)}</td><td>${esc(run.error||'—')}</td></tr>`).join('')||'<tr><td colspan="5">Sem runs registrados.</td></tr>';
  const plan=(topic.search_plan||[]).map((item,index)=>`<details class="query-detail"><summary>${esc(providerLabel(item.provider))} · ${esc(item.execution||'planejado')}</summary><code>${esc(item.query||'')}</code><button type="button" class="ghost copy-query" data-query-index="${index}">Copiar query</button></details>`).join('')||'<div class="radar-empty-inline">Sem plano de busca para este tópico.</div>';
  const events=topic.watch?.events||[];const cases=topic.watch?.cases||[];
  $('#dialogBody').innerHTML=`<div class="dialog-actions"><span class="priority-badge ${priorityClass(topic.active_search_priority)}">${esc(PRIORITY_LABELS[topic.active_search_priority]||topic.active_search_priority)}</span><a class="primary action-link" href="/?q=${encodeURIComponent(topic.label)}">Abrir busca pelo tópico</a></div><div class="dialog-metrics"><div><strong>${num(topic.document_count)}</strong><span>documentos</span></div><div><strong>${num(topic.provider_count)}</strong><span>providers</span></div><div><strong>${topic.latest_year??'—'}</strong><span>último ano</span></div><div><strong>${num(topic.full_text_count)}</strong><span>full text</span></div><div><strong>${num(topic.semantic_count)}</strong><span>semântica</span></div><div><strong>${num(topic.relational_count)}</strong><span>relações</span></div></div><section class="dialog-section"><h3>Gaps atuais</h3><div class="flag-row">${flags}</div></section><section class="dialog-section"><h3>Providers do banco</h3><div class="provider-chip-list">${(topic.providers||[]).map(provider=>`<span>${esc(providerLabel(provider))}</span>`).join('')||'<span>nenhum</span>'}</div></section><section class="dialog-section"><h3>Execução de busca ativa</h3><div class="table-wrap"><table class="run-table"><thead><tr><th>Provider</th><th>Status</th><th>Encontrados</th><th>Retornados</th><th>Observação</th></tr></thead><tbody>${searchRuns}</tbody></table></div></section><section class="dialog-section"><h3>Plano reproduzível</h3>${plan}</section><section class="dialog-section"><h3>Watch deste tópico</h3>${state.radar.watch?.stale?'<div class="warning">Watch desatualizado; deltas não são ligados ao estado atual.</div>':events.length?events.map(event=>`<div class="watch-item compact"><div><strong>${esc(eventLabel(event.event_type))}</strong><span>${esc(event.direction||'')}</span></div><small>${esc(eventValue(event))}</small></div>`).join(''):'<div class="radar-empty-inline">Sem mudança longitudinal anexada.</div>'}${cases.length?`<div class="dialog-cases">${cases.map(item=>`<span class="watch-case-badge">${esc(item.watch_priority)} · ${esc(caseLabel(item.case_type))}</span>`).join('')}</div>`:''}</section>`;
  $('#dialogBody').querySelectorAll('.copy-query').forEach(button=>button.onclick=async()=>{const item=(topic.search_plan||[])[Number(button.dataset.queryIndex)];if(!item)return;try{await navigator.clipboard.writeText(String(item.query||''));button.textContent='Copiado'}catch{button.textContent='Falha ao copiar'}});
  $('#topicDialog').showModal();
}

document.addEventListener('DOMContentLoaded',init);
