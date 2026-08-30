const state={cursor:null,loading:false,selected:null,debounce:null};
const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const fmtScore=value=>value===null||value===undefined||value===''?'—':Number(value).toLocaleString('pt-BR',{maximumFractionDigits:2});

const kindLabels={objective:'Objetivo',method:'Método / contexto',main_result:'Resultado principal',secondary_result:'Resultado secundário',conclusion:'Conclusão',limitation:'Limitação',disclosure:'Financiamento / conflitos'};
const classLabels={primary_randomized:'Ensaio randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Diretriz / guidance',unclassified:'Não classificado'};
const providerLabels={pubmed:'PubMed',europepmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs_native:'LILACS/BVS',scielo_native:'SciELO'};
const fullTextLabels={retrieved:'Texto completo',partial:'Texto parcial',unavailable:'Sem texto completo',not_attempted:'Ainda não buscado',not_retrieved:'Não recuperado'};

function tierFromReference(value){const match=String(value||'').match(/^BANK_([ABCD])_PROCESSING_PRIORITY$/);return match?match[1]:''}
function tierLabel(value){const tier=tierFromReference(value);return tier?`Tier ${tier}`:''}

function currentParams(cursor=null){
  const params=new URLSearchParams();
  const q=$('#articleQuery').value.trim();
  const tier=$('#tierFilter').value;
  const sort=$('#sortFilter').value||'relevance';
  const provider=$('#providerFilter').value;
  const docClass=$('#classFilter').value;
  const fullText=$('#fullTextFilter').value;
  const qParts=[];
  if(q)qParts.push(q);
  if(tier)qParts.push(`__nutev_tier:${tier}`);
  if(sort)qParts.push(`__nutev_sort:${sort}`);
  if(qParts.length)params.set('q',qParts.join(' '));
  if(provider)params.set('source_provider',provider);
  if(docClass)params.set('document_class',docClass);
  if(fullText)params.set('full_text_status',fullText);
  if(cursor)params.set('cursor',cursor);
  params.set('limit','50');
  return params;
}

function setState(message,type=''){
  const node=$('#workbenchState');
  node.textContent=message;
  node.className=`workbench-state ${type}`.trim();
}

function articleRow(article){
  const full=fullTextLabels[article.full_text_status]||article.full_text_status||'Texto não informado';
  const fullGood=article.full_text_status==='retrieved';
  const ids=[article.doi?`DOI ${article.doi}`:'',article.pmid?`PMID ${article.pmid}`:''].filter(Boolean);
  const tier=tierLabel(article.reference_tier);
  const priority=[tier,article.reference_rank?`rank #${fmt(article.reference_rank)}`:'',article.reference_score!==null&&article.reference_score!==undefined?`score ${fmtScore(article.reference_score)}`:''].filter(Boolean);
  return `<button class="article-row${state.selected===article.document_id?' active':''}" type="button" data-document-id="${esc(article.document_id)}">
    <div>
      <div class="article-title">${esc(article.title||'Sem título')}</div>
      <div class="article-meta">
        <span>${esc(article.year||'ano n/d')}</span>
        <span>${esc(classLabels[article.document_class]||article.document_class||'tipo n/d')}</span>
        <span>${esc(providerLabels[article.source_provider]||article.source_provider||'fonte n/d')}</span>
      </div>
      ${ids.length?`<div class="article-identifiers">${ids.map(id=>`<span>${esc(id)}</span>`).join('')}</div>`:''}
    </div>
    <div class="article-row-side">
      ${priority.map(value=>`<span class="mini-pill">${esc(value)}</span>`).join('')}
      <span class="mini-pill ${fullGood?'good':''}">${esc(full)}</span>
      <span class="mini-pill">contexto IA ${fmt(article.llm_context_chars)} chars</span>
    </div>
  </button>`;
}

