const STATUS_LABELS={
  COMPLETE:'Concluída',
  COMPLETE_WITH_PROVIDER_GAPS:'Concluída, com lacunas em algumas fontes',
  COMPLETE_WITH_AUDIT_GAPS:'Concluída, com lacunas de auditoria',
  PREFLIGHT:'Pré-verificação',
  PILOT:'Piloto',
  DEVELOPMENT:'Desenvolvimento',
  SUPPLEMENTARY:'Suplementar',
  FORMAL:'Formal'
}

const NAV_GROUPS=[
  {label:'Visão geral',items:[
    {key:'dashboard',href:'/',icon:'◫',label:'Dashboard'}
  ]},
  {label:'Evidências',items:[
    {key:'search',href:'/search.html',icon:'⌕',label:'Buscar evidências'},
    {key:'articles',href:'/articles.html',icon:'▤',label:'Corpus'},
    {key:'radar',href:'/radar.html',icon:'⌁',label:'Radar de evidências'}
  ]},
  {label:'Estratégia',items:[
    {key:'qa',href:'/review-qa.html',icon:'◎',label:'QA'},
    {key:'press',href:'/press-review.html',icon:'▣',label:'PRESS'},
    {key:'regional',href:'/regional-routes.html',icon:'↗',label:'Rotas regionais'}
  ]},
  {label:'Validação',items:[
    {key:'validation',href:'/validation/',icon:'✓',label:'Validação científica'}
  ]},
  {label:'Sistema',items:[
    {key:'history',href:'/search.html?view=history',icon:'◷',label:'Minhas buscas'}
  ]}
]

const GLOSSARY=[
  ['Busca progressiva','Execução que consulta provedores em etapas e preserva o estado de cada fonte. Uma fonte indisponível não é tratada como zero resultados.'],
  ['Provider','Fonte externa consultada pelo NutEV, como PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, SciELO ou LILACS/BVS.'],
  ['Deduplicação','Processo que consolida registros equivalentes vindos de fontes diferentes sem apagar a proveniência de origem.'],
  ['Ranking','Ordem operacional de leitura ou processamento. Ranking não significa recomendação, inclusão, qualidade metodológica ou certeza da evidência.'],
  ['ResultBundle','Estrutura processada que organiza resultados extraídos pelo pipeline. Seu texto não deve ser tratado como citação literal da publicação.'],
  ['Fonte verbatim','Trecho reproduzido literalmente de uma fonte rastreável, acompanhado de identificadores e hash quando disponível.'],
  ['EvidenceClaim','Afirmação de evidência com proveniência própria e revisão governada. Não é criada automaticamente só porque um ResultBundle existe.'],
  ['EvidenceSet','Conjunto governado de evidências associado a uma pergunta ou decisão científica específica.'],
  ['QA','Controle metodológico prospectivo da estratégia de busca. Não substitui triagem humana e não autoriza PRISMA por si só.'],
  ['PRESS','Revisão independente e estruturada de uma estratégia eletrônica de busca. Alterações materiais devem retornar ao ciclo de versionamento e PILOT.'],
  ['Pré-freeze','Estado anterior ao congelamento formal de uma estratégia. Ajustes ainda podem ocorrer desde que sejam rastreados e revalidados.'],
  ['Freeze','Congelamento formal de uma estratégia/versionamento após os gates definidos. O NutEV não deve inferir freeze apenas por haver um run executado.'],
  ['PRISMA','Relato estruturado do processo de revisão. Snapshots, pilots, QA, PRESS ou buscas exploratórias não equivalem automaticamente a uma etapa PRISMA.'],
  ['Proveniência','Rastro que liga um dado, trecho, decisão ou resultado à sua origem, versão e contexto de processamento.']
]

const STRATEGY_FLOW_STORAGE_KEY='nutev_strategy_flow:article1-scientific-closure-v1'
const STRATEGY_FLOW_KEYS=['qa','press','regional']

function escapeHtml(value){
  return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;')
}

function ensureProductStyles(){
  if(document.querySelector('link[data-nutev-product-ui]'))return
  const link=document.createElement('link')
  link.rel='stylesheet'
  link.href='/product-ui.css'
  link.dataset.nutevProductUi='true'
  document.head.appendChild(link)
}

