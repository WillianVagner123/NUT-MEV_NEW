const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const classLabels={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',implementation_evaluation:'Implementação',primary_randomized:'Randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const domainLabels={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Lifestyle Medicine',implementation_practice:'Implementação'};
const stopWords=new Set(['a','as','o','os','de','da','das','do','dos','e','em','para','por','com','que','quais','qual','como','sobre','the','of','and','for','in','to','which','what','with','from','related','documentos','documento','artigos','artigo']);
let articles=[];
let results=[];
const selected=new Set();

const normalize=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const tokens=value=>[...new Set(normalize(value).split(/[^a-z0-9]+/).filter(token=>token.length>2&&!stopWords.has(token)))];
const flatten=value=>Array.isArray(value)?value.flatMap(flatten):value&&typeof value==='object'?Object.values(value).flatMap(flatten):[String(value??'')];
const effectiveClass=row=>row.review_profile?.primary_document_class||row.document_class||'unclassified';
const domains=row=>row.review_profile?.operational_domains||[];
const matchedTerms=row=>[
  ...flatten(row.review_profile?.document_class_matches||{}),
  ...flatten(row.review_profile?.operational_domain_matches||{})
].filter(Boolean);

function searchable(row){return normalize([
  row.title,row.reference_stub,effectiveClass(row),classLabels[effectiveClass(row)],
  ...(row.routes||[]),...domains(row),...domains(row).map(value=>domainLabels[value]||value),...matchedTerms(row)
].join(' '))}

function scoreRow(row,questionTokens,questionPhrase){
  const title=normalize(row.title);const body=searchable(row);let score=0;const signals=[];
  if(questionPhrase&&questionPhrase.length>5&&title.includes(questionPhrase)){score+=30;signals.push('frase no título')}
  let titleHits=0,contextHits=0;
  for(const token of questionTokens){if(title.includes(token)){score+=6;titleHits+=1}else if(body.includes(token)){score+=2;contextHits+=1}}
  if(titleHits)signals.push(`${titleHits} termo${titleHits>1?'s':''} no título`);
  if(contextHits)signals.push(`${contextHits} termo${contextHits>1?'s':''} no perfil`);
  return {score,signals};
}

function filtersMatch(row){
  const route=$('#askRoute').value,domain=$('#askDomain').value,documentClass=$('#askClass').value;
  if(route&&!(row.routes||[]).includes(route))return false;
  if(domain&&!domains(row).includes(domain))return false;
  if(documentClass&&effectiveClass(row)!==documentClass)return false;
  return true;
}

function corpusHref(row){const q=row.doi||row.pmid||row.title||row.document_id;return `/articles.html?q=${encodeURIComponent(q)}`}

function runQuery(){
  const question=$('#askQuestion').value.trim();
  if(!question){results=[];renderResults('Digite uma pergunta para iniciar.');return}
  const qTokens=tokens(question),phrase=normalize(question);
  results=articles.filter(filtersMatch).map(row=>({row,...scoreRow(row,qTokens,phrase)})).filter(item=>item.score>0).sort((a,b)=>b.score-a.score||String(b.row.year||'').localeCompare(String(a.row.year||''))).slice(0,50);
  renderResults();
}

function renderResults(emptyMessage='Nenhum documento corresponde à consulta e aos filtros atuais.'){
  $('#askResultMeta').textContent=results.length?`${fmt(results.length)} melhores correspondências no contexto seguro`:'0 correspondências';
  $('#selectedCount').textContent=`${selected.size} selecionado${selected.size===1?'':'s'}`;
  if(!results.length){$('#askResults').innerHTML=`<p class="small-state">${esc(emptyMessage)}</p>`;return}
  $('#askResults').innerHTML=results.map(({row,signals})=>{
    const checked=selected.has(row.document_id)?' checked':'';
    return `<article class="ask-result">
      <label class="ask-select"><input type="checkbox" data-doc="${esc(row.document_id)}"${checked}><span></span></label>
      <div class="ask-result-body">
        <div class="ask-result-top"><strong>${esc(row.title||'Sem título')}</strong><a href="${corpusHref(row)}">Abrir dossier →</a></div>
        <small>${esc([row.year,row.source_provider,classLabels[effectiveClass(row)]||effectiveClass(row)].filter(Boolean).join(' · '))}</small>
        <div class="detail-chips">${(row.routes||[]).map(route=>`<span class="mini-pill">${esc(route)}</span>`).join('')}${domains(row).slice(0,4).map(domain=>`<span class="mini-pill">${esc(domainLabels[domain]||domain)}</span>`).join('')}</div>
        <div class="ask-signals">${signals.map(signal=>`<span>${esc(signal)}</span>`).join('')||'<span>correspondência de contexto</span>'}</div>
      </div>
    </article>`
  }).join('')}

function packetRows(){
  const chosen=selected.size?articles.filter(row=>selected.has(row.document_id)):results.slice(0,8).map(item=>item.row);
  return chosen.slice(0,12)
}

function buildPacket(){
  const question=$('#askQuestion').value.trim();const chosen=packetRows();
  if(!question){$('#contextPacket').value='Digite uma pergunta antes de gerar o contexto.';return}
  const route=$('#askRoute').value||'all routes',domain=$('#askDomain').value||'all domains',documentClass=$('#askClass').value||'all document classes';
  const docs=chosen.map((row,index)=>{
    const ids=[row.doi?`DOI ${row.doi}`:'',row.pmid?`PMID ${row.pmid}`:''].filter(Boolean).join(' · ');
    return `${index+1}. ${row.title||'Untitled'} (${row.year||'year unavailable'})\n   document_id: ${row.document_id}\n   ${ids||'DOI/PMID unavailable'}\n   class: ${effectiveClass(row)}\n   routes: ${(row.routes||[]).join(', ')||'unrouted'}\n   domains: ${domains(row).join(', ')||'none mapped'}\n   dossier: ${location.origin}${corpusHref(row)}`
  }).join('\n\n');
  $('#contextPacket').value=`NUTEV GROUNDED ANALYSIS PACKET\n\nQUESTION\n${question}\n\nSCOPE\nroute: ${route}\ndomain: ${domain}\ndocument class: ${documentClass}\n\nSUPPORTING DOCUMENTS (${chosen.length})\n${docs||'No supporting documents selected.'}\n\nCANONICAL CONTEXT\n${location.origin}/agent-context/article1/SEARCH_STATE.json\n${location.origin}/agent-context/article1/CONTEXT_MANIFEST.json\n${location.origin}/agent-context/article1/ARTICLE_SUMMARIES.jsonl\n\nINSTRUCTIONS FOR THE ANALYZING AGENT\n- Ground the analysis in the supporting documents and canonical NutEV context above.\n- Distinguish document metadata/machine profiles from human-accepted scientific evidence.\n- Do not treat route membership, retrieval status, class profile or lexical match as eligibility, inclusion, quality, RoB, certainty or recommendation.\n- If a claim requires deeper article content, open the Scientific Dossier / Workbench detail for that document and state when the available context is insufficient.\n- Do not infer PRISMA events or formal-search completion from this packet.\n- Return supporting document IDs alongside substantive claims.\n`;
}

async function load(){
  try{
    const response=await fetch('/agent-context/article1/ARTICLE_SUMMARIES.jsonl',{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
    articles=(await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse);
    const domainValues=[...new Set(articles.flatMap(domains))].sort((a,b)=>(domainLabels[a]||a).localeCompare(domainLabels[b]||b));
    $('#askDomain').insertAdjacentHTML('beforeend',domainValues.map(value=>`<option value="${esc(value)}">${esc(domainLabels[value]||value)}</option>`).join(''));
    const classes=[...new Set(articles.map(effectiveClass))].sort((a,b)=>(classLabels[a]||a).localeCompare(classLabels[b]||b));
    $('#askClass').insertAdjacentHTML('beforeend',classes.map(value=>`<option value="${esc(value)}">${esc(classLabels[value]||value)}</option>`).join(''));
    $('#askState').className='hidden';$('#askContent').classList.remove('hidden');$('#askHealth').textContent=`${fmt(articles.length)} resumos seguros`;$('#askHealth').className='status-pill ok';
  }catch(error){$('#askState').className='error';$('#askState').innerHTML=`<strong>Ask NutEV indisponível.</strong><div>${esc(error.message)}</div>`;$('#askHealth').textContent='contexto indisponível';$('#askHealth').className='status-pill bad'}
}

$('#runAsk').addEventListener('click',runQuery);
$('#askQuestion').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter')runQuery()});
$('.ask-suggestions').addEventListener('click',event=>{const button=event.target.closest('[data-question]');if(!button)return;$('#askQuestion').value=button.dataset.question;runQuery()});
for(const id of ['askRoute','askDomain','askClass'])$(id.startsWith('#')?id:`#${id}`).addEventListener('change',()=>{if($('#askQuestion').value.trim())runQuery()});
$('#clearAsk').addEventListener('click',()=>{$('#askQuestion').value='';$('#askRoute').value='';$('#askDomain').value='';$('#askClass').value='';selected.clear();results=[];renderResults('Nenhuma consulta executada.');$('#contextPacket').value=''});
$('#askResults').addEventListener('change',event=>{const input=event.target.closest('[data-doc]');if(!input)return;if(input.checked)selected.add(input.dataset.doc);else selected.delete(input.dataset.doc);$('#selectedCount').textContent=`${selected.size} selecionado${selected.size===1?'':'s'}`});
$('#buildPacket').addEventListener('click',buildPacket);
$('#copyPacket').addEventListener('click',async()=>{if(!$('#contextPacket').value)buildPacket();if(!$('#contextPacket').value)return;await navigator.clipboard.writeText($('#contextPacket').value);const button=$('#copyPacket');const old=button.textContent;button.textContent='Copiado';setTimeout(()=>button.textContent=old,1200)});
load();