async function loadPage({append=false}={}){
  if(state.loading)return;
  state.loading=true;
  $('#loadMore').disabled=true;
  if(!append)setState('Consultando índice…');
  try{
    const cursor=append?state.cursor:null;
    const response=await fetch(`/api/articles?${currentParams(cursor)}`,{cache:'no-store'});
    const data=await response.json();
    if(!response.ok)throw new Error(data.message||data.error||'Falha ao consultar artigos');
    if(data.status==='not_ready'){
      $('#articleHealth').textContent='índice ainda não criado';
      $('#articleHealth').className='status-pill';
      $('#articleCount').textContent='0';
      $('#workbenchContent').classList.add('hidden');
      setState(data.message||'Workbench ainda sem índice.','bad');
      return;
    }
    if(data.status!=='ready')throw new Error(data.message||'Workbench indisponível');
    $('#articleHealth').textContent=data.performance?.server_side_priority_sort?'banco + prioridade verificados':'banco verificado';
    $('#articleHealth').className='status-pill ok';
    $('#articleCount').textContent=fmt(data.total_filtered);
    state.cursor=data.next_cursor||null;
    const html=(data.articles||[]).map(articleRow).join('');
    if(append)$('#articleList').insertAdjacentHTML('beforeend',html);
    else $('#articleList').innerHTML=html||'<div class="detail-placeholder"><strong>Nenhum artigo neste filtro.</strong><p>Altere a busca ou os filtros.</p></div>';
    $('#loadMore').classList.toggle('hidden',!state.cursor);
    $('#workbenchContent').classList.remove('hidden');
    $('#workbenchState').classList.add('hidden');
  }catch(error){
    $('#articleHealth').textContent='erro no índice';
    $('#articleHealth').className='status-pill bad';
    $('#workbenchContent').classList.add('hidden');
    setState(error.message,'bad');
  }finally{
    state.loading=false;
    $('#loadMore').disabled=false;
  }
}

function snapshotHtml(snapshot){
  const entries=Object.entries(snapshot||{}).filter(([,values])=>Array.isArray(values)?values.length:Boolean(values));
  if(!entries.length)return '<p class="provenance">Nenhum campo semântico compacto disponível.</p>';
  const labels={objective:'Objetivo',population:'População',sample_size:'Amostra',intervention:'Intervenção',exposure:'Exposição',comparator:'Comparador',outcome:'Outcomes',duration:'Duração',follow_up:'Seguimento',limitation:'Limitações'};
  return `<div class="snapshot-grid">${entries.map(([key,values])=>`<div class="snapshot-item"><strong>${esc(labels[key]||key)}</strong><span>${esc((Array.isArray(values)?values:[values]).join(' · '))}</span></div>`).join('')}</div>`;
}

function resultHtml(result){
  const numbers=[...(result.effect_measures||[]),...(result.confidence_intervals||[]),...(result.p_values||[])];
  const outcomes=(result.outcomes||[]).filter(Boolean);
  return `<article class="result-card ${result.result_kind==='main_result'?'main':''}">
    <div class="result-card-head"><strong>${result.result_kind==='main_result'?'Resultado principal':'Resultado secundário'}</strong><span class="mini-pill">candidato</span></div>
    ${outcomes.length?`<div class="provenance"><strong>Outcome:</strong> ${esc(outcomes.join(' · '))}</div>`:''}
    ${numbers.length?`<div class="result-numbers">${numbers.map(value=>`<span class="result-number">${esc(value)}</span>`).join('')}</div>`:''}
    <blockquote class="source-quote">${esc(result.result_text||'')}</blockquote>
    <div class="provenance">Trecho-fonte rastreável · não é EvidenceClaim validado.</div>
  </article>`;
}

function excerptHtml(excerpt){
  const reference=excerpt.reference||{};
  const location=[excerpt.section,excerpt.locator].filter(Boolean).join(' · ');
  const ids=[reference.doi?`DOI ${reference.doi}`:'',reference.pmid?`PMID ${reference.pmid}`:''].filter(Boolean).join(' · ');
  return `<article class="quote-card">
    <div class="quote-head"><span class="quote-kind">${esc(kindLabels[excerpt.kind]||excerpt.kind)}</span><span>${esc(location)}</span></div>
    <blockquote class="source-quote">${esc(excerpt.verbatim_excerpt||'')}</blockquote>
    <div class="provenance">${esc(ids)}${ids?' · ':''}SHA ${esc(String(excerpt.excerpt_sha256||'').slice(0,12))}…</div>
  </article>`;
}