function activeNavKey(){
  const path=location.pathname.replace(/\/+$/,'')||'/'
  const params=new URLSearchParams(location.search)
  if(path==='/search.html'&&params.get('view')==='history')return 'history'
  if(path==='/')return 'dashboard'
  if(path==='/search.html'||path==='/ask.html')return 'search'
  if(['/articles.html','/evidence.html','/evidence-map.html'].includes(path))return 'articles'
  if(['/radar.html','/intelligence.html'].includes(path))return 'radar'
  if(['/review-qa.html','/review-routes.html','/quality.html','/strategy.html'].includes(path))return 'qa'
  if(path==='/press-review.html')return 'press'
  if(path==='/regional-routes.html')return 'regional'
  if(path.startsWith('/validation'))return 'validation'
  return ''
}

function canonicalNavHtml(active){
  return NAV_GROUPS.map(group=>{
    const items=group.items.map(item=>`<a class="nav-item${active===item.key?' active':''}" href="${item.href}"${active===item.key?' aria-current="page"':''}><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${escapeHtml(item.label)}</span></a>`).join('')
    return `<div class="nav-group-label">${escapeHtml(group.label)}</div>${items}`
  }).join('')
}

function normalizeNavigation(){
  const active=activeNavKey()
  const signature=`v2:${active}`
  document.querySelectorAll('.sidebar nav,.product-nav').forEach(nav=>{
    if(nav.dataset.nutevCanonicalNav===signature)return
    nav.setAttribute('aria-label','Navegação principal')
    nav.innerHTML=canonicalNavHtml(active)
    nav.dataset.nutevCanonicalNav=signature
  })
}

function shouldTranslateNode(node){
  const parent=node.parentElement
  if(!parent)return false
  return !parent.closest('code,pre,script,style,textarea,[data-raw-enum]')
}

function translateInternalEnums(root=document){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT)
  const nodes=[]
  while(walker.nextNode())nodes.push(walker.currentNode)
  for(const node of nodes){
    if(!shouldTranslateNode(node))continue
    let text=node.nodeValue||''
    for(const [raw,label] of Object.entries(STATUS_LABELS))text=text.replaceAll(raw,label)
    if(text!==node.nodeValue)node.nodeValue=text
  }
}

function explainResultCap(){
  const summary=document.querySelector('#summary')
  const values=[...document.querySelectorAll('#summary .summary-grid .kpi strong')].map(node=>Number(String(node.textContent||'').replace(/\D/g,'')))
  if(!summary||values.length<3||!Number.isFinite(values[0])||!Number.isFinite(values[2]))return
  const unique=values[0],returned=values[2]
  let note=document.querySelector('#resultCapNote')
  if(unique<=returned){note?.remove();return}
  if(!note){note=document.createElement('div');note.id='resultCapNote';note.className='review-result-note';summary.appendChild(note)}
  note.textContent=`Exibindo ${returned.toLocaleString('pt-BR')} de ${unique.toLocaleString('pt-BR')} referências únicas. Este modo possui limite de apresentação; use a busca sem teto para recuperar o conjunto completo.`
}

function markStaticKpis(){
  document.querySelectorAll('#summary .summary-grid .kpi').forEach(kpi=>{
    kpi.classList.add('static-kpi')
    kpi.setAttribute('role','group')
    kpi.setAttribute('title','Indicador informativo; não abre detalhamento.')
  })
}

function ensureSkipLink(){
  if(document.querySelector('.skip-link'))return
  const target=document.querySelector('main.main,main,.workspace-body')
  if(!target)return
  if(!target.id)target.id='mainContent'
  const link=document.createElement('a')
  link.className='skip-link'
  link.href=`#${target.id}`
  link.textContent='Pular para o conteúdo principal'
  document.body.prepend(link)
}

