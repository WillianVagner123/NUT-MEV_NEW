import{canonicalDocumentClass,documentClassLabel,documentSubtypeLabel}from'./document-classes.js';
import{countSavedArticles,getSavedArticle,listSavedArticles,removeSavedArticle,sourceUrlFor}from'./saved-library.js';

const providerLabels={pubmed:'PubMed',europepmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs_native:'LILACS/BVS',scielo_native:'SciELO'};
const confidenceLabels={high:'alta',medium:'média',low:'sinal insuficiente'};
let selectedKey='';let debounce=null;

const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmtScore=value=>value===null||value===undefined||value===''?'—':Number(value).toLocaleString('pt-BR',{maximumFractionDigits:2});
function classPresentation(value){const canonical=canonicalDocumentClass(value);const primary=documentClassLabel(canonical);const subtype=documentSubtypeLabel(value);return{primary,subtype:subtype!==primary?subtype:''}}

function installShell(){
  const topbar=document.querySelector('.articles-main .topbar');if(!topbar||document.querySelector('#savedCore'))return;
  topbar.insertAdjacentHTML('afterend',`<section id="savedCore" class="saved-core card" aria-labelledby="savedCoreTitle">
    <div class="saved-core-head">
      <div><h2 id="savedCoreTitle">Meus salvos</h2><p>Resultados guardados das suas buscas, deduplicados por DOI, PMID, URL ou identidade bibliográfica. Persistem neste navegador e não alteram o corpus científico verificado.</p></div>
      <div class="saved-core-count"><strong id="savedCoreCount">0</strong><span>salvos</span></div>
    </div>
    <div class="saved-core-tools"><label>Filtrar meus salvos<input id="savedCoreQuery" type="search" autocomplete="off" placeholder="Título, DOI, PMID, revista ou busca de origem"></label><button id="refreshSavedCore" class="ghost" type="button">Atualizar</button></div>
    <div id="savedCoreState" class="saved-core-state">Carregando Biblioteca local…</div>
    <div id="savedCoreLayout" class="saved-core-layout hidden"><div id="savedCoreList" class="saved-core-list"></div><aside id="savedCoreDetail" class="saved-core-detail"><div class="detail-placeholder"><div class="placeholder-mark">★</div><strong>Selecione um artigo salvo</strong><p>O dossiê de busca abre aqui com classificação, ranking e proveniência.</p></div></aside></div>
  </section>`);
}

