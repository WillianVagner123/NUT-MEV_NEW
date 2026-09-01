import {buildScientificSnapshot} from './scientific-snapshot.js';

const $=selector=>document.querySelector(selector);
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const pct=(value,total)=>total?`${(100*Number(value||0)/Number(total)).toLocaleString('pt-BR',{maximumFractionDigits:1})}%`:'—';
const providerLabels={pubmed:'PubMed',europepmc:'Europe PMC',europe_pmc:'Europe PMC',openalex:'OpenAlex',crossref:'Crossref',doaj:'DOAJ',semantic_scholar:'Semantic Scholar',lilacs_bvs:'LILACS / BVS',lilacs_bvs_native:'LILACS / BVS',scielo:'SciELO',scielo_native:'SciELO',scopus:'Scopus',wos:'Web of Science'};
let lastData=null;

async function fetchJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json()}
async function fetchJsonl(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);return (await response.text()).split(/\r?\n/).filter(Boolean).map(JSON.parse)}
function effectiveClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function domains(row){return row.review_profile?.operational_domains||[]}
function ageHours(value){const date=new Date(value);return Number.isFinite(date.getTime())?Math.max(0,(Date.now()-date.getTime())/36e5):null}
function severityIcon(level){return level==='error'?'!':level==='attention'?'△':'✓'}
function checkRow(label,value,level='info',note=''){return `<div class="quality-check ${level}"><i>${severityIcon(level)}</i><div><strong>${esc(label)}</strong>${note?`<small>${esc(note)}</small>`:''}</div><span>${esc(value)}</span></div>`}
function metricRow(label,value,total,note=''){return `<div class="quality-metric"><div><strong>${esc(label)}</strong><small>${esc(note)}</small></div><span>${fmt(value)}${total!==undefined?` <em>${esc(pct(value,total))}</em>`:''}</span></div>`}
function bars(counts,labels={}){const rows=Object.entries(counts||{}).sort((a,b)=>b[1]-a[1]);const max=Math.max(1,...rows.map(([,v])=>Number(v||0)));return rows.length?`<div class="quality-bars">${rows.map(([key,value])=>`<div><span>${esc(labels[key]||key)}</span><i><b style="width:${Math.max(2,100*value/max)}%"></b></i><strong>${fmt(value)}</strong></div>`).join('')}</div>`:'<p class="small-state">Sem contagens disponíveis.</p>'}

async function load(){
  $('#qualityState').className='loading dashboard-state';$('#qualityState').textContent='Executando verificações somente-leitura…';$('#qualityContent').classList.add('hidden');
  const probes=await Promise.allSettled([
    fetchJson('/api/health'),fetchJson('/api/articles/status'),fetchJson('/api/radar'),fetchJson('/agent-context/article1/SEARCH_STATE.json'),fetchJson('/agent-context/article1/CONTEXT_MANIFEST.json'),fetchJsonl('/agent-context/article1/ARTICLE_SUMMARIES.jsonl'),fetchJson('/build-info.json'),buildScientificSnapshot()
  ]);
  const names=['health','workbench','radar','searchState','manifest','articles','buildInfo','snapshot'];const data={};const errors={};
  probes.forEach((item,index)=>{if(item.status==='fulfilled')data[names[index]]=item.value;else errors[names[index]]=item.reason?.message||String(item.reason)});
  lastData={data,errors};render();
}