function glossaryRows(filter=''){
  const normalized=filter.trim().toLocaleLowerCase('pt-BR')
  const rows=GLOSSARY.filter(([term,definition])=>!normalized||`${term} ${definition}`.toLocaleLowerCase('pt-BR').includes(normalized))
  if(!rows.length)return '<p class="glossary-empty">Nenhum termo encontrado.</p>'
  return rows.map(([term,definition])=>`<div class="glossary-row"><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join('')
}

function ensureGlossary(){
  if(document.querySelector('#nutevGlossaryButton'))return
  const button=document.createElement('button')
  button.id='nutevGlossaryButton'
  button.className='glossary-trigger'
  button.type='button'
  button.textContent='Glossário científico'
  button.setAttribute('aria-haspopup','dialog')

  const dialog=document.createElement('dialog')
  dialog.id='nutevGlossaryDialog'
  dialog.className='glossary-dialog'
  dialog.innerHTML=`<div class="glossary-head"><div><span class="glossary-eyebrow">Ajuda de termos</span><h2>Glossário científico</h2><p>Definições de interface para reduzir ambiguidade sem alterar os contratos científicos internos.</p></div><button class="glossary-close" type="button" aria-label="Fechar glossário">×</button></div><label class="glossary-search">Filtrar termos<input id="nutevGlossarySearch" type="search" autocomplete="off" placeholder="Ex.: PRESS, ResultBundle, PRISMA"></label><dl id="nutevGlossaryList" class="glossary-list">${glossaryRows()}</dl>`

  document.body.append(button,dialog)
  const close=()=>{if(typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open')}
  button.addEventListener('click',()=>{if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','')})
  dialog.querySelector('.glossary-close')?.addEventListener('click',close)
  dialog.addEventListener('click',event=>{if(event.target===dialog)close()})
  dialog.querySelector('#nutevGlossarySearch')?.addEventListener('input',event=>{
    const list=dialog.querySelector('#nutevGlossaryList')
    if(list)list.innerHTML=glossaryRows(event.target.value)
  })
}

function readStrategyFlowState(){
  try{return JSON.parse(localStorage.getItem(STRATEGY_FLOW_STORAGE_KEY)||'{}')||{}}
  catch{return{}}
}

function updateStrategyFlowState(step,patch={}){
  if(!STRATEGY_FLOW_KEYS.includes(step))return null
  const current=readStrategyFlowState()
  const next={...current,[step]:{...(current[step]||{}),...patch,updated_at:new Date().toISOString()}}
  try{localStorage.setItem(STRATEGY_FLOW_STORAGE_KEY,JSON.stringify(next))}catch{}
  window.dispatchEvent(new CustomEvent('nutev:strategy-flow-update',{detail:{step,state:next}}))
  return next[step]
}

window.NutEVStrategyFlow={
  key:STRATEGY_FLOW_STORAGE_KEY,
  read:readStrategyFlowState,
  update:updateStrategyFlowState
}

function flowStatus(key,value={}){
  const status=String(value.status||'')
  if(key==='qa'){
    if(status==='TECHNICAL_PASS'){
      const done=Number(value.human_classifications_done||0),total=Number(value.human_classifications_total||0)
      return{tone:'done',label:total&&done>=total?'QA técnico concluído · amostra classificada':'QA técnico concluído · revisão humana pendente'}
    }
    if(status==='REVIEW_REQUIRED')return{tone:'warn',label:'revisão técnica necessária'}
    if(status==='READY')return{tone:'ready',label:'run elegível · QA ainda não executado'}
    if(status==='PENDING_RUN')return{tone:'pending',label:'aguardando run elegível'}
    return{tone:'pending',label:'ainda não executado'}
  }
  if(key==='press'){
    if(status==='PRESS_REVIEW_COMPLETE_PENDING_CANONICAL_REGISTRATION')return{tone:'done',label:'parecer concluído · registro canônico pendente'}
    if(status==='REVISION_REQUIRED')return{tone:'warn',label:'alteração material · revisar estratégia'}
    if(status==='PRESS_FAIL')return{tone:'warn',label:'PRESS não aprovado'}
    if(status==='PRESS_IN_REVIEW')return{tone:'ready',label:'parecer humano em revisão'}
    if(status==='READY_FOR_HUMAN_REVIEW')return{tone:'ready',label:'pacote pronto para revisão humana'}
    return{tone:'pending',label:'revisão humana ainda não registrada'}
  }
  if(key==='regional'){
    if(status==='PASS')return{tone:'done',label:'rotas documentadas · GF-01 candidato'}
    if(status==='REVIEW_REQUIRED')return{tone:'warn',label:'evidência regional incompleta'}
    if(status==='READY_FOR_EVIDENCE')return{tone:'ready',label:'aguardando evidência das rotas oficiais'}
    return{tone:'pending',label:'rotas ainda não avaliadas'}
  }
  return{tone:'pending',label:'pendente'}
}

function decorateStrategyFlow(){
  const flow=document.querySelector('.strategy-flow')
  if(!flow)return
  const state=readStrategyFlowState()
  const nodes=[...flow.children].slice(0,3)
  nodes.forEach((node,index)=>{
    const key=STRATEGY_FLOW_KEYS[index]
    const result=flowStatus(key,state[key]||{})
    let marker=node.querySelector('.strategy-flow-state')
    if(!marker){marker=document.createElement('em');marker.className='strategy-flow-state';node.appendChild(marker)}
    marker.className=`strategy-flow-state ${result.tone}`
    marker.textContent=result.label
    node.classList.toggle('done',result.tone==='done')
  })
}

function strategyGuideCopy(){
  const path=location.pathname.replace(/\/+$/,'')||'/'
  if(path==='/review-qa.html')return 'QA verifica execução, sentinelas e amostras. PASS técnico continua diferente de decisão científica humana.'
  if(path==='/press-review.html')return 'PRESS exige revisor humano independente. Parecer concluído continua diferente de GF-10, freeze e PRISMA.'
  if(path==='/regional-routes.html')return 'GF-01 documenta as rotas técnicas regionais. Completar esta etapa não autoriza freeze nem busca formal.'
  return ''
}

function ensureStrategyFlowGuide(){
  const flow=document.querySelector('.strategy-flow')
  if(!flow)return
  let guide=document.querySelector('#nutevStrategyFlowGuide')
  if(!guide){
    guide=document.createElement('div')
    guide.id='nutevStrategyFlowGuide'
    guide.className='strategy-flow-guide'
    flow.parentNode.insertBefore(guide,flow)
  }
  const copy=strategyGuideCopy()
  guide.innerHTML=`<strong>Roteiro operacional, não atalho de gate.</strong><span>A sequência orienta o trabalho; os gates permanecem independentes e nenhuma etapa autoriza automaticamente a decisão científica seguinte.${copy?` ${escapeHtml(copy)}`:''}</span>`
}

async function renderBuildIdentity(){
  try{
    const response=await fetch('/api/version',{cache:'no-store'})
    if(!response.ok)return
    const build=await response.json()
    const main=document.querySelector('main.main,.main,.workspace')
    if(!main||document.querySelector('#nutevBuildFooter'))return
    const footer=document.createElement('footer')
    footer.id='nutevBuildFooter'
    footer.className='product-footer'
    const commit=String(build.commit||'unknown')
    const shortCommit=commit==='unknown'?commit:commit.slice(0,12)
    const time=build.build_time&&build.build_time!=='unknown'?` · ${build.build_time}`:''
    footer.textContent=`NutEV · build ${shortCommit}${time}`
    main.appendChild(footer)
  }catch{}
}

function applyProductUi(root=document){
  normalizeNavigation()
  translateInternalEnums(root)
  explainResultCap()
  markStaticKpis()
  ensureSkipLink()
  ensureGlossary()
  ensureStrategyFlowGuide()
  decorateStrategyFlow()
}

ensureProductStyles()
applyProductUi()
renderBuildIdentity()

window.addEventListener('nutev:strategy-flow-update',()=>decorateStrategyFlow())
window.addEventListener('storage',event=>{if(event.key===STRATEGY_FLOW_STORAGE_KEY)decorateStrategyFlow()})

const observer=new MutationObserver(mutations=>{
  let changed=false
  for(const mutation of mutations){
    if(mutation.addedNodes.length){changed=true;break}
  }
  if(changed)applyProductUi(document)
})
observer.observe(document.documentElement,{childList:true,subtree:true})