function detailHtml(data){
  const card=data.card||{};
  const identity=card.identity||{};
  const reference=card.reference||{};
  const priority=data.bank_priority||{};
  const results=data.result_bundles||[];
  const supporting=(data.evidence_excerpts||[]).filter(item=>!['main_result','secondary_result'].includes(item.kind));
  const chips=[identity.year,classLabels[card.document_class]||card.document_class,providerLabels[identity.source_provider]||identity.source_provider,fullTextLabels[card.full_text_status]||card.full_text_status,tierLabel(priority.reference_tier),priority.reference_rank?`rank #${fmt(priority.reference_rank)}`:'',priority.reference_score!==null&&priority.reference_score!==undefined?`score ${fmtScore(priority.reference_score)}`:''].filter(Boolean);
  return `<div class="detail-head">
    <h2>${esc(identity.title||'Sem título')}</h2>
    <div class="detail-ref">${esc(reference.reference_stub||'Referência incompleta')}</div>
    <div class="detail-chips">${chips.map(value=>`<span class="mini-pill">${esc(value)}</span>`).join('')}</div>
  </div>
  <section class="detail-section"><h3>Visão rápida</h3>${snapshotHtml(card.study_snapshot)}</section>
  <section class="detail-section"><h3>Principais resultados</h3>${results.length?results.map(resultHtml).join(''):'<p class="provenance">Nenhum ResultBundle materializado para este artigo.</p>'}</section>
  <section class="detail-section"><h3>Trechos-chave</h3>${supporting.length?supporting.map(excerptHtml).join(''):'<p class="provenance">Nenhum trecho adicional selecionado.</p>'}</section>
  <section class="detail-section"><h3>Prioridade operacional</h3>
    <div class="provenance">${esc(tierLabel(priority.reference_tier)||'Tier n/d')} · rank ${esc(priority.reference_rank?`#${fmt(priority.reference_rank)}`:'n/d')} · score ${esc(fmtScore(priority.reference_score))}. Esses valores orientam ordem de leitura/processamento e não são julgamento científico.</div>
  </section>
  <section class="detail-section"><h3>Proveniência e custo</h3>
    <div class="provenance">Cache: ${esc(String(card.cache_key||'').slice(0,16))}… · contexto compacto: ${fmt(card.llm_context_chars)} caracteres · chamadas externas de LLM nesta etapa: ${Number(card.token_cost_policy?.external_llm_calls||0)} · texto integral enviado para LLM: ${card.token_cost_policy?.full_text_sent_to_llm?'sim':'não'}.</div>
  </section>`;
}

async function openArticle(documentId){
  state.selected=documentId;
  document.querySelectorAll('.article-row').forEach(row=>row.classList.toggle('active',row.dataset.documentId===documentId));
  $('#articleDetail').innerHTML='<div class="detail-placeholder"><strong>Carregando dossiê…</strong></div>';
  try{
    const response=await fetch(`/api/articles/${encodeURIComponent(documentId)}`,{cache:'no-store'});
    const data=await response.json();
    if(!response.ok)throw new Error(data.message||data.error||'Artigo não encontrado');
    $('#articleDetail').innerHTML=detailHtml(data);
  }catch(error){
    $('#articleDetail').innerHTML=`<div class="detail-placeholder"><strong>Não foi possível abrir o artigo.</strong><p>${esc(error.message)}</p></div>`;
  }
}

function resetAndLoad(){state.cursor=null;state.selected=null;$('#articleDetail').innerHTML='<div class="detail-placeholder"><div class="placeholder-mark">▤</div><strong>Selecione um artigo</strong><p>O dossiê abre aqui sem tirar você da lista.</p></div>';loadPage();}
function debouncedLoad(){clearTimeout(state.debounce);state.debounce=setTimeout(resetAndLoad,260)}

$('#articleQuery').addEventListener('input',debouncedLoad);
['tierFilter','sortFilter','providerFilter','classFilter','fullTextFilter'].forEach(id=>$('#'+id).addEventListener('change',resetAndLoad));
$('#clearFilters').addEventListener('click',()=>{$('#articleQuery').value='';$('#tierFilter').value='';$('#sortFilter').value='relevance';$('#providerFilter').value='';$('#classFilter').value='';$('#fullTextFilter').value='';resetAndLoad()});
$('#loadMore').addEventListener('click',()=>loadPage({append:true}));
$('#articleList').addEventListener('click',event=>{const row=event.target.closest('.article-row');if(row)openArticle(row.dataset.documentId)});

loadPage();