function render(){
  const {data,errors}=lastData;const articles=data.articles||[];const total=articles.length;const search=data.searchState||{};const deep=search.runtime?.deepening||{};const formal=search.formal_search||{};const fullCounts=data.snapshot?.corpus?.full_text_status_counts||{};
  const retrieved=Number(fullCounts.retrieved||0),partial=Number(fullCounts.partial||0),notRetrieved=Number(fullCounts.not_retrieved||0);const covered=retrieved+partial;
  const unclassified=articles.filter(row=>effectiveClass(row)==='unclassified').length;const missingDoi=articles.filter(row=>!row.doi).length;const missingPmid=articles.filter(row=>!row.pmid).length;const missingYear=articles.filter(row=>!row.year).length;const noDomains=articles.filter(row=>domains(row).length===0).length;const unrouted=articles.filter(row=>(row.routes||[]).length===0).length;
  const contextAge=ageHours(data.manifest?.created_at||search.created_at);const coreErrors=Object.keys(errors).length;

  $('#qualityHealth').textContent=coreErrors?`${coreErrors} superfície${coreErrors===1?'':'s'} com erro`:'checks operacionais OK';$('#qualityHealth').className=`status-pill ${coreErrors?'bad':'ok'}`;
  $('#qualityState').className='hidden';$('#qualityContent').classList.remove('hidden');
  const kpis=[['Contexto seguro',total,'resumos Article 1'],['Full-text coverage',pct(covered,total),`${fmt(covered)} retrieved + partial`],['Not retrieved',notRetrieved,'estado técnico'],['Unclassified',unclassified,'forma documental não confirmada'],['Context age',contextAge===null?'—':`${contextAge.toLocaleString('pt-BR',{maximumFractionDigits:1})} h`,'desde a geração do contexto']];
  $('#qualityKpis').innerHTML=kpis.map(([label,value,note])=>`<article class="card metric-card"><span class="metric-label">${esc(label)}</span><strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span></article>`).join('');

  const serviceRows=[
    ['Web engine',data.health?.status==='ok'?'OK':'ERROR',data.health?.status==='ok'?'info':'error',errors.health||data.health?.status||'health endpoint'],
    ['Article Workbench',data.workbench?.status==='ready'?'READY':'NOT READY',data.workbench?.status==='ready'?'info':'error',errors.workbench||data.workbench?.database||'verified workbench'],
    ['Agent context',data.manifest?'AVAILABLE':'ERROR',data.manifest?'info':'error',errors.manifest||data.manifest?.status||'context manifest'],
    ['Article summaries',articles.length?'AVAILABLE':'EMPTY',articles.length?'info':'error',errors.articles||`${fmt(articles.length)} parsed summaries`],
    ['Radar',data.radar?'AVAILABLE':'ERROR',data.radar?'info':'attention',errors.radar||'provider operations'],
    ['Scientific snapshot',data.snapshot?.snapshot_id?'HASHED':'ERROR',data.snapshot?.snapshot_id?'info':'error',errors.snapshot||data.snapshot?.snapshot_id?.slice(0,16)||'snapshot builder']
  ];$('#serviceChecks').innerHTML=serviceRows.map(row=>checkRow(...row)).join('');

  const buildCommit=data.buildInfo?.build_commit||'unknown';const buildLevel=buildCommit==='unknown'||buildCommit==='development'?'attention':'info';
  $('#contextChecks').innerHTML=[
    checkRow('Build commit',buildCommit,buildLevel,buildLevel==='info'?'verified deploy identity':'development/unknown build identity'),
    checkRow('Search ID',search.search_id||'missing',search.search_id?'info':'error','canonical Article 1 search identifier'),
    checkRow('Context age',contextAge===null?'unknown':`${contextAge.toLocaleString('pt-BR',{maximumFractionDigits:1})} h`,contextAge!==null&&contextAge>48?'attention':'info','age is operational freshness, not scientific validity'),
    checkRow('Snapshot source hashes',data.snapshot?.source_sha256?`${Object.keys(data.snapshot.source_sha256).length} hashed`:'missing',data.snapshot?.source_sha256?'info':'error','SHA-256 computed from safe source files')
  ].join('');

  $('#retrievalHealth').innerHTML=bars(fullCounts,{retrieved:'Retrieved',partial:'Partial',not_retrieved:'Not retrieved',not_attempted:'Not attempted',unavailable:'Unavailable',unknown:'Unknown'});
  $('#extractionHealth').innerHTML=bars(deep.extraction_method_counts||{},{xml_text:'XML',pdf_text:'PDF',html_text:'HTML',direct_text:'Direct text',abstract_only:'Abstract only',unavailable:'Unavailable'});

  $('#metadataChecks').innerHTML=[metricRow('Missing DOI',missingDoi,total,'DOI absence is not automatically an error'),metricRow('Missing PMID',missingPmid,total,'not every source has a PMID'),metricRow('Missing year',missingYear,total,'bibliographic completeness'),metricRow('Unclassified document type',unclassified,total,'fail-safe classification state')].join('');
  $('#mappingChecks').innerHTML=[metricRow('Unrouted',unrouted,total,'not excluded; no current B-NORM/C-STRUCT routing'),metricRow('No operational domain mapped',noDomains,total,'not evidence absence'),metricRow('Routed',total-unrouted,total,'navigation coverage')].join('');

  renderProviders(data.radar);
  const pressPass=String(formal.press_status||'').trim().toUpperCase()==='PASS';
  const masterNegation=String(formal.press_status||'').toUpperCase().includes('NOT_')&&String(formal.press_status||'').toUpperCase().includes('PASS');
  $('#guardrailChecks').innerHTML=[
    checkRow('PRESS gate uses exact equality',pressPass?'PASS exact':'NOT PASS','info',`raw status: ${formal.press_status||'not recorded'}${masterNegation?' · negated PASS token correctly remains false':''}`),
    checkRow('GF-10 remains canonical',formal.gf10_authorized?'AUTHORIZED':'LOCKED','info','observatory only reflects the master'),
    checkRow('Formal search state',formal.formal_provider_search_executed?'EXECUTED':'NOT EXECUTED','info','never inferred from discovery/deepening'),
    checkRow('PRISMA event state',formal.prisma_search_event_emitted?'EMITTED':'NOT EMITTED','info','operational funnels do not create PRISMA'),
    checkRow('Snapshot boundary',data.snapshot?.scientific_boundaries?.snapshot_is_not_prisma?'ENFORCED':'MISSING',data.snapshot?.scientific_boundaries?.snapshot_is_not_prisma?'info':'error','snapshot records state; it does not approve it')
  ].join('');
}

function renderProviders(radar){
  const providers=radar?.providers||[];
  if(!providers.length){$('#qualityProviders').innerHTML='<p class="small-state">Provider status indisponível neste momento.</p>';return}
  $('#qualityProviders').innerHTML=providers.map(item=>{const state=String(item.state||'unknown');const counts=Object.entries(item.status_counts||{}).map(([key,value])=>`${key} ${value}`).join(' · ')||'sem contagens';const lower=state.toLowerCase();const level=lower.includes('error')||lower.includes('failed')?'error':lower.includes('partial')||lower.includes('unavailable')||lower.includes('gap')?'attention':'info';return `<article class="quality-provider ${level}"><div><strong>${esc(providerLabels[item.provider]||item.provider)}</strong><span>${esc(state)}</span></div><p>${esc(counts)}</p></article>`}).join('')
}

$('#refreshQuality').addEventListener('click',load);
load();
