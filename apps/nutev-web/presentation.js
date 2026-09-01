import {buildScientificSnapshot,downloadSnapshot} from './scientific-snapshot.js';

const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];
const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
const fmt=value=>new Intl.NumberFormat('pt-BR').format(Number(value||0));
const pct=(value,total)=>`${(100*Number(value||0)/Math.max(1,Number(total||0))).toLocaleString('pt-BR',{maximumFractionDigits:1})}%`;
const classLabels={food_based_dietary_guideline:'FBDG',clinical_practice_guideline:'Diretriz clínica',consensus_statement:'Consenso',position_statement:'Position statement',framework_model:'Framework/modelo',competency_curriculum:'Competências/currículo',implementation_evaluation:'Implementação',primary_randomized:'Randomizado',primary_observational:'Observacional',primary_qualitative:'Qualitativo',evidence_synthesis:'Síntese de evidência',review:'Revisão',guidance:'Guidance',unclassified:'Não classificado'};
const domainLabels={nutrition_assessment:'Avaliação nutricional',dietary_counseling:'Aconselhamento alimentar',nutrition_prescription:'Prescrição nutricional',monitoring_follow_up:'Monitoramento / seguimento',food_skills_competencies:'Competências alimentares',food_literacy:'Food / nutrition literacy',social_context:'Contexto social',food_based_guidance:'Orientação baseada em alimentos',nutrition_care_process:'Nutrition Care Process',lifestyle_medicine:'Lifestyle Medicine',implementation_practice:'Implementação'};
let slide=0;
let snapshot=null;

function status(label,value,state){return `<article class="presentation-status ${state}"><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`}
function barList(counts,labels={},limit=8){
  const rows=Object.entries(counts||{}).sort((a,b)=>b[1]-a[1]).slice(0,limit);const max=Math.max(1,...rows.map(([,value])=>value));
  return `<div class="presentation-bars">${rows.map(([key,value])=>`<div class="presentation-bar"><div><span>${esc(labels[key]||key)}</span><strong>${fmt(value)}</strong></div><i><b style="width:${100*value/max}%"></b></i></div>`).join('')}</div>`
}
function renderFooter(){const short=snapshot.snapshot_id.slice(0,12);const commit=String(snapshot.build_commit||'unknown').slice(0,12);$$('.snapshot-footer').forEach(node=>node.innerHTML=`<span>Snapshot ${esc(short)}</span><span>Build ${esc(commit)}</span><span>${esc(new Date(snapshot.generated_at).toLocaleString('pt-BR'))}</span>`) }