function savedRow(item){
  const ids=[item.doi?`DOI ${item.doi}`:'',item.pmid?`PMID ${item.pmid}`:''].filter(Boolean);
  const latest=(item.provenance||[]).at(-1)||{};
  const classification=classPresentation(item.document_class);
  const chips=[item.year,classification.primary,classification.subtype,providerLabels[item.source_provider]||item.source_provider,item.classification_confidence?`classificação ${confidenceLabels[item.classification_confidence]||item.classification_confidence}`:''].filter(Boolean);
  return `<article class="saved-core-row${selectedKey===item.key?' active':''}" data-saved-key="${esc(item.key)}">
    <button type="button" class="saved-core-open" data-open-saved="${esc(item.key)}"><strong>${esc(item.title||'Sem título')}</strong><div class="saved-core-meta">${chips.map(value=>`<span>${esc(value)}</span>`).join('')}</div>${ids.length?`<div class="saved-core-ids">${ids.map(value=>`<span>${esc(value)}</span>`).join('')}</div>`:''}${latest.search_query?`<div class="saved-core-origin">Busca: ${esc(latest.search_query)}</div>`:''}</button>
    <div class="saved-core-row-actions">${item.source_url?`<a href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">Fonte ↗</a>`:''}<button class="ghost" type="button" data-remove-saved="${esc(item.key)}">Remover</button></div>
  </article>`;
}

function provenanceHtml(entries){
  if(!entries?.length)return'<p class="provenance">Nenhuma proveniência de busca registrada.</p>';
  return `<div class="saved-provenance-list">${entries.slice().reverse().map(entry=>`<div class="saved-provenance-item"><strong>${esc(entry.search_query||'Busca sem título')}</strong><span>${esc(providerLabels[entry.source_provider]||entry.source_provider||'fonte n/d')} · rank ${esc(entry.reference_rank??'—')} · score ${esc(fmtScore(entry.reference_score))}</span>${entry.provider_query?`<details><summary>Query executada na fonte</summary><code>${esc(entry.provider_query)}</code></details>`:''}</div>`).join('')}</div>`;
}

function savedDetailHtml(item){
  const article=item.article||{};const classification=article.search_classification||{};
  const source=item.source_url||sourceUrlFor(article);const classInfo=classPresentation(item.document_class);
  const chips=[item.year,item.journal,classInfo.primary,classInfo.subtype,providerLabels[item.source_provider]||item.source_provider,item.classification_confidence?`Confiança da classificação: ${confidenceLabels[item.classification_confidence]||item.classification_confidence}`:'',classification.taxonomy_primary||item.taxonomy_primary].filter(Boolean);
  const reasons=[];const match=classification.query_match||{};
  if((match.title_hits||[]).length)reasons.push(`título: ${(match.title_hits||[]).slice(0,6).join(', ')}`);
  if((match.abstract_hits||[]).length)reasons.push(`resumo: ${(match.abstract_hits||[]).slice(0,6).join(', ')}`);
  return `<div class="detail-head"><h2>${esc(item.title||'Sem título')}</h2><div class="detail-chips">${chips.map(value=>`<span class="mini-pill">${esc(value)}</span>`).join('')}</div></div>
    <section class="detail-section"><h3>Resumo salvo</h3><p class="saved-abstract">${esc(article.abstract||'Resumo não disponível neste resultado.')}</p></section>
    <section class="detail-section"><h3>Como o NutEV o encontrou</h3>${reasons.length?`<p class="provenance">${esc(reasons.join(' · '))}</p>`:'<p class="provenance">Sem termos de correspondência materializados neste registro.</p>'}<p class="provenance">Ranking salvo: ${esc(fmtScore(article.reference_score))} · relevância para a consulta: ${esc(fmtScore(article.query_relevance_score))} · prioridade NutEV: ${esc(fmtScore(article.nutev_priority_score))}.</p></section>
    <section class="detail-section"><h3>Proveniência das buscas</h3>${provenanceHtml(item.provenance||[])}</section>
    <section class="detail-section"><h3>Identidade e fonte</h3><p class="provenance">${item.doi?`DOI ${esc(item.doi)} · `:''}${item.pmid?`PMID ${esc(item.pmid)} · `:''}chave canônica ${esc(item.key)}</p>${source?`<p><a href="${esc(source)}" target="_blank" rel="noopener noreferrer">Abrir fonte original ↗</a></p>`:''}</section>
    <section class="detail-section"><h3>Fronteira científica</h3><p class="provenance">Artigo salvo = item de leitura/indexação. Não equivale a inclusão em revisão, qualidade metodológica, risco de viés, certeza/GRADE, causalidade ou recomendação.</p></section>`;
}

async function openSaved(key){
  selectedKey=key;document.querySelectorAll('.saved-core-row').forEach(row=>row.classList.toggle('active',row.dataset.savedKey===key));
  const detail=$('#savedCoreDetail');detail.innerHTML='<div class="detail-placeholder"><strong>Carregando dossiê salvo…</strong></div>';
  try{const item=await getSavedArticle(key);if(!item)throw new Error('Artigo salvo não encontrado.');detail.innerHTML=savedDetailHtml(item)}
  catch(error){detail.innerHTML=`<div class="detail-placeholder"><strong>Não foi possível abrir este salvo.</strong><p>${esc(error.message)}</p></div>`}
}

async function loadSaved(){
  installShell();const state=$('#savedCoreState');const layout=$('#savedCoreLayout');if(!state||!layout)return;
  state.classList.remove('hidden');state.textContent='Carregando Biblioteca local…';
  try{
    const q=$('#savedCoreQuery')?.value?.trim()||'';const [items,total]=await Promise.all([listSavedArticles({q,limit:1000}),countSavedArticles()]);
    $('#savedCoreCount').textContent=String(total);
    $('#savedCoreList').innerHTML=items.map(savedRow).join('')||'<div class="saved-core-empty"><strong>Nenhum artigo salvo neste filtro.</strong><p>Na busca, use “Guardar na Biblioteca” ou “Abrir dossiê”.</p></div>';
    layout.classList.remove('hidden');state.classList.add('hidden');
  }catch(error){layout.classList.add('hidden');state.textContent=error.message||'Biblioteca local indisponível.';state.classList.add('bad')}
}

function bindEvents(){
  $('#refreshSavedCore')?.addEventListener('click',loadSaved);
  $('#savedCoreQuery')?.addEventListener('input',()=>{clearTimeout(debounce);debounce=setTimeout(loadSaved,220)});
  $('#savedCoreList')?.addEventListener('click',async event=>{
    const open=event.target.closest('[data-open-saved]');if(open){await openSaved(open.dataset.openSaved);return}
    const remove=event.target.closest('[data-remove-saved]');if(remove){await removeSavedArticle(remove.dataset.removeSaved);if(selectedKey===remove.dataset.removeSaved){selectedKey='';$('#savedCoreDetail').innerHTML='<div class="detail-placeholder"><div class="placeholder-mark">★</div><strong>Selecione um artigo salvo</strong></div>'}await loadSaved()}
  });
}

async function init(){
  installShell();bindEvents();await loadSaved();
  const requested=new URLSearchParams(location.search).get('saved');if(requested)await openSaved(requested);
}

init();
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')loadSaved()});