function renderQuestion(){
  $('#presentationQuestion').textContent=snapshot.question||'Article 1';const formal=snapshot.formal_search||{};
  $('#questionStatuses').innerHTML=[
    status('Snapshot','VERIFIED','done'),status('Query draft',snapshot.query.status||'—','warn'),status('PRESS',formal.press_status||'PENDING','warn'),status('GF-10',formal.gf10_authorized?'AUTHORIZED':'LOCKED',formal.gf10_authorized?'done':'pending')
  ].join('')
}
function renderCorpus(){
  const corpus=snapshot.corpus||{},runtime=snapshot.runtime||{},workbench=runtime.workbench?.counts||{};
  $('#corpusKpis').innerHTML=[
    ['Bank articles',workbench.articles||workbench.article_cards||'—'],['Tier A safe context',corpus.safe_article_summaries],['Routed',corpus.routes?.union],['Unrouted',corpus.routes?.unrouted]
  ].map(([label,value])=>`<article><span>${esc(label)}</span><strong>${typeof value==='number'?fmt(value):esc(value)}</strong></article>`).join('');
  $('#presentationFulltext').innerHTML=barList(corpus.full_text_status_counts,{retrieved:'Retrieved',partial:'Partial',not_retrieved:'Not retrieved',not_attempted:'Not attempted',unavailable:'Unavailable',unknown:'Unknown'});
  $('#presentationClasses').innerHTML=barList(corpus.document_class_counts,classLabels,7)
}
function renderDomains(){
  const counts=snapshot.corpus?.operational_domain_counts||{};const rows=Object.entries(counts).sort((a,b)=>b[1]-a[1]);const total=snapshot.corpus?.safe_article_summaries||1;const max=Math.max(1,...rows.map(([,value])=>value));
  $('#presentationDomains').innerHTML=rows.map(([key,value])=>`<article><div><strong>${esc(domainLabels[key]||key)}</strong><span>${fmt(value)} · ${pct(value,total)}</span></div><i><b style="width:${100*value/max}%"></b></i></article>`).join('')
}
function renderRoutes(){
  const r=snapshot.corpus?.routes||{};
  $('#presentationRoutes').innerHTML=`
    <div class="route-circle b"><span>B-NORM</span><strong>${fmt(r['B-NORM'])}</strong><small>documentos roteados</small></div>
    <div class="route-overlap"><span>OVERLAP</span><strong>${fmt(r.overlap)}</strong><small>presentes nas duas rotas</small></div>
    <div class="route-circle c"><span>C-STRUCT</span><strong>${fmt(r['C-STRUCT'])}</strong><small>documentos roteados</small></div>
    <div class="route-unrouted"><span>UNROUTED</span><strong>${fmt(r.unrouted)}</strong><small>não excluídos; apenas sem roteamento atual</small></div>`
}
function renderReadiness(){
  const formal=snapshot.formal_search||{};const ready=[
    ['PRESS',formal.press_status||'NOT RECORDED',String(formal.press_status||'').toUpperCase()==='PASS'],
    ['GF-10',formal.gf10_authorized?'AUTHORIZED':'LOCKED',Boolean(formal.gf10_authorized)],
    ['Query freeze',formal.query_freeze_complete?'COMPLETE':'NOT COMPLETE',Boolean(formal.query_freeze_complete)],
    ['Formal provider search',formal.formal_provider_search_executed?'EXECUTED':'NOT EXECUTED',Boolean(formal.formal_provider_search_executed)],
    ['PRISMA search event',formal.prisma_search_event_emitted?'EMITTED':'NOT EMITTED',Boolean(formal.prisma_search_event_emitted)]
  ];
  $('#presentationReadiness').innerHTML=ready.map(([label,value,done])=>`<article class="${done?'done':'pending'}"><span>${esc(label)}</span><strong>${esc(value)}</strong><i>${done?'✓':'○'}</i></article>`).join('');
  const next=!ready[0][2]?'Complete PRESS review and delta tests.':!ready[1][2]?'Authorize GF-10 through the canonical scientific gate.':!ready[2][2]?'Freeze provider-specific query versions.':!ready[3][2]?'Execute the formal provider search.':'Proceed according to the canonical review protocol.';
  $('#presentationNextAction').innerHTML=`<span>NEXT REQUIRED ACTION</span><strong>${esc(next)}</strong>`
}
function render(){renderQuestion();renderCorpus();renderDomains();renderRoutes();renderReadiness();renderFooter();showSlide(0)}
function showSlide(index){slide=Math.max(0,Math.min(4,index));$$('.presentation-slide').forEach((node,i)=>node.classList.toggle('active',i===slide));$('#slidePosition').textContent=`${slide+1} / 5`;$('#slideProgress').style.width=`${20*(slide+1)}%`;$('#prevSlide').disabled=slide===0;$('#nextSlide').disabled=slide===4}

async function load(){
  try{snapshot=await buildScientificSnapshot();render();$('#presentationState').classList.add('hidden')}catch(error){$('#presentationState').className='presentation-loading error';$('#presentationState').textContent=`Presentation unavailable: ${error.message}`}
}
$('#prevSlide').addEventListener('click',()=>showSlide(slide-1));$('#nextSlide').addEventListener('click',()=>showSlide(slide+1));
document.addEventListener('keydown',event=>{if(event.key==='ArrowRight'||event.key==='PageDown')showSlide(slide+1);if(event.key==='ArrowLeft'||event.key==='PageUp')showSlide(slide-1)});
$('#fullscreen').addEventListener('click',async()=>{if(!document.fullscreenElement)await document.documentElement.requestFullscreen();else await document.exitFullscreen()});
$('#downloadSnapshot').addEventListener('click',()=>snapshot&&downloadSnapshot(snapshot));
$('#printPresentation').addEventListener('click',()=>window.print());
load();
